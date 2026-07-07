import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult
from app.project.models import Project, ProjectConfig
from app.storycad.models import Chapter, Scene, SceneContent
from app.storycad.repository import StoryCADRepository
from app.project.repository import ProjectRepository
from app.utils import row_to_dict


class ReadProjectTool(BaseTool):
    name = "read_project"
    description = "加载完整项目上下文，包括标题、体裁、描述和配置"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            pid = uuid.UUID(kwargs["project_id"])
            proj_repo = ProjectRepository(db)
            project = await proj_repo.get(pid)
            if not project:
                return ToolResult(success=False, error="Project not found")
            config = await proj_repo.get_config(pid)
            data = row_to_dict(project)
            if config:
                data["config"] = row_to_dict(config)
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ReadChapterTool(BaseTool):
    name = "read_chapter"
    description = "获取章节及其场景列表"
    parameters = {
        "type": "object",
        "properties": {
            "chapter_id": {"type": "string", "description": "章节ID"},
        },
        "required": ["chapter_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            ch_id = uuid.UUID(kwargs["chapter_id"])
            result = await db.execute(select(Chapter).where(Chapter.id == ch_id))
            chapter = result.scalar_one_or_none()
            if not chapter:
                return ToolResult(success=False, error="Chapter not found")
            scenes_result = await db.execute(
                select(Scene).where(Scene.chapter_id == ch_id).order_by(Scene.sort_order)
            )
            scenes = [row_to_dict(s) for s in scenes_result.scalars().all()]
            data = row_to_dict(chapter)
            data["scenes"] = scenes
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ReadSceneTool(BaseTool):
    name = "read_scene"
    description = "获取场景内容，包括 SceneContent"
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
        },
        "required": ["scene_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene = result.scalar_one_or_none()
            if not scene:
                return ToolResult(success=False, error="Scene not found")
            content_result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc_content = content_result.scalar_one_or_none()
            data = row_to_dict(scene)
            data["content"] = sc_content.content if sc_content else ""
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CreateSceneTool(BaseTool):
    name = "create_scene"
    description = "在指定章节中创建新场景"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "chapter_id": {"type": "string", "description": "所属章节ID"},
            "title": {"type": "string", "description": "场景标题"},
            "sort_order": {"type": "integer", "description": "排序序号"},
            "summary": {"type": "string", "description": "场景梗概"},
            "content": {"type": "string", "description": "场景正文"},
            "pov_character": {"type": "string", "description": "POV角色"},
            "setting": {"type": "string", "description": "场景地点"},
            "scene_time": {"type": "string", "description": "场景时间"},
        },
        "required": ["project_id", "chapter_id", "title"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            pid = uuid.UUID(kwargs["project_id"])
            ch_id = uuid.UUID(kwargs["chapter_id"])
            repo = StoryCADRepository(db)
            scene_data = {
                "project_id": str(pid),
                "chapter_id": str(ch_id),
                "title": kwargs.get("title", "新场景"),
                "sort_order": kwargs.get("sort_order", 0),
                "summary": kwargs.get("summary", ""),
                "pov_character": kwargs.get("pov_character", ""),
                "setting": kwargs.get("setting", ""),
                "scene_time": kwargs.get("scene_time", ""),
            }
            content = kwargs.get("content")
            created = await repo.create_entity(Scene, scene_data)
            if content:
                sc_id = uuid.UUID(created["id"])
                db.add(SceneContent(scene_id=sc_id, project_id=pid, content=content))
                await db.flush()
            from app.agent.utils import count_words
            if content:
                word_count = count_words(content)
                result = await db.execute(select(Scene).where(Scene.id == uuid.UUID(created["id"])))
                scene_obj = result.scalar_one_or_none()
                if scene_obj:
                    scene_obj.word_count = word_count
                await db.flush()
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateSceneTool(BaseTool):
    name = "update_scene"
    description = "更新场景内容、标题、POV、地点、时间、梗概等"
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "title": {"type": "string", "description": "场景标题"},
            "summary": {"type": "string", "description": "场景梗概"},
            "content": {"type": "string", "description": "场景正文"},
            "pov_character": {"type": "string", "description": "POV角色"},
            "setting": {"type": "string", "description": "场景地点"},
            "scene_time": {"type": "string", "description": "场景时间"},
        },
        "required": ["scene_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            sc_id = uuid.UUID(kwargs["scene_id"])
            repo = StoryCADRepository(db)
            update_data = {"id": str(sc_id)}
            for field in ("title", "summary", "pov_character", "setting", "scene_time"):
                if field in kwargs:
                    update_data[field] = kwargs[field]
            updated = await repo.update_entity(Scene, update_data)
            if not updated:
                return ToolResult(success=False, error="Scene not found")
            if "content" in kwargs:
                content = kwargs["content"]
                result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
                sc = result.scalar_one_or_none()
                if sc:
                    sc.content = content
                else:
                    result = await db.execute(select(Scene).where(Scene.id == sc_id))
                    scene_obj = result.scalar_one_or_none()
                    if scene_obj:
                        db.add(SceneContent(scene_id=sc_id, project_id=scene_obj.project_id, content=content))
                from app.agent.utils import count_words
                word_count = count_words(content)
                result = await db.execute(select(Scene).where(Scene.id == sc_id))
                scene_obj = result.scalar_one_or_none()
                if scene_obj:
                    scene_obj.word_count = word_count
                await db.flush()
            await db.commit()
            return ToolResult(success=True, data=updated)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))
