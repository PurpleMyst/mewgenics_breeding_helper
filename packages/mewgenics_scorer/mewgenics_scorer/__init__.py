"""Mewgenics pair scoring factors for breeding optimization."""

from .factors import (
    PairFactors,
    calculate_pair_factors,
    expected_stats,
    stat_variance,
    aggression_factor,
    libido_factor,
    trait_coverage,
    DEFAULT_STIMULATION,
)
from .ancestry import (
    build_ancestor_contribs,
    coi_from_contribs,
    risk_percent,
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
    "calculate_pair_factors",
    "expected_stats",
    "stat_variance",
    "aggression_factor",
    "libido_factor",
    "trait_coverage",
    "build_ancestor_contribs",
    "coi_from_contribs",
    "risk_percent",
    "can_breed",
    "is_hater_conflict",
    "is_lover_conflict",
    "is_mutual_lovers",
    "TraitRequirement",
    "DEFAULT_STIMULATION",
]
