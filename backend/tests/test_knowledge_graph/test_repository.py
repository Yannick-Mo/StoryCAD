import pytest
from app.knowledge_graph.repository import neo4j_repo


@pytest.mark.asyncio
async def test_create_and_get_entity():
    await neo4j_repo.connect()
    eid = "test_entity_1"
    await neo4j_repo.create_entity("test_project", "Event", eid, {"description": "test event"})
    entity = await neo4j_repo.get_entity(eid)
    assert entity is not None
    assert entity["description"] == "test event"
    await neo4j_repo.delete_entity(eid)
    await neo4j_repo.close()


@pytest.mark.asyncio
async def test_create_relation():
    await neo4j_repo.connect()
    sid, tid = "test_source", "test_target"
    await neo4j_repo.create_entity("test_project", "Event", sid, {})
    await neo4j_repo.create_entity("test_project", "Event", tid, {})
    ok = await neo4j_repo.create_relation(sid, tid, "CAUSES", {"type": "necessary"})
    assert ok
    await neo4j_repo.delete_entity(sid)
    await neo4j_repo.delete_entity(tid)
    await neo4j_repo.close()
