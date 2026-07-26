"""MCP client toolbox for the diagnosis agent: launches the four stdio tool servers as subprocesses,
aggregates their tools into Anthropic tool specs, and routes tool calls to the owning session.

Used as an async context manager so the subprocesses are torn down after each diagnosis run.
"""

import sys
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Module paths of the four servers; each is launched as `python -m <module>`.
_SERVER_MODULES = (
    "mcp_servers.metrics_server",
    "mcp_servers.logs_server",
    "mcp_servers.deploys_server",
    "mcp_servers.preddist_server",
)


class McpToolbox:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session_by_tool: dict[str, ClientSession] = {}
        self._tool_specs: list[dict[str, Any]] = []

    async def __aenter__(self) -> "McpToolbox":
        for module in _SERVER_MODULES:
            params = StdioServerParameters(command=sys.executable, args=["-m", module])
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            listed = await session.list_tools()
            for tool in listed.tools:
                self._session_by_tool[tool.name] = session
                self._tool_specs.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._stack.aclose()

    @property
    def tool_specs(self) -> list[dict[str, Any]]:
        return self._tool_specs

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        session = self._session_by_tool.get(name)
        if session is None:
            return f"error: unknown tool {name!r}"
        result = await session.call_tool(name, arguments)
        return "".join(getattr(block, "text", "") for block in result.content)
