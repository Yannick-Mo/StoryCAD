"""Co-Writer Mode — collaborative writing partner persona."""

from app.llm.types import Message

COWRITER_SYSTEM_PROMPT_TEMPLATE = """你是小说的合著者，而不是代笔人。你的工作是帮助用户**自己写出更好的故事**。

## 核心行为原则

1. **先分析，再建议** — 每次回应用户前，先从角色动机、故事逻辑、情感弧光三个维度分析当前情况。
2. **提供选项，而非答案** — 永远给出 2-3 个合理的选择，每个选项附带利弊分析。
3. **主动提问** — 当用户需求模糊时，反问澄清。不要猜测用户意图。
4. **参考已有设定** — 始终引用角色背景、前文事件、世界观设定来支撑你的分析。
5. **绝不代写** — 在你没有得到用户明确确认前，不要直接写出大段正文。最多给出段落框架或开头句子作为示例。

## 分析框架

每次回应的思维过程必须包含以下三个维度：

- **角色动机**：角色在当前场景下想要什么？他的背景如何影响这个选择？
- **故事逻辑**：每个选项对情节走向、节奏、冲突的影响是什么？
- **情感弧光**：这个选择会如何推动角色的内心成长或变化？

## 输出格式

当 mode 为 "analysis" 时，使用结构化格式：
```
## 分析
（角色动机、故事逻辑、情感弧光的分析）

## 建议选项
1. 选项一 —— 利弊分析
2. 选项二 —— 利弊分析
3. 选项三（可选） —— 利弊分析

## 问题
（如果需求不明确，列出需要用户澄清的问题）
```

当 mode 为 "direct" 时，以自然对话风格输出，但仍遵循核心行为原则。"""


class CoWriterMode:
    """Co-Writer Mode that transforms the LLM into a collaborative writing partner."""

    def build_system_prompt(self, project_context: dict, history: list[Message]) -> str:
        """Build a system prompt that activates the co-writer persona and injects project context."""
        title = project_context.get("project_title", "未命名项目")
        genre = project_context.get("genre", "未指定")
        description = project_context.get("description", "")
        ctx_lines = [f"当前项目：《{title}》", f"类型：{genre}"]
        if description:
            ctx_lines.append(f"简介：{description}")

        summary = self._summarize_history(history)

        parts = [
            COWRITER_SYSTEM_PROMPT_TEMPLATE,
            "",
            "## 项目上下文",
        ]
        parts.extend(ctx_lines)
        if summary:
            parts.append("")
            parts.append("## 对话摘要")
            parts.append(summary)

        return "\n".join(parts)

    def format_response(self, raw_content: str, mode: str = "analysis") -> str:
        """Format the LLM response with structured sections."""
        if mode == "analysis":
            sections = self._ensure_sections(raw_content)
            return sections
        return raw_content

    def _summarize_history(self, history: list[Message]) -> str:
        relevant = [m for m in history if m.role in ("user", "assistant")]
        if not relevant:
            return ""
        recent = relevant[-6:]
        lines = []
        for m in recent:
            prefix = "用户" if m.role == "user" else "AI"
            content = (m.content or "")[:200]
            lines.append(f"[{prefix}] {content}")
        return "\n".join(lines)

    def _ensure_sections(self, content: str) -> str:
        if content.strip().startswith("##"):
            return content
        return f"## 分析\n\n{content}"
