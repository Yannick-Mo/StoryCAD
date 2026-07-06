# backend/app/api/routes_ai.py
import uuid
import json as json_mod
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.api.rate_limiter import rate_limiter
from app.project.service import ProjectService
from app.project.models import Project, ProjectConfig
from app.agent.orchestrator import AgentOrchestrator
from app.agent.project_creator.graph import build_graph
from app.agent.project_creator.state import MaterialState
from app.storycad.entity_map import ENTITY_MAP
from app.storycad.repository import StoryCADRepository


class AiGenerateRequest(BaseModel):
    chapter_id: str
    mode: str
    prompt: str = ""


router = APIRouter(prefix="/api/projects/{project_id}", tags=["ai"])


@router.post("/ai/generate")
async def ai_generate(
    request: Request,
    project_id: uuid.UUID,
    payload: AiGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"ai_generate:{current_user['id']}", max_attempts=10, window=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    svc = ProjectService(db)
    project = await svc.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.mode not in ("goal", "outline", "writing"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")

    prompt = payload.prompt.strip()[:2000]

    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.generate(
        project_id,
        uuid.UUID(payload.chapter_id),
        payload.mode,
        prompt,
    )
    return result


# ============================================================
# Create project from material (LangGraph pipeline + SSE)
# ============================================================

class CreateFromMaterialRequest(BaseModel):
    title: str = "未命名项目"
    material: str


material_router = APIRouter(prefix="/api/projects", tags=["ai"])


@material_router.post("/create-from-material")
async def create_from_material(
    payload: CreateFromMaterialRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.material.strip():
        raise HTTPException(status_code=400, detail="素材不能为空")
    if len(payload.material) > 5000:
        raise HTTPException(status_code=400, detail="素材不能超过5000字")

    async def event_stream():
        graph = build_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        initial_state: MaterialState = {
            "material": payload.material.strip(),
            "project_title": payload.title.strip() or "未命名项目",
            "genre": "", "tone": "", "characters_raw": [],
            "plot_summary": "", "world_elements": "",
            "acts": [], "estimated_words": 0, "scenes": [],
            "characters": [], "relations": [],
            "global_settings": "", "errors": [],
            "_fanout_act_idx": 0, "_fanout_chap_idx": 0,
        }

        try:
            async for event in graph.astream(initial_state, config):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        preview = _make_preview(node_name, node_output)
                        yield f"data: {json_mod.dumps({'step': node_name, 'status': 'done', 'preview': preview})}\n\n"
        except Exception as e:
            yield f"data: {json_mod.dumps({'step': 'error', 'message': str(e)})}\n\n"
            return

        final_state = graph.get_state(config).values
        try:
            project_id = await _write_project_to_db(db, final_state, uuid.UUID(current_user["id"]))
            yield f"data: {json_mod.dumps({'step': 'done', 'project_id': str(project_id)})}\n\n"
        except Exception as e:
            yield f"data: {json_mod.dumps({'step': 'error', 'message': f'数据库写入失败: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _make_preview(node_name: str, output: dict) -> str:
    if node_name == "analyze_material":
        return f"类型：{output.get('genre', '')}\n基调：{output.get('tone', '')}"
    elif node_name == "plan_structure":
        acts = output.get("acts", [])
        total_ch = sum(len(a.get("chapters", [])) for a in acts)
        return f"{len(acts)}幕{total_ch}章 · 预估{output.get('estimated_words', 0)}字"
    elif node_name == "generate_scene_chapter":
        sc = output.get("scenes", [])
        return f"+{len(sc)}个场景"
    elif node_name == "design_characters":
        return f"{len(output.get('characters', []))}个角色已创建"
    elif node_name == "build_settings":
        gs = output.get("global_settings", "")
        return gs[:80] + ("..." if len(gs) > 80 else "")
    elif node_name == "validate":
        return "校验通过" if not output.get("errors") else f"修正了{len(output.get('errors', []))}个问题"
    return ""


async def _write_project_to_db(db: AsyncSession, state: dict, owner_id: uuid.UUID) -> uuid.UUID:
    svc = ProjectService(db)
    repo = StoryCADRepository(db)

    project = await svc.create_project(state.get("project_title", "未命名"), "", owner_id)
    project_id = uuid.UUID(project["id"])
    await db.commit()

    act_id_map: dict[int, str] = {}
    for act in state.get("acts", []):
        result = await repo.create_entity(
            ENTITY_MAP["acts"],
            {
                "project_id": str(project_id),
                "name": act.get("name", ""),
                "sort_order": act.get("order", 1),
                "color": act.get("color", "#8b5cf6"),
            },
        )
        act_id_map[act.get("order", 1)] = result["id"]

    chapter_sort = 0
    chap_id_map: dict[tuple[int, int], str] = {}
    for act_idx, act in enumerate(state.get("acts", [])):
        for ch_idx, ch in enumerate(act.get("chapters", [])):
            chapter_sort += 1
            act_id = act_id_map.get(act.get("order", act_idx + 1), "")
            chapter_result = await repo.create_entity(
                ENTITY_MAP["chapters"],
                {
                    "project_id": str(project_id),
                    "act_id": str(act_id),
                    "title": ch.get("title", ""),
                    "goal": ch.get("goal", ""),
                    "sort_order": chapter_sort,
                    "status": "draft",
                },
            )
            chap_id_map[(act_idx, ch_idx)] = chapter_result["id"]

    scene_sort_total = 0
    for sc in sorted(state.get("scenes", []), key=lambda s: (s["act_idx"], s["chapter_idx"])):
        cid = chap_id_map.get((sc["act_idx"], sc["chapter_idx"]))
        if cid:
            scene_sort_total += 1
            await repo.create_entity(
                ENTITY_MAP["scenes"],
                {
                    "project_id": str(project_id),
                    "chapter_id": str(cid),
                    "title": sc["title"],
                    "pov_character": sc.get("pov_character", ""),
                    "setting": sc.get("setting", ""),
                    "scene_time": sc.get("scene_time", ""),
                    "summary": sc.get("summary", ""),
                    "sort_order": scene_sort_total,
                },
            )

    char_name_to_id: dict[str, str] = {}
    for char in state.get("characters", []):
        result = await repo.create_entity(
            ENTITY_MAP["characters"],
            {
                "project_id": str(project_id),
                "name": char["name"],
                "role": char.get("role", "supporting"),
                "personality": char.get("personality", ""),
                "appearance": char.get("appearance", ""),
                "background": char.get("background", ""),
                "motivation": char.get("motivation", ""),
                "sort_order": len(char_name_to_id),
            },
        )
        char_name_to_id[char["name"]] = result["id"]

    for rel in state.get("relations", []):
        src_id = char_name_to_id.get(rel.get("char_name", ""))
        tgt_id = char_name_to_id.get(rel.get("target_name", ""))
        if src_id and tgt_id:
            await repo.create_entity(
                ENTITY_MAP["character_relations"],
                {
                    "project_id": str(project_id),
                    "character_id": str(src_id),
                    "target_id": str(tgt_id),
                    "rel_type": rel.get("rel_type", "关联"),
                    "label": rel.get("label", ""),
                    "description": rel.get("description", ""),
                },
            )

    config = ProjectConfig(
        project_id=project_id,
        total_words=state.get("estimated_words", 50000),
        template_type="custom",
    )
    db.add(config)

    gs = state.get("global_settings", "")
    if gs:
        result = await db.execute(select(Project).where(Project.id == project_id))
        proj = result.scalar_one_or_none()
        if proj:
            proj.global_settings = gs

    await db.commit()
    return project_id
