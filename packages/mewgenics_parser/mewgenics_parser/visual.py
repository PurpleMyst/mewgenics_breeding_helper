"""Visual mutation parsing utilities."""

from __future__ import annotations

import re

from .data.visual_names import VISUAL_MUTATION_NAMES
from .utils import _resolve_game_string


# Pre-compiled regexes for performance
_MUTATION_ID_RE = re.compile(r"(?<!\w)(\d{3,})\s*\{")
_COMMENT_RE = re.compile(r"//\s*(.+)")
_MUTATION_NUM_RE = re.compile(r"^Mutation \d+$")


def _make_stat_re(key: str):
    """Create a pre-compiled regex for matching stat values."""
    return re.compile(rf"(?<!\w){re.escape(key)}\s+(-?\d+)")


# Pre-compiled stat regexes for all known stat keys
_STAT_REGEXES: dict[str, re.Pattern] = {
    key: _make_stat_re(key)
    for key in (
        "str",
        "con",
        "int",
        "dex",
        "spd",
        "lck",
        "cha",
        "shield",
        "divine_shield",
    )
}


_STAT_LABELS = {
    "str": "STR",
    "con": "CON",
    "int": "INT",
    "dex": "DEX",
    "spd": "SPD",
    "lck": "LCK",
    "cha": "CHA",
    "shield": "Shield",
    "divine_shield": "Holy Shield",
}

_VISUAL_MUTATION_FIELDS = [
    ("fur", 0, "fur", "texture", "fur", "Fur"),
    ("body", 3, "body", "body", "body", "Body"),
    ("head", 8, "head", "head", "head", "Head"),
    ("tail", 13, "tail", "tail", "tail", "Tail"),
    ("leg_L", 18, "legs", "legs", "legs", "Left Leg"),
    ("leg_R", 23, "legs", "legs", "legs", "Right Leg"),
    ("arm_L", 28, "arms", "legs", "legs", "Left Arm"),
    ("arm_R", 33, "arms", "legs", "legs", "Right Arm"),
    ("eye_L", 38, "eyes", "eyes", "eyes", "Left Eye"),
    ("eye_R", 43, "eyes", "eyes", "eyes", "Right Eye"),
    ("eyebrow_L", 48, "eyebrows", "eyebrows", "eyebrows", "Left Eyebrow"),
    ("eyebrow_R", 53, "eyebrows", "eyebrows", "eyebrows", "Right Eyebrow"),
    ("ear_L", 58, "ears", "ears", "ears", "Left Ear"),
    ("ear_R", 63, "ears", "ears", "ears", "Right Ear"),
    ("mouth", 68, "mouth", "mouth", "mouth", "Mouth"),
]

_VISUAL_MUTATION_PART_LABELS = {
    "fur": "Fur",
    "body": "Body",
    "head": "Head",
    "tail": "Tail",
    "legs": "Leg",
    "arms": "Arm",
    "eyes": "Eye",
    "eyebrows": "Eyebrow",
    "ears": "Ear",
    "mouth": "Mouth",
}


def _parse_mutation_gon(
    content: str,
    game_strings: dict[str, str] | None = None,
    category: str = "",
) -> dict[int, tuple[str, str]]:
    """Parse a mutation GON file into {slot_id: (display_name, stat_desc)}."""
    if game_strings is None:
        game_strings = {}

    result: dict[int, tuple[str, str]] = {}
    csv_prefix = f"MUTATION_{category.upper()}_"
    idx = 0
    while idx < len(content):
        match = _MUTATION_ID_RE.search(content[idx:])
        if not match:
            break
        slot_id = int(match.group(1))
        block_start = idx + match.end()
        depth, block_end = 1, block_start
        while block_end < len(content) and depth > 0:
            if content[block_end] == "{":
                depth += 1
            elif content[block_end] == "}":
                depth -= 1
            block_end += 1
        block = content[block_start : block_end - 1]
        idx = block_end
        if slot_id < 300:
            continue

        name_match = _COMMENT_RE.search(block)
        raw_name = (
            name_match.group(1).strip().title() if name_match else f"Mutation {slot_id}"
        )
        csv_key = f"{csv_prefix}{slot_id}_DESC"
        if csv_key in game_strings:
            stat_desc = (
                _resolve_game_string(game_strings[csv_key], game_strings)
                .strip()
                .rstrip(".")
            )
        else:
            header = block.split("{")[0]
            stats: list[str] = []
            for key, label in _STAT_LABELS.items():
                stat_match = _STAT_REGEXES[key].search(header)
                if stat_match:
                    value = int(stat_match.group(1))
                    stats.append(f"{'+' if value > 0 else ''}{value} {label}")
            stat_desc = ", ".join(stats)
        result[slot_id] = (raw_name, stat_desc)
    return result


def _read_visual_mutation_entries(
    table: list[int],
    gpak_data: dict[str, dict[int, tuple[str, str]]] | None = None,
) -> list[dict[str, object]]:
    """Read visual mutation entries from a table.

    Args:
        table: The visual mutation table (list of mutation IDs)
        gpak_data: Optional GPAK data for mutations. If not provided, uses fallback names.
    """
    if gpak_data is None:
        gpak_data = {}
    fallback_names = VISUAL_MUTATION_NAMES
    entries: list[dict[str, object]] = []
    for (
        slot_key,
        table_index,
        group_key,
        gpak_category,
        fallback_part,
        slot_label,
    ) in _VISUAL_MUTATION_FIELDS:
        mutation_id = table[table_index] if table_index < len(table) else 0
        if mutation_id in (0, 0xFFFF_FFFF):
            continue

        display_name = ""
        detail = ""
        gpak_info = gpak_data.get(gpak_category, {}).get(mutation_id)
        if gpak_info:
            raw_name, stat_desc = gpak_info
            if _MUTATION_NUM_RE.match(raw_name):
                display_name = f"{_VISUAL_MUTATION_PART_LABELS.get(group_key, slot_label)} Mutation"
            else:
                display_name = raw_name
            detail = stat_desc
        else:
            fallback_name = fallback_names.get((fallback_part, mutation_id))
            if fallback_name is None:
                if mutation_id < 300:
                    continue
                fallback_name = f"{_VISUAL_MUTATION_PART_LABELS.get(group_key, slot_label)} {mutation_id}"
            display_name = fallback_name

        display_name = str(display_name).strip() or f"{slot_label} {mutation_id}"
        entries.append(
            {
                "slot_key": slot_key,
                "slot_label": slot_label,
                "group_key": group_key,
                "part_label": _VISUAL_MUTATION_PART_LABELS.get(group_key, slot_label),
                "mutation_id": mutation_id,
                "name": display_name,
                "detail": str(detail).strip(),
            }
        )
    return entries


def _visual_mutation_chip_items(
    entries: list[dict[str, object]],
) -> list[tuple[str, str]]:
    """Convert visual mutation entries into chip items with tooltips."""
    grouped: dict[tuple[str, int], list[dict[str, object]]] = {}
    order: list[tuple[str, int]] = []
    for entry in entries:
        key = (str(entry["group_key"]), int(entry["mutation_id"]))
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(entry)

    groups: list[dict[str, object]] = []
    for key in order:
        items = grouped[key]
        slot_labels = [str(item["slot_label"]) for item in items]
        name = str(items[0]["name"])
        mutation_id = int(items[0]["mutation_id"])
        part_label = str(items[0]["part_label"])
        detail = str(items[0]["detail"]).strip()
        title_label = (
            part_label if len(slot_labels) > 1 else str(items[0]["slot_label"])
        )
        tooltip = f"{title_label} Mutation (ID {mutation_id})\n{name}"
        if detail:
            tooltip = f"{tooltip}\n{detail}"
        if len(slot_labels) > 1:
            tooltip = f"{tooltip}\nAffects: {', '.join(slot_labels)}"
        groups.append(
            {
                "text": name,
                "tooltip": tooltip,
                "slot_labels": slot_labels,
            }
        )

    text_counts: dict[str, int] = {}
    for group in groups:
        text = str(group["text"])
        text_counts[text] = text_counts.get(text, 0) + 1

    chip_items: list[tuple[str, str]] = []
    for group in groups:
        text = str(group["text"])
        if text_counts[text] > 1:
            text = f"{text} ({' / '.join(group['slot_labels'])})"
        chip_items.append((text, str(group["tooltip"])))
    return chip_items
