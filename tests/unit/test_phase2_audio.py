import pytest
import os
import json
from agents.audio_agent.agent import assign_voices, serialize_node


def test_assign_voices_maps_deep_male_to_drew():
    handoff = {
        "voice_configs": [
            {"name": "Sarah", "voice_personality": "deep male voice"}
        ]
    }
    state = {"handoff_json": handoff, "voice_map": {}, "error": ""}
    result = assign_voices(state)
    assert "Sarah" in result["voice_map"]
    assert result["voice_map"]["Sarah"] == "29vD33N1CtxCmqQRPOHJ"  # Drew


def test_assign_voices_maps_warm_female_to_rachel():
    handoff = {
        "voice_configs": [
            {"name": "Luna", "voice_personality": "warm gentle female voice"}
        ]
    }
    state = {"handoff_json": handoff, "voice_map": {}, "error": ""}
    result = assign_voices(state)
    assert "Luna" in result["voice_map"]
    assert result["voice_map"]["Luna"] == "21m00Tcm4TlvDq8ikWAM"  # Rachel


def test_assign_voices_skips_on_error():
    state = {"handoff_json": {}, "voice_map": {}, "error": "previous failure"}
    result = assign_voices(state)
    assert result == {}


def test_serialize_node_writes_manifest(tmp_path):
    run_dir = str(tmp_path)
    state = {
        "error": "",
        "run_dir": run_dir,
        "timing_manifest": [
            {"scene_id": "scene_1", "audio_file": "test.wav", "start_ms": 0, "end_ms": 1000}
        ],
        "bgm_tracks": {}
    }

    serialize_node(state)

    manifest_path = os.path.join(run_dir, "timing_manifest.json")
    assert os.path.exists(manifest_path)

    with open(manifest_path) as f:
        data = json.load(f)

    assert data["entries"][0]["scene_id"] == "scene_1"
    assert data["entries"][0]["start_ms"] == 0
    assert data["entries"][0]["end_ms"] == 1000


def test_serialize_node_skips_on_error(tmp_path):
    run_dir = str(tmp_path)
    state = {
        "error": "something failed",
        "run_dir": run_dir,
        "timing_manifest": [],
        "bgm_tracks": {}
    }
    serialize_node(state)
    assert not os.path.exists(os.path.join(run_dir, "timing_manifest.json"))


def test_serialize_node_includes_bgm_tracks(tmp_path):
    run_dir = str(tmp_path)
    state = {
        "error": "",
        "run_dir": run_dir,
        "timing_manifest": [],
        "bgm_tracks": {"scene_1": "assets/bgm/tense_1.mp3"}
    }
    serialize_node(state)
    with open(os.path.join(run_dir, "timing_manifest.json")) as f:
        data = json.load(f)
    assert data["bgm_tracks"]["scene_1"] == "assets/bgm/tense_1.mp3"
