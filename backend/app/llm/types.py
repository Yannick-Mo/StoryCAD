from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str | None = None
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ToolCall:
    id: str
    type: Literal["function"] = "function"
    function: dict | None = None


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
class ChatResult:
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: Usage | None = None
    model: str = ""
    finish_reason: str = ""
