import re
import json
import yaml
from pathlib import Path

from app.llm.client import LLMClient, get_shared_client as _get_llm_shared_client


PROMPT_DIR = Path(__file__).parent / "project_creator" / "prompts"


def get_shared_client() -> LLMClient:
    return _get_llm_shared_client()


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return json.loads(text)


async def parse_json_safe(text: str, client: LLMClient | None = None, messages: list | None = None) -> dict:
    try:
        return parse_json(text)
    except (json.JSONDecodeError, ValueError):
        if client is None or not messages:
            return {}
    try:
        from app.llm.types import Message
        correction = [Message(role="user", content="上一条回复不是合法 JSON。请只输出合法的 JSON 对象，不要 markdown 代码块，不要多余文字。原回复：" + text[:300])]
        retry_result = await client.chat(messages + correction, temperature=0.3)
        return parse_json(retry_result.content or "")
    except (json.JSONDecodeError, ValueError):
        return {}


def load_project_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("system", "") if data else ""
    except (FileNotFoundError, yaml.YAMLError):
        return ""


def count_words(text: str) -> int:
    if not text:
        return 0
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_cjk = len(re.sub(r'[\u4e00-\u9fff]', '', text).split())
    return cjk + non_cjk
