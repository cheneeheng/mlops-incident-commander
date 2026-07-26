from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import RemediationOut
from backend.app.services import remediation_service

router = APIRouter(prefix="/api", tags=["remediations"])


@router.post("/remediations/{remediation_id}/approve", response_model=RemediationOut)
async def approve_remediation(remediation_id: str, db: AsyncSession = Depends(get_db)):
    remediation = await remediation_service.approve(db, remediation_id)
    if remediation is None:
        raise HTTPException(status_code=404, detail="remediation not found")
    return remediation


@router.post("/remediations/{remediation_id}/reject", response_model=RemediationOut)
async def reject_remediation(remediation_id: str, db: AsyncSession = Depends(get_db)):
    remediation = await remediation_service.reject(db, remediation_id)
    if remediation is None:
        raise HTTPException(status_code=404, detail="remediation not found")
    return remediation
