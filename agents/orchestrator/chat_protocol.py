import json
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context, Protocol
from agents.models.config import (
    FOCUS_ADDRESS, CALENDAR_ADDRESS, PROFILE_ADDRESS,
    TRANSCRIPTION_ADDRESS, CANVAS_ADDRESS, ASI1_API_KEY,
)
from agents.models.models import SharedAgentState
from agents.services.state_service import state_service, PendingFanOut
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

chat_proto = Protocol(spec=chat_protocol_spec)

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

INTENT_PROMPT = """You are the intent classifier for NeuroFlow, a neurodivergent study companion with 5 specialist agents.

Classify the user's message into ONE of these intents:
- "transcribe" — user just recorded a lecture, wants it transcribed and simplified
- "explain" — user asks what the professor said about a specific topic, wants clarification from the transcript
- "review" — user wants to review/study lecture material, start a study session
- "focus" — user wants to start or end a focus/pomodoro session explicitly
- "schedule" — user wants to see their calendar, free time, or upcoming events
- "grades" — user asks about grades, assignments, course info
- "overwhelm" — user is struggling, shutting down, says "I can't" or similar
- "status" — user wants an overview of today's progress
- "profile" — user wants to view or update their accessibility preferences

Return ONLY the intent word, nothing else."""


def classify_intent(query: str) -> str:
    try:
        if ASI1_API_KEY:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
            response = client.chat.completions.create(
                model="asi1-mini",
                messages=[
                    {"role": "system", "content": INTENT_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=10,
            )
            intent = response.choices[0].message.content.strip().lower().strip('"')
            valid = (
                "transcribe", "explain", "review", "focus",
                "schedule", "grades", "overwhelm", "status", "profile",
            )
            if intent in valid:
                return intent
    except Exception:
        pass

    lower = query.lower()
    if any(kw in lower for kw in ["can't", "cannot", "too much", "overwhelm", "give up", "i can't focus anymore"]):
        return "overwhelm"
    if any(kw in lower for kw in ["recorded", "transcri", "lecture audio", "just recorded"]):
        return "transcribe"
    if any(kw in lower for kw in ["what did", "professor say", "say about", "clarify", "explain"]):
        return "explain"
    if any(kw in lower for kw in ["review", "study", "help me review", "quiz me"]):
        return "review"
    if any(kw in lower for kw in ["start focus", "begin focus", "focus session", "pomodoro", "timer"]):
        return "focus"
    if any(kw in lower for kw in ["schedule", "calendar", "what's on", "free", "when am i"]):
        return "schedule"
    if any(kw in lower for kw in ["grade", "assignment", "course", "gpa", "canvas"]):
        return "grades"
    if any(kw in lower for kw in ["profile", "preference", "accessibility", "update my"]):
        return "profile"
    if any(kw in lower for kw in ["progress", "status", "how am i", "overview"]):
        return "status"
    return "explain"


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = " ".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    )
    ctx.logger.info(f"Received: {text}")

    chat_session_id = str(ctx.session)
    state = state_service.get_state(chat_session_id)

    if state is None:
        state = SharedAgentState(
            chat_session_id=chat_session_id,
            query=text,
            user_sender_address=sender,
        )
        state_service.set_state(chat_session_id, state)
    else:
        state.query = text

    intent = classify_intent(text)
    ctx.logger.info(f"Intent: {intent}")

    if intent == "transcribe":
        fanout = PendingFanOut(
            expected_agents=[TRANSCRIPTION_ADDRESS, CANVAS_ADDRESS, PROFILE_ADDRESS],
            query=text,
            user_sender=sender,
        )
        fanout.intent = "transcribe"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(TRANSCRIPTION_ADDRESS, state)
        await ctx.send(CANVAS_ADDRESS, state)
        await ctx.send(PROFILE_ADDRESS, state)
        ctx.logger.info("Fan-out: Transcription + Canvas + Profile (transcribe)")

    elif intent == "explain":
        fanout = PendingFanOut(
            expected_agents=[TRANSCRIPTION_ADDRESS, CANVAS_ADDRESS, PROFILE_ADDRESS],
            query=text,
            user_sender=sender,
        )
        fanout.intent = "explain"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(TRANSCRIPTION_ADDRESS, state)
        await ctx.send(CANVAS_ADDRESS, state)
        await ctx.send(PROFILE_ADDRESS, state)
        ctx.logger.info("Fan-out: Transcription + Canvas + Profile (explain)")

    elif intent == "review":
        fanout = PendingFanOut(
            expected_agents=[CALENDAR_ADDRESS, FOCUS_ADDRESS, TRANSCRIPTION_ADDRESS, PROFILE_ADDRESS],
            query=text,
            user_sender=sender,
        )
        fanout.intent = "review"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(CALENDAR_ADDRESS, state)
        await ctx.send(FOCUS_ADDRESS, state)
        await ctx.send(TRANSCRIPTION_ADDRESS, state)
        await ctx.send(PROFILE_ADDRESS, state)
        ctx.logger.info("Fan-out: Calendar + Focus + Transcription + Profile (review)")

    elif intent == "schedule":
        await ctx.send(CALENDAR_ADDRESS, state)
        ctx.logger.info("Routing to Calendar Agent")

    elif intent in ("focus",):
        await ctx.send(FOCUS_ADDRESS, state)
        ctx.logger.info("Routing to Focus Agent")

    elif intent == "grades":
        await ctx.send(CANVAS_ADDRESS, state)
        ctx.logger.info("Routing to Canvas Agent")

    elif intent == "overwhelm":
        fanout = PendingFanOut(
            expected_agents=[FOCUS_ADDRESS, PROFILE_ADDRESS],
            query=text,
            user_sender=sender,
        )
        fanout.intent = "overwhelm"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(FOCUS_ADDRESS, state)
        await ctx.send(PROFILE_ADDRESS, state)
        ctx.logger.info("Fan-out: Focus + Profile (overwhelm)")

    elif intent == "status":
        fanout = PendingFanOut(
            expected_agents=[FOCUS_ADDRESS, CALENDAR_ADDRESS, CANVAS_ADDRESS],
            query=text,
            user_sender=sender,
        )
        fanout.intent = "status"
        state_service.start_fanout(chat_session_id, fanout)
        await ctx.send(FOCUS_ADDRESS, state)
        await ctx.send(CALENDAR_ADDRESS, state)
        await ctx.send(CANVAS_ADDRESS, state)
        ctx.logger.info("Fan-out: Focus + Calendar + Canvas (status)")

    elif intent == "profile":
        await ctx.send(PROFILE_ADDRESS, state)
        ctx.logger.info("Routing to Profile Agent")

    else:
        await ctx.send(TRANSCRIPTION_ADDRESS, state)
        ctx.logger.info("Routing to Transcription Agent (fallback)")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


# ---------------------------------------------------------------------------
# Response formatting prompts
# ---------------------------------------------------------------------------

TRANSCRIBE_FORMAT_PROMPT = """You are NeuroFlow, a neurodivergent study companion. A student just recorded a lecture and you have the transcript, their accessibility profile, and course data.

Your job: simplify the transcript into Easy Read study notes adapted to the student's profile.

Rules:
- Reading level: grade {grade_level} — use simple sentences, define jargon
- Chunk size: {chunk_size} — break into {chunk_size} digestible sections
- Tone: {tone}
- PRESERVE exam-critical terms exactly as-is (listed below) — don't simplify these, but add a brief definition in parentheses after each
- Use bullet points and short paragraphs (max 3 sentences each)
- Bold key terms that will be on the exam
- End with "Key takeaways" (3-5 bullets)

Exam-critical terms to preserve: {exam_topics}

Transcript:
{transcript}

Course context:
{course_data}"""

EXPLAIN_FORMAT_PROMPT = """You are NeuroFlow, a neurodivergent study companion. The student is asking about a specific concept from their lecture.

Rules:
- Reading level: grade {grade_level}
- Tone: {tone}
- Use the professor's actual words from the transcript when possible, then simplify
- If this is an exam topic, flag it clearly: "This will be on the midterm"
- Give a concrete example if possible
- Keep it short — max 6-8 sentences

Student's question: {query}

Transcript search results:
{transcript_data}

Course context (exam topics):
{course_data}

Student profile:
{profile_data}"""

REVIEW_FORMAT_PROMPT = """You are NeuroFlow, a neurodivergent study companion. The student wants to review lecture material. You have their schedule, focus session state, transcript content, and accessibility profile.

Rules:
- Check how much time they have (calendar data)
- Start a focused review session sized to their available time and preferred session length
- Break the transcript content into review chunks
- Tone: {tone}, reading level: grade {grade_level}
- Highlight what's exam-critical
- End with: "Say 'done' when you finish this chunk and I'll give you the next one"

Calendar data: {calendar_data}
Focus session data: {focus_data}
Transcript content: {transcript_data}
Profile: {profile_data}
Student's message: {query}"""

OVERWHELM_FORMAT_PROMPT = """You are NeuroFlow, a neurodivergent study companion. The student is feeling overwhelmed. Respond with compassion using their real data.

Rules:
- Acknowledge their feeling FIRST — don't dismiss it
- Show what they've ALREADY accomplished (from focus stats)
- Frame everything positively ("you did X" not "you only did X")
- Adapt tone to their profile preference: {tone}
- Offer ONE tiny next action OR permission to stop entirely
- Keep it short — overwhelmed brains can't process walls of text

Student's message: {query}
Focus stats: {focus_data}
Profile: {profile_data}"""

SINGLE_FORMAT_PROMPT = """You are NeuroFlow, a neurodivergent study companion. Format the agent data below into a warm, helpful response.

Rules:
- Be concise but supportive
- Use simple formatting (line breaks, not markdown headers)
- Frame progress positively
- End with a clear next action suggestion

Student's message: {query}
Agent data: {data}"""


# ---------------------------------------------------------------------------
# Response generation
# ---------------------------------------------------------------------------

def format_with_llm(prompt: str, max_tokens: int = 800) -> str | None:
    if not ASI1_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
        response = client.chat.completions.create(
            model="asi1-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.5,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_profile_fields(fanout: PendingFanOut) -> dict:
    """Extract profile config from fanout responses."""
    profile_raw = _safe_json(fanout.received.get(PROFILE_ADDRESS, "{}"))
    profile = profile_raw.get("profile", {})
    return {
        "grade_level": profile.get("reading_grade_level", 8),
        "chunk_size": profile.get("chunk_size", "small"),
        "tone": profile.get("tone", "encouraging"),
    }


def generate_fanout_response(fanout: PendingFanOut) -> str:
    """Combine multi-agent responses into one cohesive reply."""
    intent = getattr(fanout, "intent", "")
    pf = _get_profile_fields(fanout)

    if intent == "transcribe":
        transcript_data = fanout.received.get(TRANSCRIPTION_ADDRESS, "{}")
        course_data = fanout.received.get(CANVAS_ADDRESS, "{}")
        canvas = _safe_json(course_data)
        exam_topics = canvas.get("exam_topics", [])

        transcript_obj = _safe_json(transcript_data)
        preview = transcript_obj.get("transcript_preview", transcript_obj.get("transcript", ""))

        prompt = TRANSCRIBE_FORMAT_PROMPT.format(
            grade_level=pf["grade_level"],
            chunk_size=pf["chunk_size"],
            tone=pf["tone"],
            exam_topics=", ".join(exam_topics) if exam_topics else "none listed",
            transcript=preview,
            course_data=course_data,
        )
        result = format_with_llm(prompt, max_tokens=1200)
        if result:
            return result
        return f"Transcript loaded ({transcript_obj.get('word_count', '?')} words). Ask me about any concept!"

    elif intent == "explain":
        transcript_data = fanout.received.get(TRANSCRIPTION_ADDRESS, "{}")
        course_data = fanout.received.get(CANVAS_ADDRESS, "{}")
        profile_data = fanout.received.get(PROFILE_ADDRESS, "{}")

        prompt = EXPLAIN_FORMAT_PROMPT.format(
            grade_level=pf["grade_level"],
            tone=pf["tone"],
            query=fanout.query,
            transcript_data=transcript_data,
            course_data=course_data,
            profile_data=profile_data,
        )
        result = format_with_llm(prompt)
        if result:
            return result
        return transcript_data

    elif intent == "review":
        calendar_data = fanout.received.get(CALENDAR_ADDRESS, "{}")
        focus_data = fanout.received.get(FOCUS_ADDRESS, "{}")
        transcript_data = fanout.received.get(TRANSCRIPTION_ADDRESS, "{}")
        profile_data = fanout.received.get(PROFILE_ADDRESS, "{}")

        prompt = REVIEW_FORMAT_PROMPT.format(
            tone=pf["tone"],
            grade_level=pf["grade_level"],
            calendar_data=calendar_data,
            focus_data=focus_data,
            transcript_data=transcript_data,
            profile_data=profile_data,
            query=fanout.query,
        )
        result = format_with_llm(prompt, max_tokens=1000)
        if result:
            return result
        return "Ready to review! What topic should we start with?"

    elif intent == "overwhelm":
        focus_data = fanout.received.get(FOCUS_ADDRESS, "{}")
        profile_data = fanout.received.get(PROFILE_ADDRESS, "{}")

        prompt = OVERWHELM_FORMAT_PROMPT.format(
            tone=pf["tone"],
            query=fanout.query,
            focus_data=focus_data,
            profile_data=profile_data,
        )
        result = format_with_llm(prompt)
        if result:
            return result
        return (
            "Hey, I hear you. It's okay to feel that way.\n\n"
            "Whatever you did today is real progress. You don't have to do anything else right now.\n\n"
            "When you're ready (no rush), I can suggest one tiny thing — or you can just rest."
        )

    elif intent == "status":
        all_data = {k: _safe_json(v) for k, v in fanout.received.items()}
        prompt = SINGLE_FORMAT_PROMPT.format(
            query=fanout.query,
            data=json.dumps(all_data, indent=2),
        )
        result = format_with_llm(prompt)
        return result or json.dumps(all_data, indent=2)

    all_data = {addr: data for addr, data in fanout.received.items()}
    prompt = SINGLE_FORMAT_PROMPT.format(
        query=fanout.query,
        data=json.dumps(all_data, indent=2),
    )
    result = format_with_llm(prompt)
    return result or json.dumps(all_data)


def generate_orchestrator_response_from_state(state: SharedAgentState) -> str:
    """Format a single-agent response for the user."""
    try:
        data = json.loads(state.result)
    except (json.JSONDecodeError, TypeError):
        return state.result or "I'm here. What would you like to work on?"

    if "error" in data:
        return f"Hmm, something went wrong: {data['error']}"

    prompt = SINGLE_FORMAT_PROMPT.format(
        query=state.query,
        data=json.dumps(data, indent=2),
    )
    result = format_with_llm(prompt)
    if result:
        return result
    if "message" in data:
        return data["message"]
    return state.result
