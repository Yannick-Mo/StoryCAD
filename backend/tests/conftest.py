import uuid
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings
from app.project.models import Base
from app.user.models import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn)
        yield session
        await session.close()
        await conn.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> dict:
    from app.user.repository import UserRepository
    from app.user.service import UserService
    repo = UserRepository(db_session)
    user = await repo.create("testuser", "test@example.com", UserService._hash_password("password"))
    return {"id": user.id, "username": user.username}
