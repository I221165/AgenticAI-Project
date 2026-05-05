import os
import json
from dotenv import load_dotenv

# Load environment variables (like ELEVENLABS_API_KEY)
load_dotenv()

from mcp.tool_registry import ToolRegistry
from agents.audio_agent.agent import run_phase2

def main():
    print("=== Testing Phase 2: Audio Agent ===")
    
    # Initialize tools
    ToolRegistry.register_core_tools()
    
    print("\n--- TTS Provider Selection ---")
    print("1. Local  (Coqui TTS - Requires Python <3.12)")
    print("2. Cloud  (ElevenLabs - Requires paid API Key)")
    print("3. Free   (gTTS - Google Translate, basic quality)")
    print("4. Free   (Edge-TTS - Microsoft Neural Voices, high quality) ⭐ RECOMMENDED")
    
    while True:
        try:
            provider_choice = int(input("Select your TTS provider (1-4):\n> ").strip())
            if provider_choice in [1, 2, 3, 4]:
                provider = provider_choice
                break
            else:
                print("Please enter 1, 2, 3, or 4.")
        except ValueError:
            print("Invalid input. Please enter 1, 2, 3, or 4.")
            
    if provider == 2:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key or api_key == "your_elevenlabs_api_key_here":
            print("\n[WARNING] You selected Cloud (ElevenLabs) but ELEVENLABS_API_KEY is not set properly in .env!")
            print("The agent will fail unless your environment provides the key.")
            
    print("\n--- Load Run State ---")
    run_id = input("Enter the run_id from Phase 1 (e.g., run_20260429_123456):\n> ").strip()
    
    from state_manager.storage import StateManager
    state_manager = StateManager()
    
    state = state_manager.get_state(run_id)
    if not state:
        print(f"\n[ERROR] Could not find run '{run_id}' in the database.")
        return
        
    if not state.character_roster or not state.script_output:
        print("\n[ERROR] This run is missing character or script data from Phase 1. Did Phase 1 complete successfully?")
        return
        
    print(f"\n📁 Loaded Run: {run_id} (Version {state.version})")
    
    # Construct handoff json from GlobalState
    handoff_json = {
        "voice_configs": [char.model_dump() for char in state.character_roster.characters],
        "segments": [scene.model_dump() for scene in state.script_output.scenes]
    }
    
    # We still need a local folder to store the audio files. We'll use the run_outputs/run_id folder.
    run_dir = os.path.join("run_outputs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    print("Generating Audio... this may take a moment.\n")
    
    try:
        result = run_phase2(handoff_json=handoff_json, provider=provider, run_dir=run_dir)
        
        if result.get("error"):
            print(f"\n[ERROR] Error occurred: {result['error']}")
        else:
            print("\n[SUCCESS] Phase 2 completed successfully!\n")
            
            manifest = result.get("timing_manifest", [])
            bgm = result.get("bgm_tracks", {})
            
            # Update GlobalState with Phase 2 outputs
            from shared.schemas.state_schema import TimingManifest, TimingManifestEntry
            entries = [TimingManifestEntry(**entry) for entry in manifest]
            # Since bgm is per-scene and our schema only holds one bgm_file, we might need to adjust 
            # the schema, but for now we'll just save the first one or leave it blank if multiple exist.
            # Wait, our schema says bgm_file: Optional[str]. We should just update the entries.
            state.timing_manifest = TimingManifest(
                entries=entries,
                bgm_file=list(bgm.values())[0] if bgm else None
            )
            
            # Snapshot version 3
            new_version = state_manager.snapshot(run_id, state)
            print(f"\n[StateManager] Snapshot saved: Version {new_version}")
            
            # Summary
            total_clips = len(manifest)
            total_ms = manifest[-1]["end_ms"] if manifest else 0
            total_sec = total_ms / 1000
            
            print(f"📊 Generated {total_clips} audio clips across {len(bgm)} scene(s)")
            print(f"⏱️  Total dialogue duration: {total_sec:.1f} seconds\n")
            
            print("--- Audio Files ---")
            for entry in manifest:
                dur = entry["end_ms"] - entry["start_ms"]
                print(f"  🎤 [{entry['scene_id']}] {entry['character_name']} ({entry['emotion']}) -> {dur}ms -> {entry['audio_file']}")
            
            print("\n--- BGM per Scene ---")
            for scene_id, bgm_path in bgm.items():
                print(f"  🎵 {scene_id} -> {bgm_path}")
            
            print(f"\n📁 All outputs saved to: {os.path.abspath(run_dir)}")
            
    except Exception as e:
        print(f"\n[EXCEPTION] An exception occurred: {e}")

if __name__ == "__main__":
    main()
