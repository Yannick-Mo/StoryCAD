import re
import json
import yaml
from pathlib import Path


PROMPT_DIR = Path(__file__).parent / "project_creator" / "prompts"


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return json.loads(text)


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
