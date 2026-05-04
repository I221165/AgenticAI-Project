import os
import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from mcp.tool_registry import ToolRegistry
from .planner import plan_audio_voices

try:
    from shared.utils.progress import report as _report
except ImportError:
    def _report(*a, **kw): pass

# Gap (ms) between dialogue lines per emotion — faster for heated exchanges, slower for dramatic ones
_EMOTION_GAP_MS = {
    "angry":     150,
    "furious":   100,
    "excited":   150,
    "happy":     250,
    "neutral":   300,
    "determined":250,
    "confused":  400,
    "nervous":   350,
    "scared":    400,
    "sad":       600,
    "melancholy":700,
    "whispering":500,
}
_DEFAULT_GAP_MS = 300

# Normalization target in dBFS for TTS clips before mixing
_TARGET_DBFS = -6.0

# BGM volume reduction (negative = quieter); lower = less intrusive behind dialogue
_BGM_DB_REDUCTION = -12

# Fade durations for BGM at scene boundaries
_BGM_FADE_IN_MS = 1000
_BGM_FADE_OUT_MS = 2000


class AudioState(TypedDict):
    handoff_json: Dict[str, Any]
    provider: int
    run_dir: str
    language: str
    voice_map: Dict[str, str]
    bgm_tracks: Dict[str, str]
    timing_manifest: List[Dict[str, Any]]
    mixed_audio_files: List[str]   # ordered per-scene mixed paths
    full_audio_path: str           # final concatenated audio for whole video
    error: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_clip(audio_segment):
    """Normalise a pydub AudioSegment to _TARGET_DBFS."""
    if audio_segment.dBFS == float("-inf"):
        return audio_segment  # silent clip, skip
    change_db = _TARGET_DBFS - audio_segment.dBFS
    return audio_segment.apply_gain(change_db)


def _load_audio(path: str):
    from pydub import AudioSegment
    return AudioSegment.from_mp3(path) if path.endswith(".mp3") else AudioSegment.from_wav(path)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def assign_voices(state: AudioState) -> Dict[str, Any]:
    """Node: Maps characters to ElevenLabs voice IDs (used when provider=2)."""
    if state.get("error"):
        return {}
    try:
        _report(2, 5, "Assigning character voices…")
        voice_map = plan_audio_voices({"characters": state["handoff_json"].get("voice_configs", [])})
        _report(2, 10, "Voice assignment complete")
        return {"voice_map": voice_map}
    except Exception as e:
        return {"error": f"Voice mapping failed: {str(e)}"}


def generate_dialogue_audio(state: AudioState) -> Dict[str, Any]:
    """Node: Generates a TTS audio file for every dialogue line across all scenes."""
    if state.get("error"):
        return {}

    try:
        from pydub import AudioSegment
    except ImportError:
        return {"error": "Install pydub: pip install pydub"}

    handoff_json = state["handoff_json"]
    provider = state.get("provider", 4)
    voice_map = state.get("voice_map", {})
    run_dir = state.get("run_dir", "run_outputs")
    language = state.get("language", handoff_json.get("language", "English"))

    tts_tool = ToolRegistry.get_tool("tts_generator")
    timing_manifest = []
    cumulative_ms = 0

    # Pre-count total lines so we can report real per-line progress
    all_segments = handoff_json.get("segments", [])
    total_lines = sum(len(s.get("dialogue_lines", [])) for s in all_segments)
    completed_lines = 0
    _report(2, 12, f"Generating TTS audio for {total_lines} dialogue lines…")

    for scene in all_segments:
        scene_id = scene.get("scene_id")
        scene_audio_dir = os.path.join(run_dir, "audio", scene_id)
        os.makedirs(scene_audio_dir, exist_ok=True)

        for idx, line in enumerate(scene.get("dialogue_lines", [])):
            character_name = line.get("character_name")
            text = line.get("text")
            emotion = line.get("emotion", "neutral").lower()

            # For ElevenLabs use the mapped voice_id; for others use the personality string
            voice_param = (
                voice_map.get(character_name, "Rachel")
                if provider == 2
                else next(
                    (c.get("voice_personality", "Neutral") for c in handoff_json.get("voice_configs", []) if c.get("name") == character_name),
                    "Neutral"
                )
            )

            try:
                completed_lines += 1
                # Progress: 12% → 78% distributed across all TTS lines
                tts_prog = 12 + int(66 * completed_lines / max(total_lines, 1))
                _report(2, tts_prog, f"TTS ({completed_lines}/{total_lines}): {character_name} [{emotion}] — {scene_id}")

                audio_path = tts_tool.execute(
                    text=text,
                    character_name=character_name,
                    voice_personality=voice_param,
                    emotion=emotion,
                    output_dir=scene_audio_dir,
                    provider=provider,
                    language=language,
                )

                clip = _load_audio(audio_path)
                clip = _normalize_clip(clip)       # normalise to consistent volume
                duration_ms = len(clip)

                # Re-export the normalised clip in place
                clip.export(audio_path, format="mp3" if audio_path.endswith(".mp3") else "wav")

                start_ms = cumulative_ms
                end_ms = cumulative_ms + duration_ms
                gap_ms = _EMOTION_GAP_MS.get(emotion, _DEFAULT_GAP_MS)
                cumulative_ms = end_ms + gap_ms

                timing_manifest.append({
                    "scene_id": scene_id,
                    "line_index": idx,
                    "character_name": character_name,
                    "text": text,
                    "emotion": emotion,
                    "audio_file": audio_path,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                })

            except Exception as e:
                print(f"[Audio Agent] Failed TTS for {character_name} in {scene_id}: {e}")

    return {"timing_manifest": timing_manifest}


def select_bgm(state: AudioState) -> Dict[str, Any]:
    """Node: Selects background music per scene based on tone."""
    if state.get("error"):
        return {}

    _report(2, 80, "Selecting background music for each scene…")
    bgm_tool = ToolRegistry.get_tool("bgm_selector")
    bgm_tracks = {}

    for scene in state["handoff_json"].get("segments", []):
        scene_id = scene.get("scene_id", "unknown")
        tone = scene.get("tone", "neutral")
        bgm_path = bgm_tool.execute(tone=tone)
        if bgm_path:
            bgm_tracks[scene_id] = bgm_path

    _report(2, 84, f"BGM selected for {len(bgm_tracks)} scenes")
    return {"bgm_tracks": bgm_tracks}


def mix_scene_audio(state: AudioState) -> Dict[str, Any]:
    """
    Node: Mixes dialogue clips + BGM per scene.
    - Normalises dialogue to consistent volume
    - Adds emotion-aware gaps between lines
    - Applies BGM fade-in/fade-out at scene boundaries
    - BGM ducked to _BGM_DB_REDUCTION behind dialogue
    """
    if state.get("error"):
        return {}

    try:
        from pydub import AudioSegment
    except ImportError:
        print("[Mixer] pydub not installed, skipping.")
        return {}

    timing_manifest = state.get("timing_manifest", [])
    bgm_tracks = state.get("bgm_tracks", {})
    run_dir = state.get("run_dir", "run_outputs")

    # Group dialogue entries by scene, preserving line order
    scenes: Dict[str, List] = {}
    for entry in timing_manifest:
        sid = entry["scene_id"]
        scenes.setdefault(sid, []).append(entry)

    mixed_dir = os.path.join(run_dir, "audio", "mixed")
    os.makedirs(mixed_dir, exist_ok=True)

    mixed_audio_files = []
    total_scenes = len(scenes)
    mixed_count = 0
    _report(2, 86, f"Mixing dialogue + BGM for {total_scenes} scenes…")

    for scene_id, entries in scenes.items():
        sorted_entries = sorted(entries, key=lambda x: x["line_index"])

        # Build dialogue track with emotion-aware gaps
        dialogue_track = AudioSegment.empty()
        for entry in sorted_entries:
            path = entry["audio_file"]
            if not os.path.exists(path):
                print(f"[Mixer] Missing: {path}")
                continue
            clip = _load_audio(path)
            emotion = entry.get("emotion", "neutral").lower()
            gap_ms = _EMOTION_GAP_MS.get(emotion, _DEFAULT_GAP_MS)
            dialogue_track += clip + AudioSegment.silent(duration=gap_ms)

        if len(dialogue_track) == 0:
            print(f"[Mixer] No clips for {scene_id}, skipping.")
            continue

        # Overlay BGM with fade-in and fade-out
        bgm_path = bgm_tracks.get(scene_id)
        combined = dialogue_track

        if bgm_path and os.path.exists(bgm_path):
            try:
                bgm = _load_audio(bgm_path)

                # Loop BGM to cover the full dialogue duration
                while len(bgm) < len(dialogue_track):
                    bgm += bgm
                bgm = bgm[: len(dialogue_track)]

                # Duck volume and apply fade-in/fade-out
                bgm = bgm + _BGM_DB_REDUCTION
                bgm = bgm.fade_in(_BGM_FADE_IN_MS).fade_out(_BGM_FADE_OUT_MS)

                combined = dialogue_track.overlay(bgm)
                print(
                    f"[Mixer] {scene_id}: dialogue {len(dialogue_track) / 1000:.1f}s "
                    f"+ BGM '{os.path.basename(bgm_path)}' at {_BGM_DB_REDUCTION}dB"
                )
            except Exception as e:
                print(f"[Mixer] BGM load failed for {scene_id}: {e}")
        else:
            print(f"[Mixer] {scene_id}: No BGM, dialogue only.")

        output_path = os.path.join(mixed_dir, f"{scene_id}_mixed.mp3")
        combined.export(output_path, format="mp3")
        print(f"[Mixer] Saved: {output_path}")
        mixed_audio_files.append(output_path)
        mixed_count += 1
        mix_prog = 86 + int(8 * mixed_count / max(total_scenes, 1))
        _report(2, mix_prog, f"Mixed {scene_id} ({mixed_count}/{total_scenes})")

    return {"mixed_audio_files": mixed_audio_files}


def assemble_full_audio(state: AudioState) -> Dict[str, Any]:
    """
    Node: Concatenates all per-scene mixed audios into a single full-video audio track.
    Phase 3 uses this file to sync visuals to audio.
    """
    if state.get("error"):
        return {}

    _report(2, 94, "Assembling full audio track from all scenes…")
    mixed_files = state.get("mixed_audio_files", [])
    if not mixed_files:
        print("[Full Audio] No mixed files to assemble.")
        return {"full_audio_path": ""}

    merger_tool = ToolRegistry.get_tool("audio_merger")
    run_dir = state.get("run_dir", "run_outputs")
    output_path = os.path.join(run_dir, "audio", "full_audio.mp3")

    try:
        full_path = merger_tool.execute(
            scene_audio_files=mixed_files,
            output_path=output_path,
            crossfade_ms=500,
        )
        return {"full_audio_path": full_path}
    except Exception as e:
        print(f"[Full Audio] Assembly failed: {e}")
        return {"full_audio_path": ""}


def serialize_node(state: AudioState) -> Dict[str, Any]:
    """Node: Saves timing manifest and updates the Phase 3 video handoff with audio paths."""
    if state.get("error"):
        return {}

    run_dir = state.get("run_dir", "run_outputs")
    os.makedirs(run_dir, exist_ok=True)

    # 1. Write timing_manifest.json
    manifest_path = os.path.join(run_dir, "timing_manifest.json")
    manifest_data = {
        "entries": state.get("timing_manifest", []),
        "bgm_tracks": state.get("bgm_tracks", {}),
        "full_audio_path": state.get("full_audio_path", ""),
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)

    # 2. Patch phase3_video_handoff.json with audio paths so Phase 3 can locate audio
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if os.path.exists(handoff_path):
        with open(handoff_path) as f:
            handoff = json.load(f)
        handoff["timing_manifest_path"] = manifest_path
        handoff["full_audio_path"] = state.get("full_audio_path", "")
        handoff["mixed_audio_dir"] = os.path.join(run_dir, "audio", "mixed")
        with open(handoff_path, "w") as f:
            json.dump(handoff, f, indent=2)
        print(f"[Serialize] phase3_video_handoff.json updated with audio paths.")

    return {}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_phase2_graph() -> StateGraph:
    workflow = StateGraph(AudioState)

    workflow.add_node("assign_voices",         assign_voices)
    workflow.add_node("generate_dialogue_audio", generate_dialogue_audio)
    workflow.add_node("select_bgm",            select_bgm)
    workflow.add_node("mix_scene_audio",       mix_scene_audio)
    workflow.add_node("assemble_full_audio",   assemble_full_audio)
    workflow.add_node("serialize_node",        serialize_node)

    workflow.set_entry_point("assign_voices")
    workflow.add_edge("assign_voices",           "generate_dialogue_audio")
    workflow.add_edge("generate_dialogue_audio", "select_bgm")
    workflow.add_edge("select_bgm",              "mix_scene_audio")
    workflow.add_edge("mix_scene_audio",         "assemble_full_audio")
    workflow.add_edge("assemble_full_audio",     "serialize_node")
    workflow.add_edge("serialize_node",          END)

    return workflow.compile()


def run_phase2(
    handoff_json: Dict[str, Any],
    provider: int = 4,
    run_dir: str = "run_outputs",
) -> Dict[str, Any]:
    """Run Phase 2 given the Phase 1 audio handoff JSON."""
    app = build_phase2_graph()
    os.makedirs(os.path.join(run_dir, "audio"), exist_ok=True)

    initial_state: AudioState = {
        "handoff_json": handoff_json,
        "provider": provider,
        "run_dir": run_dir,
        "language": handoff_json.get("language", "English"),
        "voice_map": {},
        "bgm_tracks": {},
        "timing_manifest": [],
        "mixed_audio_files": [],
        "full_audio_path": "",
        "error": "",
    }

    return app.invoke(initial_state)
