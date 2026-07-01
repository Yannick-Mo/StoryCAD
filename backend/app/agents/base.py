import json
import logging
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

logger = logging.getLogger(__name__)

_llm_cache: dict[float, ChatOpenAI] = {}


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    if temperature not in _llm_cache:
        _llm_cache[temperature] = ChatOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=MODEL_NAME,
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    return _llm_cache[temperature]


def run_agent(
    prompt: ChatPromptTemplate,
    inputs: dict[str, Any],
    temperature: float = 0.3
) -> dict:
    llm = get_llm(temperature)
    chain = prompt | llm

    for attempt in range(2):
        try:
            response = chain.invoke(inputs)
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt + 1}/2): {e}")
            if attempt == 1:
                raise

    return {}
