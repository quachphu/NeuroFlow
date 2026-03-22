from fastmcp import FastMCP
from datetime import datetime, timedelta
import json
import os

mcp = FastMCP("NeuroFlowCalendar")

# --- Google Calendar API setup ---

CALENDAR_ID = os.getenv(
    "GOOGLE_CALENDAR_ID",
    "f08551114a49d70d6a91f8dfd98f7c9fd291941fb32c759fecf77180318d3fa5@group.calendar.google.com",
)

_gcal_service = None


def _get_gcal_service():
    """Lazy-init Google Calendar API client. Returns None if not configured."""
    global _gcal_service
    if _gcal_service is not None:
        return _gcal_service

    creds_path = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")

    if not os.path.exists(creds_path):
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        creds = None

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        _gcal_service = build("calendar", "v3", credentials=creds)
        return _gcal_service
    except Exception as e:
        print(f"Google Calendar not available: {e}")
        return None


def _gcal_get_events(date: str) -> list[dict] | None:
    """Fetch real events from Google Calendar for a given date."""
    service = _get_gcal_service()
    if not service:
        return None

    try:
        start = datetime.strptime(date, "%Y-%m-%d").isoformat() + "Z"
        end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).isoformat() + "Z"

        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for event in result.get("items", []):
            start_time = event["start"].get("dateTime", event["start"].get("date", ""))
            end_time = event["end"].get("dateTime", event["end"].get("date", ""))
            s = start_time[11:16] if "T" in start_time else "00:00"
            e = end_time[11:16] if "T" in end_time else "23:59"
            events.append({
                "title": event.get("summary", "Untitled"),
                "start": s,
                "end": e,
                "date": date,
                "type": "event",
            })
        return events
    except Exception:
        return None


def _gcal_create_event(title: str, date: str, start: str, end: str, description: str = "") -> dict | None:
    """Create a real event on Google Calendar."""
    service = _get_gcal_service()
    if not service:
        return None

    try:
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": f"{date}T{start}:00", "timeZone": "America/Los_Angeles"},
            "end": {"dateTime": f"{date}T{end}:00", "timeZone": "America/Los_Angeles"},
        }
        created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return {"created": True, "event_id": created["id"], "link": created.get("htmlLink", "")}
    except Exception:
        return None


# --- Mock calendar fallback (synced with Canvas course schedules) ---

# Course schedules matching Canvas mock data exactly
_COURSE_SCHEDULE = [
    # CS170: Data Structures & Algorithms — MWF 9:00-10:15
    {"title": "CS170 Lecture — Data Structures & Algorithms", "start": "09:00", "end": "10:15", "type": "class", "days": [0, 2, 4]},
    # CS105: Intro to Computer Science — MWF 14:00-15:15
    {"title": "CS105 Lecture — Intro to Computer Science", "start": "14:00", "end": "15:15", "type": "class", "days": [0, 2, 4]},
    # CS180: Introduction to Artificial Intelligence — TTh 10:00-11:15
    {"title": "CS180 Lecture — Introduction to Artificial Intelligence", "start": "10:00", "end": "11:15", "type": "class", "days": [1, 3]},
    # CS170 Discussion — Tue 10:00-10:50
    {"title": "CS170 Discussion", "start": "10:00", "end": "10:50", "type": "class", "days": [1]},
]

# Recurring personal events
_PERSONAL_SCHEDULE = [
    {"title": "Team Standup", "start": "11:00", "end": "11:30", "type": "personal", "days": [0]},  # Mon
    {"title": "Lunch", "start": "12:30", "end": "13:15", "type": "personal", "days": [0, 1, 2, 3, 4]},
    {"title": "AI Study Group", "start": "14:00", "end": "15:00", "type": "personal", "days": [1]},  # Tue
    {"title": "Gym", "start": "17:00", "end": "18:00", "type": "personal", "days": [0, 2, 4]},  # MWF
]

# Deadlines/exams from Canvas (one-off events)
_DEADLINE_EVENTS = [
    {"title": "CS105: Lab 4 File I/O Due", "start": "23:59", "end": "23:59", "date": "2026-03-25", "type": "deadline"},
    {"title": "CS180 AI Midterm", "start": "10:00", "end": "12:00", "date": "2026-03-26", "type": "exam"},
    {"title": "CS180: HW5 Search Algorithms Due", "start": "23:59", "end": "23:59", "date": "2026-03-28", "type": "deadline"},
    {"title": "CS170: HW5 Graph Algorithms Due", "start": "23:59", "end": "23:59", "date": "2026-03-30", "type": "deadline"},
    {"title": "CS170 Midterm Exam", "start": "09:00", "end": "11:00", "date": "2026-04-01", "type": "exam"},
    {"title": "CS105: PA3 OOP Basics Due", "start": "23:59", "end": "23:59", "date": "2026-04-02", "type": "deadline"},
    {"title": "CS170: Lab 6 Dijkstra Due", "start": "23:59", "end": "23:59", "date": "2026-04-02", "type": "deadline"},
    {"title": "CS180: Project Multi-Agent System Due", "start": "23:59", "end": "23:59", "date": "2026-04-10", "type": "deadline"},
    {"title": "CS170 Final Project Due", "start": "23:59", "end": "23:59", "date": "2026-04-15", "type": "deadline"},
]

# Dynamic mock events list (populated on first access + extended by create_event)
mock_events = []
_mock_generated = False


def _ensure_mock_events():
    """Generate 3 weeks of recurring class/personal events + deadlines."""
    global _mock_generated
    if _mock_generated:
        return
    _mock_generated = True

    base = datetime(2026, 3, 16)  # start from a Monday
    for week_offset in range(4):  # 4 weeks of events
        for day_offset in range(7):
            d = base + timedelta(days=week_offset * 7 + day_offset)
            weekday = d.weekday()
            date_str = d.strftime("%Y-%m-%d")

            # Skip weekends for classes
            if weekday >= 5:
                continue

            # Add recurring class events
            for course in _COURSE_SCHEDULE:
                if weekday in course["days"]:
                    # Skip if there's an exam replacing the lecture
                    exam_on_day = any(
                        e["date"] == date_str and e["type"] == "exam"
                        and e["title"].startswith(course["title"][:5])
                        for e in _DEADLINE_EVENTS
                    )
                    if not exam_on_day:
                        mock_events.append({
                            "title": course["title"],
                            "start": course["start"],
                            "end": course["end"],
                            "date": date_str,
                            "type": course["type"],
                        })

            # Add recurring personal events
            for personal in _PERSONAL_SCHEDULE:
                if weekday in personal["days"]:
                    mock_events.append({
                        "title": personal["title"],
                        "start": personal["start"],
                        "end": personal["end"],
                        "date": date_str,
                        "type": personal["type"],
                    })

    # Add one-off deadlines and exams
    mock_events.extend(_DEADLINE_EVENTS)


# --- MCP Tools ---

@mcp.tool()
def get_events(date: str) -> str:
    """Get all calendar events for a given date (YYYY-MM-DD)."""
    real_events = _gcal_get_events(date)
    if real_events is not None:
        return json.dumps({"date": date, "events": real_events, "source": "google_calendar"})

    _ensure_mock_events()
    day_events = [e for e in mock_events if e["date"] == date]
    return json.dumps({"date": date, "events": day_events, "source": "mock"})


@mcp.tool()
def get_free_blocks(date: str, day_start: str = "08:00", day_end: str = "22:00") -> str:
    """Get available time blocks for a date, excluding existing events."""
    real_events = _gcal_get_events(date)
    if real_events is None:
        _ensure_mock_events()
    day_events = real_events if real_events is not None else [e for e in mock_events if e["date"] == date]
    day_events = sorted(day_events, key=lambda x: x["start"])

    free = []
    current = day_start
    for event in day_events:
        if current < event["start"]:
            start_h, start_m = map(int, current.split(":"))
            end_h, end_m = map(int, event["start"].split(":"))
            duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
            free.append({"start": current, "end": event["start"], "duration_min": duration})
        current = max(current, event["end"])
    if current < day_end:
        start_h, start_m = map(int, current.split(":"))
        end_h, end_m = map(int, day_end.split(":"))
        duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
        free.append({"start": current, "end": day_end, "duration_min": duration})

    total = sum(b["duration_min"] for b in free)
    source = "google_calendar" if real_events is not None else "mock"
    return json.dumps({"date": date, "free_blocks": free, "total_free_minutes": total, "source": source})


@mcp.tool()
def get_upcoming_deadlines(days_ahead: int = 7) -> str:
    """Get exams and deadlines within the next N days."""
    today = datetime.now()
    upcoming = []

    real_service = _get_gcal_service()
    if real_service:
        try:
            start = today.isoformat() + "Z"
            end = (today + timedelta(days=days_ahead)).isoformat() + "Z"
            result = real_service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
                q="midterm OR exam OR due OR deadline",
            ).execute()
            for event in result.get("items", []):
                dt = event["start"].get("dateTime", event["start"].get("date", ""))
                date_str = dt[:10]
                days_until = (datetime.strptime(date_str, "%Y-%m-%d") - today).days
                upcoming.append({
                    "title": event.get("summary", "Untitled"),
                    "date": date_str,
                    "days_until": max(0, days_until),
                    "type": "deadline",
                })
            return json.dumps({"deadlines": upcoming, "source": "google_calendar"})
        except Exception:
            pass

    _ensure_mock_events()
    for i in range(days_ahead):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        day_events = [
            e for e in mock_events
            if e["date"] == date and e.get("type") in ("exam", "deadline")
        ]
        for event in day_events:
            event_copy = dict(event)
            event_copy["days_until"] = i
            upcoming.append(event_copy)
    return json.dumps({"deadlines": upcoming, "source": "mock"})


@mcp.tool()
def create_event(title: str, date: str, start: str, end: str, description: str = "") -> str:
    """Add a time block to the calendar (e.g., a study session)."""
    real_result = _gcal_create_event(title, date, start, end, description)
    if real_result:
        return json.dumps(real_result)

    _ensure_mock_events()
    event = {"title": title, "start": start, "end": end, "date": date, "description": description}
    mock_events.append(event)
    return json.dumps({"created": True, "event": event, "source": "mock"})
