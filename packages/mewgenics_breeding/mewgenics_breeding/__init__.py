"""
Mewgenics breeding overview: // From analysis of glaiel::CatData::breed
    1) Stats are inherited.
        * For each stat, either the parent_a or parent_b's is taken.
        * There is a (1.0 + 0.01*Stimulation) / (2.0 + 0.01*Stimulation) chance of the better of the two stats being inherited.
        * This means stimulation is surprisingly weak:
            * At 0 stimulation, it is a 50/50.
            * At 25 stimulation, there is a 5/9 chance of the better stat being inherited.
            * At 50 stimulation, there is a 3/5 chance of the better stat being inherited.
    2) Apply passives due to Skill Share+ (which guarantees a cat's other passive is passed down when breeding).
    3) Spells are inherited.
        * There is a 0.2+0.025*Stimulation chance of inheriting a spell from a cat's parents.
            * Thus, at 0 stimulation, there is a 20% chance, and at 32+, inheritance is guaranteed.
            * Ordinarily, there is a 50/50 chance of taking a random spell from the parent_a or parent_b.
            * However, there is a 0.01*Stimulation chance of attempting to favor a parent with class spells.
                * If this happens, then the game checks if only one of the parents has any class spells.
                * If it does, the chance of choosing the other parent is set to 0.
            * Once a parent to inherit from is chosen, one of that parent's spells is inherited at random.
        * There is a 0.02+0.005*Stimulation chance of inheriting a second spell from a cat's parents.
            * If this check passes, the second spell is selected the same way as the first.
    4) A passive is inherited.
        * There is a 0.05+0.01*Stimulation chance of inheriting a passive from a cat's parents.
            * Thus at 0 stimulation, there is a 5% chance. At 95+, inheritance is guaranteed.
            * Ordinarily, there is a 50/50 chance of taking a random passive from the parent_a or parent_b.
            * However, there is a 0.01*Stimulation chance of attempting to favor taking a passive from a parent with class passives.
                * This used to be bugged (preferred class actives), but as fixed in the 2026/02/20 patch.
                * This works the same way as spell inheritance, where if only one parent has class spells, the other parent is never selected.
            * Once a parent to inherit from is chosen, one of that parent's passives is inherited at random.
                * SkillShare is excluded from inheritance.
    5) Disorders are inherited.
        * There is a flat 15% chance of inheriting a random disorder from a cat's parent_a, and 15% of inheriting a random disorder from a cat's parent_b.
        * This is unaffected by any furniture stat.
    6) If fewer than 2 disorders were inherited, the cat rolls to receive a birth defect disorder.
        * There is a 0.02 + 0.4 * (inbreeding_coefficient - 0.2) chance of receiving a disorder as a birth defect.
            * Technically, min(max(inbreeding_coefficient - 0.2, 0.0), 1.0) is multiplied by 0.4.
        * Thus, all cats with fewer than 2 inherited disorders have a 2% chance of getting one as a birth defect; inbreeding scales linearly once the coefficient gets above a threshold.
    7) The cat rolls to decide if it should receive birth defect parts later.
        * If rand() < (1.5*inbreeding_coefficient) and inbreeding_coefficient is >0.05, then a cat will receive birth defect parts later in the process.
    8) A cat's parts are inherited (note: mutations are just specific part variants).
        * There is an 80% chance that all parts are inherited.
            * Otherwise, a random part-set (i.e. both legs, both eyebrows, the head, etc) is selected to not be inherited, and will be randomly assigned.
        * For each inherited part, either the parent_a's part or the parent_b's part is taken.
        * This works like stat inheritance for preferring mutations.
            * If only one of the two parents' parts is mutated, it is preferred with a (1.0 + 0.01*Stimulation) / (2.0 + 0.01*Stimulation) chance.
            * Otherwise, it's a straight 50/50.
    9) Parts are symmetrized.
        * For parts with a left/right which must be the same, there is a 50/50 chance of replacing the left with the right or vice-versa.
    10) ...something is inherited.
        * I am not sure what this is. There is a 98% chance of inheriting it from the parents, with an even 50/50 split.
    11) Voice is inherited.
        * I haven't fully worked out what this is doing, but it seems like a 2% chance of rerolling for a new voice, and a 98% chance of somehow inheriting voice from parents.
        * Note that this may be inaccurate.
    12) If additional birth defects were rolled in step 7, they are now applied.
        * If a cat's inbreeding coefficient is <= 0.9, it will perform one pass to apply birth defects.
        * Otherwise, it will perform two passes to apply birth defects.
"""

from dataclasses import dataclass
from typing import NamedTuple

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatBodySlot
from mewgenics_parser.trait_dictionary import is_class_active, is_class_passive

PART_SETS = [
    [CatBodySlot.TEXTURE],
    [CatBodySlot.BODY],
    [CatBodySlot.HEAD],
    [CatBodySlot.TAIL],
    [CatBodySlot.MOUTH],
    [CatBodySlot.LEFT_LEG, CatBodySlot.RIGHT_LEG],
    [CatBodySlot.LEFT_ARM, CatBodySlot.RIGHT_ARM],
    [CatBodySlot.LEFT_EYE, CatBodySlot.RIGHT_EYE],
    [CatBodySlot.LEFT_EYEBROW, CatBodySlot.RIGHT_EYEBROW],
    [CatBodySlot.LEFT_EAR, CatBodySlot.RIGHT_EAR],
]


class StatsProbabilityMass(NamedTuple):
    strength: list[tuple[int, float]]
    dexterity: list[tuple[int, float]]
    constitution: list[tuple[int, float]]
    intelligence: list[tuple[int, float]]
    speed: list[tuple[int, float]]
    charisma: list[tuple[int, float]]
    luck: list[tuple[int, float]]


@dataclass(frozen=True)
class OffspringProbabilityMass:
    """The probability mass of a cat's offspring's traits, given the parents and breeding conditions."""

    stats: StatsProbabilityMass
    """The probability mass of the cat's offspring having each possible stat value. Each stat value is a tuple of (stat_value, probability)."""

    passive_abilities: dict[str, float]
    """The probability mass of the cat's offspring inheriting each passive ability. Maps passive ability ID to probability."""

    active_abilities: dict[str, float]
    """The probability mass of the cat's offspring inheriting each active ability. Maps active ability ID to probability."""

    inherited_disorders: dict[str, float]
    """The probability mass of the cat's offspring inheriting each disorder from its parents. Maps disorder ID to probability."""

    novel_disorder: float
    """The probability of the cat's offspring receiving a novel disorder as a birth defect. This is only rolled if the cat inherits fewer than 2 disorders from its parents."""

    body_parts: dict[CatBodySlot, dict[int, float]]
    """The probability mass of the cat's offspring inheriting each body part. Maps body slot to a dict mapping part ID to probability."""

    novel_birth_defect: float
    """The probability of the cat's offspring receiving novel birth defect parts. This is rolled independently of disorder inheritance, and is applied after part inheritance."""

    expected_inherited_disorders: float
    """The expected count of disorders inherited from parents (sum of disorder probabilities)."""

    expected_inherited_defects: float
    """The expected count of part defects inherited from parents, counted per representative slot (one per part-set)."""


def _clamp_prob(prob: float) -> float:
    return max(0.0, min(1.0, prob))


def _stats_inheritance(
    parent_a: Cat, parent_b: Cat, stimulation: float
) -> StatsProbabilityMass:
    # --- Stats (Step 1) ---
    better_stat_prob = _clamp_prob(
        (1.0 + 0.01 * stimulation) / (2.0 + 0.01 * stimulation)
    )
    stats_list = []
    for parent_a_stat, parent_b_stat in zip(parent_a.stat_base, parent_b.stat_base):
        better_stat = max(parent_a_stat, parent_b_stat)
        worse_stat = min(parent_a_stat, parent_b_stat)
        if better_stat == worse_stat:
            # stats[idx].append((better_stat, 1.0))
            stats_list.append([(better_stat, 1.0)])
        else:
            stats_list.append(
                [(better_stat, better_stat_prob), (worse_stat, 1.0 - better_stat_prob)]
            )
    return StatsProbabilityMass(*stats_list)


def _active_ability_inheritance(
    parent_a: Cat, parent_b: Cat, stimulation: float
) -> dict[str, float]:
    favor_class_prob = _clamp_prob(0.01 * stimulation)

    # --- Active Abilities (Steps 3 & 4) ---
    active_abilities_slot1 = {}
    active_abilities_slot2 = {}
    inherit_first_spell_prob = _clamp_prob(0.2 + 0.025 * stimulation)
    inherit_second_spell_prob = _clamp_prob(0.02 + 0.005 * stimulation)
    if inherit_first_spell_prob > 0:
        parent_a_has_class_spell = any(
            is_class_active(spell) for spell in parent_a.inheritable_actives
        )
        parent_b_has_class_spell = any(
            is_class_active(spell) for spell in parent_b.inheritable_actives
        )

        if parent_a_has_class_spell and not parent_b_has_class_spell:
            parent_a_select_prob = (
                1.0 * favor_class_prob + (1.0 - favor_class_prob) * 0.5
            )
            parent_b_select_prob = 1.0 - parent_a_select_prob
        elif parent_b_has_class_spell and not parent_a_has_class_spell:
            parent_b_select_prob = (
                1.0 * favor_class_prob + (1.0 - favor_class_prob) * 0.5
            )
            parent_a_select_prob = 1.0 - parent_b_select_prob
        else:
            parent_a_select_prob = parent_b_select_prob = 0.5

        for parent, select_prob in [
            (parent_a, parent_a_select_prob),
            (parent_b, parent_b_select_prob),
        ]:
            for active in parent.inheritable_actives:
                active_abilities_slot1.setdefault(active, 0.0)
                active_abilities_slot1[active] += (
                    inherit_first_spell_prob
                    * select_prob
                    / len(parent.inheritable_actives)
                )

                active_abilities_slot2.setdefault(active, 0.0)
                active_abilities_slot2[active] += (
                    inherit_second_spell_prob
                    * select_prob
                    / len(parent.inheritable_actives)
                )
    active_abilities = {
        active: active_abilities_slot1.get(active, 0.0)
        + active_abilities_slot2.get(active, 0.0)
        - (
            active_abilities_slot1.get(active, 0.0)
            * active_abilities_slot2.get(active, 0.0)
        )
        for active in set(active_abilities_slot1) | set(active_abilities_slot2)
    }
    return active_abilities


def _passive_ability_inheritance(
    parent_a: Cat, parent_b: Cat, stimulation: float
) -> dict[str, float]:
    favor_class_prob = _clamp_prob(0.01 * stimulation)

    # --- Passive Abilities (Step 4) ---
    passive_abilities = {}
    parent_a_ss = any(p == "SkillShare2" for p in parent_a.passive_abilities)
    parent_b_ss = any(p == "SkillShare2" for p in parent_b.passive_abilities)
    if parent_a_ss or parent_b_ss:
        # --- Skill Share+ Inheritance (Step 2) ---
        if parent_a_ss:
            [parent_a_passive] = parent_a.inheritable_passives
            passive_abilities[parent_a_passive] = 1.0
        if parent_b_ss:
            [parent_b_passive] = parent_b.inheritable_passives
            passive_abilities[parent_b_passive] = 1.0
    else:
        inherit_passive_prob = _clamp_prob(0.05 + 0.01 * stimulation)
        parent_a_has_class_passive = any(
            is_class_passive(passive) for passive in parent_a.inheritable_passives
        )
        parent_b_has_class_passive = any(
            is_class_passive(passive) for passive in parent_b.inheritable_passives
        )

        if parent_a_has_class_passive and not parent_b_has_class_passive:
            parent_a_select_prob = (
                1.0 * favor_class_prob + (1.0 - favor_class_prob) * 0.5
            )
            parent_b_select_prob = 1.0 - parent_a_select_prob
        elif parent_b_has_class_passive and not parent_a_has_class_passive:
            parent_b_select_prob = (
                1.0 * favor_class_prob + (1.0 - favor_class_prob) * 0.5
            )
            parent_a_select_prob = 1.0 - parent_b_select_prob
        else:
            parent_a_select_prob = parent_b_select_prob = 0.5

        for parent, select_prob in [
            (parent_a, parent_a_select_prob),
            (parent_b, parent_b_select_prob),
        ]:
            for passive in parent.inheritable_passives:
                passive_abilities.setdefault(passive, 0.0)
                passive_abilities[passive] += (
                    inherit_passive_prob
                    * select_prob
                    / len(parent.inheritable_passives)
                )
    return passive_abilities


def _disorder_inheritance(parent_a: Cat, parent_b: Cat) -> dict[str, float]:
    # --- Inherited Disorders (Step 5) ---
    inherited_disorders = {}

    for parent in (parent_a, parent_b):
        for disorder in parent.disorders:
            inherited_disorders.setdefault(disorder, 0.0)
            inherited_disorders[disorder] += (
                0.15 / len(parent.disorders) * (1 - 1 * inherited_disorders[disorder])
            )
    return inherited_disorders


def _novel_disorder_inheritance(parent_a: Cat, parent_b: Cat, coi: float) -> float:
    # --- Novel Disorder (Step 6) ---
    # The cat only rolls for a novel disorder if it inherited fewer than 2.
    # The probability of inheriting exactly 2 is the probability that both parents triggered their 15% roll.
    parent_a_disorder_prob = 0.15 if parent_a.disorders else 0.0
    parent_b_disorder_prob = 0.15 if parent_b.disorders else 0.0
    two_inherited_prob = parent_a_disorder_prob * parent_b_disorder_prob
    novel_disorder = 1.0 - two_inherited_prob
    base_novel_disorder_prob = 0.02 + 0.4 * _clamp_prob(coi - 0.2)
    novel_disorder = novel_disorder * base_novel_disorder_prob
    return novel_disorder


def _body_part_inheritance(
    parent_a: Cat, parent_b: Cat, stimulation: float, coi: float
) -> tuple[dict[CatBodySlot, dict[int, float]], float]:
    # --- Body Parts & Symmetrization (Steps 8 & 9) ---
    better_stat_prob = _clamp_prob(
        (1.0 + 0.01 * stimulation) / (2.0 + 0.01 * stimulation)
    )
    body_parts: dict[CatBodySlot, dict[int, float]] = {
        slot: {} for pair in PART_SETS for slot in pair
    }
    base_part_inherit = 0.80 + 0.20 * (9.0 / 10.0)  # 0.98

    for part_set in PART_SETS:
        raw_probs = {slot: {} for slot in part_set}

        for slot in part_set:
            parent_a_part = parent_a.body_parts.get(slot, 0)
            parent_b_part = parent_b.body_parts.get(slot, 0)

            # Mutations are >= 300, negative defects are < 0 (e.g., -2) or 700-710
            parent_a_mutated = parent_a_part >= 300 or parent_a_part < 0
            parent_b_mutated = parent_b_part >= 300 or parent_b_part < 0

            # Mutation favoring logic
            if parent_a_mutated and not parent_b_mutated:
                p_parent_a, p_parent_b = better_stat_prob, 1.0 - better_stat_prob
            elif parent_b_mutated and not parent_a_mutated:
                p_parent_b, p_parent_a = better_stat_prob, 1.0 - better_stat_prob
            else:
                p_parent_a, p_parent_b = 0.5, 0.5

            prob_parent_a_wins = base_part_inherit * p_parent_a
            prob_parent_b_wins = base_part_inherit * p_parent_b

            raw_probs[slot][parent_a_part] = (
                raw_probs[slot].get(parent_a_part, 0.0) + prob_parent_a_wins
            )
            raw_probs[slot][parent_b_part] = (
                raw_probs[slot].get(parent_b_part, 0.0) + prob_parent_b_wins
            )

        # Symmetrization (Step 9)
        if len(part_set) == 1:
            body_parts[part_set[0]] = raw_probs[part_set[0]]
        else:
            left_slot, right_slot = part_set
            all_parts = set(raw_probs[left_slot].keys()) | set(
                raw_probs[right_slot].keys()
            )

            for p_id in all_parts:
                avg_prob = 0.5 * raw_probs[left_slot].get(p_id, 0.0) + 0.5 * raw_probs[
                    right_slot
                ].get(p_id, 0.0)
                if avg_prob > 0:
                    body_parts[left_slot][p_id] = avg_prob
                    body_parts[right_slot][p_id] = avg_prob

    # --- Novel Birth Defect Parts (Steps 7 & 12) ---
    novel_birth_defect = _clamp_prob(1.5 * coi) if coi > 0.05 else 0.0
    # Assuming defects target the 10 part-sets uniformly
    overwrite_chance = _clamp_prob(novel_birth_defect / 10.0)
    survival_multiplier = 1.0 - overwrite_chance
    for slot, part_dict in body_parts.items():
        for p_id in part_dict:
            part_dict[p_id] *= survival_multiplier

    return body_parts, novel_birth_defect


def simulate_breeding(
    parent_a: Cat, parent_b: Cat, stimulation: float, coi: float
) -> OffspringProbabilityMass:
    assert stimulation >= 0
    stats = _stats_inheritance(parent_a, parent_b, stimulation)
    passive_abilities = _passive_ability_inheritance(parent_a, parent_b, stimulation)
    active_abilities = _active_ability_inheritance(parent_a, parent_b, stimulation)
    inherited_disorders = _disorder_inheritance(parent_a, parent_b)
    novel_disorder = _novel_disorder_inheritance(parent_a, parent_b, coi)
    body_parts, novel_birth_defect = _body_part_inheritance(
        parent_a, parent_b, stimulation, coi
    )

    expected_inherited_disorders = sum(inherited_disorders.values())

    _REP_SLOTS = [
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
    expected_inherited_defects = sum(
        prob
        for slot in _REP_SLOTS
        for pid, prob in body_parts.get(slot, {}).items()
        if pid < 0 or (700 <= pid <= 710)
    )

    return OffspringProbabilityMass(
        stats,
        passive_abilities,
        active_abilities,
        inherited_disorders,
        novel_disorder,
        body_parts,
        novel_birth_defect,
        expected_inherited_disorders,
        expected_inherited_defects,
    )
