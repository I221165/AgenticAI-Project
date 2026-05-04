import os
import subprocess
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool


class SubtitleArgs(BaseModel):
    timing_entries: List[Dict[str, Any]] = Field(..., description="Timing manifest entries.")
    output_dir: str = Field(..., description="Directory to save the .srt file.")


class SubtitleTool(BaseAgenticTool):
    name = "subtitle_generator"
    description = "Generates an SRT subtitle file from the timing manifest entries."
    args_schema = SubtitleArgs

    def execute(self, timing_entries: List[Dict[str, Any]], output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        srt_path = os.path.join(output_dir, "subtitles.srt")

        lines = []
        for idx, entry in enumerate(timing_entries, start=1):
            start = self._ms_to_srt(entry.get("start_ms", 0))
            end = self._ms_to_srt(entry.get("end_ms", 0))
            character = entry.get("character_name", "")
            text = entry.get("text", "")
            lines.append(f"{idx}\n{start} --> {end}\n[{character}]: {text}\n")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[Subtitle] SRT saved: {srt_path} ({len(timing_entries)} entries)")
        return srt_path

    @staticmethod
    def _ms_to_srt(ms: int) -> str:
        h = ms // 3_600_000
        m = (ms % 3_600_000) // 60_000
        s = (ms % 60_000) // 1_000
        r = ms % 1_000
        return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"

    @staticmethod
    def burn_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
        """
        Burns the SRT into the video. Falls back gracefully if libass is unavailable.
        Returns output_path on success, original video_path on failure.
        """
        # FFmpeg on Windows needs forward-slashes and the colon in the drive letter escaped
        srt_ffmpeg = srt_path.replace("\\", "/")
        if len(srt_ffmpeg) > 1 and srt_ffmpeg[1] == ":":
            srt_ffmpeg = srt_ffmpeg[0] + "\\:" + srt_ffmpeg[2:]

        style = "FontSize=20,PrimaryColour=&Hffffff&,OutlineColour=&H000000&,Outline=2,Bold=1"
        vf = f"subtitles='{srt_ffmpeg}':force_style='{style}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:a", "copy",
            "-preset", "fast",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Subtitle] Burn-in skipped (libass unavailable): {result.stderr[-200:]}")
            return video_path

        print(f"[Subtitle] Subtitles burned in: {output_path}")
        return output_path
