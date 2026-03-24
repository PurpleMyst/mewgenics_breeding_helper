"""Mewgenics pair scoring factors for breeding optimization."""

from .factors import (
    PairFactors,
    TraitInheritanceProbability,
    calculate_pair_factors,
    calculate_pair_quality,
)
from .compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)
from .types import TraitRequirement

__all__ = [
    "PairFactors",
    "TraitInheritanceProbability",
    "calculate_pair_factors",
    "calculate_pair_quality",
    "can_breed",
    "is_hater_conflict",
    "is_lover_conflict",
    "is_mutual_lovers",
    "TraitRequirement",
]
