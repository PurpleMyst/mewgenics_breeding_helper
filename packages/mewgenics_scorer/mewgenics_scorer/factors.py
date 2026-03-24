"""Pair factors calculation for breeding optimization."""

from dataclasses import dataclass

from mewgenics_parser import Cat, SaveData

from .compatibility import can_breed, is_mutual_lovers
from .inheritance import (
    TraitInheritanceProbability,
    calculate_trait_probability,
    expected_stats,
    inherited_disorder_chance,
    inherited_part_defect_chance,
    novel_disorder_chance,
    novel_part_defect_chance,
)
from .types import TraitRequirement

DEFAULT_STIMULATION = 50.0


def _default_01(v: float | None) -> float:
    """Normalize None to 0.5 (neutral)."""
    return 0.5 if v is None else max(0.0, min(1.0, v))


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
        # Disorder union: P(A or B) = 1 - (1-A)(1-B)
        disorder_prob = 1.0 - (1.0 - self.novel_disorder_chance) * (
            1.0 - self.inherited_disorder_chance
        )
        # Part defect union
        defect_prob = 1.0 - (1.0 - self.novel_part_defect_chance) * (
            1.0 - self.inherited_part_defect_chance
        )
        # Total malady union
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


def calculate_pair_factors(
    save_data: SaveData,
    a: Cat,
    b: Cat,
    stimulation: float = DEFAULT_STIMULATION,
    trait_requirements: list[TraitRequirement] | None = None,
) -> PairFactors:
    """Calculate all factors for a breeding pair."""

    exp_stats = expected_stats(a, b, stimulation)

    trait_probs = [
        calculate_trait_probability(trait, a, b, stimulation)
        for trait in (trait_requirements or [])
    ]

    coi = save_data.get_offspring_coi(a, b)

    return PairFactors(
        can_breed=can_breed(a, b),
        hater_conflict=False,
        lover_conflict=False,
        mutual_lovers=is_mutual_lovers(a, b),
        novel_disorder_chance=novel_disorder_chance(coi),
        novel_part_defect_chance=novel_part_defect_chance(coi),
        inherited_disorder_chance=inherited_disorder_chance(a, b),
        inherited_part_defect_chance=inherited_part_defect_chance(a, b, stimulation),
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
