"""present_options — structured option card tool.

This tool is INTERCEPTED by the interceptor layer. It never actually
runs as a database tool. Instead, when the LLM calls it during streaming,
the interceptor captures the arguments and yields them as frontend
option card events.

Design:
    - The LLM calls present_options(analysis=..., options=[...], session_update=...).
    - The interceptor layer captures this (``_INTERCEPT_TOOLS`` set).
    - The ``analysis`` text is streamed as token events.
    - The ``options`` array is yielded as ``option`` SSE events.
    - The loop pauses for user selection. Users can:
      1. Click an option card → the action from that option executes.
      2. Type free-form feedback → their own text is sent as a user message
         (the LLM should treat this like any user message — discuss, adjust, etc.)
      3. Ignore options entirely and type a message in the main input box.
    - The LLM must NOT assume rigid A/B/C — users have a free-text input
      to express ideas that go beyond or combine the presented options.
"""

from __future__ import annotations

from app.agent.tools.base import BaseTool, ToolMeta, ConcurrencyMode, ToolResult
from app.agent.interceptors import get_option_card_format


class PresentOptionsTool(BaseTool):
    """Present 2-3 structured option cards for user decision.

    This tool is INTERCEPTED — it does not execute as a normal tool.
    The interceptor layer captures its arguments and emits frontend events.

    IMPORTANT: Users are NOT limited to choosing one option. Below every
    set of option cards there is a "💬 我另有想法" button that opens a
    free-text input. Users can:
    - Pick an option as-is
    - Type their own direction ("把方案A和B结合起来...")
    - Ask follow-up questions ("方案C具体怎么写？")
    - Reject all options ("都不对，换个思路")

    The LLM should handle any free-form response naturally, just like
    any other user message in the conversation.
    """

    meta = ToolMeta(
        name="present_options",
        description=(
            "当需要用户做出方向性选择时调用此工具。\n"
            "提供 2-3 个结构化选项卡片，每个包含利弊分析和选定后的执行动作。\n"
            "\n"
            "重要：用户不限于选择一项——他们可以选择某个选项、输入自己的想法、\n"
            "组合多个方案、或者完全否定所有选项。选项卡片是沟通的起点，不是终点。\n"
            "\n"
            "调用时机：\n"
            "- 你分析了当前情况，发现有多个可行方向\n"
            "- 用户需要决定故事走向、角色发展、结构调整等\n"
            "- 你需要用户确认后才能执行写入操作\n"
            "\n"
            "不要每轮都调用它——只在真正需要用户做选择时才用。\n"
            "如果用户用自己的话回应（而非选择选项），正常继续对话即可。"
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
                    "description": "2-3 个结构化选项卡片。用户可能选择其中之一、组合多个、或提供自己的想法。",
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
