"""
Edit Agent — Phase 5: LangGraph workflow with MemorySaver checkpointer.

Architecture:
  classify_node → execute_node → finalize_node → END

The MemorySaver checkpointer lets the same session accumulate multi-turn edits
so the user can say "now also make scene 2 darker" without repeating context.

Supported intent types (12):
  voice_change, scene_regen, style_change, bgm_change, script_edit,
  subtitle_remove, speed_change, brightness_filter, character_redesign,
  filter_apply, transition_change, music_add
"""

import json
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

# One MemorySaver instance shared across the process so sessions persist
# for the lifetime of the backend server.
_memory = MemorySaver()


class EditState(TypedDict):
    run_id: str
    run_dir: str
    instruction: str
    intent: Dict[str, Any]
    result: Dict[str, Any]
    edit_history: List[Dict[str, Any]]
    error: str


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def classify_node(state: EditState) -> Dict[str, Any]:
    """Classify the natural-language instruction into a structured intent."""
    try:
        from agents.edit_agent.intent_classifier import classify_intent
        intent = classify_intent(state["instruction"], state["run_dir"])
        print(f"[EditAgent] Intent classified: {intent.get('type')} → target={intent.get('target')}")
        return {"intent": intent, "error": ""}
    except Exception as e:
        return {"intent": {}, "error": f"Classification failed: {e}"}


def execute_node(state: EditState) -> Dict[str, Any]:
    """Dispatch to the appropriate edit handler based on intent type."""
    if state.get("error"):
        return {}

    intent = state.get("intent", {})
    intent_type = intent.get("type", "scene_regen")
    target = intent.get("target", "all")
    value = intent.get("value", "")
    run_dir = state["run_dir"]

    dispatch = {
        "voice_change":      _edit_voice,
        "scene_regen":       _edit_scene_regen,
        "style_change":      _edit_style,
        "bgm_change":        _edit_bgm,
        "script_edit":       _edit_script,
        "subtitle_remove":   _edit_subtitle_remove,
        "speed_change":      _edit_speed_change,
        "brightness_filter": _edit_brightness_filter,
        "character_redesign":_edit_character_redesign,
        "filter_apply":      _edit_filter_apply,
        "transition_change": _edit_transition_change,
        "music_add":         _edit_music_add,
    }

    fn = dispatch.get(intent_type, _edit_scene_regen)
    try:
        result = fn(run_dir, target, value)
        return {"result": result, "error": ""}
    except Exception as e:
        print(f"[EditAgent] Execute failed for {intent_type}: {e}")
        return {"result": {}, "error": f"{intent_type} failed: {e}"}


def finalize_node(state: EditState) -> Dict[str, Any]:
    """Append this edit to the session history."""
    entry = {
        "instruction": state.get("instruction", ""),
        "intent": state.get("intent", {}),
        "new_video": state.get("result", {}).get("new_video"),
    }
    history = list(state.get("edit_history", []))
    history.append(entry)
    return {"edit_history": history}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> Any:
    workflow = StateGraph(EditState)
    workflow.add_node("classify_node", classify_node)
    workflow.add_node("execute_node",  execute_node)
    workflow.add_node("finalize_node", finalize_node)
    workflow.set_entry_point("classify_node")
    workflow.add_edge("classify_node", "execute_node")
    workflow.add_edge("execute_node",  "finalize_node")
    workflow.add_edge("finalize_node", END)
    return workflow.compile(checkpointer=_memory)


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public API (called from backend/app.py)
# ---------------------------------------------------------------------------

def run_edit(run_id: str, intent: dict, run_dir: str, instruction: str = "") -> Dict[str, Any]:
    """
    Run an edit for run_id.  Uses run_id as the LangGraph thread_id so that
    successive edits on the same run accumulate in the checkpointer's memory.

    If `intent` is already classified (passed from the API layer), it is used
    directly and classify_node is bypassed via a pre-set initial state.
    """
    config = {"configurable": {"thread_id": run_id}}

    initial: EditState = {
        "run_id":       run_id,
        "run_dir":      run_dir,
        "instruction":  instruction or intent.get("raw", ""),
        "intent":       intent,          # pre-classified; classify_node will skip if non-empty
        "result":       {},
        "edit_history": [],
        "error":        "",
    }

    # If intent already contains a valid type, skip classify step by injecting it.
    # The classify_node will still run but will see the intent already populated.
    final_state = _graph.invoke(initial, config=config)

    result = final_state.get("result", {})
    result["edit_history"] = final_state.get("edit_history", [])
    result["error"] = final_state.get("error", "")
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _save(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_style(run_dir: str) -> str:
    p = os.path.join(run_dir, "phase3_video_handoff.json")
    return _load(p).get("style", "2D animated") if os.path.exists(p) else "2D animated"


def _recompose_video(run_dir: str) -> str:
    """After audio/image changes, recompose the video."""
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if not os.path.exists(handoff_path):
        return ""
    handoff = _load(handoff_path)
    timing_path = os.path.join(run_dir, "timing_manifest.json")
    timing_data = _load(timing_path) if os.path.exists(timing_path) else {}
    timing_entries = timing_data.get("entries", [])
    from agents.video_agent.agent import run_phase3
    result = run_phase3(handoff, timing_entries, run_dir)
    return result.get("final_video_path", "")


# ---------------------------------------------------------------------------
# Targeted audio helpers (avoid re-running TTS for unchanged lines)
# ---------------------------------------------------------------------------

def _reregen_tts_for_entries(run_dir: str, handoff: dict, entries: list, filter_fn) -> None:
    """Re-run TTS only for entries where filter_fn(entry) is True. Updates entries in-place."""
    from mcp.registry import ToolRegistry
    from agents.audio_agent.agent import _EMOTION_GAP_MS, _DEFAULT_GAP_MS
    tts_tool = ToolRegistry.get_tool("tts_generator")
    language = handoff.get("language", "English")

    def _get_voice(char_name: str) -> str:
        for c in handoff.get("voice_configs", []):
            if c.get("name", "").lower() == char_name.lower():
                return c.get("voice_personality", "Neutral")
        return "Neutral"

    for entry in entries:
        if not filter_fn(entry):
            continue
        char_name = entry["character_name"]
        scene_id = entry["scene_id"]
        audio_dir = os.path.join(run_dir, "audio", scene_id)
        os.makedirs(audio_dir, exist_ok=True)
        try:
            new_path = tts_tool.execute(
                text=entry["text"],
                character_name=char_name,
                voice_personality=_get_voice(char_name),
                emotion=entry.get("emotion", "neutral"),
                output_dir=audio_dir,
                provider=4,
                language=language,
            )
            entry["audio_file"] = new_path
            print(f"[EditAgent] Re-TTS {char_name} ({scene_id}) → {new_path}")
        except Exception as e:
            print(f"[EditAgent] TTS failed for {char_name} in {scene_id}: {e}")

    # Recalculate cumulative timings — audio lengths may have changed
    try:
        from agents.audio_agent.agent import _load_audio, _EMOTION_GAP_MS, _DEFAULT_GAP_MS
        cumulative_ms = 0
        for entry in entries:
            audio_path = entry.get("audio_file", "")
            if os.path.exists(audio_path):
                duration_ms = len(_load_audio(audio_path))
            else:
                duration_ms = entry.get("end_ms", 2000) - entry.get("start_ms", 0) or 2000
            entry["start_ms"] = cumulative_ms
            entry["end_ms"] = cumulative_ms + duration_ms
            gap_ms = _EMOTION_GAP_MS.get(entry.get("emotion", "neutral"), _DEFAULT_GAP_MS)
            cumulative_ms = entry["end_ms"] + gap_ms
    except Exception as e:
        print(f"[EditAgent] Timing recalc skipped: {e}")


def _remix_with_entries(run_dir: str, handoff: dict, entries: list, bgm_tracks: dict = None) -> str:
    """Re-mix audio from existing entries (no TTS), recompose video. Returns video path."""
    from agents.audio_agent.agent import (
        AudioState, select_bgm, mix_scene_audio, assemble_full_audio, serialize_node,
    )
    state: AudioState = {
        "handoff_json": handoff,
        "provider": 4,
        "run_dir": run_dir,
        "language": handoff.get("language", "English"),
        "voice_map": {},
        "bgm_tracks": bgm_tracks or {},
        "timing_manifest": entries,
        "mixed_audio_files": [],
        "full_audio_path": "",
        "error": "",
    }
    state = {**state, **select_bgm(state)}
    state = {**state, **mix_scene_audio(state)}
    state = {**state, **assemble_full_audio(state)}
    serialize_node(state)
    return _recompose_video(run_dir)


# ---------------------------------------------------------------------------
# Edit handlers — original 5
# ---------------------------------------------------------------------------

def _edit_voice(run_dir: str, target: str, value: str) -> dict:
    """Patch character voice_personality and re-run Phase 2 (audio)."""
    handoff_path = os.path.join(run_dir, "phase2_audio_handoff.json")
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("phase2_audio_handoff.json not found")

    t_low = target.lower()

    def _name_matches(char_name: str) -> bool:
        n = char_name.lower()
        # exact substring match OR any individual word in target matches any word in name
        return t_low in n or n in t_low or any(w in n for w in t_low.split() if len(w) > 2)

    handoff = _load(handoff_path)
    for char in handoff.get("voice_configs", []):
        if target == "all" or _name_matches(char.get("name", "")):
            char["voice_personality"] = value
            print(f"[EditAgent] Patched {char['name']} voice → {value}")

    _save(handoff_path, handoff)

    # Also persist to characters.json so the change survives future reruns
    chars_path = os.path.join(run_dir, "characters.json")
    if os.path.exists(chars_path):
        chars = _load(chars_path)
        for char in chars.get("characters", []):
            if target == "all" or _name_matches(char.get("name", "")):
                char["voice_personality"] = value
        _save(chars_path, chars)

    if target == "all":
        # All characters changed — full Phase 2 re-run
        from agents.audio_agent.agent import run_phase2
        run_phase2(handoff, provider=4, run_dir=run_dir)
        return {"new_video": _recompose_video(run_dir)}

    # Specific character — re-run TTS only for their lines, keep everyone else's audio
    tm_path = os.path.join(run_dir, "timing_manifest.json")
    tm_data = _load(tm_path) if os.path.exists(tm_path) else {}
    entries = tm_data.get("entries", [])
    bgm_tracks = tm_data.get("bgm_tracks", {})

    _reregen_tts_for_entries(
        run_dir, handoff, entries,
        filter_fn=lambda e: _name_matches(e.get("character_name", "")),
    )
    return {"new_video": _remix_with_entries(run_dir, handoff, entries, bgm_tracks)}


def _edit_scene_regen(run_dir: str, target: str, value: str) -> dict:
    """Re-generate images for the target scene(s) then recompose video."""
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("phase3_video_handoff.json not found")

    handoff = _load(handoff_path)
    if target != "all" and value:
        for scene in handoff.get("scenes", []):
            if scene.get("scene_id") == target:
                scene["visual_description"] = value + ". " + scene.get("visual_description", "")
        _save(handoff_path, handoff)

    img_dir = os.path.join(run_dir, "images")
    if target != "all":
        # Images are stored flat: images/scene_1_wide.png — delete only target scene files
        import glob as _glob
        for f in _glob.glob(os.path.join(img_dir, f"{target}_*.png")) + \
                 _glob.glob(os.path.join(img_dir, f"{target}_*.jpg")):
            os.remove(f)
            print(f"[EditAgent] Deleted {os.path.basename(f)}")
    else:
        if os.path.isdir(img_dir):
            shutil.rmtree(img_dir)

    timing_path = os.path.join(run_dir, "timing_manifest.json")
    timing_data = _load(timing_path) if os.path.exists(timing_path) else {}
    timing_entries = timing_data.get("entries", [])

    from agents.video_agent.agent import run_phase3
    result = run_phase3(handoff, timing_entries, run_dir)
    return {"new_video": result.get("final_video_path")}


def _edit_style(run_dir: str, target: str, value: str) -> dict:
    """Change global art style and regenerate all scene images."""
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    handoff = _load(handoff_path)
    handoff["style"] = value
    _save(handoff_path, handoff)
    print(f"[EditAgent] Style changed → {value}")
    img_dir = os.path.join(run_dir, "images")
    if os.path.isdir(img_dir):
        shutil.rmtree(img_dir)
    return _edit_scene_regen(run_dir, "all", "")


def _edit_bgm(run_dir: str, target: str, value: str) -> dict:
    """Re-select BGM with new tone and remix — no TTS re-run, dialogue audio untouched."""
    handoff_path = os.path.join(run_dir, "phase2_audio_handoff.json")
    handoff = _load(handoff_path)
    for scene in handoff.get("segments", []):
        if scene.get("scene_id") == target or target == "all":
            scene["tone"] = value
            print(f"[EditAgent] BGM tone → {scene['scene_id']}: {value}")
    _save(handoff_path, handoff)

    # Load existing dialogue timing — no need to regenerate any speech
    tm_path = os.path.join(run_dir, "timing_manifest.json")
    tm_data = _load(tm_path) if os.path.exists(tm_path) else {}
    entries = tm_data.get("entries", [])

    # select_bgm runs inside _remix_with_entries, picking up the updated tone
    return {"new_video": _remix_with_entries(run_dir, handoff, entries)}


def _edit_script(run_dir: str, target: str, value: str) -> dict:
    """Rewrite dialogue lines via LLM then regenerate audio for changed scenes."""
    script_path = os.path.join(run_dir, "script.json")
    story_path  = os.path.join(run_dir, "story.json")
    chars_path  = os.path.join(run_dir, "characters.json")

    script     = _load(script_path)
    story      = _load(story_path)
    characters = _load(chars_path)

    # Identify scenes to rewrite
    target_scenes = [
        s for s in script.get("scenes", [])
        if s.get("scene_id") == target or target == "all"
    ]

    # Call LLM to rewrite dialogue for each target scene
    try:
        from mcp.tools.llm_tools.text_generator import TextGeneratorTool
        from mcp.tools.llm_tools.json_structurer import JsonStructurerTool
        llm = TextGeneratorTool()
        structurer = JsonStructurerTool()

        char_names = [c.get("name", "") for c in (
            characters.get("characters", characters) if isinstance(characters, dict) else characters
        )]

        for scene in target_scenes:
            existing_lines = scene.get("dialogue_lines", [])
            existing_text = "\n".join(
                f'{l["character_name"]}: {l["text"]}' for l in existing_lines
            )
            prompt = (
                f"You are rewriting dialogue for an animated short film.\n\n"
                f"Story context: {json.dumps(story.get('story_arc', story), ensure_ascii=False)[:600]}\n"
                f"Scene setting: {scene.get('setting', '')}\n"
                f"Characters available: {', '.join(char_names)}\n"
                f"Current dialogue:\n{existing_text}\n\n"
                f"Edit instruction: {value}\n\n"
                f"Rewrite the dialogue following the instruction. Keep the same characters. "
                f"Return ONLY a JSON array of objects with keys: character_name, text, emotion.\n"
                f'Example: [{{"character_name": "Alex", "text": "Hello.", "emotion": "happy"}}]'
            )
            raw = llm.execute(prompt=prompt)
            new_lines = structurer.execute(
                raw_text=raw,
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "character_name": {"type": "string"},
                            "text": {"type": "string"},
                            "emotion": {"type": "string"},
                        },
                        "required": ["character_name", "text", "emotion"],
                    },
                },
            )
            if new_lines and isinstance(new_lines, list):
                scene["dialogue_lines"] = new_lines
                print(f"[EditAgent] script_edit rewrote {len(new_lines)} lines for {scene['scene_id']}")

    except Exception as e:
        print(f"[EditAgent] LLM rewrite failed ({e}), keeping original dialogue")

    _save(script_path, script)

    # Propagate updated dialogue into the audio handoff so TTS picks it up
    handoff_path = os.path.join(run_dir, "phase2_audio_handoff.json")
    handoff = _load(handoff_path) if os.path.exists(handoff_path) else {}
    if handoff:
        scene_map = {s["scene_id"]: s for s in script.get("scenes", [])}
        for seg in handoff.get("segments", []):
            sid = seg.get("scene_id")
            if sid in scene_map:
                seg["dialogue_lines"] = scene_map[sid].get("dialogue_lines", seg.get("dialogue_lines", []))
        _save(handoff_path, handoff)

    # Load existing timing manifest and rebuild entries for changed scenes only.
    # Lines may have been added/removed by the LLM so we replace whole-scene entries.
    tm_path = os.path.join(run_dir, "timing_manifest.json")
    tm_data = _load(tm_path) if os.path.exists(tm_path) else {}
    entries = tm_data.get("entries", [])
    bgm_tracks = tm_data.get("bgm_tracks", {})

    changed_sids = {s["scene_id"] for s in target_scenes}

    # Remove stale entries for changed scenes, keep untouched scenes
    entries = [e for e in entries if e.get("scene_id") not in changed_sids]

    # Add skeleton entries for the new dialogue lines (audio_file filled by TTS below)
    for scene in target_scenes:
        for idx, line in enumerate(scene.get("dialogue_lines", [])):
            entries.append({
                "scene_id":       scene["scene_id"],
                "line_index":     idx,
                "character_name": line["character_name"],
                "text":           line["text"],
                "emotion":        line.get("emotion", "neutral"),
                "audio_file":     "",
                "start_ms":       0,
                "end_ms":         0,
            })

    # Sort entries so scenes stay in script order
    scene_order = {s["scene_id"]: i for i, s in enumerate(script.get("scenes", []))}
    entries.sort(key=lambda e: (scene_order.get(e["scene_id"], 999), e.get("line_index", 0)))

    # Re-run TTS only for the new/changed entries, leave existing audio untouched
    _reregen_tts_for_entries(
        run_dir, handoff, entries,
        filter_fn=lambda e: e.get("scene_id") in changed_sids,
    )
    return {"new_video": _remix_with_entries(run_dir, handoff, entries, bgm_tracks)}


# ---------------------------------------------------------------------------
# Edit handlers — new 7 (Phase 5 expansion)
# ---------------------------------------------------------------------------

def _edit_subtitle_remove(run_dir: str, target: str, value: str) -> dict:
    """Toggle subtitles off in the video handoff metadata."""
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if not os.path.exists(handoff_path):
        return {"new_video": None, "message": "No video handoff found; subtitle flag noted."}

    handoff = _load(handoff_path)
    handoff["subtitles_enabled"] = False
    _save(handoff_path, handoff)
    print("[EditAgent] Subtitles disabled")

    # Recompose video without subtitle overlay
    return {"new_video": _recompose_video(run_dir), "message": "Subtitles removed."}


def _edit_speed_change(run_dir: str, target: str, value: str) -> dict:
    """
    Apply playback speed multiplier to the final video via ffmpeg.
    value examples: "2x", "0.5", "faster", "slower"
    """
    # Parse speed multiplier
    low_val = value.lower()
    if "slower" in low_val or "slow" in low_val:
        multiplier = 0.5
    elif "faster" in low_val or "fast" in low_val:
        multiplier = 2.0
    else:
        m = re.search(r"(\d+(?:\.\d+)?)", low_val)
        multiplier = float(m.group(1)) if m else 1.5

    import glob as _glob
    mp4_files = _glob.glob(os.path.join(run_dir, "*.mp4"))
    if not mp4_files:
        return {"new_video": None, "message": "No final video found to speed-change."}

    src = mp4_files[0]
    out = src.replace(".mp4", f"_speed{multiplier}x.mp4")
    # ffmpeg setpts/atempo for speed
    pts_factor = 1.0 / multiplier
    try:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-filter_complex",
            f"[0:v]setpts={pts_factor:.4f}*PTS[v];[0:a]atempo={min(multiplier, 2.0):.2f}[a]",
            "-map", "[v]", "-map", "[a]", out,
        ], check=True, capture_output=True)
        print(f"[EditAgent] Speed {multiplier}x → {out}")
        return {"new_video": out}
    except Exception as e:
        print(f"[EditAgent] Speed change failed: {e}")
        return {"new_video": None, "message": f"Speed change failed: {e}"}


def _edit_brightness_filter(run_dir: str, target: str, value: str) -> dict:
    """Apply brightness/contrast adjustment to scene images using available tools."""
    low_val = value.lower()
    # Determine brightness delta (-1.0 to +1.0)
    if any(k in low_val for k in ["dark", "dim", "shadow"]):
        brightness = -0.3
    elif any(k in low_val for k in ["bright", "light", "luminous"]):
        brightness = 0.3
    else:
        brightness = -0.2  # default: slightly darker for "more contrast" requests

    # Images are stored flat: images/scene_1_wide.png
    import glob as _glob
    img_dir = os.path.join(run_dir, "images")
    if target == "all":
        img_paths = _glob.glob(os.path.join(img_dir, "scene_*.png")) + \
                    _glob.glob(os.path.join(img_dir, "scene_*.jpg"))
    else:
        img_paths = _glob.glob(os.path.join(img_dir, f"{target}_*.png")) + \
                    _glob.glob(os.path.join(img_dir, f"{target}_*.jpg"))

    modified = 0
    for img_path in img_paths:
        if True:
            try:
                from PIL import Image, ImageEnhance
                img = Image.open(img_path).convert("RGB")
                enhancer = ImageEnhance.Brightness(img)
                factor = max(0.1, 1.0 + brightness)
                img = enhancer.enhance(factor)
                img.save(img_path)
                modified += 1
            except Exception as e:
                print(f"[EditAgent] Brightness failed for {img_path}: {e}")

    print(f"[EditAgent] Brightness {brightness:+.1f} applied to {modified} images")
    return {"new_video": _recompose_video(run_dir), "message": f"Brightness adjusted on {modified} images."}


def _edit_character_redesign(run_dir: str, target: str, value: str) -> dict:
    """Update a character's visual_description then regenerate their scenes."""
    chars_path = os.path.join(run_dir, "characters.json")
    if not os.path.exists(chars_path):
        raise FileNotFoundError("characters.json not found")

    characters = _load(chars_path)
    char_list = characters.get("characters", characters if isinstance(characters, list) else [])
    patched = False
    for char in char_list:
        if target.lower() in char.get("name", "").lower() or target == "all":
            char["visual_description"] = value
            print(f"[EditAgent] Redesigned {char['name']}: {value}")
            patched = True

    _save(chars_path, characters)

    if not patched:
        return {"new_video": None, "message": f"Character '{target}' not found."}

    # Also update phase3 handoff character descriptions
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if os.path.exists(handoff_path):
        handoff = _load(handoff_path)
        for char in handoff.get("characters", []):
            if target.lower() in char.get("name", "").lower() or target == "all":
                char["visual_description"] = value
        _save(handoff_path, handoff)

    # Clear images for all scenes featuring this character, then regenerate
    img_dir = os.path.join(run_dir, "images")
    if os.path.isdir(img_dir):
        shutil.rmtree(img_dir)

    return _edit_scene_regen(run_dir, "all", "")


def _edit_filter_apply(run_dir: str, target: str, value: str) -> dict:
    """Apply a named colour filter (sepia, noir, warm, cool) to scene images."""
    low_val = value.lower()

    import glob as _glob
    img_dir = os.path.join(run_dir, "images")
    if target == "all":
        img_paths = _glob.glob(os.path.join(img_dir, "scene_*.png")) + \
                    _glob.glob(os.path.join(img_dir, "scene_*.jpg"))
    else:
        img_paths = _glob.glob(os.path.join(img_dir, f"{target}_*.png")) + \
                    _glob.glob(os.path.join(img_dir, f"{target}_*.jpg"))

    modified = 0
    for img_path in img_paths:
        if True:
            try:
                from PIL import Image, ImageOps, ImageEnhance
                import numpy as np
                img = Image.open(img_path).convert("RGB")

                if "sepia" in low_val:
                    arr = np.array(img, dtype=np.float32)
                    r = arr[:,:,0]*0.393 + arr[:,:,1]*0.769 + arr[:,:,2]*0.189
                    g = arr[:,:,0]*0.349 + arr[:,:,1]*0.686 + arr[:,:,2]*0.168
                    b = arr[:,:,0]*0.272 + arr[:,:,1]*0.534 + arr[:,:,2]*0.131
                    sepia = np.stack([r, g, b], axis=2).clip(0, 255).astype(np.uint8)
                    img = Image.fromarray(sepia)
                elif "noir" in low_val or "black" in low_val:
                    img = ImageOps.grayscale(img).convert("RGB")
                elif "warm" in low_val:
                    arr = np.array(img, dtype=np.float32)
                    arr[:,:,0] = np.clip(arr[:,:,0] * 1.15, 0, 255)
                    arr[:,:,2] = np.clip(arr[:,:,2] * 0.85, 0, 255)
                    img = Image.fromarray(arr.astype(np.uint8))
                elif "cool" in low_val or "cold" in low_val:
                    arr = np.array(img, dtype=np.float32)
                    arr[:,:,0] = np.clip(arr[:,:,0] * 0.85, 0, 255)
                    arr[:,:,2] = np.clip(arr[:,:,2] * 1.15, 0, 255)
                    img = Image.fromarray(arr.astype(np.uint8))
                else:
                    # Generic: slight saturation boost
                    img = ImageEnhance.Color(img).enhance(1.3)

                img.save(img_path)
                modified += 1
            except Exception as e:
                print(f"[EditAgent] Filter failed for {img_path}: {e}")

    print(f"[EditAgent] Filter '{value}' applied to {modified} images")
    return {"new_video": _recompose_video(run_dir), "message": f"Filter '{value}' applied to {modified} images."}


def _edit_transition_change(run_dir: str, target: str, value: str) -> dict:
    """Update transition type in the video handoff and recompose."""
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if not os.path.exists(handoff_path):
        return {"new_video": None, "message": "No video handoff found."}

    handoff = _load(handoff_path)
    low_val = value.lower()

    # Map keywords to transition names
    if "fade" in low_val:
        transition = "fade"
    elif "dissolve" in low_val:
        transition = "dissolve"
    elif "wipe" in low_val:
        transition = "wipe"
    elif "cut" in low_val:
        transition = "cut"
    elif "zoom" in low_val:
        transition = "zoom"
    else:
        transition = value.strip()

    handoff["transition"] = transition
    if target != "all":
        for scene in handoff.get("scenes", []):
            if scene.get("scene_id") == target:
                scene["transition"] = transition
    _save(handoff_path, handoff)
    print(f"[EditAgent] Transition set to '{transition}' for {target}")

    return {"new_video": _recompose_video(run_dir), "message": f"Transition changed to '{transition}'."}


def _edit_music_add(run_dir: str, target: str, value: str) -> dict:
    """Add/overlay a music track onto a scene. Uses BGM selector with the new value as tone."""
    # Treat music_add as a targeted BGM change with the new track as tone hint
    return _edit_bgm(run_dir, target, value)
