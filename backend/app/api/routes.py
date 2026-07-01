import asyncio
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, async_session
from app.services.generation import run_generation
from app.services.storage import (
    create_project, get_project, get_latest_skeleton, save_skeleton,
    list_projects, delete_project, get_skeleton_versions, get_skeleton_by_version
)
from app.services.graph_editor import (
    add_graph_node, update_graph_node, delete_graph_node,
    add_graph_edge, delete_graph_edge,
    add_character, update_character, delete_character
)
from app.services.export import export_json, export_markdown

router = APIRouter()


@router.get("/projects")
async def list_projects_route(db: AsyncSession = Depends(get_db)):
    projects = await list_projects(db)
    return [
        {"project_id": str(p.id), "status": p.status, "created_at": p.created_at.isoformat()}
        for p in projects
    ]


@router.post("/projects")
async def create_project_route(
    raw_input: dict,
    db: AsyncSession = Depends(get_db)
):
    project = await create_project(db, raw_input)
    asyncio.create_task(run_generation(project.id, raw_input, async_session))
    return {
        "project_id": str(project.id),
        "status": project.status
    }


@router.get("/projects/{project_id}")
async def get_project_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    project = await get_project(db, project_id)
    if not project:
        return {"error": "Project not found"}
    sk = await get_latest_skeleton(db, project_id)
    return {
        "project_id": str(project.id),
        "status": project.status,
        "skeleton": sk.skeleton if sk else None,
        "validation_report": sk.validation_report if sk else None
    }


@router.delete("/projects/{project_id}")
async def delete_project_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ok = await delete_project(db, project_id)
    if not ok:
        return {"error": "Project not found"}
    return {"ok": True}


@router.get("/projects/{project_id}/skeleton")
async def get_skeleton_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return {"error": "No skeleton found"}
    return {
        "version": sk.version,
        "skeleton": sk.skeleton,
        "validation_report": sk.validation_report
    }


@router.put("/projects/{project_id}/skeleton")
async def update_skeleton_route(project_id: uuid.UUID, skeleton: dict, db: AsyncSession = Depends(get_db)):
    sk = await get_latest_skeleton(db, project_id)
    report = sk.validation_report if sk else []
    await save_skeleton(db, project_id, skeleton, report)
    return {"ok": True}


@router.get("/projects/{project_id}/skeleton/versions")
async def skeleton_versions_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    versions = await get_skeleton_versions(db, project_id)
    return [
        {"version": v.version, "created_at": v.created_at.isoformat()}
        for v in versions
    ]


@router.get("/projects/{project_id}/skeleton/versions/{version}")
async def skeleton_version_route(project_id: uuid.UUID, version: int, db: AsyncSession = Depends(get_db)):
    sk = await get_skeleton_by_version(db, project_id, version)
    if not sk:
        return {"error": "Version not found"}
    return {"version": sk.version, "skeleton": sk.skeleton, "validation_report": sk.validation_report}


@router.post("/projects/{project_id}/validate")
async def validate_project_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    sk = await get_latest_skeleton(db, project_id)
    if not sk or not sk.skeleton:
        return {"error": "No skeleton to validate"}

    from app.agents.validator import run as validate

    state = {
        "creative_doc": sk.skeleton.get("creative_doc", {}),
        "world_rules": sk.skeleton.get("world_rules", {}),
        "characters": sk.skeleton.get("characters", []),
        "graph_data": sk.skeleton.get("graph", {}),
        "branches": sk.skeleton.get("branches", []),
        "foreshadows": sk.skeleton.get("foreshadows", []),
    }
    result = validate(state)
    report = result.get("validation_report", [])

    await save_skeleton(db, project_id, sk.skeleton, report)

    return {
        "project_id": str(project_id),
        "validation_report": report
    }


# Graph node/edge endpoints

@router.post("/projects/{project_id}/graph/nodes")
async def add_node_route(project_id: uuid.UUID, node: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await add_graph_node(db, project_id, node)
        return result
    except ValueError as e:
        return {"error": str(e)}


@router.put("/projects/{project_id}/graph/nodes/{node_id}")
async def update_node_route(project_id: uuid.UUID, node_id: str, updates: dict, db: AsyncSession = Depends(get_db)):
    result = await update_graph_node(db, project_id, node_id, updates)
    if not result:
        return {"error": "Node not found"}
    return result


@router.delete("/projects/{project_id}/graph/nodes/{node_id}")
async def delete_node_route(project_id: uuid.UUID, node_id: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_graph_node(db, project_id, node_id)
    if not ok:
        return {"error": "Node not found"}
    return {"ok": True}


@router.post("/projects/{project_id}/graph/edges")
async def add_edge_route(project_id: uuid.UUID, source: str, target: str, type: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await add_graph_edge(db, project_id, source, target, type)
        return result
    except ValueError as e:
        return {"error": str(e)}


@router.delete("/projects/{project_id}/graph/edges")
async def delete_edge_route(project_id: uuid.UUID, source: str, target: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_graph_edge(db, project_id, source, target)
    if not ok:
        return {"error": "Edge not found"}
    return {"ok": True}


# Character endpoints

@router.post("/projects/{project_id}/characters")
async def add_character_route(project_id: uuid.UUID, character: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await add_character(db, project_id, character)
        return result
    except ValueError as e:
        return {"error": str(e)}


@router.put("/projects/{project_id}/characters/{name}")
async def update_character_route(project_id: uuid.UUID, name: str, updates: dict, db: AsyncSession = Depends(get_db)):
    result = await update_character(db, project_id, name, updates)
    if not result:
        return {"error": "Character not found"}
    return result


@router.delete("/projects/{project_id}/characters/{name}")
async def delete_character_route(project_id: uuid.UUID, name: str, db: AsyncSession = Depends(get_db)):
    ok = await delete_character(db, project_id, name)
    if not ok:
        return {"error": "Character not found"}
    return {"ok": True}


# Export endpoints

@router.get("/projects/{project_id}/export/json")
async def export_json_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await export_json(db, project_id)
    if not result:
        return {"error": "No skeleton found"}
    return PlainTextResponse(
        result,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="skeleton-{project_id}.json"'}
    )


@router.get("/projects/{project_id}/export/markdown")
async def export_markdown_route(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await export_markdown(db, project_id)
    if not result:
        return {"error": "No skeleton found"}
    return PlainTextResponse(
        result,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="skeleton-{project_id}.md"'}
    )
