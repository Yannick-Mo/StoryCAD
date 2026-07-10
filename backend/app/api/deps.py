from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.config import settings
from app.database import async_session
from app.user.service import UserService

import logging
logger = logging.getLogger(__name__)

_redis_instance: Redis | None = None
_revoked_tokens: set[str] = set()


def blacklist_token(token: str) -> None:
    _revoked_tokens.add(token)


def is_token_revoked(token: str) -> bool:
    return token in _revoked_tokens


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_redis() -> Redis | None:
    """Lazily initializes and returns a shared Redis client, or None if unavailable."""
    global _redis_instance
    if _redis_instance is not None:
        return _redis_instance
    try:
        _redis_instance = Redis.from_url(settings.redis_url, decode_responses=False)
        await _redis_instance.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (using in-memory fallback): %s", exc)
        _redis_instance = None
    return _redis_instance


async def get_current_user(authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = authorization[7:]
    if is_token_revoked(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    service = UserService(db)
    return await service.get_current_user(token)
