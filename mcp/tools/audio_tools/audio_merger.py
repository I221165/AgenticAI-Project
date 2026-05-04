import os
from pydantic import BaseModel, Field
from typing import List
from ...base_tool import BaseAgenticTool


class AudioMergerArgs(BaseModel):
    scene_audio_files: List[str] = Field(..., description="Ordered list of per-scene mixed audio file paths.")
    output_path: str = Field(..., description="Path for the final concatenated full-video audio file.")
    crossfade_ms: int = Field(500, description="Crossfade overlap in ms between adjacent scene audio clips.")


class AudioMergerTool(BaseAgenticTool):
    name = "audio_merger"
    description = (
        "Concatenates per-scene mixed audio files into a single full-video audio track "
        "with smooth crossfade transitions between scenes."
    )
    args_schema = AudioMergerArgs

    def execute(
        self,
        scene_audio_files: List[str],
        output_path: str,
        crossfade_ms: int = 500,
    ) -> str:
        """
        Concatenates scene audios with crossfade transitions.
        Returns the path to the merged full-video audio file.
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError("Install pydub: pip install pydub")

        if not scene_audio_files:
            raise ValueError("No scene audio files provided.")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        combined = AudioSegment.empty()
        for i, path in enumerate(scene_audio_files):
            if not os.path.exists(path):
                print(f"[AudioMerger] Skipping missing file: {path}")
                continue

            segment = (
                AudioSegment.from_mp3(path)
                if path.endswith(".mp3")
                else AudioSegment.from_wav(path)
            )

            if i == 0:
                combined = segment
            else:
                combined = combined.append(segment, crossfade=crossfade_ms)

        if len(combined) == 0:
            raise RuntimeError("All scene audio files were missing — nothing to merge.")

        combined.export(output_path, format="mp3")
        print(f"[AudioMerger] Full audio track saved: {output_path} ({len(combined) / 1000:.1f}s)")
        return output_path
