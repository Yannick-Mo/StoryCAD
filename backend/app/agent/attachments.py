from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AttachmentInjector:
    """Per-turn context injection system.

    Instead of loading ALL context before the first turn, this injects
    relevant context incrementally each turn based on what is actually
    needed.  Inspired by Claude Code's per-turn attachment system.

    Two methods:
    - ``collect(state, tool_results, turn)`` → list of Message objects
      to inject as ``<system-reminder>`` blocks.
    - ``build_system_sections(state)`` → dict of section name → content
      for the system prompt.  Replaces the inline context building that
      was previously duplicated in loop.py.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client

    # ── Public API ──────────────────────────────────────────────────

    async def collect(
        self,
        state: dict,
        tool_results: list[dict],
        turn: int,
    ) -> list[Any]:
        """Collect all relevant attachments for the current turn.

        Returns a list of Message objects to append before the next API
        call.  Each message is wrapped in a ``<system-reminder>`` block
        so the LLM knows it is ephemeral context, not user input.
        """
        from app.llm.types import Message

        attachments: list[Message] = []

        # 1. Tool result summary (from previous turn's tool executions)
        if tool_results and turn > 1:
            summary = self._summarize_tool_results(tool_results)
            if summary:
                attachments.append(
                    Message(
                        role="system",
                        content=(
                            "<system-reminder>\n"
                            "上一轮工具执行结果：\n"
                            f"{summary}\n"
                            "</system-reminder>"
                        ),
                    )
                )

        # 2. Session progress (for cowriter mode)
        session = state.get("cowriter_session", {})
        if session and session.get("is_active"):
            progress = self._format_session_progress(session)
            if progress:
                attachments.append(
                    Message(
                        role="system",
                        content=(
                            "<system-reminder>\n"
                            f"{progress}\n"
                            "</system-reminder>"
                        ),
                    )
                )

        # 3. Recent errors (for self-correction)
        errors: list[str] = state.get("errors", []) or []
        recent_errors = [e for e in errors[-3:] if e]
        if recent_errors:
            attachments.append(
                Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        "最近的错误（请避免重复）：\n"
                        + "\n".join(f"- {e}" for e in recent_errors)
                        + "\n</system-reminder>"
                    ),
                )
            )

        # 4. Available skills context — list all skills with when_to_use
        available_skills: list = state.get("project_context", {}).get("available_skills", []) or []
        if available_skills:
            lines = ["可用技能列表（AI 可调用 invoke_skill 主动启用）："]
            for s in available_skills:
                name = s.get("name", "?")
                desc = s.get("description", "")
                when = s.get("when_to_use", "")
                if when:
                    lines.append(f"  - {name}: {desc}（适用场景：{when[:120]}）")
                else:
                    lines.append(f"  - {name}: {desc}")
            attachments.append(
                Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        + "\n".join(lines)
                        + "\n</system-reminder>"
                    ),
                )
            )

        # 5. Active skill names reminder (compact)
        active: list = state.get("active_skills", []) or []
        if active:
            active_names: list[str] = []
            for s in active:
                if isinstance(s, str):
                    active_names.append(s)
                elif isinstance(s, dict):
                    active_names.append(s.get("name", str(s)))
            if active_names:
                attachments.append(
                    Message(
                        role="system",
                        content=(
                            "<system-reminder>\n"
                            f"当前已激活技能：{', '.join(active_names)}\n"
                            "</system-reminder>"
                        ),
                    )
                )

        # 5. Pending plan reminder (if applicable)
        pending = state.get("pending_plan", {}) or {}
        if pending and not state.get("plan_confirmed", False):
            steps = pending.get("steps", [])
            if steps:
                steps_desc = "\n".join(
                    f"  {i+1}. {s.get('description', s.get('tool', ''))}"
                    for i, s in enumerate(steps[:5])
                )
                attachments.append(
                    Message(
                        role="system",
                        content=(
                            "<system-reminder>\n"
                            "有待确认的计划：\n"
                            f"{steps_desc}\n"
                            "请等待用户确认或拒绝。\n"
                            "</system-reminder>"
                        ),
                    )
                )

        return attachments

    # ── System prompt sections ───────────────────────────────────────

    def build_system_sections(self, state: Any) -> dict[str, str]:
        """Return dict of {section_name: content} for the system prompt.

        Consolidates all per-turn context that was previously built inline
        in loop.py (the ~80 lines building tool_summary, session_text,
        plan_text, error_text).  The caller should append these sections
        to the system prompt.

        Sections returned:
            tool_summary, session_progress, plan_reminder, error_context
        """
        sections: dict[str, str] = {}

        # Tool result summary (last 5)
        tool_results = getattr(state, "tool_results", []) if hasattr(state, "tool_results") else []
        if tool_results:
            lines = ["# --- 上一轮工具执行结果 ---"]
            for r in tool_results[-5:]:
                status = "OK" if r.get("success") else "FAIL"
                name = r.get("tool", "?")
                detail = ""
                if r.get("success"):
                    data = r.get("data", "")
                    if isinstance(data, str):
                        detail = self._markdown_to_plain(data, 150)
                else:
                    detail = (r.get("error", "") or "")[:150]
                lines.append(f"  [{status}] {name}: {detail}")
            sections["tool_summary"] = "\n".join(lines)

        # Session progress
        session = getattr(state, "cowriter_session", None)
        if hasattr(state, "cowriter_session") and session:
            sess = session or {}
            if sess.get("is_active"):
                phase = sess.get("phase", "explore")
                goal = sess.get("goal", "")
                focus = sess.get("current_focus", "")
                phase_cn = {
                    "explore": "探索",
                    "plan": "计划",
                    "execute": "执行",
                    "review": "评审",
                    "complete": "完成",
                }.get(phase, phase)
                lines = [f"# --- 协作进度 ---\n阶段: {phase_cn}"]
                if goal:
                    lines.append(f"目标: {goal}")
                if focus:
                    lines.append(f"焦点: {focus}")
                sections["session_progress"] = "\n".join(lines)

        # Pending plan reminder
        pending_plan = getattr(state, "pending_plan", None)
        plan_confirmed = getattr(state, "plan_confirmed", False)
        if hasattr(state, "pending_plan") and pending_plan and not plan_confirmed:
            steps = pending_plan.get("steps", [])
            if steps:
                lines = ["# --- 待确认计划 ---"]
                for i, s in enumerate(steps, 1):
                    lines.append(
                        f"  {i}. {s.get('description', s.get('tool', ''))}"
                    )
                lines.append("等待用户确认或拒绝。")
                sections["plan_reminder"] = "\n".join(lines)

        # Error context
        errors = getattr(state, "errors", []) if hasattr(state, "errors") else []
        recent = [e for e in errors[-3:] if e]
        if recent:
            sections["error_context"] = "# --- 最近的错误 ---\n" + "\n".join(
                f"- {e}" for e in recent
            )

        return sections

    # ── Static helpers ───────────────────────────────────────────────

    @staticmethod
    def _markdown_to_plain(md: str, max_len: int = 120) -> str:
        """Strip markdown formatting for tool result summaries."""
        import re

        md = re.sub(r"#{1,6}\s+", "", md)
        md = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", md)
        md = re.sub(r"`{1,3}[^`]+`{1,3}", "", md)
        md = re.sub(r">\s+", "", md)
        md = re.sub(r"\s+", " ", md).strip()
        return md[:max_len] + ("..." if len(md) > max_len else "")

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _summarize_tool_results(results: list[dict]) -> str:
        """Create a concise summary of tool execution results.

        Only the last 5 results are included to keep the context
        window manageable.
        """
        if not results:
            return ""

        lines: list[str] = []
        for r in results[-5:]:
            tool_name = r.get("tool", "unknown")
            success = r.get("success", False)
            status = "OK" if success else "FAIL"
            error = r.get("error", "")

            if success:
                data = r.get("data")
                if isinstance(data, str) and len(data) > 120:
                    data = data[:120] + "..."
                detail = str(data)[:120] if data else "ok"
                lines.append(f"  [{status}] {tool_name}: {detail}")
            else:
                lines.append(f"  [{status}] {tool_name}: {error[:120]}")

        return "\n".join(lines) if lines else ""

    @staticmethod
    def _format_session_progress(session: dict) -> str:
        """Format cowriter session progress for context injection."""
        phase = session.get("phase", "explore")
        goal = session.get("goal", "")
        current_focus = session.get("current_focus", "")
        decisions = session.get("decisions", [])

        phase_names: dict[str, str] = {
            "explore": "探索需求",
            "plan": "制定计划",
            "execute": "执行操作",
            "review": "评审结果",
            "complete": "已完成",
        }

        lines = [f"协作阶段：{phase_names.get(phase, phase)}"]
        if goal:
            lines.append(f"任务目标：{goal}")
        if current_focus:
            lines.append(f"当前焦点：{current_focus}")
        if decisions:
            lines.append(f"已完成决策：{len(decisions)} 轮")
            for d in decisions[-3:]:
                label = d.get("label", "?")
                result = d.get("result", "")
                lines.append(f"  - {label}: {result[:80]}")

        return "\n".join(lines)
