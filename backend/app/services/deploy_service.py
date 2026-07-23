"""Deploy history + activation. Stub at SKELETON; real logic in ITER_01."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Deploy


async def list_deploys(db: AsyncSession) -> list[Deploy]:
    return []  # stub — real query in ITER_01


async def activate(db: AsyncSession, model_version: str) -> Deploy | None:
    raise NotImplementedError("deploy activation lands in ITER_01")
