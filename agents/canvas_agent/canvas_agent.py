import json

from agents.models.config import CANVAS_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from agents.canvas_agent.canvas_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

canvas_agent = Agent(
    name="neuroflow-canvas",
    seed=CANVAS_SEED,
    port=8006,
    endpoint=["http://127.0.0.1:8006/submit"],
)

if ASI1_API_KEY:
    mcp_adapter = MCPServerAdapter(
        mcp_server=mcp,
        asi1_api_key=ASI1_API_KEY,
        model="asi1-mini",
    )
    for proto in mcp_adapter.protocols:
        canvas_agent.include(proto, publish_manifest=True)


@canvas_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    from agents.canvas_agent.canvas_mcp_server import (
        get_courses, get_assignments, get_grades, get_syllabus,
    )

    query = state.query.lower()
    course_id = _extract_course(query)

    if any(kw in query for kw in ["grade", "score", "gpa", "how am i doing"]):
        if course_id:
            state.result = get_grades(course_id)
        else:
            state.result = get_courses()

    elif any(kw in query for kw in ["assignment", "due", "homework", "hw", "deadline"]):
        if course_id:
            state.result = get_assignments(course_id)
        else:
            all_assignments = []
            for cid in ["CS170", "CS105", "ECON101"]:
                data = json.loads(get_assignments(cid))
                for a in data.get("assignments", []):
                    a["course_id"] = cid
                    all_assignments.append(a)
            all_assignments.sort(key=lambda x: x["due"])
            state.result = json.dumps({"assignments": all_assignments})

    elif any(kw in query for kw in ["syllabus", "topic", "exam", "midterm", "what's covered"]):
        if course_id:
            state.result = get_syllabus(course_id)
        else:
            state.result = get_syllabus("CS170")

    elif any(kw in query for kw in [
        "transcri", "lecture", "record", "search algorithm", "a*", "a star",
        "heuristic", "bfs", "dfs",
    ]):
        state.result = get_syllabus(course_id or "CS170")

    else:
        state.result = get_courses()

    await ctx.send(sender, state)


def _extract_course(query: str) -> str | None:
    q = query.upper()
    if "CS170" in q or "CS 170" in q or "DATA STRUCT" in q or "ALGORITHM" in q:
        return "CS170"
    if "CS105" in q or "CS 105" in q:
        return "CS105"
    if "EE120" in q or "EE 120" in q or "SIGNAL" in q or "SYSTEMS" in q:
        return "EE120"
    if "ECON" in q:
        return "ECON101"
    return None


if __name__ == "__main__":
    canvas_agent.run()
