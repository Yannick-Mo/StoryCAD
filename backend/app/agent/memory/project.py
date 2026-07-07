from typing import Any
from redis.asyncio import Redis


class ProjectMemory:
    def __init__(self, redis_client: Redis | None = None):
        self._redis = redis_client
        self._store: dict[str, dict] = {}

    async def set(self, project_id: str, key: str, value: Any) -> None:
        if self._redis:
            import json
            await self._redis.hset(
                f"proj_mem:{project_id}", key, json.dumps(value)
            )
        else:
            if project_id not in self._store:
                self._store[project_id] = {}
            self._store[project_id][key] = value

    async def get(self, project_id: str, key: str) -> Any | None:
        if self._redis:
            import json
            raw = await self._redis.hget(f"proj_mem:{project_id}", key)
            if raw is None:
                return None
            return json.loads(raw)
        return self._store.get(project_id, {}).get(key)

    async def delete(self, project_id: str, key: str) -> None:
        if self._redis:
            await self._redis.hdel(f"proj_mem:{project_id}", key)
        else:
            store = self._store.get(project_id)
            if store and key in store:
                del store[key]

    async def clear(self, project_id: str) -> None:
        if self._redis:
            await self._redis.delete(f"proj_mem:{project_id}")
        else:
            self._store.pop(project_id, None)