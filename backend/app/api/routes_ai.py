# backend/app/api/routes_ai.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.project.service import ProjectService
from app.agent.orchestrator import AgentOrchestrator


class AiGenerateRequest(BaseModel):
    chapter_id: str
    mode: str
    prompt: str = ""


router = APIRouter(prefix="/api/projects/{project_id}", tags=["ai"])


@router.post("/ai/generate")
async def ai_generate(
    project_id: uuid.UUID,
    payload: AiGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectService(db)
    project = await svc.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.mode not in ("goal", "outline", "writing"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")

    prompt = payload.prompt.strip()[:2000]

    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.generate(
        project_id,
        uuid.UUID(payload.chapter_id),
        payload.mode,
        prompt,
    )
    return result
