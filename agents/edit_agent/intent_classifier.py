"""
Edit Agent — Phase 5: Intent Classifier

Classifies a free-text edit instruction into one of the supported intent types:
  voice_change        — change a character's voice personality / tone
  scene_regen         — regenerate image(s) or dialogue for a specific scene
  style_change        — switch the overall visual art style
  bgm_change          — change the background music for a scene or all scenes
  script_edit         — rewrite a scene's dialogue
  subtitle_remove     — remove or toggle subtitles/captions
  speed_change        — change video playback speed (faster / slower)
  brightness_filter   — apply brightness / darkness adjustment to a scene
  character_redesign  — change a character's visual appearance description
  filter_apply        — apply a colour or visual filter (sepia, noir, warm, etc.)
  transition_change   — change the scene transition effect (fade, wipe, dissolve, etc.)
  music_add           — add a music track or sound effect overlay

Output schema:
  {
    "type": "<intent_type>",
    "target": "<scene_id | character_name | 'all'>",
    "value": "<new value / instruction>",
    "raw": "<original instruction>"
  }
"""

import os
import json
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

SUPPORTED_INTENTS = [
    "voice_change",
    "scene_regen",
    "style_change",
    "bgm_change",
    "script_edit",
    "subtitle_remove",
    "speed_change",
    "brightness_filter",
    "character_redesign",
    "filter_apply",
    "transition_change",
    "music_add",
]

_SYSTEM_PROMPT = f"""\
You are an AI that classifies video editing instructions for an animated film.

Given the user's instruction, output ONLY valid JSON with exactly these fields:
{{
  "type": one of {json.dumps(SUPPORTED_INTENTS)},
  "target": scene_id like "scene_3", a character name, or "all",
  "value": the new style/voice/instruction to apply,
  "raw": the original instruction verbatim
}}

Rules:
- voice_change: user wants to change how a character sounds ("make Ethan's voice darker", "change voice to deep")
- scene_regen: user wants to redo an image or animation ("redo scene 3 in anime style", "regenerate scene 2")
- style_change: user changes the global art style ("switch to watercolor", "make it look like pixar")
- bgm_change: user wants different music ("make the BGM more intense in scene 2", "change background music")
- script_edit: user wants dialogue rewritten ("rewrite scene 4 so Ethan is angrier", "change the line in scene 1")
- subtitle_remove: user wants subtitles removed or toggled ("remove subtitles", "hide captions", "no subtitles")
- speed_change: user wants video speed changed ("speed up scene 2", "slow down the intro", "make it faster")
- brightness_filter: user wants brightness adjusted ("make scene 3 darker", "brighten scene 1", "more contrast")
- character_redesign: user wants a character's look changed ("give Ethan blue hair", "make Olivia look younger")
- filter_apply: user wants a visual filter ("add sepia filter", "make it noir", "warm colour grade")
- transition_change: user wants scene transitions changed ("use fade between scenes", "add dissolve transition")
- music_add: user wants music added ("add dramatic music to scene 4", "add sound effect at the start")

Output only JSON, no markdown.
"""


def classify_intent(instruction: str, run_dir: str) -> dict:
    """
    Classify an edit instruction.  Tries the real LLM first,
    falls back to a rule-based classifier if the LLM call fails.
    """
    try:
        result = _llm_classify(instruction)
        # LLM may return "all" even when a character name is in the instruction — fix it up
        if result.get("target") == "all":
            char = _extract_character_target(instruction.lower(), run_dir)
            if char != "all":
                result["target"] = char
        return result
    except Exception as e:
        print(f"[IntentClassifier] LLM failed ({e}), using rule-based fallback")
        return _rule_classify(instruction, run_dir)


def _llm_classify(instruction: str) -> dict:
    import os
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    response = llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f'Instruction: "{instruction}"\n\nOutput the JSON:'),
    ])
    text = response.content if hasattr(response, "content") else str(response)
    text = re.sub(r"```json|```", "", text).strip()
    parsed = json.loads(text)
    parsed.setdefault("raw", instruction)
    if parsed.get("type") not in SUPPORTED_INTENTS:
        raise ValueError(f"Unknown intent type from LLM: {parsed.get('type')}")
    return parsed


def _rule_classify(instruction: str, run_dir: str = "") -> dict:
    """Keyword-based fallback classifier covering all 12 intent types."""
    low = instruction.lower()

    # Check more-specific multi-word phrases first to avoid false positives
    if any(k in low for k in ["subtitle", "caption", "closed caption", "remove text"]):
        intent_type = "subtitle_remove"
    elif any(k in low for k in ["speed", "faster", "slower", "slow down", "speed up", "fast forward", "time-lapse"]):
        intent_type = "speed_change"
    elif any(k in low for k in ["darker", "brighter", "brightness", "bright", "lighter", "light", "lighten", "contrast", "dim", "exposure"]):
        intent_type = "brightness_filter"
    # style_change before character_redesign so "look like anime" → style, not redesign
    # "art" is intentionally excluded — it matches "start", "heart", etc.
    elif any(k in low for k in ["style", "anime", "pixar", "watercolor", "drawing"]) or re.search(r'\bart\b', low):
        intent_type = "style_change"
    # filter_apply before character_redesign so "look like noir" → filter, not redesign
    elif any(k in low for k in ["sepia", "noir", "filter", "colour grade", "color grade", "tint", "warm tone", "cold tone", "cool tone"]):
        intent_type = "filter_apply"
    elif any(k in low for k in ["redesign", "hair", "outfit", "appearance", "character look", "wardrobe"]):
        intent_type = "character_redesign"
    elif any(k in low for k in ["transition", "fade", "wipe", "dissolve", "crossfade"]):
        intent_type = "transition_change"
    # music_add before bgm_change: "add music" / "overlay music" / "sound effect" are more specific
    elif any(k in low for k in ["add music", "sound effect", "overlay music", "overlay", "add dramatic", "audio track"]):
        intent_type = "music_add"
    elif any(k in low for k in ["voice", "sound", "tone", "pitch", "speak"]):
        intent_type = "voice_change"
    elif any(k in low for k in ["music", "bgm", "background music", "soundtrack"]):
        intent_type = "bgm_change"
    elif any(k in low for k in ["dialogue", "line", "say", "speech", "script", "rewrite", "angrier"]):
        intent_type = "script_edit"
    else:
        intent_type = "scene_regen"

    # 1. Try explicit scene number
    scene_match = re.search(r"scene[_\s]?(\d+)", low)
    if scene_match:
        target = f"scene_{scene_match.group(1)}"
    else:
        # 2. Try character name match from characters.json
        target = _extract_character_target(low, run_dir)

    return {
        "type": intent_type,
        "target": target,
        "value": instruction,
        "raw": instruction,
    }


def _extract_character_target(low: str, run_dir: str) -> str:
    """Return a matched character name from characters.json, or 'all'."""
    if not run_dir:
        return "all"
    chars_path = os.path.join(run_dir, "characters.json")
    if not os.path.exists(chars_path):
        return "all"
    try:
        with open(chars_path) as f:
            data = json.load(f)
        for char in data.get("characters", []):
            name = char.get("name", "")
            # Match full name or any single word from the name (e.g. "conductor" matches "The Conductor")
            parts = [p.lower() for p in name.split() if len(p) > 2]
            if name.lower() in low or any(p in low for p in parts):
                return name
    except Exception:
        pass
    return "all"
