"""Token-aware context compression for the autonomous agent loop.

When the estimated token count exceeds 80% of the model's context window,
this module compresses older messages into a single summary to free space
while preserving recent context fidelity.

Strategy:
    head (first 3 msgs) + summary (compressed middle) + tail (last 6 msgs)

Inspired by Claude Code's multi-layer compression pipeline (query.ts:397-543)
but simplified for StoryCAD's single-compression approach.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.types import Message

logger = logging.getLogger(__name__)

# Default model context limits (characters, approximate)
DEFAULT_MODEL_LIMIT = 128_000  # DeepSeek V3 context window (chars)

# Threshold ratios
COMPRESS_THRESHOLD = 0.80  # Start compression at 80% of limit
AGGRESSIVE_THRESHOLD = 0.95  # Aggressive compression at 95%

# Message retention counts
DEFAULT_HEAD_COUNT = 3
DEFAULT_TAIL_COUNT = 6
AGGRESSIVE_HEAD_COUNT = 1
AGGRESSIVE_TAIL_COUNT = 4


def estimate_tokens(messages: list["Message"], model_limit: int = DEFAULT_MODEL_LIMIT) -> int:
    """Estimate the token count of a message list.

    Uses a simple char/2 heuristic — fast enough to run every turn,
    accurate enough for threshold-based decisions.
    """
    total = 0
    for msg in messages:
        content = getattr(msg, "content", "") or ""
        total += len(content)
        # Tool calls add overhead
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                fn = getattr(tc, "function", {})
                args_str = str(fn.get("arguments", "")) if isinstance(fn, dict) else ""
                total += len(args_str)
    return total // 2


def should_compress(
    messages: list["Message"],
    model_limit: int = DEFAULT_MODEL_LIMIT,
) -> bool:
    """Return True if the message list should be compressed before the next call."""
    tokens = estimate_tokens(messages, model_limit)
    return tokens > int(model_limit * COMPRESS_THRESHOLD)


def _msg_role_label(role: str) -> str:
    """Map internal role names to Chinese labels for the summary."""
    return {"user": "用户", "assistant": "AI", "system": "系统"}.get(role, role)


def compress_history(
    messages: list["Message"],
    *,
    model_limit: int = DEFAULT_MODEL_LIMIT,
    head_count: int | None = None,
    tail_count: int | None = None,
) -> list["Message"]:
    """Compress a message list by summarizing the middle portion.

    Returns a new list: ``head + [summary] + tail``.

    If the list is short enough to not need compression, it's returned
    unchanged.  Callers should call :func:`should_compress` first.
    """
    from app.llm.types import Message as M

    tokens = estimate_tokens(messages, model_limit)
    ratio = tokens / model_limit if model_limit else 0

    if ratio <= COMPRESS_THRESHOLD:
        return list(messages)

    # Determine retention based on how over budget we are
    if ratio > AGGRESSIVE_THRESHOLD:
        h = head_count if head_count is not None else AGGRESSIVE_HEAD_COUNT
        t = tail_count if tail_count is not None else AGGRESSIVE_TAIL_COUNT
    else:
        h = head_count if head_count is not None else DEFAULT_HEAD_COUNT
        t = tail_count if tail_count is not None else DEFAULT_TAIL_COUNT

    # Too few messages to compress
    if len(messages) <= h + t + 2:
        return list(messages)

    head = messages[:h]
    tail = messages[-t:]
    middle = messages[h:-t]

    # Build summary of middle messages
    summary_parts: list[str] = []
    for msg in middle:
        role = _msg_role_label(getattr(msg, "role", "unknown"))
        content = (getattr(msg, "content", "") or "")[:200]
        if content:
            summary_parts.append(f"[{role}]: {content}")

    # Keep last 15 summaries (enough for context, not too many)
    kept = summary_parts[-15:] if len(summary_parts) > 15 else summary_parts

    summary = M(
        role="system",
        content=(
            "<system-reminder>\n"
            "[已压缩的历史上下文 — 以下是之前对话的摘要]\n"
            + "\n".join(kept)
            + "\n</system-reminder>"
        ),
    )

    result = list(head) + [summary] + list(tail)

    new_tokens = estimate_tokens(result, model_limit)
    logger.info(
        "Context compressed: %d msgs → %d msgs, ~%d → ~%d tokens",
        len(messages), len(result), tokens, new_tokens,
    )

    return result


def build_boundary_message(original_count: int, compressed_count: int) -> "Message":
    """Create a user-visible boundary message for context compression events."""
    from app.llm.types import Message as M

    return M(
        role="system",
        content=(
            f"[上下文自动压缩：由于对话较长，已将之前的 {original_count} 条消息"
            f"压缩为 {compressed_count} 条以保持响应质量。最近的对话内容未受影响。]"
        ),
    )
