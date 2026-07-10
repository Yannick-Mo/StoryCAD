"""CriticAgent — reads a chapter and provides structured critique."""
from __future__ import annotations

import json
import logging
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from app.llm.types import Message
from app.agent.context import ContextBuilder
from app.storycad.models import Chapter, Scene, SceneContent

logger = logging.getLogger(__name__)


class CriticOutput(BaseModel):
    scores: dict = Field(default_factory=lambda: {"structure": 0, "pacing": 0, "character": 0, "language": 0})
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    overall: str = ""
    parse_error: bool = False


class CriticAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = LLMClient()
        self.context_builder = ContextBuilder(db)

    async def review_chapter(self, project_id: uuid.UUID, chapter_id: uuid.UUID) -> CriticOutput:
        try:
            ch_result = await self.db.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter = ch_result.scalar_one_or_none()
            if not chapter:
                return CriticOutput(
                    scores={"structure": 0, "pacing": 0, "character": 0, "language": 0}
                )

            full_ctx = await self.context_builder.build_full(project_id)

            scenes_result = await self.db.execute(
                select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sort_order)
            )
            scenes = scenes_result.scalars().all()
            chapter_text_parts = [
                f"## 章节：{chapter.title}\n"
                f"目标：{chapter.goal or '未设定'}\n"
                f"状态：{chapter.status}\n"
            ]
            for sc in scenes:
                cr = await self.db.execute(select(SceneContent).where(SceneContent.scene_id == sc.id))
                content_obj = cr.scalar_one_or_none()
                content = content_obj.content if content_obj else ""
                chapter_text_parts.append(
                    f"\n### 场景：{sc.title}\n"
                    f"POV: {sc.pov_character} | 地点: {sc.setting} | 时间: {sc.scene_time}\n"
                    f"梗概: {sc.summary or '无'}\n"
                    f"正文（{len(content)}字）：\n{content[:3000]}"
                )

            chapter_text = "\n".join(chapter_text_parts)
            project_summary = (
                f"项目：{full_ctx.get('project', {}).get('title', '')} | "
                f"类型：{full_ctx.get('project', {}).get('genre', '')}"
            )

            system_prompt = (
                "你是资深小说编辑。请审阅以下章节，从四个维度评分（0-10）：\n"
                "1. 结构：起承转合是否完整，场景顺序是否合理\n"
                "2. 节奏：叙述节奏是否得当，张弛有度\n"
                "3. 角色：人物塑造是否一致，言行是否符合性格\n"
                "4. 语言：文笔质量，描写是否生动\n\n"
                "输出 JSON 格式：\n"
                "{{\n"
                '    "scores": {{"structure": int, "pacing": int, "character": int, "language": int}},\n'
                '    "strengths": [str],\n'
                '    "weaknesses": [str],\n'
                '    "suggestions": [str],\n'
                '    "overall": str\n'
                "}}"
            )

            user_text = f"{project_summary}\n\n{chapter_text}"

            msgs = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_text),
            ]
            result = await self.client.chat(messages=msgs)
            raw = result.content or ""
            try:
                parsed = json.loads(raw)
                return CriticOutput(**parsed)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to parse critic output: %s", e)
                return CriticOutput(
                    strengths=[],
                    weaknesses=[],
                    suggestions=[],
                    overall=raw,
                    parse_error=True,
                )
        except Exception as e:
            logger.error("CriticAgent review_chapter failed: %s", e)
            return CriticOutput(parse_error=True, overall=str(e))
