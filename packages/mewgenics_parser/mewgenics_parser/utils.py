"""Shared utility functions for the parser."""

from __future__ import annotations


def _resolve_game_string(value: str, game_strings: dict[str, str]) -> str:
    """Resolve a game string reference chain."""
    resolved = value
    seen: set[str] = set()
    while resolved in game_strings and resolved not in seen:
        seen.add(resolved)
        nxt = game_strings[resolved].strip()
        if not nxt:
            break
        resolved = nxt
    return resolved
