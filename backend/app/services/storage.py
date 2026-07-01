import uuid
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Project, ProjectSkeleton


async def create_project(db: AsyncSession, raw_input: dict) -> Project:
    project = Project(id=uuid.uuid4(), raw_input=raw_input, status="pending")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def update_project_status(db: AsyncSession, project_id: uuid.UUID, status: str):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project:
        project.status = status
        await db.commit()


async def save_skeleton(
    db: AsyncSession,
    project_id: uuid.UUID,
    skeleton: dict,
    validation_report: Optional[list] = None
):
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .order_by(desc(ProjectSkeleton.version))
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    sk = ProjectSkeleton(
        project_id=project_id,
        version=version,
        skeleton=skeleton,
        validation_report=validation_report
    )
    db.add(sk)
    await db.commit()


async def get_latest_skeleton(db: AsyncSession, project_id: uuid.UUID) -> Optional[ProjectSkeleton]:
    result = await db.execute(
        select(ProjectSkeleton)
        .where(ProjectSkeleton.project_id == project_id)
        .order_by(desc(ProjectSkeleton.version))
        .limit(1)
    )
    return result.scalar_one_or_none()
