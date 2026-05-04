import os
import shutil
import subprocess
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool

# Maps our transition names to FFmpeg xfade transition types
_XFADE_MAP = {
    "crossfade": "dissolve",
    "fade":      "fade",
    "wipe":      "wipeleft",
    "cut":       "dissolve",  # near-zero duration treated as cut
}
_INTRA_SCENE_TRANSITION = "dissolve"
_INTRA_TRANSITION_DUR   = 0.4   # seconds between frames within a scene
_INTER_TRANSITION_DUR   = 0.6   # seconds between scenes


class CompositorArgs(BaseModel):
    scene_clip_groups: List[List[str]] = Field(
        ..., description="Ordered list of scenes; each scene is a list of frame clip paths [wide, mid, close]."
    )
    scene_transitions: List[str] = Field(
        ..., description="Transition type between each pair of scenes (length = num_scenes - 1)."
    )
    output_path: str = Field(..., description="Path for the final composited video (no audio).")
    fps: int = Field(24, description="Video frame rate.")


class CompositorTool(BaseAgenticTool):
    name = "video_compositor"
    description = (
        "Composites per-scene frame clips into a single video: "
        "joins frames within each scene with crossfade, then joins scenes "
        "with the specified xfade transitions. Audio is added separately."
    )
    args_schema = CompositorArgs

    def execute(
        self,
        scene_clip_groups: List[List[str]],
        scene_transitions: List[str],
        output_path: str,
        fps: int = 24,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "_compositor_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        # 1. Compose each scene: join its 3 frame clips with intra-scene crossfade
        scene_videos: List[str] = []
        scene_durations: List[float] = []

        for i, frame_clips in enumerate(scene_clip_groups):
            valid = [c for c in frame_clips if os.path.exists(c)]
            if not valid:
                print(f"[Compositor] Scene {i}: no valid clips, skipping.")
                continue

            scene_out = os.path.join(tmp_dir, f"scene_{i:02d}.mp4")
            if len(valid) == 1:
                shutil.copy(valid[0], scene_out)
            else:
                clips_info = [
                    {"path": c, "duration": self._get_duration(c)}
                    for c in valid
                ]
                self._join_with_xfade(
                    clips_info,
                    transition=_INTRA_SCENE_TRANSITION,
                    transition_dur=_INTRA_TRANSITION_DUR,
                    output_path=scene_out,
                    fps=fps,
                )

            duration = self._get_duration(scene_out)
            scene_videos.append(scene_out)
            scene_durations.append(duration)
            print(f"[Compositor] Scene {i} composed: {duration:.1f}s")

        if not scene_videos:
            raise RuntimeError("No scene videos were composed.")

        # 2. Join all scene videos with inter-scene transitions
        if len(scene_videos) == 1:
            shutil.copy(scene_videos[0], output_path)
        else:
            clips_info = [
                {
                    "path": scene_videos[i],
                    "duration": scene_durations[i],
                    "transition": (scene_transitions[i] if i < len(scene_transitions) else "crossfade"),
                }
                for i in range(len(scene_videos))
            ]
            self._join_with_xfade(
                clips_info,
                transition=None,          # uses per-clip transition field
                transition_dur=_INTER_TRANSITION_DUR,
                output_path=output_path,
                fps=fps,
            )

        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)
        total = self._get_duration(output_path)
        print(f"[Compositor] Final video: {output_path} ({total:.1f}s)")
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _join_with_xfade(
        self,
        clips_info: List[Dict],
        transition: str | None,
        transition_dur: float,
        output_path: str,
        fps: int,
    ) -> str:
        """
        Joins N clips using FFmpeg xfade filter chaining.
        If `transition` is provided it applies to all joins.
        Otherwise each clip_info dict should have a 'transition' key.
        """
        if len(clips_info) == 1:
            shutil.copy(clips_info[0]["path"], output_path)
            return output_path

        cmd = ["ffmpeg", "-y"]
        for info in clips_info:
            cmd += ["-i", info["path"]]

        filter_parts = []
        running_offset = 0.0
        prev_label = "[0:v]"

        for i in range(1, len(clips_info)):
            t = transition_dur
            xfade_name = _XFADE_MAP.get(
                transition or clips_info[i - 1].get("transition", "crossfade"),
                "dissolve",
            )
            # For "cut" use near-zero transition duration
            if (transition or clips_info[i - 1].get("transition", "")) == "cut":
                t = 0.05

            running_offset += clips_info[i - 1]["duration"] - t
            out_label = f"[v{i}]"
            filter_parts.append(
                f"{prev_label}[{i}:v]"
                f"xfade=transition={xfade_name}:duration={t:.3f}:offset={running_offset:.3f}"
                f"{out_label}"
            )
            prev_label = out_label

        cmd += [
            "-filter_complex", ";".join(filter_parts),
            "-map", prev_label,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
            "-r", str(fps),
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg xfade join failed:\n{result.stderr[-600:]}")

        return output_path

    @staticmethod
    def _get_duration(video_path: str) -> float:
        """Returns video duration in seconds using ffprobe."""
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True, text=True,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 5.0  # fallback


def overlay_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Standalone helper: overlays an audio track onto a silent video.
    Video wins on length (audio is trimmed/padded to match video).
    """
    if not os.path.exists(audio_path):
        print(f"[Audio Overlay] Audio not found: {audio_path}. Skipping.")
        shutil.copy(video_path, output_path)
        return output_path

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        # No -shortest: if audio outlasts video, the last frame freezes rather
        # than cutting the audio mid-sentence.
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio overlay failed:\n{result.stderr[-400:]}")

    print(f"[Audio Overlay] Saved: {output_path}")
    return output_path
