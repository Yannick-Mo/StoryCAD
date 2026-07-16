"""Token-aware context compression for the autonomous agent loop.

Three compression layers, inspired by Claude Code's multi-layer pipeline
(``src/services/compact/``):

1. **micro_compact** — lightweight, per-turn.  Replaces cached tool
   results with short markers so the LLM still sees the schema/flow but
   avoids paying token cost for data it already processed.
2. **compress_history** — proactive, triggered at 80% threshold.
   ``head + summary + tail`` classic strategy.
3. **reactive_compress** — last-resort, triggered on API 413 / context
   overflow.  More aggressive than proactive compress.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.types import Message

logger = logging.getLogger(__name__)

# ── Default model context limits (characters, approximate) ──────────
DEFAULT_MODEL_LIMIT = 1_800_000  # ~900K tokens (chars estimate, 90% of 1M)

# ── Threshold ratios ────────────────────────────────────────────────
COMPRESS_THRESHOLD = 0.80
AGGRESSIVE_THRESHOLD = 0.95

# ── Message retention counts ───────────────────────────────────────
DEFAULT_HEAD_COUNT = 5
DEFAULT_TAIL_COUNT = 12
AGGRESSIVE_HEAD_COUNT = 3
AGGRESSIVE_TAIL_COUNT = 8
REACTIVE_HEAD_COUNT = 2
REACTIVE_TAIL_COUNT = 5

# ── Micro-compact config ────────────────────────────────────────────
# Micro-compact is disabled by default — tool results are never truncated.
# Set _MICRO_COMPACT_MAX_CHARS to a positive value to re-enable for
# extremely large results only (safety net).
_MICRO_COMPACT_MAX_CHARS: int = 0  # 0 = disabled

# Tools whose results carry entity IDs that downstream tools depend on.
# These must survive all compression layers so the LLM can chain
# list_* → extract ID → write_* across turns without re-querying.
_ID_SOURCE_TOOLS: set[str] = {
    "list_chapters", "list_scenes", "list_characters",
    "list_relations", "list_edges", "read_full_project",
    "read_chapter", "read_scene", "read_project_overview",
    "read_character", "search_nodes",
}


def _is_id_source_msg(msg: "Message") -> bool:
    """Return True if *msg* is a tool result from an ID-source tool."""
    if msg.role != "tool":
        return False
    content = msg.content or ""
    if not content.startswith("[工具执行结果:"):
        return False
    end = content.find("]")
    if end > 0:
        tool_name = content[7:end].strip()
        return tool_name in _ID_SOURCE_TOOLS
    return False


def estimate_tokens(messages: list["Message"], model_limit: int = DEFAULT_MODEL_LIMIT) -> int:
    """Estimate the token count of a message list.

    Uses a simple char/2 heuristic — fast enough to run every turn,
    accurate enough for threshold-based decisions.
    """
    total = 0
    for msg in messages:
        content = getattr(msg, "content", "") or ""
        total += len(content)
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


# ── Layer 1: Micro-compact (per-turn, lightweight) ─────────────────


def micro_compact(
    messages: list["Message"],
    keep_recent: int = 5,
) -> list["Message"]:
    """No-op per default — tool results are never truncated.

    If ``_MICRO_COMPACT_MAX_CHARS > 0``, compact any tool result larger
    than that threshold to a short marker, keeping the last *keep_recent*
    results intact.
    """
    if _MICRO_COMPACT_MAX_CHARS <= 0:
        return messages

    from app.llm.types import Message as M

    seen_large: list[int] = []
    for i, msg in enumerate(messages):
        if msg.role != "tool":
            continue
        content = msg.content or ""
        if len(content) > _MICRO_COMPACT_MAX_CHARS:
            seen_large.append(i)

    keep = set(seen_large[-keep_recent:]) if keep_recent > 0 else set()
    for i in seen_large:
        if i not in keep:
            messages[i] = M(
                role="tool",
                content=f"[工具结果已缓存: {len(messages[i].content or '')} chars]",
                tool_call_id=messages[i].tool_call_id,
                name=messages[i].name,
            )

    return messages


# ── Layer 2: Proactive compress (head + summary + tail) ────────────


def _msg_role_label(role: str) -> str:
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
    unchanged.
    """
    from app.llm.types import Message as M

    tokens = estimate_tokens(messages, model_limit)
    ratio = tokens / model_limit if model_limit else 0

    if ratio <= COMPRESS_THRESHOLD:
        return list(messages)

    if ratio > AGGRESSIVE_THRESHOLD:
        h = head_count if head_count is not None else AGGRESSIVE_HEAD_COUNT
        t = tail_count if tail_count is not None else AGGRESSIVE_TAIL_COUNT
    else:
        h = head_count if head_count is not None else DEFAULT_HEAD_COUNT
        t = tail_count if tail_count is not None else DEFAULT_TAIL_COUNT

    if len(messages) <= h + t + 2:
        return list(messages)

    head = messages[:h]
    tail = messages[-t:]
    middle = messages[h:-t]

    # Extract ID-source tool messages from middle so they survive compression
    preserved_id_msgs: list[M] = []
    rest_middle: list[M] = []
    for msg in middle:
        if _is_id_source_msg(msg):
            preserved_id_msgs.append(msg)
        else:
            rest_middle.append(msg)

    summary_parts: list[str] = []
    for msg in rest_middle:
        role = _msg_role_label(getattr(msg, "role", "unknown"))
        content = (getattr(msg, "content", "") or "")[:200]
        if content:
            summary_parts.append(f"[{role}]: {content}")

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

    result = list(head) + [summary] + preserved_id_msgs + list(tail)

    new_tokens = estimate_tokens(result, model_limit)
    logger.info(
        "Context compressed: %d msgs → %d msgs, ~%d → ~%d tokens",
        len(messages), len(result), tokens, new_tokens,
    )

    return result


# ── Layer 3: Reactive compress (413 / context overflow) ────────────


def reactive_compress(
    messages: list["Message"],
    *,
    model_limit: int = DEFAULT_MODEL_LIMIT,
) -> list["Message"]:
    """Aggressive compression for API 413 / context overflow recovery.

    More aggressive than ``compress_history``:
    - Keeps only first 1 message + last 3 messages.
    - Drops all tool messages (not user/assistant).

    This is a **last resort** — it heavily truncates context to free
    enough room for the model to continue.

    Inspired by Claude Code's ``reactiveCompact`` triggered on
    ``prompt_too_long`` error.
    """
    from app.llm.types import Message as M

    h = REACTIVE_HEAD_COUNT
    t = REACTIVE_TAIL_COUNT

    if len(messages) <= h + t + 1:
        return compress_history(
            messages, model_limit=model_limit,
            head_count=h, tail_count=t,
        )

    # Strategy: keep head + tail from non-tool messages, DROP all
    # non-ID-source tool messages, but PRESERVE ID-source tool messages
    # so the LLM can still look up entity IDs for downstream tool calls.
    id_source_msgs: list[M] = [m for m in messages if _is_id_source_msg(m)]
    non_tool: list[M] = [
        m for m in messages
        if m.role != "tool" or _is_id_source_msg(m)
    ]
    if len(non_tool) <= h + t:
        # Fall back to aggressive compress if stripping tools isn't enough
        return compress_history(
            messages, model_limit=model_limit,
            head_count=h, tail_count=t,
        )

    head = non_tool[:h]
    tail = non_tool[-t:]

    middle = non_tool[h:-t]
    summary_parts: list[str] = []
    for msg in middle:
        role_label = _msg_role_label(getattr(msg, "role", "unknown"))
        content = (getattr(msg, "content", "") or "")[:100]
        if content:
            summary_parts.append(f"[{role_label}]: {content}")

    kept = summary_parts[-8:] if len(summary_parts) > 8 else summary_parts
    summary = M(
        role="system",
        content=(
            "<system-reminder>\n"
            "[紧急上下文压缩 — 上下文过长已被截断]\n"
            + "\n".join(kept)
            + "\n</system-reminder>"
        ),
    )

    # Keep a reasonable number of ID-source messages at the end
    preserved = id_source_msgs[-3:] if len(id_source_msgs) > 3 else id_source_msgs
    result = list(head) + [summary] + list(tail) + preserved

    tokens_before = estimate_tokens(messages, model_limit)
    tokens_after = estimate_tokens(result, model_limit)
    logger.warning(
        "Reactive compress: %d msgs → %d msgs, ~%d → ~%d tokens (%.0f%% reduction)",
        len(messages), len(result), tokens_before, tokens_after,
        (1 - tokens_after / max(tokens_before, 1)) * 100,
    )

    return result


# ── Orchestrator ────────────────────────────────────────────────────


def compress_context(
    messages: list["Message"],
    *,
    model_limit: int = DEFAULT_MODEL_LIMIT,
    reactive: bool = False,
) -> list["Message"]:
    """Run the appropriate compression layer.

    Args:
        messages: Message list to compress.
        model_limit: Model context window limit.
        reactive: If True, use reactive compression (for 413 recovery).
                  Otherwise, use proactive compression.

    Returns:
        Compressed message list.
    """
    if reactive:
        return reactive_compress(messages, model_limit=model_limit)

    compressed = compress_history(messages, model_limit=model_limit)
    # If proactive compression wasn't enough (still over threshold),
    # escalate to reactive.
    if should_compress(compressed, model_limit):
        logger.warning("Proactive compress insufficient — escalating to reactive")
        return reactive_compress(messages, model_limit=model_limit)

    return compressed


def build_boundary_message(original_count: int, compressed_count: int, reactive: bool = False) -> "Message":
    """Create a user-visible boundary message for context compression events."""
    from app.llm.types import Message as M

    if reactive:
        label = "紧急压缩"
        detail = "由于上下文长度超出限制，已截断部分内容"
    else:
        label = "上下文自动压缩"
        detail = "由于对话较长，已将之前的对话内容压缩为摘要"

    return M(
        role="system",
        content=(
            f"[{label}：已将之前的 {original_count} 条消息"
            f"压缩为 {compressed_count} 条以保持响应质量。{detail}。最近的对话内容未受影响。]"
        ),
    )
