"""GPAK file parsing utilities."""
from __future__ import annotations

import csv
import io
import re
import struct
from dataclasses import dataclass

from .visual import _parse_mutation_gon


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


def load_ability_descriptions(gpak_path: str) -> dict[str, str]:
    """Load ability descriptions from the GPAK file.

    Returns {normalized_ability_id: english_desc} by reading ability/passive GON files
    and combined.csv from the game's gpak. Returns {} if gpak is unavailable.
    """
    if not gpak_path:
        return {}
    try:
        with open(gpak_path, "rb") as f:
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

            game_strings = load_gpak_text_strings(f, file_offsets)

            block_re = re.compile(r"^([A-Za-z]\w*)\s*\{", re.MULTILINE)
            desc_re = re.compile(r'^\s*desc\s+"([^"]*)"', re.MULTILINE)

            def _clean(text: str) -> str:
                text = re.sub(r"\[img:[^\]]+\]", "", text)
                text = re.sub(r"\[s:[^\]]*\]|\[/s\]", "", text)
                text = re.sub(r"\[c:[^\]]*\]|\[/c\]", "", text)
                return re.sub(r"\s+", " ", text).strip()

            result: dict[str, str] = {}
            for fname, (foff, fsz) in file_offsets.items():
                if not (
                    (fname.startswith("data/abilities/") or fname.startswith("data/passives/"))
                    and fname.endswith(".gon")
                ):
                    continue
                f.seek(foff)
                content = f.read(fsz).decode("utf-8", errors="replace")
                for bm in block_re.finditer(content):
                    ability_id = bm.group(1)
                    block_start = bm.end()
                    depth, idx = 1, block_start
                    while idx < len(content) and depth > 0:
                        if content[idx] == "{":
                            depth += 1
                        elif content[idx] == "}":
                            depth -= 1
                        idx += 1
                    block = content[block_start:idx - 1]
                    dm = desc_re.search(block)
                    if not dm:
                        continue
                    desc_val = dm.group(1)
                    desc_val = _resolve_game_string(desc_val, game_strings)
                    if not desc_val or desc_val == "nothing":
                        continue
                    result[ability_id.lower()] = _clean(desc_val)
        return result
    except Exception:
        return {}


def load_visual_mut_data(gpak_path: str) -> dict[str, dict[int, tuple[str, str]]]:
    """Load visual mutation data from the GPAK file.

    Returns {gon_category: {slot_id: (name, stat_desc)}}.
    """
    if not gpak_path:
        return {}
    try:
        with open(gpak_path, "rb") as f:
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

            game_strings = load_gpak_text_strings(f, file_offsets)

            result: dict[str, dict[int, tuple[str, str]]] = {}
            for fname, (foff, fsz) in file_offsets.items():
                if not (fname.startswith("data/mutations/") and fname.endswith(".gon")):
                    continue
                category = fname.split("/")[-1].replace(".gon", "")
                f.seek(foff)
                content = f.read(fsz).decode("utf-8", errors="replace")
                result[category] = _parse_mutation_gon(content, game_strings, category)
        return result
    except Exception:
        return {}


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
            with open(gpak_path, "rb") as f:
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

                game_strings = load_gpak_text_strings(f, file_offsets)

                block_re = re.compile(r"^([A-Za-z]\w*)\s*\{", re.MULTILINE)
                desc_re = re.compile(r'^\s*desc\s+"([^"]*)"', re.MULTILINE)

                def _clean(text: str) -> str:
                    text = re.sub(r"\[img:[^\]]+\]", "", text)
                    text = re.sub(r"\[s:[^\]]*\]|\[/s\]", "", text)
                    text = re.sub(r"\[c:[^\]]*\]|\[/c\]", "", text)
                    return re.sub(r"\s+", " ", text).strip()

                ability_descriptions: dict[str, str] = {}
                for fname, (foff, fsz) in file_offsets.items():
                    if not (
                        (fname.startswith("data/abilities/") or fname.startswith("data/passives/"))
                        and fname.endswith(".gon")
                    ):
                        continue
                    f.seek(foff)
                    content = f.read(fsz).decode("utf-8", errors="replace")
                    for bm in block_re.finditer(content):
                        ability_id = bm.group(1)
                        block_start = bm.end()
                        depth, idx = 1, block_start
                        while idx < len(content) and depth > 0:
                            if content[idx] == "{":
                                depth += 1
                            elif content[idx] == "}":
                                depth -= 1
                            idx += 1
                        block = content[block_start:idx - 1]
                        dm = desc_re.search(block)
                        if not dm:
                            continue
                        desc_val = dm.group(1)
                        desc_val = _resolve_game_string(desc_val, game_strings)
                        if not desc_val or desc_val == "nothing":
                            continue
                        ability_descriptions[ability_id.lower()] = _clean(desc_val)

                visual_mutations: dict[str, dict[int, tuple[str, str]]] = {}
                for fname, (foff, fsz) in file_offsets.items():
                    if not (fname.startswith("data/mutations/") and fname.endswith(".gon")):
                        continue
                    category = fname.split("/")[-1].replace(".gon", "")
                    f.seek(foff)
                    content = f.read(fsz).decode("utf-8", errors="replace")
                    visual_mutations[category] = _parse_mutation_gon(content, game_strings, category)

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
