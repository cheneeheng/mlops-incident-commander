"""Application-generated public IDs: prefixed, URL-safe, unguessable. Never expose DB integers."""

import secrets

# Per-entity prefixes. Kept short and stable — they appear in URLs and logs.
PREFIXES: dict[str, str] = {
    "deploy": "dep",
    "reference_profile": "ref",
    "prediction_log": "prd",
    "serving_log": "slg",
    "metric_window": "win",
    "injection": "inj",
    "incident": "inc",
    "agent_run": "run",
    "hypothesis": "hyp",
    "remediation": "rem",
    "postmortem": "pmt",
    "eval_run": "evr",
    "eval_case": "evc",
}


def new_id(entity: str) -> str:
    """Return a fresh public ID like `inc_a5Kd9x...` for the given entity name."""
    prefix = PREFIXES[entity]
    return f"{prefix}_{secrets.token_urlsafe(12)}"
