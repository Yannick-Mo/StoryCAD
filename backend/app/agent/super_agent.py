from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from app.agent.memory.checkpoint import SizeBoundedCheckpointer
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_super_graph
from app.agent.guard import InputGuard, RateLimiter
from app.agent.memory.conversation import ConversationMemory
from app.agent.memory.history_manager import HistoryManager
from app.agent.state import AgentState
from app.llm.client import LLMClient
from app.llm.types import Message

_CHAT_STREAM_TIMEOUT = 60


class SuperAgent:
    def __init__(self, db: AsyncSession, redis_client: Redis | None = None, llm_client: LLMClient | None = None):
        self.db = db
        self.redis_client = redis_client
        self._owns_llm = llm_client is None
        if llm_client is None:
            llm_client = LLMClient()
        self._llm_client = llm_client
        self.graph = build_super_graph(db, llm_client=self._llm_client, redis_client=redis_client)
        self.checkpointer = SizeBoundedCheckpointer(thread_ttl=3600)
        self.app = self.graph.compile(checkpointer=self.checkpointer)
        self.conv_memory = ConversationMemory(redis_client)
        self._history_manager: HistoryManager | None = None
        self.input_guard = InputGuard(rate_limiter=RateLimiter())

    @property
    def history_manager(self) -> HistoryManager:
        if self._history_manager is None:
            self._history_manager = HistoryManager()
        return self._history_manager

    async def chat_stream(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        mode: str = "chat",
        context_view: str | None = None,
        context_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        request_id = str(uuid.uuid4())[:8]
        log = logger.bind(request_id=request_id, project_id=project_id, user_id=user_id)
        log.info("chat_stream start | mode={} | msg_len={}", mode, len(message))

        guard_error = await self.input_guard.async_check(
            message, rate_limit_key=f"{user_id}:{conversation_id or ''}"
        )
        if guard_error:
            log.warning("guard blocked | reason={}", guard_error)
            yield {"type": "error", "data": guard_error}
            return

        if not conversation_id:
            conversation_id = await self.conv_memory.create_conversation(
                project_id, user_id
            )
            log.info("created conversation | conv_id={}", conversation_id)

        config = {"configurable": {"thread_id": conversation_id or str(uuid.uuid4())}}

        history: list[Message] = []
        if self.conv_memory:
            history = await self.conv_memory.get_history(conversation_id)

        if history:
            history = await self.history_manager.maybe_summarize(history)

        messages = list(history)
        messages.append(Message(role="user", content=message))

        project_context: dict = {}
        if context_view:
            project_context["current_view"] = context_view
        if context_id:
            project_context["current_view_id"] = context_id

        initial_state: AgentState = {
            "project_id": project_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "project_context": project_context,
            "messages": messages,
            "current_intent": "simple_q",
            "tool_results": [],
            "tool_calls": [],
            "active_skills": [],
            "mode": mode,
            "intermediate_steps": [],
            "retry_count": 0,
            "max_retries": 3,
            "current_options": [],
            "planned_steps": [],
            "current_step_index": 0,
            "errors": [],
            "pending_plan": [],
            "plan_confirmed": False,
            "retry_context": None,
            "_context_loaded": False,
            "current_node": "",
        }

        if self.conv_memory:
            await self.conv_memory.save_message(
                conversation_id, Message(role="user", content=message)
            )

        yield {"type": "conv_id", "data": conversation_id}

        assistant_content = ""
        _done_sent = False
        _last_token_time = time.monotonic()

        try:
            async with asyncio.timeout(_CHAT_STREAM_TIMEOUT):
                async for event in self.app.astream_events(
                    initial_state, config, version="v2"
                ):
                    _last_token_time = time.monotonic()
                    if event["event"] == "on_chain_start":
                        node = event.get("metadata", {}).get("langgraph_node", "")
                        if node:
                            log.debug("node_start | node={}", node)
                            label = {
                                "load_full_context": "读取项目数据...",
                                "classify_intent": "理解你的意图...",
                                "execute_tool": "执行分析...",
                                "generate": "生成回复...",
                                "plan": "制定计划...",
                            }.get(node, f"正在{node}...")
                            yield {"type": "step", "data": label}
                    elif event["event"] == "on_chain_stream":
                        chunk = event["data"]["chunk"]
                        if isinstance(chunk, dict):
                            token = chunk.get("_stream_token")
                            if token:
                                assistant_content += token
                                yield {"type": "token", "data": token}
                                continue
                            if chunk.get("_stream_done"):
                                _done_sent = True
        except asyncio.TimeoutError:
            log.warning("timeout | conv_id={}", conversation_id)
            if self.conv_memory:
                await self.conv_memory.delete_last_message(conversation_id)
            yield {"type": "error", "data": json.dumps({"message": "Request timed out. Please try again."})}
            return
        except Exception as exc:
            log.error("graph_execution_error | error_type={} | error={}", type(exc).__name__, exc, exc_info=True)
            raise

        try:
            final_state = await self.app.aget_state(config)
            if final_state and final_state.values:
                values = final_state.values

                tool_results = values.get("tool_results", [])
                # Only show real tool executions — skip internal metadata results
                visible_results = [tr for tr in tool_results if tr.get("tool") not in ("cowriter_analysis",)]
                for tr in visible_results:
                    yield {"type": "tool_done", "data": json.dumps(tr, ensure_ascii=False)}

                options = values.get("current_options", [])
                if options:
                    yield {"type": "option", "data": json.dumps(options, ensure_ascii=False)}

                pending_plan = values.get("pending_plan", [])
                plan_confirmed = values.get("plan_confirmed", False)
                if pending_plan and not plan_confirmed:
                    yield {
                        "type": "plan",
                        "data": json.dumps(
                            {
                                "steps": pending_plan,
                                "status": "awaiting_confirmation",
                            },
                            ensure_ascii=False,
                        ),
                    }

                # Only emit project_updated when actual write tools ran, not for analysis-only passes
                write_tools_executed = [tr.get("tool") for tr in visible_results if tr.get("success")]
                if write_tools_executed:
                    yield {
                        "type": "project_updated",
                        "data": json.dumps(
                            {
                                "tools_executed": write_tools_executed,
                                "all_success": all(tr.get("success", True) for tr in visible_results),
                            },
                            ensure_ascii=False,
                        ),
                    }
        except Exception as exc:
            log.error("final_state_error | error={}", exc)

        if not _done_sent:
            _done_sent = True
        yield {"type": "done", "data": ""}

        if assistant_content and self.conv_memory:
            await self.conv_memory.save_message(
                conversation_id, Message(role="assistant", content=assistant_content)
            )

        log.info("chat_stream done | tokens={}", len(assistant_content))

    async def create_conversation(self, project_id: str, user_id: str, title: str = "") -> str:
        return await self.conv_memory.create_conversation(project_id, user_id, title)

    async def list_conversations(self, project_id: str, user_id: str) -> list[dict]:
        return await self.conv_memory.list_conversations(project_id, user_id)

    async def get_conversation(self, project_id: str, user_id: str, conversation_id: str) -> dict | None:
        return await self.conv_memory.get_conversation(project_id, user_id, conversation_id)

    async def delete_conversation(self, project_id: str, user_id: str, conversation_id: str) -> bool:
        return await self.conv_memory.delete_conversation(project_id, user_id, conversation_id)

    async def close(self) -> None:
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as exc:
                logger.warning("Error closing Redis connection: %s", exc)
        if self._owns_llm and self._llm_client is not None:
            try:
                await self._llm_client.close()
            except Exception as exc:
                logger.warning("Error closing LLM client: %s", exc)


def get_super_agent(
    db: AsyncSession, redis: Redis | None = None
) -> SuperAgent:
    return SuperAgent(db, redis)
