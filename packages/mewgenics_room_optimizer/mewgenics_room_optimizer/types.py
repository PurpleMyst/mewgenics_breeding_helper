"""Data models for room optimizer."""

from dataclasses import dataclass, field
from enum import Enum

from mewgenics_parser import Cat
from mewgenics_scorer import PairFactors


class RoomType(Enum):
    """Room designation types."""

    BREEDING = "breeding"
    FIGHTING = "fighting"
    GENERAL = "general"
    HEALTH = "health"
    MUTATION = "mutation"
    NONE = "none"


@dataclass
class RoomConfig:
    """Configuration for a single room."""

    key: str
    room_type: RoomType
    max_cats: int | None
    stimulation: float

    @property
    def display_name(self) -> str:
        """Get display name from ROOM_DISPLAY, fallback to key."""
        from mewgenics_parser.constants import ROOM_DISPLAY

        return ROOM_DISPLAY.get(self.key, self.key)


@dataclass
class ScoredPair:
    """A breeding pair with quality score."""

    cat_a: Cat
    cat_b: Cat
    factors: PairFactors
    quality: float


@dataclass
class RoomAssignment:
    """Cats assigned to a room."""

    room: RoomConfig
    cats: list[Cat]
    pairs: list[ScoredPair]
    eternal_youth_cats: list[Cat] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Final optimization output."""

    rooms: list[RoomAssignment]


DEFAULT_ROOM_CONFIGS = [
    RoomConfig("Floor1_Large", RoomType.FIGHTING, None, 50.0),
    RoomConfig("Floor1_Small", RoomType.BREEDING, 6, 50.0),
    RoomConfig("Attic", RoomType.GENERAL, 6, 50.0),
    RoomConfig("Floor2_Large", RoomType.NONE, None, 50.0),
    RoomConfig("Floor2_Small", RoomType.NONE, None, 50.0),
]
