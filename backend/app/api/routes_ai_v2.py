import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user
from app.agent.super_agent import SuperAgent

router = APIRouter(prefix="/api/v2", tags=["AI v2"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    mode: str = "chat"

class NewChatRequest(BaseModel):
    title: str = ""


async def _stream_chat(agent: SuperAgent, project_id: str, user_id: str, message: str, conv_id: str | None, mode: str = "chat"):
    async for event in agent.chat_stream(project_id, user_id, message, conv_id, mode=mode):
        yield f"event: {event['type']}\ndata: {event['data']}\n\n"


@router.post("/projects/{project_id}/chat")
async def chat(
    project_id: str,
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = SuperAgent(db)
    return StreamingResponse(
        _stream_chat(agent, project_id, user["id"], req.message, req.conversation_id, req.mode),
        media_type="text/event-stream",
    )


@router.post("/projects/{project_id}/conversations")
async def new_conversation(
    project_id: str,
    req: NewChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = SuperAgent(db)
    conv = await agent.create_conversation(project_id, user["id"], req.title)
    return conv


@router.get("/projects/{project_id}/conversations")
async def list_conversations(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = SuperAgent(db)
    convs = await agent.list_conversations(project_id, user["id"])
    return convs


@router.get("/projects/{project_id}/conversations/{conv_id}")
async def get_conversation(
    project_id: str,
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = SuperAgent(db)
    conv = await agent.get_conversation(project_id, user["id"], conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/projects/{project_id}/conversations/{conv_id}")
async def delete_conversation(
    project_id: str,
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = SuperAgent(db)
    ok = await agent.delete_conversation(project_id, user["id"], conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}
