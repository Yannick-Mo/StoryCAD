from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.agent.prompts import render_prompt
from app.agent.state import AgentState
from app.agent.tools import get_tool_descriptions, get_filtered_tools
from app.llm.client import LLMClient
from app.llm.types import Message

logger = logging.getLogger(__name__)

# Negative patterns: words/phrases that should NOT be followed by a confirmation keyword
_NEGATION_PATTERNS = [
    re.compile(r"不\s*"),
    re.compile(r"别\s*"),
    re.compile(r"没\s*"),
    re.compile(r"\bdon't\s+"),
    re.compile(r"\bdo not\s+"),
    re.compile(r"\bwon't\s+"),
    re.compile(r"\bwill not\s+"),
    re.compile(r"\bcan't\s+"),
    re.compile(r"\bcannot\s+"),
    re.compile(r"\bshouldn't\s+"),
]

_REJECT_KEYWORDS = [
    "修改", "不要", "不了", "不用", "算了", "取消", "否决", "否定", "拒绝",
    "不同意", "不确认", "不执行", "不开始",
    "reject", "deny",
    "不想执行", "不要执行",
    "不需要", "不采纳",
    "不对", "不是", "不行", "不可以", "stop", "cancel", "别",
]

_REJECT_PATTERNS = [
    re.compile(r"\bno\b"),
    re.compile(r"\bnope\b"),
    re.compile(r"\bnah\b"),
    re.compile(r"\bnever\b"),
    re.compile(r"\bno\s+way\b"),
    re.compile(r"\bstop\b"),
    re.compile(r"\bcancel\b"),
]

_CONFIRM_KEYWORDS = [
    "确认", "执行", "好的", "可以", "同意", "开始",
    "yes", "ok", "confirm", "execute", "go ahead",
    "就这么办", "就这样", "行", "好", "批准", "approve",
    "直接采用", "就按这个", "就这么做", "直接执行", "开始执行",
    "就按你说的", "就用这个", "听你的",
]


def _detect_plan_confirm(content: str) -> str | None:
    """Detect plan confirmation/rejection with thorough negation awareness."""
    lower = content.lower()
    words = set(lower.split())

    # Check reject first (exact match can override partial confirm matches)
    for kw in _REJECT_KEYWORDS:
        if kw in lower:
            logger.debug("Plan reject detected via keyword '%s' in '%s'", kw, lower[:60])
            return "plan_reject"

    for pat in _REJECT_PATTERNS:
        if pat.search(lower):
            logger.debug("Plan reject detected via pattern '%s' in '%s'", pat.pattern, lower[:60])
            return "plan_reject"

    for kw in _CONFIRM_KEYWORDS:
        idx = lower.find(kw)
        while idx != -1:
            prefix = lower[max(0, idx - 8):idx].strip()
            is_negated = any(pat.search(prefix) for pat in _NEGATION_PATTERNS)
            if not is_negated:
                logger.debug("Plan confirm detected via keyword '%s' in '%s'", kw, lower[:60])
                return "plan_confirm"
            idx = lower.find(kw, idx + 1)

    return None


def create_classify_intent_node(all_tools: dict, llm_client: LLMClient):
    async def classify_intent_node(state: AgentState) -> dict:
        errors: list[str] = list(state.get("errors", []))
        steps: list[dict] = list(state.get("intermediate_steps", []))

        current_mode = state.get("mode", "chat")
        active_skills = state.get("active_skills", [])
        tools = get_filtered_tools(all_tools, active_skills, mode=current_mode)

        last_msg = state["messages"][-1] if state["messages"] else None
        if not last_msg or last_msg.role not in ("user", "tool"):
            return {"current_intent": "simple_q"}

        content = (last_msg.content or "").strip().lower()
        cowriter_active = current_mode == "cowriter"

        # --- Pending plan confirmation (keyword-based, no LLM needed) ---
        has_pending_plan = bool(state.get("pending_plan"))
        if has_pending_plan:
            plan_decision = _detect_plan_confirm(content)
            if plan_decision == "plan_confirm":
                return {
                    "current_intent": "plan_confirm",
                    "plan_confirmed": True,
                    "intermediate_steps": steps + [{"action": "plan_confirm"}],
                }
            elif plan_decision == "plan_reject":
                return {
                    "current_intent": "simple_q",
                    "plan_confirmed": False,
                    "pending_plan": {},
                    "planned_steps": [],
                    "current_step_index": 0,
                    "intermediate_steps": steps + [{"action": "plan_reject"}],
                }

            # If pending plan but no keyword match, let LLM handle it
            # (don't return early)

        # --- Cowriter choice detection ---
        is_cowriter_choice = cowriter_active and (
            "[option:" in content or any(
                kw in content for kw in [
                    "选a", "选b", "选c", "选1", "选2", "选3",
                    "option a", "option b", "option c",
                    "方案a", "方案b", "方案c",
                    "方案一", "方案二", "方案三",
                    "方案1", "方案2", "方案3",
                    "我选",
                ]
            )
        )
        # "选择" alone is too broad — require additional context
        if cowriter_active and not is_cowriter_choice and "选择" in content:
            is_cowriter_choice = any(
                kw in content for kw in [
                    "我选择", "选择方案", "选择第", "选择a", "选择b", "选择c",
                    "方案一", "方案二", "方案三",
                ]
            )
        # Natural language adoption (e.g. "直接采用", "就用这个")
        current_options = state.get("current_options", [])
        if cowriter_active and not is_cowriter_choice and current_options:
            adoption_kw = ["直接采用", "就用这个", "就按这个", "采用", "就这个", "直接写"]
            is_cowriter_choice = any(kw in content for kw in adoption_kw)
        if is_cowriter_choice and cowriter_active:
            return {"current_intent": "cowriter_choice"}

        # --- Session-aware continuation (soft override) ---
        # Only route to cowriter without LLM if message clearly looks like
        # refinement feedback on an active task. Otherwise let LLM decide.
        session = state.get("cowriter_session", {})
        if cowriter_active and session.get("is_active") and session.get("phase") in ("review", "execute"):
            short = len(content.split()) <= 15 and len(content) <= 40
            is_refinement = any(
                kw in content for kw in [
                    "再", "还", "更", "改", "修", "调", "细", "补充", "继续",
                    "然后", "接着", "下一步", "再改", "再写", "换一个",
                    "不够", "不好", "太", "重新",
                    "more", "again", "继续", "further", "refine",
                ]
            )
            adoption = any(kw in content for kw in ["好的", "可以", "行", "就这样", "不错", "挺好", "ok"])
            if short and (is_refinement or adoption):
                return {"current_intent": "cowriter"}
            # Longer messages or ambiguous ones → let LLM decide with session context

        # --- Direct write: user says "帮我写" without prior options ---
        if cowriter_active and not current_options:
            direct_write_kw = ["帮我写", "帮我创作", "帮我生成", "直接写一段",
                               "write a", "write for me", "write me"]
            if any(kw in content for kw in direct_write_kw):
                logger.debug("Direct write detected in cowriter mode, routing to cowriter")
                return {"current_intent": "cowriter"}

        # --- LLM classification (no tool definitions passed) ---
        tool_descriptions = get_tool_descriptions(tools)

        try:
            last_errors = [e for e in errors[-3:]] if errors else []
            project_ctx = state.get("project_context", {})
            rag_text = project_ctx.get("rag_context", "")

            # Last AI response for conversational context
            last_ai_response = ""
            if state.get("messages"):
                for msg in reversed(state["messages"]):
                    if msg.role == "assistant":
                        last_ai_response = (msg.content or "")[:500]
                        break

            current_options = state.get("current_options", [])
            session = state.get("cowriter_session", {})
            session_info = ""
            if session.get("is_active"):
                phase = session.get("phase", "explore")
                goal = session.get("goal", "")
                decisions = session.get("decisions", [])
                session_info = f"当前协作阶段：{phase}"
                if goal:
                    session_info += f" | 目标：{goal}"
                if decisions:
                    session_info += f" | 已完成 {len(decisions)} 轮决策"

            system_text = render_prompt("classify_intent", **{
                "has_pending_plan": has_pending_plan,
                "retry_count": state.get("retry_count", 0),
                "max_retries": state.get("max_retries", 3),
                "last_errors": "; ".join(last_errors) if last_errors else "none",
                "mode": current_mode,
                "rag_context": rag_text[:1000],
                "last_ai_response": last_ai_response,
                "current_options": current_options,
                "cowriter_session": session_info,
            })
            if not system_text:
                system_text = (
                    "You are an intent classifier. Respond with JSON: "
                    '{"intent": "simple_q|tool_call|cowriter|complex", "reason": "..."}'
                )

            tools_section = f"\n\nAvailable tools:\n{tool_descriptions}" if tool_descriptions else ""
            msgs = [
                Message(role="system", content=system_text + tools_section),
                Message(role="user", content=content),
            ]

            # No tools passed to the LLM for classification - prevent tool calling
            _t0 = time.monotonic()
            result = await llm_client.chat(
                messages=msgs,
                tools=None,
                temperature=0.1,
                request_id=state.get("trace_id", ""),
            )
            logger.debug("classify_intent LLM call took %.2fs", time.monotonic() - _t0)

            if result.tool_calls:
                # Shouldn't happen since we pass tools=None, but handle gracefully
                intent = "tool_call"
                return {
                    "current_intent": intent,
                    "tool_calls": result.tool_calls,
                    "intermediate_steps": steps + [
                        {"action": "classify", "intent": intent,
                         "tool": result.tool_calls[0].function.get("name", "") if result.tool_calls[0].function else ""}
                    ],
                }

            try:
                parsed = json.loads(result.content or "{}")
                intent = parsed.get("intent", "simple_q")
                reason = parsed.get("reason", "")
                logger.debug("Classification result: intent=%s reason=%s", intent, reason)
            except (json.JSONDecodeError, TypeError, AttributeError):
                raw = (result.content or "").strip().lower()
                if re.search(r"\bcomplex\b", raw):
                    intent = "complex"
                elif re.search(r"\bcowriter\b", raw):
                    intent = "cowriter"
                else:
                    intent = "simple_q"
                logger.debug("Classification fallback (parse failed): raw=%s intent=%s", raw[:100], intent)

            if intent not in ("simple_q", "tool_call", "cowriter", "complex"):
                intent = "simple_q"

            return {
                "current_intent": intent,
                "intermediate_steps": steps + [{"action": "classify", "intent": intent}],
            }

        except Exception as e:
            errors.append(f"Intent classification failed: {e}")
            logger.warning("Intent classification failed: %s", e)
            return {
                "current_intent": "simple_q",
                "errors": errors,
            }

    return classify_intent_node
