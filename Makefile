.PHONY: orchestrator advisor focus calendar all

advisor:
	python -m agents.advisor_agent.advisor_agent

focus:
	python -m agents.focus_agent.focus_agent

calendar:
	python -m agents.calendar_agent.calendar_agent

orchestrator:
	python -m agents.orchestrator.orchestrator_agent

all:
	@echo "Run each in a separate terminal:"
	@echo "  make advisor       # Terminal 1 (port 8001)"
	@echo "  make focus         # Terminal 2 (port 8002)"
	@echo "  make calendar      # Terminal 3 (port 8004)"
	@echo "  make orchestrator  # Terminal 4 (port 8003, start last)"
