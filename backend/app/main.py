from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Story Forge", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Story Forge API is running"}
