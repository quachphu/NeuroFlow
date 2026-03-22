from agents.models.config import FOCUS_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from agents.focus_agent.focus_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

focus_agent = Agent(
    name="neuroflow-focus",
    seed=FOCUS_SEED,
    port=8002,
    mailbox=True,
    publish_agent_details=True,
)

if ASI1_API_KEY:
    mcp_adapter = MCPServerAdapter(
        mcp_server=mcp,
        asi1_api_key=ASI1_API_KEY,
        model="asi1-mini",
    )
    for proto in mcp_adapter.protocols:
        focus_agent.include(proto, publish_manifest=True)


@focus_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    # MCP adapter handles Chat Protocol messages automatically,
    # but for orchestrator routing via SharedAgentState, call tools directly
    from agents.focus_agent.focus_mcp_server import (
        start_session, end_session, capture_thought,
        get_focus_stats, get_captured_thoughts,
    )

    query = state.query.lower()

    if any(kw in query for kw in ["start", "begin", "focus"]):
        duration = 15
        task = state.query
        for word in query.split():
            if word.isdigit():
                duration = int(word)
                break
        state.result = start_session(duration, task)
    elif any(kw in query for kw in ["end", "done", "stop", "finished"]):
        rating = 3
        for word in query.split():
            if word.isdigit() and 1 <= int(word) <= 5:
                rating = int(word)
                break
        state.result = end_session("", rating)
    elif any(kw in query for kw in ["thought", "remember", "save", "capture"]):
        state.result = capture_thought(state.query)
    elif any(kw in query for kw in ["stats", "how much", "progress", "today"]):
        state.result = get_focus_stats()
    elif any(kw in query for kw in ["thoughts", "captured", "saved"]):
        state.result = get_captured_thoughts()
    else:
        state.result = get_focus_stats()

    await ctx.send(sender, state)


if __name__ == "__main__":
    focus_agent.run()
