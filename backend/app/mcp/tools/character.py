from sqlalchemy import select
from app.mcp.server import mcp
from app.database import async_session
from app.storycad.models import Character, CharacterRelation
from app.storycad.repository import StoryCADRepository
from app.utils import row_to_dict


@mcp.tool()
async def list_characters(project_id: str) -> dict:
    """列出项目中所有角色及其关系信息"""
    async with async_session() as db:
        repo = StoryCADRepository(db)
        characters = await repo.list_entities(Character, project_id)
        relations_result = await db.execute(
            select(CharacterRelation).where(CharacterRelation.project_id == project_id)
        )
        relations = [row_to_dict(r) for r in relations_result.scalars().all()]
        return {"characters": characters, "relations": relations}


@mcp.tool()
async def create_character(
    project_id: str,
    name: str,
    role: str = "supporting",
    personality: str = "",
    appearance: str = "",
    background: str = "",
    motivation: str = "",
) -> dict:
    """创建新角色"""
    async with async_session() as db:
        repo = StoryCADRepository(db)
        data = {
            "project_id": project_id,
            "name": name,
            "role": role,
            "personality": personality,
            "appearance": appearance,
            "background": background,
            "motivation": motivation,
        }
        created = await repo.create_entity(Character, data)
        await db.commit()
        return created


@mcp.tool()
async def update_character(
    character_id: str,
    name: str | None = None,
    role: str | None = None,
    personality: str | None = None,
    appearance: str | None = None,
    background: str | None = None,
    motivation: str | None = None,
) -> dict:
    """更新角色信息"""
    async with async_session() as db:
        repo = StoryCADRepository(db)
        data = {"id": character_id}
        for field in ("name", "role", "personality", "appearance", "background", "motivation"):
            val = locals()[field]
            if val is not None:
                data[field] = val
        updated = await repo.update_entity(Character, data)
        if not updated:
            raise ValueError(f"Character {character_id} not found")
        await db.commit()
        return updated


@mcp.tool()
async def update_relation(
    project_id: str,
    character_id: str,
    target_id: str,
    rel_type: str = "关联",
    label: str = "",
    description: str = "",
    trust: int = 50,
    threat: int = 50,
    attraction: int = 50,
    relation_id: str | None = None,
) -> dict:
    """创建或更新角色关系"""
    async with async_session() as db:
        repo = StoryCADRepository(db)
        if relation_id:
            data = {"id": relation_id}
            for field in ("rel_type", "label", "description", "trust", "threat", "attraction"):
                val = locals()[field]
                if val is not None:
                    data[field] = val
            updated = await repo.update_entity(CharacterRelation, data)
            if not updated:
                raise ValueError(f"Relation {relation_id} not found")
            await db.commit()
            return updated
        else:
            from uuid import UUID
            data = {
                "project_id": project_id,
                "character_id": str(UUID(character_id)),
                "target_id": str(UUID(target_id)),
                "rel_type": rel_type,
                "label": label,
                "description": description,
                "trust": trust,
                "threat": threat,
                "attraction": attraction,
            }
            created = await repo.create_entity(CharacterRelation, data)
            await db.commit()
            return created
