import json
import re
from typing import Dict, Any, List
from mcp.tool_registry import ToolRegistry

# Duration → scene count and dialogue density
_DURATION_CONFIG = {
    "short":  {"scene_count": "3",   "dialogue_range": "2-3", "sec_range": "8 to 20"},
    "medium": {"scene_count": "5",   "dialogue_range": "3-4", "sec_range": "10 to 30"},
    "long":   {"scene_count": "7",   "dialogue_range": "4-5", "sec_range": "15 to 40"},
}

# Style → visual prompt prefix for image generation (FLUX-optimised)
_STYLE_PREFIXES = {
    "2D animated": (
        "2D animated short film, vibrant flat cel illustration, clean vector linework, "
        "expressive stylized character design, bold color blocking, dynamic posed figures, "
        "richly detailed hand-painted backgrounds, Disney renaissance meets modern cartoon aesthetic, "
        "professional animation production quality"
    ),
    "anime": (
        "anime art style, detailed cel-shading with clean ink outlines, "
        "vivid saturated color palette, Studio Ghibli inspired painterly background art, "
        "highly expressive emotive faces, flowing dynamic hair and fabric movement, "
        "dramatic cinematic framing, professional anime production quality, "
        "Makoto Shinkai atmospheric lighting"
    ),
    "Pixar 3D": (
        "Pixar CGI animation film still, photorealistic subsurface scattering on skin, "
        "soft warm global illumination, highly detailed surface textures and materials, "
        "expressive stylized character faces, cinematic depth of field bokeh, "
        "volumetric god rays, octane render quality, 3D animated feature film"
    ),
    "comic book": (
        "comic book illustration, bold black india ink outlines, Ben-Day halftone dot shading, "
        "primary color blocking with dramatic contrast, splash page composition energy, "
        "Marvel and DC aesthetic combined, dynamic action angles, "
        "graphic novel panel art, high contrast inked illustration"
    ),
    "watercolor": (
        "watercolor illustration art, soft wet-on-wet color bleeding edges, "
        "visible cold-press paper texture, loose expressive painterly brushwork, "
        "harmonious muted earthy palette with selective vibrant accents, "
        "Shaun Tan and Beatrix Potter aesthetic, delicate ink linework beneath washes, "
        "dreamy impressionistic atmospheric quality"
    ),
    "realistic cinematic": (
        "cinematic live-action film still, anamorphic 2.39:1 aspect ratio lens character, "
        "f/1.8 shallow depth of field with creamy bokeh, 35mm film grain and halation, "
        "color graded with teal-orange Hollywood LUT, "
        "photorealistic skin texture and material rendering, "
        "award-winning cinematography, Kodak Portra 400 color science"
    ),
}

# Maps scene tone to a Ken Burns camera movement for Phase 3
_TONE_TO_CAMERA = {
    "tense":      "zoom_in",
    "suspense":   "zoom_in",
    "mysterious": "zoom_in",
    "dark":       "zoom_in",
    "sad":        "zoom_out",
    "melancholy": "zoom_out",
    "emotional":  "zoom_out",
    "peaceful":   "pan_right",
    "calm":       "pan_right",
    "serene":     "pan_left",
    "happy":      "pan_right",
    "joyful":     "pan_left",
    "epic":       "pan_right",
    "heroic":     "pan_right",
    "action":     "pan_left",
    "romantic":   "zoom_in",
}

# Maps tone-change pairs to FFmpeg xfade transition types
_TRANSITION_RULES = {
    ("tense", "peaceful"):   "fade",
    ("sad", "happy"):        "fade",
    ("mysterious", "epic"):  "wipe",
    ("action", "peaceful"):  "fade",
}
_DEFAULT_TRANSITION = "crossfade"
_LAST_SCENE_TRANSITION = "fade"


def analyze_emotions(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Scans dialogue lines and fills in missing emotions via text heuristics."""
    emotion_keywords = {
        "angry":   ["!", "how dare", "unacceptable", "enough"],
        "happy":   ["love", "happy", "wonderful", "great", "amazing", "joy"],
        "sad":     ["sorry", "miss", "lost", "alone", "cry", "tears"],
        "scared":  ["afraid", "fear", "terrified", "help"],
        "excited": ["incredible", "unbelievable", "wow", "can't believe"],
        "confused": ["?", "why", "how", "what is"],
    }
    for scene in script.get("scenes", []):
        for line in scene.get("dialogue_lines", []):
            if not line.get("emotion") or line.get("emotion").strip() == "":
                text = line.get("text", "").lower()
                matched = "neutral"
                for emotion, triggers in emotion_keywords.items():
                    if any(t in text for t in triggers):
                        matched = emotion
                        break
                line["emotion"] = matched
    return script


def build_visual_prompt(script: Dict[str, Any], character_roster: Dict[str, Any] = None, style: str = "2D animated") -> Dict[str, Any]:
    """
    Tool: Enriches each scene's visual_description into a full FLUX-optimised image generation prompt.
    Includes art style, setting, character appearances, tone-matched lighting, color palette,
    atmosphere, composition keywords, and quality suffix.
    Also assigns camera_work based on scene tone.
    """
    style_prefix = _STYLE_PREFIXES.get(style, f"{style} style")
    characters = {c["name"]: c for c in (character_roster or {}).get("characters", [])}

    # Tone → detailed lighting description
    tone_lighting = {
        "tense": (
            "dramatic raking side lighting, single harsh key light casting long shadows, "
            "high contrast chiaroscuro, cool desaturated blue-grey grading, oppressive atmosphere"
        ),
        "mysterious": (
            "dim moonlight filtering through volumetric haze, cool blue-purple ambient glow, "
            "isolated warm practical light accent, silhouettes partially obscured by mist, "
            "dark vignette edges, eerie stillness"
        ),
        "sad": (
            "soft diffused overcast daylight, muted desaturated palette dominated by blue-grey, "
            "gentle rain-streaked or fogged atmosphere, low-key fill lighting with no hard shadows, "
            "emotional weight conveyed through stillness and empty negative space"
        ),
        "peaceful": (
            "warm golden hour sunlight at low angle, long soft shadows, "
            "gentle lens bloom and solar flare, amber and gold saturated palette, "
            "soft bokeh on background elements, open airy spacious composition"
        ),
        "happy": (
            "bright cheerful natural midday sunlight, vivid saturated warm colors, "
            "clean sharp crisp shadows, golden rim highlights on characters, "
            "uplifting open wide composition, energetic vibrant palette"
        ),
        "epic": (
            "dramatic golden backlighting creating powerful rim light silhouettes, "
            "volumetric god rays piercing through atmospheric haze, "
            "high contrast warm hero light against cool deep shadow, "
            "cinematic anamorphic lens flare, vast scale perspective"
        ),
        "heroic": (
            "strong directional sunrise backlight creating heroic silhouette, "
            "warm rose-gold and amber tones, dramatic underexposed foreground with blown highlights, "
            "monumental upward-looking composition, inspiring atmosphere"
        ),
        "action": (
            "dynamic harsh directional lighting, kinetic motion blur on fast elements, "
            "high contrast fast-shutter aesthetic, oblique Dutch angle energy, "
            "dust particles and debris catching light, intense saturated palette with deep blacks"
        ),
        "romantic": (
            "warm soft candlelight or golden hour glow, "
            "shallow depth of field with circular bokeh light orbs in background, "
            "amber and rose color palette, intimate close framing, "
            "soft diffusion giving skin a luminous quality"
        ),
        "dark": (
            "near-total darkness with single stark cold practical spotlight, "
            "deep inky blacks with crushed shadows, almost monochrome desaturated palette, "
            "heavy vignette pressing in from edges, claustrophobic low ceiling suggestion"
        ),
    }

    # Tone → dominant color palette hint (reinforces FLUX color generation)
    tone_palette = {
        "tense":      "cool steel blues and harsh whites",
        "mysterious": "deep indigos, teal shadows, single amber accent",
        "sad":        "muted blue-greys, washed-out desaturated tones",
        "peaceful":   "warm ambers, soft greens, golden light",
        "happy":      "vivid yellows, warm oranges, bright sky blues",
        "epic":       "burnished gold, deep crimson, vast sky blue",
        "heroic":     "rose-gold sunrise, deep silhouette blacks",
        "action":     "high contrast blacks and whites with hot accent color",
        "romantic":   "warm rose, amber candlelight, soft ivory",
        "dark":       "near-monochrome blacks and cold whites",
    }

    # FLUX quality suffix — appended to every prompt
    _QUALITY_SUFFIX = (
        "masterpiece, best quality, highly detailed, sharp focus, "
        "professional illustration, 8k resolution, award-winning composition, "
        "rich textures, perfect anatomy, no blur, no artifacts"
    )

    for scene in script.get("scenes", []):
        setting = scene.get("setting", "")
        tone = scene.get("tone", "neutral").lower()
        existing_desc = scene.get("visual_description", "")

        # Identify which characters appear and inject their full visual descriptions
        speakers = {line["character_name"] for line in scene.get("dialogue_lines", [])}
        char_descriptions = []
        for name in speakers:
            if name in characters:
                visual = characters[name].get("visual_description", "")
                if visual:
                    # Trim to key appearance details only — keep prompts focused
                    char_descriptions.append(f"{name}: {visual[:180]}")

        lighting    = tone_lighting.get(tone, "natural balanced soft lighting")
        palette     = tone_palette.get(tone, "balanced natural colors")
        char_str    = " | ".join(char_descriptions)
        char_clause = f"Characters: {char_str}. " if char_str else ""

        base = existing_desc if existing_desc else setting

        scene["visual_description"] = (
            f"{style_prefix}, "
            f"{base}. "
            f"{char_clause}"
            f"Lighting: {lighting}. "
            f"Color palette: {palette}. "
            f"Cinematic 16:9 composition, rule of thirds, foreground depth elements, "
            f"detailed background environment, expressive character faces. "
            f"{_QUALITY_SUFFIX}."
        )

        scene["camera_work"] = _TONE_TO_CAMERA.get(tone, "pan_right")

    return script


def assign_transitions(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Assigns FFmpeg xfade transition types between consecutive scenes."""
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes):
        is_last = (i == len(scenes) - 1)
        if is_last:
            scene["transition_to_next"] = _LAST_SCENE_TRANSITION
            continue
        current_tone = scene.get("tone", "neutral").lower()
        next_tone = scenes[i + 1].get("tone", "neutral").lower()
        pair = (current_tone, next_tone)
        scene["transition_to_next"] = _TRANSITION_RULES.get(pair, _DEFAULT_TRANSITION)
    return script


def validate_duration(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Calculates scene duration based on dialogue word count (~2.5 words/sec)."""
    for scene in script.get("scenes", []):
        total_words = sum(
            len(line.get("text", "").split())
            for line in scene.get("dialogue_lines", [])
        )
        scene["duration_estimate_sec"] = max(5, int(total_words / 2.5))
    return script


def normalize_scene_ids(script: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Ensures all scene IDs follow the 'scene_N' format."""
    for i, scene in enumerate(script.get("scenes", []), start=1):
        scene["scene_id"] = f"scene_{i}"
    return script


def generate_script(
    story_output: Dict[str, Any],
    character_roster: Dict[str, Any],
    style: str = "2D animated",
    duration: str = "medium",
    provider: int = 2,
    language: str = "English",
) -> Dict[str, Any]:
    """
    Agent Node: Generates the ScriptOutput (scenes with dialogue).
    """
    text_generator = ToolRegistry.get_tool("text_generator")
    json_structurer = ToolRegistry.get_tool("json_structurer")

    story_context = json.dumps(story_output)
    character_context = json.dumps(character_roster)

    cfg = _DURATION_CONFIG.get(duration, _DURATION_CONFIG["medium"])
    n_scenes = int(cfg["scene_count"])

    # Build the scenes skeleton so the model sees exactly N slots — this is more
    # reliable than a text rule like "write N scenes" which models often ignore.
    scene_skeleton = ",\n".join(
        f'    {{"scene_id": "scene_{i}", "setting": "...", "visual_description": "...", '
        f'"tone": "tense", "duration_estimate_sec": 12, "dialogue_lines": '
        f'[{{"character_name": "Name", "text": "...", "emotion": "neutral"}}]}}'
        for i in range(1, n_scenes + 1)
    )

    system_prompt = (
        "You are an acclaimed animated film screenwriter. Your scripts are celebrated for dialogue that "
        "sounds effortlessly natural yet carries enormous subtext, and for scenes where every visual "
        "detail does emotional work.\n\n"

        f"Write EXACTLY {n_scenes} scenes in {language}. "
        "Output ONLY a valid JSON object — no markdown, no prose, no explanation.\n\n"

        "━━━ SCENE WRITING PRINCIPLES ━━━\n"
        "1. DRAMATIC PURPOSE: Every scene must answer — what changes between the opening and closing beat "
        "of this scene? A scene where nothing changes is a scene that should be cut.\n"
        "2. CHARACTER VOICE: Each character's dialogue must be unmistakably theirs. "
        "A line by the protagonist should never be interchangeable with a line by the antagonist. "
        "Vocabulary, rhythm, what they say and what they withhold — all distinct.\n"
        "3. SUBTEXT: Great dialogue is about what people do NOT say. "
        "Write the surface conversation; the real conversation happens underneath. "
        "Example — bad: 'I'm so angry at you.' Good: 'You look tired. Did you sleep?' (said to someone they're furious at)\n"
        "4. IN MEDIAS RES: Start every scene in the middle of something already happening. "
        "No 'Hello, how are you' — we arrive at the moment of tension.\n"
        "5. END ON A QUESTION: Each scene should close with something unresolved that pulls the audience forward.\n\n"

        "━━━ DIALOGUE QUALITY RULES ━━━\n"
        "• Use SPECIFIC, CONCRETE language — not 'things were difficult' but "
        "'the electricity has been off for three weeks and nobody has called'\n"
        "• Let what characters DON'T finish saying do work — trailing off, interrupting themselves, "
        "changing the subject mid-sentence reveals more than completed thoughts\n"
        "• Each line must do at least one of: reveal character, escalate conflict, deepen subtext\n"
        "• Avoid exposition dumps — characters never explain things both parties already know\n"
        "• Read every line aloud mentally: does it sound like a human being or a plot device?\n\n"

        "━━━ SETTING & VISUAL DESCRIPTION ━━━\n"
        "• The setting must be SPECIFIC and VISUALIZABLE — not 'a room' but "
        "'a kitchen at 3am, dishes from three days still in the sink, one bare bulb, "
        "her coat still on like she planned to leave but didn't'\n"
        "• The physical environment should mirror or contrast the emotional state of the scene\n"
        "• Note what characters are DOING while speaking — action reveals character more than words\n"
        "• Think about what a camera would linger on — make that detail specific\n\n"

        "━━━ SCENE FLOW & PACING ━━━\n"
        f"• Scene 1: Establish the world and plant the central question\n"
        f"• Middle scenes: Each one escalates the conflict in a new direction — avoid repeating the same dynamic\n"
        f"• Final scene: Resolve the story question with emotional honesty — earned, not convenient\n\n"

        "━━━ WHAT TO AVOID ━━━\n"
        "✗ On-the-nose dialogue ('I am so angry', 'I love you so much', 'this is impossible')\n"
        "✗ Characters explaining their backstory to people who would already know it\n"
        "✗ Generic settings that could be any film ('a forest', 'an office')\n"
        "✗ Emotion labels that don't match the dialogue (marking happy when dialogue is hostile)\n"
        "✗ Filler lines that advance nothing ('Okay', 'I understand', 'Let's go')\n\n"

        f"━━━ OUTPUT FORMAT — EXACTLY {n_scenes} SCENES ━━━\n"
        "{{\n"
        '  "scenes": [\n'
        f"{scene_skeleton}\n"
        "  ]\n"
        "}}\n\n"
        "Strict rules:\n"
        f"- scenes array must have EXACTLY {n_scenes} entries — no more, no fewer\n"
        "- tone: one of: tense, mysterious, peaceful, happy, sad, epic, heroic, action, dark, romantic\n"
        "- emotion: one of: happy, sad, angry, scared, neutral, excited, confused, nervous, determined\n"
        f"- Each scene must have {cfg['dialogue_range']} dialogue_lines — each line a distinct character beat\n"
        f"- duration_estimate_sec: integer between {cfg['sec_range']}\n"
        "- Only use character names from the Character Roster — exact spelling\n"
        f"- All text fields in {language}\n"
        "- Output raw JSON only — no markdown, no text before or after"
    )

    user_prompt = (
        f"Story Arc:\n{story_context}\n\n"
        f"Character Roster:\n{character_context}\n\n"
        f"Write {n_scenes} scenes where every line of dialogue feels inevitable in retrospect "
        f"and every setting tells us something about the characters in it. "
        f"Make each scene land like a short film on its own. Output the JSON:"
    )

    # 1. Generate script scenes using the powerful 70B model
    raw_text = text_generator.execute(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_name="llama-3.3-70b-versatile" if provider == 2 else "llama3",
        provider=provider
    )

    # 2. Structure into ScriptOutput using the fast model
    script_json = json_structurer.execute(
        raw_text=raw_text,
        target_schema_name="ScriptOutput",
        model_name="llama-3.1-8b-instant" if provider == 2 else "llama3",
        provider=provider
    )

    # 3. Apply post-processing tools in order
    actual = len(script_json.get("scenes", []))
    print(f"[Script] Generated {actual} scenes (target: {n_scenes}, duration: {duration})")
    script_json = normalize_scene_ids(script_json)
    script_json = analyze_emotions(script_json)
    script_json = validate_duration(script_json)
    script_json = build_visual_prompt(script_json, character_roster, style=style)
    script_json = assign_transitions(script_json)

    return script_json
