# backend/app/agent/orchestrator.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.client import LLMClient
from app.agent.context import ContextBuilder
from app.agent.agents.goal_agent import GoalAgent
from app.agent.agents.outline_agent import OutlineAgent
from app.agent.agents.writing_agent import WritingAgent


class AgentOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = LLMClient()
        self.context_builder = ContextBuilder(db)
        self.agents = {
            "goal": GoalAgent(),
            "outline": OutlineAgent(),
            "writing": WritingAgent(),
        }

    async def generate(self, project_id: uuid.UUID, chapter_id: uuid.UUID, mode: str, user_prompt: str) -> dict:
        agent = self.agents[mode]
        context = await self.context_builder.build(mode, project_id, chapter_id)
        result = await agent.run(self.client, context, user_prompt)
        return result.model_dump()
