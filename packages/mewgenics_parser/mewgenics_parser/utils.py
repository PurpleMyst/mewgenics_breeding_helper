"""Shared utility functions for the parser."""

import re
from dataclasses import dataclass
from typing import Any

_IMG_RE = re.compile(r"\[img:([^\]]+)\]")
_SIZE_COLOR_RE = re.compile(r"\[[sc]:[^\]]*\]|\[/[sc]\]")
_WS_RE = re.compile(r"\s+")

_IMG_SUBS = {
    "cha": "CHA",
    "con": "CON",
    "dex": "DEX",
    "divineshield": "Holy Shield",
    "int": "INT",
    "lck": "LCK",
    "spd": "SPD",
    "str": "STR",
}


def _clean_game_text(text: str) -> str:
    """Clean formatting tags from game text strings, replacing known [img:...] tags with readable text."""
    text = _IMG_RE.sub(
        lambda m: _IMG_SUBS.get(m.group(1).lower(), m.group(1).title()), text
    )
    text = _SIZE_COLOR_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


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


def _parse_gon_to_dicts(text: str, *, comment_key: str = "name") -> dict[str, Any]:
    # 1. Lexical Analysis (Tokenization)
    token_specification = [
        ("BLOCK_COMMENT", r"/\*[\s\S]*?\*/"),  # Multi-line or inline block comments
        ("LINE_COMMENT", r"//[^\n]*"),  # Single-line comments
        ("STRING", r'"[^"]*"'),  # String literals
        ("LBRACE", r"\{"),  # Block start
        ("RBRACE", r"\}"),  # Block end
        (
            "LITERAL",
            r"(?:(?!//|/\*)[^\s\{\}])+",
        ),  # Keys/Values (stops if it hits a comment)
        ("SKIP", r"\s+"),  # Whitespace
    ]

    tok_regex = "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in token_specification)
    tokens = [m for m in re.finditer(tok_regex, text) if m.lastgroup != "SKIP"]

    # 2. Parsing (State Machine)
    root: dict[str, Any] = {}
    stack = [root]

    i = 0
    n = len(tokens)

    while i < n:
        match = tokens[i]
        kind = match.lastgroup
        val = match.group()

        if kind == "RBRACE":
            if len(stack) > 1:
                stack.pop()
            i += 1

        elif kind in ("LINE_COMMENT", "BLOCK_COMMENT"):
            # Standalone comments are ignored, but handled below if attached to a block
            i += 1

        elif kind == "LITERAL":
            key = val
            i += 1
            if i >= n:
                break

            next_match = tokens[i]
            next_kind = next_match.lastgroup
            next_val = next_match.group()

            if next_kind == "LBRACE":
                # Start new block
                new_node = {}
                stack[-1][key] = new_node
                stack.append(new_node)
                i += 1

                # Check for an immediate comment to save as name
                if i < n and tokens[i].lastgroup in ("LINE_COMMENT", "BLOCK_COMMENT"):
                    comment_text = tokens[i].group()
                    if tokens[i].lastgroup == "LINE_COMMENT":
                        new_node[comment_key] = comment_text[2:].strip()
                    else:
                        new_node[comment_key] = comment_text[
                            2:-2
                        ].strip()  # Strip /* and */
                    i += 1

            elif next_kind in ("LITERAL", "STRING"):
                # Assign Key-Value pair
                if next_kind == "STRING":
                    parsed_val = next_val[1:-1]
                else:
                    try:
                        parsed_val = int(next_val)
                    except ValueError:
                        try:
                            parsed_val = float(next_val)
                        except ValueError:
                            parsed_val = next_val

                stack[-1][key] = parsed_val
                i += 1
            else:
                pass  # Ignore malformed trailing literals
        else:
            i += 1

    return root


@dataclass(slots=True, frozen=True)
class NameAndDescription:
    """Simple struct for holding a name and description pair, used for abilities and mutations."""

    name: str = ""
    description: str = ""
