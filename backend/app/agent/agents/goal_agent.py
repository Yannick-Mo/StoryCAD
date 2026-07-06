# backend/app/agent/agents/goal_agent.py
from app.agent.agents.base import BaseAgent
from app.agent.schema import GoalOutput


class GoalAgent(BaseAgent):
    prompt_name = "goal"
    output_schema = GoalOutput
