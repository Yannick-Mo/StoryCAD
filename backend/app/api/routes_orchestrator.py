import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.orchestrator.service import OrchestratorService
from app.project.repository import ProjectRepository

router = APIRouter(prefix="/api/projects/{project_id}/workflow", tags=["orchestrator"])


@router.post("/start")
async def start_workflow(project_id: uuid.UUID, raw_input: dict, db: AsyncSession = Depends(get_db)):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    service = OrchestratorService(db)
    return await service.start_workflow(project_id, raw_input)


@router.get("/state")
async def get_state(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = OrchestratorService(db)
    state = await service.get_workflow_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="No workflow state found")
    return state
