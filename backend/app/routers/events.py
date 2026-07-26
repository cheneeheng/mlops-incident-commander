from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.services.event_service import broker

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def events() -> StreamingResponse:
    # No custom headers required, so the browser's native EventSource works (no auth in MVP).
    return StreamingResponse(
        broker.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
