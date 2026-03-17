"""Cat data model for Mewgenics Breeding Manager."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeGuard

import lz4.block

from .binary import BinaryReader
from .constants import _IDENT_RE, _JUNK_STRINGS, ROOM_DISPLAY, STAT_NAMES
from .trait_dictionary import is_disorder, SKILLSHARE_BASE_ID, normalize_trait_name

Stats = tuple[int, int, int, int, int, int, int]


class CatGender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    NONBINARY = "?"


class CatStatus(StrEnum):
    IN_HOUSE = "In House"
    ADVENTURE = "Adventure"
    GONE = "Gone"


def _valid_str(s: str | None) -> TypeGuard[str]:
    """Reject None, empty, and game filler strings like 'none' or 'defaultmove'."""
    return bool(s) and s.strip().lower() not in _JUNK_STRINGS


def _split_passives_and_disorders(traits: list[str]) -> tuple[list[str], list[str]]:
    """Split a list of traits into passives and disorders."""
    passives: list[str] = []
    disorders: list[str] = []
    for t in traits:
        if is_disorder(t):
            disorders.append(t)
        else:
            passives.append(t)
    return passives, disorders


def _normalize_gender(raw_gender: str | None) -> CatGender:
    """
    Normalize save-data gender variants to app-level values:
      - maleX   -> "male"
      - femaleX -> "female"
      - spidercat (ditto-like) -> "?"
    """
    g = (raw_gender or "").strip().lower()
    if g.startswith("male"):
        return CatGender.MALE
    if g.startswith("female"):
        return CatGender.FEMALE
    return CatGender.NONBINARY


def _read_db_key_candidates(
    raw: bytes, self_key: int, offsets: tuple[int, ...], base_offset: int = 0
) -> list[int]:
    keys: list[int] = []
    for off in offsets:
        pos = base_offset + off
        if pos < 0 or pos + 4 > len(raw):
            continue
        try:
            value = struct.unpack_from("<I", raw, pos)[0]
        except Exception:
            continue
        if value in (0, 0xFFFF_FFFF) or value == self_key:
            continue
        if value not in keys:
            keys.append(value)
    return keys


@dataclass(init=False, slots=True)
class Cat:
    """Main data model representing a cat in Mewgenics."""

    db_key: int
    # unique_id: str
    name: str
    gender: CatGender
    # gender_source: str
    # breed_id: int
    # collar: str
    status: CatStatus
    room: str | None
    stat_base: Stats
    # stat_mod: list
    # stat_sec: list
    stat_total: Stats
    age: int | None

    aggression: float | None
    libido: float | None
    coi: float | None

    active_abilities: list
    passive_abilities: list
    disorders: list

    # equipment: list
    mutation_ids_by_category: dict[str, list[int]]
    # mutation_chip_items: list
    # visual_mutation_entries: list
    # visual_mutation_ids: list
    # visual_mutation_slots: dict
    # body_parts: dict
    # gender_token_fields: tuple
    # gender_token: str
    # name_tag: str

    parent_a: Cat | None = field(default=None, repr=False)
    parent_b: Cat | None = field(default=None, repr=False)
    # children: list = field(default_factory=list, repr=False)

    lovers: list = field(default_factory=list, repr=False)
    haters: list = field(default_factory=list, repr=False)

    # generation: int = field(default=0, repr=False)

    # Private attributes (not included in dataclass repr)
    # _uid_int: int = field(repr=False, default=0)
    # _parent_uid_a: int = field(repr=False, default=0)
    # _parent_uid_b: int = field(repr=False, default=0)
    # _lover_uids: list = field(repr=False, default_factory=list)
    # _hater_uids: list = field(repr=False, default_factory=list)

    def __init__(
        self,
        blob: bytes,
        cat_key: int,
        house_info: dict,
        adventure_keys: set,
        current_day: int | None = None,
    ):
        uncomp_size = struct.unpack("<I", blob[:4])[0]
        raw = lz4.block.decompress(blob[4:], uncompressed_size=uncomp_size)
        r = BinaryReader(raw)

        def _stats() -> Stats:
            return (r.u32(), r.u32(), r.u32(), r.u32(), r.u32(), r.u32(), r.u32())

        self.db_key = cat_key

        # Location / status
        if cat_key in adventure_keys:
            self.status = CatStatus.ADVENTURE
            self.room = None
        elif cat_key in house_info:
            self.status = CatStatus.IN_HOUSE
            self.room = house_info[cat_key]
        else:
            self.status = CatStatus.GONE
            self.room = None

        # Blob fields
        _breed_id = r.u32()
        _uid_int = r.u64()  # cat's own unique id (seed)
        self.name = r.utf16str() or "Unnamed"

        # Optional post-name tag string (empty for most cats). Some fields below
        # are anchored to the byte immediately after this string.
        _name_tag = r.str() or ""
        personality_anchor = r.pos

        # Possible parent UIDs — fixed-position attempt.
        # parse_save will run a blob scan as a fallback if these don't resolve.
        _parent_uid_a = r.u64()
        _parent_uid_b = r.u64()

        # ↓ this seems to always be empty so idk
        _collar = r.str() or ""
        r.u32()

        r.skip(64)
        T = [r.u32() for _ in range(72)]
        _body_parts = {"texture": T[0], "bodyShape": T[3], "headShape": T[8]}

        _MUTATION_INDICES_BY_CATEGORY = {
            "texture": [0],
            "body": [3],
            "head": [8],
            "tail": [13],
            "legs": [18, 23],
            "arms": [28, 33],
            "eyes": [38, 43],
            "eyebrows": [48, 53],
            "ears": [58, 63],
            "mouth": [68],
        }
        self.mutation_ids_by_category = {
            category: [T[i] for i in indices if i < len(T)]
            for category, indices in _MUTATION_INDICES_BY_CATEGORY.items()
        }

        _gender_token_fields = tuple(r.u32() for _ in range(3))
        raw_gender = r.str()
        _gender_token = (raw_gender or "").strip().lower()
        # Authoritative sex enum near the name block:
        #   0 = male, 1 = female, 2 = undefined/both (ditto-like)
        # This byte follows the optional post-name tag string, so use the
        # tag-aware anchor (personality_anchor), not name_end + fixed offset.
        sex_code: int | None = (
            raw[personality_anchor] if personality_anchor < len(raw) else None
        )
        gender_from_code: CatGender | None = {
            0: CatGender.MALE,
            1: CatGender.FEMALE,
            2: CatGender.NONBINARY,
        }.get(sex_code)  # type: ignore[call-overload]
        if gender_from_code:
            self.gender = gender_from_code
            # self.gender_source = "sex_code"
        else:
            self.gender = _normalize_gender(raw_gender)
            # self.gender_source = "token_fallback"
        r.f64()

        self.stat_base = _stats()
        stat_mod = _stats()
        stat_sec = _stats()
        self.stat_total = tuple(
            b + m + s for b, m, s in zip(self.stat_base, stat_mod, stat_sec)
        )

        # Personality stats (age, aggression, libido, coi).
        # Libido and coi are doubles anchored after the post-name tag string.
        # Age is stored as creation_day at offset (blob_len - 103), then calculated as (current_day - creation_day).
        self.age = None
        self.aggression = None  # None = unknown
        self.libido = None
        self.coi = None

        def _read_personality(offset: int) -> float | None:
            i = personality_anchor + offset
            if i + 8 > len(raw):
                return None
            try:
                v = struct.unpack_from("<d", raw, i)[0]
            except Exception:
                return None
            if not math.isfinite(v) or not (0.0 <= v <= 1.0):
                return None
            return float(v)

        self.libido = _read_personality(32)
        self.coi = _read_personality(40)
        self.aggression = _read_personality(64)

        # Relationship slots: direct db_key references relative to the byte
        # immediately after the optional post-name tag string.
        _lover_uids = _read_db_key_candidates(
            raw, self.db_key, (48,), base_offset=personality_anchor
        )
        _hater_uids = _read_db_key_candidates(
            raw, self.db_key, (72,), base_offset=personality_anchor
        )
        self.lovers = []
        self.haters = []
        # self.children = []  # direct offspring; assigned by parse_save

        # ── Ability run — anchored on "DefaultMove" ─────────────────────────
        # The ability block is a u64-length-prefixed ASCII identifier run.
        # Structure (from open-source editor research):
        #   items[0]  = "DefaultMove"  (active slot 1 default)
        #   items[1-5] = active abilities 2-6
        #   items[6-9] = padding / unknown slots
        #   items[10]  = Passive1 mutation  (e.g. "Sturdy", "Longshot")
        #   After run:  u32 tier, then 3 × [u64 id][u32 tier] tail entries
        #               = Passive2, Disorder1, Disorder2
        curr = r.pos
        run_start = -1
        for i in range(curr, min(curr + 600, len(raw) - 19)):
            lo = struct.unpack_from("<I", raw, i)[0]
            hi = struct.unpack_from("<I", raw, i + 4)[0]
            if hi != 0 or not (1 <= lo <= 96):
                continue
            try:
                cand = raw[i + 8 : i + 8 + lo].decode("ascii")
                if cand == "DefaultMove":
                    run_start = i
                    break
            except Exception:
                continue

        if run_start != -1:
            r.seek(run_start)
            # Read the full run until a non-identifier is encountered
            run_items: list[str] = []
            for _ in range(32):
                saved = r.pos
                item = r.str()
                if item is None or not _IDENT_RE.match(item):
                    r.seek(saved)
                    break
                run_items.append(item)

            # Active abilities: items[1-5] (skip DefaultMove at [0])
            self.active_abilities = [x for x in run_items[1:6] if _valid_str(x)]

            # Passive1 is in run_items[10] (if the run is long enough)
            passives: list[str] = []
            for ri in run_items[10:]:
                if _valid_str(ri):
                    passives.append(ri)

            # After run: [u32 tier][string][u32 tier][string]...
            # Passive1 tier, then Passive2, Disorder1, Disorder2 each with tier.
            # Skip Passive1's tier first, then read 3 more string+tier pairs.
            try:
                r.u32()  # passive1 tier — discard
            except Exception:
                pass

            for _ in range(3):
                try:
                    item = r.str()
                except Exception:
                    break
                if item is not None and _IDENT_RE.match(item) and _valid_str(item):
                    if item not in passives:
                        passives.append(item)
                # Skip tier regardless of whether string was valid/junk
                try:
                    r.u32()
                except Exception:
                    break

            self.passive_abilities, self.disorders = _split_passives_and_disorders(
                passives
            )
            _equipment = []  # equipment parsing requires separate byte-marker logic

        else:
            raise RuntimeError

            # Fallback: old heuristic scan for any uppercase-starting ASCII string
            found = -1
            for i in range(curr, min(curr + 500, len(raw) - 9)):
                length = struct.unpack_from("<I", raw, i)[0]
                if (
                    0 < length < 64
                    and struct.unpack_from("<I", raw, i + 4)[0] == 0
                    and 65 <= raw[i + 8] <= 90
                ):
                    found = i
                    break
            if found != -1:
                r.seek(found)

            self.active_abilities = [
                a for a in [r.str() for _ in range(6)] if _valid_str(a)
            ]
            self.equipment = [s for s in [r.str() for _ in range(4)] if _valid_str(s)]

            all_passives: list[str] = []
            first = r.str()
            if _valid_str(first):
                all_passives.append(first)
            for _ in range(13):
                if r.remaining() < 12:
                    break
                flag = r.u32()
                if flag == 0:
                    break
                p = r.str()
                if _valid_str(p):
                    all_passives.append(p)

            self.passive_abilities, self.disorders = _split_passives_and_disorders(
                all_passives
            )

        # _mutation_chip_items = visual_items

        # Extract age from creation_day stored near the end of the blob (around blob_len - 103).
        # Search a small window around the typical offset to handle varying blob structures.
        if current_day is not None:
            try:
                # Try positions from blob_len-100 to blob_len-110, preferring closer to -103
                for offset_from_end in [
                    103,
                    102,
                    104,
                    101,
                    105,
                    100,
                    106,
                    107,
                    108,
                    109,
                    110,
                ]:
                    pos = len(raw) - offset_from_end
                    if pos + 4 > len(raw) or pos < 0:
                        continue
                    creation_day = struct.unpack_from("<I", raw, pos)[0]
                    # Valid creation_day should be between 0 and current_day
                    if 0 <= creation_day <= current_day:
                        age = current_day - creation_day
                        # Check if cat has EternalYouth
                        has_ey = any(
                            p.lower() == "eternalyouth"
                            for p in (self.passive_abilities or [])
                        )
                        # Cap age at 100 unless cat has EternalYouth
                        age_limit = 500 if has_ey else 100
                        if 0 <= age <= age_limit:
                            self.age = age
                            break
            except Exception:
                pass

    @property
    def room_display(self) -> str:
        if (s := ROOM_DISPLAY.get(self.room or "")) is not None:
            return s
        return "N/A"

    @property
    def inheritable_abilities(self) -> list[str]:
        """Returns normalized abilities for inheritance math."""
        return [normalize_trait_name(a) for a in self.active_abilities]

    @property
    def inheritable_passives(self) -> list[str]:
        """Returns normalized passives, strictly excluding SkillShare."""
        return [
            n
            for p in self.passive_abilities
            if (n := normalize_trait_name(p)) != SKILLSHARE_BASE_ID
        ]

    @property
    def all_normalized_traits(self) -> set[str]:
        """Returns a unified set of all normalized abilities, passives, and mutations."""
        traits: set[str] = set()
        traits.update(
            normalize_trait_name(t) for t in (self.active_abilities or [])
        )
        traits.update(
            normalize_trait_name(t) for t in (self.passive_abilities or [])
        )
        # traits.update(normalize_trait_name(t) for t in (self.mutations or []))
        return traits
