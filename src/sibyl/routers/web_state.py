"""Shared state for web modules."""

from sibyl.storage.engine import Engine

review_sessions: dict[str, dict] = {}

storage = Engine()
