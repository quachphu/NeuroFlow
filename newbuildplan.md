# NeuroFlow — Updated Build Brief

## Project
NeuroFlow is a multi-agent ADHD/neurodivergent study companion for BeachHacks 2026, Fetch.ai track. Built with uAgents, Agentverse, Chat Protocol v0.3.0, FastMCP + MCPServerAdapter, and ASI:One.

## Pitch
"15–20% of college students are neurodivergent. Standard AI tools don't adapt to their specific attention rhythms. NeuroFlow is a team of AI agents that each own a different piece of your academic life — your schedule, your focus sessions, your lectures, your courses, your accessibility profile — and coordinate to produce responses no single LLM could generate."

## What Changed
- **Drop the Task Agent entirely.** It was for study task decomposition — no longer core to the pitch.
- **Keep Calendar Agent and Focus Agent** as already built.
- **Add 3 new agents:** Transcription Agent, Profile Agent, Canvas Agent.
- The core story is now: lecture audio goes in → gets transcribed → gets adapted to the student's neurodivergent profile → gets contextualized with real course data → student reviews it in adaptive focus sessions scheduled around their real calendar.

## Final Agent Lineup (6 agents)

### 1. Orchestrator
- User-facing, coordinates all agents
- Classifies intent, routes to specialists, combines responses
- Handles Easy Read simplification itself — conditioned by Profile Agent's config (no separate Simplifier agent)
- Overwhelm detection: if user signals shutdown, pulls stats from Focus Agent and responds with acknowledgment + permission to stop
- Tech: uAgent + Chat Protocol v0.3.0 + ASI:One for intent classification

### 2. Calendar Agent (MCP) — ALREADY BUILT
- Owns real schedule data (mock Google Calendar for demo)
- MCP tools: get_events, get_free_blocks, get_upcoming_deadlines, create_event
- Role in new flow: tells Orchestrator how much time the student has, scopes focus session length

### 3. Focus Agent (MCP) — ALREADY BUILT
- Owns timer, session history, captured thoughts, streak data
- MCP tools: start_session, capture_thought, get_captured_thoughts, end_session, get_focus_stats
- Adaptive session length based on ratings (bad sessions get shorter, good ones get longer)
- Role in new flow: Focus Agent asks Profile Agent for default session length before starting

### 4. Transcription Agent (MCP) — NEW, BUILD THIS
- Owns raw lecture transcripts with timestamps
- Receives audio file path, calls OpenAI Whisper API (whisper-1), stores timestamped transcript
- Returns transcript text + word-level timing data + speakers_detected count
- For demo: speaker detection is mocked (hardcode speakers_detected: 1, label "Professor"). Real diarization is a roadmap item.
- MCP tools:
  - `transcribe_audio(audio_path: str)` — calls Whisper, stores result, returns transcript + word count + duration
  - `get_transcript()` — returns full session transcript
  - `get_recent(minutes: int = 5)` — returns last N minutes using timestamp data
  - `search_transcript(query: str)` — keyword search across transcript, returns matching segments
- Other agents query it: "what did the professor say about X?", "summarize the last 5 minutes"
- Demo strategy: pre-record 2-3 short audio clips of dense lecture material (30-60s each). Have pre-cached fallback transcripts in case Whisper API is slow during judging.
- Tech: FastMCP + MCPServerAdapter + openai Python SDK

### 5. Profile Agent — NEW, BUILD THIS
- Owns the student's accessibility/cognitive profile
- Stores: disability type (ADHD, dyslexia, autism), preferred session length, reading grade level, chunk size preference, tone preference (encouraging vs neutral vs precise), format preferences
- Runs FIRST before any other specialist agent — sends config to Orchestrator so every downstream response is pre-adapted
- Multi-agent moments:
  - Focus Agent asks Profile Agent for default session length before starting
  - Orchestrator asks Profile Agent what reading level and tone to use when simplifying transcripts
  - Calendar Agent scheduling density is informed by Profile Agent (ADHD = schedule at 60-70% capacity)
- Use ctx.storage for persistence. Skip Knowledge Graph — too risky for hackathon timeline.
- Tech: uAgent + ctx.storage (no MCP needed, this is internal state)

### 6. Canvas Agent (MCP) — NEW, BUILD THIS
- Owns real academic/course data via Canvas LMS (mock data for demo, same pattern as Calendar Agent)
- Knows: enrolled courses, assignment due dates, point weights, current grades, syllabus/topics
- MCP tools:
  - `get_courses()` — enrolled courses this quarter
  - `get_assignments(course_id: str)` — upcoming assignments with due dates and point weights
  - `get_grades(course_id: str)` — current grade + breakdown
  - `get_syllabus(course_id: str)` — topics covered, learning objectives (used to flag key terms that shouldn't be oversimplified)
- Multi-agent moments:
  - Transcription Agent provides transcript, Canvas Agent identifies which terms are exam-critical → Orchestrator simplifies everything else but preserves key terms with definitions
  - Task prioritization: "ECON homework is 5% and you have a 94, but CS170 midterm is 25% and you have a B+ — focus on the midterm"
  - Auto-populates deadlines instead of student manually entering them
- Mock with realistic college course data for demo (CS170, CS105, ECON, etc.)
- Tech: FastMCP + MCPServerAdapter

## Core Demo Flow (3-4 minutes)
This is the sequence that shows all 6 agents coordinating:

1. **Student:** "I just recorded my CS170 lecture on search algorithms"
   - → Transcription Agent transcribes the audio, stores timestamped transcript
   - → Canvas Agent identifies CS170 syllabus topics for this unit
   - → Profile Agent sends config (ADHD, grade level 8, short chunks)
   - → Orchestrator simplifies the transcript into Easy Read, preserving exam-critical terms flagged by Canvas Agent
   - **Output:** Simplified lecture notes with key terms preserved and defined

2. **Student:** "Wait what did the professor say about A* search?"
   - → Transcription Agent searches transcript for "A*" segments
   - → Canvas Agent confirms A* is a midterm topic (worth 25%)
   - → Orchestrator explains at the student's level per Profile Agent
   - **Output:** Targeted micro-explanation using the professor's actual words, simplified

3. **Student:** "Help me review this material"
   - → Calendar Agent: "you have 2 hours before your next class"
   - → Focus Agent: starts adaptive session (length from Profile Agent)
   - → Orchestrator builds a review session from the transcribed lecture content
   - **Output:** "Starting a 15-min review session on search algorithms. Here's your first chunk."

4. **Student:** "I can't focus anymore"
   - → Focus Agent: returns today's stats (sessions, total minutes, ratings)
   - → Orchestrator: acknowledges, lists real accomplishments, gives permission to stop
   - **Output:** "You did 2 sessions and reviewed 3 topics from today's lecture. That's real progress. Rest up."

## Collapse Test
If you collapse all agents into one LLM, you lose: real calendar data + real timer state + real lecture transcripts with timestamps + real course grades/weights + persistent accessibility profile. A single LLM can't hold all of this simultaneously. Each agent owns a different piece of real state.

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
│   ├── transcription_agent/
│   │   ├── __init__.py
│   │   ├── transcription_agent.py
│   │   ├── transcription_mcp_server.py
│   │   └── demo_audio/
│   │       ├── lecture_clip_1.wav
│   │       └── fallback_transcript.json
│   ├── profile_agent/
│   │   ├── __init__.py
│   │   └── profile_agent.py
│   └── canvas_agent/
│       ├── __init__.py
│       ├── canvas_agent.py
│       └── canvas_mcp_server.py
├── .env.example
├── .gitignore
├── Makefile
├── requirements.txt
└── README.md
```
