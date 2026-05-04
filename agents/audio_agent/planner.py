from typing import Dict, Any, List

# ElevenLabs default voice IDs (from their public voice library)
VOICE_IDS = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",   # Warm, gentle female
    "Drew": "29vD33N1CtxCmqQRPOHJ",      # Deep, authoritative male
    "Clyde": "2EiwWnXFnvU5JabPnv8n",     # Smooth, confident male
    "Dave": "CYw3kZ02Hs0563khs1Fj",      # Older, wise male
    "Mimi": "zrHiDhphv9ZnVXBqCLjz",      # High-pitched, energetic female
}

def plan_audio_voices(story_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Phase 2 Planner: Evaluates the characters in the story and assigns an appropriate
    ElevenLabs voice ID based on their voice_personality and role.
    """
    character_voices = {}
    
    for character in story_data.get("characters", []):
        name = character.get("name", "Unknown")
        personality = character.get("voice_personality", "").lower()
        role = character.get("role", "").lower()
        
        # Check female first to avoid "male" matching inside "female"
        is_female = "female" in personality or "woman" in personality or "girl" in personality
        is_male = not is_female and ("male" in personality or "man" in personality or "boy" in personality)

        voice_name = "Rachel"  # Default

        if "deep" in personality or "authoritative" in personality or is_male:
            voice_name = "Drew"
        elif "smooth" in personality or "handsome" in personality or "confident" in personality:
            voice_name = "Clyde"
        elif "old" in personality or "elderly" in personality or "wise" in personality:
            voice_name = "Dave"
        elif "high-pitched" in personality or "energetic" in personality or "fierce" in personality:
            voice_name = "Mimi"
        elif "warm" in personality or "gentle" in personality or is_female:
            voice_name = "Rachel"
            
        voice_id = VOICE_IDS.get(voice_name, VOICE_IDS["Rachel"])
        character_voices[name] = voice_id
        print(f"[Audio Planner] Assigned voice '{voice_name}' ({voice_id}) to character '{name}' (Personality: {personality})")
        
    return character_voices

