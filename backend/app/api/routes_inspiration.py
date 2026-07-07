from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.agent.inspiration.generator import InspirationGenerator
from app.agent.inspiration.challenges import get_challenges, get_random_challenge

router = APIRouter(prefix="/api/inspiration", tags=["Inspiration"])


class StarterRequest(BaseModel):
    genre: str
    style: str = ""
    constraints: list[str] | None = None


class BatchRequest(BaseModel):
    genres: list[str]
    count: int = 3


@router.post("/starter")
async def story_starter(
    req: StarterRequest,
    user: dict = Depends(get_current_user),
):
    try:
        gen = InspirationGenerator()
        result = await gen.generate_story_starter(req.genre, req.style, req.constraints)
        if result is None:
            raise HTTPException(status_code=500, detail="生成故事起点失败")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成故事起点失败: {str(e)}")


@router.post("/batch")
async def batch_starters(
    req: BatchRequest,
    user: dict = Depends(get_current_user),
):
    try:
        gen = InspirationGenerator()
        return await gen.batch_generate(req.genres, req.count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")


@router.get("/challenges")
async def list_challenges(
    difficulty: str | None = Query(None),
    genre: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    try:
        return get_challenges(difficulty, genre)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取挑战列表失败: {str(e)}")


@router.get("/challenges/random")
async def random_challenge(
    user: dict = Depends(get_current_user),
):
    try:
        return get_random_challenge()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取随机挑战失败: {str(e)}")
