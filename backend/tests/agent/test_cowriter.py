"""Tests for CoWriterMode: build_system_prompt and parse_response."""
import json
import pytest
from app.agent.cowriter.mode import CoWriterMode


class TestBuildSystemPrompt:
    def test_basic_project_context(self):
        mode = CoWriterMode()
        prompt = mode.build_system_prompt({
            "project": {"title": "星辰大海", "genre": "科幻", "description": "太空史诗"},
            "acts": [{"name": "第一幕", "chapters": [{"title": "启程", "sort_order": 1}]}],
            "characters": [{"name": "舰长", "role": "主角"}],
        }, [])

        assert "星辰大海" in prompt
        assert "科幻" in prompt
        assert "太空史诗" in prompt
        assert "1幕" in prompt
        assert "1章" in prompt
        assert "1角色" in prompt
        assert "舰长" in prompt

    def test_project_without_description(self):
        mode = CoWriterMode()
        prompt = mode.build_system_prompt({
            "project": {"title": "无简介", "genre": "奇幻"},
        }, [])

        assert "无简介" in prompt
        assert "简介：" not in prompt

    def test_with_active_skills(self):
        mode = CoWriterMode()
        prompt = mode.build_system_prompt({
            "project": {"title": "T", "genre": "G"},
            "active_skills": ["pacing", "dialogue"],
        }, [])

        assert "pacing" in prompt
        assert "dialogue" in prompt

    def test_with_tool_descriptions(self):
        mode = CoWriterMode(tool_descriptions="tool1: desc1\ntool2: desc2")
        prompt = mode.build_system_prompt({
            "project": {"title": "T", "genre": "G"},
        }, [])

        assert "tool1" in prompt

    def test_long_tool_descriptions_truncated(self):
        long_desc = "\n".join(f"tool{i}" for i in range(40))
        mode = CoWriterMode(tool_descriptions=long_desc)
        prompt = mode.build_system_prompt({
            "project": {"title": "T", "genre": "G"},
        }, [])

        assert "还有" in prompt
        assert "工具未列出" in prompt

    def test_many_characters_truncated_to_ten(self):
        mode = CoWriterMode()
        chars = [{"name": f"角色{i}", "role": "配角"} for i in range(15)]
        prompt = mode.build_system_prompt({
            "project": {"title": "T", "genre": "G"},
            "characters": chars,
        }, [])

        for i in range(10):
            assert f"角色{i}" in prompt

    def test_chapter_structure_display(self):
        mode = CoWriterMode()
        chapters = [{"title": f"第{i}章", "sort_order": i} for i in range(8)]
        prompt = mode.build_system_prompt({
            "project": {"title": "T", "genre": "G"},
            "acts": [{"name": "第一幕", "chapters": chapters}],
        }, [])

        assert "第0章" in prompt
        assert "第4章" in prompt
        assert "第7章" not in prompt
        assert "还有3章" in prompt

    def test_empty_project_context(self):
        mode = CoWriterMode()
        prompt = mode.build_system_prompt({}, [])

        assert "未命名项目" in prompt
        assert "未指定" in prompt

    def test_acts_as_list_passed_correctly(self):
        mode = CoWriterMode()
        prompt = mode.build_system_prompt({
            "project": {"title": "test", "genre": "test"},
            "acts": [],
            "characters": [],
        }, [])

        assert "0幕 / 0章 / 0场景 / 0角色" in prompt

    def test_non_dict_project_context_acts(self):
        mode = CoWriterMode()
        with pytest.raises((AttributeError, TypeError)):
            mode.build_system_prompt({
                "project": {"title": "test", "genre": "test"},
                "acts": "not_a_list",
                "characters": "not_a_list",
            }, [])


class TestStripCodeFence:
    def test_triple_backtick_no_lang(self):
        mode = CoWriterMode()
        result = mode._strip_code_fence("```\ncontent\n```")
        assert result == "content"

    def test_triple_backtick_with_lang(self):
        mode = CoWriterMode()
        result = mode._strip_code_fence("""```json\n{"key": "value"}\n```""")
        assert result == """{"key": "value"}"""

    def test_no_fence(self):
        mode = CoWriterMode()
        result = mode._strip_code_fence("plain text")
        assert result == "plain text"

    def test_partial_fence_start(self):
        mode = CoWriterMode()
        result = mode._strip_code_fence("```\ncontent")
        assert result == "content"

    def test_empty_string(self):
        mode = CoWriterMode()
        result = mode._strip_code_fence("")
        assert result == ""


class TestParseResponse:
    def test_valid_json(self):
        mode = CoWriterMode()
        raw = """{"analysis": "文本分析", "options": [{"id": "option_a", "label": "选项A"}]}"""
        result = mode.parse_response(raw)

        assert result["analysis"] == "文本分析"
        assert len(result["options"]) == 1
        assert result["options"][0]["id"] == "option_a"
        assert "parse_error" not in result

    def test_valid_json_with_code_fence(self):
        mode = CoWriterMode()
        raw = """```json\n{"analysis": "test", "options": []}\n```"""
        result = mode.parse_response(raw)

        assert result["analysis"] == "test"
        assert result["options"] == []

    def test_invalid_json_returns_fallback(self):
        mode = CoWriterMode()
        raw = "not json at all"
        result = mode.parse_response(raw)

        assert result["analysis"] == raw
        assert result["options"] == []
        assert result["parse_error"] is True

    def test_empty_string(self):
        mode = CoWriterMode()
        result = mode.parse_response("")

        assert result["parse_error"] is True

    def test_json_array_not_dict(self):
        mode = CoWriterMode()
        result = mode.parse_response('["a", "b"]')

        assert result["parse_error"] is True
        assert "not a dict" in result["error"]

    def test_formatting_with_extra_whitespace(self):
        mode = CoWriterMode()
        raw = """  {

      "analysis": "spacy json"

  }  """
        result = mode.parse_response(raw)

        assert result["analysis"] == "spacy json"
        assert result.get("parse_error") is None

    def test_valid_json_with_action(self):
        mode = CoWriterMode()
        raw = json.dumps({
            "analysis": "需要推进剧情",
            "options": [
                {
                    "id": "option_a",
                    "label": "增加冲突",
                    "description": "在场景中引入外部威胁",
                    "pros": ["增加张力"],
                    "cons": ["需要调整后续"],
                    "action": {"tool": "edit_scene", "params": {"scene_id": "s1"}},
                }
            ],
        })
        result = mode.parse_response(raw)

        assert result["options"][0]["action"]["tool"] == "edit_scene"
        assert result["options"][0]["action"]["params"]["scene_id"] == "s1"

    def test_code_fence_with_extra_chars(self):
        mode = CoWriterMode()
        raw = "```\n\n\n{\"analysis\": \"deep\"}\n\n\n```"
        result = mode.parse_response(raw)

        assert result["analysis"] == "deep"