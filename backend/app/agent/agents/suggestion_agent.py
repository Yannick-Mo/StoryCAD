"""SuggestionAgent — analyzes project state and suggests next writing steps."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.context import ContextBuilder

logger = logging.getLogger(__name__)


@dataclass
class SuggestionResult:
    suggestion_type: str = ""
    priority: str = "medium"
    message: str = ""
    target: dict | None = None
    unwritten_count: int = 0
    success: bool = True
    error: str | None = None


class SuggestionAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_builder = ContextBuilder(db)

    async def suggest_next(self, project_id: uuid.UUID) -> SuggestionResult:
        try:
            full_ctx = await self.context_builder.build_full(project_id)
            acts = full_ctx.get("acts", []) if isinstance(full_ctx, dict) else []
            unwritten: list[dict[str, Any]] = []
            for a in acts:
                for ch in a.get("chapters", []):
                    for s in ch.get("scenes", []):
                        if not s.get("content_preview"):
                            unwritten.append({
                                "act": a.get("name"),
                                "chapter": ch.get("title"),
                                "chapter_id": str(ch.get("id", "")),
                                "scene": s.get("title"),
                                "scene_id": str(s.get("id", "")),
                                "pov": s.get("pov_character"),
                                "setting": s.get("setting"),
                                "summary": s.get("summary"),
                            })

            if unwritten:
                next_scene = unwritten[0]
                return SuggestionResult(
                    suggestion_type="continue_writing",
                    priority="high",
                    message=f"建议继续写{next_scene['act']}→{next_scene['chapter']}→{next_scene['scene']}",
                    target=next_scene,
                    unwritten_count=len(unwritten),
                )

            return SuggestionResult(
                suggestion_type="review",
                priority="medium",
                message="所有场景已写完，建议进行一致性检查或节奏分析",
                unwritten_count=0,
            )
        except Exception as e:
            logger.error("SuggestionAgent.suggest_next failed: %s", e)
            return SuggestionResult(
                success=False,
                error=str(e),
                suggestion_type="error",
            )
