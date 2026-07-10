from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

import aiofiles
import yaml

from app.agent.cowriter.mode import CoWriterMode
from app.agent.guard import check_output_safety
from app.agent.prompts import render_prompt
from app.agent.state import AgentState
from app.config import settings
from app.llm.client import LLMClient
from app.llm.types import Message

logger = logging.getLogger(__name__)

# Configuration — can be overridden via env in production
MAX_SYS_CHARS = settings.llm_max_sys_chars
MAX_RAG_CHARS = settings.llm_max_rag_chars
_MAX_NON_PRIORITY_PARTS = 5

_PERSONA_CACHE: str | None = None
_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# ── Self-reflection prompts ──────────────────────────────────────────
_EVALUATION_SYSTEM_PROMPT = """你是一个AI回复质量评估员。评估小说写作助手的回复质量。

评估标准（只输出JSON）：
1. quality_score: 整数1-5
   - 5 = 建议具体可执行，包含改写前后对比，引用项目实际内容
   - 4 = 有用建议但缺少具体示例
   - 3 = 一般性建议，缺乏可操作性
   - 2 = 过于笼统，没有帮助
   - 1 = 明显有问题（幻觉、矛盾）
2. should_improve: true/false —— 仅当quality_score >= 4 时为false
3. issues: 问题列表（最多3条，空列表代表没问题）
4. feedback: 改进方向（如果should_improve为true）

高质量回复特征：
- 建议具体："第3段第2句的对话太直白" 而非 "对话可以更好"
- 包含改写前后对比
- 引用项目实际内容
- 分析原因而非指出表面问题
- 使用结构化排版（列表、加粗）

低质量回复特征：
- "这段可以写得更好" 类的空话
- 没有具体例子
- 没有引用项目实际内容（但如果工具未返回相关内容，不扣分）

输出 ONLY JSON，不要任何其他文本：{"quality_score": int, "should_improve": bool, "issues": list, "feedback": ""}"""


def _summarize_tool_results(results: list[dict]) -> str:
    """Summarize tool results briefly for the evaluation prompt."""
    lines = []
    for r in results:
        tool = r.get("tool", "unknown")
        ok = r.get("success", False)
        if ok:
            data = r.get("data", "")
            if isinstance(data, str):
                data = data[:200]
            lines.append(f"[{tool}] OK: {data}")
        else:
            lines.append(f"[{tool}] FAIL: {r.get('error', '?')}")
    return "\n".join(lines[:5])


_PERSONA_LOCK = asyncio.Lock()

async def _load_persona() -> str:
    global _PERSONA_CACHE
    if _PERSONA_CACHE is not None:
        return _PERSONA_CACHE
    async with _PERSONA_LOCK:
        if _PERSONA_CACHE is not None:
            return _PERSONA_CACHE
        path = _PROMPT_DIR / "persona.yaml"
        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                content = await f.read()
            data = await asyncio.to_thread(yaml.safe_load, content)
            _PERSONA_CACHE = (data or {}).get("system", "")
        except asyncio.CancelledError:
            raise
        except Exception:
            _PERSONA_CACHE = ""
        return _PERSONA_CACHE


def _trim_context(sys_parts: list[str]) -> str:
    combined = "\n".join(sys_parts)
    if len(combined) <= MAX_SYS_CHARS:
        return combined

    priority_keys = {
        "pending_plan", "current_options", "errors",
        "tool_results", "project", "characters", "themes", "skills",
        "rag_context",
    }
    priority_texts: list[str] = []
    non_priority: list[tuple[int, str]] = []

    for idx, part in enumerate(sys_parts):
        # Extract the key prefix before ":" if present
        part_key = part.split(":")[0].split("=")[0].split("{")[0].strip().lower()
        part_key = part_key.lstrip('"').lstrip("'")
        is_priority = part_key in priority_keys
        if is_priority and len(part) < MAX_SYS_CHARS // 2:
            priority_texts.append(part)
        elif not is_priority:
            non_priority.append((idx, part))

    kept = list(priority_texts)
    total = sum(len(p) + 1 for p in kept)

    # Add non-priority parts in order until we hit the limit
    for _, part in non_priority:
        needed = len(part) + 1
        if total + needed > MAX_SYS_CHARS:
            continue
        total += needed
        kept.append(part)

    # If still over limit (edge case: priority parts alone exceed limit), log warning and truncate
    result = "\n".join(kept)
    if len(result) > MAX_SYS_CHARS:
        logger.warning(
            "System prompt still exceeds MAX_SYS_CHARS (%d > %d) after trimming",
            len(result), MAX_SYS_CHARS,
        )
        result = result[:MAX_SYS_CHARS]

    return result


async def _build_fast_path_prompt(state: AgentState) -> str:
    """Simplified prompt for general questions that don't need project context."""
    persona = await _load_persona()
    system = f"""{persona}

你正在和一位小说作者聊天。对方问的是一般性写作问题或闲聊，
不需要使用工具或读取项目数据。用简洁、有帮助的方式回答。

# ——— 输出指南 ———
- 使用中文回复
- 简洁直接，每段不超过3句话
- 使用 markdown 结构化排版（列表、加粗），保持可读性
- 如果是写作问题，提供具体可执行的建议，附简短示例
- 如果是闲聊/问候，简短友好回应即可

# ——— 禁止行为 ———
- 不得编造信息——只提供你确实知道的知识
- 不得替用户写创作内容"""
    return system


async def _build_system_prompt(state: AgentState) -> str:
    project_ctx = state.get("project_context", {})

    # Fast path: no project context loaded, use simplified prompt
    if not project_ctx.get("project"):
        return await _build_fast_path_prompt(state)

    proj = project_ctx.get("project", {})
    title = proj.get("title", "Unnamed Project")

    tool_results = state.get("tool_results", [])
    errors = state.get("errors", [])
    pending_plan = state.get("pending_plan", [])
    plan_confirmed = state.get("plan_confirmed", False)
    current_options = state.get("current_options", [])
    retry_count = state.get("retry_count", 0)
    mode = state.get("mode", "chat")
    cowriter_active = state.get("mode") == "cowriter"

    acts = project_ctx.get("acts", [])
    total_ch = sum(len(a.get("chapters", [])) for a in acts) if acts else 0
    project_structure = f"{len(acts)} acts, {total_ch} chapters total" if acts else ""

    rag_text = project_ctx.get("rag_context", "")
    if rag_text:
        rag_text = rag_text[:MAX_RAG_CHARS]

    success_count = sum(1 for r in tool_results if r.get("success"))
    total_count = len(tool_results)

    cowriter_prompt = ""
    if cowriter_active:
        cw = CoWriterMode()
        cowriter_prompt = cw.build_system_prompt(project_ctx, list(state["messages"]))

    kwargs = {
        "persona": await _load_persona(),
        "project_title": title,
        "project_structure": project_structure,
        "rag_context": rag_text,
        "tool_results": tool_results,
        "success_count": success_count,
        "total_count": total_count,
        "errors": errors[-5:],
        "pending_plan": pending_plan,
        "plan_confirmed": plan_confirmed,
        "current_options": current_options,
        "mode": mode,
        "cowriter_prompt": cowriter_prompt,
        "retry_count": retry_count,
    }

    sys_content = render_prompt("generate", **kwargs)
    if not sys_content:
        sys_content = (
            f"You are an experienced Chinese novel editor and writing coach. "
            f"The user is working on '{title}'."
        )
    return sys_content


def _apply_output_safety(content: str) -> str:
    """Apply output safety checks and return safe content."""
    guard_error = check_output_safety(content)
    if guard_error:
        logger.warning("Output guardrail triggered: %s", guard_error)
        return (
            "I'm sorry, but I cannot provide that response. "
            "Please rephrase your request."
        )
    return content


def create_generate_node(llm_client: LLMClient):
    async def generate_node(state: AgentState):
        msgs = list(state["messages"])

        user_msgs = [m for m in msgs if m.role == "user"]
        if not user_msgs:
            fallback = "No user message found."
            msgs.append(Message(role="assistant", content=fallback))
            yield {"messages": msgs}
            return

        # ── Determine whether self-reflection should apply ──────────────
        # Only reflect when tools have been executed (writing advice / analysis),
        # not for simple chat, cowriter modes, or plan confirmations.
        tool_results: list[dict] = state.get("tool_results", [])
        should_reflect = (
            len(tool_results) > 0
            and any(r.get("success", True) for r in tool_results)
            and state.get("mode", "chat") != "cowriter"
            and not state.get("pending_plan")
        )

        full_content = ""

        if should_reflect:
            #
            # ── Reflective path: draft → evaluate → (improve) → stream ──
            #
            yield {"_stream_token": "⏳ 构思回复..."}
            sys_content = await _build_system_prompt(state)
            msgs_with_sys = [Message(role="system", content=sys_content)] + msgs

            draft: str = ""
            try:
                # Phase 1 — first draft (non-streaming, collect full output)
                draft_result = await llm_client.chat(
                    messages=msgs_with_sys, temperature=0.7,
                    request_id=state.get("trace_id", ""),
                )
                draft = draft_result.content or ""
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("First-pass generate failed, falling back to streaming: %s", e)
                should_reflect = False

            if should_reflect:
                yield {"_stream_token": "⏳ 自我评估..."}

                # Phase 2 — self-evaluation
                evaluation: dict = {}
                try:
                    last_user_msg = user_msgs[-1].content or ""
                    eval_msgs = [
                        Message(role="system", content=_EVALUATION_SYSTEM_PROMPT),
                        Message(
                            role="user",
                            content=(
                                f"用户问题：{last_user_msg}\n\n"
                                f"AI回复：{draft}\n\n"
                                f"工具结果摘要：\n{_summarize_tool_results(tool_results)}"
                            ),
                        ),
                    ]
                    eval_result = await llm_client.chat(
                        messages=eval_msgs,
                        temperature=0.1,
                        response_format="json_object",
                        request_id=state.get("trace_id", ""),
                    )
                    evaluation = json.loads(eval_result.content or "{}")
                    if not isinstance(evaluation, dict):
                        evaluation = {}
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("Self-evaluation failed, using first draft: %s", e)
                    evaluation = {}

                should_improve = evaluation.get("should_improve", False)
                quality_score = evaluation.get("quality_score", 0)

                if should_improve and quality_score < 4:
                    yield {"_stream_token": "⏳ 优化回复..."}
                    # Phase 3 — generate improved version
                    try:
                        feedback = evaluation.get("feedback", "")
                        logger.info(
                            "Self-reflection improving response (score: %s/5, issues: %s)",
                            quality_score,
                            evaluation.get("issues", []),
                        )
                        improved_msgs = list(msgs_with_sys)
                        improved_msgs.append(
                            Message(
                                role="user",
                                content=(
                                    f"[系统内部自检] 你刚才的回复质量评分{quality_score}/5。"
                                    f"需要改进的方向：{feedback}\n"
                                    f"请重新回复。注：这是自我修正，非用户新问题，不要提及修正过程。"
                                ),
                            ),
                        )
                        improved_result = await llm_client.chat(
                            messages=improved_msgs,
                            temperature=0.7,
                            request_id=state.get("trace_id", ""),
                        )
                        full_content = improved_result.content or draft
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning("Improved generation failed, using draft: %s", e)
                        full_content = draft
                else:
                    full_content = draft

        # ── Cowriter fast path: use analysis text directly, skip LLM call ──
        if not full_content and state.get("mode") == "cowriter":
            for tr in tool_results:
                if tr.get("tool") == "cowriter_analysis" and tr.get("data"):
                    full_content = tr["data"]
                    chunks = re.split(r'(?<=[。！？.!?\n])', full_content)
                    for chunk in chunks:
                        trimmed = chunk.strip()
                        if trimmed:
                            yield {"_stream_token": trimmed}
                    break

        # ── Normal streaming path (no self-reflection, no cowriter shortcut) ──
        if not full_content:
            sys_content = await _build_system_prompt(state)
            msgs_with_sys = [Message(role="system", content=sys_content)] + msgs
            try:
                async for token in llm_client.chat_stream_tokens(
                    messages=msgs_with_sys,
                    request_id=state.get("trace_id", ""),
                ):
                    full_content += token
                    yield {"_stream_token": token}
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Generate streaming failed: %s", e)
                fallback = (
                    "I encountered an error while generating a response. "
                    "Please try rephrasing your request."
                )
                msgs.append(Message(role="assistant", content=fallback))
                yield {
                    "messages": msgs,
                    "errors": state.get("errors", []) + [f"Generate failed: {e}"],
                    "_stream_done": True,
                }
                return

        #
        # ── Finalize: safety check, persist, yield done ──
        #
        full_content = _apply_output_safety(full_content)

        if should_reflect and full_content:
            # Stream the already-generated reflected response in chunks
            # for progressive UI display.
            chunks = re.split(r'(?<=[。！？.!?\n])', full_content)
            for chunk in chunks:
                trimmed = chunk.strip()
                if trimmed:
                    yield {"_stream_token": trimmed}

        assistant_msg = Message(role="assistant", content=full_content)
        msgs.append(assistant_msg)
        yield {"messages": msgs, "_stream_done": True}

    return generate_node