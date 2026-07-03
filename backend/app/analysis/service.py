import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.analysis.repository import AnalysisRepository
from app.analysis.agent import run_analysis


class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.repo = AnalysisRepository(db)

    async def analyze(self, project_id: uuid.UUID, raw_input: dict) -> dict:
        result = await run_analysis(raw_input)
        data = result.model_dump()
        await self.repo.save_analysis(project_id, data)
        return data

    async def get_analysis(self, project_id: uuid.UUID) -> dict | None:
        return await self.repo.get_latest_analysis(project_id)
