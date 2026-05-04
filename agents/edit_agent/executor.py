"""
Edit Agent — Executor

Receives the ordered plan from the Planner and dispatches each step to the
appropriate MCP tool.  The heavy lifting (image regen, filter application,
TTS, FFmpeg) is delegated to agent.py's handler functions; this module acts
as the routing layer between plan steps and those handlers.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from typing import List, Dict, Any


def execute_plan(
    plan: List[Dict[str, Any]],
    run_dir: str,
    intent: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute an ordered plan produced by planner.plan().

    Delegates to agent.py handler functions which call the appropriate
    MCP tools (image_generator, ffmpeg_tool, tts_tool, etc.).

    Args:
        plan:     List of step dicts {"action", "target", "params"}
        run_dir:  Absolute path to the run's output directory
        intent:   Original classified intent (passed through for context)

    Returns:
        {"status": "ok"|"error", "steps_run": int, "error": str|None}
    """
    from agents.edit_agent.agent import (
        _edit_scene_regen,
        _edit_style_change,
        _edit_bgm_change,
        _edit_script_edit,
        _edit_voice_change,
        _edit_subtitle_remove,
        _edit_speed_change,
        _edit_brightness_filter,
        _edit_character_redesign,
        _edit_filter_apply,
        _edit_transition_change,
        _edit_music_add,
    )

    # Map action prefixes to handler functions
    _HANDLER_MAP = {
        "regen_image":          lambda step: _edit_scene_regen(intent, run_dir),
        "delete_scene_images":  lambda step: None,
        "rerender_clip":        lambda step: None,
        "regen_all_images":     lambda step: _edit_style_change(intent, run_dir),
        "update_style_tag":     lambda step: None,
        "rerender_all_clips":   lambda step: None,
        "select_bgm":           lambda step: _edit_bgm_change(intent, run_dir),
        "replace_bgm_track":    lambda step: None,
        "rewrite_dialogue":     lambda step: _edit_script_edit(intent, run_dir),
        "regenerate_tts":       lambda step: None,
        "update_voice_config":  lambda step: _edit_voice_change(intent, run_dir),
        "toggle_subtitles":     lambda step: _edit_subtitle_remove(intent, run_dir),
        "adjust_video_speed":   lambda step: _edit_speed_change(intent, run_dir),
        "apply_brightness":     lambda step: _edit_brightness_filter(intent, run_dir),
        "update_character_appearance": lambda step: _edit_character_redesign(intent, run_dir),
        "regen_scene_images":   lambda step: None,
        "apply_colour_filter":  lambda step: _edit_filter_apply(intent, run_dir),
        "update_transition_config": lambda step: _edit_transition_change(intent, run_dir),
        "rerender_transitions": lambda step: None,
        "overlay_music_track":  lambda step: _edit_music_add(intent, run_dir),
    }

    steps_run = 0
    for step in plan:
        action = step.get("action", "")
        handler = _HANDLER_MAP.get(action)
        if handler:
            try:
                handler(step)
                steps_run += 1
            except Exception as e:
                return {"status": "error", "steps_run": steps_run, "error": str(e)}

    return {"status": "ok", "steps_run": steps_run, "error": None}
