import json
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError
from app.config import settings

logger = logging.getLogger(__name__)
_llm_cache = {}


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    if temperature not in _llm_cache:
        base_url = settings.deepseek_base_url
        api_key = settings.deepseek_api_key
        model = settings.model_name
        if settings.llm_provider == "openai":
            base_url = settings.openai_base_url or "https://api.openai.com/v1"
            api_key = settings.openai_api_key
        _llm_cache[temperature] = ChatOpenAI(
            api_key=api_key, base_url=base_url, model=model,
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    return _llm_cache[temperature]


def run_agent(prompt_messages: list, inputs: dict, temperature: float = 0.3, schema: Optional[type] = None) -> dict:
    llm = get_llm(temperature)
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    chain = prompt | llm
    for attempt in range(2):
        try:
            response = chain.invoke(inputs)
            result = json.loads(response.content)
            if schema is not None:
                validated = schema(**result)
                return validated.model_dump()
            return result
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Agent attempt {attempt + 1}/2 failed: {e}")
            if attempt == 1:
                raise
    return {}
