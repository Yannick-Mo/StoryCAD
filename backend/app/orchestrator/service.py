import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.orchestrator.machine import OrchestratorMachine
from app.orchestrator.models import WorkflowState


class OrchestratorService:
    def __init__(self, db: AsyncSession):
        self.machine = OrchestratorMachine(db)

    async def start_workflow(self, project_id: uuid.UUID, raw_input: dict) -> dict:
        return await self.machine.run_full_workflow(project_id, raw_input)

    async def get_workflow_state(self, project_id: uuid.UUID) -> Optional[dict]:
        state = await self.machine.get_state(project_id)
        if state:
            return state.model_dump()
        return None
