import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.world.agent import build_world
from app.world.repository import world_repo
from app.project.repository import ProjectRepository
from app.analysis.repository import AnalysisRepository


class WorldService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.analysis_repo = AnalysisRepository(db)

    async def generate_world(self, project_id: uuid.UUID) -> dict:
        analysis = await self.analysis_repo.get_latest_analysis(project_id)
        metadata = analysis.get("metadata", {}) if analysis else {}
        result = await build_world(metadata)
        for loc in result.locations:
            await world_repo.save_location(project_id, loc.model_dump())
        for fac in result.factions:
            await world_repo.save_faction(project_id, fac.model_dump())
        await self.project_repo.save_version(project_id, {"world": result.model_dump()})
        return result.model_dump()

    async def get_world(self, project_id: uuid.UUID) -> dict:
        return await world_repo.get_world_graph(project_id)
