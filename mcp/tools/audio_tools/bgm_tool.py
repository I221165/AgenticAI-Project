import os
from pathlib import Path
from pydantic import BaseModel, Field
from ...base_tool import BaseAgenticTool

# Resolve the project root (3 levels up from this file: tools/audio_tools/bgm_tool.py → mcp/tools/audio_tools → mcp/tools → mcp → project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BGM_DIR = str(_PROJECT_ROOT / "assets" / "bgm")

class BGMToolArgs(BaseModel):
    tone: str = Field(..., description="The mood/tone of the scene (e.g., 'tense', 'happy', 'mysterious').")
    bgm_dir: str = Field(_DEFAULT_BGM_DIR, description="Directory containing the royalty-free BGM tracks.")

class BGMTool(BaseAgenticTool):
    name = "bgm_selector"
    description = "Selects a background music track from a local royalty-free library based on the scene's tone/mood."
    args_schema = BGMToolArgs

    # Map common tone keywords to BGM filenames
    TONE_MAP = {
        "tense": ["tense", "suspense", "thriller", "dark"],
        "happy": ["happy", "joyful", "cheerful", "upbeat", "funny"],
        "sad": ["sad", "melancholy", "emotional", "heartbreak"],
        "mysterious": ["mysterious", "eerie", "curious", "wonder"],
        "peaceful": ["peaceful", "calm", "serene", "gentle", "soft"],
        "epic": ["epic", "heroic", "action", "dramatic", "intense"],
        "romantic": ["romantic", "love", "warm", "tender"],
    }

    def execute(self, tone: str, bgm_dir: str = None) -> str:
        """
        Finds all BGM files matching the scene tone and randomly picks one.
        Supports naming: happy.mp3, happy_1.mp3, happy_2.mp3, etc.
        Returns the file path, or empty string if no BGM files are available.
        """
        import random

        if bgm_dir is None:
            bgm_dir = _DEFAULT_BGM_DIR

        if not os.path.exists(bgm_dir):
            print(f"[BGM Selector] Warning: BGM directory '{bgm_dir}' does not exist.")
            return ""

        available_files = [f for f in os.listdir(bgm_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
        if not available_files:
            print("[BGM Selector] Warning: No BGM files found in assets/bgm/. Skipping BGM.")
            return ""

        tone_lower = tone.lower().strip()

        # Resolve the canonical tone via the keyword map
        canonical = tone_lower
        for canon, keywords in self.TONE_MAP.items():
            if tone_lower in keywords:
                canonical = canon
                break

        # Collect all files whose base name matches the canonical tone
        # Matches: "happy.mp3", "happy_1.mp3", "happy_2.mp3", "happy_anything.mp3"
        matches = []
        for f in available_files:
            name = os.path.splitext(f)[0].lower()
            if name == canonical or name.startswith(canonical + "_"):
                matches.append(f)

        if matches:
            chosen = random.choice(matches)
            path = os.path.join(bgm_dir, chosen)
            print(f"[BGM Selector] Tone '{tone}' -> matched {len(matches)} track(s), picked: '{chosen}'")
            return path

        # Fallback: pick any random track
        fallback = random.choice(available_files)
        print(f"[BGM Selector] No match for '{tone}', random fallback: '{fallback}'")
        return os.path.join(bgm_dir, fallback)
