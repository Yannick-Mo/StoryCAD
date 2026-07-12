"""Autonomous agent loop — model-driven, not code-driven.

Replaces the fixed-workflow agent_loop with a Claude Code-inspired design
where the LLM decides: reply, call tools, present options, ask questions.

Key differences from the old agent_loop:
  - No classify_intent gate: the model sees tools directly and decides.
  - Multi-tool turns: model can chain read→analyze→write in one turn.
  - Streaming tool execution: SAFE tools run as they arrive mid-stream.
  - Interceptor layer: mode gate, confirmation gate, option gate.
  - Token-aware context compression.
  - Layered error recovery (wired from recovery.py).

Usage::

    async for event in autonomous_loop(initial_state, tools, llm_client, db, td):
        if "_stream_token" in event:
            yield token to frontend
        elif "_tool_done" in event:
            yield tool result card
        elif "_loop_done" in event:
            final_state = event["final_state"]
            break
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context_compressor import (
    compress_history,
    should_compress,
)
from app.agent.interceptors import (
    InterceptResult,
    apply_interceptors,
    build_confirmation_plan,
)
from app.agent.loop_state import LoopState
from app.agent.prompts.builder import get_prompt_builder
from app.agent.tools import get_filtered_tools, get_tool_descriptions
from app.agent.tools.base import BaseTool
from app.agent.tools.streaming_executor import StreamingToolExecutor
from app.llm.client import LLMClient
from app.llm.types import Message

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

MAX_TURNS = 30  # Hard safety cap
MAX_RECOVERY = 3  # Max recovery attempts per error type
MAX_RAG_CHARS = 1000  # RAG context truncation
MODEL_CONTEXT_LIMIT = 100_000  # Conservative estimate for DeepSeek V3

# ── Tool execution helpers ──────────────────────────────────────────────


async def _run_single_tool_wrapper(
    tool_name: str,
    args: dict,
    tools: dict[str, BaseTool],
    db: AsyncSession,
) -> dict:
    """Execute one tool and return a result dict.

    Wraps :func:`_run_single_tool` which returns ``(result_dict, errors_list)``.
    """
    from app.agent.nodes.execute_tool import _run_single_tool

    result, errors = await _run_single_tool(tool_name, args, tools, db)
    return result


def _markdown_to_plain(md: str, max_len: int = 120) -> str:
    """Strip markdown formatting for tool result summaries."""
    # Remove headers, bold, italic, code
    md = re.sub(r"#{1,6}\s+", "", md)
    md = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", md)
    md = re.sub(r"`{1,3}[^`]+`{1,3}", "", md)
    md = re.sub(r">\s+", "", md)
    # Collapse whitespace
    md = re.sub(r"\s+", " ", md).strip()
    return md[:max_len] + ("..." if len(md) > max_len else "")


# ── Event constructors ──────────────────────────────────────────────────


def _event_step(label: str) -> dict:
    return {"_step": label}


def _event_token(text: str) -> dict:
    return {"_stream_token": text}


def _event_tool_done(result: dict) -> dict:
    return {"_tool_done": result}


def _event_options(options: list) -> dict:
    return {"current_options": options}


def _event_plan(plan: dict) -> dict:
    return {"pending_plan": plan}


def _event_done(final_state: dict) -> dict:
    return {"_loop_done": True, "final_state": final_state}


# ── System prompt builders (mode-aware) ─────────────────────────────────


def _build_chat_system_prompt(sections: list[str]) -> str:
    """System prompt sections for chat (read-only) mode."""
    builder = get_prompt_builder()
    return builder.build(list(sections))


def _build_cowriter_persona() -> str:
    """Return the cowriter persona injected when mode == 'cowriter'."""
    return """# --- 协作模式：合著者身份 ---
你是小说的**合著者**，不是代笔人。你的工作是帮助用户**自己写出更好的故事**。

## 核心行为原则
1. **先分析，再行动** — 在回复之前，从角色动机、故事逻辑、情感弧线三个维度分析当前情况
2. **提供选项，而非答案** — 当存在多个可行方向时，调用 `present_options` 工具展示 2-3 个结构化选项卡片
3. **用户不限于选项** — 用户可以选 A、选 B、说"把 A 和 B 结合一下"、或者完全否定并提出自己的方案。选项是沟通起点，不是限制
4. **主动提问** — 当用户需求模糊时，反问澄清。不要猜测用户意图
5. **引用已有设定** — 始终引用角色背景、前文事件、世界观设定来支撑你的分析
6. **可执行** — 选项中应明确用户选择后将执行什么工具和参数

## 会话阶段
- **explore（探索）** — 理解用户需求、分析现状、提供思路方向。此阶段禁止写入。
- **plan（计划）** — 用户选定方向后，规划具体执行步骤
- **execute（执行）** — 正在执行写入/修改操作
- **review（评审）** — 内容已写入，等待用户反馈
- **complete（完成）** — 当前任务已全部完成

## 何时调用 present_options
- 你分析后发现有多条可行路径需要用户决策
- 用户面临方向性选择（"你说得对，但怎么改呢？"）
- 不要每轮都调用 — 讨论和解释时直接回复即可
- 只有当真正需要用户做选择时才使用选项卡片

## 用户回应选项的多种方式
用户看到选项卡片后可能：
1. 点击某个选项 → 你会收到 "[option:X] ..." 格式的消息，执行对应的 action
2. 输入自己的想法 → 你会收到普通文本，像正常对话一样回应（讨论、调整方向、重新分析等）
3. 在选项基础上发挥 → "我选方案B，但是把结尾改成悲剧"
4. 完全否定 → "都不对，我想的是..."

不要把用户的想法当作"不在选项中所以无效"。——选项只是建议，最终决定权在用户手里。"""


def _build_tool_schemas(filtered_tools: dict[str, BaseTool]) -> list:
    """Convert filtered tools to ToolDef list for the LLM client."""
    from app.llm.types import ToolDef
    schemas = []
    for t in filtered_tools.values():
        d = t.to_openai_tool()
        schemas.append(ToolDef(function=d.get("function", {})))
    return schemas


# ── Main Autonomous Loop ────────────────────────────────────────────────


async def autonomous_loop(
    initial_state: dict,
    tools: dict[str, BaseTool],
    llm_client: LLMClient,
    db: AsyncSession,
    tool_descriptions: str,
) -> AsyncGenerator[dict, None]:
    """Model-driven autonomous agent loop.

    The LLM decides what to do each turn — reply, call tools, present
    options — and the loop continues as long as tool calls are produced.
    Code only handles safety (mode gating, confirmation, context budget).
    """

    # ── State initialization ────────────────────────────────────────
    state = LoopState.from_initial(initial_state)
    llm = llm_client

    # ── Filter tools by mode & skills ───────────────────────────────
    filtered_tools = get_filtered_tools(tools, state.active_skills, mode=state.mode)
    filtered_tool_desc = "\n".join(
        f"- {t.name}: {t.description}" for t in filtered_tools.values()
    ) or tool_descriptions
    tool_schemas = _build_tool_schemas(filtered_tools)

    # ── Phase 0: Context loading (one-time) ─────────────────────────
    if not state._context_loaded and state.project_id:
        yield _event_step("加载项目数据...")
        try:
            from app.agent.context import ContextBuilder
            import uuid as _uuid

            builder = ContextBuilder(db)
            query_hint = ""
            if state.messages:
                last = state.messages[-1]
                query_hint = (last.content or "")[:200]

            ctx = await builder.build_summary(
                _uuid.UUID(state.project_id),
                query_hint=query_hint,
                depth="minimal",
            )
            state = state.replace(project_context=ctx, _context_loaded=True,
                                  transition="context_loaded")
        except Exception as e:
            logger.warning("Context load skipped/partial: %s", e)
            state = state.replace(_context_loaded=True, transition="context_load_failed")

    # ── Build system prompt (cached per mode) ───────────────────────
    base_sections = ["identity", "output_style", "tool_usage",
                     "writing_advice", "prohibited_behaviors", "style_guide"]
    if state.mode == "chat":
        base_sections.append("chat_mode_restrictions")

    base_system = _build_chat_system_prompt(base_sections)
    cowriter_persona = _build_cowriter_persona() if state.mode == "cowriter" else ""

    # ── Main Loop ────────────────────────────────────────────────────
    while state.turn_count < MAX_TURNS:
        state = state.replace(turn_count=state.turn_count + 1)
        logger.info(
            "autonomous_loop turn=%d | mode=%s | msgs=%d | transition=%s",
            state.turn_count, state.mode, len(state.messages), state.transition,
        )

        # ── Step 1: Context Management ────────────────────────────
        if should_compress(state.messages, MODEL_CONTEXT_LIMIT):
            original_count = len(state.messages)
            state = state.replace(
                messages=compress_history(state.messages, model_limit=MODEL_CONTEXT_LIMIT),
                transition="context_compressed",
            )
            compressed_count = len(state.messages)
            logger.info("Compressed %d → %d messages", original_count, compressed_count)

        # ── Step 2: Build messages for LLM ─────────────────────────
        # Build project context section
        proj = state.project_context.get("project", {})
        proj_title = proj.get("title", "未命名")
        proj_genre = proj.get("genre", "")
        proj_id = state.project_id or proj.get("id", "unknown")

        # Build tool result summary (last 5)
        tool_summary = ""
        if state.tool_results:
            lines = ["# --- 上一轮工具执行结果 ---"]
            for r in state.tool_results[-5:]:
                status = "OK" if r.get("success") else "FAIL"
                name = r.get("tool", "?")
                detail = ""
                if r.get("success"):
                    data = r.get("data", "")
                    if isinstance(data, str):
                        detail = _markdown_to_plain(data, 150)
                else:
                    detail = (r.get("error", "") or "")[:150]
                lines.append(f"  [{status}] {name}: {detail}")
            tool_summary = "\n".join(lines)

        # Build session progress
        session_text = ""
        session = state.cowriter_session or {}
        if session.get("is_active"):
            phase = session.get("phase", "explore")
            goal = session.get("goal", "")
            focus = session.get("current_focus", "")
            phase_cn = {"explore": "探索", "plan": "计划", "execute": "执行",
                        "review": "评审", "complete": "完成"}.get(phase, phase)
            session_text = f"# --- 协作进度 ---\n阶段: {phase_cn}"
            if goal:
                session_text += f"\n目标: {goal}"
            if focus:
                session_text += f"\n焦点: {focus}"

        # Build pending plan reminder
        plan_text = ""
        if state.pending_plan and not state.plan_confirmed:
            steps = state.pending_plan.get("steps", [])
            if steps:
                plan_text = "# --- 待确认计划 ---\n"
                for i, s in enumerate(steps, 1):
                    plan_text += f"  {i}. {s.get('description', s.get('tool', ''))}\n"
                plan_text += "等待用户确认或拒绝。"

        # Build error context
        error_text = ""
        if state.errors:
            recent = [e for e in state.errors[-3:] if e]
            if recent:
                error_text = "# --- 最近的错误 ---\n" + "\n".join(f"- {e}" for e in recent)

        # Assemble system message
        system_content = base_system
        if cowriter_persona:
            system_content += "\n\n" + cowriter_persona
        system_content += f"\n\n# --- 当前项目 ---\n项目: {proj_title}"
        if proj_genre:
            system_content += f"\n类型: {proj_genre}"
        system_content += f"\nProject ID: {proj_id}"

        # Inject dynamic sections
        for section in [tool_summary, session_text, plan_text, error_text]:
            if section:
                system_content += "\n\n" + section

        # Tool list
        system_content += f"\n\n# --- 可用工具 ---\n{filtered_tool_desc}"

        # Mode declaration (highest priority — prepend)
        if state.mode == "chat":
            mode_decl = "# ——— 当前模式：对话模式（只读，不可写入）———"
        else:
            mode_decl = "# ——— 当前模式：协作模式（可读写）———"
        system_content = mode_decl + "\n\n" + system_content

        # Build final messages
        gen_msgs = [Message(role="system", content=system_content)]
        gen_msgs.extend(state.messages)

        yield _event_step("思考中...")

        # ── Step 3: LLM streaming + tool execution ─────────────────
        streaming_executor = StreamingToolExecutor(filtered_tools, db)
        tool_blocks: list[tuple[str, dict, str]] = []  # [(name, args, id), ...]
        assistant_text_parts: list[str] = []
        tool_use_count = 0

        try:
            async for chunk in llm.chat_stream_with_tools(
                messages=gen_msgs,
                tools=tool_schemas,
                temperature=0.7,
                request_id=state.trace_id,
            ):
                # Text token
                if chunk.content:
                    assistant_text_parts.append(chunk.content)
                    yield _event_token(chunk.content)

                # Tool call (complete block or incremental)
                if chunk.tool_call:
                    tc = chunk.tool_call
                    fn = tc.function if hasattr(tc, "function") else {}
                    name = fn.get("name", "") if isinstance(fn, dict) else getattr(fn, "name", "")
                    args_raw = fn.get("arguments", "{}") if isinstance(fn, dict) else getattr(fn, "arguments", "{}")

                    if isinstance(args_raw, str):
                        try:
                            args = json.loads(args_raw)
                        except json.JSONDecodeError:
                            args = {}
                    elif isinstance(args_raw, dict):
                        args = args_raw
                    else:
                        args = {}

                    if name and name.strip():
                        tool_use_count += 1
                        tool_use_id = getattr(tc, "id", f"call_{tool_use_count}")
                        tool_blocks.append((name.strip(), args, tool_use_id))
                        streaming_executor.add_tool(
                            tc,
                            tool_use_id=tool_use_id,
                            mode=state.mode,
                            read_only_tool_names={
                                t.name for t in filtered_tools.values()
                                if not t.is_write_operation
                            },
                        )

                # Yield completed results during streaming
                for result in streaming_executor.get_completed_results():
                    yield _event_tool_done(result)

                # Finish reason
                if chunk.finish_reason:
                    logger.debug("Stream finish: %s", chunk.finish_reason)

        except asyncio.CancelledError:
            streaming_executor.discard()
            raise
        except Exception as e:
            logger.error("LLM streaming error: %s", e, exc_info=True)
            streaming_executor.discard()
            # Try recovery
            decision = _try_recovery(state, llm, str(e))
            if decision.get("give_up"):
                assistant_text = "".join(assistant_text_parts)
                if assistant_text:
                    state = state.replace(
                        messages=state.messages + [Message(role="assistant", content=assistant_text)],
                        transition="error_give_up",
                    )
                yield _event_token(f"\n\n[发生错误: {decision.get('message', str(e))}]")
                break
            else:
                # Recovery action applied — get updated state and retry
                state = decision.get("state", state)
                state = state.replace(
                    errors=state.errors + [str(e)],
                    transition="error_recovery_retry",
                )
                continue

        # ── Step 4: Await remaining tools ────────────────────────────
        all_results = await streaming_executor.get_remaining_results()
        for result in all_results:
            if result.get("tool") not in ("cowriter_analysis",):
                yield _event_tool_done(result)

        # Update tool results
        new_tool_results = list(state.tool_results)
        for r in all_results:
            if r.get("tool") not in ("cowriter_analysis",):
                new_tool_results.append(r)
        state = state.replace(tool_results=new_tool_results)

        # ── Step 5: Build assistant message ──────────────────────────
        assistant_text = "".join(assistant_text_parts)
        if assistant_text.strip():
            state = state.replace(
                messages=state.messages + [Message(role="assistant", content=assistant_text)],
            )

        # ── Step 6: Interceptor Layer ────────────────────────────────
        if tool_blocks:
            intercept: InterceptResult = apply_interceptors(
                tool_blocks,
                mode=state.mode,
                cowriter_session=state.cowriter_session,
                tools_registry=filtered_tools,
            )

            # 6a: Mode-gated blocks
            if intercept.blocked:
                for msg in intercept.blocked_messages:
                    state = state.replace(
                        messages=state.messages + [Message(role="system", content=msg)],
                        transition="mode_blocked",
                    )
                # Generate response explaining the block
                yield _event_step("生成回复...")
                break  # Exit tool loop, generate final response

            # 6b: Confirmation needed
            if intercept.needs_confirmation:
                plan = build_confirmation_plan(intercept.pending_tools, filtered_tools)
                state = state.replace(
                    pending_plan=plan,
                    plan_confirmed=False,
                    transition="plan_generated_for_confirmation",
                )
                yield _event_plan(plan)
                yield _event_step("等待确认...")
                break  # Pause for user confirmation

            # 6c: Options presented
            if intercept.has_options:
                if intercept.analysis_text:
                    pass  # Already streamed above
                if intercept.options:
                    state = state.replace(
                        current_options=intercept.options,
                        transition="options_presented",
                    )
                    if intercept.session_update:
                        su = intercept.session_update
                        new_session = dict(state.cowriter_session)
                        new_session["is_active"] = True
                        if "phase" in su:
                            new_session["phase"] = su["phase"]
                        if "goal" in su:
                            new_session["goal"] = su["goal"]
                        if "current_focus" in su:
                            new_session["current_focus"] = su["current_focus"]
                        if su.get("is_complete"):
                            new_session["is_active"] = False
                        state = state.replace(cowriter_session=new_session)
                    yield _event_options(intercept.options)
                    yield _event_step("等待选择...")
                    break  # Pause for user decision

            # 6d: Allowed tools — execute them
            for tool_name, args, tool_use_id in intercept.allowed_tools:
                try:
                    result = await _run_single_tool_wrapper(tool_name, args, filtered_tools, db)
                    new_tool_results.append(result)
                    yield _event_tool_done(result)

                    # Build tool result message
                    if result.get("success"):
                        data = result.get("data", "")
                        if isinstance(data, (dict, list)):
                            data = json.dumps(data, ensure_ascii=False)
                        content = f"[工具执行结果: {tool_name}]\n{str(data)[:3000]}"
                    else:
                        content = f"[工具执行失败: {tool_name}]\n{result.get('error', 'unknown')[:500]}"

                    state = state.replace(
                        messages=state.messages + [Message(role="tool", content=content, tool_call_id=tool_use_id)],
                        tool_results=new_tool_results,
                    )
                except Exception as tool_err:
                    logger.error("Tool %s failed: %s", tool_name, tool_err)
                    state = state.replace(
                        errors=state.errors + [f"Tool {tool_name}: {tool_err}"],
                    )

        # ── Step 7: Decide next ───────────────────────────────────────
        if not tool_blocks:
            # Model only produced text — done
            logger.debug("No tool calls — finishing turn")
            break

        if state.transition in ("mode_blocked", "plan_generated_for_confirmation",
                                "options_presented"):
            # Interceptor paused the loop — break to generate final response
            break

        # Tools were executed successfully — continue for another round
        # (the model may want to chain more tool calls based on results)
        logger.info("Tools executed, continuing loop for chained operations")
        state = state.replace(
            retry_count=0,  # Reset retries for new round
            transition="tool_executed_continue",
        )

        # If the model only called tools and produced no text, retry count
        # helps avoid infinite loops where tools silently fail
        if not assistant_text.strip():
            state = state.replace(retry_count=state.retry_count + 1)
            if state.retry_count > 3:
                logger.warning("Tool-only loop detected — breaking")
                yield _event_token("\n\n[连续工具调用已超限，请重新描述你的需求]")
                break

    # ── Final: Generate response ────────────────────────────────────────
    yield _event_step("生成回复...")

    # Check if we already have an assistant message
    last_msg = state.messages[-1] if state.messages else None
    if last_msg and last_msg.role == "assistant":
        # Already have a response — just emit what we have
        pass
    else:
        # Build final response using the generate node's prompt builder
        from app.agent.nodes.generate import _build_system_prompt

        gen_state = state.to_dict()
        try:
            sys_content = await _build_system_prompt(gen_state)
        except Exception as e:
            logger.warning("_build_system_prompt failed: %s", e)
            sys_content = (
                "You are StoryCAD AI, a creative writing assistant. "
                "Respond helpfully in Chinese."
            )

        gen_msgs_final = [Message(role="system", content=sys_content)]
        gen_msgs_final.extend(state.messages)

        try:
            async for token in llm.chat_stream_tokens(
                messages=gen_msgs_final,
                temperature=0.7,
                request_id=state.trace_id,
            ):
                yield _event_token(token)
        except Exception as e:
            logger.error("Final generate error: %s", e, exc_info=True)
            yield _event_token(f"\n\n[生成回复时出错: {e}]")

    # ── Build final state dict ──────────────────────────────────────────
    final_state = state.to_dict()
    yield _event_done(final_state)


# ── Recovery helper ─────────────────────────────────────────────────────


def _try_recovery(state: LoopState, llm: LLMClient, error: str) -> dict:
    """Attempt error recovery. Returns a dict with recovery action applied.

    Returns:
        {"give_up": False} if recovery was applied and we should retry.
        {"give_up": True, "message": "..."} if recovery is exhausted.
    """
    from app.agent.recovery import ErrorClassifier, RecoveryAction

    recovery_history = state.recovery_state.get("recovery_history", [])
    decision = ErrorClassifier.classify(
        error,
        state.retry_count,
        max_retries=MAX_RECOVERY,
        recovery_history=recovery_history,
    )

    logger.info("Recovery: action=%s attempt=%d error=%s",
                decision.action.value, state.retry_count, error[:100])

    if decision.action == RecoveryAction.RETRY:
        state = state.replace(retry_count=state.retry_count + 1, transition="recovery_retry")
        return {"give_up": False, "state": state}

    if decision.action == RecoveryAction.RETRY_WITH_ERROR_CONTEXT:
        state = state.replace(
            errors=state.errors + [f"[SELF-CORRECTION] {error}"],
            retry_count=state.retry_count + 1,
            transition="recovery_error_context",
        )
        return {"give_up": False, "state": state}

    if decision.action == RecoveryAction.RETRY_WITH_COMPRESSED_CONTEXT:
        from app.agent.recovery import RecoveryExecutor
        compressed = RecoveryExecutor._compress_messages(state.messages)
        state = state.replace(
            messages=compressed,
            retry_count=state.retry_count + 1,
            transition="recovery_compressed",
        )
        return {"give_up": False, "state": state}

    if decision.action == RecoveryAction.RETRY_ESCALATED_TOKENS:
        state = state.replace(
            retry_count=state.retry_count + 1,
            transition="recovery_escalated",
        )
        return {"give_up": False, "state": state}

    if decision.action == RecoveryAction.SWITCH_MODEL:
        from app.agent.recovery import get_fallback_models
        fallbacks = get_fallback_models()
        idx = state.recovery_state.get("model_index", 0)
        if idx < len(fallbacks):
            llm.model = fallbacks[idx]
            state = state.replace(
                _model_override=fallbacks[idx],
                recovery_state={
                    **state.recovery_state,
                    "model_index": idx + 1,
                    "switched_model": fallbacks[idx],
                },
                transition="recovery_model_switch",
            )
            return {"give_up": False, "state": state}

    # Default: give up
    return {"give_up": True, "message": decision.message}
