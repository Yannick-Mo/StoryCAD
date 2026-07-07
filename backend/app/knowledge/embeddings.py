import httpx
from app.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"


async def _call_embedding_api(texts: list[str]) -> list[list[float]]:
    url = f"{settings.llm_base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    results = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in results]


async def embed_text(text: str) -> list[float]:
    vectors = await _call_embedding_api([text])
    return vectors[0]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await _call_embedding_api(texts)
