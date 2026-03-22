# NeuroFlow — Final Build Plan

## BeachHacks 2026 · Fetch.ai Track

**One-liner:** A multi-agent ADHD study companion where each agent owns real data — your calendar, your focus sessions, your task list — and coordinates to produce responses no single LLM could generate.

**Pitch:** "1 in 9 adults has ADHD. Existing tools help in isolation — a calendar here, a timer there, a to-do list somewhere else. But ADHD brains don't fail at one thing, they fail at *coordinating* all of them. NeuroFlow is a team of AI agents that each track a different part of your day and work together to keep you on track — using your real calendar, real focus data, and real task progress."

---

## Why This Wins

**Passes the collapse test.** If you collapse all agents into one, you lose the ability to simultaneously hold real calendar data + real timer state + real task progress. A single LLM can't check your Google Calendar, track a running timer, AND remember you're on step 6 of 14. Each agent owns a different piece of real state.

**Matches winner complexity.** StartNOW won with ~4 agents, a Flask backend, event-driven messaging, and a React frontend. We have 4 agents, MCP tool integration, Chat Protocol, and real external system access (Google Calendar). Similar scope, more substance.

**Strong demo.** It's an interactive loop, not a one-shot. Over 3-4 minutes you show: plan → focus → capture thought → complete session → adapt. Every response visibly requires data from multiple agents.

**Empty niche.** Zero accessibility or ADHD agents on Agentverse.

---

## Architecture

```
User (Agentverse "Chat with Agent" or ASI:One)
    │
    ▼
┌──────────────────────────────────────────┐
│         ORCHESTRATOR                     │
│                                          │
│  Talks to user. On every message:        │
│  1. Classifies intent                    │
│  2. Pulls data from relevant agents      │
│  3. Combines into a response that        │
│     requires data from multiple sources  │
└──────┬──────────┬──────────┬─────────────┘
       │          │          │
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ CALENDAR │ │  FOCUS   │ │   TASK   │
│  AGENT   │ │  AGENT   │ │  AGENT   │
│          │ │          │ │          │
│ Owns:    │ │ Owns:    │ │ Owns:    │
│ Google   │ │ Timer    │ │ Task     │
│ Calendar │ │ Sessions │ │ lists    │
│ via MCP  │ │ Streaks  │ │ Steps    │
│          │ │ Captured │ │ Progress │
│ Can:     │ │ thoughts │ │          │
│ Read     │ │ via MCP  │ │ Can:     │
│ events,  │ │          │ │ Decompose│
│ find free│ │ Can:     │ │ tasks,   │
│ blocks,  │ │ Start/   │ │ track    │
│ create   │ │ stop     │ │ steps,   │
│ events   │ │ timer,   │ │ mark     │
│          │ │ capture  │ │ complete │
│          │ │ thoughts,│ │          │
│          │ │ log      │ │          │
│          │ │ sessions │ │          │
└──────────┘ └──────────┘ └──────────┘
  MCP Server   MCP Server   Agent State
  (Calendar)   (Focus)      (ctx.storage)
```

---

## The 4 Agents — What Each Does

### Agent 1: Orchestrator

**What it is:** The only agent the user talks to. Coordinates the other three.

**What it does on every message:**
1. Classifies intent (plan my day / help me focus / what's next / I'm done / I'm struggling)
2. Sends requests to the relevant specialist agents
3. Combines their responses into a single reply that requires data from multiple sources

**Why it can't be replaced by a single LLM:** It synthesizes real-time data from three separate systems. When you say "what should I do next?" it checks: Calendar Agent ("you have 2 hours before your lecture"), Focus Agent ("you've done 30 min of focus today, ratings declining"), and Task Agent ("step 6 of 14, next step is easy"). The response requires all three.

**Overwhelm handling:** If user language signals shutdown ("I can't do this," "everything is too much"), the orchestrator pulls stats from Focus Agent (what you've already accomplished today) and responds with acknowledgment + one tiny next action OR permission to stop. This is the ADHD-specific touch.

**Implementation:**
- uAgents framework, local agent with mailbox
- Chat Protocol v0.3.0
- Uses ASI:One API for intent classification
- Communicates with specialists via ctx.send()
- ctx.storage for session continuity

---

### Agent 2: Calendar Agent

**What it is:** The agent that knows your real schedule.

**What it owns:** Connection to Google Calendar (or mock calendar for demo) via MCP.

**MCP Tools (4):**

```python
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
import json

mcp = FastMCP("NeuroFlowCalendar")

# Mock calendar — realistic college student schedule
mock_events = [
    {"title": "CS170 Lecture", "start": "09:00", "end": "10:15",
     "date": "2026-03-22", "type": "class"},
    {"title": "Team standup", "start": "11:00", "end": "11:30",
     "date": "2026-03-22", "type": "meeting"},
    {"title": "Lunch", "start": "12:30", "end": "13:15",
     "date": "2026-03-22", "type": "personal"},
    {"title": "CS105 Lecture", "start": "14:00", "end": "15:15",
     "date": "2026-03-22", "type": "class"},
    {"title": "Gym", "start": "17:00", "end": "18:00",
     "date": "2026-03-22", "type": "personal"},
    {"title": "AI Midterm", "start": "10:00", "end": "12:00",
     "date": "2026-03-26", "type": "exam"},
    {"title": "CS Project Due", "start": "23:59", "end": "23:59",
     "date": "2026-03-27", "type": "deadline"},
]

@mcp.tool()
def get_events(date: str) -> str:
    """Get all calendar events for a given date (YYYY-MM-DD)."""
    day_events = [e for e in mock_events if e["date"] == date]
    return json.dumps({"date": date, "events": day_events})

@mcp.tool()
def get_free_blocks(date: str, day_start: str = "08:00",
                    day_end: str = "22:00") -> str:
    """Get available time blocks for a date, excluding existing events."""
    day_events = sorted(
        [e for e in mock_events if e["date"] == date],
        key=lambda x: x["start"]
    )
    free = []
    current = day_start
    for event in day_events:
        if current < event["start"]:
            start_h, start_m = map(int, current.split(":"))
            end_h, end_m = map(int, event["start"].split(":"))
            duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
            free.append({
                "start": current, "end": event["start"],
                "duration_min": duration
            })
        current = max(current, event["end"])
    if current < day_end:
        start_h, start_m = map(int, current.split(":"))
        end_h, end_m = map(int, day_end.split(":"))
        duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
        free.append({
            "start": current, "end": day_end,
            "duration_min": duration
        })
    total = sum(b["duration_min"] for b in free)
    return json.dumps({
        "date": date, "free_blocks": free,
        "total_free_minutes": total
    })

@mcp.tool()
def get_upcoming_deadlines(days_ahead: int = 7) -> str:
    """Get exams and deadlines within the next N days."""
    today = datetime.now()
    upcoming = []
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
    return json.dumps({"deadlines": upcoming})

@mcp.tool()
def create_event(title: str, date: str, start: str,
                 end: str, description: str = "") -> str:
    """Add a time block to the calendar."""
    event = {
        "title": title, "start": start, "end": end,
        "date": date, "description": description
    }
    mock_events.append(event)
    return json.dumps({"created": True, "event": event})
```

**Why this can't be a single LLM:** ChatGPT doesn't know you have CS170 at 9 AM. It can't find that you have a 45-minute gap between 10:15 and 11:00. It can't see your midterm is in 4 days. This agent has real data.

---

### Agent 3: Focus Agent

**What it is:** The agent that tracks your focus sessions, captured thoughts, and energy trends.

**What it owns:** A running timer, session history, captured thoughts, streak data — all via MCP.

**MCP Tools (5):**

```python
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
import json

mcp = FastMCP("NeuroFlowFocus")

sessions = {}
captured_thoughts = []
history = []  # completed sessions

@mcp.tool()
def start_session(duration_minutes: int = 15,
                  task_name: str = "") -> str:
    """Start a focus session with a timer. Default 15 min."""
    session_id = f"s_{datetime.now().strftime('%H%M%S')}"
    sessions[session_id] = {
        "started": datetime.now().isoformat(),
        "duration": duration_minutes,
        "task": task_name,
        "end_time": (
            datetime.now() + timedelta(minutes=duration_minutes)
        ).isoformat(),
        "status": "active"
    }
    return json.dumps({
        "session_id": session_id,
        "duration": duration_minutes,
        "task": task_name
    })

@mcp.tool()
def capture_thought(thought: str) -> str:
    """Save a distracting thought without breaking focus.
    Thoughts are returned after the session ends."""
    captured_thoughts.append({
        "thought": thought,
        "time": datetime.now().isoformat()
    })
    return json.dumps({
        "saved": True,
        "total_captured": len(captured_thoughts)
    })

@mcp.tool()
def end_session(session_id: str, rating: int = 3) -> str:
    """End a focus session with a 1-5 rating.
    Returns session stats and any captured thoughts."""
    if session_id not in sessions:
        return json.dumps({"error": "Session not found"})
    session = sessions.pop(session_id)
    duration = session["duration"]

    # Adaptive next duration
    if rating <= 2:
        next_dur = max(5, duration - 5)
    elif rating >= 4:
        next_dur = min(45, duration + 5)
    else:
        next_dur = duration

    entry = {
        "duration": duration, "rating": rating,
        "task": session["task"],
        "time": datetime.now().isoformat()
    }
    history.append(entry)

    # Collect and clear captured thoughts
    thoughts = [t["thought"] for t in captured_thoughts]
    captured_thoughts.clear()

    return json.dumps({
        "duration": duration,
        "rating": rating,
        "sessions_today": len(history),
        "total_focus_min": sum(h["duration"] for h in history),
        "avg_rating": round(
            sum(h["rating"] for h in history) / len(history), 1
        ),
        "suggested_next_duration": next_dur,
        "captured_thoughts": thoughts
    })

@mcp.tool()
def get_focus_stats() -> str:
    """Get today's focus statistics."""
    if not history:
        return json.dumps({
            "sessions_today": 0,
            "total_focus_min": 0,
            "message": "No sessions yet today"
        })
    return json.dumps({
        "sessions_today": len(history),
        "total_focus_min": sum(h["duration"] for h in history),
        "avg_rating": round(
            sum(h["rating"] for h in history) / len(history), 1
        ),
        "ratings_trend": [h["rating"] for h in history],
        "tasks_worked_on": [h["task"] for h in history]
    })

@mcp.tool()
def get_captured_thoughts() -> str:
    """Get any thoughts captured during the current session."""
    return json.dumps({
        "thoughts": [t["thought"] for t in captured_thoughts],
        "count": len(captured_thoughts)
    })
```

**Why this can't be a single LLM:** ChatGPT can say "I started a timer" but nothing is actually running. It can't tell you "you've done 45 minutes of focus today across 3 sessions with declining ratings." It can't store a thought and return it later. This agent has real persistent state.

---

### Agent 4: Task Agent

**What it is:** The agent that owns your task list, breaks tasks into steps, and tracks progress.

**What it owns:** Task decompositions and completion state in ctx.storage.

**No MCP — just agent state + LLM.** This is intentional. Not everything needs an MCP server. The Task Agent uses ASI:One to decompose tasks and ctx.storage to persist them. This keeps the build simple and shows judges you use MCP where it makes sense (external tools) and agent state where that makes sense (internal data).

**Core logic:**
- Receives a task description → calls ASI:One with a decomposition prompt → stores steps in ctx.storage
- Tracks which steps are done, which are next
- Returns progress stats (6 of 14 done, next step is "add screenshots to README")
- System prompt enforces: steps start with verbs, max 15 min each, first 2 steps are trivially easy (activation runway for ADHD), breaks every 3-4 steps

**Why this can't be a single LLM:** ChatGPT would re-decompose the task every time you ask. It has no memory that you completed steps 1-5 already. This agent persists your progress.

---

## What Makes It ADHD (Not Just Productivity)

Let's be honest: the multi-agent coordination is the tech. The ADHD angle is the story and application design. Here's how we make the ADHD framing feel genuine:

**1. Activation runways in task decomposition.** Every task breakdown starts with 2 stupidly easy steps. Not "research your topic" but "open Google Scholar and type one keyword." This is a well-documented ADHD strategy — you lower the activation energy to near zero.

**2. Distraction capture.** Mid-focus-session thought saving is THE #1 requested ADHD feature. Your research doc confirms: "ADHD's fleeting thoughts vanish in seconds." The Focus Agent's `capture_thought` tool addresses this directly. You don't break focus, the thought is safe, you get it back after the session.

**3. Never punishing.** From your doc: Tiimo won Apple's App of the Year because "nothing turns red or punishes you for unfinished tasks." Our orchestrator never says "you only did 3 of 14 steps." It says "you did 3 steps and 45 minutes of focus today, that's real progress."

**4. Overwhelm detection.** When the user says "I can't," the orchestrator doesn't push harder. It acknowledges, lists what was already accomplished (pulling real data from Focus Agent), and either offers the smallest possible next action or says "you've done enough today."

**5. Adaptive session length.** Standard Pomodoro is 25 min — too long for many ADHD brains. We start at 15, adjust based on ratings. Bad sessions get shorter, not abandoned. From the doc: the key is reducing friction, not building discipline.

**6. Scheduling at 60-70% capacity.** The Schedule Builder never fills every free block. It leaves buffer time. Over-scheduling guarantees failure for ADHD.

These are design choices, not agent architecture choices. But they're what make the pitch land.

---

## Example Full Session (Demo Flow)

This is what you'd show in the 5-minute demo video, or live at the Agentverse "Chat with Agent" page.

**User:** "I have an AI midterm Thursday and a CS project README due Friday. I haven't started either. Help."

**NeuroFlow:**
```
Let me check your schedule and plan this out.

📅 Calendar check:
  - Today (Sunday): Free 1 PM - 5 PM, gym at 5
  - Monday: CS170 lecture 9-10:15, free afternoon
  - Tuesday: Team meeting 2 PM (you'll need README progress by then)
  - Thursday: AI Midterm at 10 AM ⚠️ 4 days away
  - Friday: CS Project due at midnight

📋 I've broken both tasks into steps:
  
  AI Midterm (14 steps):
  → Step 1 (2 min) 🟢 Open your lecture slides folder
  → Step 2 (2 min) 🟢 Create a new doc titled "AI Cheat Sheet"
  → Step 3 (10 min) 🟡 Skim Unit 1 slides, write down key formulas
  → Step 4 (10 min) 🟡 Do 2 practice problems from Unit 1
  → Step 5 (5 min) 🟢 Take a break
  [showing 5 of 14]

  CS README (8 steps):
  [saved for later — midterm is more urgent]

📌 Suggestion for right now:
  You have 4 hours free. Start with midterm steps 1-2 (they take 
  4 minutes total). Want me to start a focus session?
```

*Behind the scenes: Orchestrator → Calendar Agent (get_events, get_free_blocks, get_upcoming_deadlines) + Task Agent (decompose both tasks). Combined into one response with real calendar data and ADHD-friendly first steps.*

---

**User:** "yeah let's go"

**NeuroFlow:**
```
🎯 Focus session started — 15 minutes
📝 Working on: AI midterm steps 1-3

Go open those lecture slides. I'm here if you need anything.

💡 Random thought pop up? Just tell me and I'll save it.
```

*Behind the scenes: Orchestrator → Focus Agent (start_session(15, "AI midterm steps 1-3")) + Task Agent (mark steps 1-3 as in-progress).*

---

**User:** "oh wait I need to text my team about the meeting Tuesday"

**NeuroFlow:**
```
💭 Saved: "text team about Tuesday meeting"

You'll get this back after your session. Timer still running — 
11 minutes left. Back to those slides.
```

*Behind the scenes: Orchestrator → Focus Agent (capture_thought("text team about Tuesday meeting")). Timer uninterrupted.*

---

**User:** "ok I'm done, went pretty well, 4 out of 5"

**NeuroFlow:**
```
🔥 Session complete! 15 min on AI midterm.

📊 Your stats:
  Sessions today: 1 | Total focus: 15 min | Rating: 4/5
  Next suggested session: 20 min (bumped up since that went well)

📋 Progress: Steps 1-3 of 14 done (midterm)

💭 Captured thought: "text team about Tuesday meeting"
  → Want to do that now? (2 min, quick win)

⏰ You have 3 hrs 40 min before gym.

Ready for steps 4-5? Or take a break first?
```

*Behind the scenes: Orchestrator → Focus Agent (end_session(rating=4), returns stats + captured thoughts + next duration) + Task Agent (mark steps 1-3 complete, get next steps) + Calendar Agent (time remaining). All combined.*

---

**User:** "let me text the team real quick then keep going"

**NeuroFlow:**
```
Go for it. When you're ready, say "focus" and I'll start a 
20-minute session on steps 4-5.
```

---

**User (later, after 2 more sessions):** "I'm done, I can't focus anymore"

**NeuroFlow:**
```
That's okay. Look at what you actually did today:

  ✅ 3 focus sessions (50 minutes total)
  ✅ 8 of 14 midterm steps complete
  ✅ Cheat sheet started with Units 1-3
  ✅ Texted your team about Tuesday

You covered more than half your midterm prep in one afternoon. 
The remaining 6 steps + your README fit into Monday and 
Tuesday's free blocks.

Rest up. You earned it.
```

*Behind the scenes: Orchestrator → Focus Agent (get_focus_stats: 3 sessions, 50 min, ratings 4,3,3) + Task Agent (8/14 complete) + Calendar Agent (Monday and Tuesday have enough free blocks for remaining work). Combined into an encouraging, data-backed summary.*

---

## Project Structure

```
neuroflow/
├── agents/
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── orchestrator_agent.py
│   ├── calendar_agent/
│   │   ├── __init__.py
│   │   ├── calendar_agent.py
│   │   └── calendar_mcp_server.py
│   ├── focus_agent/
│   │   ├── __init__.py
│   │   ├── focus_agent.py
│   │   └── focus_mcp_server.py
│   └── task_agent/
│       ├── __init__.py
│       └── task_agent.py
├── .env.example
├── .gitignore
├── Makefile
├── requirements.txt
└── README.md
```

Intentionally flat. No `models/`, no `services/`, no `dashboard/`. Four agents, two MCP servers, one Makefile. That's it.

---

## MCP Wrapping Pattern

Both MCP servers use the same pattern:

```python
# In calendar_agent.py
from uagents import Agent
from uagents_adapter import MCPServerAdapter
from calendar_mcp_server import mcp  # FastMCP instance

mcp_adapter = MCPServerAdapter(
    mcp_server=mcp,
    asi1_api_key=os.getenv("ASI1_API_KEY"),
    model="asi1"
)

agent = Agent(
    name="neuroflow-calendar",
    port=8001,
    seed=os.getenv("CALENDAR_SEED"),
    endpoint=["http://localhost:8001/submit"],
    mailbox=True
)

mcp_adapter.register(agent)

if __name__ == "__main__":
    agent.run()
```

Same pattern for focus_agent.py with the focus MCP server.

---

## 24-Hour Sprint

### Phase 1: Foundation (Hour 0-2)

- [ ] Create GitHub repo
- [ ] Set up project structure (see above)
- [ ] `pip install uagents uagents-adapter fastmcp cosmpy python-dotenv httpx openai`
- [ ] Create `.env` with API keys + 4 seed phrases
- [ ] Write Makefile (make orchestrator / calendar / focus / task)
- [ ] Test a basic hello-world uAgent → inspector link → connect to mailbox
- [ ] Create Agentverse + ASI:One accounts, get API keys

### Phase 2: Specialist Agents (Hour 2-8)

**Hour 2-4: Task Agent (simplest, no MCP, proves the pattern)**
- [ ] Build task_agent.py with Chat Protocol v0.3.0
- [ ] Write system prompt for ASI:One: decomposition rules (verb-first, max 15 min, activation runway, breaks every 3-4 steps)
- [ ] Implement ctx.storage for persisting task lists + completion tracking
- [ ] Test: send it "write a research paper" → get steps back
- [ ] Test: send "mark step 3 done" → get updated progress
- [ ] Register on Agentverse → write README → test "Chat with Agent"
- [ ] Note down agent address

**Hour 4-6: Focus Agent + Focus MCP**
- [ ] Build focus_mcp_server.py with 5 tools (start_session, capture_thought, get_captured_thoughts, end_session, get_focus_stats)
- [ ] Test MCP server standalone
- [ ] Build focus_agent.py with MCPServerAdapter
- [ ] Register on Agentverse → write README → test "Chat with Agent"
- [ ] Test: start a session → capture a thought → end with rating → check stats
- [ ] Note down agent address

**Hour 6-8: Calendar Agent + Calendar MCP**
- [ ] Build calendar_mcp_server.py with 4 tools and realistic mock data for demo day
- [ ] Build calendar_agent.py with MCPServerAdapter
- [ ] Register on Agentverse → write README → test "Chat with Agent"
- [ ] Test: get_events → get_free_blocks → get_upcoming_deadlines
- [ ] Note down agent address

### Phase 3: Orchestrator (Hour 8-12)

**Hour 8-10: Core orchestrator**
- [ ] Build orchestrator_agent.py with Chat Protocol
- [ ] Intent classification via ASI:One (simple prompt: classify as plan/focus/progress/done/struggling)
- [ ] Wire up ctx.send() to all 3 specialist agents
- [ ] Handle responses from specialists and combine them
- [ ] Add overwhelm detection (keyword check + LLM confirmation)

**Hour 10-12: Integration testing**
- [ ] Run all 4 agents in 4 terminals
- [ ] Test the full demo flow end-to-end:
  - "Plan my afternoon" → pulls calendar + decomposes tasks
  - "Start a focus session" → starts timer
  - "I need to remember X" → captures thought
  - "Done, 4/5" → ends session, returns stats + thoughts + next steps
  - "I can't anymore" → overwhelm response with real stats
- [ ] Fix timing issues, message format issues
- [ ] Register orchestrator on Agentverse with detailed README
- [ ] Test via "Chat with Agent" on the orchestrator

### Phase 4: Polish + Discovery (Hour 12-15)

- [ ] Polish all 4 Agentverse READMEs with detailed descriptions, example queries, tags
- [ ] Add Innovation Lab badges to all READMEs
- [ ] Test ASI:One discovery: toggle Agents, ask about ADHD/focus/study planning
- [ ] Improve LLM prompts based on testing (better response formatting, tone)
- [ ] Add more mock calendar events to make demo feel realistic
- [ ] Run the full demo flow 2-3 times to find rough edges

### Phase 5: Demo + Submission (Hour 15-20)

**Hour 15-17: Demo video (5 min)**
- [ ] Script:
  - 0:00-0:30 — Hook: "1 in 9 adults has ADHD. The problem isn't intelligence, it's coordination."
  - 0:30-1:15 — Architecture: 4 agents, 2 MCP integrations, show Agentverse with all agents active
  - 1:15-3:45 — Live demo: the full session flow (plan → focus → capture → complete → adapt → overwhelm)
  - 3:45-4:30 — Show ASI:One discovering the agents. Show agent logs with inter-agent messages.
  - 4:30-5:00 — Close: accessibility niche is empty, NeuroFlow fills it.
- [ ] Record with OBS or screen recording
- [ ] Upload to YouTube (unlisted)

**Hour 17-19: GitHub README + Devpost**
- [ ] Write GitHub README (see template below)
- [ ] Devpost:
  - Inspiration: personal angle on ADHD / executive dysfunction
  - What it does: non-technical explanation
  - How we built it: Fetch.ai stack details
  - Challenges
  - What we learned
  - Built with: fetchai, uagents, agentverse, asi-one, fastmcp, python
  - Screenshots + demo video
- [ ] Submit

**Hour 19-24: Buffer**
- [ ] Fix last-minute bugs
- [ ] Pre-record backup demo in case agents are down during judging
- [ ] Practice live pitch if applicable
- [ ] Sleep

---

## Makefile

```makefile
.PHONY: orchestrator calendar focus task

task:
	cd agents/task_agent && python task_agent.py

focus:
	cd agents/focus_agent && python focus_agent.py

calendar:
	cd agents/calendar_agent && python calendar_agent.py

orchestrator:
	cd agents/orchestrator && python orchestrator_agent.py

all:
	@echo "Run each in a separate terminal:"
	@echo "  make task         # Terminal 1"
	@echo "  make focus        # Terminal 2"
	@echo "  make calendar     # Terminal 3"
	@echo "  make orchestrator # Terminal 4 (start last)"
```

---

## .env.example

```bash
# ASI:One (asi1.ai → API Keys tab)
ASI1_API_KEY=your_key

# Agentverse (agentverse.ai → settings)
AGENTVERSE_API_KEY=your_key

# Agent seeds (random strings, no spaces)
ORCHESTRATOR_SEED=mash_your_keyboard_here_1
TASK_SEED=mash_your_keyboard_here_2
FOCUS_SEED=mash_your_keyboard_here_3
CALENDAR_SEED=mash_your_keyboard_here_4

# Fallback LLM
OPENAI_API_KEY=your_key
```

---

## requirements.txt

```
uagents>=0.20.0
uagents-adapter
fastmcp
cosmpy
python-dotenv
openai
httpx
pydantic
```

---

## GitHub README

```markdown
# NeuroFlow 🧠⚡

**A multi-agent ADHD study companion built on Fetch.ai**

> BeachHacks 2026 · Fetch.ai Track

NeuroFlow is a team of 4 AI agents that each own a different piece of your 
day — your calendar, your focus sessions, your task list — and coordinate 
to keep you on track. Every response combines real data from multiple 
agents, producing recommendations no single LLM could generate.

Built for people with ADHD and executive dysfunction: activation runways, 
distraction capture, adaptive session timing, overwhelm detection, and 
scheduling at 60-70% capacity.

![tag : innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag : accessibility](https://img.shields.io/badge/accessibility-4CAF50)
![tag : chatprotocol](https://img.shields.io/badge/chatprotocol-2196F3)

## Demo

[🎥 5-minute demo video](YOUR_LINK)

## Agents

| Agent | Address | Owns | Tech |
|-------|---------|------|------|
| Orchestrator | `agent1q...` | Session coordination, overwhelm detection | uAgent + Chat Protocol |
| Calendar Agent | `agent1q...` | Real schedule data | MCP (FastMCP + MCPServerAdapter) |
| Focus Agent | `agent1q...` | Timer, sessions, captured thoughts | MCP (FastMCP + MCPServerAdapter) |
| Task Agent | `agent1q...` | Task decomposition, step progress | uAgent + ctx.storage |

## Why Multi-Agent?

Every response the orchestrator gives requires data from multiple agents:

- "What should I do next?" → needs calendar (time available) + tasks 
  (what's remaining) + focus (your energy level)
- "I'm done with my session" → needs focus (log it, get stats) + tasks 
  (mark steps complete) + calendar (what's coming up next)
- "I can't do this anymore" → needs focus (what you accomplished) + 
  tasks (progress so far) to give a data-backed encouraging response

A single LLM has none of this data. These agents do.

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/neuroflow.git
cd neuroflow
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys

# Run each in a separate terminal:
make task
make focus
make calendar
make orchestrator
```

Then open each agent's inspector link → Connect → Mailbox.
Chat with the Orchestrator via "Chat with Agent" on Agentverse.

## Example Session

> "I have a midterm Thursday and a project due Friday, help me plan"

NeuroFlow checks your real calendar, finds free blocks, decomposes 
both tasks into micro-steps, and builds a plan using your actual 
schedule.

> "Help me focus"

Starts a real 15-minute timer. Captured thoughts are saved without 
breaking flow and returned after the session.

> "Done, 4 out of 5"

Logs the session, updates stats, marks task steps complete, checks 
time remaining, and suggests what to do next — all from real data 
across three agents.

> "I can't focus anymore"

Pulls your real accomplishments from today's sessions and gives you 
permission to stop, backed by data: "You did 50 minutes and 8 of 14 
steps. That's real progress."

## Tech Stack

- Fetch.ai uAgents + Chat Protocol v0.3.0
- Agentverse (hosting, discovery)
- ASI:One (intent classification, task decomposition)
- FastMCP + MCPServerAdapter (2 MCP servers)
- Python

## Team

- [Names]
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| ASI:One API down | OpenAI fallback, swap with env var |
| Mailbox connection fails | Test in hour 1, have backup |
| MCP adapter version issues | Pin versions, test before building on top |
| Orchestrator can't combine responses cleanly | Keep specialist responses as simple JSON, do all formatting in orchestrator |
| Demo feels slow (agents take time to respond) | Pre-warm agents, have backup pre-recorded demo |
| "Why not just use ChatGPT?" | "ChatGPT can't check your calendar, track a running timer, or remember your task progress. Every response here uses real data from 3 systems." |
| "Is this really ADHD?" | "The ADHD community's #1 problem isn't any single tool — it's coordinating calendar, tasks, and focus in one place. That's what we built." |

---

## Judging Criteria Alignment

Based on the Cal Hacks 12.0 Fetch.ai rubric (most recent available):

| Criteria (Weight) | Our Angle |
|---|---|
| Functionality & Technical Implementation (25%) | 4 agents communicating via Chat Protocol, 2 MCP integrations, real data coordination |
| Use of Fetch.ai Technology (20%) | Agents on Agentverse, Chat Protocol v0.3.0, MCPServerAdapter, ASI:One LLM, Almanac registration |
| Innovation & Creativity (20%) | Empty accessibility niche, ADHD application, no similar agents on Agentverse |
| Real-World Impact & Usefulness (20%) | 1 in 9 adults with ADHD, genuine tool that combines calendar + focus + tasks |
| User Experience & Presentation (15%) | Interactive session demo, clear responses, compassionate overwhelm handling |