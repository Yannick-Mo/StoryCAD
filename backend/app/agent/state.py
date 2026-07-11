from __future__ import annotations

from typing import Any, Literal, TypedDict
from app.llm.types import Message, ToolCall

IntentType = Literal["simple_q", "tool_call", "cowriter", "cowriter_choice", "complex", "plan_confirm", "plan_reject"]


class AgentState(TypedDict):
    project_id: str | None
    user_id: str | None
    trace_id: str
    conversation_id: str | None
    project_context: dict
    messages: list[Message]
    current_intent: IntentType
    tool_calls: list[ToolCall]
    tool_results: list[dict]  # Each dict has {tool, success, data/error}
    active_skills: list[str]
    mode: str
    intermediate_steps: list[dict]
    retry_count: int
    max_retries: int
    current_options: list[dict]
    planned_steps: list[dict]
    current_step_index: int
    errors: list[str]  # Error messages
    pending_plan: dict
    plan_confirmed: bool
    retry_context: dict | None
    search_results: list[dict]
    _context_loaded: bool


def has_pending_plan(pending_plan: dict) -> bool:
    return bool(pending_plan)
