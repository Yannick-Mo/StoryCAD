from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.api.rate_limiter import rate_limiter
from app.user.service import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"register:{client_ip}"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    if not username or not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username, email, and password are required")
    service = UserService(db)
    try:
        return await service.register(username, email, password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"login:{client_ip}"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required")
    service = UserService(db)
    return await service.login(email, password)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/me")
async def update_me(payload: dict, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = current_user["id"]
    display_name = payload.get("display_name")
    password = payload.get("password")
    service = UserService(db)
    return await service.update_profile(user_id, display_name=display_name, password=password)
