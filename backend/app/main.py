from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db


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


register_routers()
