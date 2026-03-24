"""Pair factors calculation for breeding optimization using ENS architecture."""

from dataclasses import dataclass

from mewgenics_parser import Cat, SaveData, TraitCategory
from mewgenics_parser.traits import get_slots_for_category, BodyPartTrait, Trait
from mewgenics_breeding import simulate_breeding, OffspringProbabilityMass

from .types import TargetBuild, UniversalTrait

DEFAULT_STIMULATION = 50.0


@dataclass
class PairFactors:
    """All factors for evaluating a breeding pair (ENS architecture)."""

    expected_stats: list[float]

    expected_disorders: float
    expected_defects: float

    universal_ev: float
    build_yields: dict[str, float]


def _calc_expected_stats(pmf: OffspringProbabilityMass) -> list[float]:
    """Calculate expected stat values from PMF as a flat list of 7 floats."""
    stats = [
        pmf.stats.strength,
        pmf.stats.dexterity,
        pmf.stats.constitution,
        pmf.stats.intelligence,
        pmf.stats.speed,
        pmf.stats.charisma,
        pmf.stats.luck,
    ]
    result = []
    for stat_list in stats:
        expected = sum(value * prob for value, prob in stat_list)
        result.append(expected)
    return result


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

    Yield = (Sum of requirement EVs) + (Joint probability of requirements * Synergy Bonus)
            - (Sum of anti-synergy EVs)

    Returns max(0.0, yield) to prevent negative yields.
    """
    req_ev = sum(
        _get_marginal_prob(pmf, tw.trait) * tw.weight_ens for tw in build.requirements
    )
    anti_ev = sum(
        _get_marginal_prob(pmf, tw.trait) * tw.weight_ens for tw in build.anti_synergies
    )

    joint_prob = 1.0 if build.requirements else 0.0
    for tw in build.requirements:
        marginal = _get_marginal_prob(pmf, tw.trait)
        joint_prob *= marginal
    joint_prob = max(0.0, min(1.0, joint_prob))

    yield_value = req_ev + joint_prob * build.synergy_bonus_ens - anti_ev
    return max(0.0, yield_value)


def calculate_pair_factors(
    save_data: SaveData,
    a: Cat,
    b: Cat,
    stimulation: float = DEFAULT_STIMULATION,
    universals: list[UniversalTrait] | None = None,
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
    )


def calculate_pair_quality(factors: PairFactors) -> float:
    """Calculate baseline quality score from pair factors.

    This is the baseline value of a kitten in a vacuum.
    Build yields are handled exclusively by house-level diversity math.
    """
    malady = factors.expected_disorders * 5.0 + factors.expected_defects * 1.0
    return sum(factors.expected_stats) + factors.universal_ev - malady
