from typing import List, Optional
from pydantic import BaseModel, Field

# --- Phase 1 Schemas ---

class Character(BaseModel):
    name: str = Field(..., description="The name of the character")
    role: str = Field(..., description="The character's role in the story (e.g., Protagonist, Antagonist, Supporting)")
    voice_personality: str = Field(..., description="Description of how the character speaks, for TTS (e.g., 'deep, authoritative male voice', 'high-pitched, energetic female voice')")
    visual_description: str = Field(..., description="Physical appearance of the character for image generation")

class DialogueLine(BaseModel):
    character_name: str = Field(..., description="The name of the character speaking")
    text: str = Field(..., description="The exact dialogue text to be spoken")
    emotion: str = Field(..., description="The emotion of the dialogue line (e.g., happy, sad, angry, neutral)")

class Scene(BaseModel):
    scene_id: str = Field(..., description="Unique identifier for the scene (e.g., 'scene_1')")
    setting: str = Field(..., description="Brief description of where the scene takes place")
    visual_description: str = Field(..., description="Detailed visual prompt for image generation of the scene background and action")
    tone: str = Field(..., description="The overall mood or tone of the scene (e.g., tense, peaceful, mysterious)")
    duration_estimate_sec: int = Field(..., description="Estimated duration of the scene in seconds")
    dialogue_lines: List[DialogueLine] = Field(default_factory=list, description="List of dialogue lines in this scene")

class StoryOutput(BaseModel):
    title: str = Field(..., description="The title of the story")
    logline: str = Field(..., description="A one-sentence summary of the story")
    themes: List[str] = Field(default_factory=list, description="Key themes of the story")
    narrative_arc: str = Field(..., description="A summary of the intro, climax, and resolution")

class CharacterRoster(BaseModel):
    characters: List[Character] = Field(default_factory=list, description="All characters appearing in the story")

class ScriptOutput(BaseModel):
    scenes: List[Scene] = Field(default_factory=list, description="Chronological list of scenes in the story")

# --- Phase 2 Schemas ---

class TimingManifestEntry(BaseModel):
    scene_id: str = Field(..., description="The ID of the scene")
    audio_file: str = Field(..., description="Path to the generated audio file for this segment")
    start_ms: int = Field(..., description="Start time in milliseconds relative to the final video")
    end_ms: int = Field(..., description="End time in milliseconds relative to the final video")

class TimingManifest(BaseModel):
    entries: List[TimingManifestEntry] = Field(default_factory=list, description="Chronological audio timing manifest")
    bgm_file: Optional[str] = Field(None, description="Path to the background music file")

# --- Global State Schema ---

class GlobalState(BaseModel):
    """
    The central state object passed between all agent phases.
    """
    prompt: str = Field("", description="The original user prompt")
    story_output: Optional[StoryOutput] = Field(None, description="Phase 1 Output: The generated story arc")
    character_roster: Optional[CharacterRoster] = Field(None, description="Phase 1 Output: The generated characters")
    script_output: Optional[ScriptOutput] = Field(None, description="Phase 1 Output: The generated script scenes")
    timing_manifest: Optional[TimingManifest] = Field(None, description="Phase 2 Output: Audio timing details")
    final_video_path: Optional[str] = Field(None, description="Phase 3 Output: Path to the final MP4")
    
    # Track the current version for the Phase 5 undo/edit system
    version: int = Field(1, description="Current version of the state")
