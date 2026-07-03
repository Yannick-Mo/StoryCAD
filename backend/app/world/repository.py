import uuid
from app.knowledge_graph.repository import neo4j_repo


class WorldRepository:
    async def save_location(self, project_id: uuid.UUID, location: dict) -> str:
        loc_id = f"loc_{location['name']}"
        await neo4j_repo.create_entity(project_id, "Location", loc_id, location)
        return loc_id

    async def save_faction(self, project_id: uuid.UUID, faction: dict) -> str:
        fac_id = f"fac_{faction['name']}"
        await neo4j_repo.create_entity(project_id, "Faction", fac_id, faction)
        return fac_id

    async def get_world_graph(self, project_id: uuid.UUID) -> dict:
        async with await neo4j_repo.session() as session:
            locations = await session.run("MATCH (n:Location {project_id: $pid}) RETURN n", pid=str(project_id))
            factions = await session.run("MATCH (n:Faction {project_id: $pid}) RETURN n", pid=str(project_id))
            rules = await session.run("MATCH (n:WorldRule {project_id: $pid}) RETURN n", pid=str(project_id))
            return {
                "locations": [dict(record["n"]) async for record in locations],
                "factions": [dict(record["n"]) async for record in factions],
                "rules": [dict(record["n"]) async for record in rules],
            }

    async def clear_world(self, project_id: uuid.UUID):
        async with await neo4j_repo.session() as session:
            for label in ["Location", "Faction", "WorldRule"]:
                await session.run("MATCH (n:{label} {{project_id: $pid}}) DETACH DELETE n", label=label, pid=str(project_id))


world_repo = WorldRepository()
