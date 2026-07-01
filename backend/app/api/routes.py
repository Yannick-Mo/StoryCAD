import asyncio
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, async_session
from app.services.generation import run_generation
from app.services.storage import create_project, get_project, get_latest_skeleton
from app.graph.story_graph import build_story_graph

router = APIRouter()


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

    from app.services.storage import save_skeleton
    async with async_session() as session:
        await save_skeleton(session, project_id, sk.skeleton, report)

    return {
        "project_id": str(project_id),
        "validation_report": report
    }
