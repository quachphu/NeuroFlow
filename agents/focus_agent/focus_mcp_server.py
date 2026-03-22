from fastmcp import FastMCP
from datetime import datetime, timedelta
import json

mcp = FastMCP("NeuroFlowFocus")

sessions = {}
captured_thoughts = []
history = []


@mcp.tool()
def start_session(duration_minutes: int = 15, task_name: str = "") -> str:
    """Start a focus session with a timer. Default 15 min for ADHD-friendly sessions."""
    session_id = f"s_{datetime.now().strftime('%H%M%S')}"
    sessions[session_id] = {
        "started": datetime.now().isoformat(),
        "duration": duration_minutes,
        "task": task_name,
        "end_time": (datetime.now() + timedelta(minutes=duration_minutes)).isoformat(),
        "status": "active",
    }
    return json.dumps({
        "session_id": session_id,
        "duration": duration_minutes,
        "task": task_name,
        "message": f"Focus session started — {duration_minutes} minutes on '{task_name}'.",
    })


@mcp.tool()
def capture_thought(thought: str) -> str:
    """Save a distracting thought without breaking focus. Returned after session ends."""
    captured_thoughts.append({
        "thought": thought,
        "time": datetime.now().isoformat(),
    })
    return json.dumps({
        "saved": True,
        "total_captured": len(captured_thoughts),
        "message": f"Thought saved. You have {len(captured_thoughts)} captured thought(s). Back to focus.",
    })


@mcp.tool()
def get_captured_thoughts() -> str:
    """Get any thoughts captured during the current session."""
    return json.dumps({
        "thoughts": [t["thought"] for t in captured_thoughts],
        "count": len(captured_thoughts),
    })


@mcp.tool()
def end_session(session_id: str, rating: int = 3) -> str:
    """End a focus session with a 1-5 rating. Returns stats and captured thoughts."""
    if session_id not in sessions:
        active = list(sessions.keys())
        if active:
            session_id = active[-1]
        else:
            return json.dumps({"error": "No active session found"})

    session = sessions.pop(session_id)
    duration = session["duration"]

    if rating <= 2:
        next_dur = max(5, duration - 5)
    elif rating >= 4:
        next_dur = min(45, duration + 5)
    else:
        next_dur = duration

    entry = {
        "duration": duration,
        "rating": rating,
        "task": session["task"],
        "time": datetime.now().isoformat(),
    }
    history.append(entry)

    thoughts = [t["thought"] for t in captured_thoughts]
    captured_thoughts.clear()

    return json.dumps({
        "duration": duration,
        "rating": rating,
        "sessions_today": len(history),
        "total_focus_min": sum(h["duration"] for h in history),
        "avg_rating": round(sum(h["rating"] for h in history) / len(history), 1),
        "suggested_next_duration": next_dur,
        "captured_thoughts": thoughts,
    })


@mcp.tool()
def get_focus_stats() -> str:
    """Get today's focus statistics."""
    if not history:
        return json.dumps({
            "sessions_today": 0,
            "total_focus_min": 0,
            "message": "No sessions yet today. Ready when you are.",
        })
    return json.dumps({
        "sessions_today": len(history),
        "total_focus_min": sum(h["duration"] for h in history),
        "avg_rating": round(sum(h["rating"] for h in history) / len(history), 1),
        "ratings_trend": [h["rating"] for h in history],
        "tasks_worked_on": [h["task"] for h in history],
    })
