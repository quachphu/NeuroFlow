
NeuroFlow
A multi-agent study companion for neurodivergent students, built with Fetch.ai's uAgent framework and ASI-1 Mini.

What it does
NeuroFlow adapts to how your brain works. It connects your calendar, course assignments, and disability profile to create personalized study plans with smart scheduling.

4 AI Agents working together:

Orchestrator — Classifies intent and routes queries through the agent chain
Advisor — Researches disability-specific study strategies using live web search
Focus — Builds adapted focus sessions (duration, breaks, techniques)
Calendar — Finds optimal study slots based on your actual class schedule

Tech Stack
Backend: Python, FastAPI, Fetch.ai uAgents, ASI-1 Mini
Frontend: React 19, Vite, Tailwind CSS
Integrations: Google Calendar API, Canvas LMS, DuckDuckGo Search
Protocols: Agentverse mailbox, MCP, DeltaV chat protocol


# Clone and install
git clone https://github.com/your-repo/AccessOrchestra.git
cd AccessOrchestra
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in: ASI1_API_KEY, ORCHESTRATOR_SEED, ADVISOR_SEED, FOCUS_SEED, CALENDAR_SEED

# Start agents
python -m agents.advisor_agent.advisor_agent &
python -m agents.focus_agent.focus_agent &
python -m agents.calendar_agent.calendar_agent &
python -m agents.orchestrator.orchestrator_agent &

# Start server
python server.py

# Frontend
cd frontend && npm install && npm run dev
Open http://localhost:8080 to use the app.

How it works
User sends a message (e.g., "help me study for my AI midterm")
Orchestrator classifies intent → triggers agent chain
Advisor researches strategies for the student's disability
Focus builds an adapted session plan
Calendar finds open slots around existing classes
Response is synthesized and returned with proposed time slots
Built at BeachHacks 2025
