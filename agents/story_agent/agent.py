import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from mcp.tool_registry import ToolRegistry

from .story_node import generate_story_arc
from .character_node import generate_character_roster
from .script_node import generate_script
from shared.utils.serializer import serialize_phase1_outputs, get_run_dir

try:
    from shared.utils.progress import report as _report
except ImportError:
    def _report(*a, **kw): pass

class AgentState(TypedDict):
    prompt: str
    style: str
    duration: str
    language: str
    provider: int
    run_dir: str
    story_output: Dict[str, Any]
    character_roster: Dict[str, Any]
    script_output: Dict[str, Any]
    artifact_paths: Dict[str, str]
    error: str

def story_node(state: AgentState) -> Dict[str, Any]:
    try:
        _report(1, 5, "Generating story arc…")
        story = generate_story_arc(
            state["prompt"],
            duration=state.get("duration", "medium"),
            provider=state.get("provider", 2),
            language=state.get("language", "English"),
        )
        _report(1, 30, "Story arc complete")
        return {"story_output": story}
    except Exception as e:
        return {"error": f"Story node failed: {e}"}

def character_node(state: AgentState) -> Dict[str, Any]:
    if state.get("error"): return {}
    try:
        _report(1, 35, "Designing character roster…")
        characters = generate_character_roster(
            state["story_output"],
            style=state.get("style", "2D animated"),
            provider=state.get("provider", 2),
            language=state.get("language", "English"),
        )
        _report(1, 60, "Character roster ready")
        return {"character_roster": characters}
    except Exception as e:
        return {"error": f"Character node failed: {e}"}

def script_node(state: AgentState) -> Dict[str, Any]:
    if state.get("error"): return {}
    try:
        _report(1, 63, "Writing scene dialogue and visual prompts…")
        script = generate_script(
            state["story_output"],
            state["character_roster"],
            style=state.get("style", "2D animated"),
            duration=state.get("duration", "medium"),
            provider=state.get("provider", 2),
            language=state.get("language", "English"),
        )
        _report(1, 90, "Script complete")
        return {"script_output": script}
    except Exception as e:
        return {"error": f"Script node failed: {e}"}

def serialize_node(state: AgentState) -> Dict[str, Any]:
    if state.get("error"): return {}
    try:
        _report(1, 94, "Saving story artifacts to disk…")
        paths = serialize_phase1_outputs(dict(state), output_dir=state["run_dir"])
        _report(1, 99, "Phase 1 artifacts saved")
        return {"artifact_paths": paths}
    except Exception as e:
        return {"error": f"Serializer failed: {e}"}

def build_phase1_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("story_agent", story_node)
    workflow.add_node("character_agent", character_node)
    workflow.add_node("script_agent", script_node)
    workflow.add_node("serializer", serialize_node)
    
    workflow.set_entry_point("story_agent")
    workflow.add_edge("story_agent", "character_agent")
    workflow.add_edge("character_agent", "script_agent")
    workflow.add_edge("script_agent", "serializer")
    workflow.add_edge("serializer", END)
    
    app = workflow.compile()
    return app

def run_phase1(
    prompt: str,
    provider: int = 2,
    run_id: str = None,
    style: str = "2D animated",
    duration: str = "medium",
    language: str = "English",
) -> Dict[str, Any]:
    """Run Phase 1.

    Pass run_id to reuse the same folder as the StateManager run,
    so MongoDB and local disk always share one consistent run ID.
    style  — visual art style (e.g. "anime", "Pixar 3D", "2D animated")
    duration — target length: "short" | "medium" | "long"
    """
    app = build_phase1_graph()
    run_dir = get_run_dir(run_id=run_id)
    initial_state = {
        "prompt": prompt,
        "style": style,
        "duration": duration,
        "language": language,
        "provider": provider,
        "run_dir": run_dir,
        "story_output": {},
        "character_roster": {},
        "script_output": {},
        "artifact_paths": {},
        "error": ""
    }
    
    result = app.invoke(initial_state)
    return result
