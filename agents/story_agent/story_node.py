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
        f"You are a master screenwriter and story architect with decades of experience crafting "
        f"Oscar-calibre animated films. Your stories are celebrated for psychological depth, "
        f"visual richness, and universal themes that resonate across cultures and ages.\n\n"

        f"Your task: Transform the user's prompt into a compelling, emotionally layered story arc "
        f"for {duration_label}. Write all content in {language}.\n\n"

        "━━━ WHAT MAKES A GREAT ANIMATED STORY ━━━\n"
        "• A protagonist with a specific internal wound or flaw — not just a problem to solve\n"
        "• A conflict that forces them to confront that exact flaw or be destroyed by it\n"
        "• Emotional peaks AND valleys — not a flat escalation to a single climax\n"
        "• Themes explored through ACTIONS and CONSEQUENCES, not through speeches\n"
        "• A world with its own visual logic — something only animation can show\n"
        "• A resolution that earns its emotional weight — the protagonist is CHANGED, not fixed\n\n"

        "━━━ STORY STRUCTURE — CHOOSE THE SHAPE THAT FITS ━━━\n"
        "Do NOT default to the same arc every time. Read the prompt and pick whichever structure "
        "serves that specific story best. Each shape produces a completely different emotional experience:\n\n"

        "ARCHETYPE A — The Fall and Redemption\n"
        "  A character at the height of something (power, happiness, certainty) makes a fatal mistake. "
        "They lose everything. The story is their painful, earned climb back — changed by what they destroyed.\n"
        "  Best for: ambition, hubris, addiction, betrayal stories\n\n"

        "ARCHETYPE B — The Slow Revelation\n"
        "  Everything seems fine. Small wrongnesses accumulate. A truth is uncovered that reframes "
        "everything the audience thought they knew. The ending is inevitable in hindsight.\n"
        "  Best for: mystery, family secrets, identity, grief stories\n\n"

        "ARCHETYPE C — The Impossible Choice\n"
        "  Two things the protagonist loves are put in direct opposition. Every scene tightens the vice. "
        "The climax forces a choice that costs something real regardless of which way they go.\n"
        "  Best for: loyalty, sacrifice, moral dilemma, love stories\n\n"

        "ARCHETYPE D — The Corruption Arc\n"
        "  A good person is incrementally pushed toward something they swore they'd never do. "
        "Each step feels justified. The horror is how reasonable each choice seemed at the time.\n"
        "  Best for: revenge, desperation, survival, 'ends justify means' stories\n\n"

        "ARCHETYPE E — The Coming Apart\n"
        "  Something that seemed permanent — a relationship, a belief, a world — slowly disintegrates. "
        "The story is about grief, acceptance, and what survives the collapse.\n"
        "  Best for: tragedy, loss, change, letting go stories\n\n"

        "ARCHETYPE F — The Underdog's Ascent\n"
        "  A character the world has written off fights through escalating obstacles toward a goal "
        "everyone else believes is impossible. Each setback reveals what they're truly made of.\n"
        "  Best for: sports, survival, competition, proving-yourself stories\n\n"

        "After choosing your archetype, write the narrative_arc as a flowing paragraph (not bullet points, "
        "not labelled phases) — describe the emotional journey in 4-6 rich sentences that make someone "
        "want to watch this film immediately.\n\n"

        "━━━ THEME GUIDANCE ━━━\n"
        "Choose 2-3 themes the story GENUINELY explores through its events — not just mentions:\n"
        "  Strong themes: the cost of ambition, what it means to belong, loyalty vs truth, "
        "facing mortality, the burden of secrets, identity under pressure, redemption without erasure\n"
        "  Weak themes to avoid: 'friendship', 'courage', 'love' — too generic unless made specific\n\n"

        "━━━ VISUAL STORYTELLING ━━━\n"
        "• Every beat of the narrative arc must have a vivid visual representation\n"
        "• The setting should feel like a character — it should change with the protagonist's emotional state\n"
        "• Think in images: what do we SEE that communicates what the character cannot say?\n\n"

        "━━━ WHAT TO AVOID ━━━\n"
        "✗ Protagonists who succeed without genuine internal change\n"
        "✗ Antagonists who are evil without motivation — give them a coherent worldview\n"
        "✗ Resolutions that ignore the emotional wound introduced at the start\n"
        "✗ Clichés: chosen one, evil twin, it was all a dream, sudden magical solution\n"
        "✗ On-the-nose themes stated as dialogue ('the real treasure was friendship all along')\n\n"

        "━━━ OUTPUT FORMAT ━━━\n"
        "Output ONLY a valid JSON object — no markdown, no explanation, no text before or after.\n"
        "{\n"
        '  "title": "A specific, evocative title that hints at the emotional journey",\n'
        '  "logline": "A single punchy sentence: [protagonist] must [active goal] before [consequence], but [internal obstacle]",\n'
        '  "themes": ["specific theme 1", "specific theme 2"],\n'
        '  "narrative_arc": "A flowing 4-6 sentence paragraph describing the emotional journey from beginning to end — no bullet points, no phase labels, just the story as it unfolds and what it costs the protagonist."\n'
        "}\n\n"
        "Rules:\n"
        "- themes must be a JSON array of exactly 2-3 short specific strings\n"
        "- narrative_arc must be a SINGLE flowing paragraph — rich, specific, no phase labels like Intro/Climax\n"
        "- Make the narrative_arc feel like a pitch you'd give to a studio — compelling, visual, emotional\n"
        "- Output raw JSON only — no markdown code fences, no commentary"
    )

    # 1. Generate story arc — 70B outputs JSON directly so _try_direct_parse handles it
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=(
            f"User prompt: {prompt}\n\n"
            f"Now craft an emotionally rich, visually compelling story arc following all the guidelines above. "
            f"Output the JSON:"
        ),
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
