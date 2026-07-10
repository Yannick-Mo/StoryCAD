from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.agent.prompts import render_prompt
from app.agent.state import AgentState
from app.agent.tools import get_tool_descriptions, get_filtered_tools
from app.agent.tools.base import BaseTool
from app.llm.client import LLMClient
from app.llm.types import Message

logger = logging.getLogger(__name__)

MAX_PLAN_STEPS = 10
MAX_ENTITY_CHARS = 4000


def _get_write_tools(tools: dict[str, BaseTool]) -> set[str]:
    return {name for name, inst in tools.items() if inst.is_write_operation}


def _build_entity_context(project_ctx: dict) -> str:
    parts: list[str] = []
    acts = project_ctx.get("acts", [])
    chars = project_ctx.get("characters", [])
    project = project_ctx.get("project", {})
    project_entity_ids: set[str] = set()

    # Collect all valid entity IDs from project context
    if project:
        pid = project.get("id", "")
        project_entity_ids.add(pid)
        parts.append(f"Project ID: {pid}")
        parts.append(f"Title: {project.get('title', '')}")

    if acts:
        parts.append("\nActs & Chapters:")
        for a in acts:
            aid = a.get("id", "")
            project_entity_ids.add(aid)
            parts.append(f"  Act [{aid}]: {a.get('name', '')} (order {a.get('sort_order', '')})")
            for ch in a.get("chapters", []):
                cid = ch.get("id", "")
                project_entity_ids.add(cid)
                parts.append(f"    Chapter [{cid}]: {ch.get('title', '')} (order {ch.get('sort_order', '')})")
                for s in ch.get("scenes", []):
                    sid = s.get("id", "")
                    project_entity_ids.add(sid)
                    parts.append(f"      Scene [{sid}]: {s.get('title', '')}")

    if chars:
        parts.append("\nCharacters:")
        for c in chars:
            cid = c.get("id", "")
            project_entity_ids.add(cid)
            parts.append(f"  [{cid}]: {c.get('name', '')} ({c.get('role', '')})")

    themes = project_ctx.get("themes", [])
    if themes:
        parts.append("\nThemes:")
        for t in themes:
            parts.append(f"  {t.get('name', '')}")

    # Store valid IDs for downstream UUID validation
    entity_text = "\n".join(parts)

    if len(entity_text) > MAX_ENTITY_CHARS:
        truncated: list[str] = []
        for part in parts:
            if sum(len(p) + 1 for p in truncated) + len(part) > MAX_ENTITY_CHARS:
                truncated.append("  ... (truncated)")
                break
            truncated.append(part)
        entity_text = "\n".join(truncated)

    return entity_text


def _validate_step(step: dict, tools: dict[str, BaseTool]) -> list[str]:
    """Validate a single plan step. Returns a list of error messages (empty = valid)."""
    step_errors: list[str] = []
    tool_name = step.get("tool", "")
    params = step.get("params", {})

    if not tool_name:
        step_errors.append("Step missing 'tool' field")
        return step_errors

    inst = tools.get(tool_name)
    if not inst:
        step_errors.append(f"Tool '{tool_name}' not found")
        return step_errors

    schema = inst.parameters
    if not schema:
        return step_errors

    required = schema.get("required", [])
    props = schema.get("properties", {})

    for r in required:
        if r not in params or params[r] is None:
            step_errors.append(f"Step '{tool_name}': missing required param '{r}'")

    for k in params:
        if k not in props:
            step_errors.append(f"Step '{tool_name}': unknown param '{k}'")

    # Validate UUID params look like valid project entities
    for param_name, param_value in params.items():
        if isinstance(param_value, str) and param_name.endswith("_id"):
            try:
                uuid.UUID(param_value)
            except (ValueError, AttributeError):
                step_errors.append(f"Step '{tool_name}': param '{param_name}' is not a valid UUID")

    return step_errors


def create_plan_node(all_tools: dict, llm_client: LLMClient):
    async def plan_node(state: AgentState) -> dict:
        errors: list[str] = list(state.get("errors", []))
        steps: list[dict] = list(state.get("intermediate_steps", []))

        active_skills = state.get("active_skills", [])
        tools = get_filtered_tools(all_tools, active_skills)
        write_tools = _get_write_tools(tools)

        last_msg = state["messages"][-1] if state["messages"] else None
        user_content = last_msg.content if last_msg else ""

        project_ctx = state.get("project_context", {})
        entity_context = _build_entity_context(project_ctx)
        tool_descriptions = get_tool_descriptions(tools)

        retry_ctx = state.get("retry_context")
        rag_text = project_ctx.get("rag_context", "")

        system_text = render_prompt("plan", **{
            "tool_descriptions": tool_descriptions,
            "entity_context": entity_context,
            "rag_context": rag_text[:1500],
            "max_steps": MAX_PLAN_STEPS,
            "retry_context": retry_ctx,
        })
        if not system_text:
            system_text = (
                "You are a task planner. Output valid JSON: "
                '{"steps": [{"tool": "...", "params": {...}, "description": "..."}]}'
            )

        msgs = [
            Message(role="system", content=system_text),
            Message(role="user", content=user_content),
        ]

        try:
            result = await llm_client.chat(
                messages=msgs,
                response_format="json_object",
                temperature=0.2,
                request_id=state.get("trace_id", ""),
            )

            parsed = json.loads(result.content or "{}")
            steps_list = parsed.get("steps", [])
        except Exception as e:
            errors.append(f"Plan generation failed: {e}")
            logger.warning("Plan generation failed: %s", e)
            return {
                "planned_steps": [],
                "current_step_index": 0,
                "current_intent": "simple_q",
                "errors": errors,
            }

        validated: list[dict] = []
        for s in steps_list[:MAX_PLAN_STEPS]:
            step_errors = _validate_step(s, tools)
            if step_errors:
                for err in step_errors:
                    errors.append(err)
                    logger.warning("Plan step validation: %s", err)
                continue
            validated.append(s)

        if not validated:
            return {
                "planned_steps": [],
                "current_step_index": 0,
                "current_intent": "simple_q",
                "errors": errors + ["Plan produced no valid steps"],
            }

        has_write = any(s.get("tool") in write_tools for s in validated)

        return {
            "planned_steps": validated,
            "current_step_index": 0,
            "current_intent": "complex",
            "pending_plan": validated if has_write else [],
            "plan_confirmed": not has_write,
            "retry_context": None,
            "intermediate_steps": steps + [
                {"action": "plan", "steps_count": len(validated), "has_write": has_write}
            ],
        }

    return plan_node
