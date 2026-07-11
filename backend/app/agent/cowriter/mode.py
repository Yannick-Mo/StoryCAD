"""Co-Writer Mode — collaborative writing partner with structured options + execution."""
from __future__ import annotations

import json
import logging
import re

from app.agent.knowledge import APP_GUIDE

logger = logging.getLogger(__name__)

_COWRITER_SYSTEM_PROMPT = """你是小说的合著者，而不是代笔人。你的工作是帮助用户**自己写出更好的故事**。

## 核心行为原则
1. **先分析，再建议** — 每次回应用户前，先从角色动机、故事逻辑、情感弧光三个维度分析当前情况。
2. **提供选项，而非答案** — 永远给出 2-3 个合理的选择，每个选项附带利弊分析。
3. **主动提问** — 当用户需求模糊时，反问澄清。不要猜测用户意图。
4. **参考已有设定** — 始终引用角色背景、前文事件、世界观设定来支撑你的分析。
5. **可执行** — 每个选项必须附带一个 action，指明用户选择后该执行什么工具和参数。

## 输出格式
你必须输出 JSON 格式，包含以下字段：
- analysis: 你的分析文本（使用 markdown 排版：标题、列表、加粗强调），注意 markdown 符号后必须加空格（如 `## 标题`）让分析更清晰易读
- options: 选项数组，每个选项包含：
  - id: 唯一标识（option_a, option_b, ...）
  - label: 简短标题
  - description: 详细描述
  - pros: 优势列表
  - cons: 劣势列表
  - action: 用户选择后执行的操作。格式：{tool: "工具名", params: {参数字典}}
    可用工具及参数请参考当前项目可用的工具列表。

不要包含 markdown 代码块，只输出纯 JSON。"""

_MAX_TOOL_DESC_LINES = 30


class CoWriterMode:
    def __init__(self, tool_descriptions: str = ""):
        self.tool_descriptions = tool_descriptions

    def build_system_prompt(self, project_context: dict, history: list) -> str:
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

        parts = [
            _COWRITER_SYSTEM_PROMPT,
            "",
            APP_GUIDE,
            "",
            "## 项目概况",
            f"书名：《{title}》 | 类型：{genre}",
            f"结构：{act_count}幕 / {chapter_count}章 / {scene_count}场景 / {char_count}角色",
        ]
        if description:
            parts.append(f"简介：{description}")

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
