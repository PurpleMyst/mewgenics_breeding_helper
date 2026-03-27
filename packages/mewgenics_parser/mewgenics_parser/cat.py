"""Cat data model for Mewgenics Breeding Manager."""

import struct
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import NamedTuple, Self

import lz4.block

from .binary import BinaryReader
from .constants import ROOM_DISPLAY
from .trait_dictionary import SKILLSHARE_BASE_ID, normalize_ability_key


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
    DITTO = "?"


class CatStatus(StrEnum):
    IN_HOUSE = "In House"
    ADVENTURE = "Adventure"
    GONE = "Gone"


class CatBodyPartCategory(StrEnum):
    TEXTURE = auto()
    BODY = auto()
    HEAD = auto()
    TAIL = auto()
    LEGS = auto()
    EYES = auto()
    EYEBROWS = auto()
    EARS = auto()
    MOUTH = auto()


class CatBodySlot(StrEnum):
    TEXTURE = auto()
    BODY = auto()
    HEAD = auto()
    TAIL = auto()

    LEFT_LEG = auto()
    RIGHT_LEG = auto()

    LEFT_ARM = auto()
    RIGHT_ARM = auto()

    LEFT_EYE = auto()
    RIGHT_EYE = auto()

    LEFT_EYEBROW = auto()
    RIGHT_EYEBROW = auto()

    LEFT_EAR = auto()
    RIGHT_EAR = auto()

    MOUTH = auto()

    @property
    def category(self) -> CatBodyPartCategory:
        return _SLOT_CATEGORY_MAP[self]

    @property
    def counterpart(self) -> "CatBodySlot | None":
        return _SLOT_COUNTERPART_MAP.get(self)


_SLOT_CATEGORY_MAP: dict[CatBodySlot, CatBodyPartCategory] = {
    CatBodySlot.TEXTURE: CatBodyPartCategory.TEXTURE,
    CatBodySlot.BODY: CatBodyPartCategory.BODY,
    CatBodySlot.HEAD: CatBodyPartCategory.HEAD,
    CatBodySlot.TAIL: CatBodyPartCategory.TAIL,
    CatBodySlot.LEFT_LEG: CatBodyPartCategory.LEGS,
    CatBodySlot.RIGHT_LEG: CatBodyPartCategory.LEGS,
    CatBodySlot.LEFT_ARM: CatBodyPartCategory.LEGS,
    CatBodySlot.RIGHT_ARM: CatBodyPartCategory.LEGS,
    CatBodySlot.LEFT_EYE: CatBodyPartCategory.EYES,
    CatBodySlot.RIGHT_EYE: CatBodyPartCategory.EYES,
    CatBodySlot.LEFT_EYEBROW: CatBodyPartCategory.EYEBROWS,
    CatBodySlot.RIGHT_EYEBROW: CatBodyPartCategory.EYEBROWS,
    CatBodySlot.LEFT_EAR: CatBodyPartCategory.EARS,
    CatBodySlot.RIGHT_EAR: CatBodyPartCategory.EARS,
    CatBodySlot.MOUTH: CatBodyPartCategory.MOUTH,
}

_SLOT_COUNTERPART_MAP: dict[CatBodySlot, CatBodySlot] = {
    CatBodySlot.LEFT_LEG: CatBodySlot.RIGHT_LEG,
    CatBodySlot.RIGHT_LEG: CatBodySlot.LEFT_LEG,
    CatBodySlot.LEFT_ARM: CatBodySlot.RIGHT_ARM,
    CatBodySlot.RIGHT_ARM: CatBodySlot.LEFT_ARM,
    CatBodySlot.LEFT_EYE: CatBodySlot.RIGHT_EYE,
    CatBodySlot.RIGHT_EYE: CatBodySlot.LEFT_EYE,
    CatBodySlot.LEFT_EYEBROW: CatBodySlot.RIGHT_EYEBROW,
    CatBodySlot.RIGHT_EYEBROW: CatBodySlot.LEFT_EYEBROW,
    CatBodySlot.LEFT_EAR: CatBodySlot.RIGHT_EAR,
    CatBodySlot.RIGHT_EAR: CatBodySlot.LEFT_EAR,
}


@dataclass(slots=True)
class Cat:
    """Main data model representing a cat in Mewgenics."""

    db_key: int
    """Unique identifier from the save file, used for relationships and lookups."""

    name: str
    """Cat's name, decoded from UTF-16 in the blob. Defaults to 'Unnamed' if missing."""

    name_tag: str
    """Cat's nameplate symbol/tag after the name field, set by the player arbitrarily. Can be empty."""

    gender: CatGender
    """Cat's sex, normalized from multiple possible save data representations."""

    status: CatStatus
    """Current status of the cat (In House, Adventure, or Gone), determined from save data context."""

    room: str | None
    """Current room if In House, or None if on Adventure or Gone. Decoded from save data context."""

    base_stats: Stats
    """Base heritable stats tuple (HP, STR, DEX, INT, WIS, LUK, CHA) directly from the blob."""

    total_stats: Stats
    """Total stats tuple calculated from the blob's base, levelling deltas, and injury deltas."""

    age: int | None
    """Calculated age based on birthday from the blob and current_day passed to from_blob. None if birthday is missing or invalid."""

    aggression: float | None
    """Aggression personality stat, a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    libido: float | None
    """Libido personality stat, a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    fertility: float | None
    """Fertility personality stat, numerically multiplied with a partner's fertility to influence number of kittens."""

    sexuality: float | None
    """Sexual preference personality stat, a float between 0.0 and 1.0 if valid, or None if missing/invalid."""

    active_abilities: list[str]
    """List of active abilities (movement, basic attacks, and current accessible actives) extracted from the blob's ability run."""

    passive_abilities: list[str]
    """List of current usable passive ability keys extracted from the blob's ability run, normalized to exclude junk entries."""

    disorders: list[str]
    """List of disorder and mutation passives extracted from the blob's ability run, normalized to exclude junk entries."""

    body_parts: dict[CatBodySlot, int]
    """Structured body part identifiers extracted from specific body slot indices in the blob."""

    level: int
    """The current level of the cat."""

    collar: str
    """Currently equipped collar identifier."""

    coi: float
    """Coefficient of inbreeding. Identical to values in files/pedigree."""

    parent_a: Self | None = field(default=None, repr=False)
    """Direct parent cat A, assigned after parsing based on database id references. None if unknown or not found."""

    parent_b: Self | None = field(default=None, repr=False)
    """Direct parent cat B, assigned after parsing based on database id references. None if unknown or not found."""

    lover: Self | int | None = field(default=None, repr=False)
    """Lover (SQL key of loved cat) as either a Cat object (after resolution) or int (before resolution). None if no lover."""

    hater: Self | int | None = field(default=None, repr=False)
    """Hater (SQL key of rival cat) as either a Cat object (after resolution) or int (before resolution). None if no hater."""

    @classmethod
    def _decompress_blob(cls, blob: bytes) -> bytes:
        """Decompress LZ4 compressed cat blob."""
        uncomp_size = struct.unpack("<I", blob[:4])[0]
        return lz4.block.decompress(blob[4:], uncompressed_size=uncomp_size)

    @classmethod
    def _parse_identity(
        cls, r: BinaryReader, cat_key: int
    ) -> tuple[str, str, CatGender]:
        """Parse cat identity fields: name, name_tag, and gender."""
        version = r.u32()
        assert version == 19, f"Unexpected cat blob version {version} for cat {cat_key}"
        r.skip(8)
        name = r.utf16str() or "Unnamed"
        name_tag = r.str() or ""
        gender_map = {0: CatGender.MALE, 1: CatGender.FEMALE, 2: CatGender.DITTO}
        gender = gender_map[r.u32()]
        return name, name_tag, gender

    @classmethod
    def _parse_personality(
        cls, r: BinaryReader, cat_key: int
    ) -> tuple[float, float, float, float, int | None, int | None]:
        """Parse personality fields: libido, sexuality, aggression, fertility, lover_id, hater_id."""
        r.u32()
        r.skip((8 + 8 + 8 + 5 * 8) // 8)
        _unknown_none_str = r.str()
        assert _unknown_none_str == "None"
        _unknown_one = r.u32()
        assert _unknown_one == 1, (
            f"Expected constant 1 at offset {r.pos - 4} for cat {cat_key}"
        )
        libido = r.f64()
        sexuality = r.f64()
        lover_id = r.u64()
        r.skip(8)
        aggression = r.f64()
        hater_id = r.u64()
        fertility = r.f64()
        if lover_id == 0xFFFF_FFFF:
            lover_id = None
        if hater_id == 0xFFFF_FFFF:
            hater_id = None
        r.skip(8)
        return libido, sexuality, aggression, fertility, lover_id, hater_id

    @classmethod
    def _parse_body_parts(cls, r: BinaryReader, cat_key: int) -> dict[CatBodySlot, int]:
        """Parse body parts from the blob."""
        body_slots = [r.u32() for _ in range(72)]
        body_part_indices = {
            CatBodySlot.TEXTURE: 0,
            CatBodySlot.BODY: 3,
            CatBodySlot.HEAD: 8,
            CatBodySlot.TAIL: 13,
            CatBodySlot.LEFT_LEG: 18,
            CatBodySlot.RIGHT_LEG: 23,
            CatBodySlot.LEFT_ARM: 28,
            CatBodySlot.RIGHT_ARM: 33,
            CatBodySlot.LEFT_EYE: 38,
            CatBodySlot.RIGHT_EYE: 43,
            CatBodySlot.LEFT_EYEBROW: 48,
            CatBodySlot.RIGHT_EYEBROW: 53,
            CatBodySlot.LEFT_EAR: 58,
            CatBodySlot.RIGHT_EAR: 63,
            CatBodySlot.MOUTH: 68,
        }
        body_parts = {}
        for part, i in body_part_indices.items():
            part_id = body_slots[i]
            if part_id == 0xFFFFFFFE:
                part_id = -2
            assert part_id != 0, (
                f"Expected non-zero body part ID for {part.name} at slot {i}"
            )
            body_parts[part] = part_id
        r.skip(12)
        r.str()
        r.f64()
        return body_parts

    @classmethod
    def _parse_stats(cls, r: BinaryReader) -> tuple[Stats, Stats, Stats]:
        """Parse stat fields: base, mod1 (levelling), mod2 (injuries), and total."""

        def _read_stats() -> Stats:
            return Stats(r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32())

        base_stats = _read_stats()
        stat_mod1 = _read_stats()
        stat_mod2 = _read_stats()
        total_stats = Stats(
            *(b + m + s for b, m, s in zip(base_stats, stat_mod1, stat_mod2))
        )
        r.str()
        r.i32()
        r.u8()
        r.u8()
        r.u32()
        for _ in range(r.u32()):
            r.str()
            r.u32()
        return base_stats, stat_mod1, total_stats

    @classmethod
    def _parse_abilities(
        cls, r: BinaryReader
    ) -> tuple[list[str], list[str], list[str]]:
        """Parse ability fields: actives, passives, disorders."""
        actives = [s for _ in range(6) if (s := r.str()) != "None"]
        for _ in range(4):
            r.str()
        passives = []
        for _ in range(2):
            s = r.str()
            level = r.u32()
            assert level in (1, 2)
            if s and s != "None":
                passives.append(s + (str(level) if level > 1 else ""))
        disorders = []
        for _ in range(2):
            s = r.str()
            if s and s != "None":
                disorders.append(s)
            r.skip(4)
        return actives, passives, disorders

    @staticmethod
    def _skip_equipment(r: BinaryReader, cat_key: int) -> None:
        """Skip equipment struct (5 slots)."""
        for _ in range(5):
            equip_version = r.u32()
            assert equip_version == 0x5, (
                f"Unexpected equipment version {equip_version} for cat {cat_key}"
            )
            has_equip = r.u8()
            if has_equip:
                r.str()
                r.str()
                r.skip(16)
                r.skip(2)

    @classmethod
    def from_save_data(
        cls,
        blob: bytes,
        cat_key: int,
        house_info: dict,
        adventure_keys: set,
        current_day: int | None = None,
    ):
        raw = cls._decompress_blob(blob)
        r = BinaryReader(raw)

        if cat_key in adventure_keys:
            status = CatStatus.ADVENTURE
            room = None
        elif cat_key in house_info:
            status = CatStatus.IN_HOUSE
            room = house_info[cat_key]
        else:
            status = CatStatus.GONE
            room = None

        name, name_tag, gender = cls._parse_identity(r, cat_key)
        libido, sexuality, aggression, fertility, lover_id, hater_id = (
            cls._parse_personality(r, cat_key)
        )
        body_parts = cls._parse_body_parts(r, cat_key)
        base_stats, _stat_mod1, total_stats = cls._parse_stats(r)
        actives, passives, disorders = cls._parse_abilities(r)
        cls._skip_equipment(r, cat_key)
        collar = r.str()
        level = r.i32()
        coi = r.f64()

        age: int | None = None
        birthday = r.i64()
        if current_day is not None:
            candidate = current_day - birthday
            if -2 <= candidate:
                age = candidate

        return cls(
            db_key=cat_key,
            name=name,
            name_tag=name_tag,
            gender=gender,
            status=status,
            room=room,
            base_stats=base_stats,
            total_stats=total_stats,
            age=age,
            aggression=aggression,
            libido=libido,
            fertility=fertility,
            sexuality=sexuality,
            active_abilities=actives,
            passive_abilities=passives,
            disorders=disorders,
            body_parts=body_parts,
            parent_a=None,
            parent_b=None,
            lover=lover_id,
            hater=hater_id,
            level=level,
            coi=coi,
            collar=collar,
        )

    @property
    def room_display(self) -> str:
        if (s := ROOM_DISPLAY.get(self.room or "")) is not None:
            return s
        return "N/A"

    @property
    def lover_id(self) -> int | None:
        """Return lover as int db_key, regardless of whether lover is int or Cat."""
        if self.lover is None:
            return None
        if isinstance(self.lover, Cat):
            return self.lover.db_key
        return self.lover

    @property
    def hater_id(self) -> int | None:
        """Return hater as int db_key, regardless of whether hater is int or Cat."""
        if self.hater is None:
            return None
        if isinstance(self.hater, Cat):
            return self.hater.db_key
        return self.hater

    @property
    def inheritable_actives(self) -> list[str]:
        """Returns normalized actives for inheritance math; default move abilities and basic attack can not be inherited."""
        return [normalize_ability_key(a) for a in self.active_abilities[2:]]

    @property
    def inheritable_passives(self) -> list[str]:
        """Returns normalized passives, strictly excluding SkillShare."""
        return [
            n
            for p in self.passive_abilities
            if (n := normalize_ability_key(p)) != SKILLSHARE_BASE_ID
        ]

    def has_eternal_youth(self) -> bool:
        """Check if cat has EternalYouth disorder."""
        return any(p.lower() == "eternalyouth" for p in (self.disorders or []))

    def has_birth_defects(self) -> bool:
        """Check if cat has any birth defect body parts."""
        return any(
            part_id < 0 or (700 <= part_id <= 710)
            for part_id in self.body_parts.values()
        )
