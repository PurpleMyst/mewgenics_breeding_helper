"""Pair factors calculation for breeding optimization."""

from dataclasses import dataclass

from mewgenics_parser import Cat
from mewgenics_parser.constants import STAT_NAMES
from mewgenics_parser.trait_dictionary import (
    is_class_spell,
    is_class_passive,
    has_skillshare_plus,
    SKILLSHARE_PLUS_ID,
)

from .types import TraitRequirement, ScoringPreferences
from .compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)
from .ancestry import build_ancestor_contribs, coi_from_contribs, AncestorData

DEFAULT_STIMULATION = 50.0


@dataclass
class TraitInheritanceProbability:
    """Probability of a specific trait being inherited."""

    trait: TraitRequirement
    probability: float  # 0.0 to 1.0
    parent_source: str  # cat name
    inherit_chance: float  # Base inheritance roll
    parent_favor_chance: float  # Chance to favor class-trait parent


def _better_chance(stimulation: float) -> float:
    return (1.0 + 0.01 * stimulation) / (2.0 + 0.01 * stimulation)


def expected_disorder_chance(coi: float) -> float:
    """Game Step 7: Base 2% chance. CoI > 0.20 adds up to 40% (capped)."""
    # Exact game math: 0.02 + 0.4 * min(max(coi - 0.2, 0.0), 1.0)
    coi_penalty = min(max(coi - 0.20, 0.0), 1.0)
    return 0.02 + (0.4 * coi_penalty)


def expected_part_defect_chance(coi: float) -> float:
    """Game Step 8, 13: If CoI > 0.05, chance = 1.5 * CoI."""
    if coi <= 0.05:
        return 0.0
    # Cap at 1.0 (by COI > 0.90, first pass is already guaranteed)
    return min(1.5 * coi, 1.0)


def _default_01(v: float | None) -> float:
    """Normalize None to 0.5 (neutral)."""
    return 0.5 if v is None else max(0.0, min(1.0, v))


def _spell_inheritance_chance(stimulation: float) -> tuple[float, float]:
    """Returns (first_spell_chance, second_spell_chance)."""
    first = 0.2 + 0.025 * stimulation
    second = 0.02 + 0.005 * stimulation
    return min(first, 1.0), min(second, 1.0)


def _passive_inheritance_chance(stimulation: float) -> float:
    """Returns passive inheritance chance (0.05 + 0.01 * stim, capped at 1.0)."""
    return min(0.05 + 0.01 * stimulation, 1.0)


def _class_favoring_chance(stimulation: float) -> float:
    """Returns chance to favor parent with class traits."""
    return min(0.01 * stimulation, 1.0)


@dataclass
class PairFactors:
    """All factors for evaluating a breeding pair."""

    can_breed: bool
    hater_conflict: bool
    lover_conflict: bool
    mutual_lovers: bool

    expected_disorder_chance: float
    expected_part_defect_chance: float

    expected_stats: list[float]
    total_expected_stats: float

    stat_variance: float

    aggression_factor: float
    libido_factor: float
    charisma_factor: float

    trait_probabilities: list[TraitInheritanceProbability]

    @property
    def combined_malady_chance(self) -> float:
        """Probability of any birth malady (disorder OR part defect)."""
        return 1.0 - (1.0 - self.expected_disorder_chance) * (
            1.0 - self.expected_part_defect_chance
        )

    @property
    def trait_inheritance_probs(self) -> dict[str, float]:
        """Map of trait key -> inheritance probability."""
        return {}


def _calc_ability_inheritance(
    trait_key: str,
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Ability inheritance with CORRECT class-favoring algebra and pool dilution."""

    # Use normalized abilities for pool
    parent_a_spells = [a.lower() for a in parent_a.inheritable_abilities]
    parent_b_spells = [a.lower() for a in parent_b.inheritable_abilities]

    parent_a_has = trait_key in parent_a_spells
    parent_b_has = trait_key in parent_b_spells

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "neither", 0.0, 0.0)

    # Base inheritance chance: 0.2 + 0.025 * stim
    inherit_chance = _spell_inheritance_chance(stimulation)[0]

    # Class favoring chance: 0.01 * stim
    favor_chance = _class_favoring_chance(stimulation)

    # 1. Determine class spell presence
    parent_a_class = any(is_class_spell(s) for s in parent_a_spells)
    parent_b_class = any(is_class_spell(s) for s in parent_b_spells)

    # 2. Calculate parent selection probability (based on class spells only)
    if parent_a_class and not parent_b_class:
        parent_a_select_prob = 0.5 + (0.5 * favor_chance)
    elif parent_b_class and not parent_a_class:
        parent_a_select_prob = 0.5 - (0.5 * favor_chance)
    else:
        parent_a_select_prob = 0.5

    # 3. Apply pool dilution to target trait
    parent_a_pool_size = len(parent_a_spells)
    parent_b_pool_size = len(parent_b_spells)

    final_prob = 0.0
    if parent_a_has:
        final_prob += (
            parent_a_select_prob / max(1, parent_a_pool_size)
        ) * inherit_chance
    if parent_b_has:
        final_prob += (
            (1.0 - parent_a_select_prob) / max(1, parent_b_pool_size)
        ) * inherit_chance

    if parent_a_has and parent_b_has:
        parent_source = f"{parent_a.name} or {parent_b.name}"
    elif parent_a_has:
        parent_source = parent_a.name
    else:
        parent_source = parent_b.name

    return TraitInheritanceProbability(
        trait=trait,
        probability=final_prob,
        parent_source=parent_source,
        inherit_chance=inherit_chance,
        parent_favor_chance=favor_chance,
    )


def _calc_passive_inheritance(
    trait_key: str,
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Passive inheritance with SKILLSHARE+ guarantee and pool dilution."""

    # Use normalized passives for pool (already excludes SkillShare via property)
    parent_a_passives_norm = [p.lower() for p in parent_a.inheritable_passives]
    parent_b_passives_norm = [p.lower() for p in parent_b.inheritable_passives]

    parent_a_has = trait_key in parent_a_passives_norm
    parent_b_has = trait_key in parent_b_passives_norm

    # SKILLSHARE+ SPECIAL: 100% guaranteed
    # Check using RAW passives (must check for + variant)
    if has_skillshare_plus(parent_a) and parent_a_has:
        return TraitInheritanceProbability(
            trait=trait,
            probability=1.0,
            parent_source="parent_a (SkillShare+)",
            inherit_chance=1.0,
            parent_favor_chance=0.0,
        )

    if has_skillshare_plus(parent_b) and parent_b_has:
        return TraitInheritanceProbability(
            trait=trait,
            probability=1.0,
            parent_source="parent_b (SkillShare+)",
            inherit_chance=1.0,
            parent_favor_chance=0.0,
        )

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)

    inherit_chance = _passive_inheritance_chance(stimulation)
    favor_chance = _class_favoring_chance(stimulation)

    # === CRITICAL FIX: Same as abilities ===
    # 1. Determine class passive presence (NOT target trait)
    parent_a_class = any(is_class_passive(p) for p in parent_a_passives_norm)
    parent_b_class = any(is_class_passive(p) for p in parent_b_passives_norm)

    # 2. Calculate parent selection probability (based on class passives only)
    if parent_a_class and not parent_b_class:
        parent_a_select_prob = 0.5 + (0.5 * favor_chance)
    elif parent_b_class and not parent_a_class:
        parent_a_select_prob = 0.5 - (0.5 * favor_chance)
    else:
        parent_a_select_prob = 0.5

    # 3. Apply pool dilution to target trait
    parent_a_pool_size = len(parent_a_passives_norm)
    parent_b_pool_size = len(parent_b_passives_norm)

    final_prob = 0.0
    if parent_a_has:
        final_prob += (
            parent_a_select_prob / max(1, parent_a_pool_size)
        ) * inherit_chance
    if parent_b_has:
        final_prob += (
            (1.0 - parent_a_select_prob) / max(1, parent_b_pool_size)
        ) * inherit_chance

    parent_source = "parent_a" if parent_a_select_prob > 0.5 else "parent_b"
    if parent_a_has and parent_b_has:
        parent_source = "either"

    return TraitInheritanceProbability(
        trait=trait,
        probability=final_prob,
        parent_source=parent_source,
        inherit_chance=inherit_chance,
        parent_favor_chance=favor_chance,
    )


def _calc_mutation_inheritance(
    trait_key: str,
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Mutation inheritance: 80% inherit, mutation favoring with stimulation."""

    parent_a_muts = [m.lower() for m in (parent_a.mutations or [])]
    parent_b_muts = [m.lower() for m in (parent_b.mutations or [])]

    parent_a_has = trait_key in parent_a_muts
    parent_b_has = trait_key in parent_b_muts

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)

    # 80% chance to inherit parts (vs 20% reroll)
    inherit_all_chance = 0.8

    # Mutation favoring: (1.0 + 0.01*Stim) / (2.0 + 0.01*Stim)
    mutation_favor_chance = _better_chance(stimulation)

    # TODO: If Mom has "Frostbit" and Dad has "Horns" (different mutation same slot),
    # both parents are "mutated" but current logic incorrectly favors Mom for Frostbit.
    # Fix requires mapping mutations to body part slots.

    # If only one parent has mutation, apply favoring
    if parent_a_has and parent_b_has:
        parent_a_select_prob = 0.5
    elif parent_a_has:
        parent_a_select_prob = mutation_favor_chance
    else:
        parent_a_select_prob = 1.0 - mutation_favor_chance

    final_prob = inherit_all_chance * (
        parent_a_select_prob if parent_a_has else (1.0 - parent_a_select_prob)
    )

    parent_source = "parent_a" if parent_a_select_prob > 0.5 else "parent_b"
    if parent_a_has and parent_b_has:
        parent_source = "either"

    return TraitInheritanceProbability(
        trait=trait,
        probability=final_prob,
        parent_source=parent_source,
        inherit_chance=inherit_all_chance,
        parent_favor_chance=mutation_favor_chance,
    )


def calculate_trait_probability(
    trait: TraitRequirement,
    parent_a: Cat | None,
    parent_b: Cat | None,
    stimulation: float = DEFAULT_STIMULATION,
) -> TraitInheritanceProbability:
    """Calculate inheritance probability for a specific trait."""

    if parent_a is None or parent_b is None:
        return TraitInheritanceProbability(trait, 0.0, "unknown", 0.0, 0.0)

    trait_key = trait.key.lower()

    if trait.category == "ability":
        return _calc_ability_inheritance(
            trait_key, parent_a, parent_b, stimulation, trait
        )
    elif trait.category == "passive":
        return _calc_passive_inheritance(
            trait_key, parent_a, parent_b, stimulation, trait
        )
    elif trait.category == "mutation":
        return _calc_mutation_inheritance(
            trait_key, parent_a, parent_b, stimulation, trait
        )

    return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)


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


def charisma_factor(a: Cat, b: Cat) -> float:
    """Higher is better: (charisma_a + charisma_b) / 2, normalized to 0-1."""
    cha_a = a.stat_base[5] / 10.0 if len(a.stat_base) > 5 else 0.5
    cha_b = b.stat_base[5] / 10.0 if len(b.stat_base) > 5 else 0.5
    return (cha_a + cha_b) / 2.0


def trait_coverage(
    a: Cat,
    b: Cat,
    traits: list[TraitRequirement],
) -> list[TraitRequirement]:
    """Return list of TraitRequirements that either cat has."""
    matches = []
    for t in traits:
        a_has = _cat_has_trait(a, t.category, t.key)
        b_has = _cat_has_trait(b, t.category, t.key)
        if a_has or b_has:
            matches.append(t)
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
    ancestor_contribs: dict[int, dict[int, AncestorData]],
    stimulation: float = DEFAULT_STIMULATION,
    avoid_lovers: bool = True,
    planner_traits: list[TraitRequirement] | None = None,
) -> PairFactors:
    """Calculate all factors for a breeding pair."""
    ca = ancestor_contribs.get(a.db_key, {})
    cb = ancestor_contribs.get(b.db_key, {})
    coi = coi_from_contribs(ca, cb)

    exp_stats = expected_stats(a, b, stimulation)

    trait_probs = [
        calculate_trait_probability(trait, a, b, stimulation)
        for trait in (planner_traits or [])
    ]

    return PairFactors(
        can_breed=can_breed(a, b),
        hater_conflict=is_hater_conflict(a, b),
        lover_conflict=is_lover_conflict(a, b, avoid_lovers),
        mutual_lovers=is_mutual_lovers(a, b),
        expected_disorder_chance=expected_disorder_chance(coi),
        expected_part_defect_chance=expected_part_defect_chance(coi),
        expected_stats=exp_stats,
        total_expected_stats=sum(exp_stats),
        stat_variance=stat_variance(a, b),
        aggression_factor=aggression_factor(a, b),
        libido_factor=libido_factor(a, b),
        charisma_factor=charisma_factor(a, b),
        trait_probabilities=trait_probs,
    )


def calculate_pair_quality(factors: PairFactors, prefs: ScoringPreferences) -> float:
    """Calculate quality score from pair factors using Expected Value math."""
    avg_stats = factors.total_expected_stats / 7.0
    risk_factor = 1.0 - factors.combined_malady_chance / 2.0

    variance_penalty = 0.0
    if prefs.minimize_variance:
        for diff in [
            abs(a - b)
            for a, b in zip(factors.expected_stats[:3], factors.expected_stats[3:])
        ]:
            if diff > 2:
                variance_penalty += (diff**2) * 0.5

    personality_bonus = 0.0
    if prefs.prefer_low_aggression:
        personality_bonus += factors.aggression_factor * 2.5
    if prefs.prefer_high_libido:
        personality_bonus += factors.libido_factor * 2.5
    if prefs.prefer_high_charisma:
        personality_bonus += factors.charisma_factor * 2.5

    trait_bonus = (
        sum(p.probability * p.trait.weight for p in factors.trait_probabilities) * 5.0
    )

    return (
        (avg_stats + risk_factor * 20)
        - variance_penalty
        + personality_bonus
        + trait_bonus
    )
