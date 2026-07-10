"""Tests for execute_tool node helpers."""

import pytest
from app.agent.nodes.execute_tool import _validate_params
from app.agent.tools.base import BaseTool


class ValidatableTool(BaseTool):
    name = "test_tool"
    description = "A test tool"
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name"},
            "count": {"type": "integer", "description": "Count"},
        },
        "required": ["name"],
    }

    async def run(self, db, **kwargs):
        from app.agent.tools.base import ToolResult
        return ToolResult(success=True, data=kwargs)


class TestValidateParams:
    def test_valid_params(self):
        tool = ValidatableTool()
        errors = _validate_params(tool, {"name": "test"})
        assert errors == []

    def test_missing_required(self):
        tool = ValidatableTool()
        errors = _validate_params(tool, {"count": 1})
        assert len(errors) == 1
        assert "Missing required param 'name'" in errors[0]

    def test_unknown_param(self):
        tool = ValidatableTool()
        errors = _validate_params(tool, {"name": "test", "unknown": "val"})
        assert len(errors) == 1
        assert "Unknown param 'unknown'" in errors[0]

    def test_empty_schema(self):
        class NoSchemaTool(BaseTool):
            name = "no_schema"
            description = "Tool without schema"
            parameters = {}
            async def run(self, db, **kwargs):
                from app.agent.tools.base import ToolResult
                return ToolResult(success=True, data={})

        errors = _validate_params(NoSchemaTool(), {"anything": "ok"})
        assert errors == []

    def test_multiple_errors(self):
        tool = ValidatableTool()
        errors = _validate_params(tool, {"unknown1": "v1", "unknown2": "v2"})
        assert len(errors) >= 2


class TestWriteToolsConsistency:
    def test_write_tools_all_have_corresponding_run_methods(self):
        from app.agent.tools import _WRITE_TOOL_NAMES, get_tool_registry
        registry = get_tool_registry()
        for tool_name in _WRITE_TOOL_NAMES:
            assert tool_name in registry, f"Write tool '{tool_name}' not found in tool registry"
