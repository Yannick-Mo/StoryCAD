from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncGenerator

from app.agent.nodes.classify_intent import _detect_plan_confirm
from app.agent.nodes.execute_tool import (
    _execute_cowriter,
    _execute_cowriter_choice,
    _execute_planned_step,
    _execute_tool_call_streaming,
    _run_single_tool,
)
from app.agent.prompts import render_prompt
from app.agent.prompts.builder import get_prompt_builder
from app.agent.state import AgentState
from app.agent.tools import get_filtered_tools, get_tool_descriptions
from app.agent.tools.base import BaseTool
from app.llm.client import LLMClient
from app.llm.types import Message, ToolCall as TCT
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Max turns before forcing stop
MAX_TURNS = 50
# Max recovery attempts per turn
MAX_RECOVERY = 3
# Max RAG chars for classify_intent
MAX_RAG_CHARS = 1000


# ── Intent classification helper ──────────────────────────────────────


async def _classify_intent(
    messages: list[Message],
    mode: str,
    project_context: dict,
    cowriter_session: dict,
    current_options: list,
    pending_plan: dict,
    errors: list[str],
    llm_client: LLMClient,
    tool_descriptions: str,
    retry_count: int,
    trace_id: str = "",
) -> str:
    """Determine user intent from the last message.

    Returns one of: simple_q, tool_call, cowriter, cowriter_choice,
    complex, plan_confirm, plan_reject.
    """
    last_msg = messages[-1] if messages else None
    if not last_msg or last_msg.role not in ("user", "tool"):
        return "simple_q"

    content = (last_msg.content or "").strip().lower()
    cowriter_active = mode == "cowriter"

    # --- Pending plan keyword detection (fast path, no LLM) ---
    if pending_plan:
        plan_decision = _detect_plan_confirm(content)
        if plan_decision == "plan_confirm":
            return "plan_confirm"
        elif plan_decision == "plan_reject":
            return "plan_reject"

    # --- Cowriter choice detection (keyword-based fast path) ---
    is_cowriter_choice = cowriter_active and (
        "[option:" in content
        or any(
            kw in content
            for kw in [
                "选a", "选b", "选c", "选1", "选2", "选3",
                "option a", "option b", "option c",
                "方案a", "方案b", "方案c",
                "方案一", "方案二", "方案三", "方案1", "方案2", "方案3",
                "我选",
            ]
        )
    )
    if cowriter_active and not is_cowriter_choice and "选择" in content:
        is_cowriter_choice = any(
            kw in content
            for kw in [
                "我选择", "选择方案", "选择第", "选择a", "选择b", "选择c",
                "方案一", "方案二", "方案三",
            ]
        )
    if cowriter_active and not is_cowriter_choice and current_options:
        adoption_kw = ["直接采用", "就用这个", "就按这个", "采用", "就这个", "直接写"]
        is_cowriter_choice = any(kw in content for kw in adoption_kw)
    if is_cowriter_choice and cowriter_active:
        return "cowriter_choice"

    # --- Session-aware continuation (soft override) ---
    session = cowriter_session or {}
    if cowriter_active and session.get("is_active") and session.get("phase") in ("review", "execute"):
        short = len(content.split()) <= 15 and len(content) <= 40
        is_refinement = any(
            kw in content
            for kw in [
                "再", "还", "更", "改", "修", "调", "细", "补充", "继续",
                "然后", "接着", "下一步", "再改", "再写", "换一个",
                "不够", "不好", "太", "重新",
                "more", "again", "continue", "further", "refine",
            ]
        )
        adoption = any(kw in content for kw in ["好的", "可以", "行", "就这样", "不错", "挺好", "ok"])
        if short and (is_refinement or adoption):
            return "cowriter"

    # --- Direct write detection in cowriter mode ---
    if cowriter_active and not current_options:
        direct_write_kw = [
            "帮我写", "帮我创作", "帮我生成", "直接写一段",
            "write a", "write for me", "write me",
        ]
        if any(kw in content for kw in direct_write_kw):
            return "cowriter"

    # --- LLM classification ---
    # Fast keyword hints for tool_call (used as fallback)
    tool_kw = [
        "创建", "删除", "修改", "更新", "添加", "写入",
        "create", "delete", "update", "add", "write",
        "分析", "检查", "analyze", "check",
        "搜索", "search",
    ]
    has_tool_hint = any(kw in content for kw in tool_kw)

    # Build classify system prompt
    last_ai_response = ""
    for msg in reversed(messages):
        if msg.role == "assistant":
            last_ai_response = (msg.content or "")[:500]
            break

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

    last_errs = [e for e in (errors or [])[-3:]] if errors else []

    system_text = render_prompt(
        "classify_intent",
        has_pending_plan=bool(pending_plan),
        retry_count=retry_count,
        max_retries=MAX_RECOVERY,
        last_errors="; ".join(last_errs) if last_errs else "none",
        mode=mode,
        rag_context=(project_context.get("rag_context", "") or "")[:MAX_RAG_CHARS],
        last_ai_response=last_ai_response,
        current_options=current_options,
        cowriter_session=session_info,
    )
    if not system_text:
        builder = get_prompt_builder()
        system_text = builder.build(["identity"])
        if not system_text:
            system_text = (
                "You are an intent classifier. Respond with JSON: "
                '{"intent": "simple_q|tool_call|cowriter|complex", "reason": "..."}'
            )

    tools_section = f"\n\nAvailable tools:\n{tool_descriptions}" if tool_descriptions else ""
    classify_msgs = [
        Message(role="system", content=system_text + tools_section),
        Message(role="user", content=content),
    ]

    intent = "simple_q"
    try:
        _t0 = time.monotonic()
        result = await llm_client.chat(
            messages=classify_msgs,
            tools=None,
            temperature=0.1,
            request_id=trace_id,
        )
        logger.debug("classify_intent LLM call took %.2fs", time.monotonic() - _t0)

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
            elif has_tool_hint:
                intent = "tool_call"
            else:
                intent = "simple_q"
    except Exception as e:
        logger.warning("Intent classification failed: %s", e)
        intent = "tool_call" if has_tool_hint else "simple_q"

    if intent not in ("simple_q", "tool_call", "cowriter", "complex"):
        intent = "simple_q"

    return intent


# ── Main Agent Loop ───────────────────────────────────────────────────


async def agent_loop(
    initial_state: AgentState,
    tools: dict[str, BaseTool],
    llm_client: LLMClient,
    db: AsyncSession,
    tool_descriptions: str,
) -> AsyncGenerator[dict, None]:
    """Main agent loop -- pure while(True) with no state machine framework.

    Inspired by Claude Code's queryLoop in query.ts.

    Yields events that the caller (SuperAgent.chat_stream) consumes:
        {"_step": str}             -- progress label (e.g. "读取项目数据...")
        {"_stream_token": str}     -- text token for buffering
        {"_tool_done": dict}       -- tool result (streaming)
        {"current_options": list}  -- cowriter option cards
        {"pending_plan": dict}     -- plan awaiting user confirmation
        {"_loop_done": True, "final_state": AgentState} -- terminal sentinel
    """
    # ── Mutable state ─────────────────────────────────────────────
    messages: list[Message] = list(initial_state.get("messages", []))
    project_id: str = initial_state.get("project_id") or ""
    user_id: str = initial_state.get("user_id") or ""
    conversation_id: str = initial_state.get("conversation_id") or ""
    mode: str = initial_state.get("mode", "chat")
    project_context: dict = initial_state.get("project_context", {})
    active_skills: list = initial_state.get("active_skills", [])
    trace_id: str = initial_state.get("trace_id", "")

    turn: int = 0
    errors: list[str] = list(initial_state.get("errors", []))
    tool_results: list[dict] = list(initial_state.get("tool_results", []))
    intermediate_steps: list[dict] = list(initial_state.get("intermediate_steps", []))

    # Cowriter state
    cowriter_session: dict = initial_state.get("cowriter_session", {}) or {}
    current_options: list = initial_state.get("current_options", []) or []

    # Plan state
    pending_plan: dict = initial_state.get("pending_plan", {}) or {}
    planned_steps: list = initial_state.get("planned_steps", []) or []
    plan_confirmed: bool = initial_state.get("plan_confirmed", False)
    current_step_index: int = initial_state.get("current_step_index", 0)

    # Recovery state
    retry_count: int = initial_state.get("retry_count", 0)
    recovery_state: dict = initial_state.get("recovery_state", {}) or {}
    retry_context: dict | None = None

    # Step tracking for _step events (LangGraph parity)
    _shown_steps: set[str] = set()

    def _show_step(label: str, key: str = "") -> None:
        """Yield a step label once (dedup by key)."""
        nonlocal _shown_steps
        k = key or label
        if k not in _shown_steps:
            _shown_steps.add(k)
            # Yielded externally via event loop below
            # We can't yield from a non-async nested function,
            # so the caller stores this and yields after _show_step returns.
            # We use a closure list as a workaround.
            _pending_steps.append(label)

    _pending_steps: list[str] = []

    def _flush_steps() -> None:
        """Generator helper: drain and yield pending steps."""
        # This pattern lets non-async helpers queue step labels.
        pass

    # ── Filter tools by mode & skills ─────────────────────────────
    filtered_tools = get_filtered_tools(tools, active_skills, mode=mode)
    filtered_tool_desc = "\n".join(
        f"- {t.name}: {t.description}" for t in filtered_tools.values()
    ) or tool_descriptions

    # Pre-instantiate plan node (used for "complex" intent)
    from app.agent.nodes.plan import create_plan_node
    _plan_node_fn = await _make_plan_fn(tools, llm_client) if False else None
    # We'll create it lazily when needed to avoid overhead for simple_q turns.

    # ── Phase 0: Context loading (one-time) ───────────────────────
    if not initial_state.get("_context_loaded") and project_id:
        _pending_steps.append("读取项目数据...")
        try:
            from app.agent.context import ContextBuilder
            builder = ContextBuilder(db)
            needs_detail = initial_state.get("current_intent", "simple_q") in {
                "tool_call", "cowriter", "complex", "plan_confirm",
            }
            import uuid as _uuid
            if needs_detail:
                ctx = await builder.build_full(
                    _uuid.UUID(project_id),
                    query_hint=(
                        messages[-1].content[:200]
                        if messages and messages[-1].content
                        else ""
                    ),
                )
            else:
                ctx = await builder.build_summary(
                    _uuid.UUID(project_id),
                    query_hint=(
                        messages[-1].content[:200]
                        if messages and messages[-1].content
                        else ""
                    ),
                    depth="minimal",
                )
            project_context = ctx
        except Exception as e:
            logger.warning("Context load skipped/partial: %s", e)
    else:
        # Already loaded from initial_state
        _pending_steps.append("读取项目数据...")

    # Flush initial step label
    for s in _pending_steps:
        yield {"_step": s}
    _pending_steps.clear()

    # ── Main Loop ──────────────────────────────────────────────────
    intent: str = initial_state.get("current_intent", "simple_q")

    while turn < MAX_TURNS:
        turn += 1
        logger.info(
            "agent_loop turn=%d | mode=%s | intent=%s | pending_plan=%s",
            turn, mode, intent, bool(pending_plan),
        )

        # ── Phase 1: Classify Intent ────────────────────────────
        # Re-classify every turn (unless we're mid-execution)
        if intent not in ("tool_call", "execute_plan", "plan_confirm"):
            intent = await _classify_intent(
                messages=messages,
                mode=mode,
                project_context=project_context,
                cowriter_session=cowriter_session,
                current_options=current_options,
                pending_plan=pending_plan,
                errors=errors,
                llm_client=llm_client,
                tool_descriptions=tool_descriptions or filtered_tool_desc,
                retry_count=retry_count,
                trace_id=trace_id,
            )
            logger.info("agent_loop turn=%d | classified intent=%s", turn, intent)

        # ── Phase 1b: Handle plan confirm/reject ─────────────────
        if intent == "plan_confirm" and pending_plan:
            _pending_steps.append("执行计划...")
            plan_confirmed = True
            if not planned_steps and pending_plan.get("steps"):
                planned_steps = pending_plan["steps"]
            intent = "execute_plan"
        elif intent == "plan_reject":
            pending_plan = {}
            planned_steps = []
            plan_confirmed = False
            current_step_index = 0
            intent = "simple_q"
            # Clear options so stale cards don't persist
            current_options = []
            continue  # Re-classify on next turn

        # ── Phase 2: Plan Generation (complex intent) ────────────
        if intent == "complex":
            _pending_steps.append("制定计划...")
            try:
                plan_node = create_plan_node(tools, llm_client)
                plan_mini: AgentState = {
                    "project_id": project_id,
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "project_context": project_context,
                    "messages": messages,
                    "current_intent": "complex",
                    "tool_calls": [],
                    "tool_results": tool_results,
                    "active_skills": active_skills,
                    "mode": mode,
                    "intermediate_steps": intermediate_steps,
                    "retry_count": retry_count,
                    "max_retries": MAX_RECOVERY,
                    "current_options": current_options,
                    "planned_steps": [],
                    "current_step_index": 0,
                    "errors": errors,
                    "pending_plan": {},
                    "plan_confirmed": False,
                    "retry_context": retry_context,
                    "search_results": [],
                    "cowriter_session": cowriter_session,
                    "_context_loaded": True,
                    "_turn_count": turn,
                    "recovery_state": recovery_state,
                    "_model_override": initial_state.get("_model_override", ""),
                }
                plan_result = await plan_node(plan_mini)

                new_planned = plan_result.get("planned_steps", [])
                new_pending = plan_result.get("pending_plan", {})
                new_confirmed = plan_result.get("plan_confirmed", False)
                new_errors = plan_result.get("errors", [])
                if new_errors:
                    errors = list(new_errors)

                if new_planned:
                    planned_steps = new_planned
                    current_step_index = 0

                if new_pending and not new_confirmed:
                    # Has write tools -> show plan to user
                    pending_plan = new_pending
                    plan_confirmed = False
                    yield {"pending_plan": new_pending}
                    intent = "simple_q"  # Generate response to present plan
                elif new_planned and new_confirmed:
                    # No write tools -> auto-execute
                    pending_plan = {}
                    plan_confirmed = True
                    intent = "execute_plan"
                else:
                    # Plan failed to produce steps
                    intent = "simple_q"
                    if not errors:
                        errors.append("Plan produced no valid steps")

            except Exception as e:
                logger.error("Plan generation failed: %s", e, exc_info=True)
                errors.append(f"Plan generation failed: {e}")
                intent = "simple_q"
                continue

        # Flush accumulated step labels
        for s in _pending_steps:
            yield {"_step": s}
        _pending_steps.clear()

        # ── Phase 3: Execute Tools ───────────────────────────────
        if intent == "execute_plan" and planned_steps:
            # Execute planned steps (with smart batching via _execute_planned_step)
            exec_errors: list[str] = []
            _pending_steps.append("执行分析...")

            while current_step_index < len(planned_steps):
                # Build mini-state for _execute_planned_step
                exec_mini: AgentState = {
                    "project_id": project_id,
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "project_context": project_context,
                    "messages": messages,
                    "current_intent": "execute_plan",
                    "tool_calls": [],
                    "tool_results": tool_results,
                    "active_skills": active_skills,
                    "mode": mode,
                    "intermediate_steps": intermediate_steps,
                    "retry_count": retry_count,
                    "max_retries": MAX_RECOVERY,
                    "current_options": current_options,
                    "planned_steps": planned_steps,
                    "current_step_index": current_step_index,
                    "errors": errors,
                    "pending_plan": pending_plan,
                    "plan_confirmed": plan_confirmed,
                    "retry_context": retry_context,
                    "search_results": [],
                    "cowriter_session": cowriter_session,
                    "_context_loaded": True,
                    "_turn_count": turn,
                    "recovery_state": recovery_state,
                    "_model_override": initial_state.get("_model_override", ""),
                }

                step_result = await _execute_planned_step(exec_mini, filtered_tools, db)

                new_results = step_result.get("tool_results", [])
                new_errors = step_result.get("errors", [])
                new_steps = step_result.get("intermediate_steps", [])
                new_step_idx = step_result.get("current_step_index", current_step_index)
                new_retry = step_result.get("retry_count", retry_count)
                new_pending = step_result.get("pending_plan", pending_plan)
                new_confirmed = step_result.get("plan_confirmed", plan_confirmed)

                # Apply updates
                if new_results:
                    tool_results = new_results
                if new_errors:
                    errors = new_errors
                if new_steps:
                    intermediate_steps = new_steps
                current_step_index = new_step_idx
                retry_count = new_retry
                pending_plan = new_pending
                plan_confirmed = new_confirmed

                # Yield tool results for frontend
                for tr in new_results:
                    yield {"_tool_done": tr}

                # Check if we should stop retrying
                if retry_count >= MAX_RECOVERY and current_step_index < len(planned_steps):
                    # Skip failed step, advance
                    current_step_index += 1
                    retry_count = 0

            # Plan execution complete
            pending_plan = {}
            plan_confirmed = False
            current_step_index = 0
            current_options = []
            intent = "simple_q"
            yield {"_step": "生成回复..."}
            continue  # Go to generate phase

        elif intent == "tool_call":
            _pending_steps.append("执行分析...")
            for s in _pending_steps:
                yield {"_step": s}
            _pending_steps.clear()

            # Check if we can use streaming path
            use_streaming = (
                not planned_steps
                and mode != "chat"
                and hasattr(llm_client, "chat_stream_with_tools")
            )

            if use_streaming:
                # ── Streaming path ────────────────────────────
                stream_mini: AgentState = {
                    "project_id": project_id,
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "project_context": project_context,
                    "messages": messages,
                    "current_intent": "tool_call",
                    "tool_calls": [],
                    "tool_results": tool_results,
                    "active_skills": active_skills,
                    "mode": mode,
                    "intermediate_steps": intermediate_steps,
                    "retry_count": retry_count,
                    "max_retries": MAX_RECOVERY,
                    "current_options": current_options,
                    "planned_steps": planned_steps,
                    "current_step_index": current_step_index,
                    "errors": errors,
                    "pending_plan": pending_plan,
                    "plan_confirmed": plan_confirmed,
                    "retry_context": retry_context,
                    "search_results": [],
                    "cowriter_session": cowriter_session,
                    "_context_loaded": True,
                    "_turn_count": turn,
                    "recovery_state": recovery_state,
                    "_model_override": initial_state.get("_model_override", ""),
                }

                async for chunk in _execute_tool_call_streaming(
                    stream_mini, filtered_tools,
                    filtered_tool_desc or tool_descriptions,
                    llm_client, db,
                ):
                    if chunk.get("_stream_done"):
                        # Extract state updates
                        new_tr = chunk.get("tool_results")
                        if new_tr:
                            tool_results = new_tr
                        new_steps = chunk.get("intermediate_steps")
                        if new_steps:
                            intermediate_steps = new_steps
                        new_retry = chunk.get("retry_count")
                        if new_retry is not None:
                            retry_count = new_retry
                        new_errors = chunk.get("errors")
                        if new_errors:
                            errors = new_errors
                        new_intent = chunk.get("current_intent")
                        if new_intent:
                            intent = new_intent
                    elif "_stream_token" in chunk:
                        yield {"_stream_token": chunk["_stream_token"]}
                    elif "_tool_done" in chunk:
                        yield {"_tool_done": chunk["_tool_done"]}

                # Check for errors
                has_tool_error = any(
                    not r.get("success", True)
                    for r in tool_results[-3:]
                    if r.get("tool") not in ("cowriter_analysis",)
                )
                if has_tool_error and retry_count < MAX_RECOVERY:
                    # Retry next turn
                    retry_count += 1
                    continue
                elif has_tool_error and retry_count >= MAX_RECOVERY:
                    intent = "simple_q"

            else:
                # ── Non-streaming path (chat mode or no streaming support) ───
                from app.agent.nodes.execute_tool import _execute_tool_call

                tool_mini: AgentState = {
                    "project_id": project_id,
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "project_context": project_context,
                    "messages": messages,
                    "current_intent": "tool_call",
                    "tool_calls": [],
                    "tool_results": tool_results,
                    "active_skills": active_skills,
                    "mode": mode,
                    "intermediate_steps": intermediate_steps,
                    "retry_count": retry_count,
                    "max_retries": MAX_RECOVERY,
                    "current_options": current_options,
                    "planned_steps": planned_steps,
                    "current_step_index": current_step_index,
                    "errors": errors,
                    "pending_plan": pending_plan,
                    "plan_confirmed": plan_confirmed,
                    "retry_context": retry_context,
                    "search_results": [],
                    "cowriter_session": cowriter_session,
                    "_context_loaded": True,
                    "_turn_count": turn,
                    "recovery_state": recovery_state,
                    "_model_override": initial_state.get("_model_override", ""),
                }

                tc_result = await _execute_tool_call(
                    tool_mini, filtered_tools, db,
                    tool_descriptions=filtered_tool_desc or tool_descriptions,
                    llm_client=llm_client,
                )

                new_tr = tc_result.get("tool_results")
                if new_tr:
                    tool_results = new_tr
                new_steps = tc_result.get("intermediate_steps")
                if new_steps:
                    intermediate_steps = new_steps
                new_retry = tc_result.get("retry_count")
                if new_retry is not None:
                    retry_count = new_retry
                new_errors = tc_result.get("errors")
                if new_errors:
                    errors = new_errors
                new_intent = tc_result.get("current_intent")
                if new_intent:
                    intent = new_intent

                # Yield tool results for frontend
                visible = [
                    r for r in new_tr
                    if r.get("tool") not in ("cowriter_analysis",)
                ]
                for tr in visible:
                    yield {"_tool_done": tr}

            # After tool execution, generate response
            if intent == "simple_q":
                yield {"_step": "生成回复..."}
                continue  # Go to generate phase

            # Skip to next turn for retries
            if intent == "tool_call" and retry_count < MAX_RECOVERY:
                continue
            else:
                intent = "simple_q"
                yield {"_step": "生成回复..."}
                continue

        # ── Phase 4: Cowriter ────────────────────────────────────
        if intent == "cowriter":
            _pending_steps.append("协作者分析...")
            for s in _pending_steps:
                yield {"_step": s}
            _pending_steps.clear()

            cw_mini: AgentState = {
                "project_id": project_id,
                "user_id": user_id,
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "project_context": project_context,
                "messages": messages,
                "current_intent": "cowriter",
                "tool_calls": [],
                "tool_results": tool_results,
                "active_skills": active_skills,
                "mode": mode,
                "intermediate_steps": intermediate_steps,
                "retry_count": retry_count,
                "max_retries": MAX_RECOVERY,
                "current_options": current_options,
                "planned_steps": planned_steps,
                "current_step_index": current_step_index,
                "errors": errors,
                "pending_plan": pending_plan,
                "plan_confirmed": plan_confirmed,
                "retry_context": retry_context,
                "search_results": [],
                "cowriter_session": cowriter_session,
                "_context_loaded": True,
                "_turn_count": turn,
                "recovery_state": recovery_state,
                "_model_override": initial_state.get("_model_override", ""),
            }

            cw_result = await _execute_cowriter(
                cw_mini, filtered_tools, llm_client,
                filtered_tool_desc or tool_descriptions,
            )

            new_opts = cw_result.get("current_options")
            if new_opts is not None:
                current_options = new_opts
            new_session = cw_result.get("cowriter_session")
            if new_session is not None:
                cowriter_session = new_session
            new_tr = cw_result.get("tool_results")
            if new_tr:
                tool_results = new_tr
            new_steps = cw_result.get("intermediate_steps")
            if new_steps:
                intermediate_steps = new_steps
            new_errors = cw_result.get("errors")
            if new_errors:
                errors = new_errors

            # Yield options for frontend
            if current_options:
                yield {"current_options": current_options}

            # Stream analysis text for the cowriter response
            for tr in tool_results:
                if tr.get("tool") == "cowriter_analysis" and tr.get("success"):
                    analysis = tr.get("data", "") or ""
                    if analysis and not analysis.startswith("{"):
                        # Defensive: if data looks like raw JSON, try extraction
                        try:
                            parsed = json.loads(analysis)
                            if isinstance(parsed, dict):
                                analysis = (
                                    parsed.get("analysis")
                                    or parsed.get("response")
                                    or parsed.get("text")
                                    or analysis
                                )
                        except (json.JSONDecodeError, ValueError):
                            pass
                        yield {"_stream_token": analysis}
                    break

            # After cowriter, generate response or break
            if current_options:
                intent = "simple_q"
                yield {"_step": "生成回复..."}
                continue
            else:
                intent = "simple_q"
                continue

        elif intent == "cowriter_choice":
            _pending_steps.append("执行分析...")
            for s in _pending_steps:
                yield {"_step": s}
            _pending_steps.clear()

            cc_mini: AgentState = {
                "project_id": project_id,
                "user_id": user_id,
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "project_context": project_context,
                "messages": messages,
                "current_intent": "cowriter_choice",
                "tool_calls": [],
                "tool_results": tool_results,
                "active_skills": active_skills,
                "mode": mode,
                "intermediate_steps": intermediate_steps,
                "retry_count": retry_count,
                "max_retries": MAX_RECOVERY,
                "current_options": current_options,
                "planned_steps": planned_steps,
                "current_step_index": current_step_index,
                "errors": errors,
                "pending_plan": pending_plan,
                "plan_confirmed": plan_confirmed,
                "retry_context": retry_context,
                "search_results": [],
                "cowriter_session": cowriter_session,
                "_context_loaded": True,
                "_turn_count": turn,
                "recovery_state": recovery_state,
                "_model_override": initial_state.get("_model_override", ""),
            }

            cc_result = await _execute_cowriter_choice(cc_mini, filtered_tools, db)

            new_opts = cc_result.get("current_options")
            if new_opts is not None:
                current_options = new_opts
            new_session = cc_result.get("cowriter_session")
            if new_session is not None:
                cowriter_session = new_session
            new_tr = cc_result.get("tool_results")
            if new_tr:
                tool_results = new_tr
            new_steps = cc_result.get("intermediate_steps")
            if new_steps:
                intermediate_steps = new_steps
            new_errors = cc_result.get("errors")
            if new_errors:
                errors = new_errors
            new_pending = cc_result.get("pending_plan")
            if new_pending:
                pending_plan = new_pending
            new_intent = cc_result.get("current_intent")
            if new_intent:
                intent = new_intent

            # Handle write-operation plan from cowriter choice
            if pending_plan and intent == "plan_confirm":
                yield {"pending_plan": pending_plan}
                yield {"_step": "生成回复..."}
                continue
            elif intent == "cowriter":
                # Failed choice -> re-route to cowriter for regeneration
                continue
            else:
                # Tool executed successfully, yield results
                visible = [
                    r for r in new_tr
                    if r.get("tool") not in ("cowriter_analysis",)
                ]
                for tr in visible:
                    yield {"_tool_done": tr}
                if current_options:
                    yield {"current_options": current_options}
                intent = "simple_q"
                yield {"_step": "生成回复..."}
                continue

        # ── Phase 5: Generate Response ────────────────────────────
        if intent in ("simple_q",):
            yield {"_step": "生成回复..."}

            # Build system prompt using the existing _build_system_prompt
            # We construct a mini-state for it
            gen_mini: AgentState = {
                "project_id": project_id,
                "user_id": user_id,
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "project_context": project_context,
                "messages": messages,
                "current_intent": intent,
                "tool_calls": [],
                "tool_results": tool_results,
                "active_skills": active_skills,
                "mode": mode,
                "intermediate_steps": intermediate_steps,
                "retry_count": retry_count,
                "max_retries": MAX_RECOVERY,
                "current_options": current_options,
                "planned_steps": planned_steps,
                "current_step_index": current_step_index,
                "errors": errors,
                "pending_plan": pending_plan,
                "plan_confirmed": plan_confirmed,
                "retry_context": retry_context,
                "search_results": [],
                "cowriter_session": cowriter_session,
                "_context_loaded": True,
                "_turn_count": turn,
                "recovery_state": recovery_state,
                "_model_override": initial_state.get("_model_override", ""),
            }

            from app.agent.nodes.generate import _build_system_prompt
            try:
                sys_content = await _build_system_prompt(gen_mini)
            except Exception as e:
                logger.warning("_build_system_prompt failed: %s, using fallback", e)
                sys_content = (
                    "You are StoryCAD AI, a creative writing assistant. "
                    "Respond helpfully in Chinese."
                )

            gen_msgs = [
                Message(role="system", content=sys_content),
                *messages,
            ]

            # Stream response tokens
            try:
                async for token in llm_client.chat_stream_tokens(
                    messages=gen_msgs,
                    temperature=0.7,
                    request_id=trace_id,
                ):
                    yield {"_stream_token": token}
            except Exception as e:
                logger.error("Generate streaming error: %s", e, exc_info=True)
                errors.append(f"Generate error: {e}")
                yield {"_stream_token": f"\n\n[生成回复时出错: {e}]"}

            # Generation is the terminal phase for this turn
            break

        # ── Loop exit conditions ──────────────────────────────────
        if intent in ("simple_q",):
            break

        if turn >= MAX_TURNS:
            logger.warning("agent_loop: max turns reached (%d)", MAX_TURNS)
            yield {"_stream_token": "\n\n[已达到最大轮次限制]"}
            break

    # ── Build final state ───────────────────────────────────────────
    final_state: AgentState = {
        "project_id": project_id,
        "user_id": user_id,
        "trace_id": trace_id,
        "conversation_id": conversation_id,
        "project_context": project_context,
        "messages": messages,
        "current_intent": intent,
        "tool_calls": [],
        "tool_results": tool_results,
        "active_skills": active_skills,
        "mode": mode,
        "intermediate_steps": intermediate_steps,
        "retry_count": retry_count,
        "max_retries": MAX_RECOVERY,
        "current_options": current_options,
        "planned_steps": planned_steps,
        "current_step_index": current_step_index,
        "errors": errors,
        "pending_plan": pending_plan,
        "plan_confirmed": plan_confirmed,
        "retry_context": retry_context,
        "search_results": [],
        "cowriter_session": cowriter_session,
        "_context_loaded": True,
        "_turn_count": turn,
        "recovery_state": recovery_state,
        "_model_override": initial_state.get("_model_override", ""),
    }

    yield {"_loop_done": True, "final_state": final_state}


# Placeholder — plan node is created via create_plan_node
async def _make_plan_fn(tools: dict, llm_client: LLMClient):
    from app.agent.nodes.plan import create_plan_node
    return create_plan_node(tools, llm_client)
