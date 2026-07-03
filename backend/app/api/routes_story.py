import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.story.service import StoryService

router = APIRouter(prefix="/api/projects/{project_id}/story", tags=["story"])


@router.get("")
async def get_story(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = StoryService(db)
    return await service.get_story(project_id)


@router.post("/generate")
async def generate_story(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = StoryService(db)
    return await service.generate_story(project_id)


@router.post("/plots")
async def generate_plots(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = StoryService(db)
    return await service.generate_detailed_plots(project_id)
