import pytest
from agents.story_agent.story_node import validate_story_arc, estimate_duration
from agents.story_agent.character_node import check_consistency
from agents.story_agent.script_node import (
    analyze_emotions,
    build_visual_prompt,
    validate_duration,
    normalize_scene_ids,
    assign_transitions,
)


def test_validate_story_arc_adds_missing_climax():
    story = {"narrative_arc": "Intro: Starting out. Resolution: The end."}
    validated = validate_story_arc(story)
    assert "climax" in validated["narrative_arc"].lower()


def test_validate_story_arc_passes_complete_arc():
    story = {"narrative_arc": "Intro: Setup. Climax: Battle. Resolution: Peace."}
    validated = validate_story_arc(story)
    assert "intro" in validated["narrative_arc"].lower()
    assert "climax" in validated["narrative_arc"].lower()
    assert "resolution" in validated["narrative_arc"].lower()


def test_estimate_duration_minimum():
    story = {"narrative_arc": "Short arc."}
    validated = estimate_duration(story)
    assert validated["estimated_duration_sec"] >= 30


def test_check_consistency_fills_missing_fields():
    roster = {"characters": [{"name": "John"}]}
    validated = check_consistency(roster, {})
    char = validated["characters"][0]
    assert char["role"] == "Supporting"
    assert "Neutral tone" in char["voice_personality"]
    assert "standard looking" in char["visual_description"]


def test_check_consistency_preserves_existing_fields():
    roster = {"characters": [{"name": "Maya", "role": "Protagonist", "voice_personality": "fierce", "visual_description": "tall warrior"}]}
    validated = check_consistency(roster, {})
    char = validated["characters"][0]
    assert char["role"] == "Protagonist"
    assert char["voice_personality"] == "fierce"


def test_analyze_emotions_angry():
    script = {"scenes": [{"dialogue_lines": [{"text": "How dare you!", "emotion": ""}]}]}
    result = analyze_emotions(script)
    assert result["scenes"][0]["dialogue_lines"][0]["emotion"] == "angry"


def test_analyze_emotions_confused():
    script = {"scenes": [{"dialogue_lines": [{"text": "What is happening?", "emotion": None}]}]}
    result = analyze_emotions(script)
    assert result["scenes"][0]["dialogue_lines"][0]["emotion"] == "confused"


def test_analyze_emotions_happy():
    script = {"scenes": [{"dialogue_lines": [{"text": "I am so happy today.", "emotion": ""}]}]}
    result = analyze_emotions(script)
    assert result["scenes"][0]["dialogue_lines"][0]["emotion"] == "happy"


def test_analyze_emotions_preserves_existing():
    script = {"scenes": [{"dialogue_lines": [{"text": "I am so happy today.", "emotion": "sad"}]}]}
    result = analyze_emotions(script)
    assert result["scenes"][0]["dialogue_lines"][0]["emotion"] == "sad"


def test_build_visual_prompt_enriches_description():
    script = {"scenes": [{"setting": "A dark forest", "tone": "mysterious", "dialogue_lines": []}]}
    result = build_visual_prompt(script)
    desc = result["scenes"][0]["visual_description"].lower()
    assert "2d animated" in desc
    assert "dark forest" in desc
    assert "cinematic" in desc


def test_build_visual_prompt_includes_character_description():
    roster = {"characters": [{"name": "Elena", "visual_description": "young woman with red hair"}]}
    script = {
        "scenes": [{
            "setting": "A castle hall",
            "tone": "tense",
            "dialogue_lines": [{"character_name": "Elena", "text": "Run!", "emotion": "scared"}],
        }]
    }
    result = build_visual_prompt(script, roster)
    desc = result["scenes"][0]["visual_description"]
    assert "Elena" in desc
    assert "red hair" in desc


def test_build_visual_prompt_assigns_camera_work():
    script = {"scenes": [
        {"setting": "forest", "tone": "tense", "dialogue_lines": []},
        {"setting": "meadow", "tone": "peaceful", "dialogue_lines": []},
    ]}
    result = build_visual_prompt(script)
    assert result["scenes"][0]["camera_work"] == "zoom_in"
    assert result["scenes"][1]["camera_work"] == "pan_right"


def test_assign_transitions_last_scene_is_fade():
    script = {"scenes": [
        {"tone": "tense"},
        {"tone": "peaceful"},
    ]}
    result = assign_transitions(script)
    assert result["scenes"][-1]["transition_to_next"] == "fade"


def test_assign_transitions_crossfade_default():
    script = {"scenes": [
        {"tone": "happy"},
        {"tone": "happy"},
        {"tone": "happy"},
    ]}
    result = assign_transitions(script)
    assert result["scenes"][0]["transition_to_next"] == "crossfade"


def test_validate_duration_minimum():
    script = {"scenes": [{"dialogue_lines": [{"text": "word " * 5}]}]}
    result = validate_duration(script)
    assert result["scenes"][0]["duration_estimate_sec"] == 5


def test_validate_duration_scales_with_words():
    script = {"scenes": [{"dialogue_lines": [{"text": "word " * 25}]}]}
    result = validate_duration(script)
    assert result["scenes"][0]["duration_estimate_sec"] == 10


def test_normalize_scene_ids():
    script = {"scenes": [{"scene_id": "101"}, {"scene_id": "abc"}, {"scene_id": "scene_5"}]}
    result = normalize_scene_ids(script)
    assert result["scenes"][0]["scene_id"] == "scene_1"
    assert result["scenes"][1]["scene_id"] == "scene_2"
    assert result["scenes"][2]["scene_id"] == "scene_3"
