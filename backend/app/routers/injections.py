from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import InjectionCreate, InjectionOut
from backend.app.services import injection_service

router = APIRouter(prefix="/api", tags=["injections"])


@router.get("/injections", response_model=list[InjectionOut])
async def list_injections(db: AsyncSession = Depends(get_db)):
    return await injection_service.list_injections(db)


@router.post("/injections", response_model=InjectionOut, status_code=201)
async def create_injection(payload: InjectionCreate, db: AsyncSession = Depends(get_db)):
    return await injection_service.create_injection(db, payload)


@router.post("/injections/{injection_id}/stop", response_model=InjectionOut)
async def stop_injection(injection_id: str, db: AsyncSession = Depends(get_db)):
    injection = await injection_service.stop_injection(db, injection_id)
    if injection is None:
        raise HTTPException(status_code=404, detail="injection not found")
    return injection
