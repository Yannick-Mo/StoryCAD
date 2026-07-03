from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="StoryCAD", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


def register_routers():
    from app.api.routes_project import router as project_router
    app.include_router(project_router)
    from app.api.routes_analysis import router as analysis_router
    app.include_router(analysis_router)
    from app.api.routes_character import router as character_router
    app.include_router(character_router)
    from app.api.routes_world import router as world_router
    app.include_router(world_router)
    from app.api.routes_story import router as story_router
    app.include_router(story_router)
    from app.api.routes_validation import router as validation_router
    app.include_router(validation_router)
    from app.api.routes_knowledge_graph import router as kg_router
    app.include_router(kg_router)
    from app.api.routes_orchestrator import router as orchestrator_router
    app.include_router(orchestrator_router)
    from app.api.routes_export import router as export_router
    app.include_router(export_router)


register_routers()
