from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    reasoning_content: str | None = None

    def __repr__(self) -> str:
        return (
            f"Message(role={self.role!r}, content={self.content!r}, "
            f"tool_calls={self.tool_calls!r}, tool_call_id={self.tool_call_id!r}, "
            f"name={self.name!r}, reasoning_content={self.reasoning_content!r})"
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.reasoning_content:
            d["reasoning_content"] = self.reasoning_content
        if self.tool_calls:
            d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ToolCall:
    id: str
    type: Literal["function"] = "function"
    function: dict | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "function": self.function}


@dataclass
class ToolDef:
    type: Literal["function"] = "function"
    function: dict | None = None


@dataclass
class ModelDef:
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    supports_streaming: bool = True
    supports_fc: bool = True
    max_tokens: int = 8192
    cost_per_1k_input: float = 0.0001
    cost_per_1k_output: float = 0.0002


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


@dataclass
class StreamChunk:
    """A single chunk from a streaming LLM response with tool support.

    At most one of *content* or *tool_call* is non-None per chunk.
    *finish_reason* and *usage* signal the end of the stream.
    *reasoning_content* carries DeepSeek thinking-mode content (set on finish_reason).
    """
    content: str | None = None
    tool_call: ToolCall | None = None
    finish_reason: str | None = None
    usage: Usage | None = None
    reasoning_content: str | None = None


@dataclass
class ChatResult:
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: Usage | None = None
    model: str = ""
    finish_reason: str = ""
