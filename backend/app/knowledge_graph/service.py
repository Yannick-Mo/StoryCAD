import uuid
from app.knowledge_graph.repository import neo4j_repo


class KnowledgeGraphService:
    async def create_character(self, project_id: uuid.UUID, char_id: str, name: str, properties: dict) -> dict:
        props = {"name": name, **properties}
        return await neo4j_repo.create_entity(project_id, "Character", char_id, props)

    async def create_event(self, project_id: uuid.UUID, event_id: str, description: str, properties: dict) -> dict:
        props = {"description": description, **properties}
        return await neo4j_repo.create_entity(project_id, "Event", event_id, props)

    async def create_causal_edge(self, source_id: str, target_id: str, edge_type: str):
        return await neo4j_repo.create_relation(source_id, target_id, "CAUSES", {"type": edge_type})

    async def create_relationship(self, source_id: str, target_id: str, trust: int, threat: int, attraction: int):
        return await neo4j_repo.create_relation(
            source_id, target_id, "RELATES_TO",
            {"trust": trust, "threat": threat, "attraction": attraction}
        )

    async def delete_project_data(self, project_id: uuid.UUID):
        await neo4j_repo.delete_project_graph(str(project_id))


kg_service = KnowledgeGraphService()
