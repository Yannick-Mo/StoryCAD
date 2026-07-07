import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import AgentState
from app.agent.graph import build_super_graph
from app.agent.memory.conversation import ConversationMemory
from app.agent.memory.project import ProjectMemory
from app.agent.context import ContextBuilder
from app.llm.types import Message


class SuperAgent:
    def __init__(self, db: AsyncSession, redis_client: Redis | None = None):
        self.db = db
        self.graph = build_super_graph(db)
        self.checkpointer = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
        self.conv_memory = ConversationMemory(redis_client) if redis_client else None
        self.proj_memory = ProjectMemory(redis_client) if redis_client else None

    async def chat_stream(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        mode: str = "chat",
    ) -> AsyncGenerator[dict, None]:
        if not conversation_id and self.conv_memory:
            conversation_id = await self.conv_memory.create_conversation(
                project_id, user_id
            )

        project_context = await self._load_project_context(project_id)

        history: list[Message] = []
        if conversation_id and self.conv_memory:
            history = await self.conv_memory.get_history(conversation_id)

        messages = list(history)
        messages.append(Message(role="user", content=message))

        initial_state: AgentState = {
            "project_id": project_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "project_context": project_context,
            "messages": messages,
            "current_intent": "",
            "tool_results": [],
            "active_skills": project_context.get("active_skills", []),
            "rag_context": project_context.get("rag_context", []),
            "sub_agent_results": {},
            "mode": mode,
            "pending_actions": [],
            "intermediate_steps": [],
        }

        config = {
            "configurable": {"thread_id": conversation_id or str(uuid.uuid4())}
        }

        events_buffer: list[dict] = []

        yield {"type": "conv_id", "data": conversation_id}

        async for event in self.app.astream_events(
            initial_state, config, version="v1"
        ):
            if event["event"] == "on_node_start":
                yield {"type": "step", "data": f"正在{event['name']}..."}
            elif event["event"] == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield {"type": "token", "data": content}
            elif event["event"] == "on_node_end":
                if event["name"] == "generate":
                    yield {"type": "done", "data": ""}
            events_buffer.append(event)
            await self.conv_memory.save_message(
                conversation_id, Message(role="user", content=message)
            )
            assistant_content = ""
            for event in events_buffer:
                if event["type"] == "token":
                    assistant_content += event["data"]
            if assistant_content:
                await self.conv_memory.save_message(
                    conversation_id, Message(role="assistant", content=assistant_content)
                )

    async def _load_project_context(self, project_id: str) -> dict:
        from app.project.models import Project, ProjectConfig
        from sqlalchemy import select

        ctx: dict = {}
        r = await self.db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        proj = r.scalar_one_or_none()
        if not proj:
            return ctx

        ctx["project_title"] = proj.title
        ctx["genre"] = proj.genre or "未指定"
        ctx["description"] = proj.description or ""

        r = await self.db.execute(
            select(ProjectConfig).where(
                ProjectConfig.project_id == uuid.UUID(project_id)
            )
        )
        config = r.scalar_one_or_none()
        ctx["total_words"] = config.total_words if config else 100000

        from app.knowledge.skill_engine import SkillEngine
        from app.knowledge.rag import RAGEngine

        skill_engine = SkillEngine(self.db)
        ctx["active_skills"] = await skill_engine.get_active_skills(project_id)

        rag = RAGEngine(self.db)
        ctx["rag_context"] = await rag.retrieve_context(
            project_id=None,
            genre=proj.genre or "",
            query=f"{proj.genre or ''} 创作指南 写作技巧",
        )

        return ctx


def get_super_agent(
    db: AsyncSession, redis: Redis | None = None
) -> SuperAgent:
    return SuperAgent(db, redis)
