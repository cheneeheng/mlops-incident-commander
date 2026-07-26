from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import DeployActivate, DeployOut
from backend.app.services import deploy_service

router = APIRouter(prefix="/api", tags=["deploys"])


@router.get("/deploys", response_model=list[DeployOut])
async def list_deploys(db: AsyncSession = Depends(get_db)):
    return await deploy_service.list_deploys(db)


@router.post("/deploys/activate", response_model=DeployOut)
async def activate_deploy(payload: DeployActivate, db: AsyncSession = Depends(get_db)):
    deploy = await deploy_service.activate(db, payload.model_version)
    if deploy is None:
        raise HTTPException(status_code=404, detail="model_version not found")
    return deploy
