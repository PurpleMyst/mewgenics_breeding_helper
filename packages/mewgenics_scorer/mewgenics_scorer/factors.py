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

from .types import TraitRequirement
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
    parent_source: str  # "mother", "father", "skillshare_guaranteed"
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

    trait_matches: list[TraitRequirement]

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
    mother: Cat,
    father: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Ability inheritance with CORRECT class-favoring algebra and pool dilution."""

    mother_spells = [a.lower() for a in (mother.abilities or [])]
    father_spells = [a.lower() for a in (father.abilities or [])]

    mother_has = trait_key in mother_spells
    father_has = trait_key in father_spells

    if not mother_has and not father_has:
        return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)

    # Base inheritance chance: 0.2 + 0.025 * stim
    inherit_chance = _spell_inheritance_chance(stimulation)[0]

    # Class favoring chance: 0.01 * stim
    favor_chance = _class_favoring_chance(stimulation)

    # Determine class spell presence
    mother_class = any(is_class_spell(s) for s in mother_spells)
    father_class = any(is_class_spell(s) for s in father_spells)

    # CORRECTED: mother_select_prob = 0.5 + (0.5 * favor_chance)
    if mother_has and father_has:
        if mother_class and not father_class:
            # Favor mother
            mother_select_prob = 0.5 + (0.5 * favor_chance)
        elif father_class and not mother_class:
            # Favor father
            mother_select_prob = 0.5 - (0.5 * favor_chance)
        else:
            # Both or neither have class - even split
            mother_select_prob = 0.5
    elif mother_has:
        mother_select_prob = 1.0
    else:
        mother_select_prob = 0.0

    # Pool dilution: divide by parent's spell pool size
    mother_pool_size = len(mother_spells)
    father_pool_size = len(father_spells)

    final_prob = 0.0
    if mother_has:
        final_prob += (mother_select_prob / max(1, mother_pool_size)) * inherit_chance
    if father_has:
        final_prob += (
            (1.0 - mother_select_prob) / max(1, father_pool_size)
        ) * inherit_chance

    parent_source = "mother" if mother_select_prob > 0.5 else "father"
    if mother_has and father_has:
        parent_source = "either"

    return TraitInheritanceProbability(
        trait=trait,
        probability=final_prob,
        parent_source=parent_source,
        inherit_chance=inherit_chance,
        parent_favor_chance=favor_chance,
    )


def _calc_passive_inheritance(
    trait_key: str,
    mother: Cat,
    father: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Passive inheritance with SKILLSHARE+ guarantee and pool dilution."""

    # No filtering needed - Cat.disorders already separated
    mother_passives = [p.lower() for p in (mother.passive_abilities or [])]
    father_passives = [p.lower() for p in (father.passive_abilities or [])]

    mother_has = trait_key in mother_passives
    father_has = trait_key in father_passives

    # SKILLSHARE+ SPECIAL: 100% guaranteed (no pool dilution)
    if has_skillshare_plus(mother):
        other_passives = [p for p in mother_passives if p != SKILLSHARE_PLUS_ID]
        if trait_key in other_passives:
            return TraitInheritanceProbability(
                trait=trait,
                probability=1.0,
                parent_source="mother (SkillShare+)",
                inherit_chance=1.0,
                parent_favor_chance=0.0,
            )

    if has_skillshare_plus(father):
        other_passives = [p for p in father_passives if p != SKILLSHARE_PLUS_ID]
        if trait_key in other_passives:
            return TraitInheritanceProbability(
                trait=trait,
                probability=1.0,
                parent_source="father (SkillShare+)",
                inherit_chance=1.0,
                parent_favor_chance=0.0,
            )

    # Normal passive inheritance
    if not mother_has and not father_has:
        return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)

    inherit_chance = _passive_inheritance_chance(stimulation)
    favor_chance = _class_favoring_chance(stimulation)

    # Class passive presence
    mother_class = any(is_class_passive(p) for p in mother_passives)
    father_class = any(is_class_passive(p) for p in father_passives)

    # Same class-favoring math as abilities
    if mother_has and father_has:
        if mother_class and not father_class:
            mother_select_prob = 0.5 + (0.5 * favor_chance)
        elif father_class and not mother_class:
            mother_select_prob = 0.5 - (0.5 * favor_chance)
        else:
            mother_select_prob = 0.5
    elif mother_has:
        mother_select_prob = 1.0
    else:
        mother_select_prob = 0.0

    # Pool dilution
    mother_pool_size = len(mother_passives)
    father_pool_size = len(father_passives)

    final_prob = 0.0
    if mother_has:
        final_prob += (mother_select_prob / max(1, mother_pool_size)) * inherit_chance
    if father_has:
        final_prob += (
            (1.0 - mother_select_prob) / max(1, father_pool_size)
        ) * inherit_chance

    parent_source = "mother" if mother_select_prob > 0.5 else "father"
    if mother_has and father_has:
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
    mother: Cat,
    father: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Mutation inheritance: 80% inherit, mutation favoring with stimulation."""

    mother_muts = [m.lower() for m in (mother.mutations or [])]
    father_muts = [m.lower() for m in (father.mutations or [])]

    mother_has = trait_key in mother_muts
    father_has = trait_key in father_muts

    if not mother_has and not father_has:
        return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)

    # 80% chance to inherit parts (vs 20% reroll)
    inherit_all_chance = 0.8

    # Mutation favoring: (1.0 + 0.01*Stim) / (2.0 + 0.01*Stim)
    mutation_favor_chance = _better_chance(stimulation)

    # If only one parent has mutation, apply favoring
    if mother_has and father_has:
        mother_select_prob = 0.5
    elif mother_has:
        mother_select_prob = mutation_favor_chance
    else:
        mother_select_prob = 1.0 - mutation_favor_chance

    final_prob = inherit_all_chance * (
        mother_select_prob if mother_has else (1.0 - mother_select_prob)
    )

    parent_source = "mother" if mother_select_prob > 0.5 else "father"
    if mother_has and father_has:
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
    mother: Cat | None,
    father: Cat | None,
    stimulation: float = DEFAULT_STIMULATION,
) -> TraitInheritanceProbability:
    """Calculate inheritance probability for a specific trait."""

    if mother is None or father is None:
        return TraitInheritanceProbability(trait, 0.0, "unknown", 0.0, 0.0)

    trait_key = trait.key.lower()

    if trait.category == "ability":
        return _calc_ability_inheritance(trait_key, mother, father, stimulation, trait)
    elif trait.category == "passive":
        return _calc_passive_inheritance(trait_key, mother, father, stimulation, trait)
    elif trait.category == "mutation":
        return _calc_mutation_inheritance(trait_key, mother, father, stimulation, trait)

    return TraitInheritanceProbability(trait, 0.0, "none", 0.0, 0.0)


def expected_disorder_inheritance(
    mother: Cat | None,
    father: Cat | None,
) -> float:
    """Step 6: 15% chance per parent of inheriting a disorder."""
    chance = 0.0

    if mother and mother.disorders:
        chance += 0.15
    if father and father.disorders:
        chance += 0.15

    return min(chance, 0.30)  # Cap at 30%


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
        trait_matches=trait_coverage(a, b, planner_traits or []),
    )
