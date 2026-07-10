from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult, verify_project_owner
from app.storycad.models import Character, CharacterRelation
from app.storycad.repository import StoryCADRepository
from app.utils import row_to_dict


class ListCharactersTool(BaseTool):
    name = "list_characters"
    description = "列出项目中所有角色及其详细信息"
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
            repo = StoryCADRepository(db)
            characters = await repo.list_entities(Character, pid)
            relations_result = await db.execute(
                select(CharacterRelation).where(CharacterRelation.project_id == pid)
            )
            relations = [row_to_dict(r) for r in relations_result.scalars().all()]
            return ToolResult(success=True, data={"characters": characters, "relations": relations})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CreateCharacterTool(BaseTool):
    name = "create_character"
    description = "创建新角色"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "name": {"type": "string", "description": "角色名称"},
            "role": {"type": "string", "description": "角色类型（protagonist/supporting/antagonist）"},
            "personality": {"type": "string", "description": "性格描述"},
            "appearance": {"type": "string", "description": "外貌描述"},
            "background": {"type": "string", "description": "背景故事"},
            "motivation": {"type": "string", "description": "动机"},
        },
        "required": ["project_id", "name"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            pid = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, pid, kwargs.get("user_id"))
            name = kwargs["name"]
            repo = StoryCADRepository(db)
            existing = await db.execute(
                select(Character).where(
                    Character.project_id == pid,
                    Character.name == name,
                )
            )
            if existing.scalar_one_or_none():
                return ToolResult(
                    success=False,
                    error=f"A character named '{name}' already exists in this project",
                )
            data = {
                "project_id": str(pid),
                "name": name,
                "role": kwargs.get("role", "supporting"),
                "personality": kwargs.get("personality", ""),
                "appearance": kwargs.get("appearance", ""),
                "background": kwargs.get("background", ""),
                "motivation": kwargs.get("motivation", ""),
            }
            created = await repo.create_entity(Character, data)
            await db.commit()
            return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateCharacterTool(BaseTool):
    name = "update_character"
    description = "更新角色信息"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "character_id": {"type": "string", "description": "角色ID"},
            "name": {"type": "string"},
            "role": {"type": "string"},
            "personality": {"type": "string"},
            "appearance": {"type": "string"},
            "background": {"type": "string"},
            "motivation": {"type": "string"},
        },
        "required": ["character_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            char_id = uuid.UUID(kwargs["character_id"])
            result = await db.execute(select(Character).where(Character.id == char_id))
            char_obj = result.scalar_one_or_none()
            if not char_obj:
                return ToolResult(success=False, error="Character not found")
            await verify_project_owner(db, char_obj.project_id, kwargs.get("user_id"))
            repo = StoryCADRepository(db)
            data = {"id": str(char_id)}
            for field in ("name", "role", "personality", "appearance", "background", "motivation"):
                if field in kwargs:
                    data[field] = kwargs[field]
            updated = await repo.update_entity(Character, data)
            if not updated:
                return ToolResult(success=False, error="Character not found")
            await db.commit()
            return ToolResult(success=True, data=updated)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class UpdateRelationTool(BaseTool):
    name = "update_relation"
    description = "更新角色关系"
    is_write_operation = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
            "relation_id": {"type": "string", "description": "关系ID（留空则创建新关系）"},
            "character_id": {"type": "string", "description": "源角色ID"},
            "target_id": {"type": "string", "description": "目标角色ID"},
            "rel_type": {"type": "string", "description": "关系类型"},
            "label": {"type": "string", "description": "关系标签"},
            "description": {"type": "string", "description": "关系描述"},
            "trust": {"type": "integer", "description": "信任度（0-100）"},
            "threat": {"type": "integer", "description": "威胁度（0-100）"},
            "attraction": {"type": "integer", "description": "吸引力（0-100）"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            pid = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, pid, kwargs.get("user_id"))
            repo = StoryCADRepository(db)
            relation_id = kwargs.get("relation_id")
            if relation_id:
                data = {"id": str(relation_id)}
                for field in ("rel_type", "label", "description", "trust", "threat", "attraction"):
                    if field in kwargs:
                        data[field] = kwargs[field]
                updated = await repo.update_entity(CharacterRelation, data)
                if not updated:
                    return ToolResult(success=False, error="Relation not found")
                await db.commit()
                return ToolResult(success=True, data=updated)
            else:
                if "character_id" not in kwargs or "target_id" not in kwargs:
                    return ToolResult(
                        success=False,
                        error="character_id and target_id are required when creating a new relation (no relation_id provided)",
                    )
                data = {
                    "project_id": str(pid),
                    "character_id": str(uuid.UUID(kwargs["character_id"])),
                    "target_id": str(uuid.UUID(kwargs["target_id"])),
                    "rel_type": kwargs.get("rel_type", "关联"),
                    "label": kwargs.get("label", ""),
                    "description": kwargs.get("description", ""),
                    "trust": kwargs.get("trust", 50),
                    "threat": kwargs.get("threat", 50),
                    "attraction": kwargs.get("attraction", 50),
                }
                created = await repo.create_entity(CharacterRelation, data)
                await db.commit()
                return ToolResult(success=True, data=created)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))
