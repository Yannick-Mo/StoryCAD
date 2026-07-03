import uuid
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.project.models import ProjectVersion


class AnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_analysis(self, project_id: uuid.UUID, analysis: dict) -> ProjectVersion:
        result = await self.db.execute(
            select(ProjectVersion).where(ProjectVersion.project_id == project_id)
            .order_by(desc(ProjectVersion.version)).limit(1)
        )
        latest = result.scalar_one_or_none()
        version = (latest.version + 1) if latest else 1
        pv = ProjectVersion(project_id=project_id, version=version, snapshot={"analysis": analysis})
        self.db.add(pv)
        await self.db.commit()
        await self.db.refresh(pv)
        return pv

    async def get_latest_analysis(self, project_id: uuid.UUID) -> Optional[dict]:
        result = await self.db.execute(
            select(ProjectVersion).where(ProjectVersion.project_id == project_id)
            .order_by(desc(ProjectVersion.version)).limit(1)
        )
        pv = result.scalar_one_or_none()
        if pv and pv.snapshot and "analysis" in pv.snapshot:
            return pv.snapshot["analysis"]
        return None
