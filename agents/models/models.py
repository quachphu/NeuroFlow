from uagents import Model


class SharedAgentState(Model):
    """
    Shared communication contract between agents.

    Supports both hub-and-spoke (orchestrator ↔ agent) and chained
    communication (agent → agent → orchestrator) via return_address
    and chain_data fields.
    """

    chat_session_id: str
    query: str
    user_sender_address: str
    result: str = ""
    return_address: str = ""
    chain_data: str = ""
