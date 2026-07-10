"""Tests for intent classification node logic."""

import pytest
from app.agent.nodes.classify_intent import _detect_plan_confirm


class TestDetectPlanConfirm:
    def test_basic_confirm(self):
        assert _detect_plan_confirm("确认") == "plan_confirm"
        assert _detect_plan_confirm("好的") == "plan_confirm"
        assert _detect_plan_confirm("可以") == "plan_confirm"
        assert _detect_plan_confirm("同意") == "plan_confirm"
        assert _detect_plan_confirm("yes") == "plan_confirm"
        assert _detect_plan_confirm("ok") == "plan_confirm"

    def test_basic_reject(self):
        assert _detect_plan_confirm("修改") == "plan_reject"
        assert _detect_plan_confirm("不要") == "plan_reject"
        assert _detect_plan_confirm("不了") == "plan_reject"
        assert _detect_plan_confirm("不用") == "plan_reject"
        assert _detect_plan_confirm("算了") == "plan_reject"
        assert _detect_plan_confirm("no") == "plan_reject"

    def test_negation_awareness(self):
        """同意 inside 不同意 must NOT match as confirm."""
        assert _detect_plan_confirm("不同意") == "plan_reject"
        assert _detect_plan_confirm("不确认") == "plan_reject"
        assert _detect_plan_confirm("不执行") == "plan_reject"
        assert _detect_plan_confirm("不开始") == "plan_reject"

    def test_neutral_message(self):
        assert _detect_plan_confirm("今天天气不错") is None
        assert _detect_plan_confirm("我写了一个故事") is None
        assert _detect_plan_confirm("") is None
