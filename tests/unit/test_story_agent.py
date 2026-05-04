import pytest
from unittest.mock import patch, MagicMock
from agents.story_agent.agent import build_phase1_graph, run_phase1
from mcp.tool_registry import ToolRegistry
from mcp.base_tool import BaseAgenticTool
from pydantic import BaseModel

# A dummy tool for testing the structurer
class DummyStructurerTool(BaseAgenticTool):
    name = "json_structurer"
    description = "dummy"
    args_schema = BaseModel
    
    _call_count = 0
    
    def execute(self, **kwargs):
        DummyStructurerTool._call_count += 1
        schema = kwargs.get("target_schema_name", "")
        
        if schema == "StoryOutput":
            return {
                "title": "Mock Story",
                "logline": "Mock logline",
                "themes": ["adventure"],
                "narrative_arc": "Intro: A hero rises. Climax: The battle. Resolution: Peace returns."
            }
        elif schema == "CharacterRoster":
            return {
                "characters": [
                    {"name": "Hero", "role": "Protagonist", "voice_personality": "deep male voice", "visual_description": "tall warrior"}
                ]
            }
        elif schema == "ScriptOutput":
            return {
                "scenes": [
                    {
                        "scene_id": "scene_1",
                        "setting": "Castle",
                        "visual_description": "A grand castle",
                        "tone": "tense",
                        "duration_estimate_sec": 10,
                        "dialogue_lines": [
                            {"character_name": "Hero", "text": "We must fight!", "emotion": "determined"}
                        ]
                    }
                ]
            }
        return {}

# A dummy tool for testing the generator
class DummyTextGeneratorTool(BaseAgenticTool):
    name = "text_generator"
    description = "dummy"
    args_schema = BaseModel
    
    def execute(self, **kwargs):
        return "Mock raw outline"

@pytest.fixture(autouse=True)
def register_dummy_tools():
    DummyStructurerTool._call_count = 0
    ToolRegistry.register(DummyStructurerTool())
    ToolRegistry.register(DummyTextGeneratorTool())

def test_build_phase1_graph():
    app = build_phase1_graph()
    assert app is not None
    
def test_run_phase1():
    result = run_phase1("A test prompt about Mars")
    assert "error" in result
    assert result["error"] == ""
    assert "title" in result["story_output"]
    assert result["story_output"]["title"] == "Mock Story"
    assert "characters" in result["character_roster"]
    assert len(result["character_roster"]["characters"]) == 1
    assert "scenes" in result["script_output"]
    assert len(result["script_output"]["scenes"]) == 1

def test_phase1_calls_all_three_agents():
    """Verify the structurer was called 3 times (once per agent node)."""
    run_phase1("Test prompt")
    assert DummyStructurerTool._call_count == 3
