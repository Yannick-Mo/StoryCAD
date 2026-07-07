from typing import Any, TypedDict
from app.llm.types import Message, ToolCall


class AgentState(TypedDict):
    project_id: str | None
    user_id: str | None
    conversation_id: str | None
    project_context: dict
    messages: list[Message]
    current_intent: str
    tool_calls: list[ToolCall]
    tool_results: list[dict]
    active_skills: list[str]
    rag_context: list[str]
    sub_agent_results: dict[str, Any]
    pending_actions: list[str]
    intermediate_steps: list[dict]
