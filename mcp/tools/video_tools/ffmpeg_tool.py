import os
import subprocess
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool


class FFmpegKenBurnsArgs(BaseModel):
    image_path: str = Field(..., description="Path to the source image.")
    output_path: str = Field(..., description="Path for the output video clip.")
    duration: float = Field(..., description="Clip duration in seconds.")
    camera_work: str = Field("zoom_in", description="zoom_in | zoom_out | pan_right | pan_left | static")
    width: int = Field(1280, description="Output video width.")
    height: int = Field(720, description="Output video height.")
    fps: int = Field(24, description="Frames per second.")


class FFmpegTool(BaseAgenticTool):
    name = "ffmpeg_ken_burns"
    description = (
        "Creates an animated video clip from a still image using the Ken Burns "
        "(zoom/pan) effect via FFmpeg's zoompan filter."
    )
    args_schema = FFmpegKenBurnsArgs

    def execute(
        self,
        image_path: str,
        output_path: str,
        duration: float,
        camera_work: str = "zoom_in",
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
    ) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        total_frames = max(int(duration * fps), 1)
        zoompan = self._build_zoompan(camera_work, total_frames, width, height, fps)

        # Scale source 2x before zoompan to give zoom headroom without pixelation
        vf = f"scale={width * 2}:{height * 2},{zoompan},scale={width}:{height}"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", str(fps),
            "-i", image_path,
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            output_path,
        ]

        print(f"[FFmpeg] Ken Burns ({camera_work}, {duration:.1f}s) → {os.path.basename(output_path)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg zoompan failed:\n{result.stderr[-600:]}")

        return output_path

    def _build_zoompan(self, camera_work: str, d: int, w: int, h: int, fps: int) -> str:
        """Build FFmpeg zoompan filter string for the given camera movement."""
        step = 0.3 / max(d, 1)  # zoom change per frame to go from 1.0 → 1.3 over d frames
        size = f"{w}x{h}"

        if camera_work == "zoom_in":
            return (
                f"zoompan=z='min(zoom+{step:.6f},1.3)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={size}:fps={fps}"
            )
        elif camera_work == "zoom_out":
            return (
                f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.0,zoom-{step:.6f}))':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={size}:fps={fps}"
            )
        elif camera_work == "pan_right":
            return (
                f"zoompan=z=1.3:"
                f"x='min(iw*(1-1/zoom), iw/zoom*(on/{d}))':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={size}:fps={fps}"
            )
        elif camera_work == "pan_left":
            return (
                f"zoompan=z=1.3:"
                f"x='max(0, iw/zoom*(1-on/{d}))':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={size}:fps={fps}"
            )
        else:  # static
            return (
                f"zoompan=z=1.0:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={size}:fps={fps}"
            )

    @staticmethod
    def check_ffmpeg() -> bool:
        """Returns True if ffmpeg is available in PATH."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
