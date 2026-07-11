import uuid
from sqlalchemy import select
from app.mcp.server import mcp
from app.database import async_session
from app.storycad.models import Chapter, Scene, SceneContent
from app.storycad.repository import StoryCADRepository
from app.utils import row_to_dict
from app.mcp.auth import get_current_user_mcp, verify_project_ownership


@mcp.tool()
async def read_chapter(token: str, chapter_id: str) -> dict:
    """获取章节及其包含的场景列表"""
    async with async_session() as db:
        user = await get_current_user_mcp(token, db)
        result = await db.execute(select(Chapter).where(Chapter.id == uuid.UUID(chapter_id)))
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        await verify_project_ownership(str(chapter.project_id), user["id"], db)
        scenes_result = await db.execute(
            select(Scene).where(Scene.chapter_id == uuid.UUID(chapter_id)).order_by(Scene.sort_order)
        )
        scenes = [row_to_dict(s) for s in scenes_result.scalars().all()]
        data = row_to_dict(chapter)
        data["scenes"] = scenes
        return data


@mcp.tool()
async def read_scene(token: str, scene_id: str) -> dict:
    """获取场景内容，包含正文"""
    async with async_session() as db:
        user = await get_current_user_mcp(token, db)
        result = await db.execute(select(Scene).where(Scene.id == uuid.UUID(scene_id)))
        scene = result.scalar_one_or_none()
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")
        await verify_project_ownership(str(scene.project_id), user["id"], db)
        content_result = await db.execute(
            select(SceneContent).where(SceneContent.scene_id == uuid.UUID(scene_id))
        )
        sc = content_result.scalar_one_or_none()
        data = row_to_dict(scene)
        data["content"] = sc.content if sc else ""
        return data


@mcp.tool()
async def create_scene(
    token: str,
    project_id: str,
    chapter_id: str,
    title: str,
    summary: str = "",
    content: str = "",
    pov_character: str = "",
    setting: str = "",
    scene_time: str = "",
    sort_order: int = 0,
) -> dict:
    """在指定章节下创建新场景"""
    from app.agent.utils import count_words

    async with async_session() as db:
        user = await get_current_user_mcp(token, db)
        await verify_project_ownership(project_id, user["id"], db)
        repo = StoryCADRepository(db)
        scene_data = {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "title": title,
            "sort_order": sort_order,
            "summary": summary,
            "pov_character": pov_character,
            "setting": setting,
            "scene_time": scene_time,
        }
        created = await repo.create_entity(Scene, scene_data)
        if content:
            sc_id = uuid.UUID(created["id"])
            db.add(SceneContent(scene_id=sc_id, project_id=uuid.UUID(project_id), content=content))
            result = await db.execute(select(Scene).where(Scene.id == sc_id))
            scene_obj = result.scalar_one_or_none()
            if scene_obj:
                scene_obj.word_count = count_words(content)
            await db.flush()
        await db.commit()
        return created


@mcp.tool()
async def update_scene(
    token: str,
    scene_id: str,
    title: str | None = None,
    summary: str | None = None,
    content: str | None = None,
    pov_character: str | None = None,
    setting: str | None = None,
    scene_time: str | None = None,
) -> dict:
    """更新场景内容、标题、POV、地点、时间、梗概等"""
    from app.agent.utils import count_words

    async with async_session() as db:
        user = await get_current_user_mcp(token, db)
        result = await db.execute(select(Scene).where(Scene.id == uuid.UUID(scene_id)))
        scene = result.scalar_one_or_none()
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")
        await verify_project_ownership(str(scene.project_id), user["id"], db)
        repo = StoryCADRepository(db)
        update_data = {"id": scene_id}
        for field in ("title", "summary", "pov_character", "setting", "scene_time"):
            val = locals()[field]
            if val is not None:
                update_data[field] = val
        updated = await repo.update_entity(Scene, update_data)
        if content is not None:
            sid = uuid.UUID(scene_id)
            result = await db.execute(select(SceneContent).where(SceneContent.scene_id == sid))
            sc = result.scalar_one_or_none()
            if sc:
                sc.content = content
            else:
                result = await db.execute(select(Scene).where(Scene.id == sid))
                scene_obj = result.scalar_one_or_none()
                if scene_obj:
                    db.add(SceneContent(scene_id=sid, project_id=scene_obj.project_id, content=content))
            result = await db.execute(select(Scene).where(Scene.id == sid))
            scene_obj = result.scalar_one_or_none()
            if scene_obj:
                scene_obj.word_count = count_words(content)
            await db.flush()
        await db.commit()
        return updated
