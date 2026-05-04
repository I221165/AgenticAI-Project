from typing import Dict, Any
from mcp.tool_registry import ToolRegistry

def plan_story(prompt: str, provider: int = 1) -> str:
    """
    Phase 1 Planner: Drafts an initial narrative outline based on the user's prompt.
    Uses the TextGeneratorTool from the MCP layer.
    """
    # Fetch the text generator tool
    text_generator = ToolRegistry.get_tool("text_generator")
    
    system_prompt = (
        "You are an expert storyteller and screenwriter. Your job is to take a brief user prompt "
        "and expand it into a detailed narrative outline for a short animated video. "
        "Include a title, a logline, a list of 2-3 characters (with physical descriptions and vocal traits), "
        "and a sequence of 3-5 distinct scenes with clear settings and dialogue."
    )
    
    # Execute the tool (this assumes the tool is instantiated or we call execute directly if it's a class method. 
    # Let's instantiate it if it's not already in the registry, but the orchestrator should register it at startup.)
    # For now, we assume it's registered and fetchable.
    
    outline = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=prompt,
        model_name="llama3", # Budget-friendly local default
        provider=provider
    )
    
    return outline
