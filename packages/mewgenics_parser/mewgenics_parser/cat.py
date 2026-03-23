"""Cat data model for Mewgenics Breeding Manager."""

import struct
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import NamedTuple, Self, TypeGuard

import lz4.block

from .binary import BinaryReader
from .constants import _JUNK_STRINGS, ROOM_DISPLAY
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


def _valid_str(s: str | None) -> TypeGuard[str]:
    """Reject None, empty, and game filler strings like 'none' or 'defaultmove'."""
    return bool(s) and s.strip().lower() not in _JUNK_STRINGS


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
        match self:
            case CatBodySlot.TEXTURE:
                return CatBodyPartCategory.TEXTURE
            case CatBodySlot.BODY:
                return CatBodyPartCategory.BODY
            case CatBodySlot.HEAD:
                return CatBodyPartCategory.HEAD
            case CatBodySlot.TAIL:
                return CatBodyPartCategory.TAIL
            case CatBodySlot.LEFT_LEG | CatBodySlot.RIGHT_LEG:
                return CatBodyPartCategory.LEGS
            case CatBodySlot.LEFT_ARM | CatBodySlot.RIGHT_ARM:
                return CatBodyPartCategory.LEGS
            case CatBodySlot.LEFT_EYE | CatBodySlot.RIGHT_EYE:
                return CatBodyPartCategory.EYES
            case CatBodySlot.LEFT_EYEBROW | CatBodySlot.RIGHT_EYEBROW:
                return CatBodyPartCategory.EYEBROWS
            case CatBodySlot.LEFT_EAR | CatBodySlot.RIGHT_EAR:
                return CatBodyPartCategory.EARS
            case CatBodySlot.MOUTH:
                return CatBodyPartCategory.MOUTH

    @property
    def counterpart(self) -> "CatBodySlot | None":
        """Return the counterpart slot for this body part, if it exists (e.g. left vs right)."""
        match self:
            case CatBodySlot.LEFT_LEG:
                return CatBodySlot.RIGHT_LEG
            case CatBodySlot.RIGHT_LEG:
                return CatBodySlot.LEFT_LEG
            case CatBodySlot.LEFT_ARM:
                return CatBodySlot.RIGHT_ARM
            case CatBodySlot.RIGHT_ARM:
                return CatBodySlot.LEFT_ARM
            case CatBodySlot.LEFT_EYE:
                return CatBodySlot.RIGHT_EYE
            case CatBodySlot.RIGHT_EYE:
                return CatBodySlot.LEFT_EYE
            case CatBodySlot.LEFT_EYEBROW:
                return CatBodySlot.RIGHT_EYEBROW
            case CatBodySlot.RIGHT_EYEBROW:
                return CatBodySlot.LEFT_EYEBROW
            case CatBodySlot.LEFT_EAR:
                return CatBodySlot.RIGHT_EAR
            case CatBodySlot.RIGHT_EAR:
                return CatBodySlot.LEFT_EAR
            case _:
                return None


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

    stat_base: Stats
    """Base heritable stats tuple (HP, STR, DEX, INT, WIS, LUK, CHA) directly from the blob."""

    stat_total: Stats
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
    def from_save_data(
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

        def _stats() -> Stats:
            return Stats(r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32())

        # ── Location / status ───────────────────────────────────────────────────
        if cat_key in adventure_keys:
            status = CatStatus.ADVENTURE
            room = None
        elif cat_key in house_info:
            status = CatStatus.IN_HOUSE
            room = house_info[cat_key]
        else:
            status = CatStatus.GONE
            room = None

        # ── Identity ────────────────────────────────────────────────────────────
        version = r.u32()
        assert version == 19, f"Unexpected cat blob version {version} for cat {cat_key}"

        # Entropy: Random bits rolled when a cat/kitten is generated.
        # Hashed to select a picture pose in the family tree viewer.
        r.skip(8)

        name = r.utf16str() or "Unnamed"
        name_tag = r.str() or ""  # nameplate_symbol

        gender: CatGender = {
            0: CatGender.MALE,
            1: CatGender.FEMALE,
            2: CatGender.DITTO,
        }[r.u32()]

        # ── Personality ─────────────────────────────────────────────────────────
        # Sex duplicate field - appears to carry the same value as Sex
        _gender_dup = r.u32()

        # Skip over boolean status bitfields (StatusFlagsB0 through StatusFlagsB3To7).
        # These flag whether a cat cannot adventure, returned, is starving, dead, donated, etc.
        r.skip((8 + 8 + 8 + 5 * 8) // 8)

        # unknown_2 and unknown_3 could form a passive ability structure ("None", 1)
        # It's referenced as a base pointer but not functionally used in current decomp database
        _unknown_none_str = r.str()
        assert _unknown_none_str == "None"

        _unknown_one = r.u32()
        assert _unknown_one == 1, (
            f"Expected constant 1 at offset {r.pos - 4} for cat {cat_key}, got {_unknown_one}"
        )

        libido = r.f64()
        sexuality = r.f64()
        lover_id = r.u64()
        r.skip(8)  # unknown_7: Nonzero with a valid lover cat (could be affinity?)

        aggression = r.f64()
        hater_id = r.u64()

        fertility = r.f64()

        # The game uses 0xFFFFFFFF as a null sentinel for relationship slots.
        if lover_id == 0xFFFF_FFFF:
            lover_id = None
        if hater_id == 0xFFFF_FFFF:
            hater_id = None

        r.skip(8)  # unknown_9: Nonzero with a valid rival cat (could be affinity?)

        # ── Body parts ──────────────────────────────────────────────────────────
        # 72 slots of u32 body part IDs. Only specific indices are meaningful;
        # pairs of indices (e.g. legs at 18 and 23) should agree — we take the
        # last non-zero value across each part's indices.
        body_slots = [r.u32() for _ in range(72)]

        # Validated indices mapping to BodyParts struct and BodyPartDescriptors
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
            # -2 is legitimately stored as 0xFFFFFFFE in this unsigned field.
            # Further investigation needed to determine if all slots are
            # actually signed; patching only this known case for now.
            if part_id == ((-2) & ((1 << 32) - 1)):
                part_id = -2
            assert part_id != 0, (
                f"Expected non-zero body part ID for {part.name} at slot {i} for cat {cat_key}"
            )
            body_parts[part] = part_id

        r.skip(12)  # unknown_0 and unknown_1 from BodyParts struct

        # Voice actor
        _voice_code = r.str()

        # Voice pitch modifier
        r.f64()

        # ── Stats ────────────────────────────────────────────────────────────────
        stat_base = (
            _stats()
        )  # Base stats that would be passed to children (stats_heritable)
        stat_mod1 = (
            _stats()
        )  # Stat deltas as a result of levelling and events (stats_delta_levelling)
        stat_mod2 = _stats()  # Stat deltas as a result of injury (stats_delta_injuries)

        stat_total = Stats(
            *(b + m + s for b, m, s in zip(stat_base, stat_mod1, stat_mod2))
        )

        # Stores the string name of a stat; correlates with last injury
        _last_injury_debuffed_stat = r.str()

        # CampaignStats static fields (possibly tracks adventure stats)
        _hp = r.i32()
        _dead = r.u8()
        _unknown_8 = r.u8()  # unknown_0
        _unknown_1 = r.u32()

        event_stat_modifiers_count = r.u32()
        for _ in range(event_stat_modifiers_count):
            _expression = r.str()
            _unknown_0 = (
                r.u32()
            )  # Likely a downcounter indicating how many rounds this effect will last

        # ── Abilities ────────────────────────────────────────────────────────────
        # The ability block is a run of u64-length-prefixed ASCII identifiers.
        # We scan forward from the current position for the "DefaultMove" sentinel
        # that anchors the run, since the region between stats and abilities
        # contains variable-length content we don't fully understand yet.
        #
        # Run structure:
        #   [0-1]  = Movement and basic attack actives (actives_basic)
        #   [2-5]  = Current usable active ability list (actives_accessible)
        # Read up to 6 active abilities, ignoring empty/null entries.
        actives: list[str] = [s for _ in range(6) if (s := r.str()) != "None"]

        # Copy of active abilities originally inherited from parents
        _born_active_abilities: list[str] = [
            s for _ in range(4) if (s := r.str()) != "None"
        ]

        # Current usable passive ability list
        passives: list[str] = []
        for _ in range(2):
            s = r.str()
            level = r.u32()
            assert level in (1, 2), (
                "Unexpected passive ability level {level} for cat {cat_key} and passive {s}"
            )
            if s and s != "None":
                passives.append(s + (str(level) if level > 1 else ""))

        # Disorder and mutation passives
        disorders: list[str] = []
        for _ in range(2):
            s = r.str()
            if s and s != "None":
                disorders.append(s)
            r.skip(4)

        # ── Equipment (skip) ─────────────────────────────────────────────────────
        # Equipment struct layout (5 slots: head, face, neck, weapon, trinket):
        #   u32 version    - always 0x5
        #   bool has_equip
        #   if has_equip:
        #     String name
        #     String unknown_0 (set by str_aux_initialize)
        #     s32 unknown_1 (uses left)
        #     s32 unknown_2-4
        #     u8 unknown_5
        #     u8 unknown_6 (possibly times taken on adventure?)
        def _skip_equipment(r: BinaryReader) -> None:
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

        _skip_equipment(r)

        # ── Collar, Level, COI (skip) ──────────────────────────────────────────
        collar = r.str()
        level = r.i32()
        coi = r.f64()

        # ── Birthday / Age ───────────────────────────────────────────────────────
        # birthday is s64, stored near end of blob
        # Day -2 and -1 are valid (e.g., starter cats born on day -2)
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
            stat_base=stat_base,
            stat_total=stat_total,
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

    def has_eternal_youth(self) -> bool:
        """Check if cat has EternalYouth disorder."""
        return any(p.lower() == "eternalyouth" for p in (self.disorders or []))
