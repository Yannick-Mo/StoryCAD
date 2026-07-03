import uuid
from typing import Optional
from app.knowledge_graph.repository import neo4j_repo


class StoryRepository:
    async def save_story_node(self, project_id: uuid.UUID, story_data: dict) -> str:
        story_id = f"story_{project_id}"
        await neo4j_repo.create_entity(project_id, "Story", story_id, story_data)
        return story_id

    async def save_beat(self, project_id: uuid.UUID, beat: dict) -> str:
        beat_id = f"beat_{beat['title'].replace(' ', '_')}"
        await neo4j_repo.create_entity(project_id, "StoryBeat", beat_id, beat)
        return beat_id

    async def link_beat_to_act(self, beat_id: str, act: int):
        async with await neo4j_repo.session() as session:
            await session.run("MATCH (b:StoryBeat {id: $bid}) SET b.act = $act", bid=beat_id, act=act)

    async def get_story(self, project_id: uuid.UUID) -> Optional[dict]:
        async with await neo4j_repo.session() as session:
            result = await session.run("MATCH (n:Story {project_id: $pid}) RETURN n", pid=str(project_id))
            record = await result.single()
            if record:
                return neo4j_repo._deserialize_props(dict(record["n"]))
            return None

    async def get_beats(self, project_id: uuid.UUID) -> list[dict]:
        async with await neo4j_repo.session() as session:
            result = await session.run(
                "MATCH (n:StoryBeat {project_id: $pid}) RETURN n ORDER BY n.act, n.tension_level",
                pid=str(project_id)
            )
            return [neo4j_repo._deserialize_props(dict(record["n"])) async for record in result]


story_repo = StoryRepository()
