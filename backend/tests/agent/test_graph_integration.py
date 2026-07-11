"""Integration tests for the full LangGraph agent graph flow.

Tests verify graph routing, state transitions, and token streaming
without making real LLM API calls.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.state import AgentState
from app.llm.types import ChatResult, Message


class FakeLLMClient:
    """LLM client that returns canned responses without API calls."""

    def __init__(self):
        self.chat_stream_tokens = self._stream_tokens

    async def _stream_tokens(self, messages, **kwargs):
        yield "这是"
        yield "测试"
        yield "回复"

    async def chat(self, messages, **kwargs):
        last = messages[-1] if messages else None
        if last and last.role == "user":
            content = last.content or ""
        else:
            content = ""
        if "confirm" in content or "确认" in content:
            return ChatResult(content='{"intent": "plan_confirm", "reason": "user agreed"}')
        if "reject" in content or "不要" in content:
            return ChatResult(content='{"intent": "plan_reject", "reason": "user rejected"}')
        if "复杂" in content:
            return ChatResult(content='{"intent": "complex", "reason": "complex request"}')
        if "工具" in content:
            tc = MagicMock()
            tc.function = {"name": "read_project", "arguments": "{}"}
            return ChatResult(content=None, tool_calls=[tc])
        return ChatResult(content='{"intent": "simple_q", "reason": "simple query"}')


def _make_state(overrides: dict | None = None) -> AgentState:
    base: AgentState = {
        "project_id": "test-proj",
        "user_id": "test-user",
        "trace_id": "test-trace",
        "conversation_id": "test-conv",
        "project_context": {},
        "messages": [],
        "current_intent": "simple_q",
        "tool_calls": [],
        "tool_results": [],
        "active_skills": [],
        "mode": "chat",
        "intermediate_steps": [],
        "retry_count": 0,
        "max_retries": 3,
        "current_options": [],
        "planned_steps": [],
        "current_step_index": 0,
        "errors": [],
        "pending_plan": {},
        "plan_confirmed": False,
        "retry_context": None,
        "recovery_state": {},
        "_model_override": "",
        "search_results": [],
        "cowriter_session": {},
        "_context_loaded": False,
    }
    if overrides:
        base.update(overrides)
    return base


def test_graph_structure():
    """Verify the graph has the expected node structure."""
    from app.agent.graph import INTENT_TO_NODE

    assert "simple_q" in INTENT_TO_NODE
    assert "tool_call" in INTENT_TO_NODE
    assert "complex" in INTENT_TO_NODE
    assert INTENT_TO_NODE["simple_q"] == "generate"
    assert INTENT_TO_NODE["tool_call"] == "execute_tool"
    assert INTENT_TO_NODE["complex"] == "plan"


@pytest.mark.asyncio
async def test_simple_q_flow():
    """Simple question routes: classify_intent -> generate, generates tokens."""
    llm = FakeLLMClient()
    state = _make_state({
        "messages": [Message(role="user", content="你好")],
    })
    result = await _run_graph_node_sequence(state, ["classify_intent", "generate"])
    last_msg = result["messages"][-1]
    assert last_msg.role == "assistant"
    assert "测试" in (last_msg.content or "")


@pytest.mark.asyncio
async def test_generate_node_streams_tokens():
    """Generate node yields tokens progressively via async generator."""
    llm = FakeLLMClient()
    from app.agent.nodes.generate import create_generate_node

    node = create_generate_node(llm)
    state = _make_state({
        "messages": [Message(role="user", content="你好")],
    })
    tokens = []
    final_state = None
    async for update in node(state):
        if "_stream_token" in update:
            tokens.append(update["_stream_token"])
        if "messages" in update and "_stream_token" not in update:
            final_state = update
    assert len(tokens) > 0
    assert "".join(tokens) == "这是测试回复"
    assert final_state is not None
    assert final_state["messages"][-1].role == "assistant"


async def _run_graph_node_sequence(
    state: AgentState, node_order: list[str]
) -> AgentState:
    """Simulate running a sequence of graph nodes."""
    from app.agent.nodes.classify_intent import create_classify_intent_node
    from app.agent.nodes.generate import create_generate_node

    all_tools = {}
    llm = FakeLLMClient()
    current = dict(state)
    for node_name in node_order:
        if node_name == "classify_intent":
            fn = create_classify_intent_node(all_tools, llm)
            update = await fn(current)
        elif node_name == "generate":
            fn = create_generate_node(llm)
            async for update in fn(current):
                if isinstance(update, dict) and "messages" in update and "_stream_token" not in update:
                    break
        else:
            raise ValueError(f"Unknown node: {node_name}")
        current.update(update)
    return current


@pytest.mark.asyncio
async def test_plan_reject_resets_plan():
    """When user rejects a plan, pending_plan and planned_steps are cleared."""
    llm = FakeLLMClient()
    from app.agent.nodes.classify_intent import create_classify_intent_node

    node = create_classify_intent_node({}, llm)
    state = _make_state({
        "messages": [Message(role="user", content="不要这个计划")],
        "pending_plan": [{"tool": "read_project", "params": {}}],
        "planned_steps": [{"tool": "read_project", "params": {}}],
    })
    update = await node(state)
    assert update.get("current_intent") == "simple_q"
    assert update.get("pending_plan") == []
    assert update.get("planned_steps") == []
