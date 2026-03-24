"""Pair factors calculation for breeding optimization."""

import math
from dataclasses import dataclass

from mewgenics_parser import Cat, SaveData, TraitCategory
from mewgenics_parser.cat import CatBodySlot
from mewgenics_parser.traits import get_slots_for_category, BodyPartTrait
from mewgenics_breeding import simulate_breeding, OffspringProbabilityMass

from .compatibility import can_breed, is_mutual_lovers
from .types import TraitRequirement

DEFAULT_STIMULATION = 50.0

_REPRESENTATIVE_SLOTS = [
    CatBodySlot.TEXTURE,
    CatBodySlot.BODY,
    CatBodySlot.HEAD,
    CatBodySlot.TAIL,
    CatBodySlot.MOUTH,
    CatBodySlot.LEFT_LEG,
    CatBodySlot.LEFT_ARM,
    CatBodySlot.LEFT_EYE,
    CatBodySlot.LEFT_EYEBROW,
    CatBodySlot.LEFT_EAR,
]


def _default_01(v: float | None) -> float:
    """Normalize None to 0.5 (neutral)."""
    return 0.5 if v is None else max(0.0, min(1.0, v))


@dataclass
class TraitInheritanceProbability:
    """Probability of a specific trait being inherited."""

    trait: TraitRequirement
    probability: float
    parent_source: str


@dataclass
class PairFactors:
    """All factors for evaluating a breeding pair."""

    can_breed: bool
    hater_conflict: bool
    lover_conflict: bool
    mutual_lovers: bool

    novel_disorder_chance: float
    novel_part_defect_chance: float
    inherited_disorder_chance: float
    inherited_part_defect_chance: float

    expected_stats: list[float]
    total_expected_stats: float

    stat_variance: float

    aggression_factor: float
    libido_factor: float
    charisma_factor: float

    trait_probabilities: list[TraitInheritanceProbability]

    @property
    def combined_disorder_chance(self) -> float:
        """Combined novel + inherited disorder chance."""
        return 1.0 - (1.0 - self.novel_disorder_chance) * (
            1.0 - self.inherited_disorder_chance
        )

    @property
    def combined_part_defect_chance(self) -> float:
        """Combined novel + inherited part defect chance."""
        return 1.0 - (1.0 - self.novel_part_defect_chance) * (
            1.0 - self.inherited_part_defect_chance
        )

    @property
    def combined_malady_chance(self) -> float:
        """Probability of any birth malady (novel OR inherited, disorder OR part defect)."""
        disorder_prob = 1.0 - (1.0 - self.novel_disorder_chance) * (
            1.0 - self.inherited_disorder_chance
        )
        defect_prob = 1.0 - (1.0 - self.novel_part_defect_chance) * (
            1.0 - self.inherited_part_defect_chance
        )
        return 1.0 - (1.0 - disorder_prob) * (1.0 - defect_prob)


def _stat_variance(a: Cat, b: Cat) -> float:
    """Sum of absolute differences across all base stats."""
    return sum(abs(a.stat_base[i] - b.stat_base[i]) for i in range(7))


def _aggression_factor(a: Cat, b: Cat) -> float:
    """Lower is better: (1 - agg_a + 1 - agg_b) / 2."""
    return (2.0 - _default_01(a.aggression) - _default_01(b.aggression)) / 2.0


def _libido_factor(a: Cat, b: Cat) -> float:
    """Higher is better: (libido_a + libido_b) / 2."""
    return (_default_01(a.libido) + _default_01(b.libido)) / 2.0


def _charisma_factor(a: Cat, b: Cat) -> float:
    """Higher is better: (charisma_a + charisma_b) / 2, normalized to 0-1."""
    cha_a = a.stat_base[5] / 10.0 if len(a.stat_base) > 5 else 0.5
    cha_b = b.stat_base[5] / 10.0 if len(b.stat_base) > 5 else 0.5
    return (cha_a + cha_b) / 2.0


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


def _get_trait_probability(
    pmf: OffspringProbabilityMass,
    req: TraitRequirement,
    parent_a: Cat,
    parent_b: Cat,
) -> TraitInheritanceProbability:
    """Extract trait probability from PMF for a TraitRequirement."""
    trait = req.trait
    category = trait.category

    if category == TraitCategory.BODY_PART:
        assert isinstance(trait, BodyPartTrait)
        slots = get_slots_for_category(trait.body_part_category)
        slot = slots[0]
        slot_probs = pmf.body_parts.get(slot, {})
        probability = slot_probs.get(trait.part_id, 0.0)
    elif category == TraitCategory.ACTIVE_ABILITY:
        probability = pmf.active_abilities.get(trait.key, 0.0)
    elif category == TraitCategory.PASSIVE_ABILITY:
        probability = pmf.passive_abilities.get(trait.key, 0.0)
    elif category == TraitCategory.DISORDER:
        probability = pmf.inherited_disorders.get(trait.key, 0.0)
    else:
        probability = 0.0

    a_has = trait.is_possessed_by(parent_a)
    b_has = trait.is_possessed_by(parent_b)

    if a_has and b_has:
        parent_source = f"{parent_a.name} or {parent_b.name}"
    elif a_has:
        parent_source = parent_a.name
    elif b_has:
        parent_source = parent_b.name
    else:
        parent_source = "Neither"

    return TraitInheritanceProbability(
        trait=req,
        probability=probability,
        parent_source=parent_source,
    )


def _calc_inherited_part_defect_chance(pmf: OffspringProbabilityMass) -> float:
    """Calculate probability of inheriting at least one part defect.

    Uses representative slots (one per part-set) to avoid double-counting paired slots.
    """
    defect_probs = []
    for slot in _REPRESENTATIVE_SLOTS:
        slot_probs = pmf.body_parts.get(slot, {})
        defect_prob = sum(
            prob
            for part_id, prob in slot_probs.items()
            if part_id < 0 or part_id >= 700
        )
        defect_probs.append(defect_prob)

    if not defect_probs:
        return 0.0
    return 1.0 - math.prod(1.0 - p for p in defect_probs)


def _calc_inherited_disorder_chance(a: Cat, b: Cat) -> float:
    """Calculate probability of inheriting at least one disorder from parents.

    15% chance per parent with disorders, flat (no pool dilution).
    """
    return 1.0 - (1.0 - (0.15 if a.disorders else 0.0)) * (1.0 - (0.15 if b.disorders else 0.0))


def calculate_pair_factors(
    save_data: SaveData,
    a: Cat,
    b: Cat,
    stimulation: float = DEFAULT_STIMULATION,
    trait_requirements: list[TraitRequirement] | None = None,
) -> PairFactors:
    """Calculate all factors for a breeding pair."""
    coi = save_data.get_offspring_coi(a, b)
    pmf = simulate_breeding(a, b, stimulation, coi)

    exp_stats = _calc_expected_stats(pmf)

    trait_probs = [
        _get_trait_probability(pmf, req, a, b) for req in (trait_requirements or [])
    ]

    return PairFactors(
        can_breed=can_breed(a, b),
        hater_conflict=False,
        lover_conflict=False,
        mutual_lovers=is_mutual_lovers(a, b),
        novel_disorder_chance=pmf.novel_disorder,
        novel_part_defect_chance=pmf.novel_birth_defect,
        inherited_disorder_chance=_calc_inherited_disorder_chance(a, b),
        inherited_part_defect_chance=_calc_inherited_part_defect_chance(pmf),
        expected_stats=exp_stats,
        total_expected_stats=sum(exp_stats),
        stat_variance=_stat_variance(a, b),
        aggression_factor=_aggression_factor(a, b),
        libido_factor=_libido_factor(a, b),
        charisma_factor=_charisma_factor(a, b),
        trait_probabilities=trait_probs,
    )


def calculate_pair_quality(factors: PairFactors) -> float:
    """Calculate quality score from pair factors using Expected Value math."""
    avg_stats = factors.total_expected_stats / 7.0
    risk_factor = 1.0 - factors.combined_malady_chance / 2.0

    variance_penalty = 0.0

    personality_bonus = 0.0
    personality_bonus += factors.aggression_factor * 2.5
    personality_bonus += factors.libido_factor * 2.5
    personality_bonus += factors.charisma_factor * 2.5

    trait_bonus = (
        sum(p.probability * p.trait.weight for p in factors.trait_probabilities) * 5.0
    )

    return (
        (avg_stats + risk_factor * 10)
        - variance_penalty
        + personality_bonus
        + trait_bonus
    )
