import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.validation.agent import validate_story
from app.analysis.repository import AnalysisRepository
from app.character.repository import CharacterRepository
from app.world.repository import WorldRepository
from app.story.repository import StoryRepository
from app.project.repository import ProjectRepository


class ValidationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)

    async def validate(self, project_id: uuid.UUID) -> dict:
        analysis = await AnalysisRepository(self.db).get_latest_analysis(project_id)
        characters = await CharacterRepository().get_characters(project_id)
        world = await WorldRepository().get_world_graph(project_id)
        story = await StoryRepository().get_story(project_id)
        story_package = {
            "analysis": analysis or {},
            "characters": characters,
            "world": world,
            "story": story or {},
        }
        result = await validate_story(story_package)
        data = result.model_dump()
        await self.project_repo.save_version(project_id, {"validation": data})
        return data
