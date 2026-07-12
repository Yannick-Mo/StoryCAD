"""present_options — structured option card tool.

This tool is INTERCEPTED by the interceptor layer. It never actually
runs as a database tool. Instead, when the LLM calls it during streaming,
the interceptor captures the arguments and yields them as frontend
option card events.

This replaces the current JSON-forced CoWriterMode output format.
The LLM can freely choose when to present options vs. discuss, analyze,
or execute tools directly — it's not forced into JSON mode every turn.

Design:
    - The LLM calls present_options(analysis=..., options=[...], session_update=...).
    - The interceptor layer captures this (``_INTERCEPT_TOOLS`` set).
    - The ``analysis`` text is streamed as token events.
    - The ``options`` array is yielded as ``option`` SSE events.
    - The loop pauses for user selection.
    - When the user selects an option, the ``action`` from that option is
      executed as a tool call in the next turn.
"""

from __future__ import annotations

from app.agent.tools.base import BaseTool, ToolMeta, ConcurrencyMode, ToolResult
from app.agent.interceptors import get_option_card_format


class PresentOptionsTool(BaseTool):
    """Present 2-3 structured option cards for user decision.

    This tool is INTERCEPTED — it does not execute as a normal tool.
    The interceptor layer captures its arguments and emits frontend events.
    """

    meta = ToolMeta(
        name="present_options",
        description=(
            "当需要用户做出方向性选择时调用此工具。\n"
            "提供 2-3 个结构化选项卡片，每个包含利弊分析和选定后的执行动作。\n"
            "\n"
            "调用时机：\n"
            "- 你分析了当前情况，发现有多个可行方向\n"
            "- 用户需要决定故事走向、角色发展、结构调整等\n"
            "- 你需要用户确认后才能执行写入操作\n"
            "\n"
            "不要每轮都调用它——只在真正需要用户做选择时才用。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "string",
                    "description": (
                        "对当前情况的分析文本，使用 markdown 排版。\n"
                        "解释你为什么需要用户做选择，以及每个选项的背景。\n"
                        "这部分内容会直接显示给用户。"
                    ),
                },
                "options": {
                    "type": "array",
                    "description": "2-3 个结构化选项卡片",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": get_option_card_format(),
                },
                "session_update": {
                    "type": "object",
                    "description": "（可选）更新协作会话状态",
                    "properties": {
                        "phase": {
                            "type": "string",
                            "enum": ["explore", "plan", "execute", "review", "complete"],
                            "description": "会话阶段",
                        },
                        "goal": {
                            "type": "string",
                            "description": "当前任务的总体目标",
                        },
                        "current_focus": {
                            "type": "string",
                            "description": "当前正在处理的具体焦点",
                        },
                        "is_complete": {
                            "type": "boolean",
                            "description": "设为 true 表示当前任务已完成（用户满意或话题已切换）",
                        },
                    },
                },
            },
            "required": ["analysis", "options"],
        },
        concurrency=ConcurrencyMode.EXCLUSIVE,
        is_destructive=False,
        timeout=30,
        search_hint="present options to user",
    )

    is_write_operation = False  # Not a write — it's a UI interaction

    async def run(self, **kwargs) -> ToolResult:
        """This method is intercepted and never actually called.

        The interceptor layer captures present_options calls before they
        reach this method. If it IS called (e.g., in non-autonomous mode),
        we return the analysis as-is.
        """
        analysis = kwargs.get("analysis", "")
        options = kwargs.get("options", [])
        session_update = kwargs.get("session_update", {})

        return ToolResult(
            success=True,
            data={
                "analysis": analysis,
                "options": options,
                "session_update": session_update,
                "intercepted": True,
            },
            error=None,
        )
