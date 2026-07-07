import uuid
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.user.models import User
from app.project.models import Project, ProjectVersion, ProjectConfig
from app.storycad.models import (
    Act, Chapter, Scene, SceneContent, ChapterEdge,
    Character, CharacterRelation,
    Theme, ThemeChapter,
)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, username: str, email: str, password_hash: str) -> User:
        user = User(username=username, email=email, password_hash=password_hash)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def update(self, user_id: uuid.UUID, **kwargs) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self.db.commit()
        return True

    async def delete(self, user_id: uuid.UUID) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False

        result = await self.db.execute(select(Project.id).where(Project.owner_id == user_id))
        project_ids = [row[0] for row in result.all()]

        for pid in project_ids:
            await self.db.execute(delete(SceneContent).where(SceneContent.project_id == pid))
            await self.db.execute(delete(Scene).where(Scene.project_id == pid))
            await self.db.execute(delete(ChapterEdge).where(ChapterEdge.project_id == pid))
            await self.db.execute(delete(ThemeChapter).where(ThemeChapter.project_id == pid))
            await self.db.execute(delete(Chapter).where(Chapter.project_id == pid))
            await self.db.execute(delete(CharacterRelation).where(CharacterRelation.project_id == pid))
            await self.db.execute(delete(Character).where(Character.project_id == pid))
            await self.db.execute(delete(Theme).where(Theme.project_id == pid))
            await self.db.execute(delete(Act).where(Act.project_id == pid))
            await self.db.execute(delete(ProjectVersion).where(ProjectVersion.project_id == pid))
            await self.db.execute(delete(ProjectConfig).where(ProjectConfig.project_id == pid))

        await self.db.commit()

        for pid in project_ids:
            await self.db.execute(delete(Project).where(Project.id == pid))

        await self.db.delete(user)
        await self.db.commit()
        return True
