import uuid
from typing import Optional
from fastapi import APIRouter, Query
from app.knowledge_graph.repository import neo4j_repo
from app.models.errors import ErrorResponse

router = APIRouter(prefix="/api/projects/{project_id}/graph", tags=["knowledge-graph"])


@router.get("/entities")
async def list_entities(
    project_id: uuid.UUID,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (Character, Location, Faction, etc.)")
):
    async with await neo4j_repo.session() as session:
        if entity_type:
            result = await session.run(
                "MATCH (n {project_id: $pid, entity_type: $type}) RETURN n ORDER BY n.name",
                pid=str(project_id), type=entity_type
            )
        else:
            result = await session.run(
                "MATCH (n {project_id: $pid}) RETURN n ORDER BY n.entity_type, n.name",
                pid=str(project_id)
            )
        return {
            "entities": [
                {**dict(record["n"]), "id": record["n"].element_id}
                async for record in result
            ]
        }


@router.get("/relationships")
async def list_relationships(project_id: uuid.UUID, max_depth: int = Query(2, ge=1, le=5)):
    async with await neo4j_repo.session() as session:
        result = await session.run(
            "MATCH (a {project_id: $pid})-[r]-(b {project_id: $pid}) "
            "RETURN a.name AS source, b.name AS target, type(r) AS relationship, "
            "r {.*} AS properties LIMIT 100",
            pid=str(project_id)
        )
        rels = []
        async for record in result:
            rels.append({
                "source": record["source"],
                "target": record["target"],
                "relationship": record["relationship"],
                "properties": dict(record["properties"]) if record["properties"] else {},
            })
        return {"relationships": rels}


@router.get("/paths")
async def find_paths(
    project_id: uuid.UUID,
    start_name: str = Query(..., description="Starting entity name"),
    end_name: str = Query(..., description="Ending entity name"),
    max_depth: int = Query(4, ge=1, le=10)
):
    async with await neo4j_repo.session() as session:
        result = await session.run(
            "MATCH path = shortestPath("
            "(a {project_id: $pid, name: $start})-[*1..$depth]-(b {project_id: $pid, name: $end})"
            ") RETURN [n IN nodes(path) | {id: n.element_id, name: n.name, type: coalesce(n.entity_type, labels(n)[0])}] AS nodes, "
            "[r IN relationships(path) | {type: type(r)}] AS edges",
            pid=str(project_id), start=start_name, end=end_name, depth=max_depth
        )
        record = await result.single()
        if record:
            return {"nodes": list(record["nodes"]), "edges": list(record["edges"])}
        return {"nodes": [], "edges": [], "detail": "No path found"}


@router.get("/stats")
async def graph_stats(project_id: uuid.UUID):
    async with await neo4j_repo.session() as session:
        entities = await session.run(
            "MATCH (n {project_id: $pid}) RETURN n.entity_type AS type, count(*) AS count",
            pid=str(project_id)
        )
        rels = await session.run(
            "MATCH ()-[r {project_id: $pid}]-() RETURN type(r) AS type, count(*) AS count",
            pid=str(project_id)
        )
        return {
            "entities": {record["type"]: record["count"] async for record in entities},
            "relationships": {record["type"]: record["count"] async for record in rels},
        }
