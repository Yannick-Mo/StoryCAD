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

    @staticmethod
    def _extract_changes(tool_call: dict) -> dict:
        """Extract meaningful change details from a tool call's parameters.
        Filters out internal routing keys and empty values."""
        skip_keys = {"project_id", "user_id", "conversation_id", "id"}
        changes = {}
        for key, value in tool_call.get("parameters", {}).items():
            if key not in skip_keys and value is not None and value != "":
                changes[key] = str(value)[:200]  # truncate long values
        return changes

    async def _emit_tool_events(self, final_values: dict):
        """Yield tool_done, option, plan, and project_updated events from final state."""
        tool_results = final_values.get("tool_results", [])
        visible_results = [tr for tr in tool_results if tr.get("tool") not in ("cowriter_analysis",)]
        for tr in visible_results:
            yield {"type": "tool_done", "data": json.dumps(tr, ensure_ascii=False)}

        options = final_values.get("current_options", [])
        if options:
            yield {"type": "option", "data": json.dumps(options, ensure_ascii=False)}

        raw_pending_plan = final_values.get("pending_plan", [])
        plan_confirmed = final_values.get("plan_confirmed", False)
        if raw_pending_plan and not plan_confirmed:
            if isinstance(raw_pending_plan, dict):
                steps = raw_pending_plan.get("steps", [])
                extra = {k: v for k, v in raw_pending_plan.items() if k != "steps"}
            else:
                steps = raw_pending_plan
                extra = {}
            yield {
                "type": "plan",
                "data": json.dumps(
                    {
                        "steps": steps,
                        "status": "awaiting_confirmation",
                        **extra,
                    },
                    ensure_ascii=False,
                ),
            }

        write_tools = [tr.get("tool") for tr in visible_results if tr.get("success")]
        if write_tools:
            # Build detailed tool info with parameter changes
            tool_details = []
            for tr in visible_results:
                if tr.get("success"):
                    tool_call = tr.get("tool_call", {})
                    if isinstance(tool_call, dict):
                        changes = self._extract_changes(tool_call)
                    else:
                        changes = {}
                    tool_details.append({
                        "name": tr.get("tool", "unknown"),
                        "changes": changes,
                    })
            
            yield {
                "type": "project_updated",
                "data": json.dumps(
                    {
                        "tools_executed": write_tools,
                        "tool_details": tool_details,
                        "all_success": all(tr.get("success", True) for tr in visible_results),
                    },
                    ensure_ascii=False,
                ),
            }

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

        config = {"configurable": {"thread_id": conversation_id}}

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
            "trace_id": request_id,
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
            "search_results": [],
            "_context_loaded": False,
        }

        await self.conv_memory.save_message(
            conversation_id, Message(role="user", content=message)
        )

        yield {"type": "conv_id", "data": conversation_id}

        assistant_content = ""
        _done_sent = False
        _last_token_time = time.monotonic()

        # Phase 1: Buffer tokens during graph execution
        token_buffer: list[str] = []
        final_values: dict | None = None

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
                                token_buffer.append(token)
                                continue
                            if chunk.get("_stream_done"):
                                _done_sent = True
                    elif event["event"] == "on_chain_end":
                        output = event["data"].get("output")
                        if isinstance(output, dict):
                            # Capture any meaningful final state, not just when project_context present
                            if "project_context" in output or "messages" in output:
                                final_values = output
        except asyncio.TimeoutError:
            log.warning("timeout | conv_id={}", conversation_id)
            await self.conv_memory.delete_last_message(conversation_id)
            yield {"type": "error", "data": json.dumps({"message": "Request timed out. Please try again."})}
            return
        except Exception as exc:
            log.error("graph_execution_error | error_type={} | error={}", type(exc).__name__, exc, exc_info=True)
            raise

        # Phase 2: Get final state if not captured from stream
        if final_values is None:
            try:
                state = await self.app.aget_state(config)
                if state and state.values:
                    final_values = state.values
            except Exception as exc:
                log.error("final_state_error | error={}", exc, exc_info=True)
                yield {"type": "error", "data": json.dumps({"message": "Failed to get final state"})}

        # Phase 3: Emit tool results before response
        if final_values:
            async for evt in self._emit_tool_events(final_values):
                yield evt

        # Phase 4: Flush buffered response tokens
        if token_buffer:
            assistant_content = "".join(token_buffer)
            for token in token_buffer:
                yield {"type": "token", "data": token}
        elif final_values:
            messages = final_values.get("messages", [])
            if messages:
                content = messages[-1].get("content", "")
                if content:
                    assistant_content = content
                    yield {"type": "token", "data": content}

        if not _done_sent:
            _done_sent = True
        yield {"type": "done", "data": ""}

        if assistant_content:
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
