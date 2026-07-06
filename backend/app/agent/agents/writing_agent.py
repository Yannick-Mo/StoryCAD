# backend/app/agent/agents/writing_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import WritingOutput


class WritingAgent(BaseAgent):
    prompt_name = "writing"
    output_schema = WritingOutput
