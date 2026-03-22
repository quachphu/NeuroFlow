import json
from datetime import datetime, timezone
from uuid import uuid4

from agents.models.config import ORCHESTRATOR_SEED, ADVISOR_ADDRESS, FOCUS_ADDRESS, CALENDAR_ADDRESS
from agents.models.models import SharedAgentState
from agents.orchestrator.chat_protocol import (
    chat_proto, classify_intent, generate_orchestrator_response_from_state,
    generate_fanout_response,
)
from agents.services.state_service import state_service, PendingFanOut
from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import ChatMessage, EndSessionContent, TextContent

orchestrator = Agent(
    name="neuroflow-orchestrator",
    seed=ORCHESTRATOR_SEED,
    port=8003,
    mailbox=True,
    publish_agent_details=True,
)

orchestrator.include(chat_proto, publish_manifest=True)

# ── Store completed agent responses for REST polling ──
# Each entry: {"response": str, "raw_data": dict}
_completed: dict[str, dict] = {}


class HealthResponse(Model):
    status: str


class HttpMessagePost(Model):
    content: str


class HttpMessageResponse(Model):
    session_id: str
    intent: str


class HttpResultRequest(Model):
    session_id: str


class HttpResultResponse(Model):
    ready: bool
    response: str
    raw_data: str = ""


@orchestrator.on_rest_get("/health", HealthResponse)
async def health(ctx: Context) -> HealthResponse:
    return HealthResponse(status="NeuroFlow orchestrator running")


@orchestrator.on_rest_post("/message", HttpMessagePost, HttpMessageResponse)
async def message(ctx: Context, req: HttpMessagePost) -> HttpMessageResponse:
    """Accept a user message via REST → trigger the real agent chain."""
    text = req.content
    session_id = str(uuid4())

    intent = classify_intent(text)
    ctx.logger.info(f"REST /message: '{text[:50]}' → intent={intent}, session={session_id[:8]}")

    state = SharedAgentState(
        chat_session_id=session_id,
        query=text,
        user_sender_address="rest-client",
        return_address=str(ctx.agent.address),
    )
    state_service.set_state(session_id, state)

    if intent == "study":
        fanout = PendingFanOut(
            expected_agents=[CALENDAR_ADDRESS],
            query=text,
            user_sender="rest-client",
        )
        fanout.intent = "study"
        state_service.start_fanout(session_id, fanout)
        await ctx.send(ADVISOR_ADDRESS, state)
        ctx.logger.info("REST chain: Advisor → Focus → Calendar (study)")

    elif intent == "focus":
        query_lower = text.lower()
        if any(kw in query_lower for kw in ["end", "stop", "done", "finish"]):
            await ctx.send(FOCUS_ADDRESS, state)
        else:
            fanout = PendingFanOut(
                expected_agents=[FOCUS_ADDRESS],
                query=text,
                user_sender="rest-client",
            )
            fanout.intent = "focus"
            state_service.start_fanout(session_id, fanout)
            await ctx.send(ADVISOR_ADDRESS, state)

    elif intent == "schedule":
        await ctx.send(CALENDAR_ADDRESS, state)

    elif intent == "overwhelm":
        fanout = PendingFanOut(
            expected_agents=[FOCUS_ADDRESS, ADVISOR_ADDRESS],
            query=text,
            user_sender="rest-client",
        )
        fanout.intent = "overwhelm"
        state_service.start_fanout(session_id, fanout)
        state_copy = SharedAgentState(
            chat_session_id=session_id,
            query=text,
            user_sender_address="rest-client",
        )
        await ctx.send(FOCUS_ADDRESS, state_copy)
        await ctx.send(ADVISOR_ADDRESS, state_copy)

    elif intent == "advisor":
        state.return_address = ""
        await ctx.send(ADVISOR_ADDRESS, state)

    elif intent == "status":
        fanout = PendingFanOut(
            expected_agents=[FOCUS_ADDRESS, CALENDAR_ADDRESS],
            query=text,
            user_sender="rest-client",
        )
        fanout.intent = "status"
        state_service.start_fanout(session_id, fanout)
        state_copy = SharedAgentState(
            chat_session_id=session_id,
            query=text,
            user_sender_address="rest-client",
        )
        await ctx.send(FOCUS_ADDRESS, state_copy)
        await ctx.send(CALENDAR_ADDRESS, state_copy)

    else:
        await ctx.send(ADVISOR_ADDRESS, state)

    return HttpMessageResponse(session_id=session_id, intent=intent)


@orchestrator.on_rest_post("/result", HttpResultRequest, HttpResultResponse)
async def result(ctx: Context, req: HttpResultRequest) -> HttpResultResponse:
    """Poll for a completed agent response."""
    if req.session_id in _completed:
        entry = _completed.pop(req.session_id)
        return HttpResultResponse(
            ready=True,
            response=entry.get("response", ""),
            raw_data=json.dumps(entry.get("raw_data", {})),
        )
    return HttpResultResponse(ready=False, response="")


@orchestrator.on_message(SharedAgentState)
async def handle_agent_response(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Response from {sender[:20]}...: {state.result[:80]!r}")

    fanout = state_service.get_fanout(state.chat_session_id)

    if fanout:
        fanout.add_response(sender, state.result)
        ctx.logger.info(
            f"Fan-out: {len(fanout.received)}/{len(fanout.expected_agents)} responses collected"
        )

        if fanout.is_complete:
            ctx.logger.info("Fan-out complete — combining responses")
            response = generate_fanout_response(fanout)
            state_service.clear_fanout(state.chat_session_id)

            # Extract raw data (sources, sessions, etc.) from agent responses
            raw_data = {}
            for addr, raw in fanout.received.items():
                try:
                    parsed = json.loads(raw)
                    raw_data.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Store for REST polling
            _completed[state.chat_session_id] = {"response": response, "raw_data": raw_data}

            # Also send to original sender if it's a real agent (not REST)
            if fanout.user_sender != "rest-client":
                await ctx.send(
                    fanout.user_sender,
                    ChatMessage(
                        timestamp=datetime.now(tz=timezone.utc),
                        msg_id=uuid4(),
                        content=[
                            TextContent(type="text", text=response),
                            EndSessionContent(type="end-session"),
                        ],
                    ),
                )
        return

    response = generate_orchestrator_response_from_state(state)

    # Extract raw data from state
    raw_data = {}
    try:
        raw_data = json.loads(state.result)
    except (json.JSONDecodeError, TypeError):
        pass

    # Store for REST polling
    _completed[state.chat_session_id] = {"response": response, "raw_data": raw_data}

    # Also send to original sender if it's a real agent (not REST)
    if state.user_sender_address != "rest-client":
        await ctx.send(
            state.user_sender_address,
            ChatMessage(
                timestamp=datetime.now(tz=timezone.utc),
                msg_id=uuid4(),
                content=[
                    TextContent(type="text", text=response),
                    EndSessionContent(type="end-session"),
                ],
            ),
        )


if __name__ == "__main__":
    orchestrator.run()
