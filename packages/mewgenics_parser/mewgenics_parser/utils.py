"""Shared utility functions for the parser."""

import re
from dataclasses import dataclass
from typing import Any

_IMG_RE = re.compile(r"\[img:[^\]]+\]")
_SIZE_COLOR_RE = re.compile(r"\[[sc]:[^\]]*\]|\[/[sc]\]")
_WS_RE = re.compile(r"\s+")

_IMG_SUBS = {
    "cha": "CHA",
    "champion": "Champion",
    "comfort": "Comfort",
    "con": "CON",
    "dex": "DEX",
    "divineshield": "Holy Shield",
    "elite": "Elite",
    "int": "INT",
    "lck": "LCK",
    "shield": "Shield",
    "spd": "SPD",
    "str": "STR",
}


def _clean_game_text(text: str) -> str:
    """Clean formatting tags from game text strings, replacing known [img:...] tags with readable text."""

    for key, sub in _IMG_SUBS.items():
        text = re.sub(rf"\[img:{key}\]", sub, text, flags=re.IGNORECASE)

    text = _IMG_RE.sub("", text)
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


def _parse_gon_to_dicts(text: str) -> dict[str, Any]:
    # 1. Lexical Analysis (Tokenization)
    # Define the regex patterns for our syntax building blocks
    token_specification = [
        ("COMMENT", r"//[^\n]*"),  # Comments (stop at newline)
        ("STRING", r'"[^"]*"'),  # String literals enclosed in quotes
        ("LBRACE", r"\{"),  # Block start
        ("RBRACE", r"\}"),  # Block end
        ("LITERAL", r"[^\s\{\}]+"),  # Everything else (keys, numbers, unquoted strings)
        ("SKIP", r"\s+"),  # Whitespace (spaces, tabs, newlines)
    ]

    # Compile a master regex that tries to match any of the above
    tok_regex = "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in token_specification)

    # Generate a flat list of tokens, dropping the whitespace
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
            if len(stack) > 1:  # Step up the tree
                stack.pop()
            i += 1

        elif kind == "COMMENT":
            # Standalone comments can be ignored; block comments are handled in the LBRACE logic
            i += 1

        elif kind == "LITERAL":
            key = val
            i += 1
            if i >= n:
                break

            # Look ahead to the next token to determine if this is a block or a key-value pair
            next_match = tokens[i]
            next_kind = next_match.lastgroup
            next_val = next_match.group()

            if next_kind == "LBRACE":
                # We are starting a new block
                new_node = {}
                stack[-1][key] = new_node
                stack.append(new_node)
                i += 1

                # Check if there is an immediate inline comment to save
                if i < n and tokens[i].lastgroup == "COMMENT":
                    new_node["__comment__"] = tokens[i].group()[2:].strip()
                    i += 1

            elif next_kind in ("LITERAL", "STRING"):
                # We have a key-value pair
                if next_kind == "STRING":
                    parsed_val = next_val[1:-1]  # Strip quotes
                else:
                    # Type Coercion
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
                # If a literal is followed by an RBRACE, it's malformed or a boolean flag.
                # We'll ignore it for this schema, but you could handle it here.
                pass
        else:
            i += 1

    return root


@dataclass(slots=True, frozen=True)
class NameAndDescription:
    """Simple struct for holding a name and description pair, used for abilities and mutations."""

    name: str = ""
    description: str = ""
