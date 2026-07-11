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


def _summarise_tool_output(tool_name: str, result: ToolResult) -> dict[str, Any]:
    """Truncate very long tool outputs to avoid blowing up the context."""
    max_chars = 2000 if tool_name in _ANALYSIS_TOOL_NAMES else 8000
    data = result.data
    if isinstance(data, str) and len(data) > max_chars:
        data = data[:max_chars] + f"\n... [truncated, {len(result.data)} chars total]"
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
      * SAFE tools execute immediately in parallel.
      * EXCLUSIVE tools are queued and execute serially *after* all SAFE
        tools complete.
      * BARRIER tools wait for SAFE + EXCLUSIVE to finish before running
        (they see the final state).
    """

    def __init__(self, tools: dict[str, BaseTool], db: Any = None) -> None:
        self._tools = tools
        self._db = db

        # Pending async tasks (tool_use_id -> Task)
        self._pending: dict[str, asyncio.Task] = {}

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
        *,
        mode: str = "cowriter",
        read_only_tool_names: set[str] | None = None,
    ) -> None:
        """Called when a complete tool_use block arrives in the stream.

        Args:
            tool_use: A ``ToolCall`` instance or dict with ``function.name``
                      and ``function.arguments``.
            tool_use_id: The tool use block id from the LLM.
            mode: ``"chat"`` or ``"cowriter"`` – if chat mode, writes are
                  skipped and reported as blocked.
            read_only_tool_names: Set of tool names allowed in chat mode.
                                  When *mode* is ``"chat"``, any tool not in
                                  this set is rejected.  When omitted,
                                  ``tool_filter.READ_ONLY_TOOLS`` is used.
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

        # Chat mode guard: block write tools
        if mode == "chat" and tool_name not in (read_only_tool_names or set()):
            err = {
                "tool": tool_name,
                "success": False,
                "error": f"对话模式禁止写入操作，工具 '{tool_name}' 被拦截",
                "params": args,
            }
            self._completed.append((tool_use_id, err))
            self._blocked_writes.append((tool_name, args, tool_use_id))
            return

        # Determine concurrency
        concurrency = tool._effective_concurrency

        if concurrency == ConcurrencyMode.SAFE:
            # Execute immediately in background
            task = asyncio.create_task(
                self._execute_tool(tool_name, args, tool_use_id)
            )
            self._pending[tool_use_id or tool_name] = task
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
        for tid, task in list(self._pending.items()):
            if task.done():
                done_ids.append(tid)
                try:
                    result = task.result()
                    results.append(result)
                except asyncio.CancelledError:
                    results.append({"tool": tid, "success": False, "error": "Cancelled"})
                except Exception as exc:
                    results.append({"tool": tid, "success": False, "error": str(exc)})

        for tid in done_ids:
            del self._pending[tid]

        self._completed.extend((r.get("tool", ""), r) for r in results)
        return results

    async def get_remaining_results(self) -> list[dict]:
        """Wait for all pending SAFE tools, then execute queued tools serially.

        Order:
          1. Await all remaining SAFE tasks.
          2. Execute EXCLUSIVE tools serially (one at a time).
          3. Execute BARRIER tools serially.

        Returns:
            All results accumulated throughout the executor's lifecycle
            (including those returned earlier by ``get_completed_results``).
        """
        if self._discarded:
            return []

        # 1. Await all pending SAFE tools
        if self._pending:
            tasks = list(self._pending.values())
            await asyncio.gather(*tasks, return_exceptions=True)
            for tid, task in list(self._pending.items()):
                try:
                    result = task.result()
                    self._completed.append((tid, result))
                except asyncio.CancelledError:
                    self._completed.append((tid, {"tool": tid, "success": False, "error": "Cancelled"}))
                except Exception as exc:
                    self._completed.append((tid, {"tool": tid, "success": False, "error": str(exc)}))
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
        for task in self._pending.values():
            task.cancel()
        self._pending.clear()
        self._queued_exclusive.clear()
        self._queued_barrier.clear()
        self._completed.clear()
        self._blocked_writes.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _execute_tool(
        self, name: str, args: dict, tool_use_id: str = ""
    ) -> dict:
        """Execute a single tool and return a result dict."""
        tool = self._tools.get(name)
        if not tool:
            return {"tool": name, "success": False, "error": "Tool not found"}

        timeout = tool._effective_timeout if tool._effective_timeout else 30

        try:
            result: ToolResult = await asyncio.wait_for(
                tool.run(db=self._db, **args),
                timeout=timeout,
            )
            return _summarise_tool_output(name, result)
        except asyncio.TimeoutError:
            return {"tool": name, "success": False, "error": f"Timed out after {timeout}s"}
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Tool '%s' execution failed", name)
            return {"tool": name, "success": False, "error": str(exc)}


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
