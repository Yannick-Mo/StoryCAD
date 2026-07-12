from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult, ToolMeta, ConcurrencyMode, verify_project_owner
from app.project.models import Project, ProjectConfig
from app.storycad.models import Act, Chapter, Scene, SceneContent
from app.storycad.repository import StoryCADRepository
from app.project.repository import ProjectRepository
from app.utils import row_to_dict


class ReadProjectTool(BaseTool):
    meta = ToolMeta(
        name="read_project",
        description="加载完整项目上下文，包括标题、体裁、描述和配置",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="read project context config",
    )
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
            await verify_project_owner(db, pid, kwargs.get("user_id"))
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
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class CreateSceneTool(BaseTool):
    meta = ToolMeta(
        name="read_chapter",
        description="获取章节及其场景列表",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="read chapter scenes list",
    )
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
            await verify_project_owner(db, chapter.project_id, kwargs.get("user_id"))
            scenes_result = await db.execute(
                select(Scene).where(Scene.chapter_id == ch_id).order_by(Scene.sort_order)
            )
            scenes = [row_to_dict(s) for s in scenes_result.scalars().all()]
            data = row_to_dict(chapter)
            data["scenes"] = scenes
            return ToolResult(success=True, data=data)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class ReadSceneTool(BaseTool):
    meta = ToolMeta(
        name="read_scene",
        description="获取场景内容，包括 SceneContent",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="read scene content detail",
    )
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
            await verify_project_owner(db, scene.project_id, kwargs.get("user_id"))
            content_result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sc_id))
            sc_content = content_result.scalar_one_or_none()
            data = row_to_dict(scene)
            data["content"] = sc_content.content if sc_content else ""
            return ToolResult(success=True, data=data)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class ReadChapterTool(BaseTool):
    meta = ToolMeta(
        name="create_scene",
        description="在指定章节中创建新场景",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        search_hint="create scene new",
    )
    name = "create_scene"
    description = "在指定章节中创建新场景"
    is_write_operation = True
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
            await verify_project_owner(db, pid, kwargs.get("user_id"))
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
                from app.agent.utils import count_words
                word_count = count_words(content)
                scene_obj = await db.get(Scene, sc_id)
                if scene_obj:
                    scene_obj.word_count = word_count
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateSceneTool(BaseTool):
    meta = ToolMeta(
        name="update_scene",
        description="更新场景内容、标题、POV、地点、时间、梗概等",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        search_hint="update scene modify edit",
    )
    name = "update_scene"
    description = "更新场景内容、标题、POV、地点、时间、梗概等"
    is_write_operation = True
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
            scene_result = await db.get(Scene, sc_id)
            if scene_result:
                await verify_project_owner(db, scene_result.project_id, kwargs.get("user_id"))
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
                scene_obj = await db.get(Scene, sc_id)
                if sc:
                    sc.content = content
                elif scene_obj:
                    db.add(SceneContent(scene_id=sc_id, project_id=scene_obj.project_id, content=content))
                if scene_obj:
                    from app.agent.utils import count_words
                    scene_obj.word_count = count_words(content)
            await db.commit()
            return ToolResult(success=True, data=updated)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class ReadFullProjectTool(BaseTool):
    meta = ToolMeta(
        name="read_full_project",
        description="加载完整项目上下文，包括所有幕、章节、场景、角色、关系、主题",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="read full project complete context",
    )
    name = "read_full_project"
    description = "加载完整项目上下文，包括所有幕、章节、场景、角色、关系、主题"
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
            await verify_project_owner(db, pid, kwargs.get("user_id"))
            from app.agent.context import ContextBuilder
            builder = ContextBuilder(db)
            ctx = await builder.build_full(pid)
            return ToolResult(success=True, data=ctx)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SetChapterGoalTool(BaseTool):
    meta = ToolMeta(
        name="set_chapter_goal",
        description="设置章节的写作目标",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        search_hint="set chapter goal objective",
    )
    name = "set_chapter_goal"
    description = "设置章节的写作目标"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "chapter_id": {"type": "string", "description": "章节ID"},
            "goal": {"type": "string", "description": "章节目标文本"},
        },
        "required": ["chapter_id", "goal"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            ch_id = uuid.UUID(kwargs["chapter_id"])
            goal = kwargs["goal"]
            result = await db.execute(select(Chapter).where(Chapter.id == ch_id))
            ch = result.scalar_one_or_none()
            if ch:
                await verify_project_owner(db, ch.project_id, kwargs.get("user_id"))
            if not ch:
                return ToolResult(success=False, error="Chapter not found")
            ch.goal = goal
            await db.commit()
            return ToolResult(success=True, data={"chapter_id": str(ch_id), "goal": goal})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateChapterTool(BaseTool):
    meta = ToolMeta(
        name="update_chapter",
        description="更新章节信息（标题、状态、目标）",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        search_hint="update chapter modify edit",
    )
    name = "update_chapter"
    description = "更新章节信息（标题、状态、目标）"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "chapter_id": {"type": "string", "description": "章节ID"},
            "title": {"type": "string", "description": "章节标题"},
            "status": {"type": "string", "description": "状态（draft/revising/final）"},
            "goal": {"type": "string", "description": "章节目标"},
        },
        "required": ["chapter_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            ch_id = uuid.UUID(kwargs["chapter_id"])
            result = await db.execute(select(Chapter).where(Chapter.id == ch_id))
            ch = result.scalar_one_or_none()
            if not ch:
                return ToolResult(success=False, error="Chapter not found")
            await verify_project_owner(db, ch.project_id, kwargs.get("user_id"))
            if "title" in kwargs:
                ch.title = kwargs["title"]
            if "status" in kwargs:
                valid_statuses = {"draft", "revising", "final"}
                if kwargs["status"] not in valid_statuses:
                    return ToolResult(
                        success=False,
                        error=f"Invalid status '{kwargs['status']}'. Must be one of {valid_statuses}",
                    )
                ch.status = kwargs["status"]
            if "goal" in kwargs:
                ch.goal = kwargs["goal"]
            await db.commit()
            return ToolResult(success=True, data={"chapter_id": str(ch_id), "title": ch.title, "status": ch.status})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateActTool(BaseTool):
    meta = ToolMeta(
        name="update_act",
        description="更新幕信息（名称、颜色）",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        search_hint="update act modify edit",
    )
    name = "update_act"
    description = "更新幕信息（名称、颜色）"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "act_id": {"type": "string", "description": "幕ID"},
            "name": {"type": "string", "description": "幕名称"},
            "color": {"type": "string", "description": "颜色代码"},
        },
        "required": ["act_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            act_id = uuid.UUID(kwargs["act_id"])
            result = await db.execute(select(Act).where(Act.id == act_id))
            act = result.scalar_one_or_none()
            if not act:
                return ToolResult(success=False, error="Act not found")
            await verify_project_owner(db, act.project_id, kwargs.get("user_id"))
            if "name" in kwargs:
                act.name = kwargs["name"]
            if "color" in kwargs:
                act.color = kwargs["color"]
            await db.commit()
            return ToolResult(success=True, data={"act_id": str(act_id), "name": act.name})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))
