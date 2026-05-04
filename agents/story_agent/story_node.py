from typing import Dict, Any
from mcp.tool_registry import ToolRegistry
import re

def validate_story_arc(story: Dict[str, Any]) -> Dict[str, Any]:
    """PDF Tool: Validates the story arc has intro, climax, and resolution."""
    arc = story.get("narrative_arc", "").lower()
    if not arc:
        story["narrative_arc"] = "Intro: A beginning. Climax: A turning point. Resolution: An ending."
    else:
        if "intro" not in arc and "beginning" not in arc:
            story["narrative_arc"] = "Intro: " + story["narrative_arc"]
        if "climax" not in arc:
            story["narrative_arc"] += " | Climax: The peak of the conflict."
        if "resolution" not in arc and "end" not in arc:
            story["narrative_arc"] += " | Resolution: The story concludes."
    return story

def estimate_duration(story: Dict[str, Any]) -> Dict[str, Any]:
    """PDF Tool: Estimates overall duration based on word count of the arc."""
    arc = story.get("narrative_arc", "")
    words = len(arc.split())
    # Rough estimate: 1 word = 0.5 seconds of screen time for a high-level arc
    story["estimated_duration_sec"] = max(30, int(words * 0.5))
    return story

_DURATION_LABELS = {
    "short":  "a short animated film of about 1 minute",
    "medium": "a medium animated short of about 2 minutes",
    "long":   "a longer animated short of about 3 minutes",
}


def generate_story_arc(prompt: str, duration: str = "medium", provider: int = 2, language: str = "English") -> Dict[str, Any]:
    """
    Agent Node: Generates the core narrative arc (StoryOutput) from the prompt.
    """
    text_generator = ToolRegistry.get_tool("text_generator")
    json_structurer = ToolRegistry.get_tool("json_structurer")

    duration_label = _DURATION_LABELS.get(duration, _DURATION_LABELS["medium"])

    system_prompt = (
        f"You are an award-winning storyteller specializing in animated films. "
        f"Create a story suitable for {duration_label}. "
        f"Write all story content (title, logline, themes, narrative arc) in {language}. "
        "Output ONLY a valid JSON object — no markdown, no explanation, no text before or after.\n\n"
        "The JSON must follow this exact structure:\n"
        "{\n"
        '  "title": "A catchy, evocative title",\n'
        '  "logline": "A single punchy sentence summarising the story",\n'
        '  "themes": ["theme1", "theme2"],\n'
        '  "narrative_arc": "Intro: world and character setup. Climax: the central conflict peak. Resolution: satisfying conclusion."\n'
        "}\n\n"
        "Rules:\n"
        "- themes must be a JSON array of 2-3 short strings\n"
        "- narrative_arc must be a single string containing Intro, Climax, and Resolution\n"
        "- Focus on emotional resonance and visual storytelling potential\n"
        "- Output raw JSON only — no markdown code fences"
    )

    # 1. Generate story arc — 70B outputs JSON directly so _try_direct_parse handles it
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=f"{prompt}\n\nNow output the JSON:",
        model_name="llama-3.3-70b-versatile" if provider == 2 else "llama3",
        provider=provider
    )

    # 2. Structure into StoryOutput using the fast model (pure parsing task)
    story_output_json = json_structurer.execute(
        raw_text=raw_text,
        target_schema_name="StoryOutput",
        model_name="llama-3.1-8b-instant" if provider == 2 else "llama3",
        provider=provider
    )
    
    # 3. Apply Node Validation Tools
    story_output_json = validate_story_arc(story_output_json)
    story_output_json = estimate_duration(story_output_json)
    
    return story_output_json
