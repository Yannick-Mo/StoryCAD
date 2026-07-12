"""Response builder — system prompt assembly for the final generate phase.

Extracted from ``app/agent/nodes/generate.py`` (now deleted).
Provides token-budget-aware context assembly for the autonomous loop's
final-response step.  Not a LangGraph node — a plain utility.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import aiofiles
import yaml

from app.agent.prompts.builder import get_prompt_builder
from app.config import settings

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

MAX_SYSTEM_TOKENS = 8000
MAX_RAG_CHARS = settings.llm_max_rag_chars or 2000

_PERSONA_CACHE: str | None = None
_PROMPT_DIR = Path(__file__).parent / "prompts"

# Short inline mode declarations (avoid builder dependency during module init)
_MODE_DECLARATION_CHAT = "# ——— 当前模式：对话模式（只读，不可写入）———"
_MODE_DECLARATION_COWRITER = "# ——— 当前模式：协作模式（可读写，提供创作建议）———"


# ── Section model ──────────────────────────────────────────────────────


@dataclass
class _ContextSection:
    tier: int  # 0=critical, 1=high, 2=medium, 3=low
    label: str
    text: str


# ── Static section helpers ─────────────────────────────────────────────


def _get_static_section(name: str) -> str:
    """Return a cached static section from the prompt builder."""
    builder = get_prompt_builder()
    return builder.get_static_section(name)


async def _load_persona() -> str:
    """Lazily load & cache the persona prompt from system.yaml."""
    global _PERSONA_CACHE
    if _PERSONA_CACHE is not None:
        return _PERSONA_CACHE

    persona_path = _PROMPT_DIR / "system.yaml"
    try:
        async with aiofiles.open(persona_path, encoding="utf-8") as f:
            content = await f.read()
        data = await asyncio.to_thread(yaml.safe_load, content)
        _PERSONA_CACHE = (data or {}).get("identity", {}).get("content", "")
        if not _PERSONA_CACHE:
            _PERSONA_CACHE = "You are StoryCAD AI, a creative writing assistant."
    except asyncio.CancelledError:
        raise
    except Exception:
        _PERSONA_CACHE = ""
    return _PERSONA_CACHE


# ── Token estimation ───────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """CJK-aware token estimation.  CJK chars ≈ 1.5 tokens, ASCII ≈ 0.25."""
    cjk = sum(
        1
        for c in text
        if "一" <= c <= "鿿" or "　" <= c <= "〿" or "＀" <= c <= "￯"
    )
    ascii_count = len(text) - cjk
    return int(cjk * 1.5 + ascii_count * 0.25) + 1


# ── Context trimming ───────────────────────────────────────────────────


def trim_context(sections: list[_ContextSection], budget: int = MAX_SYSTEM_TOKENS) -> str:
    """Keep highest-priority content within token budget.

    Tier 0 – always included (truncated proportionally if over budget).
    Tier 1 – always included.
    Tier 2 – included if budget allows, otherwise truncated.
    Tier 3 – only included with ample room.
    """
    sections.sort(key=lambda s: (s.tier, s.label))

    result_parts: list[str] = []
    used = 0

    for sec in sections:
        tokens = estimate_tokens(sec.text)
        if sec.tier <= 1:
            result_parts.append(sec.text)
            used += tokens
        elif sec.tier == 2:
            if used + tokens <= budget:
                result_parts.append(sec.text)
                used += tokens
            else:
                remaining = budget - used
                if remaining > 100:
                    ratio = remaining / max(tokens, 1)
                    trunc_len = int(len(sec.text) * ratio)
                    truncated = sec.text[:trunc_len] + "\n... [截断]"
                    result_parts.append(truncated)
                    used += estimate_tokens(truncated)
        else:
            if used + tokens <= budget * 0.9:
                result_parts.append(sec.text)
                used += tokens

    result = "\n\n".join(result_parts)

    if used > budget:
        logger.warning(
            "system prompt over budget: %d > %d tokens, applying proportional truncation",
            used,
            budget,
        )
        tier0_count = sum(1 for s in sections if s.tier == 0)
        tier0_parts = result_parts[:tier0_count]
        tier0_tokens = sum(estimate_tokens(p) for p in tier0_parts)
        nontier0_parts = result_parts[tier0_count:]
        nontier0_tokens = used - tier0_tokens

        remaining_budget = budget - tier0_tokens
        if remaining_budget < 60:
            result = "\n\n".join(tier0_parts)
            used = tier0_tokens
        else:
            ratio = remaining_budget / max(nontier0_tokens, 1)
            truncated_parts = list(tier0_parts)
            new_used = tier0_tokens
            for part in nontier0_parts:
                trunc_len = int(len(part) * ratio)
                if trunc_len > 60:
                    truncated_parts.append(part[:trunc_len])
                    new_used += estimate_tokens(part[:trunc_len])
            result = "\n\n".join(truncated_parts)
            used = new_used

    return result


# ── Prompt builders ────────────────────────────────────────────────────


async def build_fast_path_prompt(state: dict) -> str:
    """Simplified prompt for general questions without project context."""
    persona = await _load_persona()
    system = f"""{persona}

你正在和一位小说作者聊天。对方问的是一般性写作问题或闲聊，
不需要使用工具或读取项目数据。用简洁、有帮助的方式回答。

# ——— 输出指南 ———
- 使用中文回复
- 段落长度随内容自然变化，不强行限制
- 用空行分隔段落/标题/列表，不要堆在一起
- 使用 markdown 排版，注意：
  · `##` 或 `###` 后必须加空格，前后要空行 → `## 标题`
  · `**加粗**` 标记关键词
  · `-` 列表或 `1.` 列表后必须加空格，前后要空行
  · `> 引用` 后必须加空格，前后要空行
- 如果是写作问题，提供具体可执行的建议，附简短示例
- 如果是闲聊/问候，简短友好回应即可

# ——— 禁止行为 ———
- 不得编造信息——只提供你确实知道的知识
- 不得替用户写创作内容"""
    return system


def _format_tool_data(data) -> str:
    """Format tool result data for display in the system prompt."""
    if not data:
        return "(empty)"
    if isinstance(data, str):
        return data[:200]
    try:
        # Try to extract a readable summary from dict/list results
        if isinstance(data, dict):
            # Prefer content/preview keys
            for key in ("content_preview", "summary", "result", "content"):
                val = data.get(key)
                if val and isinstance(val, str):
                    return str(val)[:200]
            return str(data)[:200]
        if isinstance(data, list):
            return f"[{len(data)} items]"
        return str(data)[:200]
    except Exception:
        return str(data)[:200]


async def build_system_prompt(state: dict) -> str:
    """Build a token-budget-aware system prompt for the final generate step.

    Args:
        state: A flat dict with the same shape as ``LoopState.to_dict()``.
    """
    from app.agent.knowledge import APP_GUIDE

    project_ctx = state.get("project_context", {})

    # Fast path: no project context loaded
    if not project_ctx.get("project"):
        return await build_fast_path_prompt(state)

    proj = project_ctx.get("project", {})
    title = proj.get("title", "Unnamed Project")
    genre = proj.get("genre", "")

    tool_results = state.get("tool_results", [])
    errors = state.get("errors", [])
    pending_plan = state.get("pending_plan", {})
    plan_confirmed = state.get("plan_confirmed", False)
    retry_count = state.get("retry_count", 0)
    mode = state.get("mode", "chat")
    cowriter_active = mode == "cowriter"

    acts = project_ctx.get("acts", [])
    total_ch = sum(len(a.get("chapters", [])) for a in acts) if acts else 0
    project_structure = f"{len(acts)} acts, {total_ch} chapters total" if acts else ""

    rag_text = project_ctx.get("rag_context", "")
    if rag_text:
        rag_text = rag_text[:MAX_RAG_CHARS]

    success_count = sum(1 for r in tool_results if r.get("success"))
    total_count = len(tool_results)

    persona = await _load_persona()
    sections: list[_ContextSection] = []

    # Tier 0 — critical: persona, mode, project identity
    sections.append(_ContextSection(tier=0, label="persona", text=persona))
    mode_decl = _MODE_DECLARATION_COWRITER if cowriter_active else _MODE_DECLARATION_CHAT
    sections.append(_ContextSection(tier=0, label="mode", text=mode_decl))
    project_title = f"你正在协助用户创作小说《{title}》。"
    if genre:
        project_title += f"\n类型：{genre}"
    sections.append(_ContextSection(tier=0, label="project_title", text=project_title))

    # Tier 1 — high: characters, structure, tool results, plan, errors
    chars = project_ctx.get("characters", [])
    if chars:
        char_lines = ["角色列表："]
        for c in chars:
            name = c.get("name", "?")
            role = c.get("role", "")
            personality = c.get("personality", "")
            if personality:
                char_lines.append(f"- {name}（{role}）：{personality[:200]}")
            else:
                char_lines.append(f"- {name}（{role}）")
        sections.append(_ContextSection(tier=1, label="characters", text="\n".join(char_lines)))

    if project_structure:
        sections.append(
            _ContextSection(tier=1, label="project_structure", text=f"项目结构：{project_structure}")
        )

    if tool_results:
        result_lines = [f"工具执行结果（{success_count}/{total_count} 成功）："]
        for r in tool_results[:5]:
            icon = "✓" if r.get("success") else "✗"
            tool_name = r.get("tool", "unknown")
            raw = r.get("data") if r.get("success") else r.get("error", "?")
            content = _format_tool_data(raw)
            result_lines.append(f"{icon} {tool_name}：{content}")
        sections.append(_ContextSection(tier=1, label="tool_results", text="\n".join(result_lines)))

    if errors:
        error_lines = ["遇到的问题："]
        for e in errors[-5:]:
            error_lines.append(f"- {e}")
        sections.append(_ContextSection(tier=1, label="errors", text="\n".join(error_lines)))

    if pending_plan and not plan_confirmed:
        plan_steps = pending_plan.get("steps", [])
        plan_reasoning = pending_plan.get("reasoning", "")
        plan_lines = ["待执行的计划（等待用户确认）："]
        if plan_reasoning:
            plan_lines.append(f"理由：{plan_reasoning}")
        for i, step in enumerate(plan_steps, 1):
            plan_lines.append(f"{i}. {step.get('description') or step.get('tool', '')}")
        plan_lines.append("请询问用户确认是否执行此计划。")
        sections.append(_ContextSection(tier=1, label="pending_plan", text="\n".join(plan_lines)))

    # Cowriter session
    session = state.get("cowriter_session", {})
    if session.get("is_active"):
        phase = session.get("phase", "explore")
        goal = session.get("goal", "")
        decisions = session.get("decisions", [])
        session_lines = [f"协作者当前阶段：{phase}"]
        if goal:
            session_lines.append(f"当前目标：{goal}")
        if decisions:
            session_lines.append(f"已完成 {len(decisions)} 轮决策")
            for d in decisions[-3:]:
                label = d.get("label", "?")
                result = d.get("result", "")
                session_lines.append(f"  - 选择了「{label}」→ {result[:100]}")
        sections.append(_ContextSection(tier=1, label="cowriter_session", text="\n".join(session_lines)))

    if retry_count > 0:
        sections.append(
            _ContextSection(tier=1, label="retry_note", text="注意：上次工具执行出错，请调整后重试。")
        )

    # Tier 3 — low: extra tool results
    if len(tool_results) > 5:
        extra = [
            f"{'✓' if r.get('success') else '✗'} {r.get('tool', '?')}"
            for r in tool_results[5:]
        ]
        sections.append(
            _ContextSection(tier=3, label="extra_tool_results", text="其他工具执行：" + "；".join(extra))
        )

    # Tier 2 — medium: RAG, themes, relations, guidelines
    if rag_text:
        sections.append(_ContextSection(tier=2, label="rag_context", text=f"参考知识：\n{rag_text}"))

    themes = project_ctx.get("themes", [])
    if themes:
        theme_names = [t.get("name", "") for t in themes if t.get("name")]
        if theme_names:
            sections.append(_ContextSection(tier=2, label="themes", text="主题：" + "、".join(theme_names)))

    relations = project_ctx.get("relations", [])
    if relations:
        # Build a character ID → name lookup from the character data
        characters = project_ctx.get("characters", [])
        char_name_by_id: dict[str, str] = {}
        for c in characters:
            cid = c.get("id")
            if cid:
                char_name_by_id[cid] = c.get("name", "?")
        rel_lines = ["角色关系："]
        for r in relations[:10]:
            char_a_id = r.get("character_id", "")
            char_b_id = r.get("target_id", "")
            char_a = char_name_by_id.get(char_a_id, "?")
            char_b = char_name_by_id.get(char_b_id, "?")
            rel_type = r.get("rel_type", "")
            label = r.get("label", "")
            display_type = label or rel_type or "关联"
            trust = r.get("trust", 0)
            threat = r.get("threat", 0)
            attraction = r.get("attraction", 0)
            extra = []
            if trust and trust != 50:
                extra.append(f"信任{trust}")
            if threat and threat != 50:
                extra.append(f"威胁{threat}")
            if attraction and attraction != 50:
                extra.append(f"吸引{attraction}")
            extra_str = f"（{'; '.join(extra)}）" if extra else ""
            rel_lines.append(f"- {char_a} → {char_b}：{display_type}{extra_str}")
        sections.append(_ContextSection(tier=2, label="relations", text="\n".join(rel_lines)))

    sections.append(_ContextSection(tier=2, label="app_guide", text=APP_GUIDE))
    sections.append(
        _ContextSection(tier=2, label="output_guide", text=_get_static_section("output_style"))
    )
    if mode == "chat":
        sections.append(
            _ContextSection(tier=2, label="chat_mode", text=_get_static_section("chat_mode_restrictions"))
        )
    sections.append(_ContextSection(tier=2, label="tool_usage", text=_get_static_section("tool_usage")))
    sections.append(
        _ContextSection(tier=2, label="writing_advice", text=_get_static_section("writing_advice"))
    )
    sections.append(
        _ContextSection(tier=2, label="prohibited", text=_get_static_section("prohibited_behaviors"))
    )
    sections.append(
        _ContextSection(tier=2, label="style_guide", text=_get_static_section("style_guide"))
    )

    return trim_context(sections)
