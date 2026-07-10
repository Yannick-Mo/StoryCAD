import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.project.service import ProjectService
from app.utils import row_to_dict

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
async def create_project(payload: dict, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    return await service.create_project(
        payload.get("title", "Untitled"),
        payload.get("description", ""),
        uuid.UUID(current_user["id"])
    )


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    status: str = Query(""),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.list_projects(uuid.UUID(current_user["id"]), page, size, search, status)


@router.get("/{project_id}")
async def get_project(project_id: uuid.UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    result = await service.get_project(project_id, uuid.UUID(current_user["id"]))
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


ALLOWED_PROJECT_FIELDS = {"title", "description", "status"}

@router.patch("/{project_id}")
async def update_project(project_id: uuid.UUID, payload: dict, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    filtered = {k: v for k, v in payload.items() if k in ALLOWED_PROJECT_FIELDS}
    service = ProjectService(db)
    ok = await service.update_project(project_id, uuid.UUID(current_user["id"]), **filtered)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.delete("/{project_id}")
async def delete_project(project_id: uuid.UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    ok = await service.delete_project(project_id, uuid.UUID(current_user["id"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.get("/{project_id}/versions")
async def get_versions(project_id: uuid.UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    versions = await service.repo.get_versions(project_id)
    return [{"version": v.version, "created_at": v.created_at.isoformat()} for v in versions]


@router.post("/{project_id}/versions")
async def save_version(project_id: uuid.UUID, payload: dict, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    pv = await service.repo.save_version(project_id, payload.get("snapshot", {}))
    return {"version": pv.version, "created_at": pv.created_at.isoformat()}


@router.get("/{project_id}/versions/latest")
async def get_latest_version(project_id: uuid.UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    versions = await service.repo.get_versions(project_id)
    if not versions:
        raise HTTPException(status_code=404, detail="No versions found")
    latest = versions[0]
    return {"version": latest.version, "snapshot": latest.snapshot, "created_at": latest.created_at.isoformat()}


@router.get("/{project_id}/versions/{version}")
async def get_version(project_id: uuid.UUID, version: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_project(project_id, uuid.UUID(current_user["id"]))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    versions = await service.repo.get_versions(project_id)
    target = next((v for v in versions if v.version == version), None)
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"version": target.version, "snapshot": target.snapshot, "created_at": target.created_at.isoformat()}


@router.get("/{project_id}/config")
async def get_project_config(
    project_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    config = await service.get_config(uuid.UUID(current_user["id"]), project_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return row_to_dict(config)


@router.put("/{project_id}/config")
async def update_project_config(
    project_id: uuid.UUID,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    config = await service.update_config(uuid.UUID(current_user["id"]), project_id, payload)
    if not config:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}
