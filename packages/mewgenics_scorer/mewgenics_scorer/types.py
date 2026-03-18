"""Type definitions for mewgenics_scorer."""

from dataclasses import dataclass
from mewgenics_parser.traits import Trait


@dataclass
class ScoringPreferences:
    """User preferences for scoring breeding pairs."""

    minimize_variance: bool = False
    prefer_low_aggression: bool = False
    prefer_high_libido: bool = False
    prefer_high_charisma: bool = False
    maximize_throughput: bool = False

@dataclass(slots=True)
class TraitRequirement:
    """A trait to score pair coverage for, with an associated weight."""

    trait: Trait
    weight: float = 5.0
