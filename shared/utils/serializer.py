import os
import json
from datetime import datetime
from typing import Dict, Any

def generate_run_id() -> str:
    """Creates a unique run ID based on the current timestamp."""
    return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def get_run_dir(run_id: str = None, base_dir: str = "run_outputs") -> str:
    """Returns the path for a specific run. Creates a new run if no run_id is given."""
    if not run_id:
        run_id = generate_run_id()
    run_dir = os.path.join(base_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

def serialize_phase1_outputs(state: Dict[str, Any], output_dir: str = "run_outputs") -> Dict[str, str]:
    """
    Takes the multi-agent state from Phase 1 and serializes it into the exact files
    required by the PDF specifications.
    Returns a dictionary of the generated file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    story = state.get("story_output", {})
    characters = state.get("character_roster", {})
    script = state.get("script_output", {})
    
    paths = {}
    
    # 1. story.json
    paths["story.json"] = os.path.join(output_dir, "story.json")
    with open(paths["story.json"], "w") as f:
        json.dump(story, f, indent=2)
        
    # 2. characters.json
    paths["characters.json"] = os.path.join(output_dir, "characters.json")
    with open(paths["characters.json"], "w") as f:
        json.dump(characters, f, indent=2)
        
    # 3. script.json
    paths["script.json"] = os.path.join(output_dir, "script.json")
    with open(paths["script.json"], "w") as f:
        json.dump(script, f, indent=2)
        
    # 4. phase2_audio_handoff.json
    # Consumed by Phase 2. Contains characters (for voice configs) and scenes (for TTS text/timing)
    handoff_audio = {
        "language": state.get("language", "English"),
        "voice_configs": characters.get("characters", []),
        "segments": script.get("scenes", [])
    }
    paths["phase2_audio_handoff.json"] = os.path.join(output_dir, "phase2_audio_handoff.json")
    with open(paths["phase2_audio_handoff.json"], "w") as f:
        json.dump(handoff_audio, f, indent=2)
        
    # 5. phase3_video_handoff.json
    # Consumed by Phase 3. Contains enriched scenes (visual prompts, camera work, transitions)
    # and characters (for consistent image generation across scenes).
    handoff_video = {
        "style": state.get("style", "2D animated"),
        "characters": characters.get("characters", []),
        "scenes": [
            {
                "scene_id": s.get("scene_id"),
                "setting": s.get("setting"),
                "visual_description": s.get("visual_description"),
                "tone": s.get("tone"),
                "duration_estimate_sec": s.get("duration_estimate_sec"),
                "camera_work": s.get("camera_work", "pan_right"),
                "transition_to_next": s.get("transition_to_next", "crossfade"),
                "dialogue_lines": s.get("dialogue_lines", []),
            }
            for s in script.get("scenes", [])
        ],
    }
    paths["phase3_video_handoff.json"] = os.path.join(output_dir, "phase3_video_handoff.json")
    with open(paths["phase3_video_handoff.json"], "w") as f:
        json.dump(handoff_video, f, indent=2)
        
    # 6. summary.json
    summary = {
        "run_status": "Success" if not state.get("error") else "Failed",
        "errors": state.get("error", None),
        "artifact_paths": paths
    }
    paths["summary.json"] = os.path.join(output_dir, "summary.json")
    with open(paths["summary.json"], "w") as f:
        json.dump(summary, f, indent=2)
        
    return paths
