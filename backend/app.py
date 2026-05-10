"""
StoryForge AI — FastAPI backend
Full pipeline: Phase 1 (Story) → Phase 2 (Audio) → Phase 3 (Video)

Endpoints:
  POST  /api/runs                    create run + start pipeline
  WS    /ws/{run_id}                 real-time progress stream
  GET   /api/runs                    list all past runs
  GET   /api/runs/{run_id}           full run state (story/chars/script/video)
  GET   /api/runs/{run_id}/video     serve final MP4
  GET   /api/runs/{run_id}/audio/{file}  serve audio file
  POST  /api/runs/{run_id}/edit         AI edit intent → partial re-run
  GET   /api/runs/{run_id}/messages     chat history for this run
  POST  /api/runs/{run_id}/rerun/{n}    re-run pipeline from phase n (1-3)
  GET   /api/runs/{run_id}/versions     version history
  POST  /api/runs/{run_id}/revert/{v}
  GET   /health
"""

import asyncio
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── project root on sys.path ─────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Ensure relative-path imports (run_outputs/, assets/) resolve from project root
os.chdir(ROOT)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="StoryForge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
RUNS_BASE = os.path.join(ROOT, "run_outputs")
os.makedirs(RUNS_BASE, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=4)

# ── In-memory state ───────────────────────────────────────────────────────────
RUNS: Dict[str, Dict[str, Any]] = {}
WS_CLIENTS: Dict[str, List[WebSocket]] = {}
HITL_EVENTS: Dict[str, asyncio.Event] = {}
HITL_CANCELLED: set = set()

# ── MongoDB (optional) ────────────────────────────────────────────────────────
_mongo_col = None
try:
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    _mc = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=2000)
    _mc.server_info()
    _mongo_col = _mc["storyforge"]["runs"]
    print("[MongoDB] Connected ✓")
except Exception as _e:
    print(f"[MongoDB] Not available ({_e}) — in-memory only")


# ── Startup: register ALL MCP tools ──────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    try:
        from mcp.tool_registry import ToolRegistry
        ToolRegistry.register_core_tools()
        ToolRegistry.register_video_tools()
        print("[Startup] All MCP tools registered ✓")
    except Exception as e:
        print(f"[Startup] Tool registration warning: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_dir(run_id: str) -> str:
    return os.path.join(RUNS_BASE, run_id)


def _load_json(path: str) -> Optional[dict]:
    try:
        if path and os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _db_upsert(run_id: str, data: dict):
    if _mongo_col is None:
        return
    try:
        _mongo_col.update_one({"run_id": run_id}, {"$set": data}, upsert=True)
    except Exception:
        pass


def _db_load(run_id: str) -> Optional[dict]:
    if _mongo_col is None:
        return None
    try:
        return _mongo_col.find_one({"run_id": run_id}, {"_id": 0})
    except Exception:
        return None


# ── Per-run message history ───────────────────────────────────────────────────
# Primary store: MongoDB $push into runs.messages array.
# Fallback (no Mongo): JSON file at run_dir/messages.json.

def _msg_push(run_id: str, role: str, text: str, **extra):
    """Append a chat message to the run's history."""
    from datetime import datetime
    msg = {"role": role, "text": text, "ts": datetime.utcnow().isoformat(), **extra}
    if _mongo_col is not None:
        try:
            _mongo_col.update_one(
                {"run_id": run_id},
                {"$push": {"messages": msg}},
                upsert=True,
            )
            return
        except Exception:
            pass
    # File fallback
    _msg_file_append(run_id, msg)


def _msg_list(run_id: str) -> List[Dict[str, Any]]:
    """Return all messages for a run, oldest first."""
    if _mongo_col is not None:
        try:
            doc = _mongo_col.find_one({"run_id": run_id}, {"_id": 0, "messages": 1})
            if doc:
                return doc.get("messages", [])
        except Exception:
            pass
    return _msg_file_load(run_id)


def _msg_file_path(run_id: str) -> str:
    return os.path.join(_run_dir(run_id), "messages.json")


def _msg_file_load(run_id: str) -> List[Dict[str, Any]]:
    p = _msg_file_path(run_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return []


def _msg_file_append(run_id: str, msg: dict):
    msgs = _msg_file_load(run_id)
    msgs.append(msg)
    try:
        os.makedirs(_run_dir(run_id), exist_ok=True)
        with open(_msg_file_path(run_id), "w") as f:
            json.dump(msgs, f, indent=2)
    except Exception:
        pass


async def _broadcast(run_id: str, data: dict):
    """Send a JSON message to all connected WebSocket clients for this run."""
    dead = []
    for ws in WS_CLIENTS.get(run_id, []):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        WS_CLIENTS.get(run_id, []).remove(ws)


async def _emit(run_id: str, phase: int, status: str, progress: int, message: str = ""):
    """Broadcast a phase-progress event and print it for server-side logging."""
    print(f"  [Phase {phase}] {status.upper():8s} {progress:3d}%  {message}")
    await _broadcast(run_id, {
        "phase": phase,
        "status": status,
        "progress": progress,
        "message": message,
        "ts": datetime.utcnow().isoformat(),
    })


def _hitl_key(run_id: str, phase: int) -> str:
    return f"{run_id}_{phase}"


def _cancel_hitl_for_run(run_id: str):
    """Unblock all HITL waits for a run and mark them as cancelled."""
    for key in list(HITL_EVENTS.keys()):
        if key.startswith(f"{run_id}_"):
            HITL_CANCELLED.add(key)
            HITL_EVENTS[key].set()


async def _hitl_wait(run_id: str, phase: int) -> bool:
    """
    Pause the pipeline and broadcast waiting_approval.
    Returns True if the user approved, False if rerun was requested.
    """
    key = _hitl_key(run_id, phase)
    evt = asyncio.Event()
    HITL_EVENTS[key] = evt
    await _emit(run_id, phase, "waiting_approval", 100, "Awaiting your approval to continue…")
    await evt.wait()
    HITL_EVENTS.pop(key, None)
    if key in HITL_CANCELLED:
        HITL_CANCELLED.discard(key)
        return False
    return True


def _make_phase_runner(fn, run_id: str, loop):
    """
    Wrap a phase function so that when it runs in the thread-pool executor
    it registers a progress callback.  Any agent that calls
    shared.utils.progress.report() will fire real WebSocket events.
    """
    def wrapped():
        from shared.utils.progress import set_callback, clear_callback

        def sync_cb(phase, progress, message):
            if loop.is_closed():
                return
            try:
                asyncio.run_coroutine_threadsafe(
                    _emit(run_id, phase, "running", progress, message),
                    loop,
                )
            except RuntimeError as e:
                print(f"[Progress] Emit scheduling failed (phase {phase}): {e}")

        set_callback(run_id, sync_cb)
        try:
            return fn()
        finally:
            clear_callback()
    return wrapped


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def _run_pipeline(run_id: str, prompt: str, style: str, duration: str, language: str):
    """
    Full Phase 1 → 2 → 3 pipeline with real per-step WebSocket progress events.
    Each phase function is wrapped so that shared.utils.progress.report() calls
    from inside agent nodes fire actual WebSocket events in real time.
    """
    loop = asyncio.get_running_loop()
    RUNS[run_id]["status"] = "running"
    _db_upsert(run_id, {"status": "running"})

    print(f"\n{'='*60}")
    print(f"[Pipeline] Starting run {run_id}")
    print(f"  Prompt: {prompt[:60]}...")
    print(f"  Style: {style}  |  Duration: {duration}")
    print(f"{'='*60}")

    # ── Phase 1: Story & Script ──────────────────────────────
    try:
        await _emit(run_id, 1, "running", 2, "Starting story generation…")

        from agents.story_agent.agent import run_phase1

        result1 = await loop.run_in_executor(
            _executor,
            _make_phase_runner(
                lambda: run_phase1(prompt, provider=2, run_id=run_id, style=style, duration=duration, language=language),
                run_id, loop,
            ),
        )

        if result1.get("error"):
            raise RuntimeError(result1["error"])

        run_dir = result1.get("run_dir", _run_dir(run_id))
        RUNS[run_id]["run_dir"] = run_dir
        _db_upsert(run_id, {"status": "phase1_done", "run_dir": run_dir})
        _save_meta(run_id, {**RUNS[run_id], "status": "phase1_done"})
        await _emit(run_id, 1, "done", 100, "Story & script complete ✓")

    except Exception as e:
        err = f"Phase 1 failed: {e}"
        print(f"[Phase 1 ERROR] {traceback.format_exc()}")
        RUNS[run_id]["status"] = "error"
        RUNS[run_id]["error"] = err
        _db_upsert(run_id, {"status": "error", "error": err})
        await _emit(run_id, 1, "error", 0, err)
        return

    if not await _hitl_wait(run_id, 1):
        return

    # ── Phase 2: Audio ───────────────────────────────────────
    try:
        await _emit(run_id, 2, "running", 2, "Loading audio handoff…")

        run_dir = RUNS[run_id]["run_dir"]
        handoff_audio = _load_json(os.path.join(run_dir, "phase2_audio_handoff.json")) or {}

        from agents.audio_agent.agent import run_phase2

        result2 = await loop.run_in_executor(
            _executor,
            _make_phase_runner(
                lambda: run_phase2(handoff_audio, provider=4, run_dir=run_dir),
                run_id, loop,
            ),
        )

        _db_upsert(run_id, {
            "status": "phase2_done",
            "full_audio_path": result2.get("full_audio_path", ""),
        })
        await _emit(run_id, 2, "done", 100, "Audio pipeline complete ✓")

    except Exception as e:
        err = f"Phase 2 failed: {e}"
        print(f"[Phase 2 ERROR] {traceback.format_exc()}")
        RUNS[run_id]["status"] = "error"
        RUNS[run_id]["error"] = err
        _db_upsert(run_id, {"status": "error", "error": err})
        await _emit(run_id, 2, "error", 0, err)
        return

    if not await _hitl_wait(run_id, 2):
        return

    # ── Phase 3: Video ───────────────────────────────────────
    try:
        await _emit(run_id, 3, "running", 2, "Loading video handoff…")

        run_dir = RUNS[run_id]["run_dir"]
        handoff_video  = _load_json(os.path.join(run_dir, "phase3_video_handoff.json")) or {}
        timing_data    = _load_json(os.path.join(run_dir, "timing_manifest.json")) or {}
        timing_entries = timing_data.get("entries", [])

        from agents.video_agent.agent import run_phase3

        result3 = await loop.run_in_executor(
            _executor,
            _make_phase_runner(
                lambda: run_phase3(handoff_video, timing_entries, run_dir),
                run_id, loop,
            ),
        )

        final_video = result3.get("final_video_path", "")
        if not final_video or not os.path.exists(final_video):
            final_video = os.path.join(run_dir, "video", "final_video.mp4")

        RUNS[run_id]["final_video_path"] = final_video
        _db_upsert(run_id, {"status": "phase3_done", "final_video_path": final_video})
        await _emit(run_id, 3, "done", 100, "Video composition complete ✓")

    except Exception as e:
        err = f"Phase 3 failed: {e}"
        print(f"[Phase 3 ERROR] {traceback.format_exc()}")
        RUNS[run_id]["status"] = "error"
        RUNS[run_id]["error"] = err
        _db_upsert(run_id, {"status": "error", "error": err})
        await _emit(run_id, 3, "error", 0, err)
        return

    if not await _hitl_wait(run_id, 3):
        return

    # ── Phase 4: Finalize ────────────────────────────────────
    try:
        await _emit(run_id, 4, "running", 50, "Saving state snapshot…")
        from state_manager.snapshot import save_snapshot
        from state_manager.history import save_version as _save_v0
        _rdir = RUNS[run_id].get("run_dir", _run_dir(run_id))
        save_snapshot(run_id, _rdir)
        _save_v0(_rdir, label="Original")

        RUNS[run_id]["status"] = "done"
        _db_upsert(run_id, {
            "status": "done",
            "completed_at": datetime.utcnow().isoformat(),
            "final_video_path": RUNS[run_id].get("final_video_path", ""),
        })
        await _emit(run_id, 4, "done", 100, "Done! Your film is ready.")
        print(f"\n[Pipeline] Run {run_id} COMPLETE ✓")

    except Exception as e:
        print(f"[Finalize WARNING] {e}")
        RUNS[run_id]["status"] = "done"
        await _emit(run_id, 4, "done", 100, "Done!")


# ── Models ────────────────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    prompt: str
    style: str = "2D animated"
    duration: str = "medium"
    language: str = "English"


class EditRequest(BaseModel):
    instruction: str
    base_version: Optional[int] = None   # if set, restore this version before editing


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/runs")
async def create_run(body: CreateRunRequest, background_tasks: BackgroundTasks):
    from shared.utils.serializer import generate_run_id
    run_id = generate_run_id()

    RUNS[run_id] = {
        "run_id":     run_id,
        "status":     "pending",
        "prompt":     body.prompt,
        "style":      body.style,
        "duration":   body.duration,
        "language":   body.language,
        "created_at": datetime.utcnow().isoformat(),
    }
    _db_upsert(run_id, RUNS[run_id])

    # Create run directory and persist metadata so server restarts can recover
    os.makedirs(_run_dir(run_id), exist_ok=True)
    _save_meta(run_id, RUNS[run_id])

    background_tasks.add_task(
        _start_pipeline_bg, run_id, body.prompt, body.style, body.duration, body.language
    )
    return {"run_id": run_id, "status": "pending"}


async def _start_pipeline_bg(run_id, prompt, style, duration, language):
    """BackgroundTasks wrapper for the async pipeline."""
    await _run_pipeline(run_id, prompt, style, duration, language)


@app.websocket("/ws/{run_id}")
async def ws_progress(ws: WebSocket, run_id: str):
    await ws.accept()
    WS_CLIENTS.setdefault(run_id, []).append(ws)
    print(f"[WS] Client connected for run {run_id}  (total: {len(WS_CLIENTS[run_id])})")

    # Hydrate from disk/DB so reconnects after restart show correct status
    cur = _hydrate_run(run_id)
    if cur:
        # If run dir exists with output files, infer completed phases
        rdir = _run_dir(run_id)
        if cur.get("status") in ("unknown", "pending", "") and os.path.isdir(rdir):
            if _load_json(os.path.join(rdir, "timing_manifest.json")):
                cur["status"] = "phase2_done"
            elif _load_json(os.path.join(rdir, "script.json")):
                cur["status"] = "phase1_done"
        await ws.send_json({"type": "state", "status": cur.get("status", "unknown")})

    # Re-emit any live HITL approval waits so reconnecting clients see the correct state
    for _hk in list(HITL_EVENTS.keys()):
        if _hk.startswith(f"{run_id}_"):
            _hphase = int(_hk.rsplit("_", 1)[-1])
            await ws.send_json({
                "phase": _hphase, "status": "waiting_approval",
                "progress": 100, "message": "Awaiting your approval to continue…",
                "ts": datetime.utcnow().isoformat(),
            })

    try:
        while True:
            await asyncio.sleep(20)
            await ws.send_json({"type": "ping"})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if run_id in WS_CLIENTS and ws in WS_CLIENTS[run_id]:
            WS_CLIENTS[run_id].remove(ws)
        print(f"[WS] Client disconnected for run {run_id}")


@app.get("/api/runs")
async def list_runs():
    runs_list: List[dict] = []

    # 1. MongoDB
    if _mongo_col is not None:
        try:
            docs = list(_mongo_col.find({}, {"_id": 0}).sort("created_at", -1).limit(100))
            if docs:
                return {"runs": docs}
        except Exception:
            pass

    # 2. Local disk
    if os.path.isdir(RUNS_BASE):
        for run_id in sorted(os.listdir(RUNS_BASE), reverse=True):
            rdir = os.path.join(RUNS_BASE, run_id)
            if not os.path.isdir(rdir):
                continue
            mem = RUNS.get(run_id, {})
            story = _load_json(os.path.join(rdir, "story.json"))
            mp4   = _find_mp4(run_id)
            runs_list.append({
                "run_id":        run_id,
                "status":        mem.get("status", "done" if mp4 else "unknown"),
                "prompt":        mem.get("prompt") or (story.get("premise", "") if story else ""),
                "style":         mem.get("style", ""),
                "duration":      mem.get("duration", ""),
                "created_at":    mem.get("created_at", ""),
                "has_video":     bool(mp4),
                "video_url":     f"/api/runs/{run_id}/video" if mp4 else None,
                "thumbnail_url": _find_thumbnail(run_id),
            })

    # 3. In-memory runs not yet on disk
    for run_id, data in RUNS.items():
        if not any(r["run_id"] == run_id for r in runs_list):
            runs_list.append({
                "run_id":     run_id,
                "status":     data.get("status", "pending"),
                "prompt":     data.get("prompt", ""),
                "style":      data.get("style", ""),
                "duration":   data.get("duration", ""),
                "created_at": data.get("created_at", ""),
                "has_video":  False,
                "video_url":  None,
            })

    return {"runs": runs_list}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    rdir = _run_dir(run_id)
    mem  = RUNS.get(run_id) or _db_load(run_id) or {}
    if not mem and not os.path.isdir(rdir):
        raise HTTPException(404, "Run not found")
    if mem and run_id not in RUNS:
        RUNS[run_id] = mem

    story      = _load_json(os.path.join(rdir, "story.json"))
    characters = _load_json(os.path.join(rdir, "characters.json"))
    script     = _load_json(os.path.join(rdir, "script.json"))
    timing     = _load_json(os.path.join(rdir, "timing_manifest.json"))
    handoff    = _load_json(os.path.join(rdir, "phase3_video_handoff.json"))
    mp4        = _find_mp4(run_id)

    from state_manager.history import list_versions
    versions = list_versions(rdir) if os.path.isdir(rdir) else []
    for v in versions:
        vp = v.get("video_path", "")
        v["video_url"] = (
            f"/api/runs/{run_id}/versions/{v['version']}/video"
            if vp and os.path.exists(vp) else None
        )

    return {
        "run_id":     run_id,
        "status":     mem.get("status", "unknown"),
        "prompt":     mem.get("prompt", ""),
        "style":      mem.get("style") or (handoff.get("style") if handoff else ""),
        "duration":   mem.get("duration", ""),
        "created_at": mem.get("created_at", ""),
        "error":      mem.get("error"),
        "story":      story,
        "characters": characters,
        "script":     script,
        "timing":     timing,
        "has_video":  bool(mp4),
        "video_url":  f"/api/runs/{run_id}/video" if mp4 else None,
        "versions":   versions,
    }


@app.get("/api/runs/{run_id}/video")
async def serve_video(run_id: str):
    mp4 = _find_mp4(run_id)
    if not mp4:
        raise HTTPException(404, "Video not ready yet")
    return FileResponse(mp4, media_type="video/mp4", filename=f"{run_id}.mp4")


@app.get("/api/runs/{run_id}/images")
async def list_images(run_id: str):
    """Return all generated image paths for a run, grouped by scene."""
    images_dir = os.path.join(_run_dir(run_id), "images")
    if not os.path.isdir(images_dir):
        return {"images": []}

    result = []
    for fname in sorted(os.listdir(images_dir)):
        if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            result.append({
                "filename": fname,
                "url": f"/api/runs/{run_id}/images/{fname}",
                # derive scene_id from filename pattern: scene_1_wide.png
                "scene_id": "_".join(fname.split("_")[:2]) if "_" in fname else fname,
                "frame_type": fname.split("_")[2].split(".")[0] if fname.count("_") >= 2 else "wide",
            })
    return {"images": result}


@app.get("/api/runs/{run_id}/audio")
async def list_audio(run_id: str):
    """
    List all audio files for a run.
    Returns:
      mixed — one entry per scene (scene_N_mixed.mp3)
      lines — per-character TTS lines (character_name_emotion_hash.mp3)
      files — alias for mixed (backward compat)
    """
    audio_dir = os.path.join(_run_dir(run_id), "audio")
    if not os.path.isdir(audio_dir):
        return {"mixed": [], "lines": [], "files": []}

    mixed, lines = [], []
    for root, _dirs, fnames in os.walk(audio_dir):
        rel = os.path.relpath(root, audio_dir).replace("\\", "/")
        is_mixed = "mixed" in rel
        for fname in sorted(fnames):
            if not fname.lower().endswith((".mp3", ".wav")):
                continue
            url = f"/api/runs/{run_id}/audio/{fname}"
            if is_mixed:
                scene_id = fname.replace("_mixed.mp3", "").replace("_mixed.wav", "")
                mixed.append({"filename": fname, "url": url, "scene_id": scene_id})
            else:
                base  = fname.rsplit(".", 1)[0]          # strip extension
                parts = base.rsplit("_", 2)              # ['char name', 'emotion', 'hash']
                char_name = parts[0].title() if len(parts) >= 3 else base
                emotion   = parts[1]          if len(parts) >= 3 else ""
                scene_id  = rel               if rel != "."        else "unknown"
                lines.append({
                    "filename":       fname,
                    "url":            url,
                    "scene_id":       scene_id,
                    "character_name": char_name,
                    "emotion":        emotion,
                })

    return {"mixed": mixed, "lines": lines, "files": mixed}


@app.get("/api/runs/{run_id}/images/{filename}")
async def serve_image(run_id: str, filename: str):
    images_dir = os.path.join(_run_dir(run_id), "images")
    fpath = os.path.join(images_dir, filename)
    if not os.path.exists(fpath):
        raise HTTPException(404, f"Image {filename} not found")
    ext = filename.rsplit(".", 1)[-1].lower()
    mt = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
    return FileResponse(fpath, media_type=mt)


@app.get("/api/runs/{run_id}/audio/{filename}")
async def serve_audio(run_id: str, filename: str):
    rdir  = _run_dir(run_id)
    # Search recursively in run_dir/audio/
    for root, _, files in os.walk(os.path.join(rdir, "audio")):
        if filename in files:
            return FileResponse(
                os.path.join(root, filename),
                media_type="audio/mpeg",
            )
    raise HTTPException(404, f"Audio file {filename} not found")


@app.get("/api/runs/{run_id}/messages")
async def get_messages(run_id: str):
    return {"messages": _msg_list(run_id)}


@app.post("/api/runs/{run_id}/edit")
async def edit_run(run_id: str, body: EditRequest, background_tasks: BackgroundTasks):
    rdir = _run_dir(run_id)
    if not os.path.isdir(rdir) and run_id not in RUNS:
        raise HTTPException(404, "Run not found")

    from state_manager.history import save_version, restore_version
    # If editing from a specific version, restore it first so the edit
    # branches from that point rather than from the latest live state
    if body.base_version is not None:
        restore_version(rdir, body.base_version)

    version_num = save_version(rdir, label=body.instruction[:40])

    from agents.edit_agent.intent_classifier import classify_intent
    intent = classify_intent(body.instruction, rdir)

    # Persist user message immediately
    _msg_push(run_id, "user", body.instruction)

    background_tasks.add_task(_execute_edit_bg, run_id, intent, body.instruction, version_num)

    return {
        "intent":        intent,
        "version_saved": version_num,
        "message":       f"Running edit: {intent.get('type', 'unknown')}",
    }


async def _execute_edit_bg(run_id: str, intent: dict, instruction: str, version_num: int):
    loop = asyncio.get_event_loop()
    intent_type = intent.get("type", "edit")
    target      = intent.get("target", "all")
    await _emit(run_id, 5, "running", 0, f"Processing edit: {instruction}")
    try:
        from agents.edit_agent.agent import run_edit
        # Wire progress callback so sub-phase (Phase 2/3) events reach the WebSocket
        wrapped = _make_phase_runner(
            lambda: run_edit(run_id, intent, _run_dir(run_id), instruction),
            run_id, loop,
        )
        result = await loop.run_in_executor(_executor, wrapped)
        if result.get("new_video"):
            RUNS.setdefault(run_id, {})["final_video_path"] = result["new_video"]
        ai_text = (
            f"Intent: **{intent_type}** → target: {target}. "
            f"Edit applied successfully. Saved as v{version_num}."
        )
        _msg_push(run_id, "ai", ai_text, intent_type=intent_type, version=version_num)
        await _emit(run_id, 5, "done", 100, "Edit applied ✓")
    except Exception as e:
        err_text = f"Edit failed ({intent_type}): {e}"
        _msg_push(run_id, "ai", err_text, intent_type=intent_type, version=version_num, error=True)
        await _emit(run_id, 5, "error", 0, f"Edit failed: {e}")


@app.get("/api/runs/{run_id}/versions")
async def get_versions(run_id: str):
    from state_manager.history import list_versions
    rdir = _run_dir(run_id)
    versions = list_versions(rdir)
    # Attach a servable video_url for each version that has a recorded video
    for v in versions:
        vp = v.get("video_path", "")
        v["video_url"] = (
            f"/api/runs/{run_id}/versions/{v['version']}/video"
            if vp and os.path.exists(vp) else None
        )
    return {"versions": versions}


@app.get("/api/runs/{run_id}/versions/{version}/video")
async def serve_version_video(run_id: str, version: int):
    """Serve the video for a version — prefers the local snapshot copy."""
    rdir = _run_dir(run_id)
    # Check for video stored inside the version folder first (new approach)
    local_copy = os.path.join(rdir, "versions", f"v{version}", "video", "final_video.mp4")
    if os.path.exists(local_copy):
        return FileResponse(local_copy, media_type="video/mp4", filename=f"{run_id}_v{version}.mp4")
    # Fall back to the recorded path (old snapshots without local copy)
    from state_manager.history import get_version_meta
    meta = get_version_meta(rdir, version)
    if not meta:
        raise HTTPException(404, f"Version {version} not found")
    vp = meta.get("video_path", "")
    if not vp or not os.path.exists(vp):
        raise HTTPException(404, f"Video for version {version} not found on disk")
    return FileResponse(vp, media_type="video/mp4", filename=f"{run_id}_v{version}.mp4")


@app.get("/api/runs/{run_id}/versions/{version}/audio/{filepath:path}")
async def serve_version_audio(run_id: str, version: int, filepath: str):
    """Serve an audio file from a version snapshot."""
    if ".." in filepath:
        raise HTTPException(400, "Invalid path")
    audio_path = os.path.join(_run_dir(run_id), "versions", f"v{version}", "audio", filepath)
    if not os.path.exists(audio_path):
        raise HTTPException(404, "Audio file not found in this version")
    ext = os.path.splitext(filepath)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    return FileResponse(audio_path, media_type=media_type)


@app.get("/api/runs/{run_id}/versions/{version}/images/{filename}")
async def serve_version_image(run_id: str, version: int, filename: str):
    """Serve a snapshotted image from versions/vN/images/."""
    # Basic path safety: only allow simple filenames
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    img_path = os.path.join(_run_dir(run_id), "versions", f"v{version}", "images", filename)
    if not os.path.exists(img_path):
        raise HTTPException(404, f"Image not found in version {version}")
    ext = os.path.splitext(filename)[1].lower()
    media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    return FileResponse(img_path, media_type=media_type)


@app.get("/api/runs/{run_id}/versions/{version}/assets")
async def get_version_assets(run_id: str, version: int):
    """Return the full asset snapshot for a version: images, characters, script."""
    rdir = _run_dir(run_id)
    ver_dir = os.path.join(rdir, "versions", f"v{version}")
    if not os.path.isdir(ver_dir):
        raise HTTPException(404, f"Version {version} not found")

    from state_manager.history import get_version_meta
    meta = get_version_meta(rdir, version) or {}

    # Images in snapshot
    import glob as _glob
    img_dir = os.path.join(ver_dir, "images")
    images = []
    for img_path in sorted(_glob.glob(os.path.join(img_dir, "*.png")) +
                           _glob.glob(os.path.join(img_dir, "*.jpg"))):
        fname = os.path.basename(img_path)
        # Parse scene_id and frame_type from filename e.g. scene_1_wide.png
        parts = fname.rsplit(".", 1)[0].split("_")
        scene_id = "_".join(parts[:2]) if len(parts) >= 3 else parts[0]
        frame_type = parts[2] if len(parts) >= 3 else ""
        images.append({
            "filename":   fname,
            "scene_id":   scene_id,
            "frame_type": frame_type,
            "url": f"/api/runs/{run_id}/versions/{version}/images/{fname}",
        })

    # Characters and script from snapshot JSON
    characters = _load_json(os.path.join(ver_dir, "characters.json"))
    script     = _load_json(os.path.join(ver_dir, "script.json"))
    story      = _load_json(os.path.join(ver_dir, "story.json"))

    # Video: prefer local snapshot copy, fall back to recorded path
    local_video = os.path.join(ver_dir, "video", "final_video.mp4")
    has_video = os.path.exists(local_video) or (
        meta.get("video_path") and os.path.exists(meta.get("video_path", ""))
    )

    # Audio: list mixed per-scene files and full audio track from snapshot
    audio_files = []
    audio_dir = os.path.join(ver_dir, "audio")
    if os.path.isdir(audio_dir):
        full_track = os.path.join(audio_dir, "full_audio.mp3")
        if os.path.exists(full_track):
            audio_files.append({
                "type": "full",
                "filename": "full_audio.mp3",
                "url": f"/api/runs/{run_id}/versions/{version}/audio/full_audio.mp3",
            })
        mixed_dir = os.path.join(audio_dir, "mixed")
        if os.path.isdir(mixed_dir):
            for f in sorted(os.listdir(mixed_dir)):
                if f.endswith(".mp3"):
                    audio_files.append({
                        "type": "mixed",
                        "filename": f,
                        "url": f"/api/runs/{run_id}/versions/{version}/audio/mixed/{f}",
                    })

    return {
        "version":    version,
        "label":      meta.get("label", f"v{version}"),
        "saved_at":   meta.get("saved_at", ""),
        "video_url":  f"/api/runs/{run_id}/versions/{version}/video" if has_video else None,
        "images":     images,
        "characters": characters,
        "script":     script,
        "story":      story,
        "audio":      audio_files,
    }


@app.post("/api/runs/{run_id}/revert/{version}")
async def revert_version(run_id: str, version: int):
    from state_manager.history import restore_version, get_version_meta, truncate_after
    rdir = _run_dir(run_id)
    restore_version(rdir, version)
    truncate_after(rdir, version)   # delete all versions newer than this one
    meta = get_version_meta(rdir, version) or {}
    label = meta.get("label", f"v{version}")
    vp = meta.get("video_path", "")
    version_video_url = (
        f"/api/runs/{run_id}/versions/{version}/video"
        if vp and os.path.exists(vp) else None
    )
    current_mp4 = _find_mp4(run_id)
    _msg_push(
        run_id, "ai",
        f"Reverted to v{version}: \"{label}\". Script, characters, and audio config restored.",
        action="revert", version=version,
    )
    return {
        "message":           f"Reverted to version {version}",
        "version":           version,
        "version_video_url": version_video_url,
        "current_video_url": f"/api/runs/{run_id}/video" if current_mp4 else None,
    }


@app.post("/api/runs/{run_id}/approve/{phase}")
async def approve_phase(run_id: str, phase: int):
    """Signal that the user approved a HITL checkpoint — resumes the waiting pipeline."""
    key = _hitl_key(run_id, phase)
    evt = HITL_EVENTS.get(key)
    if evt:
        evt.set()
        return {"message": f"Phase {phase} approved — pipeline continuing"}
    return {"message": "No pending approval found for this phase"}


@app.post("/api/runs/{run_id}/rerun/{phase}")
async def rerun_phase(run_id: str, phase: int, background_tasks: BackgroundTasks):
    if phase not in (1, 2, 3):
        raise HTTPException(400, "Phase must be 1, 2, or 3")

    rdir = _run_dir(run_id)
    if run_id not in RUNS and not os.path.isdir(rdir):
        raise HTTPException(404, "Run not found")

    # Recover prompt/style/etc. from disk or MongoDB if server was restarted
    run = _hydrate_run(run_id)
    RUNS.setdefault(run_id, run)
    RUNS[run_id]["status"] = "running"
    RUNS[run_id]["run_dir"] = rdir

    prompt   = run.get("prompt", "")
    style    = run.get("style", "2D animated")
    duration = run.get("duration", "medium")
    language = run.get("language", "English")

    _cancel_hitl_for_run(run_id)
    background_tasks.add_task(_rerun_phase_bg, run_id, phase, prompt, style, duration, language)
    return {"message": f"Re-running from phase {phase}", "run_id": run_id}


async def _rerun_phase_bg(run_id: str, from_phase: int, prompt: str, style: str, duration: str, language: str):
    loop = asyncio.get_running_loop()
    run_dir = _run_dir(run_id)
    RUNS.setdefault(run_id, {})["run_dir"] = run_dir

    if from_phase <= 1:
        try:
            await _emit(run_id, 1, "running", 2, "Re-running story generation…")
            from agents.story_agent.agent import run_phase1
            result1 = await loop.run_in_executor(
                _executor,
                _make_phase_runner(
                    lambda: run_phase1(prompt, provider=2, run_id=run_id, style=style, duration=duration, language=language),
                    run_id, loop,
                ),
            )
            if result1.get("error"):
                raise RuntimeError(result1["error"])
            run_dir = result1.get("run_dir", run_dir)
            RUNS[run_id]["run_dir"] = run_dir
            await _emit(run_id, 1, "done", 100, "Story & script complete ✓")
        except Exception as e:
            await _emit(run_id, 1, "error", 0, f"Phase 1 failed: {e}")
            RUNS[run_id]["status"] = "error"
            return
        if not await _hitl_wait(run_id, 1):
            return

    if from_phase <= 2:
        try:
            await _emit(run_id, 2, "running", 2, "Re-running audio generation…")
            handoff_audio = _load_json(os.path.join(run_dir, "phase2_audio_handoff.json")) or {}
            handoff_audio["language"] = language  # inject in case handoff predates language support
            from agents.audio_agent.agent import run_phase2
            result2 = await loop.run_in_executor(
                _executor,
                _make_phase_runner(
                    lambda: run_phase2(handoff_audio, provider=4, run_dir=run_dir),
                    run_id, loop,
                ),
            )
            _db_upsert(run_id, {"status": "phase2_done", "full_audio_path": result2.get("full_audio_path", "")})
            await _emit(run_id, 2, "done", 100, "Audio pipeline complete ✓")
        except Exception as e:
            await _emit(run_id, 2, "error", 0, f"Phase 2 failed: {e}")
            RUNS[run_id]["status"] = "error"
            return
        if not await _hitl_wait(run_id, 2):
            return

    if from_phase <= 3:
        try:
            await _emit(run_id, 3, "running", 2, "Re-running video composition…")
            handoff_video  = _load_json(os.path.join(run_dir, "phase3_video_handoff.json")) or {}
            timing_data    = _load_json(os.path.join(run_dir, "timing_manifest.json")) or {}
            timing_entries = timing_data.get("entries", [])
            from agents.video_agent.agent import run_phase3
            result3 = await loop.run_in_executor(
                _executor,
                _make_phase_runner(
                    lambda: run_phase3(handoff_video, timing_entries, run_dir),
                    run_id, loop,
                ),
            )
            final_video = result3.get("final_video_path", "")
            if not final_video or not os.path.exists(final_video):
                final_video = os.path.join(run_dir, "video", "final_video.mp4")
            RUNS[run_id]["final_video_path"] = final_video
            _db_upsert(run_id, {"status": "phase3_done", "final_video_path": final_video})
            await _emit(run_id, 3, "done", 100, "Video composition complete ✓")
        except Exception as e:
            await _emit(run_id, 3, "error", 0, f"Phase 3 failed: {e}")
            RUNS[run_id]["status"] = "error"
            return
        if not await _hitl_wait(run_id, 3):
            return

    try:
        await _emit(run_id, 4, "running", 50, "Saving state snapshot…")
        from state_manager.snapshot import save_snapshot
        save_snapshot(run_id, run_dir)
        RUNS[run_id]["status"] = "done"
        _db_upsert(run_id, {"status": "done", "completed_at": datetime.utcnow().isoformat()})
        await _emit(run_id, 4, "done", 100, "Done! Your film is ready.")
    except Exception as e:
        print(f"[Rerun Finalize WARNING] {e}")
        RUNS[run_id]["status"] = "done"
        await _emit(run_id, 4, "done", 100, "Done!")


@app.get("/health")
def health():
    from mcp.tool_registry import ToolRegistry
    return {
        "status": "ok",
        "tools":  list(ToolRegistry._tools.keys()),
        "runs":   len(RUNS),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _save_meta(run_id: str, data: dict):
    """Persist prompt/style/duration/language to disk so restarts can recover them."""
    try:
        path = os.path.join(_run_dir(run_id), "meta.json")
        os.makedirs(_run_dir(run_id), exist_ok=True)
        with open(path, "w") as f:
            json.dump({k: data.get(k, "") for k in ("run_id", "prompt", "style", "duration", "language", "created_at", "status")}, f, indent=2)
    except Exception as e:
        print(f"[meta] Failed to save meta.json: {e}")


def _hydrate_run(run_id: str) -> dict:
    """
    Ensure RUNS[run_id] exists with prompt/style/etc.
    Priority: existing RUNS entry → MongoDB → disk meta.json → empty defaults.
    """
    existing = RUNS.get(run_id)
    if existing and existing.get("prompt"):
        return existing

    # Try MongoDB
    db_doc = _db_load(run_id)
    if db_doc and db_doc.get("prompt"):
        RUNS[run_id] = db_doc
        return db_doc

    # Try disk meta.json
    meta = _load_json(os.path.join(_run_dir(run_id), "meta.json"))
    if meta:
        merged = {**(RUNS.get(run_id) or {}), **meta}
        RUNS[run_id] = merged
        return merged

    # Nothing found — return whatever partial data we have
    return RUNS.get(run_id, {"run_id": run_id})


def _find_thumbnail(run_id: str) -> Optional[str]:
    """Return URL of the first available generated image for a run (for gallery cards)."""
    images_dir = os.path.join(_run_dir(run_id), "images")
    if not os.path.isdir(images_dir):
        return None
    for fname in sorted(os.listdir(images_dir)):
        if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return f"/api/runs/{run_id}/images/{fname}"
    return None


def _find_mp4(run_id: str) -> Optional[str]:
    """Find the final MP4 for a run (checks several possible locations)."""
    rdir = _run_dir(run_id)
    mem  = RUNS.get(run_id, {})

    # 1. In-memory path stored after Phase 3
    fp = mem.get("final_video_path", "")
    if fp and os.path.exists(fp):
        return fp

    # 2. Standard output location from subtitle_tool
    candidates = [
        os.path.join(rdir, "video", "final_video.mp4"),
        os.path.join(rdir, "video", "audio_video.mp4"),
        os.path.join(rdir, "video", "silent_video.mp4"),
        os.path.join(rdir, "final_video.mp4"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # 3. Any .mp4 inside the run dir
    for root, _, files in os.walk(rdir):
        for f in files:
            if f.endswith(".mp4"):
                return os.path.join(root, f)

    return None


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
