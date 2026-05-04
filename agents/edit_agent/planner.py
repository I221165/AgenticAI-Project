"""
Edit Agent — Planner

Receives a classified intent dict from the IntentClassifier and produces
an ordered list of execution steps that the executor will carry out.

Each plan step is a dict:
  {
    "action":  str,   # e.g. "regen_image", "apply_filter", "rewrite_script"
    "target":  str,   # scene_id, character name, or "all"
    "params":  dict,  # action-specific parameters
  }
"""

from typing import List, Dict, Any


# Mapping from intent type → ordered action(s) the executor should run
_INTENT_TO_ACTIONS: Dict[str, List[str]] = {
    "voice_change":       ["update_voice_config", "regenerate_tts"],
    "scene_regen":        ["delete_scene_images", "regen_image", "rerender_clip"],
    "style_change":       ["update_style_tag", "regen_all_images", "rerender_all_clips"],
    "bgm_change":         ["select_bgm", "replace_bgm_track"],
    "script_edit":        ["rewrite_dialogue", "regenerate_tts"],
    "subtitle_remove":    ["toggle_subtitles"],
    "speed_change":       ["adjust_video_speed"],
    "brightness_filter":  ["apply_brightness"],
    "character_redesign": ["update_character_appearance", "regen_scene_images"],
    "filter_apply":       ["apply_colour_filter"],
    "transition_change":  ["update_transition_config", "rerender_transitions"],
    "music_add":          ["overlay_music_track"],
}


def plan(intent: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a classified intent into an ordered list of execution steps.

    Args:
        intent: Output of IntentClassifier.classify_intent()
                {"type": ..., "target": ..., "value": ..., "raw": ...}

    Returns:
        List of step dicts consumed by the executor.
    """
    intent_type = intent.get("type", "scene_regen")
    target      = intent.get("target", "all")
    value       = intent.get("value", "")

    actions = _INTENT_TO_ACTIONS.get(intent_type, ["scene_regen"])

    return [
        {"action": action, "target": target, "params": {"value": value}}
        for action in actions
    ]
