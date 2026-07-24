"""Domain exceptions mapped to HTTP status codes by handlers registered in main.py."""


class ConflictError(Exception):
    """An operation conflicts with the current state of the resource (maps to HTTP 409)."""
