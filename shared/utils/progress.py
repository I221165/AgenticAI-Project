"""
Thread-safe progress reporter.
Agents import `report()` to emit progress that the backend forwards to WebSocket.
The backend calls `set_callback(run_id, fn)` before launching each phase thread.

Uses a global dict keyed by thread-ID instead of threading.local() to avoid the
double-import problem where two import paths create separate _local instances.
"""

import threading

_lock = threading.Lock()
_thread_callbacks: dict = {}   # thread_id -> callable(phase, progress, message)


def set_callback(run_id: str, callback):
    """Call from inside the phase thread (before running any agent work)."""
    tid = threading.get_ident()
    with _lock:
        _thread_callbacks[tid] = callback


def clear_callback():
    """Call when the phase is done to free the slot."""
    tid = threading.get_ident()
    with _lock:
        _thread_callbacks.pop(tid, None)


def report(phase: int, progress: int, message: str):
    """
    Call from inside any agent node to emit a real-time progress event.
    Prints to terminal (always) and fires the registered callback if one exists
    for the current thread.
    """
    print(f"  [Phase {phase}] {progress:3d}%  {message}")
    tid = threading.get_ident()
    with _lock:
        cb = _thread_callbacks.get(tid)
    if cb:
        try:
            cb(phase, progress, message)
        except Exception as e:
            print(f"  [Progress] callback error: {e}")
