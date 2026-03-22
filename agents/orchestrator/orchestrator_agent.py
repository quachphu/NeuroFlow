from datetime import datetime, timezone
from uuid import uuid4

from agents.models.config import ORCHESTRATOR_SEED
from agents.models.models import SharedAgentState
from agents.orchestrator.chat_protocol import (
    chat_proto, generate_orchestrator_response_from_state,
    generate_fanout_response,
)
from agents.services.state_service import state_service
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


class HealthResponse(Model):
    status: str


class HttpMessagePost(Model):
    content: str


class HttpMessageResponse(Model):
    response: str


@orchestrator.on_rest_get("/health", HealthResponse)
async def health(ctx: Context) -> HealthResponse:
    return HealthResponse(status="NeuroFlow orchestrator running")


@orchestrator.on_rest_post("/message", HttpMessagePost, HttpMessageResponse)
async def message(ctx: Context, req: HttpMessagePost) -> HttpMessageResponse:
    return HttpMessageResponse(response=f"Received: {req.content}")


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
