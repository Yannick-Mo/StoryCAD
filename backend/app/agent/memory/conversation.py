from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from loguru import logger
from redis.asyncio import Redis

from app.llm.types import Message


_CONV_PREFIX = "conv:"
_CONV_META_PREFIX = "conv_meta:"
_CONV_MSGS_PREFIX = "conv_msgs:"
_SET_PREFIX = "conv_set:"
MAX_HISTORY_MESSAGES = 200


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
        self._lock = asyncio.Lock()
        self._store: dict[str, list[dict]] = {}
        self._meta: dict[str, dict] = {}

    async def create_conversation(self, project_id: str, user_id: str, title: str = "") -> str:
        conv_id = str(uuid.uuid4())
        meta = {"project_id": project_id, "user_id": user_id, "title": title}
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.hset(
                f"{_CONV_PREFIX}{conv_id}",
                mapping={"project_id": project_id, "user_id": user_id, "title": title},
            )
            pipe.sadd(f"{_SET_PREFIX}{project_id}:{user_id}", conv_id)
            await pipe.execute()
        else:
            async with self._lock:
                self._meta[conv_id] = meta
                self._store[conv_id] = []
        return conv_id

    async def get_or_create_conversation(self, project_id: str, user_id: str, conversation_id: str | None = None, title: str = "") -> tuple[str, bool]:
        """Return (conversation_id, is_new). Atomic check-and-create."""
        if conversation_id:
            existing = await self.get_conversation(project_id, user_id, conversation_id)
            if existing:
                return conversation_id, False
        cid = await self.create_conversation(project_id, user_id, title)
        return cid, True

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
        async with self._lock:
            raw = self._store.get(conversation_id, [])
        return [_dict_to_msg(d) for d in raw]

    async def save_message(self, conversation_id: str, message: Message) -> None:
        d = _msg_to_dict(message)
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.rpush(f"{_CONV_MSGS_PREFIX}{conversation_id}", json.dumps(d))
            pipe.ltrim(f"{_CONV_MSGS_PREFIX}{conversation_id}", -MAX_HISTORY_MESSAGES, -1)
            pipe.expire(f"{_CONV_MSGS_PREFIX}{conversation_id}", 86400 * 7)
            await pipe.execute()
        else:
            async with self._lock:
                if conversation_id not in self._store:
                    self._store[conversation_id] = []
                self._store[conversation_id].append(d)
                if len(self._store[conversation_id]) > MAX_HISTORY_MESSAGES:
                    self._store[conversation_id] = self._store[conversation_id][-MAX_HISTORY_MESSAGES:]

    async def list_conversations(self, project_id: str, user_id: str) -> list[dict]:
        if self._redis:
            conv_ids = await self._redis.smembers(f"{_SET_PREFIX}{project_id}:{user_id}")
            convs = []
            for cid_bytes in conv_ids:
                cid = cid_bytes.decode() if isinstance(cid_bytes, bytes) else cid_bytes
                data = await self._redis.hgetall(f"{_CONV_PREFIX}{cid}")
                if data:
                    decoded = {}
                    for k, v in data.items():
                        k_str = k.decode() if isinstance(k, bytes) else k
                        v_str = v.decode() if isinstance(v, bytes) else v
                        decoded[k_str] = v_str
                    decoded["id"] = cid
                    convs.append(decoded)
            return convs
        async with self._lock:
            result = []
            for cid, meta in self._meta.items():
                if meta.get("project_id") == project_id and meta.get("user_id") == user_id:
                    result.append({"id": cid, **meta})
            return result

    async def get_conversation(self, project_id: str, user_id: str, conversation_id: str) -> dict | None:
        if self._redis:
            data = await self._redis.hgetall(f"{_CONV_PREFIX}{conversation_id}")
            if data:
                decoded = {}
                for k, v in data.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    decoded[k_str] = v_str
                if decoded.get("project_id") != project_id or decoded.get("user_id") != user_id:
                    return None
                # Include messages for frontend ConversationDetail contract
                messages = await self.get_history(conversation_id)
                decoded["messages"] = [
                    {
                        "id": f"{conversation_id}-{i}",
                        "role": m.role,
                        "content": m.content or "",
                        "created_at": decoded.get("created_at", ""),
                    }
                    for i, m in enumerate(messages)
                ]
                return decoded
            return None
        async with self._lock:
            meta = self._meta.get(conversation_id)
        if meta and meta.get("project_id") == project_id and meta.get("user_id") == user_id:
            messages = await self.get_history(conversation_id)
            meta["messages"] = [
                {
                    "id": f"{conversation_id}-{i}",
                    "role": m.role,
                    "content": m.content or "",
                    "created_at": meta.get("created_at", ""),
                }
                for i, m in enumerate(messages)
            ]
            return meta
        return None

    async def delete_last_message(self, conversation_id: str) -> None:
        if self._redis:
            await self._redis.rpop(f"{_CONV_MSGS_PREFIX}{conversation_id}")
        else:
            async with self._lock:
                if conversation_id in self._store and self._store[conversation_id]:
                    self._store[conversation_id].pop()

    async def delete_conversation(self, project_id: str, user_id: str, conversation_id: str) -> bool:
        if self._redis:
            belongs = await self._redis.sismember(
                f"{_SET_PREFIX}{project_id}:{user_id}", conversation_id
            )
            if not belongs:
                return False
            pipe = self._redis.pipeline()
            pipe.delete(f"{_CONV_PREFIX}{conversation_id}")
            pipe.delete(f"{_CONV_MSGS_PREFIX}{conversation_id}")
            pipe.srem(f"{_SET_PREFIX}{project_id}:{user_id}", conversation_id)
            await pipe.execute()
            return True
        async with self._lock:
            meta = self._meta.get(conversation_id)
        if meta and meta.get("project_id") == project_id and meta.get("user_id") == user_id:
            async with self._lock:
                self._meta.pop(conversation_id, None)
                self._store.pop(conversation_id, None)
            return True
        return False