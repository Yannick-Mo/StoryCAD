from __future__ import annotations

import json
import logging
import re

from app.agent.knowledge import APP_GUIDE
from app.agent.prompts.builder import get_prompt_builder

logger = logging.getLogger(__name__)

_COWRITER_SYSTEM_PROMPT = """你是小说的合著者，而不是代笔人。你的工作是帮助用户**自己写出更好的故事**。

## 核心行为原则
1. **先分析，再建议** — 每次回应用户前，先从角色动机、故事逻辑、情感弧光三个维度分析当前情况。
2. **提供选项，而非答案** — 永远给出 2-3 个合理的选择，每个选项附带利弊分析。
3. **主动提问** — 当用户需求模糊时，反问澄清。不要猜测用户意图。
4. **参考已有设定** — 始终引用角色背景、前文事件、世界观设定来支撑你的分析。
5. **可执行** — 每个选项必须附带一个 action，指明用户选择后该执行什么工具和参数。

## 工具参数严格规范（CRITICAL - 最高优先级）
你在 action.params 中使用的参数名**必须与下方工具定义完全一致**，包括字母大小写和下划线位置：
- 不得编造参数名（如果工具定义中参数是 `global_settings`，绝不可写成 `global_setting`、`world_setting`、`background` 等）
- 不得遗漏 required 参数（如果工具要求 `project_id`，action.params 中必须包含它）
- 不得传入工具定义中没有的参数名
- 参数值类型必须匹配：string 类型的参数用字符串，integer 类型的用整数

### 每个工具的具体参数定义（只能使用这些参数名）
{tool_params_detail}

## 项目上下文
当前项目的 project_id 是 `{project_id}`。在 action.params 中填写 project_id 时，必须使用这个确切的 UUID 值。

## 会话阶段管理
你与用户的协作分为多个阶段，每个阶段有明确目标：

- **explore（探索）** — 理解用户需求、分析现状、提供思路方向。**不要执行任何写入工具**。
- **plan（计划）** — 用户选定方向后，规划具体执行步骤。
- **execute（执行）** — 正在执行写入/修改操作。工具执行后等待用户确认效果。
- **review（评审）** — 内容已写入，等待用户反馈。用户可能要求修改或细化。
- **complete（完成）** — 当前任务已全部完成。

阶段转换规则（自动判断）：
- explore → 用户选了方向 → 进入 plan 或 execute
- execute → 工具执行成功 → 进入 review
- review → 用户要求修改 → 回到 execute（同任务细化）
- review → 用户表示满意 → 进入 complete
- 任意阶段 → 用户问题与当前任务完全无关 → 标记 complete（结束旧任务）

## 输出格式
你必须输出 JSON 格式，包含以下字段：
- analysis: 你的分析文本（使用 markdown 排版：标题、列表、加粗强调），注意 markdown 符号后必须加空格（如 `## 标题`）让分析更清晰易读
- options: 选项数组，每个选项包含：
  - id: 唯一标识（option_a, option_b, ...）
  - label: 简短标题
  - description: 详细描述
  - pros: 优势列表
  - cons: 劣势列表
  - action: 用户选择后执行的操作。格式：{{tool: "工具名", params: {{参数字典}}}}
    可用工具及参数请参考当前项目可用的工具列表。
- session_update: 会话状态更新（可选，不填则保持当前状态）：
  - phase: 下一阶段（explore/plan/execute/review/complete）
  - goal: 当前任务的总体目标描述
  - current_focus: 当前正在处理的具体焦点
  - is_complete: true 表示当前任务全部完成（用户满意或话题已切换）

不要包含 markdown 代码块，只输出纯 JSON。"""

_MAX_TOOL_DESC_LINES = 30


def _build_session_context(session: dict) -> str:
    if not session or not session.get("is_active"):
        return ""

    phase = session.get("phase", "explore")
    goal = session.get("goal", "")
    current_focus = session.get("current_focus", "")
    decisions = session.get("decisions", [])

    lines = ["## 当前协作状态", f"阶段：{phase}"]
    if goal:
        lines.append(f"目标：{goal}")
    if current_focus:
        lines.append(f"当前焦点：{current_focus}")

    if decisions:
        lines.append("\n已完成的决策：")
        for d in decisions:
            r = d.get("round", "?")
            label = d.get("label", "?")
            action = d.get("action", "")
            result = d.get("result", "")
            feedback = d.get("user_feedback", "")
            lines.append(f"  第{r}轮：选择了「{label}」→ {action}")
            if result:
                lines.append(f"    结果：{result[:200]}")
            if feedback:
                lines.append(f"    用户反馈：{feedback[:200]}")

    return "\n".join(lines)


class CoWriterMode:
    def __init__(self, tool_descriptions: str = ""):
        self.tool_descriptions = tool_descriptions

    def build_system_prompt(self, project_context: dict, history: list, session: dict | None = None, project_id: str = "") -> str:
        proj = project_context.get("project", {})
        title = proj.get("title", "未命名项目")
        genre = proj.get("genre", "未指定")
        description = proj.get("description", "")

        acts = project_context.get("acts", []) if isinstance(project_context, dict) else []
        chars = project_context.get("characters", []) if isinstance(project_context, dict) else []

        act_count = len(acts)
        chapter_count = sum(len(a.get("chapters", [])) for a in acts)
        scene_count = sum(sum(len(ch.get("scenes", [])) for ch in a.get("chapters", [])) for a in acts)
        char_count = len(chars)

        # ── Use the modular prompt builder for static + dynamic sections ──
        builder = get_prompt_builder()

        # Build the base from cached static sections
        base = builder.build(["identity", "output_style"])

        # Render project context dynamically
        project_section = builder.render_dynamic_section("project_context",
            title=title,
            genre=genre,
            description=description,
            act_count=act_count,
            chapter_count=chapter_count,
            scene_count=scene_count,
            char_count=char_count,
            project_id=project_id or proj.get("id", "unknown"),
        )

        # Build strict tool params detail section
        tool_params_detail = self._build_tool_params_detail()

        # Inject project_id into the cowriter-specific system prompt header
        pid = project_id or proj.get("id", "unknown")
        system_header = _COWRITER_SYSTEM_PROMPT.format(
            tool_params_detail=tool_params_detail,
            project_id=pid,
        )

        # Render session context dynamically via builder (or fall back to
        # the legacy _build_session_context for detailed decision history)
        sess = session or {}
        session_section = ""
        if sess.get("is_active"):
            # Use builder for the structured part
            decisions = sess.get("decisions", [])
            recent_decisions = []
            for d in decisions[-3:]:
                recent_decisions.append({
                    "round": d.get("round", "?"),
                    "label": d.get("label", "?"),
                    "action": d.get("action", ""),
                    "result": d.get("result", ""),
                })

            session_section = builder.render_dynamic_section("session_state",
                phase=sess.get("phase", "explore"),
                goal=sess.get("goal", ""),
                current_focus=sess.get("current_focus", ""),
                decision_count=len(decisions),
                recent_decisions=recent_decisions,
            )

        # Assemble all parts: base identity/style + header-specific + project + session + app guide + tools + data
        parts = [
            base,
            system_header,
            project_section,
        ]

        if session_section:
            parts.append(session_section)

        parts.append("")
        parts.append(APP_GUIDE)

        skills = project_context.get("active_skills", [])
        if skills:
            parts.append(f"已启用技能：{', '.join(skills)}")

        if self.tool_descriptions:
            truncated = self._truncate_tool_descriptions(self.tool_descriptions)
            parts.append(f"\n## 可用工具\n{truncated}")

        if chars:
            parts.append("\n## 角色一览")
            for c in chars[:10]:
                parts.append(f"- {c.get('name')}（{c.get('role','')}）")

        if acts:
            parts.append("\n## 章节结构")
            for a in acts:
                chs = a.get("chapters", [])
                ch_list = ", ".join(f"{ch.get('sort_order',0)}. {ch.get('title','')}" for ch in chs[:5])
                parts.append(f"【{a.get('name','')}】{ch_list}")
                if len(chs) > 5:
                    parts.append(f"  ...还有{len(chs)-5}章")

        return "\n".join(parts)

    @staticmethod
    def _build_tool_params_detail() -> str:
        """Build a strict, precise listing of every tool's parameter names, types, and required status.
        This is embedded in the system prompt so the LLM never hallucinates wrong parameter names."""
        from app.agent.tools import get_tool_registry
        tools = get_tool_registry()
        lines = []
        for name, tool in sorted(tools.items()):
            params = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            if not params:
                lines.append(f"- {name}: 无参数")
                continue
            is_write = " [写入]" if tool.is_write_operation else " [只读]"
            lines.append(f"- {name}{is_write}: {tool.description}")
            for p_name, p_schema in sorted(params.items()):
                req = " (REQUIRED)" if p_name in required else ""
                p_type = p_schema.get("type", "string")
                p_desc = p_schema.get("description", "")
                lines.append(f"    · {p_name} ({p_type}){req}: {p_desc}")
        return "\n".join(lines)

    @staticmethod
    def _truncate_tool_descriptions(desc: str) -> str:
        lines = desc.split("\n")
        if len(lines) <= _MAX_TOOL_DESC_LINES:
            return desc
        return "\n".join(lines[:_MAX_TOOL_DESC_LINES]) + f"\n  ...还有{len(lines) - _MAX_TOOL_DESC_LINES}个工具未列出"

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n```\s*$", "", text)
        return text

    def parse_response(self, raw_content: str) -> dict:
        text = self._strip_code_fence(raw_content.strip())
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("JSON response is not a dict")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("CoWriter JSON parse failed: %s", e)
            return {
                "analysis": text,
                "options": [],
                "parse_error": True,
                "error": str(e),
            }
