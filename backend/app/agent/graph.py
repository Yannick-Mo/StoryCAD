from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
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
    "execute_tool": "execute_tool",
}

def _get_or_create_llm(llm_client: LLMClient | None = None) -> LLMClient:
    return llm_client or LLMClient()


def _build_tool_descriptions(all_tools: dict) -> str:
    return "\n".join(f"- {t.name}: {t.description}" for t in all_tools.values())


def _route_intent(state: AgentState) -> str:
    pending = state.get("pending_plan", [])
    if pending:
        return "execute_tool"
    return state.get("current_intent", "simple_q")


def _route_after_plan(state: AgentState) -> str:
    plan_confirmed: bool = state.get("plan_confirmed", False)
    pending: list = state.get("pending_plan", [])
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

    if has_error and retry < max_retry:
        return "retry"

    step_idx: int = state.get("current_step_index", 0)
    planned: list[dict] = state.get("planned_steps", [])

    if has_error and retry >= max_retry:
        return "continue"

    if step_idx < len(planned):
        return "continue_plan"

    if retry >= max_retry:
        return "continue"

    return "continue"


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
        },
    )

    builder.add_edge("generate", END)

    return builder
