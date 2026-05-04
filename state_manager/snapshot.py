"""
Snapshot: persist a point-in-time copy of a run's state JSON files.
Each snapshot is stored at run_dir/versions/vN/ and records which
version number it corresponds to.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any


_STATE_FILES = [
    "story.json",
    "characters.json",
    "script.json",
    "timing_manifest.json",
    "phase2_audio_handoff.json",
    "phase3_video_handoff.json",
    "summary.json",
]


def save_snapshot(run_id: str, run_dir: str) -> str:
    """Write a summary.json with run metadata at the end of a pipeline run."""
    summary_path = os.path.join(run_dir, "summary.json")
    if not os.path.exists(summary_path):
        summary = {
            "run_id": run_id,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "done",
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
    return summary_path
