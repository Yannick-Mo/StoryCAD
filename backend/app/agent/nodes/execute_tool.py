from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.cowriter.mode import CoWriterMode
from app.agent.state import AgentState
from app.agent.tools import get_filtered_tools
from app.agent.tools.base import BaseTool, ToolResult
from app.llm.client import LLMClient
from app.llm.types import Message, StreamChunk, ToolCall as TCT

logger = logging.getLogger(__name__)

_READ_TOOL_TIMEOUT = 15
_WRITE_TOOL_TIMEOUT = 60
_ANALYSIS_TOOL_TIMEOUT = 120
_DEFAULT_TOOL_TIMEOUT = 30

_MAX_READ_BATCH_SIZE = 5

_ANALYSIS_TOOL_NAMES = {"analyze_chapter", "project_health", "check_consistency", "analyze_rhythm", "suggest_next"}


def _get_tool_timeout(tool: BaseTool) -> int:
    if tool.is_write_operation:
        return _WRITE_TOOL_TIMEOUT
    if tool.name in _ANALYSIS_TOOL_NAMES:
        return _ANALYSIS_TOOL_TIMEOUT
    return _READ_TOOL_TIMEOUT


def _validate_params(tool: BaseTool, args: dict) -> list[str]:
    errors: list[str] = []
    schema = tool.parameters
    if not schema:
        return errors
    required = schema.get("required", [])
    props = schema.get("properties", {})
    for r in required:
        if r not in args or args[r] is None:
            errors.append(f"Missing required param '{r}' for tool '{tool.name}'")
    for k in args:
        if k not in props:
            errors.append(f"Unknown param '{k}' for tool '{tool.name}'")
    return errors


async def _run_single_tool(
    tool_name: str,
    args: dict,
    tools: dict[str, BaseTool],
    db: AsyncSession,
    step_idx: int | None = None,
    description: str = "",
    user_id: str | None = None,
) -> tuple[dict, list[str]]:
    errors: list[str] = []
    inst = tools.get(tool_name)
    if not inst:
        err_msg = f"Tool '{tool_name}' not found in available tools"
        return {
            "tool": tool_name,
            "success": False,
            "error": err_msg,
            "params": args,
        }, [err_msg]

    validation_errors = _validate_params(inst, args)
    if validation_errors:
        err_msg = "; ".join(validation_errors)
        return {
            "tool": tool_name,
            "success": False,
            "error": err_msg,
            "params": args,
        }, validation_errors

    timeout = _get_tool_timeout(inst)
    try:
        tr: ToolResult = await asyncio.wait_for(
            inst.run(db=db, user_id=user_id, **args), timeout=timeout
        )
        result: dict[str, Any] = {
            "tool": tool_name,
            "success": tr.success,
            "data": tr.data,
        }
        if tr.error:
            result["error"] = tr.error
        if step_idx is not None:
            result["planned_step"] = step_idx
            result["description"] = description
        if not tr.success:
            err = tr.error or "Unknown error"
            errors.append(f"Tool '{tool_name}' failed: {err}")
            result["params"] = args
        return result, errors
    except asyncio.TimeoutError:
        err_msg = f"Tool '{tool_name}' timed out after {timeout}s"
        result: dict[str, Any] = {
            "tool": tool_name, "success": False,
            "error": err_msg, "params": args,
        }
        if step_idx is not None:
            result["planned_step"] = step_idx
        return result, [err_msg]
    except Exception as e:
        if isinstance(e, asyncio.CancelledError):
            raise
        err_msg = f"Tool '{tool_name}' error: {e}"
        result: dict[str, Any] = {
            "tool": tool_name, "success": False,
            "error": err_msg, "params": args,
        }
        if step_idx is not None:
            result["planned_step"] = step_idx
        return result, [str(e)]


def _is_read_only_tool(tool_name: str, tools: dict[str, BaseTool]) -> bool:
    from app.agent.tool_filter import READ_ONLY_TOOLS
    return tool_name in READ_ONLY_TOOLS


async def _run_tool_batch(
    step_specs: list[tuple[int, str, dict, str]],
    tools: dict[str, BaseTool],
    db: AsyncSession,
    user_id: str | None = None,
) -> tuple[list[dict], list[str]]:
    """Run multiple independent read-only tools in parallel.

    step_specs: list of (step_idx, tool_name, args, description)
    Returns (results_sorted_by_idx, all_errors).
    """

    async def _run_one(step_idx: int, tool_name: str, args: dict, description: str) -> tuple[int, dict, list[str]]:
        result, errors = await _run_single_tool(tool_name, args, tools, db, step_idx, description, user_id=user_id)
        return step_idx, result, errors

    tasks = [_run_one(si, tn, a, d) for si, tn, a, d in step_specs]
    completed = await asyncio.gather(*tasks)

    completed.sort(key=lambda x: x[0])

    all_results: list[dict] = []
    all_errors: list[str] = []
    for _, result, errors in completed:
        all_results.append(result)
        all_errors.extend(errors)

    return all_results, all_errors


async def _execute_planned_step(
    state: AgentState, tools: dict, db: AsyncSession
) -> dict:
    planned_steps = state.get("planned_steps", [])
    step_idx = state.get("current_step_index", 0)
    errors: list[str] = list(state.get("errors", []))
    steps: list[dict] = list(state.get("intermediate_steps", []))

    if step_idx >= len(planned_steps):
        return {
            "pending_plan": {},
            "plan_confirmed": False,
            "current_step_index": 0,
        }

    # Scan ahead for consecutive read-only steps we can parallelize
    batch_indices: list[int] = []
    for i in range(step_idx, len(planned_steps)):
        if len(batch_indices) >= _MAX_READ_BATCH_SIZE:
            break
        tool_name = planned_steps[i].get("tool", "")
        if _is_read_only_tool(tool_name, tools):
            batch_indices.append(i)
        else:
            break

    if len(batch_indices) > 1:
        # Parallel batch execution
        step_specs = [
            (
                idx,
                planned_steps[idx].get("tool", ""),
                planned_steps[idx].get("params", {}),
                planned_steps[idx].get("description", ""),
            )
            for idx in batch_indices
        ]
        batch_results, tool_errors = await _run_tool_batch(step_specs, tools, db, user_id=state.get("user_id"))
        errors.extend(tool_errors)

        for idx, result_ in zip(batch_indices, batch_results):
            sp = planned_steps[idx]
            steps.append({
                "action": sp.get("tool", ""),
                "args": sp.get("params", {}),
                "result": result_,
                "planned_step": idx,
                "description": sp.get("description", ""),
            })

        has_error = any(not r.get("success", True) for r in batch_results)
        current_retry = state.get("retry_count", 0)
        max_retry = state.get("max_retries", 3)
        last_idx = batch_indices[-1]

        if has_error and current_retry >= max_retry:
            # Retries exhausted — force-advance past the batch (skip)
            step_idx = last_idx + 1
        elif has_error:
            # Keep at batch start for retry
            step_idx = batch_indices[0]
        else:
            step_idx = last_idx + 1

        is_last = step_idx >= len(planned_steps)

        return {
            "tool_results": state.get("tool_results", []) + batch_results,
            "intermediate_steps": steps,
            "current_step_index": step_idx,
            "retry_count": 0 if not has_error else (current_retry + 1),
            "errors": errors,
            "pending_plan": {} if is_last else state.get("pending_plan", {}),
            "plan_confirmed": False if is_last else state.get("plan_confirmed", False),
        }

    # Single step execution (write tool, analysis tool, or lone read tool)
    idx = batch_indices[0] if batch_indices else step_idx
    step = planned_steps[idx]
    tool_name = step.get("tool", "")
    args = step.get("params", {})
    description = step.get("description", "")

    result, tool_errors = await _run_single_tool(
        tool_name, args, tools, db, idx, description, user_id=state.get("user_id")
    )
    errors.extend(tool_errors)
    steps.append({
        "action": tool_name, "args": args, "result": result,
        "planned_step": idx, "description": description,
    })
    has_error = not result.get("success", True)
    current_retry = state.get("retry_count", 0)
    max_retry = state.get("max_retries", 3)

    if has_error and current_retry >= max_retry:
        # Retries exhausted — force-advance past failed step (skip)
        next_idx = idx + 1
    elif has_error:
        next_idx = idx  # Keep for retry
    else:
        next_idx = idx + 1

    is_last = next_idx >= len(planned_steps)

    return {
        "tool_results": state.get("tool_results", []) + [result],
        "intermediate_steps": steps,
        "current_step_index": next_idx,
        "retry_count": 0 if not has_error else (current_retry + 1),
        "errors": errors,
        "pending_plan": {} if is_last else state.get("pending_plan", {}),
        "plan_confirmed": False if is_last else state.get("plan_confirmed", False),
    }


async def _execute_tool_call(
    state: AgentState, tools: dict, db: AsyncSession, tool_descriptions: str = "",
    llm_client: LLMClient | None = None,
) -> dict:
    """Execute tool calls from the LLM. If tool_calls is empty (the common case
    because classify_intent passes tools=None to the LLM to prevent tool-calling
    during classification), re-invoke the LLM with tools enabled to generate
    actual tool calls — otherwise we'd reach here with intent=tool_call but
    nothing to execute, falling through to generate which only *describes* what
    it would do without actually doing it.
    """
    from app.agent.tool_filter import READ_ONLY_TOOLS
    from app.agent.prompts import render_prompt
    from app.agent.prompts.builder import get_prompt_builder

    mode = state.get("mode", "chat")
    tool_calls = state.get("tool_calls", [])
    results: list[dict] = []
    steps: list[dict] = list(state.get("intermediate_steps", []))
    errors: list[str] = list(state.get("errors", []))
    has_error = False
    was_write_blocked = False

    # ── If we have no tool_calls, re-generate them with tools enabled ──
    if not tool_calls and llm_client:
        user_msgs = [m for m in state.get("messages", []) if m.role == "user"]
        if not user_msgs:
            return {
                "tool_results": state.get("tool_results", []),
                "errors": errors + ["No user message to generate tool calls from"],
                "current_intent": "simple_q",
            }

        last_user = user_msgs[-1]

        # Build a focused tool-execution system prompt
        proj = state.get("project_context", {}).get("project", {})
        pid = state.get("project_id", "")
        project_info = ""
        if proj:
            title = proj.get("title", "未命名")
            genre = proj.get("genre", "")
            project_info = f"当前项目: {title}"
            if genre:
                project_info += f"({genre})"
            if pid:
                project_info += f" [project_id: {pid}]"

        system = render_prompt("tool_execution", **{
            "project_info": project_info,
            "project_id": pid,
            "mode": mode,
            "tool_descriptions": tool_descriptions,
            "last_errors": "; ".join(errors[-3:]) if errors else "none",
        })
        if not system:
            # Fallback: use the modular builder's tool_execution_context + identity
            builder = get_prompt_builder()
            base = builder.build(["identity"])
            exec_ctx = builder.render_dynamic_section("tool_execution_context",
                project_id=pid,
                project_info=project_info,
                tool_descriptions=tool_descriptions,
                last_errors="; ".join(errors[-3:]) if errors else "none",
                mode=mode,
            )
            system = f"{base}\n\n{exec_ctx}"
        if not system:
            system = (
                "你是工具执行助手。根据用户请求，调用合适的工具。\n"
                f"项目 ID 是 {pid}。\n\n"
                "可用工具:\n"
                f"{tool_descriptions}\n\n"
                "如果用户要求执行写操作且当前模式允许，请直接调用对应工具。"
                "如果当前模式不允许写入，回复说明而不是调用工具。"
            )

        try:
            # Convert tool dicts to ToolDef for LLM
            tool_defs = [t.to_openai_tool() for t in tools.values()]
            tool_def_objects = [
                type("ToolDef", (), {"type": d["type"], "function": d["function"]})()
                for d in tool_defs
            ]

            result = await llm_client.chat(
                messages=[
                    Message(role="system", content=system),
                    Message(role="user", content=last_user.content or ""),
                ],
                tools=tool_def_objects,
                temperature=0.2,
                request_id=state.get("trace_id", ""),
            )

            if result.tool_calls:
                # Convert LLM tool_calls to state tool_calls format
                from app.llm.types import ToolCall as TCT
                converted: list = []
                for tc in result.tool_calls:
                    if isinstance(tc, TCT):
                        converted.append(tc)
                    elif isinstance(tc, dict):
                        converted.append(TCT(
                            id=tc.get("id", ""),
                            function=tc.get("function", {}),
                        ))
                tool_calls = converted
                logger.info(
                    "_execute_tool_call: LLM regenerated %d tool calls: %s",
                    len(tool_calls),
                    [(tc.function.get("name", "") if tc.function else "?") for tc in tool_calls],
                )
            else:
                # LLM chose not to call any tools — fall through to generate
                logger.info("_execute_tool_call: LLM generated no tool calls even with tools enabled")
                return {
                    "tool_results": state.get("tool_results", []),
                    "errors": errors,
                    "current_intent": "simple_q",
                }
        except Exception as e:
            logger.error("_execute_tool_call: LLM tool call generation failed: %s", e)
            return {
                "tool_results": state.get("tool_results", []),
                "errors": errors + [f"工具调用生成失败: {e}"],
                "current_intent": "simple_q",
            }

    for tc in tool_calls:
        fn_name = ""
        args: dict = {}
        if tc.function:
            fn_name = tc.function.get("name", "")
            try:
                args = json.loads(tc.function.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}

        if mode == "chat" and fn_name and fn_name not in READ_ONLY_TOOLS:
            result = {
                "tool": fn_name,
                "success": False,
                "error": f"对话模式禁止写入操作，工具 '{fn_name}' 被拦截",
                "params": args,
            }
            results.append(result)
            errors.append(f"Write tool '{fn_name}' blocked in chat mode")
            steps.append({"action": fn_name, "args": args, "result": result})
            has_error = True
            was_write_blocked = True
            continue

        result, tool_errors = await _run_single_tool(fn_name, args, tools, db, user_id=state.get("user_id"))
        results.append(result)
        errors.extend(tool_errors)
        steps.append({"action": fn_name, "args": args, "result": result})
        if not result.get("success", True):
            has_error = True

    return {
        "tool_results": state.get("tool_results", []) + results,
        "intermediate_steps": steps,
        "retry_count": 0 if not has_error else (state.get("retry_count", 0) + 1),
        "errors": errors,
        "current_intent": "simple_q" if was_write_blocked else state.get("current_intent", "tool_call"),
        "retry_context": None if not has_error else (
            {
                "failed_step": fn_name if has_error else None,
                "error": errors[-1] if errors else None,
            }
        ),
    }


async def _execute_tool_call_streaming(
    state: AgentState,
    tools: dict[str, BaseTool],
    tool_descriptions: str,
    llm_client: LLMClient,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Streaming version -- execute tools as they arrive from the LLM.

    Unlike :func:`_execute_tool_call` which calls the LLM synchronously and
    then executes tools, this function:
      1. Streams the LLM response with tools enabled.
      2. As each complete tool_use block arrives, hands it to
         :class:`StreamingToolExecutor` for immediate execution.
      3. Yields ``_stream_token`` dicts for text content (like generate does).
      4. Yields ``_tool_done`` dicts as read-only (SAFE) tools complete.
      5. After the stream ends, waits for remaining SAFE tools and runs
         queued write tools serially, yielding their results.

    This is the optimized path used when the LLM client supports
    ``chat_stream_with_tools``.  It avoids the round-trip delay of waiting
    for the full LLM response before starting tool execution.
    """
    from app.agent.tool_filter import READ_ONLY_TOOLS
    from app.agent.prompts import render_prompt
    from app.agent.prompts.builder import get_prompt_builder
    from app.agent.tools.streaming_executor import StreamingToolExecutor

    mode = state.get("mode", "chat")
    errors: list[str] = list(state.get("errors", []))
    results_accum: list[dict] = []
    steps: list[dict] = list(state.get("intermediate_steps", []))
    has_error = False
    was_write_blocked = False

    # -- Build the system prompt (same as _execute_tool_call) --
    proj = state.get("project_context", {}).get("project", {})
    pid = state.get("project_id", "")
    project_info = ""
    if proj:
        title = proj.get("title", "未命名")
        genre = proj.get("genre", "")
        project_info = f"当前项目: {title}"
        if genre:
            project_info += f"({genre})"
        if pid:
            project_info += f" [project_id: {pid}]"

    system = render_prompt("tool_execution", **{
        "project_info": project_info,
        "project_id": pid,
        "mode": mode,
        "tool_descriptions": tool_descriptions,
        "last_errors": "; ".join(errors[-3:]) if errors else "none",
    })
    if not system:
        builder = get_prompt_builder()
        base = builder.build(["identity"])
        exec_ctx = builder.render_dynamic_section("tool_execution_context",
            project_id=pid,
            project_info=project_info,
            tool_descriptions=tool_descriptions,
            last_errors="; ".join(errors[-3:]) if errors else "none",
            mode=mode,
        )
        system = f"{base}\n\n{exec_ctx}"
    if not system:
        system = (
            "你是工具执行助手。根据用户请求，调用合适的工具。\n"
            f"项目 ID 是 {pid}。\n\n"
            "可用工具:\n"
            f"{tool_descriptions}\n\n"
            "如果用户要求执行写操作且当前模式允许，请直接调用对应工具。"
            "如果当前模式不允许写入，回复说明而不是调用工具。"
        )

    user_msgs = [m for m in state.get("messages", []) if m.role == "user"]
    if not user_msgs:
        yield {"_stream_done": True, "tool_results": state.get("tool_results", []),
               "errors": errors + ["No user message to generate tool calls from"],
               "current_intent": "simple_q"}
        return

    last_user = user_msgs[-1]

    # -- Build tool definitions --
    tool_defs = [t.to_openai_tool() for t in tools.values()]
    tool_def_objects = [
        type("ToolDef", (), {"type": d["type"], "function": d["function"]})()
        for d in tool_defs
    ]

    # -- Set up the streaming executor --
    executor = StreamingToolExecutor(tools, db=db)
    content_parts: list[str] = []
    tool_calls_received = False

    try:
        async for chunk in llm_client.chat_stream_with_tools(
            messages=[
                Message(role="system", content=system),
                Message(role="user", content=last_user.content or ""),
            ],
            tools=tool_def_objects,
            temperature=0.2,
            request_id=state.get("trace_id", ""),
        ):
            # -- Content: yield as stream tokens --
            if chunk.content:
                content_parts.append(chunk.content)
                yield {"_stream_token": chunk.content}

            # -- Tool call: hand to executor immediately --
            if chunk.tool_call:
                tool_calls_received = True
                fn = chunk.tool_call.function or {}
                fn_name = fn.get("name", "").strip()
                args_raw = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except (json.JSONDecodeError, TypeError):
                    args = {}

                logger.debug("streaming tool: %s args=%s", fn_name,
                             json.dumps(args, ensure_ascii=False)[:120])

                executor.add_tool(
                    chunk.tool_call,
                    tool_use_id=chunk.tool_call.id,
                    mode=mode,
                    read_only_tool_names=READ_ONLY_TOOLS,
                )

            # -- Check for completed SAFE tools, yield tool_done events --
            for result in executor.get_completed_results():
                results_accum.append(result)
                steps.append({
                    "action": result.get("tool", ""),
                    "args": result.get("params", {}),
                    "result": result,
                })
                if not result.get("success", True):
                    has_error = True
                yield {"_tool_done": result}

            # -- Finish reason: stream ended --
            if chunk.finish_reason:
                logger.debug("streaming_llm finish_reason=%s", chunk.finish_reason)

    except Exception as exc:
        logger.exception("Streaming tool call generation failed")
        executor.discard()
        yield {"_stream_done": True, "tool_results": state.get("tool_results", []),
               "errors": errors + [f"工具调用生成失败: {exc}"],
               "current_intent": "simple_q"}
        return

    # -- Wait for remaining SAFE + execute queued EXCLUSIVE/BARRIER tools --
    remaining = await executor.get_remaining_results()
    for result in remaining:
        # Avoid double-counting results already yielded via get_completed_results
        already = any(
            r.get("tool") == result.get("tool") and r.get("success") is result.get("success")
            for r in results_accum
        )
        if not already:
            results_accum.append(result)
            steps.append({
                "action": result.get("tool", ""),
                "args": result.get("params", {}),
                "result": result,
            })
            if not result.get("success", True):
                has_error = True
            yield {"_tool_done": result}

    # Check for blocked writes
    for r in results_accum:
        if not r.get("success") and "对话模式禁止写入操作" in (r.get("error") or ""):
            was_write_blocked = True
            break

    if not tool_calls_received and not results_accum:
        # LLM chose not to call any tools
        yield {"_stream_done": True, "tool_results": state.get("tool_results", []),
               "errors": errors, "current_intent": "simple_q"}
        return

    # -- Yield final state update --
    yield {
        "_stream_done": True,
        "tool_results": state.get("tool_results", []) + results_accum,
        "intermediate_steps": steps,
        "retry_count": 0 if not has_error else (state.get("retry_count", 0) + 1),
        "errors": errors,
        "current_intent": "simple_q" if was_write_blocked else state.get("current_intent", "tool_call"),
        "retry_context": None if not has_error else (
            {
                "failed_step": results_accum[-1].get("tool", "") if has_error and results_accum else None,
                "error": errors[-1] if errors else None,
            }
        ),
    }


async def _execute_cowriter(
    state: AgentState,
    tools: dict,
    llm_client: LLMClient,
    tool_descriptions: str,
) -> dict:
    errors: list[str] = list(state.get("errors", []))
    steps: list[dict] = list(state.get("intermediate_steps", []))
    project_ctx = state.get("project_context", {})
    session: dict = state.get("cowriter_session", {})

    # Filter tool descriptions by active skills
    active_skills = state.get("active_skills", [])
    filtered_tools = get_filtered_tools(tools, active_skills)
    filtered_desc = "\n".join(
        f"- {t.name}: {t.description}" for t in filtered_tools.values()
    )

    cw = CoWriterMode(filtered_desc or tool_descriptions)

    try:
        system_prompt = cw.build_system_prompt(
            project_ctx, list(state["messages"]), session=session,
            project_id=state.get("project_id", ""),
        )

        # Include recent conversation for context (up to 3 user-assistant pairs)
        all_msgs = list(state["messages"])
        recent = [m for m in all_msgs if m.role in ("user", "assistant")][-4:]

        llm_msgs = [
            Message(role="system", content=system_prompt),
            *recent,
        ]

        result = await llm_client.chat(
            messages=llm_msgs, response_format="json_object",
            request_id=state.get("trace_id", ""),
        )
        parsed = cw.parse_response(result.content or "{}")
        options = parsed.get("options", [])
        analysis = parsed.get("analysis", "")
        session_update = parsed.get("session_update", {})

        # Defensive: if analysis looks like raw JSON (parse_response fell back),
        # try to extract the actual text from it
        if analysis.startswith("{"):
            try:
                raw = json.loads(analysis)
                if isinstance(raw, dict):
                    for key in ("analysis", "response", "text", "content"):
                        val = raw.get(key)
                        if isinstance(val, str) and val.strip():
                            analysis = val
                            break
            except (json.JSONDecodeError, ValueError):
                pass

        # Build/update session from LLM's session_update
        if not session or not session.get("phase"):
            session = {
                "is_active": True,
                "phase": "explore",
                "goal": "",
                "current_focus": "",
                "decisions": [],
            }

        if session_update:
            if "phase" in session_update:
                session["phase"] = session_update["phase"]
            if "goal" in session_update:
                session["goal"] = session_update["goal"]
            if "current_focus" in session_update:
                session["current_focus"] = session_update["current_focus"]
            if session_update.get("is_complete"):
                pass  # Leave options & session as-is; LLM starts new task in next call

        return {
            "current_options": options,
            "cowriter_session": session,
            "tool_results": [
                {
                    "tool": "cowriter_analysis",
                    "success": True,
                    "data": analysis,
                }
            ],
            "intermediate_steps": steps
            + [
                {
                    "action": "cowriter_analysis",
                    "options_count": len(options),
                }
            ],
        }
    except Exception as e:
        errors.append(f"Cowriter analysis failed: {e}")
        return {
            "current_options": state.get("current_options", []),
            "cowriter_session": state.get("cowriter_session", {}),
            "tool_results": [
                {
                    "tool": "cowriter_analysis",
                    "success": False,
                    "error": str(e),
                }
            ],
            "errors": errors,
        }


async def _execute_cowriter_choice(
    state: AgentState, tools: dict, db: AsyncSession
) -> dict:
    """Handle user selection of a cowriter option card.

    BUG FIXES applied:
    - Bug 2: Write operations ALWAYS go through plan confirmation (never auto-execute
      from option cards). This ensures the user sees what tool+params will be used.
    - Bug 3: On tool failure, route back to cowriter (not blind retry with same params).
    - Bug 5: Auto-inject project_id from state when the tool requires it.
    - Bug 6: Roll back session phase to 'explore' on failure so LLM knows to regenerate.
    """
    errors: list[str] = list(state.get("errors", []))
    results: list[dict] = []
    steps: list[dict] = list(state.get("intermediate_steps", []))
    has_error = False

    user_content = (
        state["messages"][-1].content if state["messages"] else ""
    )
    options = state.get("current_options", [])
    session: dict = state.get("cowriter_session", {})

    selected = None

    # Try structured "[option:{id}]" format first (sent by frontend option click)
    m = re.search(r'\[option:\s*(\w+)\]', user_content.lower())
    if m:
        target_id = m.group(1)
        for opt in options:
            if opt.get("id", "").lower() == target_id:
                selected = opt
                break

    if not selected:
        for opt in options:
            opt_id = opt.get("id", "").lower()
            if re.search(r'\b' + re.escape(opt_id) + r'\b', user_content.lower()):
                selected = opt
                break
    if not selected:
        for opt in options:
            opt_label = opt.get("label", "").lower()
            if opt_label and (
                re.search(r'\b' + re.escape(opt_label[:8]) + r'\b', user_content.lower())
                or any(
                    re.search(r'\b' + re.escape(kw) + r'\b', user_content.lower())
                    for kw in ["选a", "选b", "选1", "选2"]
                )
            ):
                selected = opt
                break
    if not selected and options:
        selected = options[0]

    if selected and selected.get("action"):
        action = selected["action"]
        tool_name = action.get("tool", "")
        params = action.get("params", {})

        # ── Bug 5: Auto-inject project_id if the tool requires it ──
        tool_inst = tools.get(tool_name, {})
        if tool_inst:
            tool_schema = getattr(tool_inst, "parameters", {}) or {}
            tool_required = tool_schema.get("required", [])
            tool_props = tool_schema.get("properties", {})
            if "project_id" in tool_props and not params.get("project_id"):
                injected_pid = state.get("project_id", "")
                if injected_pid:
                    params["project_id"] = injected_pid
                    logger.info(
                        "cowriter_choice: auto-injected project_id=%s into %s",
                        injected_pid, tool_name,
                    )

            # ── Bug 2: Write operations ALWAYS go through plan confirmation ──
            # No auto-confirm from option cards. The user must review and approve.
            if tool_inst.is_write_operation:
                # But first, validate params before presenting the plan
                validation_errors = _validate_params(tool_inst, params)
                if validation_errors:
                    # ── Bug 3 & 6: params are invalid → route back to cowriter ──
                    err_msg = "; ".join(validation_errors)
                    logger.warning(
                        "cowriter_choice: invalid params from LLM option '%s': %s",
                        selected.get("label", ""), err_msg,
                    )
                    # Record the failure in session and roll back phase
                    round_num = len(session.get("decisions", [])) + 1
                    session.setdefault("decisions", []).append({
                        "round": round_num,
                        "choice": selected.get("id", ""),
                        "label": selected.get("label", ""),
                        "action": f"{tool_name}(invalid)",
                        "result": f"参数验证失败：{err_msg}",
                        "user_feedback": "",
                    })
                    session["phase"] = "explore"  # Bug 6: rollback
                    session["is_active"] = True
                    return {
                        "current_intent": "cowriter",  # Bug 3: re-route to cowriter
                        "current_options": options,
                        "cowriter_session": session,
                        "errors": errors + [f"选项 '{selected.get('label','')}' 参数有误: {err_msg}"],
                        "intermediate_steps": steps,
                        "tool_results": state.get("tool_results", []),
                    }

                step = {"tool": tool_name, "params": params}
                return {
                    "pending_plan": {
                        "steps": [step],
                        "reasoning": selected.get("description", "协写操作"),
                    },
                    "current_intent": "plan_confirm",
                    "current_options": options,
                    "cowriter_session": session,
                }

        # ── Read-only tool: execute directly (no confirmation needed) ──
        result, tool_errors = await _run_single_tool(
            tool_name, params, tools, db, user_id=state.get("user_id")
        )
        result["option"] = selected.get("label")
        results.append(result)
        errors.extend(tool_errors)
        steps.append(
            {
                "action": tool_name,
                "args": params,
                "result": result,
                "option": selected.get("label"),
            }
        )
        if not result.get("success", True):
            has_error = True

        # Record decision in session
        round_num = len(session.get("decisions", [])) + 1
        decision = {
            "round": round_num,
            "choice": selected.get("id", ""),
            "label": selected.get("label", ""),
            "action": f"{tool_name}({json.dumps(params, ensure_ascii=False)[:100]})",
            "result": "成功" if result.get("success") else f"失败：{result.get('error', '')}",
            "user_feedback": "",
        }
        session.setdefault("decisions", []).append(decision)
        if result.get("success") and not session.get("phase") == "complete":
            session["phase"] = "review"
        elif not result.get("success"):
            session["phase"] = "explore"  # Bug 6: rollback on failure
        session["is_active"] = True

        # ── Bug 3: on failure, route to cowriter for regeneration ──
        if has_error:
            return {
                "tool_results": state.get("tool_results", []) + results,
                "intermediate_steps": steps,
                "retry_count": 0,  # reset retry — cowriter will regenerate
                "errors": errors,
                "current_options": options,  # keep options visible for context
                "cowriter_session": session,
                "current_intent": "cowriter",  # re-route to cowriter for fix
            }

        return {
            "tool_results": state.get("tool_results", []) + results,
            "intermediate_steps": steps,
            "retry_count": 0,
            "errors": errors,
            "current_options": options,
            "cowriter_session": session,
            "current_intent": state.get("current_intent", "simple_q"),
        }
    elif selected:
        results.append(
            {
                "tool": "cowriter_choice",
                "success": True,
                "data": f"User selected: {selected.get('label', '')}",
            }
        )

    current_intent = state.get("current_intent", "simple_q")
    if not selected:
        current_intent = "simple_q"

    return {
        "tool_results": results if not selected else state.get("tool_results", []) + results,
        "intermediate_steps": steps,
        "retry_count": 0,
        "errors": errors,
        "current_options": options,
        "cowriter_session": session,
        "current_intent": current_intent,
    }


_CHAT_MODE_SAFETY_MESSAGE = "对话模式下不能执行写入操作。如需创建、修改、删除内容，请切换到协作模式。"


def _is_chat_write_attempt(state: AgentState) -> tuple[bool, str]:
    mode = state.get("mode", "chat")
    if mode != "chat":
        return False, ""
    intent = state.get("current_intent", "")
    if intent == "cowriter":
        return True, "Cowriter 意图在对话模式中不可用"
    return False, ""


async def _apply_recovery_decision(
    pending_decision: dict,
    state: AgentState,
) -> dict | None:
    """Apply the recovery transformation stored in pending_decision.

    Called when the graph routes back to execute_tool via the 'recovery'
    edge.  Applies the delay, state mutation, etc. that the RecoveryExecutor
    decided on.  Returns a dict of state updates to merge.
    """
    from app.agent.recovery import RecoveryAction, RecoveryExecutor, get_fallback_models

    action_str = pending_decision.get("action", "")
    try:
        action = RecoveryAction(action_str)
    except ValueError:
        logger.warning("Unknown recovery action: %s", action_str)
        return None

    delay = pending_decision.get("delay_seconds", 0)
    message = pending_decision.get("message", "")
    context = pending_decision.get("context", {})

    if delay > 0:
        await asyncio.sleep(delay)

    updates: dict = {}
    recovery_state = dict(state.get("recovery_state", {}))
    history: list[str] = list(recovery_state.get("recovery_history", []))
    history.append(action.value)
    recovery_state["recovery_history"] = history
    recovery_state["last_action"] = action.value
    recovery_state["last_message"] = message

    if action == RecoveryAction.RETRY:
        logger.info("Recovery retry after %ss: %s", delay, message)

    elif action == RecoveryAction.RETRY_WITH_ERROR_CONTEXT:
        # Inject the error into state so the LLM can self-correct
        errors: list[str] = list(state.get("errors", []))
        original = context.get("original_error", "")
        errors.append(
            f"[SELF-CORRECTION] Previous attempt failed: {original}"
        )
        updates["errors"] = errors
        updates["retry_context"] = {
            "failed": True,
            "error": original,
            "correction_attempt": context.get("retry_attempt", 1),
        }
        recovery_state["self_correction_applied"] = True

    elif action == RecoveryAction.RETRY_WITH_COMPRESSED_CONTEXT:
        executor = RecoveryExecutor()
        compressed = executor._compress_messages(state.get("messages", []))
        updates["messages"] = compressed
        recovery_state["context_compressed"] = True

    elif action == RecoveryAction.RETRY_ESCALATED_TOKENS:
        recovery_state["escalated_tokens"] = True

    elif action == RecoveryAction.SWITCH_MODEL:
        fallbacks = get_fallback_models()
        model_index = recovery_state.get("model_index", 0)
        if model_index < len(fallbacks):
            new_model = fallbacks[model_index]
            recovery_state["model_index"] = model_index + 1
            recovery_state["switched_model"] = new_model
            updates["_model_override"] = new_model
            logger.warning("Switching to fallback model: %s (index %d)", new_model, model_index)
        else:
            recovery_state["models_exhausted"] = True
            updates["errors"] = list(state.get("errors", [])) + [
                "All fallback models exhausted"
            ]

    elif action == RecoveryAction.GIVE_UP:
        recovery_state["gave_up"] = True
        recovery_state["gave_up_reason"] = message

    updates["recovery_state"] = recovery_state
    return updates


def create_execute_tool_node(
    tools: dict,
    llm_client: LLMClient,
    db: AsyncSession,
    tool_descriptions: str,
):
    async def execute_tool_node(state: AgentState):
        # Streaming flag: when True, the node yields _(stream_token|tool_done)
        # events for consumption by super_agent's astream_events loop.
        use_streaming = (
            state.get("current_intent") == "tool_call"
            and not state.get("planned_steps")
            and state.get("mode", "chat") != "chat"
        )

        # ── Layered error recovery pre-processing ──
        # When the router sets a pending_decision in recovery_state, apply
        # the recovery transformation (delay, compress, switch model, etc.)
        # before the normal intent dispatch runs.
        recovery_state = state.get("recovery_state", {})
        pending_decision = recovery_state.get("pending_decision")
        if pending_decision:
            recovery_updates = await _apply_recovery_decision(pending_decision, state)
            if recovery_updates:
                for k, v in recovery_updates.items():
                    if k == "messages" and isinstance(v, list):
                        # Replace messages entirely (for compression)
                        state[k] = v
                    elif k == "errors" and isinstance(v, list):
                        state[k] = v
                    elif k == "retry_context":
                        state[k] = v
                    elif k == "_model_override":
                        state[k] = v
                # Update recovery_state, clearing pending_decision
                new_rs = recovery_updates.get("recovery_state", recovery_state)
                new_rs.pop("pending_decision", None)
                state["recovery_state"] = new_rs
                logger.info(
                    "recovery applied: action=%s",
                    pending_decision.get("action", "unknown"),
                )

        # Chat mode safety gate: only read-only tools may execute
        blocked, reason = _is_chat_write_attempt(state)
        if blocked:
            result = {
                "errors": state.get("errors", []) + [reason],
                "tool_results": [{
                    "tool": "_safety_gate",
                    "success": False,
                    "data": _CHAT_MODE_SAFETY_MESSAGE,
                    "error": reason,
                }],
                "current_intent": "simple_q",
            }
            yield result
            return

        pending_plan = state.get("pending_plan", {})
        plan_confirmed = state.get("plan_confirmed", False)

        if pending_plan and not plan_confirmed:
            yield {
                "current_intent": "simple_q",
                "intermediate_steps": list(state.get("intermediate_steps", [])),
            }
            return

        if pending_plan and plan_confirmed:
            # Sync steps from pending_plan into planned_steps so
            # _execute_planned_step can find them.  The cowriter-choice
            # flow sets pending_plan but never runs the plan node, which
            # is where planned_steps normally gets populated.
            planned_steps = state.get("planned_steps", [])
            if not planned_steps and pending_plan.get("steps"):
                state["planned_steps"] = pending_plan["steps"]
            yield await _execute_planned_step(state, tools, db)
            return

        step_idx = state.get("current_step_index", 0)
        if step_idx < len(state.get("planned_steps", [])):
            yield await _execute_planned_step(state, tools, db)
            return

        intent = state.get("current_intent", "")

        if intent == "tool_call":
            if use_streaming:
                # ── Streaming path: execute tools as they arrive ──
                final: dict | None = None
                async for chunk in _execute_tool_call_streaming(
                    state, tools, tool_descriptions, llm_client, db,
                ):
                    if chunk.get("_stream_done"):
                        # Extract the final state update, discard the stream_done flag
                        final = {k: v for k, v in chunk.items() if not k.startswith("_stream")}
                    else:
                        yield chunk
                # Yield the final state dict (or fallback)
                yield final or {
                    "current_intent": "simple_q",
                }
            else:
                yield await _execute_tool_call(state, tools, db, tool_descriptions, llm_client)
        elif intent == "cowriter":
            yield await _execute_cowriter(
                state, tools, llm_client, tool_descriptions
            )
        elif intent == "cowriter_choice":
            yield await _execute_cowriter_choice(state, tools, db)
        elif intent == "complex":
            yield {
                "errors": state.get("errors", [])
                + ["Complex intent reached execute_tool without routing through plan node"],
                "current_intent": "simple_q",
                "intermediate_steps": list(state.get("intermediate_steps", [])),
                "tool_results": state.get("tool_results", []),
                "current_step_index": state.get("current_step_index", 0),
                "retry_count": state.get("retry_count", 0),
            }
        else:
            yield {
                "current_intent": "simple_q",
                "intermediate_steps": list(state.get("intermediate_steps", [])),
            }

    return execute_tool_node
