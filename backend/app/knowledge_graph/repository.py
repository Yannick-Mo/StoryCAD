import json
import uuid
from typing import Optional
from neo4j import AsyncGraphDatabase

from app.config import settings


class Neo4jRepository:
    def __init__(self):
        self._driver = None

    async def connect(self):
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def session(self):
        await self.connect()
        return self._driver.session()

    @staticmethod
    def _sanitize_props(props: dict) -> dict:
        return {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in props.items()}

    @staticmethod
    def _deserialize_props(props: dict) -> dict:
        result = {}
        for k, v in props.items():
            if isinstance(v, str):
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            else:
                result[k] = v
        return result

    async def create_entity(self, project_id: uuid.UUID, label: str, entity_id: str, properties: dict) -> dict:
        async with await self.session() as session:
            result = await session.run(
                f"CREATE (n:{label} {{id: $id, project_id: $project_id}}) SET n += $props RETURN n",
                id=entity_id, project_id=str(project_id), props=self._sanitize_props(properties)
            )
            record = await result.single()
            return self._deserialize_props(dict(record["n"])) if record else {}

    async def get_entity(self, entity_id: str) -> Optional[dict]:
        async with await self.session() as session:
            result = await session.run("MATCH (n {id: $id}) RETURN n", id=entity_id)
            record = await result.single()
            return self._deserialize_props(dict(record["n"])) if record else None

    async def update_entity(self, entity_id: str, properties: dict) -> bool:
        async with await self.session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) SET n += $props RETURN n",
                id=entity_id, props=self._sanitize_props(properties)
            )
            record = await result.single()
            return record is not None

    async def delete_entity(self, entity_id: str) -> bool:
        async with await self.session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) as deleted",
                id=entity_id
            )
            record = await result.single()
            return record["deleted"] > 0 if record else False

    async def create_relation(self, source_id: str, target_id: str, rel_type: str, properties: dict = None) -> bool:
        props_clause = "SET r += $props" if properties else ""
        san_props = self._sanitize_props(properties) if properties else {}
        async with await self.session() as session:
            result = await session.run(
                f"MATCH (a {{id: $sid}}), (b {{id: $tid}}) "
                f"CREATE (a)-[r:{rel_type}]->(b) {props_clause} RETURN r",
                sid=source_id, tid=target_id, props=san_props
            )
            record = await result.single()
            return record is not None

    async def get_entity_relations(self, entity_id: str) -> list[dict]:
        async with await self.session() as session:
            result = await session.run(
                "MATCH (n {id: $id})-[r]-() RETURN type(r) as type, startNode(r).id as source, endNode(r).id as target",
                id=entity_id
            )
            return [dict(record) async for record in result]

    async def query_path(self, start_id: str, end_id: str, max_depth: int = 5) -> list[list[dict]]:
        async with await self.session() as session:
            result = await session.run(
                "MATCH p = shortestPath((a {id: $sid})-[*..$depth]-(b {id: $tid})) "
                "RETURN [n IN nodes(p) | {id: n.id, labels: labels(n)}] as path",
                sid=start_id, tid=end_id, depth=max_depth
            )
            records = await result.fetch()
            return [record["path"] for record in records if record]

    async def delete_project_graph(self, project_id: str):
        async with await self.session() as session:
            await session.run("MATCH (n {project_id: $pid}) DETACH DELETE n", pid=project_id)


neo4j_repo = Neo4jRepository()
