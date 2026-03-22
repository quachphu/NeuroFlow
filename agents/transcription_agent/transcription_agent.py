import json
import os

from agents.models.config import TRANSCRIPTION_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from agents.transcription_agent.transcription_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

transcription_agent = Agent(
    name="neuroflow-transcription",
    seed=TRANSCRIPTION_SEED,
    port=8005,
    endpoint=["http://127.0.0.1:8005/submit"],
)

if ASI1_API_KEY:
    mcp_adapter = MCPServerAdapter(
        mcp_server=mcp,
        asi1_api_key=ASI1_API_KEY,
        model="asi1-mini",
    )
    for proto in mcp_adapter.protocols:
        transcription_agent.include(proto, publish_manifest=True)


DEMO_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "demo_audio")


@transcription_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    from agents.transcription_agent.transcription_mcp_server import (
        transcribe_audio, get_transcript, get_recent, search_transcript,
    )

    query = state.query.lower()

    if any(kw in query for kw in ["transcri", "record", "just recorded", "lecture audio"]):
        audio_path = _find_demo_audio()
        state.result = transcribe_audio(audio_path)

    elif any(kw in query for kw in ["what did", "professor say", "say about", "explain", "clarify"]):
        concept = _extract_concept(query)
        if concept:
            state.result = search_transcript(concept)
        else:
            state.result = get_transcript()

    elif any(kw in query for kw in ["last", "recent", "past"]):
        minutes = 5
        for n in [3, 5, 10, 15]:
            if str(n) in query:
                minutes = n
                break
        state.result = get_recent(minutes)

    elif any(kw in query for kw in ["full transcript", "whole transcript", "all of it"]):
        state.result = get_transcript()

    else:
        state.result = get_transcript()

    await ctx.send(sender, state)


def _find_demo_audio() -> str:
    for ext in [".wav", ".mp3", ".m4a", ".webm"]:
        for fname in os.listdir(DEMO_AUDIO_DIR):
            if fname.endswith(ext):
                return os.path.join(DEMO_AUDIO_DIR, fname)
    return ""


def _extract_concept(query: str) -> str | None:
    """Pull out the concept the user is asking about."""
    markers = ["about", "say about", "explain", "clarify", "mean by"]
    lower = query.lower()
    for marker in markers:
        if marker in lower:
            idx = lower.index(marker) + len(marker)
            rest = query[idx:].strip().strip("?").strip('"').strip("'")
            if rest:
                return rest
    return None


if __name__ == "__main__":
    transcription_agent.run()
