.PHONY: orchestrator profile focus calendar transcription canvas all

profile:
	python -m agents.profile_agent.profile_agent

focus:
	python -m agents.focus_agent.focus_agent

calendar:
	python -m agents.calendar_agent.calendar_agent

transcription:
	python -m agents.transcription_agent.transcription_agent

canvas:
	python -m agents.canvas_agent.canvas_agent

orchestrator:
	python -m agents.orchestrator.orchestrator_agent

all:
	@echo "Run each in a separate terminal:"
	@echo "  make profile       # Terminal 1 (port 8001)"
	@echo "  make focus         # Terminal 2 (port 8002)"
	@echo "  make calendar      # Terminal 3 (port 8004)"
	@echo "  make transcription # Terminal 4 (port 8005)"
	@echo "  make canvas        # Terminal 5 (port 8006)"
	@echo "  make orchestrator  # Terminal 6 (port 8003, start last)"
