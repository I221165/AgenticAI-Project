# StoryForge AI — Agentic Animated Video Generator

An end-to-end multi-agent pipeline that transforms a one-line text prompt into a fully composed animated short film, with an AI-powered editing studio for iterative post-production.

## Technology Stack

| Layer | Technology |
|---|---|
| LLM / Agent Framework | LangChain + LangGraph (StateGraph + MemorySaver) |
| LLM Provider | Groq (Llama 3.1 8B / 70B) |
| Image Generation | Pollinations.ai (free, no key required) |
| Text-to-Speech | Edge-TTS (Microsoft Neural, free) / ElevenLabs |
| Background Music | Local BGM assets (MP3) |
| Video Composition | FFmpeg |
| Backend API | FastAPI + WebSocket (real-time progress) |
| Database | MongoDB (optional; falls back to local JSON files) |
| Frontend | React + Vite + Tailwind CSS |
| Testing | pytest (113 unit tests across all 5 phases) |

## Project Structure

```
├── agents/
│   ├── story_agent/      # Phase 1 — story, characters, script generation
│   ├── audio_agent/      # Phase 2 — TTS, BGM, timing manifest
│   ├── video_agent/      # Phase 3 — image gen, Ken Burns animation, FFmpeg
│   └── edit_agent/       # Phase 5 — intent classifier + LangGraph edit agent
│       └── tests/        # 51 unit tests for the edit intent classifier
├── backend/
│   └── app.py            # FastAPI server — all REST + WebSocket endpoints
├── frontend/
│   └── src/pages/StudioPage.jsx  # Full editing studio UI
├── mcp/                  # Internal Model Context Protocol tool layer
│   ├── tool_registry.py
│   └── tools/            # image_gen, tts, bgm, ffmpeg, compositor, subtitle…
├── state_manager/
│   └── history.py        # Version snapshots — save / list / restore
├── shared/
│   └── schemas/          # Pydantic schemas (GlobalState, Character, Scene…)
├── tests/
│   └── unit/             # 62 unit tests for Phases 1–4
├── conftest.py           # pytest sys.path fix (local mcp/ takes precedence)
├── requirements.txt
└── .env.example
```

## Prerequisites

- Python 3.10–3.12 (3.13 works with the audioop-lts shim)
- Node.js 18+ and npm
- FFmpeg installed and on PATH — download from https://ffmpeg.org/download.html
- MongoDB (optional — the system works without it using local JSON files)

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd "AgenticAI Project/Agentic Project/Agentic Project"
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here   # optional
MONGO_URI=mongodb://localhost:27017/              # optional
```

Only `GROQ_API_KEY` is required for the full pipeline. Pollinations.ai (image generation) and Edge-TTS (voice) are free and need no key.

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Start the backend

```bash
python start_backend.py
# or directly:
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at http://localhost:8000

### Start the frontend (separate terminal)

```bash
cd frontend
npm run dev
```

The studio UI will be available at http://localhost:5173

## Pipeline Phases

| Phase | What it does |
|---|---|
| **Phase 1 — Story Agent** | Generates story arc, character roster, and scene script from a text prompt using LangGraph + Groq LLM |
| **Phase 2 — Audio Agent** | Assigns voices per character, runs TTS (Edge-TTS/ElevenLabs), selects BGM, builds timing manifest |
| **Phase 3 — Video Agent** | Generates wide/mid/close keyframes per scene (Pollinations.ai), applies Ken Burns animation, composites with FFmpeg, syncs audio, burns subtitles |
| **Phase 4 — API + Studio** | FastAPI backend exposes all pipeline controls; React StudioPage provides real-time progress, asset browser, and version history |
| **Phase 5 — Edit Agent** | LangGraph agent with MemorySaver classifies 12 intent types (voice, style, filter, speed, brightness, transitions, etc.) and applies targeted edits with full version control |

## Running Tests

```bash
# All 113 unit tests
pytest tests/unit/ agents/edit_agent/tests/ -v

# Phase 1 tests only (story/character/script agent helpers)
pytest tests/unit/test_phase1_agents.py -v

# Phase 2 tests only (audio agent + voice assignment)
pytest tests/unit/test_phase2_audio.py -v

# Phase 3 tests only (video agent durations + serialization)
pytest tests/unit/test_phase3_video.py -v

# Phase 4 tests only (API helpers + version history)
pytest tests/unit/test_phase4_api.py -v

# Phase 5 tests only (edit intent classifier — 51 tests)
pytest agents/edit_agent/tests/test_intent_classifier.py -v
```

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runs` | Create a new run and start the pipeline |
| `WS` | `/ws/{run_id}` | Real-time progress stream |
| `GET` | `/api/runs` | List all past runs |
| `GET` | `/api/runs/{run_id}` | Full run state (story, characters, script, video) |
| `GET` | `/api/runs/{run_id}/video` | Stream the final MP4 |
| `POST` | `/api/runs/{run_id}/edit` | Submit an AI edit instruction |
| `GET` | `/api/runs/{run_id}/messages` | Chat history for this run |
| `GET` | `/api/runs/{run_id}/versions` | Version history |
| `POST` | `/api/runs/{run_id}/revert/{v}` | Revert to a previous version |
| `GET` | `/api/runs/{run_id}/versions/{v}/assets` | Assets for a specific version snapshot |

## Edit Intent Types

The Phase 5 edit agent recognises 12 intent types:

| Intent | Example instruction |
|---|---|
| `voice_change` | "Make Ethan's voice deeper" |
| `scene_regen` | "Regenerate scene 3 in watercolor style" |
| `style_change` | "Switch to anime style" |
| `bgm_change` | "Use more intense music in scene 2" |
| `script_edit` | "Rewrite scene 4 so Ethan is angrier" |
| `subtitle_remove` | "Remove subtitles" |
| `speed_change` | "Speed up scene 2" |
| `brightness_filter` | "Make scene 1 a bit more bright" |
| `character_redesign` | "Give Ethan blue hair" |
| `filter_apply` | "Add a sepia filter to all scenes" |
| `transition_change` | "Use a dissolve transition between scenes" |
| `music_add` | "Add dramatic music to scene 4" |
