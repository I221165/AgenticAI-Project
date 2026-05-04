"""
Unit tests for Phase 4 — API layer utilities and version history.

Tests focus on the pure-Python helpers that back the API endpoints:
  - JSON file loading helper (_load_json logic)
  - Message file helpers (_msg_file_append / _msg_file_load)
  - Version history: save_version, list_versions, restore_version, get_version_meta

The FastAPI endpoint tests are covered by integration tests; these unit tests
verify the business logic that the endpoints delegate to.
"""
import json
import os
import pytest


# ── _load_json equivalent (inline, no FastAPI import) ───────────────────────

def _load_json(path):
    try:
        if path and os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def test_load_json_returns_none_for_missing_file():
    assert _load_json("/nonexistent/path/that/does/not/exist.json") is None


def test_load_json_returns_dict_for_valid_file(tmp_path):
    p = tmp_path / "test.json"
    p.write_text('{"key": "value"}')
    assert _load_json(str(p)) == {"key": "value"}


def test_load_json_returns_none_for_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json}")
    assert _load_json(str(p)) is None


def test_load_json_returns_none_for_empty_path():
    assert _load_json("") is None


def test_load_json_returns_none_for_none_path():
    assert _load_json(None) is None


# ── Message file helpers ─────────────────────────────────────────────────────

def _msg_file_path(base, run_id):
    return os.path.join(base, run_id, "messages.json")


def _msg_file_load(base, run_id):
    p = _msg_file_path(base, run_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return []


def _msg_file_append(base, run_id, msg):
    msgs = _msg_file_load(base, run_id)
    msgs.append(msg)
    os.makedirs(os.path.join(base, run_id), exist_ok=True)
    with open(_msg_file_path(base, run_id), "w") as f:
        json.dump(msgs, f, indent=2)


def test_msg_file_load_returns_empty_for_missing(tmp_path):
    assert _msg_file_load(str(tmp_path), "run_nonexistent") == []


def test_msg_file_append_creates_file(tmp_path):
    _msg_file_append(str(tmp_path), "run_001",
                     {"role": "user", "text": "Hello", "ts": "2026-01-01"})
    p = tmp_path / "run_001" / "messages.json"
    assert p.exists()


def test_msg_file_append_accumulates_messages(tmp_path):
    base = str(tmp_path)
    _msg_file_append(base, "run_002", {"role": "user", "text": "Edit scene 1", "ts": "t1"})
    _msg_file_append(base, "run_002", {"role": "ai",   "text": "Done",          "ts": "t2"})
    msgs = _msg_file_load(base, "run_002")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "ai"


def test_msg_file_append_preserves_order(tmp_path):
    base = str(tmp_path)
    for i in range(5):
        _msg_file_append(base, "run_003", {"role": "user", "text": f"msg {i}", "ts": f"t{i}"})
    msgs = _msg_file_load(base, "run_003")
    assert [m["text"] for m in msgs] == [f"msg {i}" for i in range(5)]


# ── Version history (state_manager/history.py) ──────────────────────────────

from state_manager.history import (
    save_version,
    list_versions,
    restore_version,
    get_version_meta,
)


def _make_run(tmp_path, story=None, characters=None):
    """Set up a minimal run directory with JSON artifacts."""
    rdir = str(tmp_path)
    if story is None:
        story = {"title": "Test Story", "premise": "Once upon a time"}
    if characters is None:
        characters = {"characters": [{"name": "Hero"}]}
    with open(os.path.join(rdir, "story.json"), "w") as f:
        json.dump(story, f)
    with open(os.path.join(rdir, "characters.json"), "w") as f:
        json.dump(characters, f)
    return rdir


def test_save_version_returns_version_number(tmp_path):
    rdir = _make_run(tmp_path)
    v = save_version(rdir, label="initial")
    assert v == 1


def test_save_version_increments(tmp_path):
    rdir = _make_run(tmp_path)
    v1 = save_version(rdir)
    v2 = save_version(rdir)
    assert v2 == v1 + 1


def test_save_version_creates_version_json(tmp_path):
    rdir = _make_run(tmp_path)
    v = save_version(rdir, label="my label")
    meta_path = os.path.join(rdir, "versions", f"v{v}", "version.json")
    assert os.path.exists(meta_path)
    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["version"] == v
    assert meta["label"] == "my label"
    assert "saved_at" in meta


def test_save_version_copies_json_artifacts(tmp_path):
    rdir = _make_run(tmp_path)
    v = save_version(rdir)
    snapshot_dir = os.path.join(rdir, "versions", f"v{v}")
    assert os.path.exists(os.path.join(snapshot_dir, "story.json"))
    assert os.path.exists(os.path.join(snapshot_dir, "characters.json"))


def test_save_version_snapshots_images(tmp_path):
    rdir = _make_run(tmp_path)
    img_dir = os.path.join(rdir, "images")
    os.makedirs(img_dir, exist_ok=True)
    open(os.path.join(img_dir, "scene_1_wide.png"), "w").close()
    open(os.path.join(img_dir, "scene_2_mid.png"),  "w").close()

    v = save_version(rdir)
    snap_img = os.path.join(rdir, "versions", f"v{v}", "images")
    assert os.path.exists(os.path.join(snap_img, "scene_1_wide.png"))
    assert os.path.exists(os.path.join(snap_img, "scene_2_mid.png"))


def test_list_versions_returns_sorted_desc(tmp_path):
    rdir = _make_run(tmp_path)
    save_version(rdir)
    save_version(rdir)
    save_version(rdir)
    versions = list_versions(rdir)
    nums = [v["version"] for v in versions]
    assert nums == sorted(nums, reverse=True)


def test_list_versions_empty_when_no_versions(tmp_path):
    rdir = str(tmp_path)
    os.makedirs(rdir, exist_ok=True)
    assert list_versions(rdir) == []


def test_get_version_meta_returns_correct_version(tmp_path):
    rdir = _make_run(tmp_path)
    v = save_version(rdir, label="tagged release")
    meta = get_version_meta(rdir, v)
    assert meta is not None
    assert meta["version"] == v
    assert meta["label"] == "tagged release"


def test_get_version_meta_returns_none_for_missing(tmp_path):
    rdir = str(tmp_path)
    os.makedirs(rdir, exist_ok=True)
    assert get_version_meta(rdir, 999) is None


def test_restore_version_overwrites_current(tmp_path):
    rdir = _make_run(tmp_path, story={"title": "Original", "premise": "v1 premise"})
    v = save_version(rdir)

    # Mutate story.json after snapshot
    with open(os.path.join(rdir, "story.json"), "w") as f:
        json.dump({"title": "Mutated", "premise": "changed"}, f)

    restore_version(rdir, v)

    with open(os.path.join(rdir, "story.json")) as f:
        restored = json.load(f)
    assert restored["title"] == "Original"


def test_restore_version_raises_for_missing_version(tmp_path):
    rdir = str(tmp_path)
    os.makedirs(rdir, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        restore_version(rdir, 999)
