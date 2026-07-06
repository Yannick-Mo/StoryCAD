# backend/app/agent/client.py
import httpx
from app.config import settings


class LLMClient:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
