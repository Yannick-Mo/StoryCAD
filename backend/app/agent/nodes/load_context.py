from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from app.agent.context import ContextBuilder
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def create_load_context_node(context_builder: ContextBuilder):
    async def load_full_context_node(state: AgentState) -> dict:
        project_id = state.get("project_id")
        if not project_id:
            return {"project_context": {}, "_context_loaded": False}

        messages = state.get("messages", [])
        query_hint = ""
        for m in reversed(messages):
            if m.role == "user" and m.content:
                query_hint = m.content[:200]
                break

        current_intent = state.get("current_intent", "simple_q")

        try:
            # Use build_full for writing/analysis intents; build_summary for simple queries
            detailed_intents = {"tool_call", "cowriter", "complex", "plan_confirm"}
            needs_detail = current_intent in detailed_intents

            if needs_detail:
                ctx = await context_builder.build_full(
                    uuid.UUID(project_id), query_hint=query_hint
                )
            else:
                ctx = await context_builder.build_summary(
                    uuid.UUID(project_id), query_hint=query_hint, depth="minimal"
                )

            return {
                "project_context": ctx,
                "_context_loaded": True,
            }
        except Exception as e:
            logger.error("Context load failed for %s: %s", project_id, e)
            return {
                "project_context": {
                    "project": {"id": str(project_id)},
                    "error": str(e),
                },
                "_context_loaded": False,
                "errors": state.get("errors", []) + [f"Context load failed: {e}"],
            }

    return load_full_context_node
