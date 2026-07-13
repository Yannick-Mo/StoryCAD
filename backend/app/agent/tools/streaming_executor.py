# backend/app/agent/tools/streaming_executor.py
# ============================================================================
# StreamingToolExecutor — executes tools as they arrive from a streaming LLM
# response, rather than waiting for the full response.
#
# Inspired by Claude Code's StreamingToolExecutor in query.ts:
#   - Read-only (SAFE) tools execute immediately in parallel.
#   - Write (EXCLUSIVE) tools queue and execute serially after SAFE tools
#     complete.
#   - BARRIER tools wait for all others (SAFE + EXCLUSIVE) before running.
# ============================================================================
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agent.tools.base import BaseTool, ConcurrencyMode, ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tool names whose *output* should be dropped from tool_results visible to
# the frontend (they're internal signalling tools, not meaningful to users).
_INTERNAL_TOOLS: set[str] = {"cowriter_analysis"}

# Tools whose output is typically very long and should be summarized.
_ANALYSIS_TOOL_NAMES: set[str] = {
    "analyze_chapter", "project_health", "check_consistency",
    "analyze_rhythm", "suggest_next",
}

# Generic list/structural tools — the LLM mostly needs IDs and names,
# not the full content of each entity.  Content-read tools (read_scene,
# read_full_project, list_characters) are EXCLUDED because they carry
# creative text that must be preserved in full.
_STRUCTURAL_TOOL_NAMES: set[str] = {
    "list_chapters", "list_scenes",
    "list_relations", "list_edges", "search_nodes",
}

# Tools that produce purely structural JSON.
# Content-creative tools (list_characters) are excluded.
_JSON_OUTPUT_TOOLS: set[str] = {
    "list_chapters", "list_scenes",
    "list_relations", "list_edges", "search_nodes",
    "project_health", "analyze_rhythm",
}


def _smart_summarise(data: str, max_chars: int, tool_name: str) -> str:
    """Structure-aware summarization instead of blind truncation.

    Three strategies:
    1. **JSON** — preserve top-level keys, truncate long arrays
       ("完整角色列表: 15 项，已显示 3 项")
    2. **Long text** — head + tail with middle compressed
    3. **Short** — return as-is
    """
    if len(data) <= max_chars:
        return data

    # Strategy 1: JSON structure preservation
    if tool_name in _JSON_OUTPUT_TOOLS or data.strip().startswith("{"):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                total = len(parsed)
                if total > 3:
                    kept = json.dumps(parsed[:3], ensure_ascii=False, indent=2)
                    return f"{kept}\n... (完整列表: {total} 项，已显示前 3 项)"
                return json.dumps(parsed, ensure_ascii=False, indent=2)[:max_chars]
            if isinstance(parsed, dict):
                # Truncate long string values
                truncated = {}
                for k, v in parsed.items():
                    if isinstance(v, str) and len(v) > 500:
                        truncated[k] = v[:200] + f"... [{len(v)} chars]"
                    elif isinstance(v, list) and len(v) > 5:
                        truncated[k] = v[:3] + [f"... ({len(v)} 项)"]
                    else:
                        truncated[k] = v
                result = json.dumps(truncated, ensure_ascii=False, indent=2)
                if len(result) > max_chars:
                    result = result[:max_chars] + f"\n... [truncated, {len(data)} chars total]"
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 2: Head + tail for long text
    half = max_chars // 2
    head = data[:half]
    tail = data[-half:] if len(data) > half * 2 else ""
    if tail:
        return f"{head}\n\n...[中间省略 {len(data) - max_chars} 字符]...\n\n{tail}"
    return data[:max_chars] + f"\n... [truncated, {len(data)} chars total]"


def _summarise_tool_output(tool_name: str, result: ToolResult, tool: BaseTool | None = None) -> dict[str, Any]:
    """Truncate very long tool outputs to avoid blowing up the context.

    Uses the tool's ``max_result_chars`` when available, otherwise falls
    back to a heuristic based on tool category.
    """
    if tool is not None and hasattr(tool, "_effective_max_result_chars"):
        max_chars = tool._effective_max_result_chars
    elif tool_name in _ANALYSIS_TOOL_NAMES:
        max_chars = 2000
    elif tool_name in _STRUCTURAL_TOOL_NAMES:
        max_chars = 4000
    else:
        max_chars = 8000

    data = result.data
    if isinstance(data, str) and len(data) > max_chars:
        data = _smart_summarise(data, max_chars, tool_name)
    elif data is None or data == "":
        data = "(empty)"
    return {
        "tool": tool_name,
        "success": result.success,
        "data": data,
        "error": result.error,
    }


# ---------------------------------------------------------------------------
# StreamingToolExecutor
# ---------------------------------------------------------------------------

class StreamingToolExecutor:
    """Executes tools as they arrive from a streaming LLM response.

    Lifecycle::

        executor = StreamingToolExecutor(tools, db)

        # Phase 1 – during streaming
        for chunk in llm_client.chat_stream_with_tools(...):
            if chunk.tool_call:
                executor.add_tool(chunk.tool_call, tool_use_id=...)
            for result in executor.get_completed_results():
                yield {"type": "tool_done", "data": result}

        # Phase 2 – after stream ends
        for result in await executor.get_remaining_results():
            yield {"type": "tool_done", "data": result}

        # If the model fallback path is taken, discard pending work:
        executor.discard()

    Concurrency rules:
      * SAFE tools execute immediately, serialised through an :class:`asyncio.Lock`
        because all tools share a single :class:`AsyncSession` instance which
        is **not** safe for concurrent use.
      * EXCLUSIVE tools are queued and execute serially *after* all SAFE
        tools complete.
      * BARRIER tools wait for SAFE + EXCLUSIVE to finish before running
        (they see the final state).
    """

    def __init__(self, tools: dict[str, BaseTool], db: Any = None,
                 project_id: str = "", user_id: str = "") -> None:
        self._tools = tools
        self._db = db
        self._project_id = project_id
        self._user_id = user_id

        # Serialise SAFE tool access — AsyncSession is not coroutine-safe
        self._safe_lock = asyncio.Lock()

        # Pending async tasks (tool_use_id -> (tool_name, Task))
        self._pending: dict[str, tuple[str, asyncio.Task]] = {}

        # Completed results: list of (tool_use_id, result_dict)
        self._completed: list[tuple[str, dict]] = []

        # Queued EXCLUSIVE tools: (tool_name, args, tool_use_id)
        self._queued_exclusive: list[tuple[str, dict, str]] = []

        # Queued BARRIER tools: (tool_name, args, tool_use_id)
        self._queued_barrier: list[tuple[str, dict, str]] = []

        self._discarded = False

        # Track the last user message for mode checks
        self._blocked_writes: list[tuple[str, dict, str]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_tool(
        self,
        tool_use: Any,
        tool_use_id: str = "",
    ) -> None:
        """Called when a complete tool_use block arrives in the stream.

        Args:
            tool_use: A ``ToolCall`` instance or dict with ``function.name``
                      and ``function.arguments``.
            tool_use_id: The tool use block id from the LLM.

        Mode-gating is NOT performed here — that's the interceptor layer's
        job.  The executor simply queues tools by concurrency mode.
        """
        if self._discarded:
            return

        # Extract tool name and args from various input shapes
        tool_name, args = _extract_tool_call_info(tool_use)
        if not tool_name:
            logger.warning("StreamingToolExecutor.add_tool: could not extract tool name")
            return

        # Resolve tool instance
        tool = self._tools.get(tool_name)
        if not tool:
            err = {"tool": tool_name, "success": False, "error": f"Tool '{tool_name}' not found"}
            self._completed.append((tool_use_id, err))
            return

        # Determine concurrency
        concurrency = tool._effective_concurrency

        if concurrency == ConcurrencyMode.SAFE:
            task = asyncio.create_task(
                self._execute_tool(tool_name, args, tool_use_id)
            )
            self._pending[tool_use_id or tool_name] = (tool_name, task)
        elif concurrency == ConcurrencyMode.EXCLUSIVE:
            self._queued_exclusive.append((tool_name, args, tool_use_id))
        elif concurrency == ConcurrencyMode.BARRIER:
            self._queued_barrier.append((tool_name, args, tool_use_id))
        else:
            # Unknown concurrency mode – treat as EXCLUSIVE
            self._queued_exclusive.append((tool_name, args, tool_use_id))

    def get_completed_results(self) -> list[dict]:
        """Yield completed results during streaming.

        Non-blocking — only returns tasks that have already finished.
        Call this for every chunk or at a polling interval during the stream.

        Returns:
            List of result dicts for tools that have completed since the
            last call.  Each dict has ``{tool, success, data, error}``.
        """
        results: list[dict] = []
        done_ids: list[str] = []
        for tid, (tool_name, task) in list(self._pending.items()):
            if task.done():
                done_ids.append(tid)
                try:
                    result = task.result()
                    results.append(result)
                except asyncio.CancelledError:
                    results.append({"tool": tool_name, "success": False, "error": "Cancelled", "_tool_use_id": tid})
                except Exception as exc:
                    results.append({"tool": tool_name, "success": False, "error": str(exc), "_tool_use_id": tid})

        for tid in done_ids:
            del self._pending[tid]

        self._completed.extend((r.get("tool", ""), r) for r in results)
        return results

    # ── Split API for interceptor-aware execution ──────────────────────
    # The autonomous loop calls these in order:
    #   1. add_tool() during streaming (SAFE runs immediately; EXCL/BARRIER queued)
    #   2. await_pending_safe() after stream — waits for in-flight SAFE tools
    #   3. get_queued_tools() — returns queued EXCL/BARRIER tools (no execution)
    #   4. interceptor decides which tools are allowed
    #   5. execute_tool() — public, called by loop for each allowed tool
    #   6. clear_queued() — discard tools blocked by interceptor

    async def await_pending_safe(self) -> list[dict]:
        """Wait for in-flight SAFE tools only. Does NOT touch queued tools.

        Returns:
            Results from SAFE tools that completed (including those already
            yielded via ``get_completed_results``).
        """
        if self._discarded:
            return []

        if self._pending:
            tasks = [task for _, task in self._pending.values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            for tid, (tool_name, task) in list(self._pending.items()):
                try:
                    result = task.result()
                    self._completed.append((tid, result))
                except asyncio.CancelledError:
                    self._completed.append((tid, {"tool": tool_name, "success": False, "error": "Cancelled", "_tool_use_id": tid}))
                except Exception as exc:
                    self._completed.append((tid, {"tool": tool_name, "success": False, "error": str(exc), "_tool_use_id": tid}))
            self._pending.clear()

        return [r for _, r in self._completed]

    def get_queued_tools(self) -> tuple[list[tuple[str, dict, str]], list[tuple[str, dict, str]]]:
        """Return queued EXCLUSIVE and BARRIER tools without executing them.

        Returns:
            ``(exclusive_list, barrier_list)`` where each list contains
            ``(tool_name, args, tool_use_id)`` tuples.
        """
        return list(self._queued_exclusive), list(self._queued_barrier)

    def clear_queued(self) -> None:
        """Discard queued EXCLUSIVE/BARRIER tools without executing them.

        Called when the interceptor blocks, needs confirmation, or captures
        options — the queued tools should not execute.
        """
        self._queued_exclusive.clear()
        self._queued_barrier.clear()

    async def get_remaining_results(self) -> list[dict]:
        """Wait for all pending SAFE tools, then execute queued tools serially.

        Order:
          1. Await all remaining SAFE tasks.
          2. Execute EXCLUSIVE tools serially (one at a time).
          3. Execute BARRIER tools serially.

        Returns:
            All results accumulated throughout the executor's lifecycle
            (including those returned earlier by ``get_completed_results``).

        Note:
            Prefer the split API (``await_pending_safe`` + ``get_queued_tools``
            + ``execute_tool``) in the autonomous loop so the interceptor can
            gate EXCLUSIVE/BARRIER tools before execution.  This method exists
            for backward compatibility with the LangGraph path.
        """
        if self._discarded:
            return []

        # 1. Await all pending SAFE tools
        if self._pending:
            tasks = [task for _, task in self._pending.values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            for tid, (tool_name, task) in list(self._pending.items()):
                try:
                    result = task.result()
                    self._completed.append((tid, result))
                except asyncio.CancelledError:
                    self._completed.append((tid, {"tool": tool_name, "success": False, "error": "Cancelled", "_tool_use_id": tid}))
                except Exception as exc:
                    self._completed.append((tid, {"tool": tool_name, "success": False, "error": str(exc), "_tool_use_id": tid}))
            self._pending.clear()

        # 2. Execute EXCLUSIVE tools serially
        for tool_name, args, tool_use_id in self._queued_exclusive:
            if self._discarded:
                break
            result = await self._execute_tool(tool_name, args, tool_use_id)
            self._completed.append((tool_use_id, result))
        self._queued_exclusive.clear()

        # 3. Execute BARRIER tools serially
        for tool_name, args, tool_use_id in self._queued_barrier:
            if self._discarded:
                break
            result = await self._execute_tool(tool_name, args, tool_use_id)
            self._completed.append((tool_use_id, result))
        self._queued_barrier.clear()

        # Return all results as a flat list
        return [r for _, r in self._completed]

    def discard(self) -> None:
        """Discard all pending and queued work.

        Called when the model fallback path is taken (e.g. the streaming LLM
        call failed and a different model is being tried), or when the user
        cancels mid-stream.
        """
        self._discarded = True
        for _, task in self._pending.values():
            task.cancel()
        self._pending.clear()
        self._queued_exclusive.clear()
        self._queued_barrier.clear()
        self._completed.clear()
        self._blocked_writes.clear()

    # ------------------------------------------------------------------
    # Public execution entry-point (for interceptor-aware callers)
    # ------------------------------------------------------------------

    async def execute_tool(
        self, name: str, args: dict, tool_use_id: str = ""
    ) -> dict:
        """Execute a single tool and return a result dict.

        Public — called by the autonomous loop for tools that passed the
        interceptor gates.  Also called internally by ``_execute_tool``.
        """
        return await self._execute_tool(name, args, tool_use_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _execute_tool(
        self, name: str, args: dict, tool_use_id: str = ""
    ) -> dict:
        """Execute a single tool and return a result dict.

        The result always includes ``_tool_use_id`` so callers can correlate
        results with their originating tool-use blocks.
        """
        tool = self._tools.get(name)
        if not tool:
            return {"tool": name, "success": False, "error": "Tool not found", "_tool_use_id": tool_use_id}

        # Inject project_id and user_id into tool args if missing (LLM often
        # omits them on chained tool calls).
        merged = dict(args)
        if self._project_id and "project_id" not in merged:
            merged["project_id"] = self._project_id
        if self._user_id and "user_id" not in merged:
            merged["user_id"] = self._user_id

        timeout = tool._effective_timeout if tool._effective_timeout else 30

        try:
            # SAFE tools share the same AsyncSession (not coroutine-safe), so
            # serialise their DB access through the executor lock.  EXCLUSIVE
            # and BARRIER tools are already serial via the queue.
            if tool._effective_concurrency == ConcurrencyMode.SAFE:
                async with self._safe_lock:
                    result: ToolResult = await asyncio.wait_for(
                        tool.run(db=self._db, **merged),
                        timeout=timeout,
                    )
            else:
                result: ToolResult = await asyncio.wait_for(
                    tool.run(db=self._db, **merged),
                    timeout=timeout,
                )
            d = _summarise_tool_output(name, result, tool)
            d["_tool_use_id"] = tool_use_id
            return d
        except asyncio.TimeoutError:
            return {"tool": name, "success": False, "error": f"Timed out after {timeout}s", "_tool_use_id": tool_use_id}
        except asyncio.CancelledError:
            raise
        except KeyError as ke:
            return {"tool": name, "success": False,
                    "error": f"缺少必要参数: {ke}。请检查工具描述中的 required 参数并全部提供",
                    "_tool_use_id": tool_use_id}
        except Exception as exc:
            logger.exception("Tool '%s' execution failed", name)
            return {"tool": name, "success": False, "error": str(exc), "_tool_use_id": tool_use_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_tool_call_info(tool_use: Any) -> tuple[str, dict]:
    """Extract (tool_name, args) from various input shapes.

    Accepts:
      - ``ToolCall`` dataclass (has ``.function`` dict with name/arguments)
      - ``StreamChunk`` dataclass (has ``.tool_call`` which is a ToolCall)
      - Plain dict with ``function.name`` and ``function.arguments``
    """
    # StreamChunk
    if hasattr(tool_use, "tool_call") and tool_use.tool_call is not None:
        tool_use = tool_use.tool_call

    # ToolCall
    if hasattr(tool_use, "function") and tool_use.function:
        fn = tool_use.function
        name = fn.get("name", "") if isinstance(fn, dict) else getattr(fn, "name", "")
        arguments = fn.get("arguments", "{}") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
    # Dict
    elif isinstance(tool_use, dict):
        fn = tool_use.get("function", {})
        name = fn.get("name", "")
        arguments = fn.get("arguments", "{}")
    else:
        return "", {}

    if isinstance(arguments, str):
        try:
            args = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            args = {}
    elif isinstance(arguments, dict):
        args = arguments
    else:
        args = {}

    name = name.strip()
    return name, args
