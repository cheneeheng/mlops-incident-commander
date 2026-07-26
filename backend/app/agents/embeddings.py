"""Sentence-embedding helper for postmortem memory. all-MiniLM-L6-v2 → 384-dim, normalized so that
cosine distance is meaningful. The dim is baked into the Postmortem.embedding column (Vector(384)) —
do not swap the model for one with a different dimension without a migration."""

import asyncio
from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384


@lru_cache
def _model() -> Any:  # SentenceTransformer has no complete stubs; loaded lazily (heavy import).
    return SentenceTransformer(_MODEL_NAME)


async def embed(text: str) -> list[float]:
    """Encode text to a normalized 384-dim vector, off the event loop (encode is CPU-bound)."""
    vector = await asyncio.to_thread(
        lambda: _model().encode(text, normalize_embeddings=True)
    )
    return [float(x) for x in vector]
