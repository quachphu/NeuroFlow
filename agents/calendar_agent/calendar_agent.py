import json
from datetime import datetime, timedelta

from agents.models.config import CALENDAR_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from agents.calendar_agent.calendar_mcp_server import mcp
from uagents import Agent, Context
from uagents_adapter import MCPServerAdapter

calendar_agent = Agent(
    name="neuroflow-calendar",
    seed=CALENDAR_SEED,
    port=8004,
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
        calendar_agent.include(proto, publish_manifest=True)


@calendar_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    from agents.calendar_agent.calendar_mcp_server import (
        get_events, get_free_blocks, get_upcoming_deadlines, create_event,
    )

    query = state.query.lower()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    is_plan = any(kw in query for kw in [
        "plan", "midterm", "exam", "study", "help me",
        "project due", "deadline", "prepare",
    ])

    if is_plan:
        state.result = _handle_plan_query(ctx, query, today)
    elif any(kw in query for kw in ["free", "available", "open", "block"]):
        date = _extract_date(query) or _resolve_day_name(query, today) or today_str
        state.result = get_free_blocks(date)
    elif any(kw in query for kw in ["deadline", "due", "upcoming"]):
        state.result = get_upcoming_deadlines(7)
    elif any(kw in query for kw in ["create", "add", "book"]):
        state.result = create_event(
            title="Study session", date=today_str,
            start="15:00", end="16:00",
            description="Auto-scheduled by NeuroFlow",
        )
    else:
        date = _extract_date(query) or _resolve_day_name(query, today) or today_str
        state.result = get_events(date)

    await ctx.send(sender, state)


def _handle_plan_query(ctx, query: str, today: datetime) -> str:
    """For plan queries: get deadlines, multi-day free blocks, auto-schedule study sessions."""
    from agents.calendar_agent.calendar_mcp_server import (
        get_events, get_free_blocks, get_upcoming_deadlines, create_event,
    )

    deadlines = json.loads(get_upcoming_deadlines(7))
    deadline_list = deadlines.get("deadlines", [])
    deadline_dates = {dl["date"] for dl in deadline_list}

    label = deadline_list[0]["title"] if deadline_list else "Upcoming Work"

    daily = []
    for i in range(1, 8):
        d = today + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        date_str = d.strftime("%Y-%m-%d")
        day_name = d.strftime("%A")
        is_deadline = date_str in deadline_dates

        events = json.loads(get_events(date_str))
        free = json.loads(get_free_blocks(date_str))
        daily.append({
            "day": day_name,
            "date": date_str,
            "events": events.get("events", []),
            "free_blocks": free.get("free_blocks", []),
            "total_free_min": free.get("total_free_minutes", 0),
            "is_deadline_day": is_deadline,
        })

    scheduled = []
    for day_info in daily:
        if day_info["is_deadline_day"]:
            continue

        best = _pick_best_study_block(day_info["free_blocks"])
        if not best:
            continue

        start = best["start"]
        sh, sm = map(int, start.split(":"))
        end_h = sh + 1
        if end_h > 22:
            continue
        end_time = f"{end_h:02d}:{sm:02d}"

        result = json.loads(create_event(
            title=f"Study: {label}",
            date=day_info["date"],
            start=start,
            end=end_time,
            description="Auto-scheduled by NeuroFlow",
        ))
        if result.get("created"):
            scheduled.append({
                "day": day_info["day"],
                "date": day_info["date"],
                "time": f"{start}-{end_time}",
                "title": f"Study: {label}",
            })

    return json.dumps({
        "action": "plan_data",
        "deadlines": deadlines,
        "daily_schedule": daily,
        "auto_scheduled_sessions": scheduled,
        "message": f"Found {len(scheduled)} study slots and created sessions on your Google Calendar.",
    })


def _pick_best_study_block(free_blocks: list[dict]) -> dict | None:
    """Pick the best free block for studying (prefer afternoon, >= 60 min)."""
    candidates = [b for b in free_blocks if b["duration_min"] >= 60]
    if not candidates:
        return None

    for b in candidates:
        hour = int(b["start"].split(":")[0])
        if 13 <= hour <= 17:
            return b

    for b in candidates:
        hour = int(b["start"].split(":")[0])
        if 9 <= hour <= 12:
            return b

    return candidates[0]


def _resolve_day_name(query: str, ref_date: datetime = None) -> str | None:
    """Resolve 'Monday', 'Thursday' etc. to YYYY-MM-DD relative to ref_date."""
    if ref_date is None:
        ref_date = datetime.now()

    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "mon": 0, "tues": 1, "tue": 1, "wed": 2,
        "thurs": 3, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    }

    lower = query.lower()
    if "today" in lower:
        return ref_date.strftime("%Y-%m-%d")
    if "tomorrow" in lower:
        return (ref_date + timedelta(days=1)).strftime("%Y-%m-%d")

    for name, weekday in sorted(day_map.items(), key=lambda x: -len(x[0])):
        if name in lower:
            days_ahead = (weekday - ref_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (ref_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return None


def _extract_date(query: str) -> str | None:
    """Try to find a YYYY-MM-DD date in the query."""
    import re
    match = re.search(r"\d{4}-\d{2}-\d{2}", query)
    return match.group(0) if match else None


if __name__ == "__main__":
    calendar_agent.run()
