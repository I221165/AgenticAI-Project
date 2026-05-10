import os
import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from mcp.tool_registry import ToolRegistry

try:
    from shared.utils.progress import report as _report
except ImportError:
    def _report(*a, **kw): pass


_MIN_FRAME_DURATION = 2.0          # minimum seconds per Ken Burns clip
_FRAME_TYPES = ["wide", "mid", "close"]
_INTRA_TRANSITION_DUR = 0.4        # must match compositor_tool._INTRA_TRANSITION_DUR

# Per-frame camera work: wide uses the scene's assigned motion,
# mid is static for contrast, close always zooms in for intimacy.
_FRAME_CAMERA_WORK = {
    "wide":  lambda cw: cw,
    "mid":   lambda _: "static",
    "close": lambda _: "zoom_in",
}


class VideoState(TypedDict):
    handoff_json: Dict[str, Any]           # phase3_video_handoff.json
    timing_manifest: List[Dict[str, Any]]  # entries from timing_manifest.json
    run_dir: str
    fps: int
    scene_image_groups: Dict[str, List[str]]  # scene_id -> [wide, mid, close] image paths
    scene_clip_groups: Dict[str, List[str]]   # scene_id -> [wide, mid, close] clip paths
    scene_order: List[str]                    # ordered scene IDs
    silent_video_path: str
    audio_video_path: str
    final_video_path: str
    error: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_scene_durations(
    timing_manifest: List[Dict[str, Any]],
    scenes_map: Dict[str, Any],
) -> Dict[str, float]:
    """
    Derives actual per-scene video duration from the timing manifest.
    Uses the dialogue span (max end_ms - min start_ms) + 500ms trailing pause.
    Falls back to duration_estimate_sec when a scene has no dialogue entries.
    """
    from collections import defaultdict
    scene_entries: Dict[str, List] = defaultdict(list)
    for entry in timing_manifest:
        sid = entry.get("scene_id")
        if sid:
            scene_entries[sid].append(entry)

    result = {}
    for sid, scene in scenes_map.items():
        entries = scene_entries.get(sid, [])
        if entries:
            span_ms = max(e["end_ms"] for e in entries) - min(e["start_ms"] for e in entries)
            result[sid] = max((span_ms + 500) / 1000.0, _MIN_FRAME_DURATION * 3)
        else:
            result[sid] = max(float(scene.get("duration_estimate_sec", 6)), _MIN_FRAME_DURATION * 3)
    return result


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def generate_scene_images(state: VideoState) -> Dict[str, Any]:
    """Node: Generate wide/mid/close keyframe images for every scene via Pollinations.ai."""
    if state.get("error"):
        return {}

    img_tool = ToolRegistry.get_tool("image_generator")
    run_dir = state["run_dir"]
    scenes = state["handoff_json"].get("scenes", [])
    image_dir = os.path.join(run_dir, "images")

    # Style is stored in the handoff so every image reflects the chosen art direction
    style = state["handoff_json"].get("style", "2D animated")

    scene_image_groups: Dict[str, List[str]] = {}
    scene_order: List[str] = []

    total_images = len(scenes) * len(_FRAME_TYPES)
    generated = 0
    _report(3, 5, f"Generating {total_images} images for {len(scenes)} scenes…")

    for scene in scenes:
        scene_id = scene["scene_id"]
        # visual_description already contains the style prefix from build_visual_prompt,
        # but we append the style keyword again as a reinforcement tag for Pollinations.
        prompt = scene.get("visual_description", "")
        if style.lower() not in prompt.lower():
            prompt = f"{prompt}, {style} style"
        frame_paths: List[str] = []

        for frame_type in _FRAME_TYPES:
            generated += 1
            img_prog = 5 + int(48 * generated / max(total_images, 1))
            _report(3, img_prog, f"Image {generated}/{total_images}: {scene_id} [{frame_type}]")
            try:
                path = img_tool.execute(
                    prompt=prompt,
                    scene_id=scene_id,
                    frame_type=frame_type,
                    output_dir=image_dir,
                )
                frame_paths.append(path)
            except Exception as e:
                print(f"[VideoAgent] Image gen failed {scene_id}/{frame_type}: {e}")

        if frame_paths:
            scene_image_groups[scene_id] = frame_paths
            scene_order.append(scene_id)
        else:
            print(f"[VideoAgent] No images for {scene_id}, skipping scene.")

    return {"scene_image_groups": scene_image_groups, "scene_order": scene_order}


def animate_frames(state: VideoState) -> Dict[str, Any]:
    """
    Node: Animate each scene's keyframe images into video clips.

    Strategy per scene:
      1. Try Wan I2V (DashScope) on the wide/first image — produces a real
         AI-animated clip with natural camera motion.
      2. If Wan fails or is not configured → Ken Burns FFmpeg on all 3
         frames (wide/mid/close), same as before.

    Downstream nodes (compose_scenes, sync_audio, subtitles) are unchanged.
    """
    if state.get("error"):
        return {}

    ffmpeg_tool  = ToolRegistry.get_tool("ffmpeg_ken_burns")
    wan_tool     = ToolRegistry.get_tool("wan_video")
    use_wan      = bool(os.getenv("DASHSCOPE_API_KEY", "").strip())

    run_dir = state["run_dir"]
    fps = state.get("fps", 24)
    scenes_map = {s["scene_id"]: s for s in state["handoff_json"].get("scenes", [])}
    clips_dir = os.path.join(run_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    scene_audio_durations = _compute_scene_durations(
        state.get("timing_manifest", []),
        scenes_map,
    )

    scene_clip_groups: Dict[str, List[str]] = {}
    all_image_groups = state.get("scene_image_groups", {})
    total_scenes = len(all_image_groups)
    done = 0
    _report(3, 55, f"Animating {total_scenes} scenes {'(Wan I2V + Ken Burns fallback)' if use_wan else '(Ken Burns)'}…")

    for scene_id, image_paths in all_image_groups.items():
        if not image_paths:
            continue

        scene = scenes_map.get(scene_id, {})
        n = len(image_paths)
        target_duration = scene_audio_durations.get(
            scene_id,
            max(float(scene.get("duration_estimate_sec", 6)), _MIN_FRAME_DURATION * n),
        )
        camera_work = scene.get("camera_work", "zoom_in")
        done += 1
        anim_prog = 55 + int(22 * done / max(total_scenes, 1))

        # ── Try Wan I2V on the wide (first) image ───────────────────────────
        if use_wan:
            wide_img = image_paths[0]
            wan_clip = os.path.join(clips_dir, f"{scene_id}_wan.mp4")
            wan_prompt = _build_wan_prompt(scene)
            _report(3, anim_prog, f"Wan I2V {done}/{total_scenes}: {scene_id}…")
            try:
                path = wan_tool.execute(
                    image_path=wide_img,
                    output_path=wan_clip,
                    prompt=wan_prompt,
                    duration=target_duration,
                    resolution="720P",
                    camera_work=camera_work,
                    fps=fps,
                    force_fallback=False,
                )
                scene_clip_groups[scene_id] = [path]
                print(f"[VideoAgent] Wan I2V OK: {scene_id}")
                continue
            except Exception as e:
                print(f"[VideoAgent] Wan I2V failed for {scene_id}: {e} — falling back to Ken Burns")

        # ── Ken Burns fallback: wide/mid/close ───────────────────────────────
        frame_duration = max(
            (target_duration + (n - 1) * _INTRA_TRANSITION_DUR) / n,
            _MIN_FRAME_DURATION,
        )
        clip_paths: List[str] = []
        for i, img_path in enumerate(image_paths):
            frame_type = _FRAME_TYPES[i] if i < len(_FRAME_TYPES) else "wide"
            cam = _FRAME_CAMERA_WORK[frame_type](camera_work)
            out_clip = os.path.join(clips_dir, f"{scene_id}_{frame_type}.mp4")
            _report(3, anim_prog, f"Ken Burns {done}/{total_scenes}: {scene_id} [{frame_type}]")
            try:
                path = ffmpeg_tool.execute(
                    image_path=img_path,
                    output_path=out_clip,
                    duration=frame_duration,
                    camera_work=cam,
                    fps=fps,
                )
                clip_paths.append(path)
            except Exception as e:
                print(f"[VideoAgent] Ken Burns failed {scene_id}/{frame_type}: {e}")

        if clip_paths:
            scene_clip_groups[scene_id] = clip_paths

    return {"scene_clip_groups": scene_clip_groups}


def _build_wan_prompt(scene: Dict[str, Any]) -> str:
    """Build a motion prompt for Wan I2V from the scene's handoff data."""
    desc    = scene.get("visual_description", "") or scene.get("description", "")
    mood    = scene.get("mood", "")
    cam     = scene.get("camera_work", "zoom_in")
    cam_map = {
        "zoom_in":   "slow cinematic push-in toward the subject",
        "zoom_out":  "slow cinematic pull-back revealing the environment",
        "pan_right": "smooth horizontal pan right across the scene",
        "pan_left":  "smooth horizontal pan left across the scene",
        "static":    "locked-off static camera, subtle atmospheric movement",
    }
    cam_desc = cam_map.get(cam, "cinematic camera movement")
    return (
        f"{desc}. {cam_desc}. "
        f"Mood: {mood}. Natural motion, atmospheric lighting, film grain, "
        f"24fps, cinematic depth of field, professional cinematography."
    )[:800]


def compose_scenes(state: VideoState) -> Dict[str, Any]:
    """Node: Join all per-scene clips into a single silent video with xfade transitions."""
    if state.get("error"):
        return {}

    compositor = ToolRegistry.get_tool("video_compositor")
    run_dir = state["run_dir"]
    scene_order = state.get("scene_order", [])
    scenes_map = {s["scene_id"]: s for s in state["handoff_json"].get("scenes", [])}
    scene_clip_groups = state.get("scene_clip_groups", {})

    ordered_clip_groups = [
        scene_clip_groups[sid]
        for sid in scene_order
        if sid in scene_clip_groups
    ]

    if not ordered_clip_groups:
        return {"error": "No scene clips available for composition."}

    # n-1 transitions for n scenes
    transitions = [
        scenes_map[sid].get("transition_to_next", "crossfade")
        for sid in scene_order[:-1]
        if sid in scenes_map
    ]

    video_dir = os.path.join(run_dir, "video")
    os.makedirs(video_dir, exist_ok=True)
    silent_path = os.path.join(video_dir, "silent_video.mp4")
    _report(3, 79, f"Compositing {len(ordered_clip_groups)} scenes with xfade transitions…")

    try:
        compositor.execute(
            scene_clip_groups=ordered_clip_groups,
            scene_transitions=transitions,
            output_path=silent_path,
            fps=state.get("fps", 24),
        )
        return {"silent_video_path": silent_path}
    except Exception as e:
        return {"error": f"Composition failed: {e}"}


def sync_audio(state: VideoState) -> Dict[str, Any]:
    """Node: Overlay the full mixed audio track onto the silent video."""
    if state.get("error"):
        return {}

    from mcp.tools.video_tools.compositor_tool import overlay_audio

    run_dir = state["run_dir"]
    silent_path = state.get("silent_video_path", "")
    full_audio_path = state["handoff_json"].get("full_audio_path", "")

    if not silent_path or not os.path.exists(silent_path):
        return {"error": "Silent video not found for audio sync."}

    audio_video_path = os.path.join(run_dir, "video", "audio_video.mp4")
    _report(3, 86, "Syncing audio track to video…")

    try:
        result = overlay_audio(silent_path, full_audio_path, audio_video_path)
        return {"audio_video_path": result}
    except Exception as e:
        return {"error": f"Audio sync failed: {e}"}


def add_subtitles(state: VideoState) -> Dict[str, Any]:
    """Node: Generate SRT from timing manifest and burn subtitles into the video."""
    if state.get("error"):
        return {}

    from mcp.tools.video_tools.subtitle_tool import SubtitleTool

    run_dir = state["run_dir"]
    timing_manifest = state.get("timing_manifest", [])
    source_video = state.get("audio_video_path") or state.get("silent_video_path", "")

    if not source_video or not os.path.exists(source_video):
        return {"error": "No video found for subtitle burn-in."}

    subtitles_dir = os.path.join(run_dir, "subtitles")
    _report(3, 92, f"Generating SRT and burning subtitles ({len(timing_manifest)} lines)…")
    srt_tool = SubtitleTool()
    srt_path = srt_tool.execute(timing_entries=timing_manifest, output_dir=subtitles_dir)

    final_path = os.path.join(run_dir, "video", "final_video.mp4")
    result = SubtitleTool.burn_subtitles(source_video, srt_path, final_path)
    return {"final_video_path": result}


def serialize_node(state: VideoState) -> Dict[str, Any]:
    """Node: Write phase3_output.json with all artifact paths."""
    if state.get("error"):
        print(f"[VideoAgent] Pipeline ended with error: {state['error']}")
        return {}

    run_dir = state["run_dir"]
    output = {
        "run_dir": run_dir,
        "silent_video_path": state.get("silent_video_path", ""),
        "audio_video_path": state.get("audio_video_path", ""),
        "final_video_path": state.get("final_video_path", ""),
        "scenes_composed": len(state.get("scene_order", [])),
        "images_generated": sum(len(v) for v in state.get("scene_image_groups", {}).values()),
    }

    manifest_path = os.path.join(run_dir, "phase3_output.json")
    with open(manifest_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[VideoAgent] Phase 3 complete!")
    print(f"  Final video : {output['final_video_path']}")
    print(f"  Scenes      : {output['scenes_composed']}")
    print(f"  Images      : {output['images_generated']}")
    return {}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_phase3_graph() -> StateGraph:
    workflow = StateGraph(VideoState)

    workflow.add_node("generate_scene_images", generate_scene_images)
    workflow.add_node("animate_frames",         animate_frames)
    workflow.add_node("compose_scenes",         compose_scenes)
    workflow.add_node("sync_audio",             sync_audio)
    workflow.add_node("add_subtitles",          add_subtitles)
    workflow.add_node("serialize_node",         serialize_node)

    workflow.set_entry_point("generate_scene_images")
    workflow.add_edge("generate_scene_images", "animate_frames")
    workflow.add_edge("animate_frames",        "compose_scenes")
    workflow.add_edge("compose_scenes",        "sync_audio")
    workflow.add_edge("sync_audio",            "add_subtitles")
    workflow.add_edge("add_subtitles",         "serialize_node")
    workflow.add_edge("serialize_node",        END)

    return workflow.compile()


def run_phase3(
    handoff_json: Dict[str, Any],
    timing_entries: List[Dict[str, Any]],
    run_dir: str,
    fps: int = 24,
) -> Dict[str, Any]:
    """Run Phase 3 video generation pipeline."""
    ToolRegistry.register_video_tools()
    app = build_phase3_graph()
    os.makedirs(os.path.join(run_dir, "video"), exist_ok=True)

    initial_state: VideoState = {
        "handoff_json": handoff_json,
        "timing_manifest": timing_entries,
        "run_dir": run_dir,
        "fps": fps,
        "scene_image_groups": {},
        "scene_clip_groups": {},
        "scene_order": [],
        "silent_video_path": "",
        "audio_video_path": "",
        "final_video_path": "",
        "error": "",
    }

    return app.invoke(initial_state)
