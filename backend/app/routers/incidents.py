from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import IncidentDetail, IncidentSummary
from backend.app.services import incident_service

router = APIRouter(prefix="/api", tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentSummary])
async def list_incidents(db: AsyncSession = Depends(get_db)):
    return await incident_service.list_incidents(db)


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident
