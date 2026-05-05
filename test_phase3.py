import os
import json
from dotenv import load_dotenv

load_dotenv()

from agents.video_agent.agent import run_phase3
from mcp.tools.video_tools.ffmpeg_tool import FFmpegTool


def main():
    print("=== Testing Phase 3: Video Generation ===")

    # 1. Check FFmpeg availability
    if not FFmpegTool.check_ffmpeg():
        print("\n[ERROR] FFmpeg is not installed or not in PATH.")
        print("Install it from https://ffmpeg.org/download.html and add it to PATH.")
        return

    print("[OK] FFmpeg found.")

    # 2. Select run_id
    print("\n--- Run Selection ---")
    base_dir = "run_outputs"
    if os.path.isdir(base_dir):
        runs = sorted(
            [d for d in os.listdir(base_dir) if d.startswith("run_")],
            reverse=True,
        )
        if runs:
            print("Available runs:")
            for i, r in enumerate(runs[:10], 1):
                print(f"  {i}. {r}")
            print()

    run_id = input("Enter run_id (e.g. run_20260501_130423): ").strip()
    if not run_id:
        print("[ERROR] run_id is required.")
        return

    run_dir = os.path.join(base_dir, run_id)
    if not os.path.isdir(run_dir):
        print(f"[ERROR] Run directory not found: {run_dir}")
        return

    # 3. Load phase3_video_handoff.json
    handoff_path = os.path.join(run_dir, "phase3_video_handoff.json")
    if not os.path.exists(handoff_path):
        print(f"[ERROR] phase3_video_handoff.json not found in {run_dir}")
        print("Run Phase 1 and Phase 2 first.")
        return

    with open(handoff_path) as f:
        handoff_json = json.load(f)

    scenes = handoff_json.get("scenes", [])
    print(f"\n[OK] Loaded handoff: {len(scenes)} scene(s)")
    for s in scenes:
        print(f"  - {s['scene_id']}: {s.get('tone', '?')} tone, "
              f"{s.get('duration_estimate_sec', '?')}s, "
              f"camera={s.get('camera_work', '?')}, "
              f"transition={s.get('transition_to_next', '?')}")

    # 4. Load timing_manifest.json
    manifest_path = os.path.join(run_dir, "timing_manifest.json")
    timing_entries = []
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest_data = json.load(f)
        timing_entries = manifest_data.get("entries", [])
        print(f"[OK] Loaded timing manifest: {len(timing_entries)} dialogue line(s)")

        # Patch full_audio_path into handoff_json if Phase 2 ran
        if "full_audio_path" not in handoff_json or not handoff_json["full_audio_path"]:
            handoff_json["full_audio_path"] = manifest_data.get("full_audio_path", "")
    else:
        print("[WARNING] timing_manifest.json not found — subtitles will be empty.")

    full_audio = handoff_json.get("full_audio_path", "")
    if full_audio and os.path.exists(full_audio):
        print(f"[OK] Full audio: {full_audio}")
    else:
        print("[WARNING] Full audio not found — video will be silent.")

    # 5. FPS option
    fps_input = input("\nFPS (default 24): ").strip()
    fps = int(fps_input) if fps_input.isdigit() else 24

    print(f"\nStarting Phase 3 pipeline (fps={fps})...")
    print("Step 1/6: Generating scene images via Pollinations.ai ...")
    print("(This may take a few minutes per scene — images are cached on disk)\n")

    try:
        result = run_phase3(
            handoff_json=handoff_json,
            timing_entries=timing_entries,
            run_dir=run_dir,
            fps=fps,
        )

        if result.get("error"):
            print(f"\n[ERROR] {result['error']}")
        else:
            final_video = result.get("final_video_path", "")
            print("\n[SUCCESS] Phase 3 completed!")
            print(f"  Final video : {final_video}")
            print(f"  Silent video: {result.get('silent_video_path', '')}")
            print(f"  Scenes      : {result.get('scenes_composed', 0)}")
            print(f"  Images      : {result.get('images_generated', 0)}")

            output_manifest = os.path.join(run_dir, "phase3_output.json")
            if os.path.exists(output_manifest):
                print(f"\n  Full output manifest: {output_manifest}")

    except Exception as e:
        print(f"\n[EXCEPTION] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
