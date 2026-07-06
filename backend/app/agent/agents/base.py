# backend/app/agent/agents/base.py
import json
import yaml
from pathlib import Path
from pydantic import BaseModel
from app.agent.client import LLMClient


PROMPT_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent:
    prompt_name: str = ""
    output_schema: type[BaseModel] = BaseModel

    def _load_yaml(self, name: str) -> dict:
        path = PROMPT_DIR / f"{name}.yaml"
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_persona(self) -> str:
        data = self._load_yaml("persona")
        return data.get("system", "")

    def _system_prompt(self, context: dict, user_prompt: str) -> str:
        data = self._load_yaml(self.prompt_name)
        template = data.get("system", "")
        persona = self._load_persona()
        prompt = template.format(persona=persona, **context, user_prompt=user_prompt)
        return prompt

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
            text = "\n".join(lines[1:end])
        return json.loads(text)

    async def run(self, client: LLMClient, context: dict, user_prompt: str) -> BaseModel:
        system = self._system_prompt(context, user_prompt)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "请按 JSON 格式输出"},
        ]
        raw = await client.chat(messages)
        parsed = self._parse_json(raw)
        return self.output_schema.model_validate(parsed)
