import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.world.service import WorldService

router = APIRouter(prefix="/api/projects/{project_id}/world", tags=["world"])


@router.get("")
async def get_world(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WorldService(db)
    return await service.get_world(project_id)


@router.post("/generate")
async def generate_world(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WorldService(db)
    return await service.generate_world(project_id)
