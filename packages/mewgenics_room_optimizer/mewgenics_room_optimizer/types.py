"""Data models for room optimizer."""

from dataclasses import dataclass, field
from enum import Enum

from mewgenics_parser import Cat
from mewgenics_scorer import PairFactors, ScoringPreferences, TraitRequirement


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
    max_cats: int | None
    base_stim: float


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
class OptimizationParams:
    """Optimizer configuration."""

    min_stats: int = 0
    max_risk: float = 0.2
    avoid_lovers: bool = True
    stimulation: float = 50.0
    trait_requirements: list[TraitRequirement] = field(default_factory=list)
    gay_flags: dict[int, bool] = field(default_factory=dict)
    scoring_prefs: ScoringPreferences | None = None
    sa_temperature: float = 100.0
    sa_cooling_rate: float = 0.95
    sa_neighbors_per_temp: int = 200


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
    RoomConfig("Floor1_Large", "Ground Floor Left", RoomType.FIGHTING, None, 50.0),
    RoomConfig("Floor1_Small", "Ground Floor Right", RoomType.BREEDING, 6, 50.0),
    RoomConfig("Attic", "Top Floor", RoomType.GENERAL, 6, 50.0),
    RoomConfig("Floor2_Large", "Second Floor Left", RoomType.NONE, None, 50.0),
    RoomConfig("Floor2_Small", "Second Floor Right", RoomType.NONE, None, 50.0),
]
