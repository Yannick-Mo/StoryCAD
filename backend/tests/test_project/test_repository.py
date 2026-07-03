import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.project.repository import ProjectRepository


@pytest.mark.asyncio
async def test_create_project(db_session: AsyncSession):
    repo = ProjectRepository(db_session)
    project = await repo.create("Test Project")
    assert project.title == "Test Project"
    assert project.status == "init"
    assert project.id is not None


@pytest.mark.asyncio
async def test_get_project(db_session: AsyncSession):
    repo = ProjectRepository(db_session)
    created = await repo.create("Get Test")
    found = await repo.get(created.id)
    assert found is not None
    assert found.title == "Get Test"
