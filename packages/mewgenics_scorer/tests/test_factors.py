"""Tests for mewgenics_scorer factors module."""

import pytest
from inline_snapshot import snapshot
from mewgenics_parser import Cat, TraitCategory, create_trait
from mewgenics_parser.cat import CatBodyParts, CatGender, CatStatus, Stats

from mewgenics_scorer.factors import *
from mewgenics_scorer.factors import _aggression_factor, _libido_factor, _stat_variance
from mewgenics_scorer.inheritance import *
from mewgenics_scorer.inheritance import (
    _better_chance,
    _class_favoring_chance,
    _passive_inheritance_chance,
    _spell_inheritance_chance,
    cat_has_defect_in_slot,
    cat_has_mutation_in_slot,
    inherited_disorder_chance,
    inherited_part_defect_chance,
    novel_disorder_chance,
    novel_part_defect_chance,
)
from mewgenics_scorer.types import TraitRequirement
from mewgenics_parser.traits import BodyPartTrait


def _default_body_parts() -> CatBodyParts:
    return CatBodyParts(
        texture=0,
        body=0,
        head=0,
        tail=0,
        legs=0,
        arms=0,
        eyes=0,
        eyebrows=0,
        ears=0,
        mouth=0,
    )


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    stat_base: list[int] | None = None,
    aggression: float | None = None,
    libido: float | None = None,
    passives: list | None = None,
    abilities: list | None = None,
    disorders: list | None = None,
    lovers: list[Cat] | None = None,
    haters: list[Cat] | None = None,
    parent_a: Cat | None = None,
    parent_b: Cat | None = None,
    body_parts: CatBodyParts | None = None,
):
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        status=CatStatus.IN_HOUSE,
        gender=gender,
        stat_base=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        stat_total=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        aggression=aggression,
        libido=libido,
        passive_abilities=passives or [],
        active_abilities=abilities or [],
        disorders=disorders or [],
        lovers=lovers or [],
        haters=haters or [],
        parent_a=parent_a,
        parent_b=parent_b,
        room="Test Room",
        age=5,
        coi=0.0,
        body_parts=body_parts or _default_body_parts(),
    )


class TestExpectedStats:
    """Tests for expected_stats function."""

    def test_identical_stats(self):
        a = make_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, stat_base=[5, 5, 5, 5, 5, 5, 5])
        result = expected_stats(a, b, 50.0)
        assert all(s == 5.0 for s in result)

    def test_different_stats(self):
        a = make_cat(1, stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_cat(2, stat_base=[0, 10, 0, 0, 0, 0, 0])
        result = expected_stats(a, b, 50.0)
        # First stat: max(10,0)*chance + min(10,0)*(1-chance) = 10*chance
        # Second stat: max(0,10)*chance + min(0,10)*(1-chance) = 10*chance
        chance = _better_chance(50.0)
        assert abs(result[0] - 10 * chance) < 0.0001
        assert abs(result[1] - 10 * chance) < 0.0001


class TestStatVariance:
    """Tests for stat_variance function."""

    def test_identical_stats(self):
        a = make_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, stat_base=[5, 5, 5, 5, 5, 5, 5])
        assert _stat_variance(a, b) == 0.0

    def test_all_different(self):
        a = make_cat(1, stat_base=[10, 10, 10, 10, 10, 10, 10])
        b = make_cat(2, stat_base=[0, 0, 0, 0, 0, 0, 0])
        assert _stat_variance(a, b) == 70.0  # 7 * 10


class TestAggressionFactor:
    """Tests for aggression_factor function."""

    def test_both_low_aggression(self):
        a = make_cat(1, aggression=0.1)
        b = make_cat(2, aggression=0.1)
        result = _aggression_factor(a, b)
        assert result > 0.8  # High factor for low aggression

    def test_both_high_aggression(self):
        a = make_cat(1, aggression=0.9)
        b = make_cat(2, aggression=0.9)
        result = _aggression_factor(a, b)
        assert result < 0.2  # Low factor for high aggression

    def test_unknown_aggression_defaults(self):
        a = make_cat(1, aggression=None)
        b = make_cat(2, aggression=None)
        assert _aggression_factor(a, b) == 0.5


class TestLibidoFactor:
    """Tests for libido_factor function."""

    def test_both_low_libido(self):
        a = make_cat(1, libido=0.1)
        b = make_cat(2, libido=0.1)
        result = _libido_factor(a, b)
        assert result < 0.2

    def test_both_high_libido(self):
        a = make_cat(1, libido=0.9)
        b = make_cat(2, libido=0.9)
        result = _libido_factor(a, b)
        assert result > 0.8

    def test_unknown_libido_defaults(self):
        a = make_cat(1, libido=None)
        b = make_cat(2, libido=None)
        assert _libido_factor(a, b) == 0.5


class TestCalculatePairFactors:
    """Tests for calculate_pair_factors function."""

    def test_basic_calculation(self):
        a = make_cat(1, CatGender.MALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, CatGender.FEMALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        assert isinstance(result, PairFactors)
        assert result.can_breed is True
        assert result.hater_conflict is False
        assert result.lover_conflict is False
        assert result.mutual_lovers is False

    def test_unrelated_cats_no_risk(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        # Unrelated cats have CoI = 0.0, so:
        # - disorder chance = 2% (base)
        # - part defect chance = 0% (CoI <= 0.05)
        assert result.novel_disorder_chance == 0.02
        assert result.novel_part_defect_chance == 0.0

    def test_total_expected_stats(self):
        a = make_cat(1, CatGender.MALE, stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_cat(2, CatGender.FEMALE, stat_base=[0, 10, 0, 0, 0, 0, 0])
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        # Should be 7 values that sum to something based on better_chance
        assert len(result.expected_stats) == 7
        assert result.total_expected_stats == sum(result.expected_stats)


class TestSpellInheritanceChance:
    """Tests for spell inheritance chance functions."""

    def test_spell_inheritance_0_stim(self):
        first, second = _spell_inheritance_chance(0.0)
        assert first == 0.2
        assert second == 0.02

    def test_spell_inheritance_32_stim(self):
        first, second = _spell_inheritance_chance(32.0)
        assert first == 1.0  # 0.2 + 0.025*32 = 1.0 (capped)
        assert second == 0.02 + 0.005 * 32

    def test_spell_inheritance_50_stim(self):
        first, second = _spell_inheritance_chance(50.0)
        assert first == 1.0  # Capped at 1.0
        assert second == 0.27  # 0.02 + 0.005*50 = 0.27


class TestPassiveInheritanceChance:
    """Tests for passive inheritance chance."""

    def test_passive_inheritance_0_stim(self):
        chance = _passive_inheritance_chance(0.0)
        assert chance == 0.05

    def test_passive_inheritance_50_stim(self):
        chance = _passive_inheritance_chance(50.0)
        assert chance == 0.55  # 0.05 + 0.01*50

    def test_passive_inheritance_95_stim(self):
        chance = _passive_inheritance_chance(95.0)
        assert chance == 1.0  # Capped at 1.0


class TestClassFavoringChance:
    """Tests for class-favoring chance."""

    def test_favoring_0_stim(self):
        chance = _class_favoring_chance(0.0)
        assert chance == 0.0

    def test_favoring_50_stim(self):
        chance = _class_favoring_chance(50.0)
        assert chance == 0.5

    def test_favoring_100_stim(self):
        chance = _class_favoring_chance(100.0)
        assert chance == 1.0


class TestTraitInheritanceProbability:
    """Tests for calculate_trait_probability function."""

    def test_ability_neither_parent_has(self):
        mother = make_cat(1, abilities=[])
        father = make_cat(2, abilities=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        assert result.probability == 0.0
        assert result.parent_source in ("None", "Neither")

    def test_ability_single_parent_has(self):
        mother = make_cat(1, abilities=["PathOfTheHunter"])
        father = make_cat(2, abilities=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # At 0 stim: 50% parent pick * 20% inherit chance * 100% pool = 10%
        # Parent selection is decoupled from trait possession
        assert result.probability == pytest.approx(0.1)

    def test_ability_pool_dilution(self):
        # Mother has 4 spells, father has 1
        mother = make_cat(1, abilities=["A", "B", "C", "PathOfTheHunter"])
        father = make_cat(2, abilities=["Zap"])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # 50% parent pick * 20% inherit chance * (1/4 pool size) = 2.5%
        # Parent selection is decoupled from trait possession
        assert result.probability == pytest.approx(0.025)

    def test_passive_skillshare_plus_guaranteed(self):
        mother = make_cat(1, passives=["SkillShare2", "Sturdy"])
        father = make_cat(2, passives=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # SkillShare+ guarantees other passives
        assert result.probability == 1.0
        assert "SkillShare+" in result.parent_source

    def test_passive_disorder_not_in_passive_pool(self):
        # Disorders should NOT be in passive_abilities (separated at parse time)
        mother = make_cat(1, passives=["Sturdy"], disorders=["Blind"])
        father = make_cat(2, passives=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.PASSIVE_ABILITY, "Blind")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # blind is a disorder, not a passive - should not inherit via passive mechanics
        assert result.probability == 0.0

    # def test_mutation_inheritance_80_percent(self):
    #     mother = make_cat(1, mutations=["Frostbit"])
    #     father = make_cat(2, mutations=[])
    #     trait = TraitRequirement("mutation", "Frostbit")
    #
    #     result = calculate_trait_probability(trait, mother, father, 0.0)
    #
    #     # 80% inherit parts * 50% favor for mother (when only she has it at 0 stim)
    #     # = 0.8 * 0.5 = 0.4
    #     assert result.probability == pytest.approx(0.4)
    #
    # def test_mutation_favoring_with_stimulation(self):
    #     mother = make_cat(1, mutations=["Frostbit"])
    #     father = make_cat(2, mutations=[])
    #     trait = TraitRequirement("mutation", "Frostbit")
    #
    #     result = calculate_trait_probability(trait, mother, father, 50.0)
    #
    #     # At 50 stim, mutation favor = (1 + 0.5)/(2 + 0.5) = 1.5/2.5 = 0.6
    #     # 80% inherit * 60% favor = 48%
    #     expected = 0.8 * ((1.0 + 0.01 * 50) / (2.0 + 0.01 * 50))
    #     assert result.probability == pytest.approx(expected)
    #
    def test_passive_skillshare_not_inherited(self):
        """Base SkillShare cannot be inherited - should always return 0%."""
        mother = make_cat(1, passives=["SkillShare", "Sturdy"])
        father = make_cat(2, passives=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.PASSIVE_ABILITY, "SkillShare")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Base skillshare is excluded from inheritable pool
        assert result.probability == 0.0

    def test_passive_upgraded_ability_normalized(self):
        """Querying for base passive matches parent's upgraded variant."""
        mother = make_cat(1, passives=["Sturdy2"])
        father = make_cat(2, passives=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Should match because normalized = "sturdy"
        assert result.probability > 0.0

    def test_ability_upgraded_ability_normalized(self):
        """Querying for base ability matches parent's upgraded variant."""
        mother = make_cat(1, abilities=["PathOfTheHunter2"])
        father = make_cat(2, abilities=[])
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        )

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Should match because normalized = "paththehunter"
        assert result.probability > 0.0


class TestClassFavoringAlgebra:
    """Tests verifying the corrected class-favoring math."""

    def test_class_favoring_100_percent(self):
        # At 100 stim, favor_chance = 1.0
        # mother_select should be 0.5 + 0.5*1.0 = 1.0
        mother = make_cat(1, abilities=["PathOfTheHunter"])  # class spell
        father = make_cat(2, abilities=["Swat"])  # generic spell
        trait = TraitRequirement(
            trait=create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        )

        result = calculate_trait_probability(trait, mother, father, 100.0)

        # With 100% favor chance, should strongly favor mother (class spell holder)
        # At 100 stim, inherit chance is capped at 1.0
        assert result.parent_favor_chance == 1.0


class TestNovelMaladyChance:
    """Tests for novel disorder and part defect chance functions."""

    def test_novel_disorder_at_coi_0(self):
        assert novel_disorder_chance(0.0) == 0.02

    def test_novel_disorder_at_coi_0_3(self):
        assert novel_disorder_chance(0.3) == pytest.approx(0.06)

    def test_novel_disorder_at_coi_1_0(self):
        # Formula: 0.02 + 0.4 * min(max(coi - 0.2, 0.0), 1.0)
        # At coi=1.0: 0.02 + 0.4 * min(0.8, 1.0) = 0.02 + 0.32 = 0.34
        assert novel_disorder_chance(1.0) == pytest.approx(0.34)

    def test_novel_part_defect_at_coi_0_03(self):
        assert novel_part_defect_chance(0.03) == 0.0

    def test_novel_part_defect_at_coi_0_5(self):
        assert novel_part_defect_chance(0.5) == 0.75


class TestInheritedDisorderChance:
    """Tests for inherited_disorder_chance function."""

    def test_no_parents_no_disorders(self):
        a = make_cat(1, disorders=[])
        b = make_cat(2, disorders=[])
        assert inherited_disorder_chance(a, b) == 0.0

    def test_one_parent_has_disorder(self):
        a = make_cat(1, disorders=["Blind"])
        b = make_cat(2, disorders=[])
        assert inherited_disorder_chance(a, b) == pytest.approx(0.15)

    def test_both_parents_have_disorders(self):
        a = make_cat(1, disorders=["Blind", "Lame"])
        b = make_cat(2, disorders=["Deaf"])
        result = inherited_disorder_chance(a, b)
        expected = 1.0 - (1.0 - 0.15 / 2) * (1.0 - 0.15 / 1)
        assert result == pytest.approx(expected, rel=0.01)


class TestInheritedPartDefectChance:
    """Tests for inherited_part_defect_chance function."""

    def test_no_defects(self):
        a = make_cat(1)
        b = make_cat(2)
        assert inherited_part_defect_chance(a, b, 0.0) == 0.0

    def test_one_parent_has_defect(self):
        a = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=700,
                mouth=0,
            ),
        )
        b = make_cat(2)
        result = inherited_part_defect_chance(a, b, 0.0)
        assert result == pytest.approx(0.4)


class TestMutationFavoring:
    """Tests for mutation favoring fix in body part inheritance."""

    def test_mom_has_mutation_slot_dad_not(self):
        mother = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=300,
                mouth=0,
            ),
        )
        father = make_cat(
            2,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=0,
                mouth=0,
            ),
        )
        trait = TraitRequirement(trait=create_trait(TraitCategory.BODY_PART, "Ears300"))

        result = calculate_trait_probability(trait, mother, father, 0.0)

        assert result.probability == pytest.approx(0.4)

    def test_both_parents_different_mutations_same_slot(self):
        mother = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=300,
                mouth=0,
            ),
        )
        father = make_cat(
            2,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=320,
                mouth=0,
            ),
        )
        trait = TraitRequirement(trait=create_trait(TraitCategory.BODY_PART, "Ears300"))

        result = calculate_trait_probability(trait, mother, father, 0.0)

        assert result.probability == pytest.approx(0.4)

    def test_mutation_favoring_at_high_stimulation(self):
        mother = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=300,
                mouth=0,
            ),
        )
        father = make_cat(
            2,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=0,
                mouth=0,
            ),
        )
        trait = TraitRequirement(trait=create_trait(TraitCategory.BODY_PART, "Ears300"))

        result = calculate_trait_probability(trait, mother, father, 50.0)

        assert result.probability == pytest.approx(0.48)


class TestDisorderTraitProbability:
    """Tests for disorder trait inheritance probability."""

    def test_disorder_neither_parent_has(self):
        mother = make_cat(1, disorders=[])
        father = make_cat(2, disorders=[])
        trait = TraitRequirement(trait=create_trait(TraitCategory.DISORDER, "Blind"))

        result = calculate_trait_probability(trait, mother, father)

        assert result.probability == 0.0

    def test_disorder_one_parent_has(self):
        mother = make_cat(1, disorders=["Blind"])
        father = make_cat(2, disorders=[])
        trait = TraitRequirement(trait=create_trait(TraitCategory.DISORDER, "Blind"))

        result = calculate_trait_probability(trait, mother, father)

        assert result.probability == pytest.approx(0.15)

    def test_disorder_pool_dilution(self):
        mother = make_cat(1, disorders=["Blind", "Lame", "Deaf"])
        father = make_cat(2, disorders=[])
        trait = TraitRequirement(trait=create_trait(TraitCategory.DISORDER, "Blind"))

        result = calculate_trait_probability(trait, mother, father)

        assert result.probability == pytest.approx(0.05)


class TestBodyPartTraitHelpers:
    """Tests for BodyPartTrait helper functions."""

    def test_get_slot(self):
        trait = BodyPartTrait(_key="Ears300")
        assert trait.get_slot() == "ears"

    def test_get_part_id(self):
        trait = BodyPartTrait(_key="Ears300")
        assert trait.get_part_id() == 300

    def test_cat_has_mutation_in_slot_true(self):
        cat = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=300,
                mouth=0,
            ),
        )
        assert cat_has_mutation_in_slot(cat, "ears") is True

    def test_cat_has_mutation_in_slot_true_for_defect(self):
        # Birth defects (700+) ARE mutations per the game
        cat = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=700,
                mouth=0,
            ),
        )
        assert cat_has_mutation_in_slot(cat, "ears") is True

    def test_cat_has_defect_in_slot_true(self):
        cat = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=700,
                mouth=0,
            ),
        )
        assert cat_has_defect_in_slot(cat, "ears") is True

    def test_cat_has_defect_in_slot_false_for_mutation(self):
        cat = make_cat(
            1,
            body_parts=CatBodyParts(
                texture=0,
                body=0,
                head=0,
                tail=0,
                legs=0,
                arms=0,
                eyes=0,
                eyebrows=0,
                ears=300,
                mouth=0,
            ),
        )
        assert cat_has_defect_in_slot(cat, "ears") is False
