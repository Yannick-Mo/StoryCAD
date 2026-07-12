"""Autonomous agent loop — model-driven, not code-driven.

A Claude Code-inspired design where the LLM decides: reply, call tools,
ask questions.  Code only handles safety (mode gating, confirmation,
context budget).

Key features:
  - No intent classification — the model sees tools directly and decides.
  - Multi-tool turns: model can chain read → analyze → write in one turn.
  - Streaming tool execution: SAFE tools run as they arrive mid-stream.
  - Interceptor layer: mode gate + confirmation gate.
  - Token-aware context compression.
  - Plan confirm/reject detection at loop entry (no LLM re-generation).
  - Layered error recovery (delegated to recovery.py).
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

MAX_TURNS = 30
MAX_RECOVERY = 3
MAX_RAG_CHARS = 1000
MODEL_CONTEXT_LIMIT = 100_000

# ── Helpers ────────────────────────────────────────────────────────────


def _markdown_to_plain(md: str, max_len: int = 120) -> str:
    """Strip markdown formatting for tool result summaries."""
    md = re.sub(r"#{1,6}\s+", "", md)
    md = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", md)
    md = re.sub(r"`{1,3}[^`]+`{1,3}", "", md)
    md = re.sub(r">\s+", "", md)
    md = re.sub(r"\s+", " ", md).strip()
    return md[:max_len] + ("..." if len(md) > max_len else "")


def _strip_orphan_tool_messages(messages: list[Message]) -> list[Message]:
    """Remove ``tool`` messages whose preceding ``assistant`` lacks ``tool_calls``.

    DeepSeek / OpenAI enforce::

        Messages with role 'tool' must be a response to a preceding
        message with 'tool_calls'.

    When the autonomous loop adds a tool result via a separate turn (plan
    confirm, or the final "no tools" turn), the assistant message may not
    carry ``tool_calls``, which makes the subsequent ``tool`` message
    invalid.  This helper strips those orphaned tool messages so the LLM
    call succeeds.
    """
    cleaned: list[Message] = []
    for m in messages:
        if m.role == "tool":
            # Find the most recent assistant message before this tool
            prev_assistant = None
            for prev in reversed(cleaned):
                if prev.role == "assistant":
                    prev_assistant = prev
                    break
            if prev_assistant is None or not prev_assistant.tool_calls:
                # Orphaned tool message — drop it
                continue
        cleaned.append(m)
    return cleaned


# ── Event constructors ──────────────────────────────────────────────────


def _event_step(label: str) -> dict:
    return {"_step": label}


def _event_token(text: str) -> dict:
    return {"_stream_token": text}


def _event_tool_done(result: dict) -> dict:
    return {"_tool_done": result}


def _event_plan(plan: dict) -> dict:
    return {"pending_plan": plan}


def _event_done(final_state: dict) -> dict:
    return {"_loop_done": True, "final_state": final_state}


# ── Confirm/reject detection ────────────────────────────────────────────

# Keywords that signal the user wants to confirm a pending plan.
_CONFIRM_KEYWORDS: list[str] = [
    "确认", "好的", "可以", "行", "执行", "开始", "ok", "yes",
    "没问题", "就这样", "同意", "接受", "做吧", "干吧",
    "按这个来", "照这个来", "用这个", "直接", "就按",
]
_REJECT_KEYWORDS: list[str] = [
    "拒绝", "取消", "不要", "不行", "算了", "no", "cancel",
    "换个", "换一个", "重新", "再来", "不对", "不好",
    "重来", "再想想", "不",
]


def _detect_plan_decision(user_content: str, pending_plan: dict) -> str:
    """Check if *user_content* confirms or rejects a pending plan.

    Returns ``"confirm"``, ``"reject"``, or ``""`` (no decision detected).
    """
    if not pending_plan or not pending_plan.get("steps"):
        return ""

    content_lower = user_content.strip().lower()

    # Check confirm keywords first (more specific matches)
    for kw in _CONFIRM_KEYWORDS:
        if kw in content_lower:
            return "confirm"

    # Check reject keywords
    for kw in _REJECT_KEYWORDS:
        if kw in content_lower:
            return "reject"

    return ""


# ── System prompt builders ─────────────────────────────────────────────


def _build_chat_system_prompt(sections: list[str]) -> str:
    """System prompt sections from the modular builder (system.yaml)."""
    builder = get_prompt_builder()
    return builder.build(list(sections))


def _build_cowriter_persona() -> str:
    """Return the cowriter persona injected when mode == 'cowriter'.

    No ``present_options`` tool reference — the LLM writes options as
    plain markdown text in its response.  Users reply freely.
    """
    return """# --- 协作模式：合著者身份 ---
你是小说的**合著者**，不是代笔人。你的工作是帮助用户**自己写出更好的故事**。

## 核心行为原则
1. **先分析，再行动** — 在回复之前，从角色动机、故事逻辑、情感弧线三个维度分析当前情况
2. **提供选项，而非答案** — 当存在多个可行方向时，在回复中使用 markdown 列表展示 2-3 个选项及其利弊分析
3. **选项只是参考** — 用户可能接受某个选项、组合多个方案、或完全提出自己的方向。选项是讨论起点，不是限制
4. **主动提问** — 当用户需求模糊时，反问澄清。不要猜测用户意图
5. **引用已有设定** — 始终引用角色背景、前文事件、世界观设定来支撑你的分析

## 会话阶段
- **explore（探索）** — 理解用户需求、分析现状、提供思路方向。此阶段禁止写入。
- **plan（计划）** — 用户选定方向后，规划具体执行步骤
- **execute（执行）** — 正在执行写入/修改操作
- **review（评审）** — 内容已写入，等待用户反馈
- **complete（完成）** — 当前任务已全部完成

## 展示选项的方式
当需要用户做方向选择时，在对话中直接使用 markdown 列出选项：

### 关于角色动机，有三个可能方向

**方案一：复仇驱动** — 角色因过去的创伤而寻求复仇
- 优点：动机强烈，容易引起读者共鸣
- 缺点：可能过于老套，需要独特的转折

**方案二：利益驱动** — 角色为了自身利益而行动
- 优点：现实感强，空间更大
- 缺点：角色容易显得自私

**方案三：扭曲的爱** — 角色出于扭曲的"爱"而行动
- 优点：深度足，人物更立体
- 缺点：写作难度较高

请告诉我你的想法，或选择其中某个方向。

## 选项回应规则
用户可能回应：
- "我选方案二" — 执行方案二
- "把 A 和 B 结合一下" — 讨论怎么融合
- "我想的方向是..." — 尊重用户的创意并分析可行性
- "都不对，换个思路" — 重新分析并提供新的选项

不要把用户的回应当作"不在选项中所以无效"。选项只是建议，最终决定权在用户手里。"""


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

    The LLM decides what to do each turn — reply, call tools, ask for
    direction.  Code only handles safety (mode gating, confirmation,
    context budget).
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

    # ── Attachment injector (for per-turn context sections) ────────
    from app.agent.attachments import AttachmentInjector
    _attach = AttachmentInjector()

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

    # ── Build static system prompt (once, outside loop) ─────────────
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

        # ── Confirm/reject detection (before LLM call) ────────────
        if state.pending_plan and not state.plan_confirmed:
            last_user_msg = ""
            for m in reversed(state.messages):
                if m.role == "user":
                    last_user_msg = m.content or ""
                    break

            decision = _detect_plan_decision(last_user_msg, state.pending_plan)
            if decision == "confirm":
                logger.info("Plan confirmed by user — executing plan steps directly")
                yield _event_step("执行已确认的计划...")

                # Build a synthetic assistant message with tool_calls from
                # the pending_plan so the tool-result messages that follow
                # have a valid preceding tool_calls message (OpenAI API req).
                from app.llm.types import ToolCall
                plan_tool_calls = []
                for step in state.pending_plan.get("steps", []):
                    tc = ToolCall(
                        id=step.get("tool_use_id", f"plan_{step.get('tool', '')}"),
                        function={"name": step.get("tool", ""), "arguments": json.dumps(step.get("params", {}))},
                    )
                    plan_tool_calls.append(tc)

                state = state.replace(
                    messages=state.messages + [
                        Message(role="assistant", content=None, tool_calls=plan_tool_calls)
                    ],
                )

                for step in state.pending_plan.get("steps", []):
                    tool_name = step.get("tool", "")
                    args = step.get("params", {})
                    tool_use_id = step.get("tool_use_id", "")
                    try:
                        result = await StreamingToolExecutor(filtered_tools, db).execute_tool(
                            tool_name, args, tool_use_id,
                        )
                    except Exception as exc:
                        result = {"tool": tool_name, "success": False, "error": str(exc)}
                    yield _event_tool_done(result)

                    # Build tool result message
                    if result.get("success"):
                        data = result.get("data", "")
                        if isinstance(data, (dict, list)):
                            data = json.dumps(data, ensure_ascii=False)
                        content = f"[工具执行结果: {tool_name}]\n{str(data)[:3000]}"
                    else:
                        content = f"[工具执行失败: {tool_name}]\n{result.get('error', 'unknown')[:500]}"

                    new_tr = list(state.tool_results) + [result]
                    state = state.replace(
                        messages=state.messages + [Message(role="tool", content=content, tool_call_id=tool_use_id)],
                        tool_results=new_tr,
                    )

                state = state.replace(
                    pending_plan={},
                    plan_confirmed=True,
                    transition="plan_confirmed_and_executed",
                )
                break  # Skip LLM call, go to final response

            elif decision == "reject":
                logger.info("Plan rejected by user — clearing pending plan")
                state = state.replace(
                    pending_plan={},
                    plan_confirmed=False,
                    transition="plan_rejected",
                )
                yield _event_step("已取消计划...")
                # Fall through to LLM for response about rejection

        # ── Step 1: Context Management ────────────────────────────
        if should_compress(state.messages, MODEL_CONTEXT_LIMIT):
            original_count = len(state.messages)
            state = state.replace(
                messages=compress_history(state.messages, model_limit=MODEL_CONTEXT_LIMIT),
                transition="context_compressed",
            )
            logger.info("Compressed %d → %d messages", original_count, len(state.messages))

        # ── Step 2: Build messages for LLM ─────────────────────────
        # Use AttachmentInjector for per-turn context sections
        dynamic_sections = _attach.build_system_sections(state)

        # Project context
        proj = state.project_context.get("project", {})
        proj_title = proj.get("title", "未命名")
        proj_genre = proj.get("genre", "")
        proj_id = state.project_id or proj.get("id", "unknown")

        # Assemble system message
        system_content = base_system
        if cowriter_persona:
            system_content += "\n\n" + cowriter_persona
        system_content += f"\n\n# --- 当前项目 ---\n项目: {proj_title}"
        if proj_genre:
            system_content += f"\n类型: {proj_genre}"
        system_content += f"\nProject ID: {proj_id}"

        # Inject dynamic sections from AttachmentInjector
        for section_name in ("tool_summary", "session_progress", "plan_reminder", "error_context"):
            text = dynamic_sections.get(section_name)
            if text:
                system_content += "\n\n" + text

        # Tool list
        system_content += f"\n\n# --- 可用工具 ---\n{filtered_tool_desc}"

        # Mode declaration (highest priority — prepend)
        if state.mode == "chat":
            mode_decl = "# ——— 当前模式：对话模式（只读，不可写入）———"
        else:
            mode_decl = "# ——— 当前模式：协作模式（可读写）———"
        system_content = mode_decl + "\n\n" + system_content

        # Build final messages — strip orphaned tool messages that would
        # violate the OpenAI/DeepSeek API requirement (tool must follow
        # an assistant with tool_calls).
        gen_msgs = [Message(role="system", content=system_content)]
        gen_msgs.extend(_strip_orphan_tool_messages(list(state.messages)))

        yield _event_step("思考中...")

        # ── Step 3: LLM streaming + tool execution ─────────────────
        streaming_executor = StreamingToolExecutor(filtered_tools, db)
        tool_blocks: list[tuple[str, dict, str]] = []
        # Preserve the original ToolCall objects so the assistant message
        # carries a valid tool_calls field (required by OpenAI/DeepSeek API).
        tool_call_objects: list = []
        assistant_text_parts: list[str] = []
        tool_use_count = 0

        try:
            async for chunk in llm.chat_stream_with_tools(
                messages=gen_msgs,
                tools=tool_schemas,
                temperature=0.7,
                request_id=state.trace_id,
            ):
                if chunk.content:
                    assistant_text_parts.append(chunk.content)
                    yield _event_token(chunk.content)

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
                        tool_call_objects.append(tc)
                        streaming_executor.add_tool(tc, tool_use_id=tool_use_id)

                for result in streaming_executor.get_completed_results():
                    yield _event_tool_done(result)

                if chunk.finish_reason:
                    logger.debug("Stream finish: %s", chunk.finish_reason)

        except asyncio.CancelledError:
            streaming_executor.discard()
            raise
        except Exception as e:
            logger.error("LLM streaming error: %s", e, exc_info=True)
            streaming_executor.discard()
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
                state = decision.get("state", state)
                state = state.replace(
                    errors=state.errors + [str(e)],
                    transition="error_recovery_retry",
                )
                continue

        # ── Step 4: Await in-flight SAFE tools only ────────────────
        safe_results = await streaming_executor.await_pending_safe()
        queued_excl, queued_barrier = streaming_executor.get_queued_tools()

        new_tool_results = list(state.tool_results)
        safe_result_map: dict[str, dict] = {}
        for r in safe_results:
            if r.get("tool") not in ("cowriter_analysis",):
                new_tool_results.append(r)
                yield _event_tool_done(r)
                safe_result_map[r.get("_tool_use_id", "")] = r
        state = state.replace(tool_results=new_tool_results)

        # ── Step 5: Build assistant message (WITH tool_calls for API spec) ──
        assistant_text = "".join(assistant_text_parts)
        if assistant_text.strip() or tool_call_objects:
            assistant_msg = Message(role="assistant", content=assistant_text or None)
            if tool_call_objects:
                assistant_msg.tool_calls = list(tool_call_objects)
            state = state.replace(
                messages=state.messages + [assistant_msg],
            )

        # ── Step 6: Interceptor Layer (BEFORE EXCL/BARRIER exec) ───
        if tool_blocks:
            intercept: InterceptResult = apply_interceptors(
                tool_blocks,
                mode=state.mode,
                cowriter_session=state.cowriter_session,
                tools_registry=filtered_tools,
            )

            queued_ids: set[str] = {
                tid for _, _, tid in queued_excl + queued_barrier
            }

            # 6a: Mode-gated blocks
            if intercept.blocked:
                streaming_executor.clear_queued()
                for msg in intercept.blocked_messages:
                    state = state.replace(
                        messages=state.messages + [Message(role="system", content=msg)],
                        transition="mode_blocked",
                    )
                yield _event_step("生成回复...")
                break

            # 6b: Confirmation needed
            if intercept.needs_confirmation:
                streaming_executor.clear_queued()
                plan = build_confirmation_plan(intercept.pending_tools, filtered_tools)
                state = state.replace(
                    pending_plan=plan,
                    plan_confirmed=False,
                    transition="plan_generated_for_confirmation",
                )
                yield _event_plan(plan)
                yield _event_step("等待确认...")
                break

            # 6c: Allowed tools — execute queued (non-SAFE) ones
            for tool_name, args, tool_use_id in intercept.allowed_tools:
                if tool_use_id in queued_ids:
                    try:
                        result = await streaming_executor.execute_tool(tool_name, args, tool_use_id)
                    except Exception as tool_err:
                        result = {"tool": tool_name, "success": False, "error": str(tool_err)}
                        logger.error("Tool %s failed: %s", tool_name, tool_err)

                    new_tool_results.append(result)
                    yield _event_tool_done(result)

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
                else:
                    # SAFE tool — build message for LLM next turn
                    existing = safe_result_map.get(tool_use_id)
                    if existing:
                        if existing.get("success"):
                            data = existing.get("data", "")
                            if isinstance(data, (dict, list)):
                                data = json.dumps(data, ensure_ascii=False)
                            content = f"[工具执行结果: {tool_name}]\n{str(data)[:3000]}"
                        else:
                            content = f"[工具执行失败: {tool_name}]\n{existing.get('error', 'unknown')[:500]}"
                        state = state.replace(
                            messages=state.messages + [Message(role="tool", content=content, tool_call_id=tool_use_id)],
                        )

            streaming_executor.clear_queued()

        # ── Step 7: Decide next ─────────────────────────────────────
        if not tool_blocks:
            logger.debug("No tool calls — finishing turn")
            break

        if state.transition in ("mode_blocked", "plan_generated_for_confirmation"):
            break

        # Tools executed — continue for chained operations
        logger.info("Tools executed, continuing loop for chained operations")
        state = state.replace(
            retry_count=0,
            transition="tool_executed_continue",
        )

        if not assistant_text.strip():
            state = state.replace(retry_count=state.retry_count + 1)
            if state.retry_count > 3:
                logger.warning("Tool-only loop detected — breaking")
                yield _event_token("\n\n[连续工具调用已超限，请重新描述你的需求]")
                break

    # ── Final: Generate response ────────────────────────────────────
    yield _event_step("生成回复...")

    last_msg = state.messages[-1] if state.messages else None
    if last_msg and last_msg.role == "assistant":
        pass  # Already have a response
    else:
        from app.agent.response_builder import build_system_prompt

        gen_state = state.to_dict()
        try:
            sys_content = await build_system_prompt(gen_state)
        except Exception as e:
            logger.warning("build_system_prompt failed: %s", e)
            sys_content = (
                "You are StoryCAD AI, a creative writing assistant. "
                "Respond helpfully in Chinese."
            )

        # Strip orphaned tool messages that lack a preceding assistant
        # with tool_calls (DeepSeek/OpenAI API rejects these).
        msgs_for_final = list(state.messages)
        cleaned = _strip_orphan_tool_messages(msgs_for_final)

        gen_msgs_final = [Message(role="system", content=sys_content)]
        gen_msgs_final.extend(cleaned)

        try:
            async for token in llm.chat_stream_tokens(
                messages=gen_msgs_final,
                temperature=0.7,
                request_id=state.trace_id,
            ):
                yield _event_token(token)
        except Exception as e:
            logger.error("Final generate error: %s", e, exc_info=True)
            err_msg = str(e)
            # If we already had assistant text from streaming, don't overwrite
            if not assistant_text_parts:
                yield _event_token(f"\n\n[生成回复时出错: {err_msg[:200]}]")
            else:
                logger.warning("Final gen failed but partial response exists")

    # ── Build final state dict ──────────────────────────────────────
    final_state = state.to_dict()
    yield _event_done(final_state)


# ── Recovery helper ─────────────────────────────────────────────────────


def _try_recovery(state: LoopState, llm: LLMClient, error: str) -> dict:
    """Attempt error recovery. Delegates to ``RecoveryExecutor.apply()``.

    Returns:
        ``{"give_up": False, "state": <updated LoopState>}`` if recovery
        was applied and we should retry.
        ``{"give_up": True, "message": "..."}`` if recovery is exhausted.
    """
    from app.agent.recovery import ErrorClassifier, RecoveryAction, RecoveryExecutor, get_fallback_models

    recovery_history = state.recovery_state.get("recovery_history", [])
    decision = ErrorClassifier.classify(
        error,
        state.retry_count,
        max_retries=MAX_RECOVERY,
        recovery_history=recovery_history,
    )

    logger.info(
        "Recovery: action=%s attempt=%d error=%s",
        decision.action.value, state.retry_count, error[:100],
    )

    if decision.action == RecoveryAction.GIVE_UP:
        return {"give_up": True, "message": decision.message}

    # Delegate to RecoveryExecutor for all non-GIVE_UP actions
    executor = RecoveryExecutor(fallback_models=get_fallback_models())
    state_dict = state.to_dict()
    # apply() is async — but we're in a sync helper called from the
    # exception handler.  We build a sync-compatible result instead.
    # Recovery actions that modify state (non-async parts) are handled
    # inline; the delay is handled at the retry level.

    retry_state = state.replace(
        retry_count=state.retry_count + 1,
    )

    if decision.action == RecoveryAction.RETRY:
        return {"give_up": False, "state": retry_state.replace(transition="recovery_retry")}

    if decision.action == RecoveryAction.RETRY_WITH_ERROR_CONTEXT:
        return {"give_up": False, "state": retry_state.replace(
            errors=state.errors + [f"[SELF-CORRECTION] {error}"],
            transition="recovery_error_context",
        )}

    if decision.action == RecoveryAction.RETRY_WITH_COMPRESSED_CONTEXT:
        from app.agent.context_compressor import compress_history
        compressed = compress_history(state.messages, model_limit=MODEL_CONTEXT_LIMIT)
        return {"give_up": False, "state": retry_state.replace(
            messages=compressed,
            transition="recovery_compressed",
        )}

    if decision.action == RecoveryAction.RETRY_ESCALATED_TOKENS:
        return {"give_up": False, "state": retry_state.replace(
            transition="recovery_escalated",
        )}

    if decision.action == RecoveryAction.SWITCH_MODEL:
        fallbacks = get_fallback_models()
        idx = state.recovery_state.get("model_index", 0)
        if idx < len(fallbacks):
            llm.model = fallbacks[idx]
            return {"give_up": False, "state": retry_state.replace(
                _model_override=fallbacks[idx],
                recovery_state={
                    **state.recovery_state,
                    "model_index": idx + 1,
                    "switched_model": fallbacks[idx],
                },
                transition="recovery_model_switch",
            )}

    return {"give_up": True, "message": decision.message}
