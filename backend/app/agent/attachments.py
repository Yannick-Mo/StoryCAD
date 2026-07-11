from __future__ import annotations

import logging
import time
from typing import Any

from app.llm.types import Message

logger = logging.getLogger(__name__)


class AttachmentInjector:
    """Per-turn context injection system.

    Instead of loading ALL context before the first turn (load_full_context),
    this injects relevant context incrementally each turn based on what is
    actually needed.  Inspired by Claude Code's per-turn attachment system
    (query.ts:1580-1628).

    Context types injected:
    1. Tool result summary  -- previous turn's tool executions
    2. Session progress     -- cowriter session phase and decisions
    3. Recent errors        -- errors for self-correction
    4. Active skills        -- currently active skill names
    5. Pending plan reminder -- unconfirmed plans awaiting user action
    6. Relevant memory      -- recent conversation context (cached, first 5 turns)
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory_cache: dict[str, tuple[float, list[dict]]] = {}
        self._cache_ttl = 300  # 5 minutes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def collect(
        self,
        state: dict,
        tool_results: list[dict],
        turn: int,
    ) -> list[Message]:
        """Collect all relevant attachments for the current turn.

        Returns a list of Message objects to append before the next API
        call.  Each message is wrapped in a ``<system-reminder>`` block
        so the LLM knows it is ephemeral context, not user input.
        """
        attachments: list[Message] = []

        # 1. Tool result summary (from previous turn's tool executions)
        if tool_results and turn > 1:
            summary = self._summarize_tool_results(tool_results)
            if summary:
                attachments.append(Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        "上一轮工具执行结果：\n"
                        f"{summary}\n"
                        "</system-reminder>"
                    ),
                ))

        # 2. Session progress (for cowriter mode)
        session = state.get("cowriter_session", {})
        if session and session.get("is_active"):
            progress = self._format_session_progress(session)
            if progress:
                attachments.append(Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        f"{progress}\n"
                        "</system-reminder>"
                    ),
                ))

        # 3. Recent errors (for self-correction)
        errors: list[str] = state.get("errors", []) or []
        recent_errors = [e for e in errors[-3:] if e]
        if recent_errors:
            attachments.append(Message(
                role="system",
                content=(
                    "<system-reminder>\n"
                    "最近的错误（请避免重复）：\n"
                    + "\n".join(f"- {e}" for e in recent_errors)
                    + "\n</system-reminder>"
                ),
            ))

        # 4. Active skills context
        skills: list = state.get("active_skills", []) or []
        if skills:
            skill_names: list[str] = []
            for s in skills:
                if isinstance(s, str):
                    skill_names.append(s)
                elif isinstance(s, dict):
                    skill_names.append(s.get("name", str(s)))
            if skill_names:
                attachments.append(Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        f"已启用的技能：{', '.join(skill_names)}\n"
                        "</system-reminder>"
                    ),
                ))

        # 5. Pending plan reminder (if applicable)
        pending = state.get("pending_plan", {}) or {}
        if pending and not state.get("plan_confirmed", False):
            steps = pending.get("steps", [])
            if steps:
                steps_desc = "\n".join(
                    f"  {i+1}. {s.get('description', s.get('tool', ''))}"
                    for i, s in enumerate(steps[:5])
                )
                attachments.append(Message(
                    role="system",
                    content=(
                        "<system-reminder>\n"
                        "有待确认的计划：\n"
                        f"{steps_desc}\n"
                        "请等待用户确认或拒绝。\n"
                        "</system-reminder>"
                    ),
                ))

        # 6. Relevant memory (from conversation history, with caching)
        #    Only inject on turns 2-5: turn 1 has no history, and
        #    by turn 6 the model has enough context from the
        #    conversation itself.
        if 2 <= turn <= 5:
            context_loaded = state.get("_context_loaded", False)
            if context_loaded and self._redis:
                memories = await self._fetch_relevant_memories(state)
                if memories:
                    mem_text = "\n".join(
                        f"- {m.get('title', '')}: {m.get('content', '')[:200]}"
                        for m in memories[:5]
                    )
                    attachments.append(Message(
                        role="system",
                        content=(
                            "<system-reminder>\n"
                            "相关项目知识：\n"
                            f"{mem_text}\n"
                            "</system-reminder>"
                        ),
                    ))

        return attachments

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
                lines.append(
                    f"  [{status}] {tool_name}: {error[:120]}"
                )

        return "\n".join(lines) if lines else ""

    @staticmethod
    def _format_session_progress(session: dict) -> str:
        """Format cowriter session progress for context injection.

        Provides a high-level overview so the LLM remembers the
        current phase, goal, and recent decisions without needing
        to re-read the full conversation.
        """
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

        lines = [
            f"协作阶段：{phase_names.get(phase, phase)}",
        ]
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

    async def _fetch_relevant_memories(self, state: dict) -> list[dict]:
        """Fetch recent conversation context with caching.

        Uses the conversation_id to look up recent messages from the
        current conversation.  Results are cached per conversation for
        ``_cache_ttl`` seconds to avoid redundant Redis round-trips
        across multiple injection calls.
        """
        conversation_id = state.get("conversation_id", "")
        if not conversation_id:
            return []

        cache_key = f"mem:{conversation_id}"
        now = time.time()

        if cache_key in self._memory_cache:
            ts, items = self._memory_cache[cache_key]
            if now - ts < self._cache_ttl:
                return items

        try:
            from app.agent.memory.conversation import ConversationMemory
            conv_memory = ConversationMemory(self._redis)
            history = await conv_memory.get_history(conversation_id)
            if history:
                items: list[dict] = []
                for msg in history[-3:]:
                    role = getattr(msg, "role", "")
                    content = getattr(msg, "content", "") or ""
                    if (
                        role in ("user", "assistant")
                        and content
                        and len(content) > 20
                    ):
                        items.append({
                            "title": "最近对话",
                            "content": content[:200],
                        })
                self._memory_cache[cache_key] = (now, items)
                return items
        except Exception as e:
            logger.debug("Failed to fetch memories: %s", e)

        return []
