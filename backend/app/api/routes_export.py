import uuid
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.export.models import ExportRequest
from app.export.service import ExportService
from fastapi.responses import PlainTextResponse, Response

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])


@router.post("")
async def export_story(project_id: uuid.UUID, request: ExportRequest = Body(...), db: AsyncSession = Depends(get_db)):
    service = ExportService(db)
    result = await service.export(project_id, request)
    if request.format == "markdown":
        return PlainTextResponse(content=result.content, media_type=result.mime_type,
                                 headers={"Content-Disposition": f"attachment; filename={result.filename}"})
    return Response(content=result.content, media_type=result.mime_type,
                    headers={"Content-Disposition": f"attachment; filename={result.filename}"})
