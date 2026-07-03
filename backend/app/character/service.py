import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.character.agent import design_characters
from app.character.repository import character_repo
from app.knowledge_graph.repository import neo4j_repo
from app.project.repository import ProjectRepository
from app.analysis.repository import AnalysisRepository


class CharacterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.analysis_repo = AnalysisRepository(db)

    async def generate_characters(self, project_id: uuid.UUID) -> dict:
        analysis = await self.analysis_repo.get_latest_analysis(project_id)
        metadata = analysis.get("metadata", {}) if analysis else {}
        result = await design_characters(metadata)
        for char in result.characters:
            await character_repo.save_character_to_graph(project_id, char.model_dump())
        for rel in result.relationships:
            await character_repo.save_relationship(f"char_{rel.from_name}", f"char_{rel.to_name}", rel.model_dump())
        await self.project_repo.save_version(project_id, {"characters": result.model_dump()})
        return result.model_dump()

    async def get_characters(self, project_id: uuid.UUID) -> list[dict]:
        return await character_repo.get_characters(project_id)

    async def update_character(self, project_id: uuid.UUID, name: str, updates: dict) -> bool:
        async with await neo4j_repo.session() as session:
            result = await session.run("MATCH (n:Character {project_id: $pid, name: $name}) SET n += $props RETURN n", pid=str(project_id), name=name, props=neo4j_repo._sanitize_props(updates))
            return (await result.single()) is not None

    async def delete_character(self, project_id: uuid.UUID, name: str) -> bool:
        return await character_repo.delete_character(project_id, name)