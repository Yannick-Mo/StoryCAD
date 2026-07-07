from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.agent.consistency.checker import ConsistencyChecker
from app.agent.consistency.models import ConsistencyReport
from app.database import async_session

router = APIRouter(prefix="/api/consistency", tags=["consistency"])


@router.post("/projects/{project_id}/check", response_model=ConsistencyReport)
async def check_consistency(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    async with async_session() as db:
        checker = ConsistencyChecker(db)
        report = await checker.check_all(project_id)
        return report
