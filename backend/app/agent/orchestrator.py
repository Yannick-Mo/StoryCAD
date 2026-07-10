# backend/app/agent/orchestrator.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from app.agent.context import ContextBuilder
from app.agent.agents.goal_agent import GoalAgent
from app.agent.agents.outline_agent import OutlineAgent



class AgentOrchestrator:
    def __init__(self, db: AsyncSession, llm_client: LLMClient | None = None):
        self.db = db
        self._llm_client = llm_client or LLMClient()
        self.client = self._llm_client
        self.context_builder = ContextBuilder(db)
        self.agents = {
            "goal": GoalAgent(),
            "outline": OutlineAgent(),
        }

    async def generate(self, project_id: uuid.UUID, chapter_id: uuid.UUID, mode: str, user_prompt: str) -> dict:
        agent = self.agents[mode]
        context = await self.context_builder.build(mode, project_id, chapter_id)
        result = await agent.run(self.client, context, user_prompt)
        return result.model_dump()
