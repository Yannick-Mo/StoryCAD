# backend/app/agent/agents/outline_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import OutlineOutput


class OutlineAgent(BaseAgent):
    prompt_name = "outline"
    output_schema = OutlineOutput
