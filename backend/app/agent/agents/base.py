# backend/app/agent/agents/base.py
import yaml
from pathlib import Path
from pydantic import BaseModel
from app.agent.client import LLMClient
from app.agent.utils import parse_json


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

        skill_names = context.get("active_skills") or []
        if skill_names:
            persona = f"已启用技能：{', '.join(skill_names)}\n" + persona

        try:
            prompt = template.format(persona=persona, **context, user_prompt=user_prompt)
        except KeyError:
            prompt = template

        rag_context = context.get("rag_context") or ""
        if rag_context:
            prompt += f"\n\n参考知识：\n{rag_context}"

        return prompt

    async def run(self, client: LLMClient, context: dict, user_prompt: str) -> BaseModel:
        system = self._system_prompt(context, user_prompt)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "请按 JSON 格式输出"},
        ]
        raw = await client.chat(messages)
        parsed = parse_json(raw)
        return self.output_schema.model_validate(parsed)
