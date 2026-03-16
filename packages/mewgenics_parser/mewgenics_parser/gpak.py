"""GPAK file parsing utilities."""

from __future__ import annotations

import csv
import io
import re
import struct
from dataclasses import dataclass

from .utils import _resolve_game_string
from .visual import _parse_mutation_gon


# Pre-compiled regexes for performance
_BLOCK_RE = re.compile(r"^([A-Za-z]\w*)\s*\{", re.MULTILINE)
_DESC_RE = re.compile(r'^\s*desc\s+"([^"]*)"', re.MULTILINE)

# Pre-compiled regexes for _clean_game_text
_IMG_RE = re.compile(r"\[img:[^\]]+\]")
_SIZE_RE = re.compile(r"\[s:[^\]]*\]|\[/s\]")
_COLOR_RE = re.compile(r"\[c:[^\]]*\]|\[/c\]")
_WS_RE = re.compile(r"\s+")


def _clean_game_text(text: str) -> str:
    """Clean formatting tags from game text strings."""
    text = _IMG_RE.sub("", text)
    text = _SIZE_RE.sub("", text)
    text = _COLOR_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


def _read_gpak_header(path: str) -> dict[str, tuple[int, int]]:
    """Read GPAK file header, return {filename: (offset, size)}."""
    with open(path, "rb") as f:
        count = struct.unpack("<I", f.read(4))[0]
        entries = []
        for _ in range(count):
            name_len = struct.unpack("<H", f.read(2))[0]
            name = f.read(name_len).decode("utf-8", errors="replace")
            size = struct.unpack("<I", f.read(4))[0]
            entries.append((name, size))
        dir_end = f.tell()

        file_offsets: dict[str, tuple[int, int]] = {}
        offset = dir_end
        for name, size in entries:
            file_offsets[name] = (offset, size)
            offset += size
        return file_offsets


def _parse_gon_abilities(content: str, game_strings: dict[str, str]) -> dict[str, str]:
    """Parse ability GON content into {ability_id: description}."""
    result: dict[str, str] = {}
    for bm in _BLOCK_RE.finditer(content):
        ability_id = bm.group(1)
        block_start = bm.end()
        depth, idx = 1, block_start
        while idx < len(content) and depth > 0:
            if content[idx] == "{":
                depth += 1
            elif content[idx] == "}":
                depth -= 1
            idx += 1
        block = content[block_start : idx - 1]
        dm = _DESC_RE.search(block)
        if not dm:
            continue
        desc_val = dm.group(1)
        desc_val = _resolve_game_string(desc_val, game_strings)
        if not desc_val or desc_val == "nothing":
            continue
        result[ability_id.lower()] = _clean_game_text(desc_val)
    return result


def load_gpak_text_strings(
    file_obj,
    file_offsets: dict[str, tuple[int, int]],
) -> dict[str, str]:
    """Load text strings from CSV files in the GPAK."""
    strings: dict[str, str] = {}
    for fname, (csv_off, csv_sz) in file_offsets.items():
        if not (fname.startswith("data/text/") and fname.endswith(".csv")):
            continue
        file_obj.seek(csv_off)
        raw_csv = file_obj.read(csv_sz).decode("utf-8-sig", errors="replace")
        for row in csv.reader(io.StringIO(raw_csv)):
            if len(row) >= 2 and row[0] and not row[0].startswith("//"):
                strings[row[0]] = row[1]
    return strings


@dataclass
class GameData:
    """Bundle of all GPAK game data."""

    ability_descriptions: dict[str, str]
    visual_mutations: dict[str, dict[int, tuple[str, str]]]
    game_strings: dict[str, str]

    @classmethod
    def from_gpak(cls, gpak_path: str) -> "GameData":
        """Load all data from the GPAK file."""
        if not gpak_path:
            return cls(
                ability_descriptions={},
                visual_mutations={},
                game_strings={},
            )

        try:
            file_offsets = _read_gpak_header(gpak_path)

            # Read all .gon files into memory once
            gon_contents: dict[str, str] = {}
            with open(gpak_path, "rb") as f:
                game_strings = load_gpak_text_strings(f, file_offsets)
                for fname in file_offsets:
                    if not fname.endswith(".gon"):
                        continue
                    foff, fsz = file_offsets[fname]
                    f.seek(foff)
                    gon_contents[fname] = f.read(fsz).decode("utf-8", errors="replace")

            # Process abilities (no more file I/O)
            ability_descriptions: dict[str, str] = {}
            for fname, content in gon_contents.items():
                if fname.startswith("data/abilities/") or fname.startswith(
                    "data/passives/"
                ):
                    ability_descriptions.update(
                        _parse_gon_abilities(content, game_strings)
                    )

            # Process visual mutations (no more file I/O)
            visual_mutations: dict[str, dict[int, tuple[str, str]]] = {}
            for fname, content in gon_contents.items():
                if fname.startswith("data/mutations/"):
                    category = fname.split("/")[-1].replace(".gon", "")
                    visual_mutations[category] = _parse_mutation_gon(
                        content, game_strings, category
                    )

            return cls(
                ability_descriptions=ability_descriptions,
                visual_mutations=visual_mutations,
                game_strings=game_strings,
            )
        except Exception:
            return cls(
                ability_descriptions={},
                visual_mutations={},
                game_strings={},
            )
