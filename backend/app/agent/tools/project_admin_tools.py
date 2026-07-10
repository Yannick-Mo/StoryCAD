from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.project.models import Project, ProjectConfig
from app.storycad.models import Act, Chapter, ChapterEdge, Character, CharacterRelation, Scene, SceneContent
from app.storycad.repository import StoryCADRepository
from app.agent.tools.base import BaseTool, ToolResult, verify_project_owner
from app.agent.project_creator.state import MaterialState
from app.agent.utils import count_words
from app.utils import row_to_dict


class CreateActTool(BaseTool):
    name = "create_act"
    description = "在项目中创建新幕（Act），必须指定项目ID"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "name": {"type": "string", "description": "幕名称，例如'第一幕'、'第二幕'"},
            "color": {"type": "string", "description": "颜色代码，例如'#8b5cf6'"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            result = await db.execute(
                select(func.coalesce(func.max(Act.sort_order), -1))
                .where(Act.project_id == project_id)
            )
            max_order = result.scalar() or -1
            sort_order = max_order + 1

            repo = StoryCADRepository(db)
            created = await repo.create_entity(Act, {
                "project_id": str(project_id),
                "name": kwargs.get("name", "新幕"),
                "color": kwargs.get("color", "#8b5cf6"),
                "sort_order": sort_order,
            })
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class CreateChapterTool(BaseTool):
    name = "create_chapter"
    description = "在指定幕（Act）中创建新章节（Chapter），必须指定项目ID和幕ID"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "act_id": {"type": "string", "description": "所属幕ID"},
            "title": {"type": "string", "description": "章节标题"},
            "goal": {"type": "string", "description": "章节写作目标"},
            "status": {"type": "string", "description": "状态：draft/revising/final"},
        },
        "required": ["project_id", "act_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            act_id = uuid.UUID(kwargs["act_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            act_result = await db.execute(
                select(Act).where(Act.id == act_id, Act.project_id == project_id)
            )
            if not act_result.scalar_one_or_none():
                return ToolResult(success=False, error=f"Act {act_id} not found in project {project_id}")

            result = await db.execute(
                select(func.coalesce(func.max(Chapter.sort_order), -1))
                .where(Chapter.project_id == project_id)
            )
            max_order = result.scalar() or -1
            sort_order = max_order + 1

            repo = StoryCADRepository(db)
            created = await repo.create_entity(Chapter, {
                "project_id": str(project_id),
                "act_id": str(act_id),
                "title": kwargs.get("title", "新章"),
                "goal": kwargs.get("goal", ""),
                "status": kwargs.get("status", "draft"),
                "sort_order": sort_order,
            })
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class DeleteSceneTool(BaseTool):
    name = "delete_scene"
    description = "删除指定场景（Scene），同时删除场景正文内容"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "scene_id": {"type": "string", "description": "场景ID"},
            "project_id": {"type": "string", "description": "项目ID（用于权限验证）"},
        },
        "required": ["scene_id", "project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            scene_id = uuid.UUID(kwargs["scene_id"])
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            scene = await db.get(Scene, scene_id)
            if not scene:
                return ToolResult(success=False, error="Scene not found")
            if scene.project_id != project_id:
                return ToolResult(success=False, error="Scene does not belong to this project")

            await db.delete(scene)
            await db.execute(
                select(SceneContent).where(SceneContent.scene_id == scene_id)
            )
            await db.execute(
                SceneContent.__table__.delete().where(SceneContent.scene_id == scene_id)
            )
            await db.flush()
            await _recalc_chapter_counts(db, project_id)
            await db.commit()
            return ToolResult(success=True, data={"deleted_scene_id": kwargs["scene_id"]})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class DeleteChapterTool(BaseTool):
    name = "delete_chapter"
    description = "删除指定章节（Chapter），同时删除该章节下的所有场景和场景正文（数据库级联删除）"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "chapter_id": {"type": "string", "description": "章节ID"},
            "project_id": {"type": "string", "description": "项目ID（用于权限验证）"},
        },
        "required": ["chapter_id", "project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            chapter_id = uuid.UUID(kwargs["chapter_id"])
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            chapter = await db.get(Chapter, chapter_id)
            if not chapter:
                return ToolResult(success=False, error="Chapter not found")
            if chapter.project_id != project_id:
                return ToolResult(success=False, error="Chapter does not belong to this project")

            scene_ids = await db.execute(
                select(Scene.id).where(Scene.chapter_id == chapter_id)
            )
            for (sid,) in scene_ids.all():
                await db.execute(
                    SceneContent.__table__.delete().where(SceneContent.scene_id == sid)
                )
            await db.execute(Scene.__table__.delete().where(Scene.chapter_id == chapter_id))
            await db.delete(chapter)
            await db.flush()
            await _recalc_chapter_counts(db, project_id)
            await db.commit()
            return ToolResult(success=True, data={"deleted_chapter_id": kwargs["chapter_id"]})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class DeleteActTool(BaseTool):
    name = "delete_act"
    description = "删除指定幕（Act），同时删除该幕下的所有章节和场景（数据库级联删除）"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "act_id": {"type": "string", "description": "幕ID"},
            "project_id": {"type": "string", "description": "项目ID（用于权限验证）"},
        },
        "required": ["act_id", "project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            act_id = uuid.UUID(kwargs["act_id"])
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            act = await db.get(Act, act_id)
            if not act:
                return ToolResult(success=False, error="Act not found")
            if act.project_id != project_id:
                return ToolResult(success=False, error="Act does not belong to this project")

            chapter_ids = await db.execute(
                select(Chapter.id).where(Chapter.act_id == act_id)
            )
            for (chid,) in chapter_ids.all():
                scene_ids = await db.execute(
                    select(Scene.id).where(Scene.chapter_id == chid)
                )
                for (sid,) in scene_ids.all():
                    await db.execute(
                        SceneContent.__table__.delete().where(SceneContent.scene_id == sid)
                    )
                await db.execute(Scene.__table__.delete().where(Scene.chapter_id == chid))
            await db.execute(Chapter.__table__.delete().where(Chapter.act_id == act_id))
            await db.delete(act)
            await db.flush()
            await _recalc_chapter_counts(db, project_id)
            await db.commit()
            return ToolResult(success=True, data={"deleted_act_id": kwargs["act_id"]})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateProjectTool(BaseTool):
    name = "update_project"
    description = "更新项目全局设定，包括标题、描述、体裁、全局世界观设定、目标字数等。只传入需要修改的字段即可"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "title": {"type": "string", "description": "项目标题"},
            "description": {"type": "string", "description": "项目描述"},
            "genre": {"type": "string", "description": "故事体裁，例如'奇幻'、'科幻'、'悬疑'"},
            "global_settings": {"type": "string", "description": "世界观设定、背景设定等全局设定文本"},
            "target_audience": {"type": "string", "description": "目标读者群体"},
            "total_words": {"type": "integer", "description": "目标总字数"},
            "template_type": {"type": "string", "description": "模板类型，例如'four_act'、'three_act'"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            project = await db.get(Project, project_id)
            if not project:
                return ToolResult(success=False, error="Project not found")

            for field in ("title", "description", "genre", "global_settings"):
                if field in kwargs:
                    setattr(project, field, kwargs[field])

            config_fields = {"target_audience", "total_words", "template_type"}
            if any(f in kwargs for f in config_fields):
                config = await db.execute(
                    select(ProjectConfig).where(ProjectConfig.project_id == project_id)
                )
                config_obj = config.scalar_one_or_none()
                if config_obj:
                    for field in config_fields:
                        if field in kwargs:
                            setattr(config_obj, field, kwargs[field])

            await db.commit()
            return ToolResult(success=True, data={
                "project_id": str(project_id),
                "title": project.title,
                "description": project.description,
                "genre": project.genre,
                "global_settings": (project.global_settings or "")[:200],
            })
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class CreateProjectFromMaterialTool(BaseTool):
    name = "create_project_from_material"
    description = "根据用户提供的创作素材，自动生成完整项目（包括幕、章、场景、角色、关系、世界观设定）。"\
                  "返回新创建的项目ID。素材至少10个字"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "material": {"type": "string", "description": "用户的创作素材，描述想要创作的故事内容，至少10个字"},
            "project_title": {"type": "string", "description": "项目标题"},
        },
        "required": ["material", "project_title"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            material = kwargs.get("material", "").strip()
            if len(material) < 10:
                return ToolResult(success=False, error="素材至少需要10个字来表达基本创意")
            if len(material) > 5000:
                return ToolResult(success=False, error="素材不能超过5000字")

            user_id = kwargs.get("user_id")
            if not user_id:
                return ToolResult(success=False, error="创建项目需要用户登录")

            from app.agent.project_creator.graph import build_graph
            graph = build_graph()

            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            initial_state: MaterialState = {
                "material": material,
                "project_title": kwargs.get("project_title", "未命名项目").strip() or "未命名项目",
                "genre": "", "tone": "", "characters_raw": [],
                "plot_summary": "", "world_elements": "",
                "acts": [], "estimated_words": 0, "scenes": [],
                "characters": [], "relations": [], "edges": [],
                "global_settings": "", "errors": [],
            }

            try:
                async for _event in graph.astream(initial_state, config):
                    pass
            except Exception as e:
                return ToolResult(success=False, error=f"项目生成失败: {e}")

            final_state = graph.get_state(config).values

            project_id = await _write_new_project(db, final_state, uuid.UUID(user_id))
            return ToolResult(success=True, data={
                "project_id": str(project_id),
            })
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class CreateEdgeTool(BaseTool):
    name = "create_edge"
    description = "在两个章节之间创建连线关系（ChapterEdge），用于表示时间线、因果、闪回等章节间关系"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "source_id": {"type": "string", "description": "源章节ID"},
            "target_id": {"type": "string", "description": "目标章节ID"},
            "edge_type": {"type": "string", "description": "连线类型，例如'timeline'、'cause_effect'、'flashback'、'parallel'"},
            "label": {"type": "string", "description": "连线标签"},
            "source_handle": {"type": "string", "description": "源端手柄位置，例如's-r'（右）、's-l'（左）"},
            "target_handle": {"type": "string", "description": "目标端手柄位置，如't-l'（左）、't-r'（右）"},
        },
        "required": ["project_id", "source_id", "target_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            src_id = uuid.UUID(kwargs["source_id"])
            tgt_id = uuid.UUID(kwargs["target_id"])

            source_ch = await db.get(Chapter, src_id)
            if not source_ch or source_ch.project_id != project_id:
                return ToolResult(success=False, error=f"Source chapter {src_id} not found in project")
            target_ch = await db.get(Chapter, tgt_id)
            if not target_ch or target_ch.project_id != project_id:
                return ToolResult(success=False, error=f"Target chapter {tgt_id} not found in project")

            existing = await db.execute(
                select(ChapterEdge).where(
                    ChapterEdge.project_id == project_id,
                    ChapterEdge.source_id == src_id,
                    ChapterEdge.target_id == tgt_id,
                )
            )
            if existing.scalar_one_or_none():
                return ToolResult(success=False, error="An edge already exists between these two chapters")

            repo = StoryCADRepository(db)
            created = await repo.create_entity(ChapterEdge, {
                "project_id": str(project_id),
                "source_id": str(src_id),
                "target_id": str(tgt_id),
                "edge_type": kwargs.get("edge_type", "timeline"),
                "label": kwargs.get("label", ""),
                "source_handle": kwargs.get("source_handle", "s-r"),
                "target_handle": kwargs.get("target_handle", "t-l"),
            })
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateEdgeTool(BaseTool):
    name = "update_edge"
    description = "更新章节连线的类型、标签或手柄位置"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "edge_id": {"type": "string", "description": "连线ID"},
            "edge_type": {"type": "string", "description": "连线类型"},
            "label": {"type": "string", "description": "连线标签"},
            "source_handle": {"type": "string", "description": "源端手柄位置"},
            "target_handle": {"type": "string", "description": "目标端手柄位置"},
        },
        "required": ["project_id", "edge_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))

            edge_id = uuid.UUID(kwargs["edge_id"])
            edge = await db.get(ChapterEdge, edge_id)
            if not edge or edge.project_id != project_id:
                return ToolResult(success=False, error="Edge not found")

            for field in ("edge_type", "label", "source_handle", "target_handle"):
                if field in kwargs:
                    setattr(edge, field, kwargs[field])
            await db.commit()
            return ToolResult(success=True, data={
                "edge_id": str(edge_id),
                "edge_type": edge.edge_type,
                "label": edge.label,
            })
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class DeleteEdgeTool(BaseTool):
    name = "delete_edge"
    description = "删除指定章节连线"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "edge_id": {"type": "string", "description": "连线ID"},
        },
        "required": ["project_id", "edge_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            project_id = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, project_id, kwargs.get("user_id"))
            edge_id = uuid.UUID(kwargs["edge_id"])
            edge = await db.get(ChapterEdge, edge_id)
            if not edge or edge.project_id != project_id:
                return ToolResult(success=False, error="Edge not found")
            await db.delete(edge)
            await db.commit()
            return ToolResult(success=True, data={"deleted_edge_id": kwargs["edge_id"]})
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


async def _recalc_chapter_counts(db: AsyncSession, project_id: uuid.UUID) -> None:
    counts = await db.execute(
        select(Scene.chapter_id, func.count(Scene.id), func.coalesce(func.sum(Scene.word_count), 0))
        .where(Scene.project_id == project_id)
        .group_by(Scene.chapter_id)
    )
    for row in counts.all():
        await db.execute(
            Chapter.__table__.update().where(Chapter.id == row[0])
            .values(scene_count=row[1], total_words=row[2])
        )
    chapters_without_scenes = await db.execute(
        select(Chapter.id).where(Chapter.project_id == project_id)
        .where(~Chapter.id.in_(select(Scene.chapter_id).where(Scene.project_id == project_id)))
    )
    for (cid,) in chapters_without_scenes.all():
        await db.execute(
            Chapter.__table__.update().where(Chapter.id == cid)
            .values(scene_count=0, total_words=0)
        )


async def _write_new_project(
    db: AsyncSession,
    state: dict,
    owner_id: uuid.UUID,
) -> uuid.UUID:
    repo = StoryCADRepository(db)
    project_title = state.get("project_title", "未命名项目")
    project = Project(
        title=project_title[:255],
        description=state.get("genre", "") or "",
        owner_id=owner_id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    project_id = project.id

    act_id_map: dict[int, str] = {}
    for act_idx, act in enumerate(state.get("acts", [])):
        result = await repo.create_entity(Act, {
            "project_id": str(project_id),
            "name": act.get("name", ""),
            "sort_order": act.get("order", act_idx + 1),
            "color": act.get("color", "#8b5cf6"),
        })
        act_id_map[act_idx] = result["id"]

    chapter_sort = 0
    chap_id_map: dict[tuple[int, int], str] = {}
    for act_idx, act in enumerate(state.get("acts", [])):
        for ch_idx, ch in enumerate(act.get("chapters", [])):
            chapter_sort += 1
            act_id = act_id_map.get(act_idx, "")
            chapter_result = await repo.create_entity(Chapter, {
                "project_id": str(project_id),
                "act_id": str(act_id),
                "title": ch.get("title", ""),
                "goal": ch.get("goal", ""),
                "sort_order": chapter_sort,
                "status": "draft",
            })
            chap_id_map[(act_idx, ch_idx)] = chapter_result["id"]

    scene_sort_total = 0
    per_chapter_count: dict[tuple[int, int], int] = {}
    for sc in sorted(
        state.get("scenes", []),
        key=lambda s: (s.get("act_idx", 0), s.get("chapter_idx", 0)),
    ):
        cid = chap_id_map.get((sc["act_idx"], sc["chapter_idx"]))
        if not cid:
            continue
        key = (sc["act_idx"], sc["chapter_idx"])
        per_chapter_count[key] = per_chapter_count.get(key, 0) + 1
        if per_chapter_count[key] > 5:
            continue
        scene_sort_total += 1
        await repo.create_entity(Scene, {
            "project_id": str(project_id),
            "chapter_id": str(cid),
            "title": sc["title"],
            "pov_character": sc.get("pov_character", ""),
            "setting": sc.get("setting", ""),
            "scene_time": sc.get("scene_time", ""),
            "summary": sc.get("summary", ""),
            "sort_order": scene_sort_total,
        })

    char_name_to_id = {}
    for char in state.get("characters", []):
        result = await repo.create_entity(Character, {
            "project_id": str(project_id),
            "name": char["name"],
            "role": char.get("role", "supporting"),
            "personality": char.get("personality", ""),
            "appearance": char.get("appearance", ""),
            "background": char.get("background", ""),
            "motivation": char.get("motivation", ""),
        })
        char_name_to_id[char["name"]] = result["id"]

    for rel in state.get("relations", []):
        src_id = char_name_to_id.get(rel.get("char_name", ""))
        tgt_id = char_name_to_id.get(rel.get("target_name", ""))
        if src_id and tgt_id:
            await repo.create_entity(CharacterRelation, {
                "project_id": str(project_id),
                "character_id": str(src_id),
                "target_id": str(tgt_id),
                "rel_type": rel.get("rel_type", "关联"),
                "label": rel.get("label", ""),
                "description": rel.get("description", ""),
            })

    for edge in state.get("edges", []):
        src = chap_id_map.get(
            (edge.get("source_act_idx", 0), edge.get("source_chapter_idx", 0))
        )
        tgt = chap_id_map.get(
            (edge.get("target_act_idx", 0), edge.get("target_chapter_idx", 0))
        )
        if src and tgt:
            await repo.create_entity(ChapterEdge, {
                "project_id": str(project_id),
                "source_id": str(src),
                "target_id": str(tgt),
                "edge_type": edge.get("type", "timeline"),
                "label": edge.get("label", ""),
                "source_handle": "s-r",
                "target_handle": "t-l",
            })

    config = ProjectConfig(
        project_id=project_id,
        total_words=state.get("estimated_words", 50000),
        template_type="custom",
    )
    db.add(config)

    gs = state.get("global_settings", "")
    if gs:
        project.global_settings = gs

    await db.commit()
    return project_id
