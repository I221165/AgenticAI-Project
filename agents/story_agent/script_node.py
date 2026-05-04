import json
import re
from typing import Dict, Any, List
from mcp.tool_registry import ToolRegistry

# Duration → scene count and dialogue density
_DURATION_CONFIG = {
    "short":  {"scene_count": "3",   "dialogue_range": "2-3", "sec_range": "8 to 20"},
    "medium": {"scene_count": "5",   "dialogue_range": "3-4", "sec_range": "10 to 30"},
    "long":   {"scene_count": "7",   "dialogue_range": "4-5", "sec_range": "15 to 40"},
}

# Style → visual prompt prefix for image generation
_STYLE_PREFIXES = {
    "2D animated":         "2D animated short film style, flat design with expressive characters",
    "anime":               "anime art style, detailed line art, vibrant colors, Studio Ghibli inspired",
    "Pixar 3D":            "Pixar-style 3D animation, soft lighting, expressive faces, cinematic",
    "comic book":          "comic book art style, bold ink outlines, halftone shading, dynamic composition",
    "watercolor":          "watercolor painting style, soft color washes, painterly textures, artistic",
    "realistic cinematic": "realistic cinematic photography, shallow depth of field, film grain, dramatic lighting",
}

# Maps scene tone to a Ken Burns camera movement for Phase 3
_TONE_TO_CAMERA = {
    "tense":      "zoom_in",
    "suspense":   "zoom_in",
    "mysterious": "zoom_in",
    "dark":       "zoom_in",
    "sad":        "zoom_out",
    "melancholy": "zoom_out",
    "emotional":  "zoom_out",
    "peaceful":   "pan_right",
    "calm":       "pan_right",
    "serene":     "pan_left",
    "happy":      "pan_right",
    "joyful":     "pan_left",
    "epic":       "pan_right",
    "heroic":     "pan_right",
    "action":     "pan_left",
    "romantic":   "zoom_in",
}

# Maps tone-change pairs to FFmpeg xfade transition types
_TRANSITION_RULES = {
    ("tense", "peaceful"):   "fade",
    ("sad", "happy"):        "fade",
    ("mysterious", "epic"):  "wipe",
    ("action", "peaceful"):  "fade",
}
_DEFAULT_TRANSITION = "crossfade"
_LAST_SCENE_TRANSITION = "fade"


def analyze_emotions(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Scans dialogue lines and fills in missing emotions via text heuristics."""
    emotion_keywords = {
        "angry":   ["!", "how dare", "unacceptable", "enough"],
        "happy":   ["love", "happy", "wonderful", "great", "amazing", "joy"],
        "sad":     ["sorry", "miss", "lost", "alone", "cry", "tears"],
        "scared":  ["afraid", "fear", "terrified", "help"],
        "excited": ["incredible", "unbelievable", "wow", "can't believe"],
        "confused": ["?", "why", "how", "what is"],
    }
    for scene in script.get("scenes", []):
        for line in scene.get("dialogue_lines", []):
            if not line.get("emotion") or line.get("emotion").strip() == "":
                text = line.get("text", "").lower()
                matched = "neutral"
                for emotion, triggers in emotion_keywords.items():
                    if any(t in text for t in triggers):
                        matched = emotion
                        break
                line["emotion"] = matched
    return script


def build_visual_prompt(script: Dict[str, Any], character_roster: Dict[str, Any] = None, style: str = "2D animated") -> Dict[str, Any]:
    """
    Tool: Enriches each scene's visual_description into a full image-generation prompt.
    Includes art style, setting, characters present, lighting, and quality keywords.
    Also assigns camera_work based on scene tone.
    """
    style_prefix = _STYLE_PREFIXES.get(style, f"{style} style")
    characters = {c["name"]: c for c in (character_roster or {}).get("characters", [])}

    tone_lighting = {
        "tense":      "dramatic side lighting, deep shadows, high contrast",
        "mysterious": "dim moonlight, misty atmosphere, cool blue tones",
        "sad":        "soft overcast light, muted desaturated palette",
        "peaceful":   "warm golden hour sunlight, soft diffused light",
        "happy":      "bright warm sunlight, vibrant colors, soft shadows",
        "epic":       "dramatic golden backlighting, god rays, cinematic flare",
        "heroic":     "strong backlight silhouette, warm epic tones",
        "action":     "dynamic harsh lighting, motion blur hints",
        "romantic":   "warm soft candlelight, gentle bokeh background",
        "dark":       "near-total darkness, single cold spotlight",
    }

    for scene in script.get("scenes", []):
        setting = scene.get("setting", "")
        tone = scene.get("tone", "neutral").lower()
        existing_desc = scene.get("visual_description", "")

        # Identify which characters appear in this scene
        speakers = {line["character_name"] for line in scene.get("dialogue_lines", [])}
        char_descriptions = []
        for name in speakers:
            if name in characters:
                char_descriptions.append(
                    f"{name} ({characters[name].get('visual_description', 'a character')})"
                )

        lighting = tone_lighting.get(tone, "natural balanced lighting")
        char_str = "; ".join(char_descriptions) if char_descriptions else ""
        char_clause = f"Characters present: {char_str}. " if char_str else ""

        # Build the enriched visual prompt using the chosen art style
        base = existing_desc if existing_desc else setting
        scene["visual_description"] = (
            f"{style_prefix}, {base}. "
            f"{char_clause}"
            f"{lighting}. "
            f"Cinematic composition, expressive faces, detailed backgrounds, "
            f"high quality illustration, 16:9 aspect ratio."
        )

        # Assign camera movement for Phase 3 Ken Burns effect
        scene["camera_work"] = _TONE_TO_CAMERA.get(tone, "pan_right")

    return script


def assign_transitions(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Assigns FFmpeg xfade transition types between consecutive scenes."""
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes):
        is_last = (i == len(scenes) - 1)
        if is_last:
            scene["transition_to_next"] = _LAST_SCENE_TRANSITION
            continue
        current_tone = scene.get("tone", "neutral").lower()
        next_tone = scenes[i + 1].get("tone", "neutral").lower()
        pair = (current_tone, next_tone)
        scene["transition_to_next"] = _TRANSITION_RULES.get(pair, _DEFAULT_TRANSITION)
    return script


def validate_duration(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Calculates scene duration based on dialogue word count (~2.5 words/sec)."""
    for scene in script.get("scenes", []):
        total_words = sum(
            len(line.get("text", "").split())
            for line in scene.get("dialogue_lines", [])
        )
        scene["duration_estimate_sec"] = max(5, int(total_words / 2.5))
    return script


def normalize_scene_ids(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Ensures all scene IDs follow the 'scene_N' format."""
    for i, scene in enumerate(script.get("scenes", []), start=1):
        scene["scene_id"] = f"scene_{i}"
    return script


def generate_script(
    story_output: Dict[str, Any],
    character_roster: Dict[str, Any],
    style: str = "2D animated",
    duration: str = "medium",
    provider: int = 2,
    language: str = "English",
) -> Dict[str, Any]:
    """
    Agent Node: Generates the ScriptOutput (scenes with dialogue).
    """
    text_generator = ToolRegistry.get_tool("text_generator")
    json_structurer = ToolRegistry.get_tool("json_structurer")

    story_context = json.dumps(story_output)
    character_context = json.dumps(character_roster)

    cfg = _DURATION_CONFIG.get(duration, _DURATION_CONFIG["medium"])
    n_scenes = int(cfg["scene_count"])

    # Build the scenes skeleton so the model sees exactly N slots — this is more
    # reliable than a text rule like "write N scenes" which models often ignore.
    scene_skeleton = ",\n".join(
        f'    {{"scene_id": "scene_{i}", "setting": "...", "visual_description": "...", '
        f'"tone": "tense", "duration_estimate_sec": 12, "dialogue_lines": '
        f'[{{"character_name": "Name", "text": "...", "emotion": "neutral"}}]}}'
        for i in range(1, n_scenes + 1)
    )

    system_prompt = (
        "You are an expert screenwriter. Output ONLY a valid JSON object — no markdown, no prose, no explanation.\n\n"
        f"The JSON must contain EXACTLY {n_scenes} scenes in this structure:\n"
        "{{\n"
        '  "scenes": [\n'
        f"{scene_skeleton}\n"
        "  ]\n"
        "}}\n\n"
        "Rules (follow strictly):\n"
        f"- The scenes array must have EXACTLY {n_scenes} entries — no more, no fewer\n"
        "- tone must be exactly one of: tense, mysterious, peaceful, happy, sad, epic, heroic, action, dark, romantic\n"
        "- emotion must be exactly one of: happy, sad, angry, scared, neutral, excited, confused, nervous, determined\n"
        f"- Each scene must have {cfg['dialogue_range']} dialogue_lines with meaningful spoken text\n"
        f"- duration_estimate_sec must be an integer between {cfg['sec_range']}\n"
        "- Only use character names that appear in the provided Character Roster\n"
        f"- All dialogue_lines text must be written in {language}\n"
        "- Output raw JSON only — no markdown code fences, no text before or after"
    )

    user_prompt = (
        f"Story Arc:\n{story_context}\n\n"
        f"Character Roster:\n{character_context}\n\n"
        f"Now write exactly {n_scenes} scenes and output the JSON:"
    )

    # 1. Generate script scenes using the powerful 70B model
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_name="llama-3.3-70b-versatile" if provider == 2 else "llama3",
        provider=provider
    )

    # 2. Structure into ScriptOutput using the fast model
    script_json = json_structurer.execute(
        raw_text=raw_text,
        target_schema_name="ScriptOutput",
        model_name="llama-3.1-8b-instant" if provider == 2 else "llama3",
        provider=provider
    )

    # 3. Apply post-processing tools in order
    actual = len(script_json.get("scenes", []))
    print(f"[Script] Generated {actual} scenes (target: {n_scenes}, duration: {duration})")
    script_json = normalize_scene_ids(script_json)
    script_json = analyze_emotions(script_json)
    script_json = validate_duration(script_json)
    script_json = build_visual_prompt(script_json, character_roster, style=style)
    script_json = assign_transitions(script_json)

    return script_json
