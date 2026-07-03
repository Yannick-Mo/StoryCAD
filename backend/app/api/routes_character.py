import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.character.service import CharacterService

router = APIRouter(prefix="/api/projects/{project_id}/characters", tags=["characters"])


@router.get("")
async def list_characters(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = CharacterService(db)
    return await service.get_characters(project_id)


@router.post("/generate")
async def generate_characters(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = CharacterService(db)
    return await service.generate_characters(project_id)


@router.put("/{name}")
async def update_character(project_id: uuid.UUID, name: str, updates: dict, db: AsyncSession = Depends(get_db)):
    service = CharacterService(db)
    ok = await service.update_character(project_id, name, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"ok": True}


@router.delete("/{name}")
async def delete_character(project_id: uuid.UUID, name: str, db: AsyncSession = Depends(get_db)):
    service = CharacterService(db)
    ok = await service.delete_character(project_id, name)
    if not ok:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"ok": True}