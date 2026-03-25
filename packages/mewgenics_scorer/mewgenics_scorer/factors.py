"""Pair factors calculation for breeding optimization using ENS architecture."""

import math
from dataclasses import dataclass, field

from mewgenics_parser import Cat, SaveData, TraitCategory
from mewgenics_parser.traits import (
    BodyPartTrait,
    CatBodyPartCategory,
    Trait,
    get_slots_for_category,
)
from mewgenics_breeding import simulate_breeding, OffspringProbabilityMass

from .types import TargetBuild, TraitWeight

DEFAULT_STIMULATION = 50.0


@dataclass
class PairFactors:
    """All factors for evaluating a breeding pair (ENS architecture)."""

    expected_stats: list[float]

    expected_disorders: float
    expected_defects: float

    universal_ev: float
    build_yields: dict[str, float]

    breeding_prob: float = field(default=1.0)


def _calc_expected_stats(pmf: OffspringProbabilityMass) -> list[float]:
    """Calculate expected stat values from PMF as a flat list of 7 floats."""
    return [sum(value * prob for value, prob in stat_list) for stat_list in pmf.stats]


def _get_marginal_prob(pmf: OffspringProbabilityMass, trait: Trait) -> float:
    """Extract the marginal probability of a trait from the PMF.

    For BODY_PART traits, only checks slots[0] to avoid double-counting
    from symmetrization (left/right pairs share the same probability).
    """
    category = trait.category

    if category == TraitCategory.BODY_PART:
        assert isinstance(trait, BodyPartTrait)
        slots = get_slots_for_category(trait.body_part_category)
        if slots:
            slot = slots[0]
            slot_probs = pmf.body_parts.get(slot, {})
            return slot_probs.get(trait.part_id, 0.0)
        return 0.0
    elif category == TraitCategory.ACTIVE_ABILITY:
        return pmf.active_abilities.get(trait.key, 0.0)
    elif category == TraitCategory.PASSIVE_ABILITY:
        return pmf.passive_abilities.get(trait.key, 0.0)
    elif category == TraitCategory.DISORDER:
        return pmf.inherited_disorders.get(trait.key, 0.0)
    else:
        return 0.0


def _evaluate_build(pmf: OffspringProbabilityMass, build: TargetBuild) -> float:
    """Evaluate the expected yield of a build from a PMF.

    Yield = (Sum of requirement EVs) + (Synergy Prob * Synergy Bonus)
            - (Sum of anti-synergy EVs)

    Where Synergy Prob = P(at least one passive) * P(at least one active)
                          * ∏P(at least one body part per slot set)

    Returns max(0.0, yield) to prevent negative yields.
    """
    req_ev = sum(
        _get_marginal_prob(pmf, tw.trait) * tw.weight_ens for tw in build.requirements
    )
    anti_ev = sum(
        _get_marginal_prob(pmf, tw.trait) * tw.weight_ens for tw in build.anti_synergies
    )

    passive_reqs = [
        tw
        for tw in build.requirements
        if tw.trait.category == TraitCategory.PASSIVE_ABILITY
    ]
    active_reqs = [
        tw
        for tw in build.requirements
        if tw.trait.category == TraitCategory.ACTIVE_ABILITY
    ]
    body_part_reqs = [
        tw for tw in build.requirements if tw.trait.category == TraitCategory.BODY_PART
    ]

    p_at_least_one_passive = 1.0
    if passive_reqs:
        p_at_least_one_passive = 1.0 - math.prod(
            1.0 - _get_marginal_prob(pmf, tw.trait) for tw in passive_reqs
        )

    p_at_least_one_active = 1.0
    if active_reqs:
        p_at_least_one_active = 1.0 - math.prod(
            1.0 - _get_marginal_prob(pmf, tw.trait) for tw in active_reqs
        )

    body_parts_by_category: dict[CatBodyPartCategory, list] = {}
    for tw in body_part_reqs:
        trait = tw.trait
        assert isinstance(trait, BodyPartTrait)
        body_parts_by_category.setdefault(trait.body_part_category, []).append(tw)

    body_part_product = 1.0
    for cat_tws in body_parts_by_category.values():
        p_at_least_one = 1.0 - math.prod(
            1.0 - _get_marginal_prob(pmf, tw.trait) for tw in cat_tws
        )
        body_part_product *= p_at_least_one

    synergy_prob = p_at_least_one_passive * p_at_least_one_active * body_part_product

    yield_value = req_ev + synergy_prob * build.synergy_bonus_ens - anti_ev
    return max(0.0, yield_value)


def calculate_pair_factors(
    save_data: SaveData,
    a: Cat,
    b: Cat,
    stimulation: float = DEFAULT_STIMULATION,
    universals: list[TraitWeight] | None = None,
    target_builds: list[TargetBuild] | None = None,
) -> PairFactors:
    """Calculate all factors for a breeding pair using ENS architecture."""
    coi = save_data.get_offspring_coi(a, b)
    pmf = simulate_breeding(a, b, stimulation, coi)

    expected_stats = _calc_expected_stats(pmf)

    expected_disorders = pmf.expected_inherited_disorders + pmf.novel_disorder
    expected_defects = pmf.expected_inherited_defects + pmf.novel_birth_defect

    universal_ev = 0.0
    if universals:
        universal_ev = sum(
            _get_marginal_prob(pmf, u.trait) * u.weight_ens for u in universals
        )

    build_yields: dict[str, float] = {}
    if target_builds:
        build_yields = {
            build.name: _evaluate_build(pmf, build) for build in target_builds
        }

    return PairFactors(
        expected_stats=expected_stats,
        expected_disorders=expected_disorders,
        expected_defects=expected_defects,
        universal_ev=universal_ev,
        build_yields=build_yields,
        breeding_prob=(1 - (a.sexuality or 0.0)) * (1 - (b.sexuality or 0.0)),
    )


def calculate_pair_quality(factors: PairFactors) -> float:
    """Calculate baseline quality score from pair factors.

    This is the baseline value of a kitten in a vacuum.
    Build yields are handled exclusively by house-level diversity math.
    """
    malady = factors.expected_disorders * 5.0 + factors.expected_defects * 1.0
    base_quality = sum(factors.expected_stats) + factors.universal_ev - malady
    return base_quality * factors.breeding_prob
