"""
Unit tests — Edit Agent: Intent Classifier (Phase 5)

Tests all 12 supported intent types using the rule-based fallback classifier
so that tests run without a live LLM / network connection.
"""

import sys
import os

# Ensure project root is importable
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import pytest
from agents.edit_agent.intent_classifier import _rule_classify, classify_intent, SUPPORTED_INTENTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify(instruction: str) -> str:
    """Run rule-based classifier and return the intent type."""
    return _rule_classify(instruction)["type"]


def _target(instruction: str) -> str:
    return _rule_classify(instruction)["target"]


# ---------------------------------------------------------------------------
# 1. voice_change
# ---------------------------------------------------------------------------

class TestVoiceChange:
    def test_make_voice_deeper(self):
        assert _classify("Make Ethan's voice deeper") == "voice_change"

    def test_change_tone(self):
        assert _classify("Change the tone of Olivia's speech") == "voice_change"

    def test_pitch(self):
        assert _classify("Lower the pitch for Mark") == "voice_change"

    def test_speak_keyword(self):
        assert _classify("Change how Ethan speaks in scene 3") == "voice_change"


# ---------------------------------------------------------------------------
# 2. scene_regen
# ---------------------------------------------------------------------------

class TestSceneRegen:
    def test_redo_scene(self):
        assert _classify("Redo scene 3") == "scene_regen"

    def test_regenerate(self):
        assert _classify("Regenerate scene 2 visuals") == "scene_regen"

    def test_scene_target_extracted(self):
        assert _target("Redo scene 4 with more detail") == "scene_4"


# ---------------------------------------------------------------------------
# 3. style_change
# ---------------------------------------------------------------------------

class TestStyleChange:
    def test_anime_style(self):
        assert _classify("Make it look like anime") == "style_change"

    def test_watercolor(self):
        assert _classify("Switch to watercolor art style") == "style_change"

    def test_pixar(self):
        assert _classify("Render everything in Pixar style") == "style_change"

    def test_drawing(self):
        assert _classify("Change to pencil drawing style") == "style_change"


# ---------------------------------------------------------------------------
# 4. bgm_change
# ---------------------------------------------------------------------------

class TestBgmChange:
    def test_bgm_keyword(self):
        assert _classify("Change the BGM to something sad") == "bgm_change"

    def test_background_music(self):
        assert _classify("Make the background music more intense in scene 2") == "bgm_change"

    def test_target_scene(self):
        assert _target("Change BGM for scene 5") == "scene_5"


# ---------------------------------------------------------------------------
# 5. script_edit
# ---------------------------------------------------------------------------

class TestScriptEdit:
    def test_rewrite_dialogue(self):
        assert _classify("Rewrite the dialogue in scene 4 so Ethan is angrier") == "script_edit"

    def test_change_line(self):
        assert _classify("Change Ethan's line in scene 1") == "script_edit"

    def test_say_keyword(self):
        assert _classify("Make Olivia say something kinder") == "script_edit"

    def test_script_keyword(self):
        assert _classify("Edit the script for scene 3") == "script_edit"


# ---------------------------------------------------------------------------
# 6. subtitle_remove
# ---------------------------------------------------------------------------

class TestSubtitleRemove:
    def test_remove_subtitles(self):
        assert _classify("Remove subtitles from the video") == "subtitle_remove"

    def test_hide_captions(self):
        assert _classify("Hide captions") == "subtitle_remove"

    def test_no_subtitles(self):
        assert _classify("I don't want any subtitles") == "subtitle_remove"


# ---------------------------------------------------------------------------
# 7. speed_change
# ---------------------------------------------------------------------------

class TestSpeedChange:
    def test_speed_up(self):
        assert _classify("Speed up scene 2") == "speed_change"

    def test_slow_down(self):
        assert _classify("Slow down the intro") == "speed_change"

    def test_faster(self):
        assert _classify("Make it faster") == "speed_change"

    def test_slower(self):
        assert _classify("Make the video slower") == "speed_change"

    def test_time_lapse(self):
        assert _classify("Apply time-lapse effect") == "speed_change"


# ---------------------------------------------------------------------------
# 8. brightness_filter
# ---------------------------------------------------------------------------

class TestBrightnessFilter:
    def test_make_darker(self):
        assert _classify("Make scene 3 darker") == "brightness_filter"

    def test_brighten(self):
        assert _classify("Brighten up scene 1") == "brightness_filter"

    def test_contrast(self):
        assert _classify("Increase the contrast in scene 2") == "brightness_filter"

    def test_dim(self):
        assert _classify("Dim the lighting in scene 4") == "brightness_filter"


# ---------------------------------------------------------------------------
# 9. character_redesign
# ---------------------------------------------------------------------------

class TestCharacterRedesign:
    def test_hair_change(self):
        assert _classify("Give Ethan blue hair") == "character_redesign"

    def test_outfit(self):
        assert _classify("Change Olivia's outfit to a red dress") == "character_redesign"

    def test_appearance(self):
        assert _classify("Update Mark's appearance to look older") == "character_redesign"

    def test_redesign_keyword(self):
        assert _classify("Redesign Ethan's look") == "character_redesign"


# ---------------------------------------------------------------------------
# 10. filter_apply
# ---------------------------------------------------------------------------

class TestFilterApply:
    def test_sepia(self):
        assert _classify("Add a sepia filter to the video") == "filter_apply"

    def test_noir(self):
        assert _classify("Make it look like noir") == "filter_apply"

    def test_warm_tones(self):
        assert _classify("Apply warm colour grade") == "filter_apply"

    def test_tint(self):
        assert _classify("Add a blue tint to scene 2") == "filter_apply"


# ---------------------------------------------------------------------------
# 11. transition_change
# ---------------------------------------------------------------------------

class TestTransitionChange:
    def test_fade(self):
        assert _classify("Use a fade transition between scenes") == "transition_change"

    def test_dissolve(self):
        assert _classify("Add dissolve transition") == "transition_change"

    def test_wipe(self):
        assert _classify("Switch to wipe transition") == "transition_change"

    def test_transition_keyword(self):
        assert _classify("Change the scene transition to crossfade") == "transition_change"


# ---------------------------------------------------------------------------
# 12. music_add
# ---------------------------------------------------------------------------

class TestMusicAdd:
    def test_add_music(self):
        assert _classify("Add dramatic music to scene 4") == "music_add"

    def test_sound_effect(self):
        assert _classify("Add a sound effect at the start") == "music_add"

    def test_overlay_music(self):
        assert _classify("Overlay some epic music on scene 3") == "music_add"

    def test_audio_track(self):
        assert _classify("Add a new audio track for the climax") == "music_add"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestOutputSchema:
    def test_all_fields_present(self):
        result = _rule_classify("Make it darker in scene 3")
        assert "type" in result
        assert "target" in result
        assert "value" in result
        assert "raw" in result

    def test_type_is_valid(self):
        for instruction in [
            "Darker scene", "Faster video", "Remove subtitles",
            "Sepia filter", "Fade transition", "Add music",
        ]:
            assert _rule_classify(instruction)["type"] in SUPPORTED_INTENTS

    def test_scene_target_extraction(self):
        assert _rule_classify("Make scene_5 brighter")["target"] == "scene_5"
        assert _rule_classify("Edit scene 12 dialogue")["target"] == "scene_12"
        assert _rule_classify("Change the whole video")["target"] == "all"


# ---------------------------------------------------------------------------
# All 12 types covered
# ---------------------------------------------------------------------------

class TestAllIntentTypesCovered:
    def test_twelve_types_exist(self):
        assert len(SUPPORTED_INTENTS) == 12

    def test_all_types_reachable(self):
        sample_instructions = {
            "voice_change":       "Change Ethan's voice",
            "scene_regen":        "Regenerate scene 1",
            "style_change":       "Switch to anime style",
            "bgm_change":         "Change the BGM",
            "script_edit":        "Rewrite the dialogue",
            "subtitle_remove":    "Remove subtitles",
            "speed_change":       "Speed up the video",
            "brightness_filter":  "Make it darker",
            "character_redesign": "Give Ethan blue hair",
            "filter_apply":       "Add sepia filter",
            "transition_change":  "Use fade transition",
            "music_add":          "Add dramatic music",
        }
        for expected_type, instruction in sample_instructions.items():
            result_type = _classify(instruction)
            assert result_type == expected_type, (
                f"Expected '{expected_type}' for '{instruction}', got '{result_type}'"
            )
