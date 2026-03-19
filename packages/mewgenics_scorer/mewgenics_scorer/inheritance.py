from dataclasses import dataclass

from mewgenics_parser import Cat, TraitCategory
from mewgenics_parser.trait_dictionary import (
    has_skillshare_plus,
    is_class_active,
    is_class_passive,
)
from mewgenics_parser.traits import (
    BodyPartTrait,
    cat_has_defect_in_slot,
    cat_has_mutation_in_slot,
)

from .types import TraitRequirement

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


def novel_disorder_chance(coi: float) -> float:
    """Game Step 7: Base 2% chance. CoI > 0.20 adds up to 40% (capped).

    This is the chance for a NEW disorder caused by inbreeding, not inherited from parents.
    """
    # Exact game math: 0.02 + 0.4 * min(max(coi - 0.2, 0.0), 1.0)
    coi_penalty = min(max(coi - 0.20, 0.0), 1.0)
    return 0.02 + (0.4 * coi_penalty)


def novel_part_defect_chance(coi: float) -> float:
    """Game Step 8, 13: If CoI > 0.05, chance = 1.5 * CoI.

    This is the chance for NEW birth defect parts caused by inbreeding, not inherited from parents.
    """
    if coi <= 0.05:
        return 0.0
    # Cap at 1.0 (by COI > 0.90, first pass is already guaranteed)
    return min(1.5 * coi, 1.0)


def inherited_disorder_chance(parent_a: Cat, parent_b: Cat) -> float:
    """Game Step 6: 15% chance to inherit a random disorder from each parent.

    Only applies if parent has disorders. Pool dilution: 15% / len(disorders).
    Returns P(any disorder inherited) = 1 - P(no disorder from mom) * P(no disorder from dad)
    """
    mom_has = len(parent_a.disorders) > 0 if parent_a.disorders else False
    dad_has = len(parent_b.disorders) > 0 if parent_b.disorders else False

    if not mom_has and not dad_has:
        return 0.0

    # 15% chance per parent, diluted by pool size
    # P(no disorder from mom) = 1 - (0.15 / pool_size) if mom has disorders, else 1
    if mom_has:
        mom_no = 1.0 - (0.15 / len(parent_a.disorders))
    else:
        mom_no = 1.0

    if dad_has:
        dad_no = 1.0 - (0.15 / len(parent_b.disorders))
    else:
        dad_no = 1.0

    # P(any disorder) = 1 - P(no disorder from mom) * P(no disorder from dad)
    return 1.0 - (mom_no * dad_no)


def inherited_part_defect_chance(
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float = DEFAULT_STIMULATION,
) -> float:
    """Game Step 9: For each slot with a negative part, calculate inheritance.

    Returns combined OR probability: P(any defect part inherited).
    Uses 80% inherit chance with mutation/defect favoring logic.
    """
    # Get all body part slots
    from dataclasses import asdict

    slots = asdict(parent_a.body_parts).keys()

    inherit_all_chance = 0.8
    mutation_favor_chance = _better_chance(stimulation)

    # Calculate probability for each slot having a defect inherited
    # P(any slot inherits) = 1 - P(no slots inherit)
    slot_probs = []

    for slot in slots:
        a_has_defect = cat_has_defect_in_slot(parent_a, slot)
        b_has_defect = cat_has_defect_in_slot(parent_b, slot)

        if not a_has_defect and not b_has_defect:
            continue

        # Determine selection probability based on favoring
        if a_has_defect and not b_has_defect:
            select_a_prob = mutation_favor_chance
        elif b_has_defect and not a_has_defect:
            select_a_prob = 1.0 - mutation_favor_chance
        else:
            # Both have defects in this slot or neither - 50/50
            select_a_prob = 0.5

        # Probability of inheriting THIS slot's defect
        slot_prob = inherit_all_chance * max(select_a_prob, 1.0 - select_a_prob)
        slot_probs.append(slot_prob)

    if not slot_probs:
        return 0.0

    # Combined OR probability: P(any slot inherits) = 1 - P(no slots inherit)
    combined = 1.0
    for p in slot_probs:
        combined *= 1.0 - p

    return 1.0 - combined


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


def calculate_trait_probability(
    trait: TraitRequirement,
    parent_a: Cat | None,
    parent_b: Cat | None,
    stimulation: float = DEFAULT_STIMULATION,
) -> TraitInheritanceProbability:
    """Calculate inheritance probability for a specific trait."""

    if parent_a is None or parent_b is None:
        return TraitInheritanceProbability(trait, 0.0, "Unknown", 0.0, 0.0)

    category = trait.trait.category
    if category == TraitCategory.ACTIVE_ABILITY:
        return _calc_ability_inheritance(parent_a, parent_b, stimulation, trait)
    elif category == TraitCategory.PASSIVE_ABILITY:
        return _calc_passive_inheritance(parent_a, parent_b, stimulation, trait)
    elif category == TraitCategory.BODY_PART:
        return _calc_body_part_inheritance(parent_a, parent_b, stimulation, trait)
    elif category == TraitCategory.DISORDER:
        return _calc_disorder_inheritance(parent_a, parent_b, trait)

    return TraitInheritanceProbability(trait, 0.0, "Neither", 0.0, 0.0)


def _calc_disorder_inheritance(
    parent_a: Cat,
    parent_b: Cat,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Disorder inheritance: 15% chance per parent with pool dilution."""

    parent_a_has = trait.trait.is_possessed_by(parent_a)
    parent_b_has = trait.trait.is_possessed_by(parent_b)

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "Neither", 0.0, 0.0)

    inherit_chance = 0.15

    final_prob = 0.0
    if parent_a_has:
        final_prob += inherit_chance / len(parent_a.disorders)
    if parent_b_has:
        final_prob += inherit_chance / len(parent_b.disorders)

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
        parent_favor_chance=0.0,
    )


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


def _calc_ability_inheritance(
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Ability inheritance with CORRECT class-favoring algebra and pool dilution."""

    # Use normalized abilities for pool
    parent_a_spells = parent_a.inheritable_abilities
    parent_b_spells = parent_b.inheritable_abilities

    parent_a_has = trait.trait.is_possessed_by(parent_a)
    parent_b_has = trait.trait.is_possessed_by(parent_b)

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "Neither", 0.0, 0.0)

    # Base inheritance chance: 0.2 + 0.025 * stim
    inherit_chance = _spell_inheritance_chance(stimulation)[0]

    # Class favoring chance: 0.01 * stim
    favor_chance = _class_favoring_chance(stimulation)

    # 1. Determine class spell presence
    parent_a_class = any(is_class_active(s) for s in parent_a_spells)
    parent_b_class = any(is_class_active(s) for s in parent_b_spells)

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
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Passive inheritance with SKILLSHARE+ guarantee and pool dilution."""

    # Use normalized passives for pool (already excludes SkillShare via property)
    parent_a_passives_norm = parent_a.inheritable_passives
    parent_b_passives_norm = parent_b.inheritable_passives

    parent_a_has = trait.trait.is_possessed_by(parent_a)
    parent_b_has = trait.trait.is_possessed_by(parent_b)

    # SKILLSHARE+ SPECIAL: 100% guaranteed
    # Check using RAW passives (must check for + variant)
    if has_skillshare_plus(parent_a) and parent_a_has:
        return TraitInheritanceProbability(
            trait=trait,
            probability=1.0,
            parent_source=f"{parent_a.name} (SkillShare+)",
            inherit_chance=1.0,
            parent_favor_chance=0.0,
        )

    if has_skillshare_plus(parent_b) and parent_b_has:
        return TraitInheritanceProbability(
            trait=trait,
            probability=1.0,
            parent_source=f"{parent_b.name} (SkillShare+)",
            inherit_chance=1.0,
            parent_favor_chance=0.0,
        )

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "Neither", 0.0, 0.0)

    inherit_chance = _passive_inheritance_chance(stimulation)
    favor_chance = _class_favoring_chance(stimulation)

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


def _calc_body_part_inheritance(
    parent_a: Cat,
    parent_b: Cat,
    stimulation: float,
    trait: TraitRequirement,
) -> TraitInheritanceProbability:
    """Mutation inheritance: 80% inherit, mutation favoring with stimulation."""

    body_trait: BodyPartTrait = trait.trait  # type: ignore[assignment]
    assert isinstance(body_trait, BodyPartTrait)
    slot = body_trait.get_slot()

    parent_a_has = body_trait.is_possessed_by(parent_a)
    parent_b_has = body_trait.is_possessed_by(parent_b)

    if not parent_a_has and not parent_b_has:
        return TraitInheritanceProbability(trait, 0.0, "Neither", 0.0, 0.0)

    # 80% chance to inherit parts (vs 20% reroll)
    inherit_all_chance = 0.8

    # Mutation favoring: (1.0 + 0.01*Stim) / (2.0 + 0.01*Stim)
    mutation_favor_chance = _better_chance(stimulation)

    # Check if each parent has a mutation in THIS specific slot
    parent_a_slot_mutated = cat_has_mutation_in_slot(parent_a, slot)
    parent_b_slot_mutated = cat_has_mutation_in_slot(parent_b, slot)

    # Apply favoring only when ONE parent has mutation in THIS slot
    if parent_a_slot_mutated and not parent_b_slot_mutated:
        parent_a_select_prob = mutation_favor_chance
    elif parent_b_slot_mutated and not parent_a_slot_mutated:
        parent_a_select_prob = 1.0 - mutation_favor_chance
    else:
        # Both mutated in this slot, or neither mutated - 50/50
        parent_a_select_prob = 0.5

    final_prob = inherit_all_chance * (
        parent_a_select_prob if parent_a_has else (1.0 - parent_a_select_prob)
    )

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
        inherit_chance=inherit_all_chance,
        parent_favor_chance=mutation_favor_chance,
    )
