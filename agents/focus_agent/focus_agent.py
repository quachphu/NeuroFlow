import json

from agents.models.config import FOCUS_SEED, ASI1_API_KEY, CALENDAR_ADDRESS, ADVISOR_ADDRESS
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
    ctx.logger.info(f"Received from {sender[:20]}...: session={state.chat_session_id}, query={state.query!r}")
    from agents.focus_agent.focus_mcp_server import (
        start_session, end_session, capture_thought,
        get_focus_stats, get_captured_thoughts,
    )

    query = state.query.lower()

    if state.chain_data:
        ctx.logger.info("Chain message from Advisor — building session plan from research")
        advisor_data = json.loads(state.chain_data)
        advice = advisor_data.get("advice", {})
        profile = advisor_data.get("profile", {})

        duration = advice.get("recommended_session_length", profile.get("preferred_session_length", 15))
        break_len = advice.get("recommended_break_length", 5)
        strategies = advice.get("strategies", [])
        task = state.query

        result_raw = start_session(duration, task)
        session_data = json.loads(result_raw)

        session_plan = {
            "session": session_data,
            "plan": {
                "duration_minutes": duration,
                "break_length": break_len,
                "strategies": strategies,
                "technique": strategies[0] if strategies else "Pomodoro",
                "task": task,
            },
            "advisor_data": advisor_data,
        }

        state.chain_data = json.dumps(session_plan)
        state.result = ""

        ctx.logger.info(f"Chaining: Focus → Calendar (session plan: {duration}min, forwarding)")
        await ctx.send(CALENDAR_ADDRESS, state)
        return

    if any(kw in query for kw in ["end", "done", "stop", "finished"]):
        rating = 3
        for word in query.split():
            if word.isdigit() and 1 <= int(word) <= 5:
                rating = int(word)
                break
        state.result = end_session("", rating)
        await ctx.send(sender, state)

    elif any(kw in query for kw in ["can't", "cannot", "overwhelm", "too much"]):
        state.result = get_focus_stats()
        await ctx.send(sender, state)

    elif any(kw in query for kw in ["stats", "how much", "progress", "today"]):
        state.result = get_focus_stats()
        await ctx.send(sender, state)

    elif any(kw in query for kw in ["thought", "remember", "save", "capture"]):
        state.result = capture_thought(state.query)
        await ctx.send(sender, state)

    else:
        state.result = get_focus_stats()
        await ctx.send(sender, state)


if __name__ == "__main__":
    focus_agent.run()
