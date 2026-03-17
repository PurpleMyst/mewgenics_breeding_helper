"""Cat data model for Mewgenics Breeding Manager."""

from __future__ import annotations

import struct
import lz4.block
import math
from dataclasses import dataclass, field
from typing import Optional

from .binary import BinaryReader
from .constants import STAT_NAMES, _JUNK_STRINGS, _IDENT_RE, ROOM_DISPLAY
from .visual import (
    _read_visual_mutation_entries,
    _visual_mutation_chip_items,
    _VISUAL_MUTATION_FIELDS,
)


def _valid_str(s: Optional[str]) -> bool:
    """Reject None, empty, and game filler strings like 'none' or 'defaultmove'."""
    return bool(s) and s.strip().lower() not in _JUNK_STRINGS


def _normalize_gender(raw_gender: Optional[str]) -> str:
    """
    Normalize save-data gender variants to app-level values:
      - maleX   -> "male"
      - femaleX -> "female"
      - spidercat (ditto-like) -> "?"
    """
    g = (raw_gender or "").strip().lower()
    if g.startswith("male"):
        return "male"
    if g.startswith("female"):
        return "female"
    if g == "spidercat":
        return "?"
    return "?"


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
    unique_id: str
    name: str
    gender: str
    gender_source: str
    breed_id: int
    collar: str
    status: str
    room: str
    stat_base: list
    stat_mod: list
    stat_sec: list
    total_stats: dict
    age: Optional[int]
    aggression: Optional[float]
    libido: Optional[float]
    coi: Optional[float]
    abilities: list
    passive_abilities: list
    equipment: list
    mutations: list
    mutation_chip_items: list
    visual_mutation_entries: list
    visual_mutation_ids: list
    visual_mutation_slots: dict
    body_parts: dict
    parent_a: Optional[Cat] = field(default=None, repr=False)
    parent_b: Optional[Cat] = field(default=None, repr=False)
    children: list = field(default_factory=list, repr=False)
    lovers: list = field(default_factory=list, repr=False)
    haters: list = field(default_factory=list, repr=False)
    generation: int = field(default=0, repr=False)
    gender_token_fields: tuple
    gender_token: str
    name_tag: str

    # Private attributes (not included in dataclass repr)
    _uid_int: int = field(repr=False, default=0)
    _parent_uid_a: int = field(repr=False, default=0)
    _parent_uid_b: int = field(repr=False, default=0)
    _lover_uids: list = field(repr=False, default_factory=list)
    _hater_uids: list = field(repr=False, default_factory=list)

    def __init__(
        self,
        blob: bytes,
        cat_key: int,
        house_info: dict,
        adventure_keys: set,
        current_day: Optional[int] = None,
    ):
        uncomp_size = struct.unpack("<I", blob[:4])[0]
        raw = lz4.block.decompress(blob[4:], uncompressed_size=uncomp_size)
        r = BinaryReader(raw)

        self.db_key = cat_key

        # Location / status
        if cat_key in adventure_keys:
            self.status = "Adventure"
            self.room = "Adventure"
        elif cat_key in house_info:
            self.status = "In House"
            self.room = house_info[cat_key]
        else:
            self.status = "Gone"
            self.room = ""

        # Blob fields
        self.breed_id = r.u32()
        self._uid_int = r.u64()  # cat's own unique id (seed)
        self.unique_id = hex(self._uid_int)
        self.name = r.utf16str()

        # Optional post-name tag string (empty for most cats). Some fields below
        # are anchored to the byte immediately after this string.
        self.name_tag = r.str() or ""
        personality_anchor = r.pos

        # Possible parent UIDs — fixed-position attempt.
        # parse_save will run a blob scan as a fallback if these don't resolve.
        self._parent_uid_a = r.u64()
        self._parent_uid_b = r.u64()

        self.collar = r.str() or ""
        r.u32()

        r.skip(64)
        T = [r.u32() for _ in range(72)]
        self.body_parts = {"texture": T[0], "bodyShape": T[3], "headShape": T[8]}
        self.visual_mutation_slots = {
            slot_key: T[table_index]
            for slot_key, table_index, *_ in _VISUAL_MUTATION_FIELDS
            if table_index < len(T)
        }
        visual_entries = _read_visual_mutation_entries(T)
        visual_items = _visual_mutation_chip_items(visual_entries)
        self.visual_mutation_entries = visual_entries
        self.visual_mutation_ids = [
            int(entry["mutation_id"]) for entry in visual_entries
        ]
        visual_display_names = [text for text, _ in visual_items]

        self.gender_token_fields = tuple(r.u32() for _ in range(3))
        raw_gender = r.str()
        self.gender_token = (raw_gender or "").strip().lower()
        # Authoritative sex enum near the name block:
        #   0 = male, 1 = female, 2 = undefined/both (ditto-like)
        # This byte follows the optional post-name tag string, so use the
        # tag-aware anchor (personality_anchor), not name_end + fixed offset.
        sex_code = raw[personality_anchor] if personality_anchor < len(raw) else None
        gender_from_code = {0: "male", 1: "female", 2: "?"}.get(sex_code)
        if gender_from_code:
            self.gender = gender_from_code
            self.gender_source = "sex_code"
        else:
            self.gender = _normalize_gender(raw_gender)
            self.gender_source = "token_fallback"
        r.f64()

        self.stat_base = [r.u32() for _ in range(7)]
        self.stat_mod = [r.i32() for _ in range(7)]
        self.stat_sec = [r.i32() for _ in range(7)]

        self.total_stats = {
            n: self.stat_base[i] + self.stat_mod[i] + self.stat_sec[i]
            for i, n in enumerate(STAT_NAMES)
        }

        # Personality stats (age, aggression, libido, coi).
        # Libido and coi are doubles anchored after the post-name tag string.
        # Age is stored as creation_day at offset (blob_len - 103), then calculated as (current_day - creation_day).
        self.age = None
        self.aggression = None  # None = unknown
        self.libido = None
        self.coi = None

        def _read_personality(offset: int) -> Optional[float]:
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
        self._lover_uids = _read_db_key_candidates(
            raw, self.db_key, (48,), base_offset=personality_anchor
        )
        self._hater_uids = _read_db_key_candidates(
            raw, self.db_key, (72,), base_offset=personality_anchor
        )
        self.lovers = []
        self.haters = []
        self.children = []  # direct offspring; assigned by parse_save

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
            self.abilities = [x for x in run_items[1:6] if _valid_str(x)]

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

            self.passive_abilities = passives
            self.equipment = []  # equipment parsing requires separate byte-marker logic

        else:
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

            self.abilities = [a for a in [r.str() for _ in range(6)] if _valid_str(a)]
            self.equipment = [s for s in [r.str() for _ in range(4)] if _valid_str(s)]

            self.passive_abilities = []
            first = r.str()
            if _valid_str(first):
                self.passive_abilities.append(first)
            for _ in range(13):
                if r.remaining() < 12:
                    break
                flag = r.u32()
                if flag == 0:
                    break
                p = r.str()
                if _valid_str(p):
                    self.passive_abilities.append(p)

        self.mutations = visual_display_names
        self.mutation_chip_items = visual_items

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
                        if has_ey:
                            if 0 <= age <= 500:
                                self.age = age
                                break
                        else:
                            if 0 <= age <= 100:
                                self.age = age
                                break
            except Exception:
                pass

    @property
    def room_display(self) -> str:
        if not self.room or self.room == "Adventure":
            return self.room or ""
        return ROOM_DISPLAY.get(self.room, self.room)

    @property
    def gender_display(self) -> str:
        g = (self.gender or "").strip().lower()
        if g.startswith("male"):
            return "M"
        if g.startswith("female"):
            return "F"
        return "?"

    @property
    def can_move(self) -> bool:
        return self.status == "In House"

    @property
    def short_name(self) -> str:
        """First word of name for compact displays."""
        return self.name.split()[0] if self.name else "?"
