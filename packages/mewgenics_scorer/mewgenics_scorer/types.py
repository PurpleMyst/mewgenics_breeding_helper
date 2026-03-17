"""Type definitions for mewgenics_scorer."""

from dataclasses import dataclass


@dataclass
class TraitRequirement:
    """A trait to score pair coverage for."""

    category: str  # "mutation", "passive", "ability"
    key: str  # e.g., "Frostbit", "Sturdy"
    weight: float = 1.0  # 1-10, for future weighting


@dataclass
class ScoringPreferences:
    """User preferences for scoring breeding pairs."""

    minimize_variance: bool = False
    prefer_low_aggression: bool = False
    prefer_high_libido: bool = False
    prefer_high_charisma: bool = False
