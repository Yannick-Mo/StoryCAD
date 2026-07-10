from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.cowriter.mode import CoWriterMode
from app.agent.state import AgentState
from app.agent.tools import get_filtered_tools
from app.agent.tools.base import BaseTool, ToolResult
from app.llm.client import LLMClient
from app.llm.types import Message

logger = logging.getLogger(__name__)

_READ_TOOL_TIMEOUT = 15
_WRITE_TOOL_TIMEOUT = 60
_ANALYSIS_TOOL_TIMEOUT = 120
_DEFAULT_TOOL_TIMEOUT = 30

# Maximum batch size for parallel read-only tool execution.
# Prevents resource exhaustion from too many concurrent DB queries.
_MAX_READ_BATCH_SIZE = 5


def _get_tool_timeout(tool: BaseTool) -> int:
    if tool.is_write_operation:
        return _WRITE_TOOL_TIMEOUT
    name = tool.name.lower()
    if any(kw in name for kw in ("analyze", "check", "health", "rhythm", "suggest")):
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
    inst = tools.get(tool_name)
    if not inst:
        return False
    return not inst.is_write_operation


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
            "pending_plan": [],
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
            "retry_count": current_retry + (1 if has_error else 0),
            "errors": errors,
            "pending_plan": [] if is_last else state.get("pending_plan", []),
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
        "retry_count": current_retry + (1 if has_error else 0),
        "errors": errors,
        "pending_plan": [] if is_last else state.get("pending_plan", []),
        "plan_confirmed": False if is_last else state.get("plan_confirmed", False),
    }


async def _execute_tool_call(
    state: AgentState, tools: dict, db: AsyncSession
) -> dict:
    from app.agent.tool_filter import READ_ONLY_TOOLS

    mode = state.get("mode", "chat")
    tool_calls = state.get("tool_calls", [])
    results: list[dict] = []
    steps: list[dict] = list(state.get("intermediate_steps", []))
    errors: list[str] = list(state.get("errors", []))
    has_error = False

    for tc in tool_calls:
        fn_name = ""
        args: dict = {}
        if tc.function:
            fn_name = tc.function.get("name", "")
            try:
                args = json.loads(tc.function.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}

        # Chat mode runtime safety: reject write operations
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
        "retry_count": state.get("retry_count", 0) + (1 if has_error else 0),
        "errors": errors,
        "retry_context": {
            "failed_step": fn_name if has_error else None,
            "error": tool_errors[-1] if has_error and tool_errors else None,
        }
        if has_error
        else None,
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

    # Filter tool descriptions by active skills
    active_skills = state.get("active_skills", [])
    filtered_tools = get_filtered_tools(tools, active_skills)
    filtered_desc = "\n".join(
        f"- {t.name}: {t.description}" for t in filtered_tools.values()
    )

    cw = CoWriterMode(filtered_desc or tool_descriptions)
    user_msg = state["messages"][-1] if state["messages"] else None
    user_content = user_msg.content if user_msg else ""

    try:
        system_prompt = cw.build_system_prompt(
            project_ctx, list(state["messages"])
        )
        msgs = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_content),
        ]
        result = await llm_client.chat(
            messages=msgs, response_format="json_object",
            request_id=state.get("trace_id", ""),
        )
        parsed = cw.parse_response(result.content or "{}")
        options = parsed.get("options", [])
        analysis = parsed.get("analysis", "")

        return {
            "current_options": options,
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
            "current_options": [],
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
    errors: list[str] = list(state.get("errors", []))
    results: list[dict] = []
    steps: list[dict] = list(state.get("intermediate_steps", []))
    has_error = False

    user_content = (
        state["messages"][-1].content if state["messages"] else ""
    )
    options = state.get("current_options", [])

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
            if opt_id in user_content.lower():
                selected = opt
                break
    if not selected:
        for opt in options:
            opt_label = opt.get("label", "").lower()
            if opt_label and (
                opt_label[:8] in user_content.lower()
                or any(
                    kw in user_content.lower()
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

        # Defer write operations to plan confirmation flow
        tool_inst = tools.get(tool_name)
        if tool_inst and tool_inst.is_write_operation:
            step = {
                "tool": tool_name,
                "params": params,
            }
            return {
                "pending_plan": {
                    "steps": [step],
                    "reasoning": selected.get("description", "协写操作"),
                },
                "current_intent": "plan_confirm",
                "current_options": [],
            }

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
    elif selected:
        results.append(
            {
                "tool": "cowriter_choice",
                "success": True,
                "data": f"User selected: {selected.get('label', '')}",
            }
        )

    return {
        "tool_results": state.get("tool_results", []) + results,
        "intermediate_steps": steps,
        "retry_count": state.get("retry_count", 0)
        + (1 if has_error else 0),
        "errors": errors,
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


def create_execute_tool_node(
    tools: dict,
    llm_client: LLMClient,
    db: AsyncSession,
    tool_descriptions: str,
):
    async def execute_tool_node(state: AgentState) -> dict:
        # Chat mode safety gate: only read-only tools may execute
        blocked, reason = _is_chat_write_attempt(state)
        if blocked:
            return {
                "errors": state.get("errors", []) + [reason],
                "tool_results": [{
                    "tool": "_safety_gate",
                    "success": False,
                    "data": _CHAT_MODE_SAFETY_MESSAGE,
                    "error": reason,
                }],
                "current_intent": "simple_q",
            }

        pending_plan = state.get("pending_plan", [])
        plan_confirmed = state.get("plan_confirmed", False)

        if pending_plan and plan_confirmed:
            return await _execute_planned_step(state, tools, db)

        step_idx = state.get("current_step_index", 0)
        if step_idx < len(state.get("planned_steps", [])):
            return await _execute_planned_step(state, tools, db)

        intent = state.get("current_intent", "")

        if intent == "tool_call":
            return await _execute_tool_call(state, tools, db)
        elif intent == "cowriter":
            return await _execute_cowriter(
                state, tools, llm_client, tool_descriptions
            )
        elif intent == "cowriter_choice":
            return await _execute_cowriter_choice(state, tools, db)
        elif intent == "complex":
            return {
                "errors": state.get("errors", [])
                + ["Complex intent reached execute_tool without routing through plan node"],
                "current_intent": "simple_q",
                "intermediate_steps": list(state.get("intermediate_steps", [])),
                "tool_results": state.get("tool_results", []),
                "current_step_index": state.get("current_step_index", 0),
                "retry_count": state.get("retry_count", 0),
            }
        else:
            return {
                "current_intent": "simple_q",
                "intermediate_steps": list(state.get("intermediate_steps", [])),
            }

    return execute_tool_node
