"""Latency-injection middleware: sleeps the currently-injected added latency before handling each
request. The value is refreshed from the DB by the 5s poller in main.py."""

import asyncio
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from serving.app import state


class LatencyInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        added_latency_ms = state.runtime.added_latency_ms
        if added_latency_ms > 0:
            await asyncio.sleep(added_latency_ms / 1000.0)
        return await call_next(request)
