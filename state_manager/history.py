"""
Version history: copies key JSON artifacts into run_dir/versions/vN/
before each edit so edits are fully reversible.

Each version snapshot also records the path of the video file that existed
at save time, so callers can serve a per-version video for before/after comparison.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


_VERSIONED_FILES = [
    "story.json",
    "characters.json",
    "script.json",
    "timing_manifest.json",
    "phase2_audio_handoff.json",
    "phase3_video_handoff.json",
]


def _versions_dir(run_dir: str) -> str:
    d = os.path.join(run_dir, "versions")
    os.makedirs(d, exist_ok=True)
    return d


def _next_version(run_dir: str) -> int:
    vdir = _versions_dir(run_dir)
    existing = [
        int(d[1:]) for d in os.listdir(vdir)
        if d.startswith("v") and d[1:].isdigit()
    ]
    return (max(existing) + 1) if existing else 1


def _find_mp4(run_dir: str) -> Optional[str]:
    """Return the most recently modified MP4 inside run_dir, or None."""
    candidates = [
        os.path.join(run_dir, "video", "final_video.mp4"),
        os.path.join(run_dir, "video", "audio_video.mp4"),
        os.path.join(run_dir, "video", "silent_video.mp4"),
        os.path.join(run_dir, "final_video.mp4"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Walk and pick the newest mp4
    best = None
    best_mtime = 0
    for root, _, files in os.walk(run_dir):
        if "versions" in root:
            continue  # don't scan snapshots
        for f in files:
            if f.endswith(".mp4"):
                p = os.path.join(root, f)
                mtime = os.path.getmtime(p)
                if mtime > best_mtime:
                    best_mtime = mtime
                    best = p
    return best


def save_version(run_dir: str, label: str = "") -> int:
    """
    Copy current JSON state + images into versions/vN/.
    Also records the current video path for before/after comparison.
    Returns version number.
    """
    import glob as _glob

    v = _next_version(run_dir)
    dest = os.path.join(_versions_dir(run_dir), f"v{v}")
    os.makedirs(dest, exist_ok=True)

    # Snapshot JSON config files
    for fname in _VERSIONED_FILES:
        src = os.path.join(run_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, fname))

    # Snapshot images (flat files: images/scene_1_wide.png …)
    img_src_dir = os.path.join(run_dir, "images")
    img_dst_dir = os.path.join(dest, "images")
    if os.path.isdir(img_src_dir):
        os.makedirs(img_dst_dir, exist_ok=True)
        for img_path in _glob.glob(os.path.join(img_src_dir, "*.png")) + \
                        _glob.glob(os.path.join(img_src_dir, "*.jpg")):
            shutil.copy2(img_path, os.path.join(img_dst_dir, os.path.basename(img_path)))

    meta = {
        "version":    v,
        "label":      label or f"Auto-save v{v}",
        "saved_at":   datetime.now(timezone.utc).isoformat(),
        "video_path": _find_mp4(run_dir) or "",
    }
    with open(os.path.join(dest, "version.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return v


def list_versions(run_dir: str) -> List[Dict[str, Any]]:
    """Return all saved versions sorted descending by number."""
    vdir = _versions_dir(run_dir)
    versions = []
    for d in os.listdir(vdir):
        if not (d.startswith("v") and d[1:].isdigit()):
            continue
        meta_path = os.path.join(vdir, d, "version.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        else:
            meta = {"version": int(d[1:]), "label": d, "saved_at": "", "video_path": ""}
        versions.append(meta)
    return sorted(versions, key=lambda x: x["version"], reverse=True)


def get_version_meta(run_dir: str, version: int) -> Optional[Dict[str, Any]]:
    """Return metadata for a specific version, or None if not found."""
    meta_path = os.path.join(_versions_dir(run_dir), f"v{version}", "version.json")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        return json.load(f)


def restore_version(run_dir: str, version: int):
    """Copy files from versions/vN/ back into run_dir (overwriting current)."""
    src_dir = os.path.join(_versions_dir(run_dir), f"v{version}")
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"Version v{version} not found in {run_dir}")

    for fname in _VERSIONED_FILES:
        src = os.path.join(src_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(run_dir, fname))
