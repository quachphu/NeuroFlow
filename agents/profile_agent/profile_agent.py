import json

from agents.models.config import PROFILE_SEED
from agents.models.models import SharedAgentState
from uagents import Agent, Context

profile_agent = Agent(
    name="neuroflow-profile",
    seed=PROFILE_SEED,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

DEFAULT_PROFILE = {
    "disability_type": "ADHD",
    "preferred_session_length": 15,
    "reading_grade_level": 8,
    "chunk_size": "small",
    "tone": "encouraging",
    "scheduling_capacity": 0.65,
    "format_preferences": {
        "use_bullet_points": True,
        "bold_key_terms": True,
        "max_paragraph_sentences": 3,
    },
}


def _get_profile(ctx: Context) -> dict:
    raw = ctx.storage.get("profile")
    if raw:
        return json.loads(raw)
    ctx.storage.set("profile", json.dumps(DEFAULT_PROFILE))
    return dict(DEFAULT_PROFILE)


def _save_profile(ctx: Context, profile: dict):
    ctx.storage.set("profile", json.dumps(profile))


@profile_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")

    query = state.query.lower()
    profile = _get_profile(ctx)

    if any(kw in query for kw in ["update", "set", "change"]):
        state.result = _handle_update(ctx, query, profile)
    else:
        state.result = json.dumps({
            "action": "profile",
            "profile": profile,
        })

    await ctx.send(sender, state)


def _handle_update(ctx: Context, query: str, profile: dict) -> str:
    updated = []

    if "dyslexia" in query:
        profile["disability_type"] = "dyslexia"
        profile["reading_grade_level"] = 6
        profile["chunk_size"] = "small"
        updated.append("disability_type=dyslexia, reading_grade_level=6")
    elif "autism" in query:
        profile["disability_type"] = "autism"
        profile["tone"] = "precise"
        updated.append("disability_type=autism, tone=precise")
    elif "adhd" in query:
        profile["disability_type"] = "ADHD"
        profile["tone"] = "encouraging"
        updated.append("disability_type=ADHD, tone=encouraging")

    for length in [10, 15, 20, 25, 30, 45]:
        if str(length) in query and ("min" in query or "session" in query):
            profile["preferred_session_length"] = length
            updated.append(f"preferred_session_length={length}")
            break

    if updated:
        _save_profile(ctx, profile)
        return json.dumps({
            "action": "profile_updated",
            "updated_fields": updated,
            "profile": profile,
        })

    return json.dumps({
        "action": "profile",
        "profile": profile,
        "message": "No changes detected. Current profile returned.",
    })


if __name__ == "__main__":
    profile_agent.run()
