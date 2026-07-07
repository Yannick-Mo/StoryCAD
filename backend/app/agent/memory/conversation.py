import json
import uuid
from typing import Any
from redis.asyncio import Redis
from app.llm.types import Message


_CONV_PREFIX = "conv:"
_CONV_META_PREFIX = "conv_meta:"
_CONV_MSGS_PREFIX = "conv_msgs:"


def _msg_to_dict(m: Message) -> dict[str, Any]:
    d: dict[str, Any] = {"role": m.role}
    if m.content is not None:
        d["content"] = m.content
    if m.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "type": tc.type, "function": tc.function}
            for tc in m.tool_calls
        ]
    if m.tool_call_id:
        d["tool_call_id"] = m.tool_call_id
    if m.name:
        d["name"] = m.name
    return d


def _dict_to_msg(d: dict) -> Message:
    return Message(
        role=d.get("role", "user"),
        content=d.get("content"),
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )


class ConversationMemory:
    def __init__(self, redis_client: Redis | None = None):
        self._redis = redis_client
        self._store: dict[str, list[dict]] = {}
        self._meta: dict[str, dict] = {}

    async def create_conversation(self, project_id: str, user_id: str, title: str = "") -> str:
        conv_id = str(uuid.uuid4())
        meta = {"project_id": project_id, "user_id": user_id, "title": title}
        if self._redis:
            await self._redis.hset(
                f"{_CONV_PREFIX}{conv_id}",
                mapping={"project_id": project_id, "user_id": user_id, "title": title},
            )
        else:
            self._meta[conv_id] = meta
            self._store[conv_id] = []
        return conv_id

    async def get_history(self, conversation_id: str) -> list[Message]:
        if self._redis:
            raw = await self._redis.lrange(
                f"{_CONV_MSGS_PREFIX}{conversation_id}", 0, -1
            )
            msgs = []
            for item in raw:
                d = json.loads(item)
                msgs.append(_dict_to_msg(d))
            return msgs
        raw = self._store.get(conversation_id, [])
        return [_dict_to_msg(d) for d in raw]

    async def save_message(self, conversation_id: str, message: Message) -> None:
        d = _msg_to_dict(message)
        if self._redis:
            await self._redis.rpush(
                f"{_CONV_MSGS_PREFIX}{conversation_id}", json.dumps(d)
            )
        else:
            if conversation_id not in self._store:
                self._store[conversation_id] = []
            self._store[conversation_id].append(d)

    async def list_conversations(self, project_id: str, user_id: str) -> list[dict]:
        if self._redis:
            pattern = f"{_CONV_PREFIX}{project_id}:{user_id}:*"
            cursor = 0
            keys = []
            while True:
                cursor, batch = await self._redis.scan(cursor, match=pattern)
                keys.extend(batch)
                if cursor == 0:
                    break
            convs = []
            for key in keys:
                data = await self._redis.hgetall(key)
                if data:
                    convs.append(data)
            return convs
        return []

    async def get_conversation(self, project_id: str, user_id: str, conversation_id: str) -> dict | None:
        if self._redis:
            data = await self._redis.hgetall(f"{_CONV_PREFIX}{conversation_id}")
            return data if data else None
        return None

    async def delete_conversation(self, project_id: str, user_id: str, conversation_id: str) -> bool:
        if self._redis:
            await self._redis.delete(f"{_CONV_PREFIX}{conversation_id}")
            await self._redis.delete(f"{_CONV_MSGS_PREFIX}{conversation_id}")
        return True