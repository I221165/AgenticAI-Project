import pytest
from pydantic import ValidationError
from shared.schemas.state_schema import Character, DialogueLine, Scene, StoryOutput, CharacterRoster, ScriptOutput, GlobalState

def test_character_schema_valid():
    char = Character(
        name="Aria",
        role="Protagonist",
        voice_personality="soft, determined female voice",
        visual_description="young woman with silver hair and a spacesuit"
    )
    assert char.name == "Aria"
    assert char.role == "Protagonist"

def test_character_schema_missing_field():
    with pytest.raises(ValidationError):
        Character(name="Aria", role="Protagonist")

def test_story_output_schema():
    story = StoryOutput(
        title="Journey to Mars",
        logline="An astronaut finds water on Mars.",
        themes=["exploration", "discovery"],
        narrative_arc="Intro: Aria lands on Mars. Climax: She discovers an ocean. Resolution: She reports back to Earth."
    )
    assert story.title == "Journey to Mars"
    assert len(story.themes) == 2

def test_character_roster_schema():
    roster = CharacterRoster(
        characters=[
            Character(
                name="Aria",
                role="Protagonist",
                voice_personality="soft",
                visual_description="spacesuit"
            )
        ]
    )
    assert len(roster.characters) == 1

def test_script_output_schema():
    script = ScriptOutput(
        scenes=[
            Scene(
                scene_id="scene_1",
                setting="Mars surface",
                visual_description="Red dust blowing",
                tone="mysterious",
                duration_estimate_sec=10,
                dialogue_lines=[
                    DialogueLine(
                        character_name="Aria",
                        text="It's beautiful.",
                        emotion="awe"
                    )
                ]
            )
        ]
    )
    assert len(script.scenes) == 1
    assert script.scenes[0].dialogue_lines[0].text == "It's beautiful."

def test_global_state_initialization():
    state = GlobalState(prompt="A test prompt")
    assert state.prompt == "A test prompt"
    assert state.story_output is None
    assert state.character_roster is None
    assert state.script_output is None
    assert state.version == 1
