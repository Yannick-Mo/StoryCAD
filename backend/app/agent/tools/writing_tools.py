from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult, verify_project_owner
from app.storycad.models import Scene, SceneContent
from app.agent.utils import count_words


class WriteSceneContentTool(BaseTool):
    name = "write_scene_content"
    description = "写入场景正文内容，更新场景字数"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "content": {"type": "string", "description": "场景正文内容"},
        },
        "required": ["scene_id", "content"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            content = kwargs["content"]
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if not scene_obj:
                return ToolResult(success=False, error="Scene not found")
            await verify_project_owner(db, scene_obj.project_id, kwargs.get("user_id"))
            result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc = result.scalar_one_or_none()
            if sc:
                sc.content = content
            else:
                db.add(SceneContent(scene_id=sc_id, project_id=scene_obj.project_id, content=content))
            wc = count_words(content)
            scene_obj.word_count = wc
            await db.commit()
            return ToolResult(success=True, data={"scene_id": str(sc_id), "word_count": wc, "content_preview": content[:200]})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class ContinueSceneTool(BaseTool):
    name = "continue_scene"
    description = "基于前文风格分析，续写场景内容（追加到已有内容后）"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "additional_content": {"type": "string", "description": "续写的内容"},
        },
        "required": ["scene_id", "additional_content"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            additional = kwargs["additional_content"]
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if not scene_obj:
                return ToolResult(success=False, error="Scene not found")
            await verify_project_owner(db, scene_obj.project_id, kwargs.get("user_id"))
            result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc = result.scalar_one_or_none()
            existing = sc.content if sc else ""
            new_content = existing + ("\n\n" if existing else "") + additional
            writer = WriteSceneContentTool()
            return await writer.run(db, user_id=kwargs.get("user_id"), scene_id=str(sc_id), content=new_content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RewriteSceneTool(BaseTool):
    name = "rewrite_scene"
    description = "以指定风格或要求重写场景内容"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "content": {"type": "string", "description": "重写后的内容"},
            "style": {"type": "string", "description": "风格说明（更悬疑/更简洁/更有张力等）"},
        },
        "required": ["scene_id", "content"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            content = kwargs["content"]
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if not scene_obj:
                return ToolResult(success=False, error="Scene not found")
            await verify_project_owner(db, scene_obj.project_id, kwargs.get("user_id"))
            writer = WriteSceneContentTool()
            return await writer.run(db, user_id=kwargs.get("user_id"), scene_id=str(sc_id), content=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ExpandSelectionTool(BaseTool):
    name = "expand_selection"
    description = "扩写指定段落，保持风格一致"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "original_text": {"type": "string", "description": "原始文本（用于定位）"},
            "expanded_text": {"type": "string", "description": "扩写后的完整段落"},
        },
        "required": ["scene_id", "original_text", "expanded_text"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            original = kwargs["original_text"]
            expanded = kwargs["expanded_text"]
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if not scene_obj:
                return ToolResult(success=False, error="Scene not found")
            await verify_project_owner(db, scene_obj.project_id, kwargs.get("user_id"))
            result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc = result.scalar_one_or_none()
            if not sc:
                return ToolResult(success=False, error="Scene content not found")
            if original not in sc.content:
                return ToolResult(
                    success=False,
                    error="AI output did not match the selected text in the scene. The original text could not be found in the current content.",
                )
            new_content = sc.content.replace(original, expanded, 1)
            writer = WriteSceneContentTool()
            return await writer.run(db, user_id=kwargs.get("user_id"), scene_id=str(sc_id), content=new_content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CompressSelectionTool(BaseTool):
    name = "compress_selection"
    description = "压缩指定段落，保持关键信息"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "original_text": {"type": "string", "description": "原始文本"},
            "compressed_text": {"type": "string", "description": "压缩后的文本"},
        },
        "required": ["scene_id", "original_text", "compressed_text"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            original = kwargs["original_text"]
            compressed = kwargs["compressed_text"]
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if not scene_obj:
                return ToolResult(success=False, error="Scene not found")
            await verify_project_owner(db, scene_obj.project_id, kwargs.get("user_id"))
            result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc = result.scalar_one_or_none()
            if not sc:
                return ToolResult(success=False, error="Scene content not found")
            if original not in sc.content:
                return ToolResult(
                    success=False,
                    error="AI output did not match the selected text in the scene. The original text could not be found in the current content.",
                )
            new_content = sc.content.replace(original, compressed, 1)
            writer = WriteSceneContentTool()
            return await writer.run(db, user_id=kwargs.get("user_id"), scene_id=str(sc_id), content=new_content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
