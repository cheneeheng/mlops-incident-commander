"""Latency-injection middleware. Stub at SKELETON; ITER_01 polls the active latency injection from
the DB every 5s and sleeps accordingly to degrade /predict latency on demand."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class LatencyInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # stub — real latency injection in ITER_01
        return await call_next(request)
