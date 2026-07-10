"""Tests for per-skill tool filtering."""

import pytest
from app.agent.tool_filter import get_available_tools, READ_ONLY_TOOLS, GENERAL_TOOLS, SKILL_TO_TOOLS


class FakeTool:
    def __init__(self, name: str, is_write: bool = False):
        self.name = name
        self.description = f"Tool {name}"
        self.parameters = {"type": "object", "properties": {}, "required": []}
        self.is_write_operation = is_write

    def to_openai_tool(self):
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


@pytest.fixture
def all_tools():
    names = set(GENERAL_TOOLS)
    for tools in SKILL_TO_TOOLS.values():
        names.update(tools)
    return {n: FakeTool(n) for n in names}


class TestGetAvailableTools:
    def test_no_skills_chat_mode(self, all_tools):
        result = get_available_tools(all_tools, [], mode="chat")
        assert set(result.keys()) == READ_ONLY_TOOLS

    def test_no_skills_cowriter_mode(self, all_tools):
        result = get_available_tools(all_tools, [], mode="cowriter")
        assert set(result.keys()) == GENERAL_TOOLS

    def test_character_dev_skill_chat(self, all_tools):
        result = get_available_tools(all_tools, ["character_dev"], mode="chat")
        assert set(result.keys()) == READ_ONLY_TOOLS
        for name in result:
            assert name in READ_ONLY_TOOLS, f"Tool '{name}' is write but appeared in chat mode"

    def test_character_dev_skill_cowriter(self, all_tools):
        result = get_available_tools(all_tools, ["character_dev"], mode="cowriter")
        expected = GENERAL_TOOLS | SKILL_TO_TOOLS["character_dev"]
        assert set(result.keys()) == expected

    def test_multiple_skills_union_cowriter(self, all_tools):
        result = get_available_tools(all_tools, ["character_dev", "plot_outline"], mode="cowriter")
        expected = GENERAL_TOOLS | SKILL_TO_TOOLS["character_dev"] | SKILL_TO_TOOLS["plot_outline"]
        assert set(result.keys()) == expected

    def test_unknown_skill_chat_mode(self, all_tools):
        result = get_available_tools(all_tools, ["nonexistent_skill"], mode="chat")
        assert set(result.keys()) == READ_ONLY_TOOLS

    def test_unknown_skill_cowriter_mode(self, all_tools):
        result = get_available_tools(all_tools, ["nonexistent_skill"], mode="cowriter")
        assert set(result.keys()) == GENERAL_TOOLS

    def test_skill_is_dict_cowriter(self, all_tools):
        result = get_available_tools(all_tools, [{"name": "character_dev"}], mode="cowriter")
        expected = GENERAL_TOOLS | SKILL_TO_TOOLS["character_dev"]
        assert set(result.keys()) == expected

    def test_all_skills_enables_all_tools_cowriter(self, all_tools):
        all_skill_names = list(SKILL_TO_TOOLS.keys())
        result = get_available_tools(all_tools, all_skill_names, mode="cowriter")
        all_enabled = GENERAL_TOOLS.copy()
        for tools in SKILL_TO_TOOLS.values():
            all_enabled.update(tools)
        assert set(result.keys()) == all_enabled

    def test_all_skills_chat_still_readonly(self, all_tools):
        all_skill_names = list(SKILL_TO_TOOLS.keys())
        result = get_available_tools(all_tools, all_skill_names, mode="chat")
        for name in result:
            assert name in READ_ONLY_TOOLS, f"Tool '{name}' is not read-only but appeared in chat mode"
