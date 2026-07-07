from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db

def _validate_config():
    if not settings.jwt_secret_key:
        raise ValueError(
            "JWT_SECRET_KEY is not configured. Set it in .env file or JWT_SECRET_KEY environment variable."
        )
_validate_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="StoryCAD", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


def register_routers():
    from app.api.routes_auth import router as auth_router
    app.include_router(auth_router)
    from app.api.routes_project import router as project_router
    app.include_router(project_router)
    from app.api.routes_storycad import router as storycad_router
    app.include_router(storycad_router)
    from app.api.routes_ai import router as ai_router
    app.include_router(ai_router)
    from app.api.routes_ai import material_router
    app.include_router(material_router)
    from app.api.routes_ai_v2 import router as ai_v2_router
    app.include_router(ai_v2_router)

    from app.mcp.server import mcp
    app.mount("/mcp", mcp.sse_app())


register_routers()
