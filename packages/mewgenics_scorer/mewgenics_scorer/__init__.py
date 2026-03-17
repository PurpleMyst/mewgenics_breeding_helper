"""Mewgenics pair scoring factors for breeding optimization."""

from .factors import (
    PairFactors,
    TraitInheritanceProbability,
    calculate_pair_factors,
    calculate_pair_quality,
    calculate_trait_probability,
    expected_stats,
    stat_variance,
    aggression_factor,
    libido_factor,
    trait_coverage,
    expected_disorder_chance,
    expected_part_defect_chance,
    DEFAULT_STIMULATION,
)
from .ancestry import (
    AncestorData,
    build_ancestor_contribs,
    coi_from_contribs,
)
from .compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)
from .types import TraitRequirement, ScoringPreferences

__all__ = [
    "PairFactors",
    "TraitInheritanceProbability",
    "calculate_pair_factors",
    "calculate_pair_quality",
    "calculate_trait_probability",
    "expected_stats",
    "stat_variance",
    "aggression_factor",
    "libido_factor",
    "trait_coverage",
    "expected_disorder_chance",
    "expected_part_defect_chance",
    "build_ancestor_contribs",
    "coi_from_contribs",
    "AncestorData",
    "can_breed",
    "is_hater_conflict",
    "is_lover_conflict",
    "is_mutual_lovers",
    "TraitRequirement",
    "ScoringPreferences",
    "DEFAULT_STIMULATION",
]
