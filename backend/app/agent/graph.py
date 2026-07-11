from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ContextBuilder
from app.agent.nodes import (
    create_classify_intent_node,
    create_execute_tool_node,
    create_generate_node,
    create_load_context_node,
    create_plan_node,
)
from app.agent.state import AgentState
from app.agent.tools import get_tool_registry
from app.llm.client import LLMClient

INTENT_TO_NODE: dict[str, str] = {
    "simple_q": "generate",
    "tool_call": "execute_tool",
    "cowriter": "execute_tool",
    "cowriter_choice": "execute_tool",
    "complex": "plan",
    "plan_confirm": "execute_tool",
    "plan_reject": "generate",
    "execute_tool": "execute_tool",
}

def _get_or_create_llm(llm_client: LLMClient | None = None) -> LLMClient:
    return llm_client or LLMClient()


def _build_tool_descriptions(all_tools: dict) -> str:
    return "\n".join(f"- {t.name}: {t.description}" for t in all_tools.values())


def _route_intent(state: AgentState) -> str:
    pending: dict = state.get("pending_plan", {})
    if pending:
        return "execute_tool"
    return state.get("current_intent", "simple_q")


def _route_after_plan(state: AgentState) -> str:
    plan_confirmed: bool = state.get("plan_confirmed", False)
    pending: dict = state.get("pending_plan", {})
    if plan_confirmed:
        return "execute_tool"
    if not pending:
        return "generate"
    return "execute_tool"


def _route_after_tool(state: AgentState) -> str:
    retry: int = state.get("retry_count", 0)
    max_retry: int = state.get("max_retries", 3)
    results: list[dict] = state.get("tool_results", [])
    has_error: bool = any(not r.get("success", True) for r in results)
    step_idx: int = state.get("current_step_index", 0)
    planned: list[dict] = state.get("planned_steps", [])
    intent: str = state.get("current_intent", "")

    logger.warning("_route_after_tool retry={} has_error={} step_idx={} planned={} intent={} recent_results={}",
                   retry, has_error, step_idx, len(planned), intent,
                   [(r.get("tool"), r.get("success")) for r in results[-3:]])

    # Bug 4: Cowriter intent means we're regenerating options (e.g. after failed choice).
    # Route back to execute_tool so _execute_cowriter() gets called, NOT generate.
    if intent == "cowriter":
        # Check if this is a recovery from a failed cowriter choice
        failed_cowriter_choice = any(
            r.get("tool") in ("cowriter_analysis", "cowriter_choice") or r.get("option")
            for r in results[-2:]
        )
        if failed_cowriter_choice and has_error:
            logger.info("cowriter_choice failed -> routing back to cowriter for regeneration")
            return "regenerate"

    # ── Layered error recovery (opt-in via llm_recovery_enabled) ──
    if has_error and _is_recovery_enabled():
        recovery_route = _maybe_recovery_route(state, has_error)
        if recovery_route:
            return recovery_route

    if has_error and retry < max_retry:
        # Check if the error is due to mode restriction (blocked write in chat mode)
        for r in results:
            if not r.get("success", True):
                error = r.get("error", "")
                if "对话模式禁止写入操作" in error or "blocked in chat mode" in error:
                    logger.warning("write_blocked -> continue (skip retry)")
                    return "continue"
        return "retry"
    if has_error and retry >= max_retry:
        return "continue"
    if step_idx < len(planned):
        return "continue_plan"
    if retry >= max_retry:
        return "continue"
    return "continue"


def _is_recovery_enabled() -> bool:
    from app.config import settings
    return getattr(settings, "llm_recovery_enabled", False)


def _maybe_recovery_route(state: AgentState, has_error: bool) -> str | None:
    """When layered recovery is enabled, classify the error and decide whether
    to use recovery instead of simple retry.

    Returns a route string ("recovery" or "recovery_give_up") if recovery
    should handle this, or None to fall through to the legacy retry logic.
    """
    if not has_error:
        return None

    from app.agent.recovery import ErrorClassifier, RecoveryAction, get_fallback_models

    errors: list[str] = state.get("errors", [])
    error_text = "; ".join(errors[-3:]) if errors else "unknown error"
    attempt = state.get("retry_count", 0)

    # Incorporate error from tool_results if errors list is sparse
    if not error_text or error_text == "unknown error":
        results = state.get("tool_results", [])
        result_errors = [
            r.get("error", "") for r in results
            if not r.get("success", True) and r.get("error")
        ]
        if result_errors:
            error_text = "; ".join(result_errors[-3:])

    recovery_history = state.get("recovery_state", {}).get("recovery_history", [])

    decision = ErrorClassifier.classify(
        error_text, attempt,
        max_retries=state.get("max_retries", 3),
        recovery_history=recovery_history,
    )

    logger.info(
        "Recovery decision: action=%s message=%s attempt=%d",
        decision.action.value, decision.message, attempt,
    )

    if decision.action == RecoveryAction.GIVE_UP:
        return "recovery_give_up"

    # Store the decision so execute_tool can apply it on the next pass
    recovery_state = dict(state.get("recovery_state", {}))
    recovery_state["pending_decision"] = {
        "action": decision.action.value,
        "message": decision.message,
        "delay_seconds": decision.delay_seconds,
        "context": decision.context,
    }
    state["recovery_state"] = recovery_state

    return "recovery"


def build_super_graph(
    db: AsyncSession,
    llm_client: LLMClient | None = None,
    redis_client: Any | None = None,
) -> StateGraph:
    llm = _get_or_create_llm(llm_client)
    all_tools = get_tool_registry(db, llm_client=llm)
    context_builder = ContextBuilder(db, redis_client=redis_client)

    builder = StateGraph(AgentState)

    builder.add_node("load_full_context", create_load_context_node(context_builder))

    dynamic_classify = create_classify_intent_node(all_tools, llm)
    builder.add_node("classify_intent", dynamic_classify)

    dynamic_plan = create_plan_node(all_tools, llm)
    builder.add_node("plan", dynamic_plan)

    tool_descriptions = _build_tool_descriptions(all_tools)
    dynamic_execute = create_execute_tool_node(all_tools, llm, db, tool_descriptions)
    builder.add_node("execute_tool", dynamic_execute)

    builder.add_node("generate", create_generate_node(llm))

    builder.add_edge(START, "load_full_context")
    builder.add_edge("load_full_context", "classify_intent")

    builder.add_conditional_edges(
        "classify_intent",
        _route_intent,
        INTENT_TO_NODE,
    )

    builder.add_conditional_edges(
        "plan",
        _route_after_plan,
        {"execute_tool": "execute_tool", "generate": "generate"},
    )

    builder.add_conditional_edges(
        "execute_tool",
        _route_after_tool,
        {
            "continue": "generate",
            "retry": "execute_tool",
            "continue_plan": "execute_tool",
            "regenerate": "execute_tool",
            "recovery": "execute_tool",
            "recovery_give_up": "generate",
        },
    )

    builder.add_edge("generate", END)

    return builder
