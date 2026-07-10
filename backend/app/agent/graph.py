from __future__ import annotations

import re
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
}

# ---- Fast-path detection for general questions ----
# These patterns reliably indicate a general writing question or greeting
# that does NOT require project context or tool calling.
_FAST_PATH_PATTERNS = [
    re.compile(r"^(如何|怎么|怎样|如何才|怎样才能|怎么才|如何可以|怎么可以)"),
    re.compile(r"^(什么是|什么叫|什么是)"),
    re.compile(r"^(可以|能)\S{,4}(告诉|解释|推荐|介绍|说说|问)"),
    re.compile(r"^(请问|请教|想问|想请教|想问问|想了解)"),
    re.compile(r"^(好的|可以|谢谢|感谢|ok|yes|明白|知道了|收到)"),
    re.compile(r"^(你好|您好|hello|hi|hey|早上好|下午好|晚上好|在吗|在不在)"),
    re.compile(r"^(what|how|why|when|where|who|can you|could you)"),
]

_FAST_PATH_BLOCK_KEYWORDS = [
    "第", "章", "节", "幕",
    "角色", "人物", "主角", "配角", "反派",
    "场景", "小说", "项目",
    "修改", "创建", "新增", "删除", "更新",
    "分析", "检查",
    "create", "edit", "delete", "add", "remove", "update", "rewrite",
]


def _is_general_question(state: AgentState) -> bool:
    """Return True iff the latest user message is a general question
    that can skip context loading and intent classification.

    Must be conservative: only fast-path when we are highly confident
    the message has no project-specific intent.
    """
    messages = state.get("messages", [])
    if not messages:
        return False

    last = messages[-1]
    if last.role != "user":
        return False

    content = (last.content or "").strip()

    # Only fast-path short messages (< 120 chars)
    if len(content) > 120:
        return False

    # If any project keyword is present, do NOT fast-path
    content_lower = content.lower()
    for kw in _FAST_PATH_BLOCK_KEYWORDS:
        if kw in content_lower:
            return False

    # Must match at least one general-question pattern
    for pat in _FAST_PATH_PATTERNS:
        if pat.search(content_lower):
            return True

    return False

def _get_or_create_llm(llm_client: LLMClient | None = None) -> LLMClient:
    return llm_client or LLMClient()


def _build_tool_descriptions(all_tools: dict) -> str:
    return "\n".join(f"- {t.name}: {t.description}" for t in all_tools.values())


def _route_intent(state: AgentState) -> str:
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

    # If retries exhausted but steps remain, advance past them
    # (the _execute_planned_step handler already force-advances the
    #  step index; if we still see remaining steps, go to generate)
    if has_error and retry >= max_retry:
        return "continue"

    if step_idx < len(planned):
        return "continue_plan"

    return "continue"


def _route_from_start(state: AgentState) -> str:
    """Route the initial message: fast-path → generate, or normal flow."""
    if _is_general_question(state):
        return "fast_path"
    if state.get("_context_loaded", False):
        return "skip_load"
    return "load"


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

    # START → fast_path = skip everything, go straight to generate
    builder.add_conditional_edges(
        START,
        _route_from_start,
        {
            "fast_path": "generate",
            "load": "load_full_context",
            "skip_load": "classify_intent",
        },
    )
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
