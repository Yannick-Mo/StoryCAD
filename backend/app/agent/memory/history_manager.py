"""Conversation history management: summarization, sliding window, pruning."""

from __future__ import annotations

import math
from typing import Any

from loguru import logger

from app.llm.client import LLMClient
from app.llm.types import Message

MAX_HISTORY_TOKENS_EST = 6000
MAX_HISTORY_TOKENS_HARD = 8000
SUMMARIZE_AFTER = 20
KEEP_RECENT = 10
MIN_SUMMARIZE_INTERVAL = 5
TOKEN_ESTIMATE_SAFETY = 1.5


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f')
    ascii_len = len(text) - chinese
    return int(math.ceil((chinese * 1.5 + ascii_len * 0.25) * TOKEN_ESTIMATE_SAFETY))


def _sanitize_for_summary(messages: list[Message]) -> list[Message]:
    """Remove internal tool details, keep only essential info."""
    sanitized: list[Message] = []
    for m in messages:
        if m.role == "tool":
            sanitized.append(Message(
                role="tool",
                content=f"[Tool executed: {m.name or 'unknown'}]",
                tool_call_id=m.tool_call_id,
            ))
        elif m.tool_calls:
            sanitized.append(Message(
                role=m.role,
                content=m.content,
                tool_calls=None,
            ))
        else:
            sanitized.append(m)
    return sanitized


class HistoryManager:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()
        self._last_summary_count = 0

    async def maybe_summarize(self, messages: list[Message]) -> list[Message]:
        user_msgs = [m for m in messages if m.role == "user"]
        raw_text = " ".join(m.content or "" for m in messages)
        total_tokens = _estimate_tokens(raw_text)

        if len(user_msgs) <= SUMMARIZE_AFTER and total_tokens <= MAX_HISTORY_TOKENS_EST:
            return messages

        if len(messages) - self._last_summary_count < MIN_SUMMARIZE_INTERVAL:
            return messages

        # Hard limit: if still above MAX_HISTORY_TOKENS_HARD after summary, truncate further
        try:
            summary = await self._summarize_old(messages)
        except Exception:
            logger.exception("Summarization failed, keeping original messages")
            return messages

        if not summary or summary == "[Summary unavailable]":
            return messages

        recent = messages[-KEEP_RECENT * 2:] if len(messages) > KEEP_RECENT * 2 else messages

        self._last_summary_count = len(messages)
        summary_msg = Message(role="system", content=f"[Conversation summary up to this point]:\n{summary}")

        result = [summary_msg] + recent

        post_summary_text = " ".join(m.content or "" for m in result)
        if _estimate_tokens(post_summary_text) > MAX_HISTORY_TOKENS_HARD:
            result = [summary_msg] + recent[-KEEP_RECENT:]

        return result

    async def _summarize_old(self, messages: list[Message]) -> str:
        cleaned = _sanitize_for_summary(messages)
        cutoff = min(len(cleaned), KEEP_RECENT * 2)
        old = cleaned[:-cutoff] if cutoff > 0 else cleaned
        recent = cleaned[-cutoff:] if cutoff > 0 else []

        old_text = ""
        for m in old:
            role = "User" if m.role == "user" else "Assistant"
            old_text += f"{role}: {(m.content or '')[:500]}\n"

        recent_text = ""
        for m in recent:
            role = "User" if m.role == "user" else "Assistant"
            recent_text += f"{role}: {(m.content or '')[:300]}\n"

        prompt = (
            "Summarize the following conversation between a user and a novel-writing assistant. "
            "Keep it concise but include: key user requests, decisions made, project changes, and any pending actions.\n\n"
            "Older messages:\n" + old_text + "\n"
            "Most recent messages (for context):\n" + recent_text + "\n\n"
            "Summary:"
        )

        msgs = [Message(role="user", content=prompt)]
        try:
            result = await self.llm.chat(messages=msgs, temperature=0.3, max_tokens=1024)
            return result.content or ""
        except Exception:
            logger.exception("LLM summarization call failed")
            return "[Summary unavailable]"
