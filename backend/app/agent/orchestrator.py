# backend/app/agent/orchestrator.py
import uuid
import logging
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from app.agent.context import ContextBuilder
from app.agent.agents.goal_agent import GoalAgent
from app.agent.agents.outline_agent import OutlineAgent

logger = logging.getLogger(__name__)


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

    async def create_project_from_material(
        self, user_id: uuid.UUID, material: str, db: AsyncSession, project_title: str = "未命名项目"
    ) -> AsyncGenerator[dict, None]:
        """Create a project from raw material with transaction rollback on failure."""
        from app.agent.project_creator.graph import run_pipeline
        from app.agent.project_creator.state import MaterialState
        from app.agent.tools.project_admin_tools import _write_new_project

        initial_state: MaterialState = {
            "material": material,
            "project_title": project_title.strip() or "未命名项目",
            "genre": "", "tone": "", "characters_raw": [],
            "plot_summary": "", "world_elements": "",
            "acts": [], "estimated_words": 0, "scenes": [],
            "characters": [], "relations": [], "edges": [],
            "global_settings": "", "errors": [],
        }

        try:
            async with db.begin_nested():
                async for node_name, node_output in run_pipeline(initial_state):
                    if isinstance(node_output, dict) and node_output.get("errors"):
                        raise RuntimeError(f"Step {node_name} failed: {node_output['errors']}")
                    yield {"type": "step", "node": node_name, "data": node_output}

                final_state = initial_state
                project_id = await _write_new_project(db, final_state, user_id, do_commit=False)
                yield {"type": "project_id", "project_id": str(project_id)}
        except Exception as e:
            logger.error("createFromMaterial failed, rolling back: %s", e)
            yield {"type": "error", "data": {"step": "material_creation", "detail": str(e)}}
            return

        await db.commit()
        yield {"type": "done", "data": {"message": "项目创建成功"}}
