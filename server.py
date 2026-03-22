import json
import os
from datetime import datetime

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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
    STUDY_PLAN_PROMPT, OVERWHELM_PROMPT, SINGLE_FORMAT_PROMPT, PLAN_DAY_PROMPT,
)
from agents.calendar_agent.calendar_mcp_server import (
    get_events, get_free_blocks, get_upcoming_deadlines, create_event,
)
from agents.focus_agent.focus_mcp_server import (
    start_session, capture_thought, end_session, get_focus_stats,
)
from agents.advisor_agent.advisor_agent import (
    DEFAULT_PROFILE, _research_strategies, _synthesize_advice,
)
from agents.canvas_agent.canvas_mcp_server import (
    get_all_upcoming as canvas_get_upcoming,
    get_courses as canvas_get_courses,
)

_profile = dict(DEFAULT_PROFILE)

# ── Research cache (keyed by disability + topic, 10-min TTL) ──
_research_cache: dict[str, dict] = {}
_CACHE_TTL_SEC = 600

# ── Course code → subject mapping for topic extraction ──
_COURSE_SUBJECTS: dict[str, str] = {
    "cs170": "data structures algorithms",
    "cs100": "introduction to computer science",
    "cs105": "introduction to computer science",
    "cs120": "programming fundamentals",
    "cs180": "artificial intelligence",
    "cs240": "computer architecture",
    "cs274": "operating systems",
    "cs332": "file structures databases",
    "cs335": "internet web programming",
    "cs340": "programming languages",
    "cs350": "software engineering",
    "cs380": "machine learning",
    "cs420": "computer networks",
    "math122": "calculus I",
    "math123": "calculus II",
    "math224": "linear algebra",
    "math247": "discrete mathematics",
    "math370": "probability statistics",
    "phys151": "general physics mechanics",
    "phys152": "general physics electromagnetism",
    "engr101": "introduction to engineering",
}


def _extract_study_topic(query: str) -> str:
    """Pull the core study topic from a user query.

    Checks for course codes first (CS170 → 'data structures algorithms'),
    then falls back to extracting key noun-phrases from the query.
    Returns a short string like 'data structures algorithms' or 'midterm exam prep'.
    """
    import re
    lower = query.lower()

    # 1. Check for course codes (e.g., "CS170", "cs 170", "MATH 122")
    course_match = re.search(r'\b([a-z]{2,4})\s*(\d{3})\b', lower)
    if course_match:
        code = f"{course_match.group(1)}{course_match.group(2)}"
        if code in _COURSE_SUBJECTS:
            return _COURSE_SUBJECTS[code]

    # 2. Strip common filler words and extract key terms
    # Remove question starters and common chat phrasing
    cleaned = re.sub(
        r'^(help me|can you|please|i need to|i want to|how do i|how to|'
        r'i need help with|help with|let me|i have to)\s+',
        '', lower,
    )
    # Remove trailing filler
    cleaned = re.sub(r'\s+(please|thanks|thank you|asap)$', '', cleaned)

    # 3. Look for "study for X", "prepare for X", "work on X" patterns
    topic_match = re.search(
        r'(?:study|prepare|prep|review|practice|work|cram|learn|focus on|help with)\s+'
        r'(?:for\s+)?(?:my\s+|the\s+|a\s+)?(.+?)(?:\s+exam|\s+midterm|\s+final|\s+test|\s+quiz|\s+homework|\s+hw|\s+assignment)?$',
        cleaned,
    )
    if topic_match:
        topic = topic_match.group(1).strip()
        # Remove articles/possessives that slipped through
        topic = re.sub(r'^(my|the|a|an)\s+', '', topic)
        if len(topic) > 2:
            return topic

    # 4. Detect exam-type context words even without the pattern above
    exam_words = {"exam", "midterm", "final", "test", "quiz", "homework", "hw", "assignment", "project", "lab"}
    subject_words = []
    skip = {"study", "for", "my", "the", "a", "an", "me", "help", "with",
            "how", "to", "do", "i", "can", "you", "please", "need", "want"}
    for word in cleaned.split():
        word_clean = re.sub(r'[^a-z0-9]', '', word)
        if word_clean and word_clean not in skip and word_clean not in exam_words:
            subject_words.append(word_clean)

    if subject_words:
        return " ".join(subject_words[:5])

    # 5. Ultimate fallback
    return "general study skills"


def _cached_research(disability: str, query: str) -> dict:
    """Return cached research if fresh, otherwise fetch and cache.

    Cache is keyed by (disability, topic) so that different subjects get
    different research results even for the same disability.
    """
    import time
    topic = _extract_study_topic(query)

    # If topic is too generic (e.g. "midterm this week"), try to enrich it
    # by looking at Canvas for upcoming exams
    generic_words = {"midterm", "exam", "final", "test", "quiz", "this", "week", "study", "general study skills"}
    topic_words = set(topic.lower().split())
    if topic_words.issubset(generic_words):
        try:
            canvas_raw = json.loads(canvas_get_upcoming(7))
            exams = [a for a in canvas_raw.get("upcoming", [])
                     if any(w in a.get("title", "").lower() for w in ["midterm", "exam", "final", "test", "quiz"])]
            if exams:
                # Use the soonest exam's course as the topic
                exam = exams[0]
                course_name = exam.get("course", "").lower()
                exam_title = exam.get("title", "")
                topic = f"{course_name} {exam_title}".strip()[:60]
        except Exception:
            pass

    key = f"{disability.lower()}:{topic}"
    now = time.time()
    cached = _research_cache.get(key)
    if cached and (now - cached["ts"]) < _CACHE_TTL_SEC:
        return {**cached["data"], "_cached": True, "_topic": topic}
    result = _research_strategies(disability, query, _profile)
    _research_cache[key] = {"data": result, "ts": now}
    return {**result, "_cached": False, "_topic": topic}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str
    agents_used: list[str]
    chain_log: list[dict] = []
    focus_started: bool = False
    focus_duration: int = 0


class FocusStartRequest(BaseModel):
    duration_minutes: int = 0


class FocusEndRequest(BaseModel):
    rating: int = 3


def _parse_date_from_query(query: str) -> str:
    import re
    from datetime import timedelta

    today = datetime.now()
    lower = query.lower()

    match = re.search(r"\d{4}-\d{2}-\d{2}", query)
    if match:
        return match.group(0)

    ordinal = re.search(r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)", lower)
    if ordinal:
        day = int(ordinal.group(1))
        target = today.replace(day=day)
        if target < today:
            if today.month == 12:
                target = target.replace(year=today.year + 1, month=1)
            else:
                target = target.replace(month=today.month + 1)
        return target.strftime("%Y-%m-%d")

    if "tomorrow" in lower:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in lower:
        return today.strftime("%Y-%m-%d")

    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tue": 1, "tues": 1, "wed": 2,
        "thu": 3, "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
    }
    for name, weekday in sorted(day_map.items(), key=lambda x: -len(x[0])):
        if name in lower:
            days_ahead = (weekday - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    intent = classify_intent(req.message)
    agents_used = []
    chain_log = []
    response = ""

    if intent == "study":
        agents_used = ["advisor", "focus", "calendar"]

        # Step 0: Advisor pulls Canvas data
        chain_log.append({"from": "orchestrator", "to": "advisor", "action": "Fetching Canvas assignments & grades"})
        canvas_raw = json.loads(canvas_get_upcoming(14))
        canvas_courses = json.loads(canvas_get_courses())
        canvas_data = {"upcoming": canvas_raw.get("upcoming", []), "courses": canvas_courses.get("courses", [])}
        chain_log.append({"from": "advisor", "to": "advisor", "action": f"Found {canvas_raw.get('total', 0)} upcoming assignments"})

        # Step 1: Orchestrator → Advisor (web research, cached)
        disability = _profile.get("disability_type", "ADHD")
        topic_preview = _extract_study_topic(req.message)
        chain_log.append({"from": "orchestrator", "to": "advisor", "action": f"Research '{topic_preview}' strategies for {disability}"})
        research = _cached_research(disability, req.message)
        sources = research.get("sources", [])
        chain_log.append({"from": "advisor", "to": "advisor", "action": f"Found {len(sources)} research sources"})

        advice = _synthesize_advice(_profile, research, req.message)

        # Step 2: Advisor → Focus (chain)
        chain_log.append({"from": "advisor", "to": "focus", "action": "Forward research + Canvas data for session planning"})
        duration = advice.get("recommended_session_length", _profile.get("preferred_session_length", 15))
        strategies = advice.get("strategies", [])
        focus_raw = start_session(duration, req.message[:50])
        chain_log.append({"from": "focus", "to": "focus", "action": f"Built {duration}-min session plan using Advisor's strategies"})

        # Step 3: Focus → Calendar (propose, don't auto-book)
        chain_log.append({"from": "focus", "to": "calendar", "action": "Checking calendar for free slots"})
        today = datetime.now().strftime("%Y-%m-%d")
        free_raw = get_free_blocks(today)
        deadlines_raw = get_upcoming_deadlines(7)

        proposed_slots = _propose_slots(req.message, duration, strategies, canvas_data.get("upcoming", []))
        chain_log.append({"from": "calendar", "to": "orchestrator", "action": f"Found {len(proposed_slots)} available slots"})

        plan_data = {
            "proposed_slots": proposed_slots,
            "advisor_advice": advice,
            "advisor_research": {"sources": sources},
            "canvas": canvas_data,
            "focus_session": json.loads(focus_raw),
            "free_blocks_today": free_raw,
            "deadlines": deadlines_raw,
        }

        prompt = STUDY_PLAN_PROMPT.format(
            tone=_profile.get("tone", "encouraging"),
            query=req.message,
            data=json.dumps(plan_data, indent=2),
        )
        response = format_with_llm(prompt, max_tokens=1000) or f"Study plan created! {len(scheduled)} sessions scheduled."

    elif intent == "focus":
        query_lower = req.message.lower()
        if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
            agents_used = ["focus"]
            chain_log.append({"from": "orchestrator", "to": "focus", "action": "End focus session"})
            response = end_session("", 3)
            chain_log.append({"from": "focus", "to": "orchestrator", "action": "Session ended, stats returned"})
        elif any(kw in query_lower for kw in ["stat", "how", "progress"]):
            agents_used = ["focus"]
            chain_log.append({"from": "orchestrator", "to": "focus", "action": "Get focus stats"})
            response = get_focus_stats()
            chain_log.append({"from": "focus", "to": "orchestrator", "action": "Stats returned"})
        else:
            agents_used = ["advisor", "focus"]
            # Advisor → Focus chain
            disability = _profile.get("disability_type", "ADHD")
            topic_preview = _extract_study_topic(req.message)
            chain_log.append({"from": "orchestrator", "to": "advisor", "action": f"Research focus strategies for '{topic_preview}' ({disability})"})
            research = _cached_research(disability, req.message)
            advice = _synthesize_advice(_profile, research, req.message)
            duration = advice.get("recommended_session_length", _profile.get("preferred_session_length", 15))
            chain_log.append({"from": "advisor", "to": "focus", "action": f"Recommended {duration}-min sessions based on research"})
            response = start_session(duration, req.message[:50])
            chain_log.append({"from": "focus", "to": "orchestrator", "action": f"Session started ({duration} min, research-adapted)"})

        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response)
        response = format_with_llm(prompt) or response

    elif intent == "schedule":
        agents_used = ["calendar"]
        date = _parse_date_from_query(req.message)
        chain_log.append({"from": "orchestrator", "to": "calendar", "action": f"Get schedule for {date}"})
        response_data = get_events(date)
        if any(kw in req.message.lower() for kw in ["free", "available", "open"]):
            response_data = get_free_blocks(date)
        chain_log.append({"from": "calendar", "to": "orchestrator", "action": "Schedule data returned"})

        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response_data)
        response = format_with_llm(prompt) or response_data

    elif intent == "overwhelm":
        agents_used = ["focus", "advisor"]
        chain_log.append({"from": "orchestrator", "to": "focus", "action": "Get today's accomplishments"})
        chain_log.append({"from": "orchestrator", "to": "advisor", "action": "Get disability-aware support"})
        focus_raw = get_focus_stats()
        chain_log.append({"from": "focus", "to": "orchestrator", "action": "Session stats returned"})
        chain_log.append({"from": "advisor", "to": "orchestrator", "action": f"Support strategies for {_profile['disability_type']}"})

        prompt = OVERWHELM_PROMPT.format(
            query=req.message,
            focus_data=focus_raw,
            advisor_data=json.dumps(_profile),
        )
        response = format_with_llm(prompt) or (
            "Hey, I hear you. It's okay to feel that way.\n\n"
            "Whatever you did today counts. You don't have to do anything else right now."
        )

    elif intent == "advisor":
        agents_used = ["advisor"]
        _handle_profile_update(req.message)
        chain_log.append({"from": "orchestrator", "to": "advisor", "action": "Update/view profile"})
        chain_log.append({"from": "advisor", "to": "orchestrator", "action": "Profile returned"})
        response = json.dumps({"profile": _profile}, indent=2)
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response)
        response = format_with_llm(prompt) or response

    elif intent == "status":
        agents_used = ["focus", "calendar"]
        chain_log.append({"from": "orchestrator", "to": "focus", "action": "Get today's stats"})
        chain_log.append({"from": "orchestrator", "to": "calendar", "action": "Get today's schedule"})
        today = datetime.now().strftime("%Y-%m-%d")
        focus_raw = get_focus_stats()
        cal_raw = get_events(today)
        chain_log.append({"from": "focus", "to": "orchestrator", "action": "Stats returned"})
        chain_log.append({"from": "calendar", "to": "orchestrator", "action": "Schedule returned"})

        data = {"focus": json.loads(focus_raw), "calendar": json.loads(cal_raw)}
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=json.dumps(data, indent=2))
        response = format_with_llm(prompt) or json.dumps(data, indent=2)

    else:
        agents_used = ["advisor"]
        chain_log.append({"from": "orchestrator", "to": "advisor", "action": "General query"})
        chain_log.append({"from": "advisor", "to": "orchestrator", "action": "Response returned"})
        prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=json.dumps(_profile))
        response = format_with_llm(prompt) or "I'm here. What would you like to work on?"

    focus_started = False
    focus_duration = 0
    if intent == "focus" and not any(kw in req.message.lower() for kw in ["end", "stop", "done", "stat", "how"]):
        focus_started = True
        focus_duration = _profile.get("preferred_session_length", 15)

    return ChatResponse(
        response=response, intent=intent, agents_used=agents_used,
        chain_log=chain_log, focus_started=focus_started, focus_duration=focus_duration,
    )


def _sse_event(data: dict) -> str:
    return json.dumps(data) + "\n"


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming endpoint — emits NDJSON events between real processing steps."""

    async def generate():
        intent = classify_intent(req.message)
        yield _sse_event({"type": "intent", "intent": intent})

        agents_used = []
        chain_log = []
        response = ""

        if intent == "study":
            agents_used = ["advisor", "focus", "calendar"]
            sources = []
            canvas_data = {}
            proposed_slots = []

            # Step 0: Orchestrator dispatches to Advisor with Canvas data
            step = {"from": "orchestrator", "to": "advisor", "action": f"Routing '{req.message[:40]}' — pulling Canvas data first"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})

            canvas_raw = json.loads(canvas_get_upcoming(14))
            canvas_courses = json.loads(canvas_get_courses())
            canvas_data = {"upcoming": canvas_raw.get("upcoming", []), "courses": canvas_courses.get("courses", [])}
            n_upcoming = canvas_raw.get("total", 0)

            # Show what Canvas found — list actual assignments
            urgent = [a for a in canvas_raw.get("upcoming", []) if a.get("days_left", 99) <= 5]
            all_titles = [f"{a['title']} ({a.get('days_left', '?')}d)" for a in canvas_raw.get("upcoming", [])[:4]]
            step = {"from": "advisor", "to": "advisor", "action": f"Loaded {n_upcoming} assignments from Canvas LMS"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor", "detail": ", ".join(all_titles) if all_titles else "No upcoming assignments"})

            # Step 1: Advisor web research (cached)
            disability = _profile.get("disability_type", "ADHD")
            topic_preview = _extract_study_topic(req.message)
            step = {"from": "advisor", "to": "advisor", "action": f"Researching '{topic_preview}' strategies for {disability}"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})

            research = _cached_research(disability, req.message)
            sources = research.get("sources", [])
            was_cached = research.get("_cached", False)
            search_query = research.get("query", "")

            cache_note = " (cached)" if was_cached else " via web search"
            source_titles = ", ".join(s.get("title", "")[:40] for s in sources[:2]) if sources else "none"
            step = {"from": "advisor", "to": "advisor", "action": f"Found {len(sources)} sources on '{topic_preview}'{cache_note}"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor", "detail": f'Search: "{search_query[:60]}…" → {source_titles}'})

            # Emit sources event for frontend visualization
            if sources:
                yield _sse_event({"type": "sources", "sources": sources})

            advice = _synthesize_advice(_profile, research, req.message)

            # Step 2: Advisor → Focus (show what advice is being passed)
            strat_preview = " + ".join(s[:35] for s in advice.get("strategies", [])[:2]) or "strategies ready"
            step = {"from": "advisor", "to": "focus", "action": f"Passing {len(advice.get('strategies', []))} strategies to Focus Agent"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "focus", "detail": strat_preview})

            duration = advice.get("recommended_session_length", _profile.get("preferred_session_length", 15))
            strategies = advice.get("strategies", [])
            focus_raw = start_session(duration, req.message[:50])

            key_insight = advice.get("key_insight", "")[:80]
            step = {"from": "focus", "to": "focus", "action": f"Designed {duration}-min focused session based on Advisor's research"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "focus", "detail": key_insight or f"Session length optimized for {disability}"})

            # Step 3: Focus → Calendar (propose slots, show what's being checked)
            step = {"from": "focus", "to": "calendar", "action": "Scanning your weekly schedule for study windows"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "calendar"})

            today = datetime.now().strftime("%Y-%m-%d")
            free_raw = get_free_blocks(today)
            deadlines_raw = get_upcoming_deadlines(14)

            # Show calendar checking events
            today_events = json.loads(get_events(today)).get("events", [])
            event_names = [e["title"] for e in today_events[:4]]
            if event_names:
                step = {"from": "calendar", "to": "calendar", "action": f"Today's schedule: {', '.join(event_names)}"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "calendar"})

            proposed_slots = _propose_slots(req.message, duration, strategies, canvas_data.get("upcoming", []))

            # Gather the schedule for each proposed day so the LLM can see lectures + gaps
            day_schedules = {}
            for slot in proposed_slots:
                d = slot["date"]
                if d not in day_schedules:
                    day_schedules[d] = json.loads(get_events(d)).get("events", [])

            # Show each proposed slot with its contextual reason
            for s in proposed_slots[:3]:
                step = {"from": "calendar", "to": "calendar", "action": f"{s['day']} {s['start']}-{s['end']} — {s['reason']}"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "calendar"})

            step = {"from": "calendar", "to": "orchestrator", "action": f"Proposed {len(proposed_slots)} study slots based on your class schedule"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            plan_data = {
                "proposed_slots": proposed_slots,
                "day_schedules": day_schedules,
                "advisor_advice": advice,
                "advisor_research": {"sources": sources},
                "canvas": canvas_data,
                "focus_session": json.loads(focus_raw),
                "free_blocks_today": free_raw,
                "deadlines": deadlines_raw,
            }
            prompt = STUDY_PLAN_PROMPT.format(
                tone=_profile.get("tone", "encouraging"),
                query=req.message,
                data=json.dumps(plan_data, indent=2),
            )
            yield _sse_event({"type": "step", "from": "orchestrator", "to": "orchestrator", "action": "Formatting study plan", "active": "orchestrator"})
            response = format_with_llm(prompt, max_tokens=1000) or f"Study plan ready! {len(proposed_slots)} time slots found."

        elif intent == "focus":
            query_lower = req.message.lower()
            if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
                agents_used = ["focus"]
                step = {"from": "orchestrator", "to": "focus", "action": "End focus session"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "focus"})
                response = end_session("", 3)
                step = {"from": "focus", "to": "orchestrator", "action": "Session ended, stats returned"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "orchestrator"})
            elif any(kw in query_lower for kw in ["stat", "how", "progress"]):
                agents_used = ["focus"]
                step = {"from": "orchestrator", "to": "focus", "action": "Get focus stats"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "focus"})
                response = get_focus_stats()
                step = {"from": "focus", "to": "orchestrator", "action": "Stats returned"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "orchestrator"})
            else:
                agents_used = ["advisor", "focus"]
                disability = _profile.get("disability_type", "ADHD")
                topic_preview = _extract_study_topic(req.message)
                step = {"from": "orchestrator", "to": "advisor", "action": f"Research focus strategies for '{topic_preview}' ({disability})"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "advisor"})
                research = _cached_research(disability, req.message)
                advice = _synthesize_advice(_profile, research, req.message)
                duration = advice.get("recommended_session_length", _profile.get("preferred_session_length", 15))
                step = {"from": "advisor", "to": "focus", "action": f"Recommended {duration}-min sessions based on research"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "focus"})
                response = start_session(duration, req.message[:50])
                step = {"from": "focus", "to": "orchestrator", "action": f"Session started ({duration} min, research-adapted)"}
                chain_log.append(step)
                yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response)
            yield _sse_event({"type": "step", "from": "orchestrator", "to": "orchestrator", "action": "Formatting response", "active": "orchestrator"})
            response = format_with_llm(prompt) or response

        elif intent == "schedule":
            agents_used = ["calendar"]
            date = _parse_date_from_query(req.message)
            step = {"from": "orchestrator", "to": "calendar", "action": f"Get schedule for {date}"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "calendar"})
            response_data = get_events(date)
            if any(kw in req.message.lower() for kw in ["free", "available", "open"]):
                response_data = get_free_blocks(date)
            step = {"from": "calendar", "to": "orchestrator", "action": "Schedule data returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})
            prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response_data)
            yield _sse_event({"type": "step", "from": "orchestrator", "to": "orchestrator", "action": "Formatting response", "active": "orchestrator"})
            response = format_with_llm(prompt) or response_data

        elif intent == "overwhelm":
            agents_used = ["focus", "advisor"]
            step = {"from": "orchestrator", "to": "focus", "action": "Get today's accomplishments"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "focus"})
            focus_raw = get_focus_stats()
            step = {"from": "focus", "to": "orchestrator", "action": "Session stats returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            step = {"from": "orchestrator", "to": "advisor", "action": "Get disability-aware support"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})
            step = {"from": "advisor", "to": "orchestrator", "action": f"Support strategies for {_profile['disability_type']}"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            prompt = OVERWHELM_PROMPT.format(
                query=req.message,
                focus_data=focus_raw,
                advisor_data=json.dumps(_profile),
            )
            yield _sse_event({"type": "step", "from": "orchestrator", "to": "orchestrator", "action": "Formatting compassionate response", "active": "orchestrator"})
            response = format_with_llm(prompt) or (
                "Hey, I hear you. It's okay to feel that way.\n\n"
                "Whatever you did today counts. You don't have to do anything else right now."
            )

        elif intent == "advisor":
            agents_used = ["advisor"]
            _handle_profile_update(req.message)
            step = {"from": "orchestrator", "to": "advisor", "action": "Update/view profile"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})
            step = {"from": "advisor", "to": "orchestrator", "action": "Profile returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})
            response = json.dumps({"profile": _profile}, indent=2)
            prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=response)
            response = format_with_llm(prompt) or response

        elif intent == "status":
            agents_used = ["focus", "calendar"]
            step = {"from": "orchestrator", "to": "focus", "action": "Get today's stats"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "focus"})
            today = datetime.now().strftime("%Y-%m-%d")
            focus_raw = get_focus_stats()
            step = {"from": "focus", "to": "orchestrator", "action": "Stats returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            step = {"from": "orchestrator", "to": "calendar", "action": "Get today's schedule"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "calendar"})
            cal_raw = get_events(today)
            step = {"from": "calendar", "to": "orchestrator", "action": "Schedule returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            data = {"focus": json.loads(focus_raw), "calendar": json.loads(cal_raw)}
            prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=json.dumps(data, indent=2))
            yield _sse_event({"type": "step", "from": "orchestrator", "to": "orchestrator", "action": "Formatting response", "active": "orchestrator"})
            response = format_with_llm(prompt) or json.dumps(data, indent=2)

        elif intent == "plan":
            agents_used = ["advisor", "calendar"]

            # Advisor researches disability-optimized routines
            disability = _profile.get("disability_type", "ADHD")
            topic_preview = _extract_study_topic(req.message)
            step = {"from": "orchestrator", "to": "advisor", "action": f"Research daily routines for '{topic_preview}' ({disability})"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})

            research = _cached_research(disability, req.message)
            step = {"from": "advisor", "to": "advisor", "action": f"Found {len(research.get('sources', []))} sources on '{topic_preview}' routines"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})

            # Calendar: what's already scheduled
            step = {"from": "orchestrator", "to": "calendar", "action": "Check today's schedule"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "calendar"})
            today = datetime.now().strftime("%Y-%m-%d")
            cal_raw = get_events(today)
            free_raw = get_free_blocks(today)
            step = {"from": "calendar", "to": "orchestrator", "action": "Schedule returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})

            prompt = PLAN_DAY_PROMPT.format(
                query=req.message,
                profile=json.dumps(_profile),
                calendar=cal_raw,
                research=json.dumps(research.get("sources", [])[:2]),
            )
            response = format_with_llm(prompt, max_tokens=600) or "Let me help you plan your day."

        else:
            agents_used = ["advisor"]
            step = {"from": "orchestrator", "to": "advisor", "action": "General query"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "advisor"})
            step = {"from": "advisor", "to": "orchestrator", "action": "Response returned"}
            chain_log.append(step)
            yield _sse_event({"type": "step", **step, "active": "orchestrator"})
            prompt = SINGLE_FORMAT_PROMPT.format(query=req.message, data=json.dumps(_profile))
            response = format_with_llm(prompt) or "I'm here. What would you like to work on?"

        # Only start focus timer when user explicitly asks for a focus session
        focus_started = False
        focus_duration = 0
        if intent == "focus" and not any(kw in req.message.lower() for kw in ["end", "stop", "done", "stat", "how"]):
            focus_started = True
            focus_duration = _profile.get("preferred_session_length", 15)

        done_event = {
            "type": "done",
            "response": response,
            "intent": intent,
            "agents_used": agents_used,
            "chain_log": chain_log,
            "focus_started": focus_started,
            "focus_duration": focus_duration,
        }
        # Attach sources/canvas/proposals if study intent produced them
        if intent == "study":
            done_event["sources"] = sources
            done_event["canvas"] = canvas_data
            done_event["proposed_slots"] = proposed_slots
        yield _sse_event(done_event)

    return StreamingResponse(generate(), media_type="application/x-ndjson")


def _propose_slots(task: str, duration: int, strategies: list, canvas_upcoming: list = None) -> list:
    """Find available time slots but don't book them. Returns proposals with contextual reasons."""
    from datetime import timedelta
    today = datetime.now()
    proposals = []

    # Build deadline awareness from Canvas
    deadline_dates = {}
    for a in (canvas_upcoming or []):
        deadline_dates[a.get("due", "")] = a.get("title", "assignment")

    for i in range(1, 8):
        d = today + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        date_str = d.strftime("%Y-%m-%d")

        # Get the day's events so we can build contextual reasons
        day_events = json.loads(get_events(date_str)).get("events", [])
        free = json.loads(get_free_blocks(date_str))
        blocks = free.get("free_blocks", [])
        best = None
        reason = ""

        # Find the best block and build a reason referencing actual classes
        for b in blocks:
            if b["duration_min"] < duration:
                continue
            hour = int(b["start"].split(":")[0])
            minute = int(b["start"].split(":")[1]) if ":" in b["start"] else 0

            # Find what class/event ends right before this free block
            preceding_class = None
            following_class = None
            for ev in day_events:
                ev_end_h, ev_end_m = map(int, ev["end"].split(":"))
                ev_start_h, ev_start_m = map(int, ev["start"].split(":"))
                # Event ends within 30 min before our slot starts
                ev_end_total = ev_end_h * 60 + ev_end_m
                slot_start_total = hour * 60 + minute
                if 0 <= (slot_start_total - ev_end_total) <= 30:
                    preceding_class = ev["title"]
                # Event starts after our slot
                if ev_start_h * 60 + ev_start_m > slot_start_total and not following_class:
                    following_class = ev["title"]

            if preceding_class:
                reason = f"Right after {preceding_class} — review while material is fresh"
            elif 9 <= hour < 12:
                reason = f"Morning gap — {_profile.get('disability_type', 'ADHD')}-friendly fresh-mind window"
            elif following_class:
                reason = f"Before {following_class} — warm up with related concepts"
            else:
                reason = f"Open {d.strftime('%A')} slot — no classes competing for attention"

            best = b
            break

        if not best:
            continue

        # Override with deadline-aware reasons (higher priority)
        if date_str in deadline_dates:
            reason = f"Day of {deadline_dates[date_str]} deadline — final review session"
        day_before = (d - timedelta(days=1)).strftime("%Y-%m-%d")
        if day_before in deadline_dates:
            reason = f"Day before {deadline_dates[day_before]} due — last prep session"

        start = best["start"]
        sh, sm = map(int, start.split(":"))
        end_m = sm + duration
        end_h = sh + end_m // 60
        end_m = end_m % 60
        end_time = f"{end_h:02d}:{end_m:02d}"

        proposals.append({
            "day": d.strftime("%A"),
            "date": date_str,
            "start": start,
            "end": end_time,
            "duration_min": duration,
            "reason": reason,
            "task": task[:40],
            "strategies": strategies[:2] if strategies else ["focused study"],
        })
        if len(proposals) >= 3:
            break

    return proposals


class ScheduleConfirmRequest(BaseModel):
    slots: list[dict]


@app.post("/api/schedule/confirm")
async def schedule_confirm(req: ScheduleConfirmRequest):
    """Confirm and book proposed study slots on Google Calendar."""
    booked = []
    for slot in req.slots:
        strategy_text = ", ".join(slot.get("strategies", ["focused study"]))
        result = json.loads(create_event(
            title=f"Study: {slot.get('task', 'Study session')}",
            date=slot["date"],
            start=slot["start"],
            end=slot["end"],
            description=f"Strategy: {strategy_text}\nReason: {slot.get('reason', '')}\nScheduled by NeuroFlow",
        ))
        if result.get("created"):
            booked.append({
                "day": slot.get("day", ""),
                "date": slot["date"],
                "time": f"{slot['start']}-{slot['end']}",
            })
    return {"booked": booked, "count": len(booked)}


def _handle_profile_update(query: str):
    lower = query.lower()
    if "dyslexia" in lower:
        _profile["disability_type"] = "dyslexia"
        _profile["reading_grade_level"] = 6
        _profile["preferred_session_length"] = 20
    elif "autism" in lower or "asd" in lower:
        _profile["disability_type"] = "autism"
        _profile["tone"] = "precise"
        _profile["preferred_session_length"] = 25
    elif "adhd" in lower:
        _profile["disability_type"] = "ADHD"
        _profile["tone"] = "encouraging"
        _profile["preferred_session_length"] = 15


@app.post("/api/focus/start")
async def focus_start(req: FocusStartRequest):
    duration = req.duration_minutes or _profile.get("preferred_session_length", 15)
    return json.loads(start_session(duration))


@app.post("/api/focus/end")
async def focus_end(req: FocusEndRequest):
    return json.loads(end_session("", req.rating))


@app.get("/api/focus/stats")
async def focus_stats():
    return json.loads(get_focus_stats())


@app.post("/api/focus/capture")
async def focus_capture(thought: str = Form(...)):
    return json.loads(capture_thought(thought))


@app.get("/api/advisor")
async def get_advisor():
    return _profile


class ProfileUpdateRequest(BaseModel):
    disability_type: str | None = None
    preferred_session_length: int | None = None
    tone: str | None = None
    best_focus_time: str | None = None
    challenges: list[str] | None = None
    subjects: list[str] | None = None


@app.post("/api/profile")
async def update_profile(req: ProfileUpdateRequest):
    """Update Advisor profile — used by the profile setup UI."""
    if req.disability_type:
        _profile["disability_type"] = req.disability_type
    if req.preferred_session_length:
        _profile["preferred_session_length"] = req.preferred_session_length
    if req.tone:
        _profile["tone"] = req.tone
    if req.best_focus_time:
        _profile["best_focus_time"] = req.best_focus_time
    if req.challenges:
        _profile["challenges"] = req.challenges
    if req.subjects:
        _profile["subjects"] = req.subjects
    return _profile


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": 4}


# ---------------------------------------------------------------------------
# Serve frontend (must be AFTER all /api routes)
# ---------------------------------------------------------------------------
_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
