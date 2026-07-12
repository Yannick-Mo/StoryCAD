"""Atomic state container for the autonomous agent loop.

Inspired by Claude Code's State aggregator pattern (query.ts:204-217):
every continue site writes the full state atomically — no partial updates,
no forgetting to reset a field.

Usage::

    state = LoopState.from_initial(initial_agent_state_dict)
    ...
    state = state.replace(messages=new_msgs, transition="tool_executed")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent.state import AgentState
from app.llm.types import Message


@dataclass
class LoopState:
    """Mutable cross-iteration state for the autonomous agent loop.

    Every ``continue`` site calls :meth:`replace` which returns a **new**
    instance — no shared mutable references, no partial updates, and each
    transition declares a ``transition`` reason string for debugging.
    """

    # ── Immutable identifiers ──
    project_id: str = ""
    user_id: str = ""
    conversation_id: str = ""
    trace_id: str = ""

    # ── Mode ──
    mode: str = "chat"

    # ── Messages (the conversation) ──
    messages: list[Message] = field(default_factory=list)

    # ── Project data ──
    project_context: dict = field(default_factory=dict)
    active_skills: list = field(default_factory=list)

    # ── Tool execution ──
    tool_results: list[dict] = field(default_factory=list)
    intermediate_steps: list[dict] = field(default_factory=list)

    # ── Cowriter ──
    cowriter_session: dict = field(default_factory=dict)
    current_options: list[dict] = field(default_factory=list)

    # ── Plan / confirmation ──
    pending_plan: dict = field(default_factory=dict)
    plan_confirmed: bool = False
    planned_steps: list[dict] = field(default_factory=list)
    current_step_index: int = 0

    # ── Error / recovery ──
    errors: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    retry_context: dict | None = None
    recovery_state: dict = field(default_factory=dict)
    _model_override: str = ""

    # ── Lifecycle tracking ──
    turn_count: int = 0
    _context_loaded: bool = False

    # ── Diagnostic ──
    transition: str = ""  # Why the previous iteration continued (for logging)

    def replace(self, **overrides: Any) -> "LoopState":
        """Return a new LoopState with the given fields replaced.

        Every continue site MUST use this — it guarantees atomicity and
        makes the transition reason visible in logs.
        """
        d = {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "trace_id": self.trace_id,
            "mode": self.mode,
            "messages": self.messages,
            "project_context": self.project_context,
            "active_skills": self.active_skills,
            "tool_results": self.tool_results,
            "intermediate_steps": self.intermediate_steps,
            "cowriter_session": self.cowriter_session,
            "current_options": self.current_options,
            "pending_plan": self.pending_plan,
            "plan_confirmed": self.plan_confirmed,
            "planned_steps": self.planned_steps,
            "current_step_index": self.current_step_index,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_context": self.retry_context,
            "recovery_state": self.recovery_state,
            "_model_override": self._model_override,
            "turn_count": self.turn_count,
            "_context_loaded": self._context_loaded,
            "transition": self.transition,
        }
        d.update(overrides)
        return LoopState(**d)

    @classmethod
    def from_initial(cls, initial_state: AgentState) -> "LoopState":
        """Create a LoopState from the initial AgentState dict."""
        return cls(
            project_id=initial_state.get("project_id") or "",
            user_id=initial_state.get("user_id") or "",
            conversation_id=initial_state.get("conversation_id") or "",
            trace_id=initial_state.get("trace_id", ""),
            mode=initial_state.get("mode", "chat"),
            messages=list(initial_state.get("messages", [])),
            project_context=initial_state.get("project_context", {}),
            active_skills=list(initial_state.get("active_skills", [])),
            tool_results=list(initial_state.get("tool_results", [])),
            intermediate_steps=list(initial_state.get("intermediate_steps", [])),
            cowriter_session=dict(initial_state.get("cowriter_session", {}) or {}),
            current_options=list(initial_state.get("current_options", []) or []),
            pending_plan=dict(initial_state.get("pending_plan", {}) or {}),
            plan_confirmed=initial_state.get("plan_confirmed", False),
            planned_steps=list(initial_state.get("planned_steps", []) or []),
            current_step_index=initial_state.get("current_step_index", 0),
            errors=list(initial_state.get("errors", [])),
            retry_count=initial_state.get("retry_count", 0),
            max_retries=initial_state.get("max_retries", 3),
            retry_context=initial_state.get("retry_context"),
            recovery_state=dict(initial_state.get("recovery_state", {}) or {}),
            _model_override=initial_state.get("_model_override", ""),
            turn_count=initial_state.get("_turn_count", 0),
            _context_loaded=initial_state.get("_context_loaded", False),
            transition="initial",
        )

    def to_dict(self) -> AgentState:
        """Convert back to an AgentState dict for save_agent_state compatibility."""
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "trace_id": self.trace_id,
            "mode": self.mode,
            "messages": self.messages,
            "project_context": self.project_context,
            "active_skills": self.active_skills,
            "tool_results": self.tool_results,
            "intermediate_steps": self.intermediate_steps,
            "cowriter_session": self.cowriter_session,
            "current_options": self.current_options,
            "pending_plan": self.pending_plan,
            "plan_confirmed": self.plan_confirmed,
            "planned_steps": self.planned_steps,
            "current_step_index": self.current_step_index,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_context": self.retry_context,
            "recovery_state": self.recovery_state,
            "_model_override": self._model_override,
            "_turn_count": self.turn_count,
            "_context_loaded": self._context_loaded,
            "current_intent": "simple_q",
            "tool_calls": [],
            "search_results": [],
        }
