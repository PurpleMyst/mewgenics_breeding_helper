"""Cat data model for Mewgenics Breeding Manager."""

from __future__ import annotations

import math
import struct
# import warnings
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import NamedTuple, TypeGuard

import lz4.block

from .binary import BinaryReader
from .constants import _IDENT_RE, _JUNK_STRINGS, ROOM_DISPLAY
from .trait_dictionary import SKILLSHARE_BASE_ID, is_disorder, normalize_ability_key


class Stats(NamedTuple):
    """Structured representation of a cat's stats."""

    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    speed: int
    charisma: int
    luck: int


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


class CatBodyPartCategory(StrEnum):
    TEXTURE = "texture"
    BODY = "body"
    HEAD = "head"
    TAIL = "tail"
    LEGS = "legs"
    ARMS = "arms"
    EYES = "eyes"
    EYEBROWS = "eyebrows"
    EARS = "ears"
    MOUTH = "mouth"


@dataclass(slots=True, frozen=True)
class CatBodyParts:
    """Structured representation of a cat's body part identifiers."""

    texture: int
    body: int
    head: int
    tail: int
    legs: int
    arms: int
    eyes: int
    eyebrows: int
    ears: int
    mouth: int


@dataclass(slots=True)
class Cat:
    """Main data model representing a cat in Mewgenics."""

    db_key: int
    """Unique identifier from the save file, used for relationships and lookups."""

    name: str
    """Cat's name, decoded from UTF-16 in the blob. Defaults to 'Unnamed' if missing."""

    gender: CatGender
    """Cat's gender, normalized from multiple possible save data representations."""

    status: CatStatus
    """Current status of the cat (In House, Adventure, or Gone), determined from save data context."""

    room: str | None
    """Current room if In House, or None if on Adventure or Gone. Decoded from save data context."""

    stat_base: Stats
    """Base stats tuple (HP, STR, DEX, INT, WIS, LUK, CHA) directly from the blob."""

    stat_total: Stats
    """Total stats tuple (base + modifiers) calculated from the blob's base, mod, and sec stat groups."""

    age: int | None
    """Calculated age based on creation_day from the blob and current_day passed to from_blob. Capped at 100 unless EternalYouth is present, in which case capped at 500. None if creation_day is missing or invalid."""

    aggression: float | None
    """Aggression personality stat, a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    libido: float | None
    """Libido personality stat, a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    coi: float | None
    """Coefficient of Inbreeding (COI), a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    active_abilities: list[str]
    """List of active ability keys extracted from the blob's ability run, normalized to exclude junk entries."""

    passive_abilities: list[str]
    """List of passive ability keys extracted from the blob's ability run, normalized to exclude junk entries."""

    disorders: list[str]
    """List of disorder keys extracted from the blob's ability run, normalized to exclude junk entries."""

    body_parts: CatBodyParts
    """Structured body part identifiers extracted from specific body slot indices in the blob."""

    parent_a: Cat | None
    """Direct parent cat A, assigned after parsing based on UID references. None if unknown or not found."""

    parent_b: Cat | None
    """Direct parent cat B, assigned after parsing based on UID references. None if unknown or not found."""

    lovers: list[Cat]
    """List of lover cats, assigned after parsing based on UID references. Empty if none or unknown."""

    haters: list[Cat]
    """List of hater cats, assigned after parsing based on UID references. Empty if none or unknown."""

    @classmethod
    def from_blob(
        cls,
        blob: bytes,
        cat_key: int,
        house_info: dict,
        adventure_keys: set,
        current_day: int | None = None,
    ):
        uncomp_size = struct.unpack("<I", blob[:4])[0]
        raw = lz4.block.decompress(blob[4:], uncompressed_size=uncomp_size)
        r = BinaryReader(raw)

        def _stats(*, signed: bool) -> Stats:
            n = r.i32 if signed else r.u32
            return Stats(n(), n(), n(), n(), n(), n(), n())

        db_key = cat_key

        # Location / status
        if cat_key in adventure_keys:
            status = CatStatus.ADVENTURE
            room = None
        elif cat_key in house_info:
            status = CatStatus.IN_HOUSE
            room = house_info[cat_key]
        else:
            status = CatStatus.GONE
            room = None

        # Blob fields
        _breed_id = r.u32()
        _uid_int = r.u64()  # cat's own unique id (seed)
        name = r.utf16str() or "Unnamed"

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

        body_slots = [r.u32() for _ in range(72)]
        body_part_indices = {
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
        body_part_values = {}
        for part, indices in body_part_indices.items():
            value = 0
            for i in indices:
                if i < len(body_slots):
                    new_value = body_slots[i]
                    if new_value == 0:
                        continue
                    # if value != 0 and new_value != value:
                    #     warnings.warn(
                    #         f"Conflicting values for {part} for cat {db_key}: {value} vs {new_value}"
                    #     )
                    value = new_value
            body_part_values[part] = value
        body_parts = CatBodyParts(
            texture=body_part_values.get("texture", 0),
            body=body_part_values.get("body", 0),
            head=body_part_values.get("head", 0),
            tail=body_part_values.get("tail", 0),
            legs=body_part_values.get("legs", 0),
            arms=body_part_values.get("arms", 0),
            eyes=body_part_values.get("eyes", 0),
            eyebrows=body_part_values.get("eyebrows", 0),
            ears=body_part_values.get("ears", 0),
            mouth=body_part_values.get("mouth", 0),
        )

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
            gender = gender_from_code
            # gender_source = "sex_code"
        else:
            gender = _normalize_gender(raw_gender)
            # gender_source = "token_fallback"
        r.f64()

        stat_base = _stats(signed=False)
        stat_mod = _stats(signed=True)
        stat_sec = _stats(signed=True)
        stat_total = Stats(
            *(b + m + s for b, m, s in zip(stat_base, stat_mod, stat_sec))
        )

        # Personality stats (age, aggression, libido, coi).
        # Libido and coi are doubles anchored after the post-name tag string.
        # Age is stored as creation_day at offset (blob_len - 103), then calculated as (current_day - creation_day).
        age = None
        aggression = None  # None = unknown
        libido = None
        coi = None

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

        libido = _read_personality(32)
        coi = _read_personality(40)
        aggression = _read_personality(64)

        # Relationship slots: direct db_key references relative to the byte
        # immediately after the optional post-name tag string.
        _lover_uids = _read_db_key_candidates(
            raw, db_key, (48,), base_offset=personality_anchor
        )
        _hater_uids = _read_db_key_candidates(
            raw, db_key, (72,), base_offset=personality_anchor
        )
        lovers = []
        haters = []
        # children = []  # direct offspring; assigned by parse_save

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
            active_abilities = [x for x in run_items[1:6] if _valid_str(x)]

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

            passive_abilities, disorders = _split_passives_and_disorders(passives)
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

            active_abilities = [a for a in [r.str() for _ in range(6)] if _valid_str(a)]
            _equipment = [s for s in [r.str() for _ in range(4)] if _valid_str(s)]

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

            passive_abilities, disorders = _split_passives_and_disorders(all_passives)

        # _mutation_chip_items = visual_items

        # Extract age from creation_day stored near the end of the blob (around blob_len - 103).
        # Search a small window around the typical offset to handle varying blob structures.
        if current_day is not None:
            has_ey = any(p.lower() == "eternalyouth" for p in disorders)
            # Cap age at 100 unless cat has EternalYouth
            age_limit = 500 if has_ey else 100
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
                        if 0 <= age <= age_limit:
                            age = age
                            break
            except Exception as e:
                warnings.warn(f"Failed to extract age for cat {db_key}: {e}")

        return cls(
            db_key=db_key,
            name=name,
            gender=gender,
            status=status,
            room=room,
            stat_base=stat_base,
            stat_total=stat_total,
            age=age,
            aggression=aggression,
            libido=libido,
            coi=coi,
            active_abilities=active_abilities,
            passive_abilities=passive_abilities,
            disorders=disorders,
            body_parts=body_parts,
            parent_a=None,
            parent_b=None,
            lovers=lovers,
            haters=haters,
        )

    @property
    def room_display(self) -> str:
        if (s := ROOM_DISPLAY.get(self.room or "")) is not None:
            return s
        return "N/A"

    @property
    def inheritable_abilities(self) -> list[str]:
        """Returns normalized abilities for inheritance math."""
        return [normalize_ability_key(a) for a in self.active_abilities]

    @property
    def inheritable_passives(self) -> list[str]:
        """Returns normalized passives, strictly excluding SkillShare."""
        return [
            n
            for p in self.passive_abilities
            if (n := normalize_ability_key(p)) != SKILLSHARE_BASE_ID
        ]

    @property
    def body_part_keys(self) -> list[str]:
        """Returns body part identifiers as normalized trait keys for inheritance math."""
        return [
            f"{category.title()}{id}"
            for category, id in asdict(self.body_parts).items()
        ]

    @property
    def all_normalized_traits(self) -> set[str]:
        """Returns a unified set of all normalized abilities, passives, disorders, and body part keys for this cat."""
        traits: set[str] = set()
        traits.update(normalize_ability_key(t) for t in self.active_abilities)
        traits.update(normalize_ability_key(t) for t in self.passive_abilities)
        traits.update(normalize_ability_key(t) for t in self.disorders)
        traits.update(self.body_part_keys)
        return traits
