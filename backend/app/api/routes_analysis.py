import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.analysis.service import AnalysisService

router = APIRouter(prefix="/api/projects/{project_id}/analysis", tags=["analysis"])


@router.post("")
async def analyze_project(project_id: uuid.UUID, raw_input: dict, db: AsyncSession = Depends(get_db)):
    service = AnalysisService(db)
    return await service.analyze(project_id, raw_input)


@router.get("")
async def get_analysis(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = AnalysisService(db)
    result = await service.get_analysis(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="No analysis found")
    return result
