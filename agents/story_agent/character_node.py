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
        f"You are a legendary character designer and psychologist for {style} animated films. "
        f"Your characters are iconic because they feel psychologically real — they have histories, "
        f"contradictions, and wounds that drive every decision they make. "
        f"Write all character content in {language}.\n\n"

        "━━━ WHAT MAKES A GREAT ANIMATED CHARACTER ━━━\n"
        "• A clear WANT (external goal everyone can see) AND a NEED (internal truth they resist)\n"
        "• A defining flaw that is also their greatest strength in the wrong context\n"
        "• A backstory wound that justifies why they are the way they are NOW\n"
        "• A speech pattern so distinctive you could identify them with the author's name removed\n"
        "• Visual design where every choice — color, posture, texture — communicates personality\n\n"

        "━━━ CHARACTER DYNAMICS ━━━\n"
        "• Characters must create productive TENSION with each other — not just help or hinder\n"
        "• The Protagonist and Antagonist represent opposing worldviews, not just opposing goals\n"
        "• Every supporting character should challenge the protagonist's core belief in some way\n"
        "• Avoid pure villains — even the antagonist believes they are right\n\n"

        "━━━ VOICE PERSONALITY GUIDE ━━━\n"
        "Be hyper-specific. Bad: 'deep male voice'. Good: 'a low unhurried baritone that never rises above "
        "a conversational murmur — he speaks as if every word is a small concession, with faint traces "
        "of an accent he has tried to lose, and long pauses that feel like warnings'\n"
        "Include: pitch, pace, texture (smooth/gravelly/breathy/clipped), emotional tell when under stress, "
        "any accent or speech quirk, and what their silence communicates\n\n"

        "━━━ VISUAL DESCRIPTION GUIDE ━━━\n"
        f"Design for {style} art style. Every visual choice must communicate character:\n"
        "• Silhouette test: would this character be recognizable as a shape alone?\n"
        "• Color psychology: warm = open/vital, cool = closed/calculating, desaturated = lost/defeated\n"
        "• Posture and physical habit: how they stand, what they do with their hands, how they move\n"
        "• Clothing as character: worn/pristine, practical/decorative, hiding/displaying something\n"
        "• One specific detail that becomes their visual signature (a scar, an object they always carry, "
        "a way of tilting their head)\n\n"

        "━━━ WHAT TO AVOID ━━━\n"
        "✗ Characters defined purely by their function (the wise mentor, the comic relief)\n"
        "✗ Villains with no internal logic or motivation\n"
        "✗ Protagonists without visible flaws\n"
        "✗ Generic voice descriptions like 'friendly' or 'deep'\n"
        "✗ Visual descriptions that could apply to any character\n\n"

        "━━━ OUTPUT FORMAT ━━━\n"
        "Output ONLY a valid JSON object — no markdown, no explanation.\n"
        "{\n"
        '  "characters": [\n'
        "    {\n"
        '      "name": "Full Character Name",\n'
        '      "role": "Protagonist",\n'
        '      "voice_personality": "detailed voice description as specified above",\n'
        f'      "visual_description": "detailed physical description drawn in {style} style"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Create exactly 2-4 characters — every character must earn their place in the story\n"
        "- role must be one of: Protagonist, Antagonist, Supporting, Narrator\n"
        "- voice_personality must be at least 2 rich sentences covering pitch, pace, texture, and emotional tells\n"
        f"- visual_description must cover age, build, hair, eyes, clothing, posture, signature detail, "
        f"all rendered in {style} art style — minimum 3 sentences\n"
        "- Output raw JSON only — no markdown code fences"
    )

    # 1. Generate characters — 70B outputs JSON directly so _try_direct_parse handles it
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=(
            f"Story Context:\n{story_context}\n\n"
            f"Design characters who feel like they existed before this story started and will continue "
            f"after it ends. Each character must emerge organically from the story's themes and conflicts. "
            f"Output the JSON:"
        ),
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
