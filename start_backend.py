"""
Run from the project root:
  python start_backend.py

Or with the venv:
  venv\Scripts\python.exe start_backend.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import uvicorn

if __name__ == "__main__":
    print(f"[Server] Starting StoryForge AI backend")
    print(f"[Server] Root: {ROOT}")
    print(f"[Server] http://localhost:8000")
    print(f"[Server] Press Ctrl+C to stop\n")
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # keep False so background tasks don't get killed on reload
    )
