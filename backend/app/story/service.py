import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.story.agents import generate_structure, generate_plots
from app.story.repository import story_repo
from app.project.repository import ProjectRepository
from app.analysis.repository import AnalysisRepository
from app.character.repository import CharacterRepository
from app.world.repository import WorldRepository


class StoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.analysis_repo = AnalysisRepository(db)

    async def generate_story(self, project_id: uuid.UUID) -> dict:
        analysis = await self.analysis_repo.get_latest_analysis(project_id)
        characters = await CharacterRepository().get_characters(project_id)
        world = await WorldRepository().get_world_graph(project_id)
        metadata = {
            "analysis": analysis.get("metadata", {}) if analysis else {},
            "characters": characters,
            "world": world,
        }
        structure_result = await generate_structure(metadata)
        structure_data = structure_result.model_dump()
        await story_repo.save_story_node(project_id, structure_data)
        if structure_result.plot_arcs:
            all_beats = []
            for arc in structure_result.plot_arcs:
                all_beats.extend(arc.beats or [])
            for beat in all_beats:
                beat_id = await story_repo.save_beat(project_id, beat.model_dump())
                await story_repo.link_beat_to_act(beat_id, beat.act)
        await self.project_repo.save_version(project_id, {"story_structure": structure_data})
        return structure_data

    async def get_story(self, project_id: uuid.UUID) -> dict:
        return (await story_repo.get_story(project_id)) or {}

    async def generate_detailed_plots(self, project_id: uuid.UUID) -> dict:
        story = await story_repo.get_story(project_id)
        if not story:
            return {"error": "Generate story structure first"}
        result = await generate_plots(story)
        for beat in result.get("beats", []):
            beat_id = await story_repo.save_beat(project_id, beat)
            await story_repo.link_beat_to_act(beat_id, beat.get("act", 1))
        await self.project_repo.save_version(project_id, {"detailed_plots": result})
        return result
