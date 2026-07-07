from app.config import settings
from app.llm import LLMClient as _LLMClient
from app.llm import Message as _Message
from app.llm import configure_from_settings as _configure_from_settings


class LLMClient:
    """Backward-compatible wrapper around the new LLM infrastructure.

    Existing callers expect LLMClient.chat(messages, temperature, max_tokens)
    to return a plain string.  This wrapper converts old-style dict messages
    to app.llm.Message objects and returns result.content.
    """

    def __init__(self):
        try:
            self._client = _LLMClient()
        except KeyError:
            _configure_from_settings(settings)
            self._client = _LLMClient()

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        new_messages = [
            _Message(role=m["role"], content=m.get("content"))
            for m in messages
        ]
        result = await self._client.chat(
            messages=new_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.content or ""
