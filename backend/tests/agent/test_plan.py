"""Tests for plan node and write tools logic."""

from app.agent.tools import _WRITE_TOOL_NAMES


class TestWriteTools:
    def test_known_write_tools(self):
        write_tools = _WRITE_TOOL_NAMES
        assert "update_chapter" in write_tools
        assert "write_scene_content" in write_tools
        assert "create_character" in write_tools
        assert "read_project" not in write_tools
        assert "search_knowledge" not in write_tools

    def test_all_write_tools_actually_exist(self):
        """Verify write tools names follow the naming convention."""
        write_tools = _WRITE_TOOL_NAMES
        for tool in write_tools:
            assert not tool.startswith("read_"), f"Read tool in write tools: {tool}"
            assert not tool.startswith("search_"), f"Search tool in write tools: {tool}"
            assert not tool.startswith("list_"), f"List tool in write tools: {tool}"
            assert not tool.startswith("analyze_"), f"Analyze tool in write tools: {tool}"
            assert not tool.startswith("check_"), f"Check tool in write tools: {tool}"
