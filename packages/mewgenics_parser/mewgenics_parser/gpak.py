"""GPAK file parsing utilities."""

from mewgenics_parser.constants import STAT_NAMES

import csv
import io
import struct
import zipfile
from collections import defaultdict
from dataclasses import dataclass
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
    for ability_id, ability_info in d.items():
        if not isinstance(ability_info, dict):
            continue

        # Seems to be that templates have their data under a "meta" key, IDK man.
        raw_name = ability_info.get("name", ability_info.get("meta", {}).get("name", ""))
        name = _clean_game_text(_resolve_game_string(raw_name, game_strings))

        raw_desc = ability_info.get("desc", ability_info.get("meta", {}).get("desc", ""))
        desc = _clean_game_text(_resolve_game_string(raw_desc, game_strings))

        # If both name and description are empty, try to look under variant_of or just go with sane
        # defaults.
        if not name or not desc:
            variant_of = ability_info.get("variant_of", "")
            if isinstance(variant_of, str) and variant_of in result:
                name = name or result[variant_of].name
                desc = desc or result[variant_of].description

        name = name or ability_id

        # TODO: This is just lazily copy-pasted from the mutation parsing code, it should be adapted
        # to an helper + it should be handled for upgraded abilities as well.
        stat_descriptions = []
        for stat_name in STAT_NAMES:
            # XXX: ↑ The body part GON files have the stat changes directly under the mutation
            # entry, but the ability GON files have them nested under "stats", so we need to check
            # both places.
            stat_change = ability_info.get("stats", {}).get(stat_name.lower())
            if isinstance(stat_change, int):
                stat_descriptions.append(f"{stat_change:+} {stat_name}")
        if stat_descriptions:
            desc += (" " if desc else "") + ", ".join(stat_descriptions)

        # Load upgraded versions of the ability (e.g., "Fireball2" for "Fireball+") if they exist in
        # the GON data, using the same description if not specified.
        for i in range(2, 10):
            if str(i) in ability_info:
                result[f"{ability_id}{i}"] = NameAndDescription(
                    name=_clean_game_text(
                        _resolve_game_string(
                            ability_info[str(i)].get("name", f"{name}{'+' * (i - 1)}"),
                            game_strings,
                        )
                    ),
                    description=_clean_game_text(
                        _resolve_game_string(
                            ability_info[str(i)].get("desc", desc), game_strings
                        )
                    ),
                )

        result[ability_id] = NameAndDescription(name=name, description=desc)
    return result


def _parse_mutation_gon(
    content: str, game_strings: dict[str, str]
) -> dict[str, DefaultDict[int, NameAndDescription]]:
    """Parse a mutation GON file into {mutation_id: NameAndDescription}."""
    gon_data = _parse_gon_to_dicts(content)
    result = {}
    for category, mutations in gon_data.items():
        category_text: dict[int, NameAndDescription] = {}
        for mutation_id_str, mutation_info in mutations.items():
            if not isinstance(mutation_info, dict):
                continue
            try:
                mutation_id = int(mutation_id_str)
            except ValueError:
                continue
            name = _clean_game_text(
                _resolve_game_string(
                    mutation_info.pop(
                        "name", f"{category.title()} Mutation {mutation_id}"
                    ),
                    game_strings,
                )
            ).title()
            desc = _clean_game_text(
                _resolve_game_string(mutation_info.pop("desc", ""), game_strings)
            )

            # Mutations with complex effects usually have a description, while the ones that simply
            # add a stat bonus/malus often have an empty description and just list the bonus/malus
            # in the mutation_info, leaving the description field empty. In that case, we can try to
            # construct a more informative description from the mutation_info.
            stat_descriptions = []
            for stat_name in STAT_NAMES:
                stat_change = mutation_info.get(stat_name.lower())
                if isinstance(stat_change, int):
                    stat_descriptions.append(f"{stat_change:+} {stat_name}")
            if stat_descriptions:
                desc += (" " if desc else "") + ", ".join(stat_descriptions)
            if category.casefold() not in name.casefold():
                name = f"{name} ({category.title()})"

            category_text[mutation_id] = NameAndDescription(name=name, description=desc)
        result[category] = defaultdict(lambda: NameAndDescription(), category_text)
    return result


def _load_game_strings(gon_contents: dict[str, str]) -> dict[str, str]:
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
    """Mapping of ability ID (e.g., "Fireball") to its name and description."""

    body_part_text: DefaultDict[str, DefaultDict[int, NameAndDescription]]
    """Mapping of body part category (e.g., "arm") to mapping of mutation ID to name and description."""

    game_strings: dict[str, str]
    """Mapping of game string ID to its text content, loaded from CSV files in the GPAK."""

    @classmethod
    def from_gpak(cls, gpak_path: str) -> Self:
        """Load all data from the GPAK file."""
        gon_contents = cls.read_gon_contents(gpak_path)
        game_strings = _load_game_strings(gon_contents)

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
                mutation_text.update(_parse_mutation_gon(content, game_strings))

        # HACK: Arms do not exist as a separate category in the GON files, but mutations that would
        # be categorized as arms are instead categorized under legs. To avoid
        # confusion, we can just copy the leg mutations to arms as well.
        if "arms" not in mutation_text and "legs" in mutation_text:
            mutation_text["arms"] = mutation_text["legs"]

        return cls(
            ability_text=defaultdict(
                lambda: NameAndDescription(),
                ability_descriptions,
            ),
            body_part_text=defaultdict(
                lambda: defaultdict(lambda: NameAndDescription()),
                mutation_text,
            ),
            game_strings=game_strings,
        )

    @staticmethod
    def read_gon_contents(gpak_path: str) -> dict[str, str]:
        """Read GON file contents from the GPAK."""
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
            for fname in file_offsets:
                if not fname.endswith(".gon") and not (
                    fname.startswith("data/text/") and fname.endswith(".csv")
                ):
                    continue
                foff, fsz = file_offsets[fname]
                f.seek(foff)
                gon_contents[fname] = f.read(fsz).decode("utf-8", errors="replace")

            return gon_contents

    @classmethod
    def empty(cls) -> Self:
        return cls(
            ability_text=defaultdict(lambda: NameAndDescription()),
            body_part_text=defaultdict(lambda: defaultdict(lambda: NameAndDescription())),
            game_strings={},
        )

    @classmethod
    def extract_and_dump(cls, gpak_path: str, output_path: str) -> None:
        """Create a zip file containing all GON and CSV files extracted from the GPAK."""
        gon_contents = cls.read_gon_contents(gpak_path)
        with zipfile.ZipFile(output_path, "w") as zf:
            for fname, content in gon_contents.items():
                if fname.endswith(".gon") or (
                    fname.startswith("data/text/") and fname.endswith(".csv")
                ):
                    zf.writestr(fname, content)
