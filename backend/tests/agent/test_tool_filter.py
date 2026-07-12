"""Tests for mode-based tool filtering (no skill gating)."""

import pytest
from app.agent.tool_filter import get_available_tools, READ_ONLY_TOOLS, COWRITER_TOOLS


class FakeTool:
    def __init__(self, name: str):
        self.name = name
        self.description = f"Tool {name}"
        self.parameters = {"type": "object", "properties": {}, "required": []}

    def to_openai_tool(self):
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


_ALL_TOOL_NAMES = READ_ONLY_TOOLS | COWRITER_TOOLS


@pytest.fixture
def all_tools():
    return {n: FakeTool(n) for n in _ALL_TOOL_NAMES}


class TestGetAvailableTools:
    def test_chat_mode_only_readonly(self, all_tools):
        result = get_available_tools(all_tools, mode="chat")
        assert set(result.keys()) == READ_ONLY_TOOLS

    def test_chat_mode_never_has_write_tools(self, all_tools):
        result = get_available_tools(all_tools, mode="chat")
        for name in result:
            assert name in READ_ONLY_TOOLS, f"Write tool '{name}' leaked into chat mode"

    def test_cowriter_mode_includes_all(self, all_tools):
        result = get_available_tools(all_tools, mode="cowriter")
        assert set(result.keys()) == READ_ONLY_TOOLS | COWRITER_TOOLS

    def test_cowriter_has_write_tools(self, all_tools):
        result = get_available_tools(all_tools, mode="cowriter")
        for name in COWRITER_TOOLS:
            assert name in result, f"Write tool '{name}' missing in cowriter mode"

    def test_chat_filters_out_write_tools(self, all_tools):
        chat_tools = get_available_tools(all_tools, mode="chat")
        for name in all_tools:
            if name in COWRITER_TOOLS:
                assert name not in chat_tools, f"Write tool '{name}' leaked into chat"

    def test_empty_registry(self):
        result = get_available_tools({}, mode="cowriter")
        assert result == {}

    def test_partial_registry(self):
        subset = {n: FakeTool(n) for n in ["read_project", "delete_character", "nonexistent"]}
        result = get_available_tools(subset, mode="chat")
        assert "read_project" in result
        assert "delete_character" not in result
        assert "nonexistent" not in result

    def test_chat_mode_missing_tools_omitted(self, all_tools):
        chat_tools = get_available_tools(all_tools, mode="chat")
        missing = set(chat_tools.keys()) - READ_ONLY_TOOLS
        assert not missing, f"Unexpected tools in chat: {missing}"
