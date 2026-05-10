import os
from dotenv import load_dotenv
import json

# Load environment variables (like GROQ_API_KEY)
load_dotenv()

from agents.story_agent.agent import run_phase1
from mcp.tool_registry import ToolRegistry

def main():
    print("=== Testing Phase 1: Story Agent ===")
    
    # Initialize tools
    ToolRegistry.register_core_tools()
    
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:1b")

    print("\n--- Provider Selection ---")
    print(f"1. Local  (Ollama - {ollama_model})")
    print("2. Cloud  (Groq   - llama-3.3-70b-versatile)")

    while True:
        try:
            provider_choice = int(input("Select your provider (1 or 2): ").strip())
            if provider_choice in [1, 2]:
                provider = provider_choice
                break
            else:
                print("Please enter 1 or 2.")
        except ValueError:
            print("Invalid input. Please enter 1 or 2.")

    if provider == 1:
        print(f"\n[Ollama] Using model: {ollama_model}")
        print("[NOTE] Small models (1b) may produce shorter or simpler stories.")
        print("       Make sure Ollama is running:  ollama serve")
    elif provider == 2:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key or groq_key == "your_groq_api_key_here":
            print("\n[WARNING] GROQ_API_KEY is not set in .env — cloud run will fail.")
            
    print("\n--- Story Prompt ---")
    prompt = input("Enter a prompt for the story (e.g., 'A young astronaut discovers a hidden ocean on Mars'):\n> ").strip()

    if not prompt:
        print("Using default prompt...")
        prompt = "A young astronaut discovers a hidden ocean on Mars"

    print("\n--- Duration ---")
    print("1. Short  (~1 min,  3 scenes)")
    print("2. Medium (~2 min,  5 scenes)  [default]")
    print("3. Long   (~3 min,  7 scenes)")
    duration_map = {"1": "short", "2": "medium", "3": "long"}
    dur_choice = input("Select duration (1/2/3, default=2): ").strip()
    duration = duration_map.get(dur_choice, "medium")

    print("\n--- Visual Style ---")
    style_options = {
        "1": "2D animated",
        "2": "anime",
        "3": "Pixar 3D",
        "4": "comic book",
        "5": "watercolor",
        "6": "realistic cinematic",
    }
    for k, v in style_options.items():
        print(f"{k}. {v}")
    print("Or type a custom style (e.g. 'noir detective', 'cyberpunk')")
    style_input = input("Select style (1-6 or custom, default=1): ").strip()
    style = style_options.get(style_input, style_input if style_input else "2D animated")

    print(f"\nPrompt  : '{prompt}'")
    print(f"Duration: {duration}")
    print(f"Style   : {style}")
    print("Generating story... this may take a moment.")
    
    try:
        from state_manager.storage import StateManager
        state_manager = StateManager()
        
        # 1. Create a new run via StateManager — this generates the canonical run_id
        run_id = state_manager.create_run(prompt)
        print(f"\n[StateManager] Created run: {run_id} (Version 1)")

        # 2. Run Phase 1 — pass the same run_id so local folder matches MongoDB
        result = run_phase1(prompt=prompt, provider=provider, run_id=run_id, style=style, duration=duration)
        
        if result.get("error"):
            print(f"\n[ERROR] Error occurred: {result['error']}")
        else:
            # 3. Retrieve state and update it
            state = state_manager.get_state(run_id)
            if state:
                # Update with Phase 1 outputs
                from shared.schemas.state_schema import StoryOutput, CharacterRoster, ScriptOutput
                state.story_output = StoryOutput(**result.get("story_output", {}))
                state.character_roster = CharacterRoster(**result.get("character_roster", {}))
                state.script_output = ScriptOutput(**result.get("script_output", {}))
                
                # 4. Snapshot version 2
                new_version = state_manager.snapshot(run_id, state)
                print(f"[StateManager] Snapshot saved: Version {new_version}")
            
            print("\n[SUCCESS] Phase 1 completed successfully!\n")
            print(f"📁 Local file folder (for assets): {result.get('run_dir', 'unknown')}\n")
            print("--- Generated Artifacts (JSON files are still exported for reference) ---")
            for name, path in result.get("artifact_paths", {}).items():
                print(f"✅ {name} -> {path}")
            
            # Print a snippet of the story
            print("\n--- Story Arc Snippet ---")
            print(json.dumps(result.get("story_output", {}), indent=2))
            
    except Exception as e:
        print(f"\n[EXCEPTION] An exception occurred: {e}")

if __name__ == "__main__":
    main()
