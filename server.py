import json
import os
import shutil
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="NeuroFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from agents.orchestrator.chat_protocol import (
    classify_intent, format_with_llm,
    TRANSCRIBE_FORMAT_PROMPT, EXPLAIN_FORMAT_PROMPT,
    REVIEW_FORMAT_PROMPT, OVERWHELM_FORMAT_PROMPT,
    SINGLE_FORMAT_PROMPT,
)
from agents.transcription_agent.transcription_mcp_server import (
    transcribe_audio, get_transcript, search_transcript,
)
from agents.calendar_agent.calendar_mcp_server import (
    get_events, get_free_blocks, get_upcoming_deadlines,
)
from agents.focus_agent.focus_mcp_server import (
    start_session, capture_thought, end_session, get_focus_stats,
)
from agents.canvas_agent.canvas_mcp_server import (
    get_courses, get_assignments, get_grades, get_syllabus,
)
from agents.profile_agent.profile_agent import DEFAULT_PROFILE

UPLOAD_DIR = os.path.join(
    os.path.dirname(__file__),
    "agents", "transcription_agent", "demo_audio",
)

_profile = dict(DEFAULT_PROFILE)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str
    agents_used: list[str]


class FocusStartRequest(BaseModel):
    duration_minutes: int = 0


class FocusEndRequest(BaseModel):
    rating: int = 3


def _extract_concept(query: str) -> str | None:
    markers = ["about", "say about", "explain", "clarify", "mean by"]
    lower = query.lower()
    for marker in markers:
        if marker in lower:
            idx = lower.index(marker) + len(marker)
            rest = query[idx:].strip().strip("?").strip('"').strip("'")
            if rest:
                return rest
    return None


def _extract_course(query: str) -> str | None:
    q = query.upper()
    if "CS170" in q or "CS 170" in q or "ALGORITHM" in q:
        return "CS170"
    if "CS105" in q or "CS 105" in q:
        return "CS105"
    if "EE120" in q or "EE 120" in q or "SIGNAL" in q or "SYSTEMS" in q:
        return "EE120"
    if "ECON" in q:
        return "ECON101"
    return None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    intent = classify_intent(req.message)
    agents_used = []
    response = ""

    if intent == "transcribe":
        agents_used = ["transcription", "canvas", "profile"]
        t_raw = transcribe_audio()
        t_data = json.loads(t_raw)

        full_transcript = t_data.get("transcript_preview", "")
        full_result = json.loads(get_transcript())
        if "transcript" in full_result:
            full_transcript = full_result["transcript"]

        course_id = _extract_course(req.message)
        if not course_id:
            course_id = _extract_course(full_transcript[:500]) or "CS170"
        c_raw = get_syllabus(course_id)
        c_data = json.loads(c_raw)

        prompt = TRANSCRIBE_FORMAT_PROMPT.format(
            grade_level=_profile["reading_grade_level"],
            chunk_size=_profile["chunk_size"],
            tone=_profile["tone"],
            exam_topics=", ".join(c_data.get("exam_topics", [])),
            transcript=full_transcript[:2000],
            course_data=c_raw,
        )
        response = format_with_llm(prompt, max_tokens=1200) or f"Transcript loaded ({t_data.get('word_count', '?')} words). Ask me about any concept!"

    elif intent == "explain":
        agents_used = ["transcription", "canvas", "profile"]
        concept = _extract_concept(req.message)
        search_raw = search_transcript(concept) if concept else get_transcript()

        course_id = _extract_course(req.message) or "CS170"
        c_raw = get_syllabus(course_id)

        prompt = EXPLAIN_FORMAT_PROMPT.format(
            grade_level=_profile["reading_grade_level"],
            tone=_profile["tone"],
            query=req.message,
            transcript_data=search_raw,
            course_data=c_raw,
            profile_data=json.dumps(_profile),
        )
        response = format_with_llm(prompt) or search_raw

    elif intent == "review":
        agents_used = ["calendar", "focus", "transcription", "profile"]
        today = datetime.now().strftime("%Y-%m-%d")
        cal_raw = get_free_blocks(today)
        focus_raw = get_focus_stats()
        t_raw = get_transcript()

        prompt = REVIEW_FORMAT_PROMPT.format(
            tone=_profile["tone"],
            grade_level=_profile["reading_grade_level"],
            calendar_data=cal_raw,
            focus_data=focus_raw,
            transcript_data=t_raw,
            profile_data=json.dumps(_profile),
            query=req.message,
        )
        response = format_with_llm(prompt, max_tokens=1000) or "Ready to review! What topic should we start with?"

    elif intent == "schedule":
        agents_used = ["calendar"]
        today = datetime.now().strftime("%Y-%m-%d")
        response_data = get_events(today)
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response_data)
        response = format_with_llm(prompt) or response_data

    elif intent == "focus":
        agents_used = ["focus"]
        query_lower = req.message.lower()
        if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
            response = end_session(3)
        elif any(kw in query_lower for kw in ["stat", "how", "progress"]):
            response = get_focus_stats()
        else:
            duration = _profile.get("preferred_session_length", 15)
            response = start_session(duration)
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response)
        response = format_with_llm(prompt) or response

    elif intent == "grades":
        agents_used = ["canvas"]
        course_id = _extract_course(req.message)
        if course_id:
            response_data = get_grades(course_id)
        else:
            response_data = get_courses()
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response_data)
        response = format_with_llm(prompt) or response_data

    elif intent == "overwhelm":
        agents_used = ["focus", "profile"]
        focus_raw = get_focus_stats()
        prompt = OVERWHELM_FORMAT_PROMPT.format(
            tone=_profile["tone"],
            query=req.message,
            focus_data=focus_raw,
            profile_data=json.dumps(_profile),
        )
        response = format_with_llm(prompt) or (
            "Hey, I hear you. It's okay to feel that way.\n\n"
            "Whatever you did today counts. You don't have to do anything else right now."
        )

    elif intent == "profile":
        agents_used = ["profile"]
        response = json.dumps({"profile": _profile}, indent=2)

    else:
        agents_used = ["transcription"]
        t_raw = get_transcript()
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=t_raw)
        response = format_with_llm(prompt) or t_raw

    return ChatResponse(response=response, intent=intent, agents_used=agents_used)


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    t_result = json.loads(transcribe_audio(dest))
    full = json.loads(get_transcript())

    return {
        **t_result,
        "transcript": full.get("transcript", ""),
        "segments": full.get("segment_count", 0),
    }


@app.post("/api/focus/start")
async def focus_start(req: FocusStartRequest):
    duration = req.duration_minutes or _profile.get("preferred_session_length", 15)
    return json.loads(start_session(duration))


@app.post("/api/focus/end")
async def focus_end(req: FocusEndRequest):
    return json.loads(end_session(req.rating))


@app.get("/api/focus/stats")
async def focus_stats():
    return json.loads(get_focus_stats())


@app.post("/api/focus/capture")
async def focus_capture(thought: str = Form(...)):
    return json.loads(capture_thought(thought))


@app.get("/api/profile")
async def get_profile():
    return _profile


@app.get("/api/courses")
async def courses():
    return json.loads(get_courses())


@app.get("/api/transcript")
async def transcript():
    raw = get_transcript()
    return json.loads(raw)


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": 6}
