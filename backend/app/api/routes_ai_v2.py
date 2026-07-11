from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, field_validator
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.super_agent import SuperAgent
from app.api.deps import get_db, get_current_user, get_redis
from app.llm.client import get_shared_client, get_tracker
from app.project.repository import ProjectRepository

router = APIRouter(prefix="/api/v2", tags=["AI v2"])

SSE_PING_INTERVAL = 15


async def _verify_project_owner(db: AsyncSession, project_id: uuid.UUID, user: dict) -> None:
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project or str(project.owner_id) != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")


def _format_sse(event: str, data: str) -> str:
    """Format an SSE event, properly encoding newlines in data.

    SSE requires multi-line data to be split across multiple 'data:' lines.
    Single-line encoding breaks when data contains \\n characters.
    """
    lines = data.split('\n')
    out = f"event: {event}\n"
    for line in lines:
        out += f"data: {line}\n"
    out += "\n"
    return out


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    mode: str = "chat"
    context_view: str | None = None
    context_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be empty")
        return v


class NewChatRequest(BaseModel):
    title: str = ""


async def _stream_chat(
    project_id: str,
    user_id: str,
    message: str,
    conv_id: str | None,
    mode: str = "chat",
    context_view: str | None = None,
    context_id: str | None = None,
    agent: SuperAgent | None = None,
    request: Request | None = None,
) -> AsyncGenerator[str, None]:
    yield "retry: 3000\n\n"

    queue: asyncio.Queue = asyncio.Queue(maxsize=128)

    async def _run_chat():
        try:
            async for event in agent.chat_stream(project_id, user_id, message, conv_id, mode=mode, context_view=context_view, context_id=context_id):
                await queue.put(("event", event))
        except BaseException as exc:
            await queue.put(("error", exc))
        finally:
            await queue.put(("done", None))

    chat_task = asyncio.create_task(_run_chat())

    try:
        while True:
            if request is not None and await request.is_disconnected():
                break
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=SSE_PING_INTERVAL)
            except asyncio.TimeoutError:
                if request is not None and await request.is_disconnected():
                    break
                yield "event: ping\ndata: {}\n\n"
                continue

            if kind == "done":
                break
            if kind == "error":
                raise payload
            if kind == "event":
                if request is not None and await request.is_disconnected():
                    break
                yield _format_sse(payload['type'], payload['data'])
    except BaseException as exc:
        logger.error("AI chat error: {}", exc, exc_info=True)
        yield f"event: error\ndata: {json.dumps({'message': 'Internal error', 'detail': 'An unexpected error occurred'})}\n\n"
    finally:
        chat_task.cancel()


@router.post("/projects/{project_id}/chat")
async def chat(
    project_id: uuid.UUID,
    req: ChatRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    await _verify_project_owner(db, project_id, user)
    llm_client = get_shared_client()
    agent = SuperAgent(db=db, redis_client=redis_client, llm_client=llm_client)
    return StreamingResponse(
        _stream_chat(str(project_id), user["id"], req.message, req.conversation_id, req.mode, context_view=req.context_view, context_id=req.context_id, agent=agent, request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/projects/{project_id}/conversations")
async def new_conversation(
    project_id: uuid.UUID,
    req: NewChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    await _verify_project_owner(db, project_id, user)
    llm_client = get_shared_client()
    agent = SuperAgent(db=db, redis_client=redis_client, llm_client=llm_client)
    conv = await agent.create_conversation(str(project_id), user["id"], req.title)
    return {"conversation_id": conv, "project_id": str(project_id), "title": req.title}


@router.get("/projects/{project_id}/conversations")
async def list_conversations(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    await _verify_project_owner(db, project_id, user)
    llm_client = get_shared_client()
    agent = SuperAgent(db=db, redis_client=redis_client, llm_client=llm_client)
    convs = await agent.list_conversations(str(project_id), user["id"])
    return {"conversations": convs}


@router.get("/projects/{project_id}/conversations/{conv_id}")
async def get_conversation(
    project_id: uuid.UUID,
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    await _verify_project_owner(db, project_id, user)
    llm_client = get_shared_client()
    agent = SuperAgent(db=db, redis_client=redis_client, llm_client=llm_client)
    conv = await agent.get_conversation(str(project_id), user["id"], conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/projects/{project_id}/conversations/{conv_id}")
async def delete_conversation(
    project_id: uuid.UUID,
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    await _verify_project_owner(db, project_id, user)
    llm_client = get_shared_client()
    agent = SuperAgent(db=db, redis_client=redis_client, llm_client=llm_client)
    ok = await agent.delete_conversation(str(project_id), user["id"], conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.get("/usage")
async def get_usage(user: dict = Depends(get_current_user)):
    """Get global token usage statistics."""
    return get_tracker().get_global_total()


@router.get("/usage/session/{session_id}")
async def get_session_usage(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
):
    """Get token usage for a specific session."""
    # TODO: Validate session ownership once TokenTracker tracks user_id
    return get_tracker().get_session_total(str(session_id))
