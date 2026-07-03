import uuid
from app.knowledge_graph.repository import neo4j_repo


class CharacterRepository:
    async def save_character_to_graph(self, project_id: uuid.UUID, profile: dict) -> str:
        char_id = f"char_{profile['name']}"
        await neo4j_repo.create_entity(project_id, "Character", char_id, profile)
        return char_id

    async def save_relationship(self, from_id: str, to_id: str, rel: dict):
        await neo4j_repo.create_relation(from_id, to_id, "RELATES_TO", rel)

    async def get_characters(self, project_id: uuid.UUID) -> list[dict]:
        async with await neo4j_repo.session() as session:
            result = await session.run("MATCH (n:Character {project_id: $pid}) RETURN n", pid=str(project_id))
            return [neo4j_repo._deserialize_props(dict(record["n"])) async for record in result]

    async def delete_character(self, project_id: uuid.UUID, name: str) -> bool:
        async with await neo4j_repo.session() as session:
            result = await session.run("MATCH (n:Character {project_id: $pid, name: $name}) DETACH DELETE n RETURN count(n)", pid=str(project_id), name=name)
            record = await result.single()
            return record[0] > 0 if record else False


character_repo = CharacterRepository()