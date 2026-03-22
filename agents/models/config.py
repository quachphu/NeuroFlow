import os
from dotenv import find_dotenv, load_dotenv
from uagents_core.identity import Identity

load_dotenv(find_dotenv())

ORCHESTRATOR_SEED = os.getenv("ORCHESTRATOR_SEED")
FOCUS_SEED = os.getenv("FOCUS_SEED")
CALENDAR_SEED = os.getenv("CALENDAR_SEED")
ADVISOR_SEED = os.getenv("ADVISOR_SEED")

ASI1_API_KEY = os.getenv("ASI1_API_KEY")

ORCHESTRATOR_ADDRESS = Identity.from_seed(seed=ORCHESTRATOR_SEED, index=0).address
FOCUS_ADDRESS = Identity.from_seed(seed=FOCUS_SEED, index=0).address
CALENDAR_ADDRESS = Identity.from_seed(seed=CALENDAR_SEED, index=0).address
ADVISOR_ADDRESS = Identity.from_seed(seed=ADVISOR_SEED, index=0).address
