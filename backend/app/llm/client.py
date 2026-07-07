import asyncio
from typing import Any, Literal

import httpx

from .types import ChatResult, Message, ToolCall, ToolDef, Usage
from .registry import get as _get_model
from .tracker import TokenTracker

RETRYABLE_STATUSES = {429, 500, 502, 503}
MAX_RETRIES = 3


class LLMError(Exception):
    pass


_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    return _tracker


def _message_to_dict(msg: Message) -> dict:
    d: dict[str, Any] = {"role": msg.role}
    if msg.content is not None:
        d["content"] = msg.content
    else:
        d["content"] = None
    if msg.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "type": tc.type, "function": tc.function}
            for tc in msg.tool_calls
        ]
    if msg.tool_call_id:
        d["tool_call_id"] = msg.tool_call_id
    if msg.name:
        d["name"] = msg.name
    return d


def _tool_def_to_dict(td: ToolDef) -> dict:
    return {"type": td.type, "function": td.function}


class LLMClient:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "deepseek-chat"
        model = _get_model(self.model_name)
        self.api_key = model.api_key
        self.base_url = model.base_url
        self.model_def = model

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: list[ToolDef] | None = None,
        tool_choice: str = "auto",
        response_format: Literal["json_object"] | None = None,
    ) -> ChatResult:
        model_name = model or self.model_name
        model_def = _get_model(model_name)

        body: dict[str, Any] = {
            "model": model_name,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if stream:
            body["stream"] = True

        if tools:
            body["tools"] = [_tool_def_to_dict(t) for t in tools]
            body["tool_choice"] = tool_choice

        if response_format == "json_object":
            body["response_format"] = {"type": response_format}

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    headers = {
                        "Authorization": f"Bearer {model_def.api_key}",
                        "Content-Type": "application/json",
                    }

                    if stream:
                        return await self._handle_stream(
                            client, headers, body, model_name
                        )

                    resp = await client.post(
                        f"{model_def.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_response(data, model_name)

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in RETRYABLE_STATUSES:
                    raise LLMError(
                        f"LLM API error {e.response.status_code}: {e.response.text}"
                    ) from e
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
            except Exception as e:
                raise LLMError(f"Unexpected LLM error: {e}") from e

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

        raise LLMError(f"LLM request failed after {MAX_RETRIES} retries") from last_error

    async def _handle_stream(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        body: dict,
        model_name: str,
    ) -> ChatResult:
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        finish_reason = ""
        usage_data: dict | None = None

        async with client.stream(
            "POST",
            f"{self.model_def.base_url}/chat/completions",
            headers=headers,
            json=body,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {})

                if delta.get("content"):
                    content_parts.append(delta["content"])

                if delta.get("tool_calls"):
                    for tc_chunk in delta["tool_calls"]:
                        idx = tc_chunk.get("index", 0)
                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                ToolCall(id="", function={"name": "", "arguments": ""})
                            )
                        if tc_chunk.get("id"):
                            tool_calls[idx].id = tc_chunk["id"]
                        if tc_chunk.get("function"):
                            fn = tc_chunk["function"]
                            if fn.get("name"):
                                tool_calls[idx].function["name"] += fn["name"]
                            if fn.get("arguments"):
                                tool_calls[idx].function["arguments"] += fn["arguments"]

                finish = chunk.get("choices", [{}])[0].get("finish_reason")
                if finish:
                    finish_reason = finish

                usage_data = chunk.get("usage")

        content = "".join(content_parts) or None

        usage: Usage | None = None
        if usage_data:
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            _tracker.track(
                model=model_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )

        return ChatResult(
            content=content,
            tool_calls=tool_calls or None,
            usage=usage,
            model=model_name,
            finish_reason=finish_reason,
        )

    def _parse_response(self, data: dict, model_name: str) -> ChatResult:
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content")

        tool_calls: list[ToolCall] | None = None
        if msg.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    type=tc.get("type", "function"),
                    function=tc.get("function"),
                )
                for tc in msg["tool_calls"]
            ]

        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        _tracker.track(
            model=model_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        return ChatResult(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=model_name,
            finish_reason=choice.get("finish_reason", ""),
        )
