"""Anthropic client primitives shared by the agent nodes: a lazily-cached async client, a token
usage accumulator, and helpers to pull final text and parse JSON from a model response."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from anthropic import AsyncAnthropic

from backend.app.config import get_settings

# ~4 chars/token; cap each tool result near 2k tokens to keep diagnosis context bounded.
TOOL_RESULT_CHAR_CAP = 8000


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    # usage: Any — anthropic's Message.usage; typed loosely to avoid pinning SDK response types.
    def add(self, usage: Any) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens


@lru_cache
def get_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


# response: Any — anthropic Message; content blocks are a discriminated union narrowed by .type.
def final_text(response: Any) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


# Returns parsed JSON; values are Any because model output is arbitrary JSON validated downstream.
def extract_json(text: str) -> dict[str, Any]:
    """Parse the first JSON object in the text, tolerating stray prose or ``` fences."""
    match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if match is None:
        raise ValueError("no JSON object in model output")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model output JSON is not an object")
    return parsed


def truncate_tool_result(text: str) -> str:
    if len(text) <= TOOL_RESULT_CHAR_CAP:
        return text
    return text[:TOOL_RESULT_CHAR_CAP] + "\n...[truncated]"
