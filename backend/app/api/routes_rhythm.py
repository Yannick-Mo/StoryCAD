"""Rhythm analysis API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.agent.rhythm.analyzer import RhythmAnalyzer

router = APIRouter(prefix="/api/rhythm", tags=["Rhythm"])


@router.get("/projects/{project_id}/analyze")
async def analyze_rhythm(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        analyzer = RhythmAnalyzer(db)
        return await analyzer.analyze(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"节奏分析失败: {str(e)}")
