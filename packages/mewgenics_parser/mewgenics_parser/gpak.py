"""GPAK file parsing utilities."""

import csv
import io
import re
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Self

from .utils import (
    NameAndDescription,
    _clean_game_text,
    _parse_gon_to_dicts,
    _resolve_game_string,
)


def _parse_gon_abilities(
    content: str, game_strings: dict[str, str]
) -> dict[str, NameAndDescription]:
    """Parse ability GON content into {ability_id: NameAndDescription}."""

    d = _parse_gon_to_dicts(content)
    result: dict[str, NameAndDescription] = {}
    for ability_id, data in d.items():
        if not isinstance(data, dict):
            continue

        # Seems to be that templates have their data under a "meta" key, IDK man.
        raw_name = data.get("name", data.get("meta", {}).get("name", ""))
        name = (
            _clean_game_text(
                _resolve_game_string(raw_name, game_strings)
            )
        )

        raw_desc = data.get("desc", data.get("meta", {}).get("desc", ""))
        desc = _clean_game_text(
            _resolve_game_string(raw_desc, game_strings)
        )

        # If both name and description are empty, try to look under variant_of or just go with sane
        # defaults.
        if not name or not desc:
            variant_of = data.get("variant_of", "")
            if isinstance(variant_of, str) and variant_of in result:
                name = name or result[variant_of].name
                desc = desc or result[variant_of].description

        name = name or ability_id

        # Load upgraded versions of the ability (e.g., "Fireball2" for "Fireball+") if they exist in
        # the GON data, using the same description if not specified.
        for i in range(2, 10):
            if str(i) in data:
                result[f"{ability_id}{i}"] = NameAndDescription(
                    name=_clean_game_text(
                        _resolve_game_string(
                            data[str(i)].get("name", f"{name}{'+' * (i - 1)}"),
                            game_strings,
                        )
                    ),
                    description=_clean_game_text(
                        _resolve_game_string(
                            data[str(i)].get("desc", desc), game_strings
                        )
                    ),
                )

        result[ability_id] = NameAndDescription(name=name, description=desc)
    return result


def _parse_mutation_gon(
    content: str, game_strings: dict[str, str], category: str
) -> DefaultDict[int, NameAndDescription]:
    """Parse a mutation GON file into {mutation_id: NameAndDescription}."""
    d = _parse_gon_to_dicts(content)
    result: dict[int, NameAndDescription] = {}
    for mutation_id_str, data in d.items():
        if not isinstance(data, dict):
            continue
        try:
            mutation_id = int(mutation_id_str)
        except ValueError:
            continue
        name_val = _clean_game_text(
            _resolve_game_string(
                data.get("name", f"{category.title()} Mutation {mutation_id}"),
                game_strings,
            )
        )
        desc_val = _clean_game_text(
            _resolve_game_string(data.get("desc", ""), game_strings)
        )
        if not name_val and not desc_val:
            continue
        result[mutation_id] = NameAndDescription(name=name_val, description=desc_val)
    return defaultdict(lambda: NameAndDescription(), result)


def _load_gpak_text_strings(gon_contents: dict[str, str]) -> dict[str, str]:
    """Load text strings from CSV files in the GPAK."""
    strings: dict[str, str] = {}
    for fname, raw_csv in gon_contents.items():
        if not (fname.startswith("data/text/") and fname.endswith(".csv")):
            continue
        for row in csv.reader(io.StringIO(raw_csv)):
            if len(row) >= 2 and row[0] and not row[0].startswith("//"):
                strings[row[0]] = row[1]
    return strings


@dataclass(slots=True)
class GameData:
    """Bundle of all GPAK game data."""

    ability_text: DefaultDict[str, NameAndDescription]
    mutation_text_by_part_and_id: DefaultDict[str, DefaultDict[int, NameAndDescription]]
    game_strings: dict[str, str]

    @classmethod
    def from_gpak(cls, gpak_path: str) -> Self:
        """Load all data from the GPAK file."""
        with open(gpak_path, "rb") as f:
            # Parse the directory at the start of the file; length of entries is a 4-byte LE int,
            # followed by that many entries of:
            # - name length (2-byte LE int)
            # - name (UTF-8 string)
            # - size (4-byte LE int)
            count = struct.unpack("<I", f.read(4))[0]
            entries = []
            for _ in range(count):
                name_len = struct.unpack("<H", f.read(2))[0]
                name = f.read(name_len).decode("utf-8", errors="replace")
                size = struct.unpack("<I", f.read(4))[0]
                entries.append((name, size))
            dir_end = f.tell()

            # Compute file offsets based on the sizes in the directory
            file_offsets: dict[str, tuple[int, int]] = {}
            offset = dir_end
            for name, size in entries:
                file_offsets[name] = (offset, size)
                offset += size

            # Read all .gon files into memory at once
            gon_contents: dict[str, str] = {}
            with open(gpak_path, "rb") as f:
                for fname in file_offsets:
                    if not fname.endswith(".gon") and not (
                        fname.startswith("data/text/") and fname.endswith(".csv")
                    ):
                        continue
                    foff, fsz = file_offsets[fname]
                    f.seek(foff)
                    gon_contents[fname] = f.read(fsz).decode("utf-8", errors="replace")

        game_strings = _load_gpak_text_strings(gon_contents)

        ability_descriptions: dict[str, NameAndDescription] = {}
        for fname, content in gon_contents.items():
            if (
                fname.startswith("data/abilities/")
                or fname.startswith("data/passives/")
                and fname.endswith(".gon")
            ):
                ability_descriptions.update(_parse_gon_abilities(content, game_strings))

        mutation_text: dict[str, DefaultDict[int, NameAndDescription]] = {}
        for fname, content in gon_contents.items():
            if fname.startswith("data/mutations/") and fname.endswith(".gon"):
                category = fname.split("/")[-1].replace(".gon", "")
                mutation_text[category] = _parse_mutation_gon(
                    content, game_strings, category
                )

        return cls(
            ability_text=defaultdict(
                lambda: NameAndDescription(),
                ability_descriptions,
            ),
            mutation_text_by_part_and_id=defaultdict(
                lambda: defaultdict(lambda: NameAndDescription()),
                mutation_text,
            ),
            game_strings=game_strings,
        )
