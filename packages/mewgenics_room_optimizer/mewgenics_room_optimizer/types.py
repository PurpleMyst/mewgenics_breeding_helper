"""Data models for room optimizer."""

from dataclasses import dataclass, field
from enum import Enum

from mewgenics_parser import Cat
from mewgenics_scorer import PairFactors, TraitRequirement


class RoomType(Enum):
    """Room designation types."""

    BREEDING = "breeding"
    FIGHTING = "fighting"
    GENERAL = "general"
    NONE = "none"


@dataclass
class RoomConfig:
    """Configuration for a single room."""

    key: str
    display_name: str
    room_type: RoomType
    max_cats: int | None = None  # None = unlimited for FIGHTING


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


@dataclass
class OptimizationParams:
    """Optimizer configuration."""

    min_stats: int = 0
    max_risk: float = 20.0
    minimize_variance: bool = True
    avoid_lovers: bool = True
    prefer_low_aggression: bool = True
    prefer_high_libido: bool = True
    stimulation: float = 50.0
    planner_traits: list[TraitRequirement] = field(default_factory=list)


@dataclass
class OptimizationStats:
    """Summary statistics."""

    total_cats: int
    assigned_cats: int
    total_pairs: int
    breeding_rooms_used: int
    general_rooms_used: int
    avg_pair_quality: float
    avg_risk_percent: float


@dataclass
class OptimizationResult:
    """Final optimization output."""

    rooms: list[RoomAssignment]
    excluded_cats: list[Cat]
    stats: OptimizationStats


DEFAULT_ROOM_CONFIGS = [
    RoomConfig("Floor1_Large", "Ground Floor Left", RoomType.FIGHTING, None),
    RoomConfig("Floor1_Small", "Ground Floor Right", RoomType.BREEDING, 6),
    RoomConfig("Attic", "Top Floor", RoomType.GENERAL, 6),
    RoomConfig("Floor2_Large", "Second Floor Left", RoomType.NONE, None),
    RoomConfig("Floor2_Small", "Second Floor Right", RoomType.NONE, None),
]
