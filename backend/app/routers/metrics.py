from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import MetricWindowOut
from backend.app.services import metrics_service

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/windows", response_model=list[MetricWindowOut])
async def list_windows(since: datetime | None = None, db: AsyncSession = Depends(get_db)):
    return await metrics_service.list_windows(db, since)
