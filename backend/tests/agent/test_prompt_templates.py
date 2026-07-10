"""Tests for prompt templating system (Jinja2-based)."""

import pytest
from app.agent.prompts import PromptTemplate, PromptLoader


class TestPromptTemplate:
    def test_basic_render(self):
        tpl = PromptTemplate("Hello {{name}}!")
        assert tpl.render(name="World") == "Hello World!"

    def test_multiple_vars(self):
        tpl = PromptTemplate("{{greeting}}, {{name}}!")
        assert tpl.render(greeting="Hi", name="Alice") == "Hi, Alice!"

    def test_unknown_var_preserved(self):
        tpl = PromptTemplate("Hello {{name}}!")
        assert tpl.render(other="val") == "Hello {{name}}!"

    def test_dict_values(self):
        tpl = PromptTemplate("Data: {{data}}")
        result = tpl.render(data={"key": "val"})
        assert "key" in result
        assert "val" in result

    def test_int_values(self):
        tpl = PromptTemplate("Count: {{count}}")
        assert tpl.render(count=42) == "Count: 42"

    def test_bool_values(self):
        tpl = PromptTemplate("Flag: {{flag}}")
        assert tpl.render(flag=True) == "Flag: True"

    def test_condition_with_comparison(self):
        text = "{% if count > 0 %}yes{% else %}no{% endif %}"
        assert "yes" in PromptTemplate(text).render(count=5)
        assert "no" in PromptTemplate(text).render(count=0)

    def test_compound_condition(self):
        text = "{% if a and b %}both{% else %}not both{% endif %}"
        result = PromptTemplate(text).render(a=True, b=True)
        assert "both" in result
        result2 = PromptTemplate(text).render(a=True, b=False)
        assert "not both" in result2

    def test_equals_condition(self):
        text = '{% if mode == "cowriter" %}cowriter{% else %}chat{% endif %}'
        result = PromptTemplate(text).render(mode="cowriter")
        assert "cowriter" in result
        result2 = PromptTemplate(text).render(mode="chat")
        assert "chat" in result2


class TestConditionals:
    def test_if_true(self):
        text = "{% if show %}shown{% endif %}"
        result = PromptTemplate(text).render(show=True)
        assert "shown" in result

    def test_if_false(self):
        text = "{% if show %}hidden{% endif %}"
        result = PromptTemplate(text).render(show=False)
        assert "hidden" not in result

    def test_if_else_true(self):
        text = "{% if show %}yes{% else %}no{% endif %}"
        result = PromptTemplate(text).render(show=True)
        assert "yes" in result
        assert "no" not in result

    def test_if_else_false(self):
        text = "{% if show %}yes{% else %}no{% endif %}"
        result = PromptTemplate(text).render(show=False)
        assert "no" in result
        assert "yes" not in result

    def test_if_with_non_bool(self):
        text = "{% if items %}have items{% else %}empty{% endif %}"
        result = PromptTemplate(text).render(items=["a", "b"])
        assert "have items" in result
        result2 = PromptTemplate(text).render(items=[])
        assert "empty" in result2


class TestLoops:
    def test_for_loop_simple(self):
        text = "{% for item in items %}{{item}}{% endfor %}"
        result = PromptTemplate(text).render(items=["a", "b", "c"])
        assert result == "abc"

    def test_for_loop_with_newlines(self):
        text = "{% for item in items %}\n{{item}}{% endfor %}"
        result = PromptTemplate(text).render(items=["a", "b", "c"])
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_for_loop_dict_items(self):
        text = "{% for item in items %}{{item.name}}{% endfor %}"
        result = PromptTemplate(text).render(items=[{"name": "foo"}, {"name": "bar"}])
        assert "foo" in result
        assert "bar" in result

    def test_for_loop_with_filter(self):
        text = "{% for item in items %}{{item}}{% endfor %}"
        result = PromptTemplate(text).render(items=[1, 2, 3])
        assert "123" in result


class TestFilters:
    def test_join_filter(self):
        tpl = PromptTemplate("{{items | join(', ')}}")
        result = tpl.render(items=["a", "b", "c"])
        assert result == "a, b, c"

    def test_take_filter(self):
        text = "{% for item in items|take(2) %}{{item}}{% endfor %}"
        result = PromptTemplate(text).render(items=["a", "b", "c"])
        assert result == "ab"

    def test_length_filter(self):
        tpl = PromptTemplate("{{items | length}}")
        result = tpl.render(items=["a", "b", "c"])
        assert result == "3"


class TestPromptLoader:
    def test_load_existing(self):
        loader = PromptLoader()
        tpl = loader.load("classify_intent")
        assert tpl is not None

    def test_plan_prompt(self):
        loader = PromptLoader()
        tpl = loader.load("plan")
        assert tpl is not None
        result = tpl.render(tool_descriptions="tool1: desc", entity_context="Project: test", max_steps=10, retry_context=None)
        assert "tool1" in result

    def test_generate_prompt(self):
        loader = PromptLoader()
        tpl = loader.load("generate")
        assert tpl is not None
        result = tpl.render(project_title="Test", project_structure="", rag_context="", tool_results=[], success_count=0, total_count=0, errors=[], pending_plan=[], plan_confirmed=False, current_options=[], mode="chat", cowriter_prompt="", retry_count=0)
        assert "Test" in result

    def test_cowriter_prompt(self):
        loader = PromptLoader()
        tpl = loader.load("cowriter")
        assert tpl is not None

    def test_load_nonexistent(self):
        loader = PromptLoader()
        tpl = loader.load("nonexistent")
        assert tpl is None
