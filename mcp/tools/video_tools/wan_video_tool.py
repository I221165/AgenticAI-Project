"""
Wan Image-to-Video MCP tool (Alibaba DashScope).
Tries wan2.6-i2v-flash (or whichever model is set via DASHSCOPE_WAN_I2V_MODEL).
Falls back to Ken Burns FFmpeg so the pipeline never breaks.
"""
import math
import os
import requests
import subprocess
import shutil
from typing import List, Optional
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool

_DASHSCOPE_REGION = os.getenv("DASHSCOPE_REGION", "singapore").lower()
_DASHSCOPE_BASE_URLS = {
    "singapore": "https://dashscope-intl.aliyuncs.com/api/v1",
    "virginia":  "https://dashscope-us.aliyuncs.com/api/v1",
    "beijing":   "https://dashscope.aliyuncs.com/api/v1",
}
_DASHSCOPE_BASE = _DASHSCOPE_BASE_URLS.get(_DASHSCOPE_REGION, _DASHSCOPE_BASE_URLS["singapore"])

# Duration caps per model (DashScope spec)
_MODEL_MAX_SEC = {
    "wan2.2-i2v-flash":   5.0,
    "wan2.5-i2v-preview": 10.0,
    "wan2.6-i2v-flash":   15.0,
    "wan2.6-i2v":         15.0,
    "wan2.7-i2v":         15.0,
}
_DEFAULT_MODEL = "wan2.6-i2v-flash"


def _safe_get(obj, key: str, default=""):
    if obj is None:
        return default
    try:
        return obj[key]
    except (KeyError, TypeError):
        pass
    try:
        return getattr(obj, key)
    except (KeyError, AttributeError):
        return default


def _dashscope_key() -> str:
    return os.getenv("DASHSCOPE_API_KEY", "").strip()


def _configure_dashscope():
    import dashscope
    dashscope.api_key = _dashscope_key()
    dashscope.base_http_api_url = _DASHSCOPE_BASE


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 5.0


def _ffmpeg_concat(chunk_paths: List[str], output_path: str):
    """Concatenate MP4 chunks using FFmpeg concat demuxer."""
    list_file = output_path + ".concat.txt"
    with open(list_file, "w") as f:
        for p in chunk_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.remove(list_file)
    except Exception:
        pass
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed:\n{result.stderr[-400:]}")


def _ken_burns_fallback(
    image_path: str,
    output_path: str,
    duration: float,
    camera_work: str,
    fps: int,
    width: int,
    height: int,
) -> str:
    """Ken Burns via FFmpeg — guaranteed fallback."""
    total_frames = max(int(duration * fps), 1)
    step = 0.3 / max(total_frames, 1)
    size = f"{width}x{height}"

    motion_map = {
        "zoom_in":  (
            f"zoompan=z='min(zoom+{step:.6f},1.3)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={size}:fps={fps}"
        ),
        "zoom_out": (
            f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.0,zoom-{step:.6f}))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={size}:fps={fps}"
        ),
        "pan_right": (
            f"zoompan=z=1.3:"
            f"x='min(iw*(1-1/zoom), iw/zoom*(on/{total_frames}))':"
            f"y='ih/2-(ih/zoom/2)':d={total_frames}:s={size}:fps={fps}"
        ),
        "pan_left": (
            f"zoompan=z=1.3:"
            f"x='max(0, iw/zoom*(1-on/{total_frames}))':"
            f"y='ih/2-(ih/zoom/2)':d={total_frames}:s={size}:fps={fps}"
        ),
    }
    zoompan = motion_map.get(camera_work, (
        f"zoompan=z=1.0:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={size}:fps={fps}"
    ))
    vf = f"scale={width * 2}:{height * 2},{zoompan},scale={width}:{height}"

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-framerate", str(fps),
        "-i", image_path, "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-r", str(fps), output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg fallback failed:\n{result.stderr[-400:]}")
    return output_path


class WanVideoArgs(BaseModel):
    image_path: str = Field(..., description="Path to the source image.")
    output_path: str = Field(..., description="Path for the output MP4 clip.")
    prompt: str = Field(..., description="Motion/scene description for Wan I2V.")
    duration: float = Field(5.0, description="Target clip duration in seconds.")
    resolution: str = Field("720P", description="480P | 720P | 1080P")
    camera_work: str = Field("zoom_in", description="Ken Burns fallback motion: zoom_in | zoom_out | pan_right | pan_left | static")
    fps: int = Field(24, description="FPS for Ken Burns fallback.")
    width: int = Field(1280, description="Width for Ken Burns fallback.")
    height: int = Field(720, description="Height for Ken Burns fallback.")
    force_fallback: bool = Field(False, description="Skip Wan and use Ken Burns directly.")


class WanVideoTool(BaseAgenticTool):
    name = "wan_video"
    description = (
        "Animates a still image into a video clip using Alibaba Wan I2V (DashScope). "
        "Automatically falls back to Ken Burns FFmpeg if Wan is unavailable or fails. "
        "Returns path to the generated MP4."
    )
    args_schema = WanVideoArgs

    def execute(
        self,
        image_path: str,
        output_path: str,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720P",
        camera_work: str = "zoom_in",
        fps: int = 24,
        width: int = 1280,
        height: int = 720,
        force_fallback: bool = False,
    ) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        key = _dashscope_key()
        if not force_fallback and key:
            try:
                result = self._wan_i2v(image_path, output_path, prompt, duration, resolution)
                if result:
                    return result
            except Exception as e:
                print(f"[WanVideo] Wan I2V failed, using Ken Burns fallback: {e}")

        print(f"[WanVideo] Ken Burns fallback → {os.path.basename(output_path)}")
        return _ken_burns_fallback(image_path, output_path, duration, camera_work, fps, width, height)

    def _wan_i2v(
        self,
        image_path: str,
        output_path: str,
        prompt: str,
        duration: float,
        resolution: str,
    ) -> Optional[str]:
        model = os.getenv("DASHSCOPE_WAN_I2V_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
        max_sec = _MODEL_MAX_SEC.get(model, 10.0)
        num_chunks = max(1, math.ceil(duration / max_sec))

        try:
            _configure_dashscope()
            from dashscope import VideoSynthesis
            from http import HTTPStatus
        except ImportError:
            print("[WanVideo] dashscope SDK not installed — pip install dashscope")
            return None

        abs_image = os.path.abspath(image_path).replace("\\", "/")
        img_url = f"file://{abs_image}"

        print(f"[WanVideo] {model} ({resolution}) — {num_chunks} chunk(s) for {duration:.1f}s scene")

        chunk_paths: List[str] = []
        tmp_dir = output_path + "_chunks"
        os.makedirs(tmp_dir, exist_ok=True)

        for chunk_idx in range(num_chunks):
            chunk_path = os.path.join(tmp_dir, f"chunk_{chunk_idx:02d}.mp4")
            chunk_dur = min(max_sec, duration - chunk_idx * max_sec)
            print(f"[WanVideo] Chunk {chunk_idx + 1}/{num_chunks} ({chunk_dur:.1f}s)…")

            rsp = VideoSynthesis.call(
                model=model,
                prompt=prompt[:800],
                img_url=img_url,
                resolution=resolution,
                api_key=_dashscope_key(),
            )

            task_status = _safe_get(rsp.output, "task_status")
            video_url   = _safe_get(rsp.output, "video_url")
            task_code   = _safe_get(rsp.output, "code")
            task_msg    = _safe_get(rsp.output, "message")

            if rsp.status_code != HTTPStatus.OK or task_status != "SUCCEEDED" or not video_url:
                print(f"[WanVideo] Chunk {chunk_idx + 1} failed: status={task_status} code={task_code} msg={task_msg}")
                # Clean up and signal fallback
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return None

            r = requests.get(video_url, timeout=180)
            r.raise_for_status()
            with open(chunk_path, "wb") as f:
                f.write(r.content)
            chunk_paths.append(chunk_path)
            print(f"[WanVideo] Chunk {chunk_idx + 1}/{num_chunks} done ({_probe_duration(chunk_path):.1f}s)")

        # Assemble
        if len(chunk_paths) == 1:
            shutil.copy2(chunk_paths[0], output_path)
        else:
            print(f"[WanVideo] Concatenating {len(chunk_paths)} chunks…")
            _ffmpeg_concat(chunk_paths, output_path)

        shutil.rmtree(tmp_dir, ignore_errors=True)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[WanVideo] Saved: {output_path} ({size_mb:.1f} MB) via {model}")
        return output_path
