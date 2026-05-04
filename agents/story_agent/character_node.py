import json
from typing import Dict, Any
from mcp.tool_registry import ToolRegistry

def check_consistency(roster: Dict[str, Any], story: Dict[str, Any]) -> Dict[str, Any]:
    """PDF Tool: Checks if characters fit the story and fixes common missing attributes."""
    for char in roster.get("characters", []):
        if not char.get("name"): char["name"] = "Unknown"
        if not char.get("role"): char["role"] = "Supporting"
        if not char.get("voice_personality"): char["voice_personality"] = "Neutral tone"
        if not char.get("visual_description"): char["visual_description"] = "A standard looking character."
    return roster

def generate_character_roster(story_output: Dict[str, Any], style: str = "2D animated", provider: int = 2, language: str = "English") -> Dict[str, Any]:
    """
    Agent Node: Generates the CharacterRoster based on the StoryOutput.
    """
    text_generator = ToolRegistry.get_tool("text_generator")
    json_structurer = ToolRegistry.get_tool("json_structurer")

    story_context = json.dumps(story_output)

    system_prompt = (
        f"You are an expert character designer for {style} animated films. "
        f"Write all character names, roles, and descriptions in {language}. "
        "Output ONLY a valid JSON object — no markdown, no explanation, no text before or after.\n\n"
        "The JSON must follow this exact structure:\n"
        "{\n"
        '  "characters": [\n'
        "    {\n"
        '      "name": "Character Name",\n'
        '      "role": "Protagonist",\n'
        '      "voice_personality": "warm, gentle male voice in his early 20s, slightly nervous",\n'
        f'      "visual_description": "A young man, early 20s, slim build, messy dark hair, tired eyes — drawn in {style} style"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Create 2-4 distinct characters that fit the story\n"
        "- role must be one of: Protagonist, Antagonist, Supporting, Narrator\n"
        "- voice_personality must specify gender, approximate age, and manner of speaking\n"
        f"- visual_description must include age, build, hair, eyes, clothing, and be described in {style} art style\n"
        "- Output raw JSON only — no markdown code fences"
    )

    # 1. Generate characters — 70B outputs JSON directly so _try_direct_parse handles it
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=f"Story Context:\n{story_context}\n\nNow output the JSON:",
        model_name="llama-3.3-70b-versatile" if provider == 2 else "llama3",
        provider=provider
    )

    # 2. Structure into CharacterRoster using the fast model
    roster_json = json_structurer.execute(
        raw_text=raw_text,
        target_schema_name="CharacterRoster",
        model_name="llama-3.1-8b-instant" if provider == 2 else "llama3",
        provider=provider
    )
    
    # 3. Apply Node Validation Tools
    roster_json = check_consistency(roster_json, story_output)
    
    return roster_json
