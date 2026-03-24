"""Tests validating that simulate_breeding matches legacy game mechanics.

These tests were ported from mewgenics_scorer's test_factors.py after
the backend swap to mewgenics_breeding's simulate_breeding function.
"""

from pytest import approx

from mewgenics_breeding import simulate_breeding
from mewgenics_parser.cat import Cat, CatBodySlot, CatGender, CatStatus, Stats


def _default_body_parts() -> dict[CatBodySlot, int]:
    return {
        CatBodySlot.TEXTURE: 0,
        CatBodySlot.BODY: 0,
        CatBodySlot.HEAD: 0,
        CatBodySlot.TAIL: 0,
        CatBodySlot.LEFT_LEG: 0,
        CatBodySlot.RIGHT_LEG: 0,
        CatBodySlot.LEFT_ARM: 0,
        CatBodySlot.RIGHT_ARM: 0,
        CatBodySlot.LEFT_EYE: 0,
        CatBodySlot.RIGHT_EYE: 0,
        CatBodySlot.LEFT_EYEBROW: 0,
        CatBodySlot.RIGHT_EYEBROW: 0,
        CatBodySlot.LEFT_EAR: 0,
        CatBodySlot.RIGHT_EAR: 0,
        CatBodySlot.MOUTH: 0,
    }


DEFAULT_PARTS = _default_body_parts()


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    stat_base: list[int] | None = None,
    passives: list | None = None,
    abilities: list | None = None,
    disorders: list | None = None,
    body_parts: dict[CatBodySlot, int] | None = None,
) -> Cat:
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        status=CatStatus.IN_HOUSE,
        gender=gender,
        stat_base=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        stat_total=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        aggression=0.5,
        libido=0.5,
        sexuality=None,
        passive_abilities=passives or [],
        active_abilities=abilities or [],
        disorders=disorders or [],
        parent_a=None,
        parent_b=None,
        room="Test Room",
        age=5,
        body_parts=body_parts or DEFAULT_PARTS.copy(),
        lover=None,
        hater=None,
        fertility=0.5,
        level=1,
        collar="",
        coi=0.0,
    )


class TestAbilityPoolDilution:
    """Tests for ability inheritance with pool dilution.

    Note: The first 2 active abilities (default move + default attack) are not
    inheritable. So ability at index 0 is NOT inheritable.
    """

    def test_ability_pool_dilution(self) -> None:
        """Mother has 4 spells (indices 0-3), father has 1 (index 0, skipped).

        Mother inheritable: C (idx 2), PathOfTheHunter (idx 3) = pool size 2
        Father inheritable: empty (only 1 ability at idx 0, skipped)

        At 0 stim with no class spells:
        - Parent pick: 50% mom, 50% dad (dad contributes 0 due to empty pool)
        - First spell inherit: 20% * 50% = 0.1
        - Second spell inherit: 2% * 50% = 0.01
        - Pool pick (mom): 1/2 = 0.5

        Combined: P = (0.1 + 0.01 - 0.1*0.01) * 0.5 = 0.05475
        """
        mother = make_cat(1, abilities=["A", "B", "C", "PathOfTheHunter"])
        father = make_cat(2, abilities=["Zap"])
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        assert pmf.active_abilities.get("PathOfTheHunter", 0.0) == approx(0.05475)

    def test_ability_single_parent_has(self) -> None:
        """Mother has PathOfTheHunter at index 0 (NOT inheritable - skipped).

        Since index 0 is the default move and not inheritable, this returns 0.
        """
        mother = make_cat(1, abilities=["PathOfTheHunter"])
        father = make_cat(2, abilities=[])
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        assert pmf.active_abilities.get("PathOfTheHunter", 0.0) == 0.0


class TestPassivePoolDilution:
    """Tests for passive inheritance with pool dilution."""

    def test_passive_single_parent(self) -> None:
        """Father has no passives. Mother has one passive 'Sturdy'.

        Expected: 50% parent pick * 5% inherit = 2.5%
        """
        mother = make_cat(1, passives=["Sturdy"])
        father = make_cat(2, passives=[])
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        assert pmf.passive_abilities.get("Sturdy", 0.0) == approx(0.025)


class TestDisorderPoolDilution:
    """Tests for disorder inheritance with pool dilution."""

    def test_disorder_single_parent(self) -> None:
        """Mother has one disorder 'Blind'. Should be 15%."""
        mother = make_cat(1, disorders=["Blind"])
        father = make_cat(2, disorders=[])
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        assert pmf.inherited_disorders.get("Blind", 0.0) == approx(0.15)

    def test_disorder_pool_dilution(self) -> None:
        """Mother has 3 disorders. Query one. Should be 0.15/3 = 5%."""
        mother = make_cat(1, disorders=["Blind", "Lame", "Deaf"])
        father = make_cat(2, disorders=[])
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        assert pmf.inherited_disorders.get("Blind", 0.0) == approx(0.05)


class TestSymmetrization:
    """Tests for body part symmetrization logic.

    Symmetrization averages left/right probabilities with 50% chance to copy
    one side to the other. For paired slots (like EARS), we check only the
    first slot to avoid double-counting.
    """

    def test_cross_symmetrical_parents(self) -> None:
        """Mom has LEFT_EAR=300, Dad has RIGHT_EAR=300. Query Ears300.

        Expected: symmetrization averages both sides -> 0.49
        Left probability = 0.5 * (prob_left_from_mom + prob_left_from_dad)
        = 0.5 * (0.49 + 0.49) = 0.49
        """
        mother = make_cat(1, body_parts={**DEFAULT_PARTS, CatBodySlot.LEFT_EAR: 300})
        father = make_cat(2, body_parts={**DEFAULT_PARTS, CatBodySlot.RIGHT_EAR: 300})
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        prob = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(300, 0.0)
        assert prob == approx(0.49)

    def test_full_bilateral_symmetry(self) -> None:
        """Mother has Ears300 in both LEFT and RIGHT. Query Ears300.

        Expected: 98% inherit * 0.5 symmetrization = 0.49
        When both sides have the same mutation, symmetrization of 0.5 * (0.5 + 0.5) = 0.5
        """
        mother = make_cat(
            1,
            body_parts={
                **DEFAULT_PARTS,
                CatBodySlot.LEFT_EAR: 300,
                CatBodySlot.RIGHT_EAR: 300,
            },
        )
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        prob = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(300, 0.0)
        assert prob == approx(0.49)

    def test_unpaired_category_no_symmetrization(self) -> None:
        """Tail is unpaired - should not go through symmetrization.

        Mother has TAIL=300, no mutation on father.
        Expected: 98% * 50% = 0.49 (no symmetrization division)
        """
        mother = make_cat(1, body_parts={**DEFAULT_PARTS, CatBodySlot.TAIL: 300})
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        prob = pmf.body_parts.get(CatBodySlot.TAIL, {}).get(300, 0.0)
        assert prob == approx(0.49)

    def test_mutation_favoring_at_stimulation_50(self) -> None:
        """At 50 stim, mutation favor = 60%.

        Mom has LEFT_EAR=300, dad has none. Query Ears300 at 50 stim.
        At 50 stim: favor = (1 + 0.5)/(2 + 0.5) = 1.5/2.5 = 0.6
        prob_given_inherit = 0.5 * (0.6 + 0.4) = 0.5 (symmetrization of 60% favor)
        Final = 0.98 * 0.5 * 0.6 = 0.294
        """
        mother = make_cat(1, body_parts={**DEFAULT_PARTS, CatBodySlot.LEFT_EAR: 300})
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=0.0)
        prob = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(300, 0.0)
        assert prob == approx(0.294)

    def test_mutation_favoring_at_stimulation_0(self) -> None:
        """At 0 stim, mutation favor = 50%.

        Mom has LEFT_EAR=300, dad has none. Query Ears300 at 0 stim.
        98% inherit * symmetrization(50% favor) = 0.98 * 0.25 = 0.245
        """
        mother = make_cat(1, body_parts={**DEFAULT_PARTS, CatBodySlot.LEFT_EAR: 300})
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)
        prob = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(300, 0.0)
        assert prob == approx(0.245)


class TestMutationFavoringRegression:
    """Regression tests for specific mutation-favoring bugs."""

    def test_neither_parent_has_mutation_returns_zero(self) -> None:
        """Parents have Ears300 and Ears400, but we ask about Ears700.

        This was a bug where the probability was non-zero even though
        neither parent has Ears700. The fix ensures exact part_id matching.
        """
        mother = make_cat(1, body_parts={**DEFAULT_PARTS, CatBodySlot.LEFT_EAR: 300})
        father = make_cat(2, body_parts={**DEFAULT_PARTS, CatBodySlot.RIGHT_EAR: 400})
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)

        # Neither parent has Ears700, so probability should be 0
        prob = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(700, 0.0)
        assert prob == 0.0, f"Expected 0.0 but got {prob}"


class TestInheritedPartDefectEdgeCases:
    """Tests for inherited part defects edge cases."""

    def test_no_defects_returns_zero(self) -> None:
        """Both parents have no mutations (all parts = 0). No defects possible."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)

        # Sum all defect probabilities (part_id < 0 or >= 700)
        defect_total = 0.0
        for slot_probs in pmf.body_parts.values():
            for part_id, prob in slot_probs.items():
                if part_id < 0 or part_id >= 700:
                    defect_total += prob
        assert defect_total == 0.0

    def test_multi_category_defect_accumulation(self) -> None:
        """Ear defect (paired) + Tail defect (unpaired) should accumulate via OR.

        Paired slot (EAR): 98% * 25% symmetrized = 24.5%
        Unpaired slot (TAIL): 98% * 50% = 49%
        OR accumulation: 1 - (1-0.245)*(1-0.49) = 0.61495
        """
        mother = make_cat(
            1,
            body_parts={
                **DEFAULT_PARTS,
                CatBodySlot.LEFT_EAR: 700,  # Paired slot defect
                CatBodySlot.TAIL: 700,  # Unpaired slot defect
            },
        )
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=0.0, coi=0.0)

        # Check individual defect probabilities
        ear_defect = pmf.body_parts.get(CatBodySlot.LEFT_EAR, {}).get(700, 0.0)
        tail_defect = pmf.body_parts.get(CatBodySlot.TAIL, {}).get(700, 0.0)

        # Ear: 0.98 * 0.25 symmetrized = 0.245
        assert ear_defect == approx(0.245)
        # Tail: 0.98 * 0.5 = 0.49
        assert tail_defect == approx(0.49)


class TestNovelMaladyThresholds:
    """Tests for novel disorder and birth defect thresholds at various CoI levels."""

    def test_novel_disorder_at_coi_0(self) -> None:
        """At CoI=0, base novel disorder is 2%."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=0.0)
        assert pmf.novel_disorder == approx(0.02)

    def test_novel_disorder_at_coi_0_3(self) -> None:
        """At CoI=0.3, novel disorder = 0.02 + 0.4*(0.3-0.2) = 0.06."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=0.3)
        assert pmf.novel_disorder == approx(0.06)

    def test_novel_disorder_at_coi_1_0(self) -> None:
        """At CoI=1.0, novel disorder = 0.02 + 0.4*min(0.8,1.0) = 0.34."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=1.0)
        assert pmf.novel_disorder == approx(0.34)

    def test_novel_part_defect_at_coi_below_threshold(self) -> None:
        """At CoI <= 0.05, no novel birth defects."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=0.03)
        assert pmf.novel_birth_defect == 0.0

    def test_novel_part_defect_at_coi_0_5(self) -> None:
        """At CoI=0.5, novel birth defect = 1.5 * 0.5 = 0.75."""
        mother = make_cat(1)
        father = make_cat(2)
        pmf = simulate_breeding(mother, father, stimulation=50.0, coi=0.5)
        assert pmf.novel_birth_defect == approx(0.75)
