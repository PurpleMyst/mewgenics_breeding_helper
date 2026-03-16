"""Pair factors calculation for breeding optimization."""

from dataclasses import dataclass

from mewgenics_parser import Cat
from mewgenics_parser.constants import STAT_NAMES

from .types import TraitRequirement
from .compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)
from .ancestry import build_ancestor_contribs, coi_from_contribs, risk_percent

DEFAULT_STIMULATION = 50.0


def _better_chance(stimulation: float) -> float:
    return (1.0 + 0.01 * stimulation) / (2.0 + 0.01 * stimulation)


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
    risk_percent: float

    expected_stats: list[float]
    total_expected_stats: float

    stat_variance: float

    aggression_factor: float
    libido_factor: float

    trait_matches: list[str]


def expected_stats(
    a: Cat, b: Cat, stimulation: float = DEFAULT_STIMULATION
) -> list[float]:
    """Calculate expected stat values for offspring."""
    chance = _better_chance(stimulation)
    return [
        max(a.stat_base[i], b.stat_base[i]) * chance
        + min(a.stat_base[i], b.stat_base[i]) * (1 - chance)
        for i in range(7)
    ]


def stat_variance(a: Cat, b: Cat) -> float:
    """Sum of absolute differences across all base stats."""
    return sum(abs(a.stat_base[i] - b.stat_base[i]) for i in range(7))


def aggression_factor(a: Cat, b: Cat) -> float:
    """Lower is better: (1 - agg_a + 1 - agg_b) / 2."""
    return (2.0 - _default_01(a.aggression) - _default_01(b.aggression)) / 2.0


def libido_factor(a: Cat, b: Cat) -> float:
    """Higher is better: (libido_a + libido_b) / 2."""
    return (_default_01(a.libido) + _default_01(b.libido)) / 2.0


def trait_coverage(
    a: Cat,
    b: Cat,
    traits: list[TraitRequirement],
) -> list[str]:
    """Return list of trait keys that either cat has."""
    matches = []
    for t in traits:
        a_has = _cat_has_trait(a, t.category, t.key)
        b_has = _cat_has_trait(b, t.category, t.key)
        if a_has or b_has:
            matches.append(t.key)
    return matches


def _cat_has_trait(cat: Cat, category: str, key: str) -> bool:
    key_lower = key.lower()
    if category == "mutation":
        return any(m.lower() == key_lower for m in (cat.mutations or []))
    elif category == "passive":
        return any(p.lower() == key_lower for p in (cat.passive_abilities or []))
    elif category == "ability":
        return any(a.lower() == key_lower for a in (cat.abilities or []))
    return False


def calculate_pair_factors(
    a: Cat,
    b: Cat,
    ancestor_contribs: dict[int, dict[int, float]],
    stimulation: float = DEFAULT_STIMULATION,
    avoid_lovers: bool = True,
    planner_traits: list[TraitRequirement] | None = None,
) -> PairFactors:
    """Calculate all factors for a breeding pair."""
    ca = ancestor_contribs.get(a.db_key, {})
    cb = ancestor_contribs.get(b.db_key, {})
    coi = coi_from_contribs(ca, cb)

    exp_stats = expected_stats(a, b, stimulation)

    return PairFactors(
        can_breed=can_breed(a, b),
        hater_conflict=is_hater_conflict(a, b),
        lover_conflict=is_lover_conflict(a, b, avoid_lovers),
        mutual_lovers=is_mutual_lovers(a, b),
        risk_percent=risk_percent(coi),
        expected_stats=exp_stats,
        total_expected_stats=sum(exp_stats),
        stat_variance=stat_variance(a, b),
        aggression_factor=aggression_factor(a, b),
        libido_factor=libido_factor(a, b),
        trait_matches=trait_coverage(a, b, planner_traits or []),
    )
