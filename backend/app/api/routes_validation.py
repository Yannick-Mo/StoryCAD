import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.validation.service import ValidationService

router = APIRouter(prefix="/api/projects/{project_id}/validation", tags=["validation"])


@router.post("")
async def validate_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = ValidationService(db)
    return await service.validate(project_id)
