from agents.models.models import SharedAgentState


class PendingFanOut:
    """Tracks multi-agent requests that need responses from multiple agents."""

    def __init__(self, expected_agents: list[str], query: str, user_sender: str):
        self.expected_agents = set(expected_agents)
        self.received: dict[str, str] = {}
        self.query = query
        self.user_sender = user_sender

    def add_response(self, agent_address: str, result: str):
        self.received[agent_address] = result

    @property
    def is_complete(self) -> bool:
        return self.expected_agents.issubset(set(self.received.keys()))


class InMemoryStateService:
    def __init__(self) -> None:
        self._store: dict[str, SharedAgentState] = {}
        self._fanouts: dict[str, PendingFanOut] = {}

    def set_state(self, chat_session_id: str, state: SharedAgentState) -> None:
        self._store[chat_session_id] = state

    def get_state(self, chat_session_id: str) -> SharedAgentState | None:
        return self._store.get(chat_session_id)

    def start_fanout(self, session_id: str, fanout: PendingFanOut):
        self._fanouts[session_id] = fanout

    def get_fanout(self, session_id: str) -> PendingFanOut | None:
        return self._fanouts.get(session_id)

    def clear_fanout(self, session_id: str):
        self._fanouts.pop(session_id, None)


state_service = InMemoryStateService()
