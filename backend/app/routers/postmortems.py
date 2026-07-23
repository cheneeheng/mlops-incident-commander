from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas import PostmortemOut
from backend.app.services import postmortem_service

router = APIRouter(prefix="/api", tags=["postmortems"])


@router.get("/postmortems", response_model=list[PostmortemOut])
async def list_postmortems(db: AsyncSession = Depends(get_db)):
    return await postmortem_service.list_postmortems(db)


@router.get("/postmortems/{postmortem_id}", response_model=PostmortemOut)
async def get_postmortem(postmortem_id: str, db: AsyncSession = Depends(get_db)):
    postmortem = await postmortem_service.get_postmortem(db, postmortem_id)
    if postmortem is None:
        raise HTTPException(status_code=404, detail="postmortem not found")
    return postmortem
