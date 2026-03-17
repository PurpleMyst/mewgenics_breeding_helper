"""Mewgenics pair scoring factors for breeding optimization."""

from .factors import (
    PairFactors,
    TraitInheritanceProbability,
    calculate_pair_factors,
    calculate_trait_probability,
    expected_stats,
    stat_variance,
    aggression_factor,
    libido_factor,
    trait_coverage,
    expected_disorder_chance,
    expected_part_defect_chance,
    expected_disorder_inheritance,
    DEFAULT_STIMULATION,
)
from .ancestry import (
    build_ancestor_contribs,
    coi_from_contribs,
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
    "calculate_trait_probability",
    "expected_stats",
    "stat_variance",
    "aggression_factor",
    "libido_factor",
    "trait_coverage",
    "expected_disorder_chance",
    "expected_part_defect_chance",
    "expected_disorder_inheritance",
    "build_ancestor_contribs",
    "coi_from_contribs",
    "can_breed",
    "is_hater_conflict",
    "is_lover_conflict",
    "is_mutual_lovers",
    "TraitRequirement",
    "DEFAULT_STIMULATION",
]
