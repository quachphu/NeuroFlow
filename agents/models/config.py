import os
from dotenv import find_dotenv, load_dotenv
from uagents_core.identity import Identity

load_dotenv(find_dotenv())

ORCHESTRATOR_SEED = os.getenv("ORCHESTRATOR_SEED")
FOCUS_SEED = os.getenv("FOCUS_SEED")
CALENDAR_SEED = os.getenv("CALENDAR_SEED")
PROFILE_SEED = os.getenv("PROFILE_SEED")
TRANSCRIPTION_SEED = os.getenv("TRANSCRIPTION_SEED")
CANVAS_SEED = os.getenv("CANVAS_SEED")

ASI1_API_KEY = os.getenv("ASI1_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FOCUS_ADDRESS = Identity.from_seed(seed=FOCUS_SEED, index=0).address
CALENDAR_ADDRESS = Identity.from_seed(seed=CALENDAR_SEED, index=0).address
PROFILE_ADDRESS = Identity.from_seed(seed=PROFILE_SEED, index=0).address
TRANSCRIPTION_ADDRESS = Identity.from_seed(seed=TRANSCRIPTION_SEED, index=0).address
CANVAS_ADDRESS = Identity.from_seed(seed=CANVAS_SEED, index=0).address
