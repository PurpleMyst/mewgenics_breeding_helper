"""Tests for mewgenics_scorer factors module."""

from unittest.mock import MagicMock

import pytest

from mewgenics_scorer.factors import (
    DEFAULT_STIMULATION,
    PairFactors,
    _better_chance,
    _default_01,
    _spell_inheritance_chance,
    _passive_inheritance_chance,
    _class_favoring_chance,
    aggression_factor,
    calculate_pair_factors,
    calculate_trait_probability,
    expected_stats,
    libido_factor,
    stat_variance,
    trait_coverage,
)
from mewgenics_scorer.types import TraitRequirement


def make_mock_cat(
    db_key: int,
    gender: str = "male",
    stat_base: list[int] | None = None,
    aggression: float | None = None,
    libido: float | None = None,
    passives: list | None = None,
    abilities: list | None = None,
    disorders: list | None = None,
    lovers=None,
    haters=None,
    parent_a=None,
    parent_b=None,
):
    cat = MagicMock()
    cat.db_key = db_key
    cat.gender = gender
    cat.stat_base = stat_base or [5, 5, 5, 5, 5, 5, 5]
    cat.aggression = aggression
    cat.libido = libido
    cat.passive_abilities = passives or []
    cat.active_abilities = abilities or []
    cat.disorders = disorders or []
    cat.lovers = lovers or []
    cat.haters = haters or []
    cat.parent_a = parent_a
    cat.parent_b = parent_b

    # Add inheritable_ properties (normalized, lowercase, SkillShare excluded)
    from mewgenics_parser.trait_dictionary import (
        normalize_trait_name,
        SKILLSHARE_BASE_ID,
    )

    cat.inheritable_abilities = [
        normalize_trait_name(a) for a in (abilities or [])
    ]

    cat.inheritable_passives = [
        normalize_trait_name(p)
        for p in (passives or [])
        if normalize_trait_name(p) != SKILLSHARE_BASE_ID
    ]

    return cat


class TestBetterChance:
    """Tests for _better_chance function."""

    def test_default_stimulation(self):
        chance = _better_chance(DEFAULT_STIMULATION)
        expected = (1.0 + 0.01 * 50) / (2.0 + 0.01 * 50)
        assert abs(chance - expected) < 0.0001

    def test_zero_stimulation(self):
        chance = _better_chance(0.0)
        assert chance == 0.5

    def test_high_stimulation(self):
        chance = _better_chance(100.0)
        assert chance > 0.5


class TestDefault01:
    """Tests for _default_01 function."""

    def test_value_in_range(self):
        assert _default_01(0.5) == 0.5

    def test_none_returns_half(self):
        assert _default_01(None) == 0.5

    def test_clamps_above_one(self):
        assert _default_01(1.5) == 1.0

    def test_clamps_below_zero(self):
        assert _default_01(-0.5) == 0.0


class TestExpectedStats:
    """Tests for expected_stats function."""

    def test_identical_stats(self):
        a = make_mock_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_mock_cat(2, stat_base=[5, 5, 5, 5, 5, 5, 5])
        result = expected_stats(a, b, 50.0)
        assert all(s == 5.0 for s in result)

    def test_different_stats(self):
        a = make_mock_cat(1, stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_mock_cat(2, stat_base=[0, 10, 0, 0, 0, 0, 0])
        result = expected_stats(a, b, 50.0)
        # First stat: max(10,0)*chance + min(10,0)*(1-chance) = 10*chance
        # Second stat: max(0,10)*chance + min(0,10)*(1-chance) = 10*chance
        chance = _better_chance(50.0)
        assert abs(result[0] - 10 * chance) < 0.0001
        assert abs(result[1] - 10 * chance) < 0.0001


class TestStatVariance:
    """Tests for stat_variance function."""

    def test_identical_stats(self):
        a = make_mock_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_mock_cat(2, stat_base=[5, 5, 5, 5, 5, 5, 5])
        assert stat_variance(a, b) == 0.0

    def test_all_different(self):
        a = make_mock_cat(1, stat_base=[10, 10, 10, 10, 10, 10, 10])
        b = make_mock_cat(2, stat_base=[0, 0, 0, 0, 0, 0, 0])
        assert stat_variance(a, b) == 70.0  # 7 * 10


class TestAggressionFactor:
    """Tests for aggression_factor function."""

    def test_both_low_aggression(self):
        a = make_mock_cat(1, aggression=0.1)
        b = make_mock_cat(2, aggression=0.1)
        result = aggression_factor(a, b)
        assert result > 0.8  # High factor for low aggression

    def test_both_high_aggression(self):
        a = make_mock_cat(1, aggression=0.9)
        b = make_mock_cat(2, aggression=0.9)
        result = aggression_factor(a, b)
        assert result < 0.2  # Low factor for high aggression

    def test_unknown_aggression_defaults(self):
        a = make_mock_cat(1, aggression=None)
        b = make_mock_cat(2, aggression=None)
        assert aggression_factor(a, b) == 0.5


class TestLibidoFactor:
    """Tests for libido_factor function."""

    def test_both_low_libido(self):
        a = make_mock_cat(1, libido=0.1)
        b = make_mock_cat(2, libido=0.1)
        result = libido_factor(a, b)
        assert result < 0.2

    def test_both_high_libido(self):
        a = make_mock_cat(1, libido=0.9)
        b = make_mock_cat(2, libido=0.9)
        result = libido_factor(a, b)
        assert result > 0.8

    def test_unknown_libido_defaults(self):
        a = make_mock_cat(1, libido=None)
        b = make_mock_cat(2, libido=None)
        assert libido_factor(a, b) == 0.5


class TestTraitCoverage:
    """Tests for trait_coverage function."""

    def test_a_has_trait(self):
        a = make_mock_cat(1, passives=["Host"])
        b = make_mock_cat(2)
        traits = [TraitRequirement("passive", "Host")]
        result = trait_coverage(a, b, traits)
        # Check the key of the returned TraitRequirement
        assert len(result) == 1
        assert result[0].key == "Host"

    def test_b_has_trait(self):
        a = make_mock_cat(1)
        b = make_mock_cat(2, passives=["Host"])
        traits = [TraitRequirement("passive", "Host")]
        result = trait_coverage(a, b, traits)
        assert len(result) == 1
        assert result[0].key == "Host"

    def test_neither_has_trait(self):
        a = make_mock_cat(1)
        b = make_mock_cat(2)
        traits = [TraitRequirement("passive", "Host")]
        result = trait_coverage(a, b, traits)
        assert len(result) == 0

    def test_passive_ability(self):
        a = make_mock_cat(1, passives=["Sturdy"])
        b = make_mock_cat(2)
        traits = [TraitRequirement("passive", "Sturdy")]
        result = trait_coverage(a, b, traits)
        assert len(result) == 1
        assert result[0].key == "Sturdy"


class TestCalculatePairFactors:
    """Tests for calculate_pair_factors function."""

    def test_basic_calculation(self):
        a = make_mock_cat(1, gender="male", stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_mock_cat(2, gender="female", stat_base=[5, 5, 5, 5, 5, 5, 5])
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        assert isinstance(result, PairFactors)
        assert result.can_breed is True
        assert result.hater_conflict is False
        assert result.lover_conflict is False
        assert result.mutual_lovers is False

    def test_unrelated_cats_no_risk(self):
        a = make_mock_cat(1, gender="male")
        b = make_mock_cat(2, gender="female")
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        # Unrelated cats have CoI = 0.0, so:
        # - disorder chance = 2% (base)
        # - part defect chance = 0% (CoI <= 0.05)
        assert result.expected_disorder_chance == 0.02
        assert result.expected_part_defect_chance == 0.0

    def test_total_expected_stats(self):
        a = make_mock_cat(1, gender="male", stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_mock_cat(2, gender="female", stat_base=[0, 10, 0, 0, 0, 0, 0])
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
        mother = make_mock_cat(1, abilities=[])
        father = make_mock_cat(2, abilities=[])
        trait = TraitRequirement("ability", "PathOfTheHunter")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        assert result.probability == 0.0
        assert result.parent_source in ("none", "neither")

    def test_ability_single_parent_has(self):
        mother = make_mock_cat(1, abilities=["PathOfTheHunter"])
        father = make_mock_cat(2, abilities=[])
        trait = TraitRequirement("ability", "PathOfTheHunter")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # At 0 stim: 50% parent pick * 20% inherit chance * 100% pool = 10%
        # Parent selection is decoupled from trait possession
        assert result.probability == pytest.approx(0.1)

    def test_ability_pool_dilution(self):
        # Mother has 4 spells, father has 1
        mother = make_mock_cat(1, abilities=["A", "B", "C", "PathOfTheHunter"])
        father = make_mock_cat(2, abilities=["Zap"])
        trait = TraitRequirement("ability", "PathOfTheHunter")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # 50% parent pick * 20% inherit chance * (1/4 pool size) = 2.5%
        # Parent selection is decoupled from trait possession
        assert result.probability == pytest.approx(0.025)

    def test_passive_skillshare_plus_guaranteed(self):
        mother = make_mock_cat(1, passives=["SkillShare2", "Sturdy"])
        father = make_mock_cat(2, passives=[])
        trait = TraitRequirement("passive", "Sturdy")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # SkillShare+ guarantees other passives
        assert result.probability == 1.0
        assert "SkillShare+" in result.parent_source

    def test_passive_disorder_not_in_passive_pool(self):
        # Disorders should NOT be in passive_abilities (separated at parse time)
        mother = make_mock_cat(1, passives=["Sturdy"], disorders=["Blind"])
        father = make_mock_cat(2, passives=[])
        trait = TraitRequirement("passive", "Blind")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # blind is a disorder, not a passive - should not inherit via passive mechanics
        assert result.probability == 0.0

    # def test_mutation_inheritance_80_percent(self):
    #     mother = make_mock_cat(1, mutations=["Frostbit"])
    #     father = make_mock_cat(2, mutations=[])
    #     trait = TraitRequirement("mutation", "Frostbit")
    #
    #     result = calculate_trait_probability(trait, mother, father, 0.0)
    #
    #     # 80% inherit parts * 50% favor for mother (when only she has it at 0 stim)
    #     # = 0.8 * 0.5 = 0.4
    #     assert result.probability == pytest.approx(0.4)
    #
    # def test_mutation_favoring_with_stimulation(self):
    #     mother = make_mock_cat(1, mutations=["Frostbit"])
    #     father = make_mock_cat(2, mutations=[])
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
        mother = make_mock_cat(1, passives=["SkillShare", "Sturdy"])
        father = make_mock_cat(2, passives=[])
        trait = TraitRequirement("passive", "SkillShare")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Base skillshare is excluded from inheritable pool
        assert result.probability == 0.0

    def test_passive_upgraded_ability_normalized(self):
        """Querying for base passive matches parent's upgraded variant."""
        mother = make_mock_cat(1, passives=["Sturdy2"])
        father = make_mock_cat(2, passives=[])
        trait = TraitRequirement("passive", "Sturdy")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Should match because normalized = "sturdy"
        assert result.probability > 0.0

    def test_ability_upgraded_ability_normalized(self):
        """Querying for base ability matches parent's upgraded variant."""
        mother = make_mock_cat(1, abilities=["PathOfTheHunter2"])
        father = make_mock_cat(2, abilities=[])
        trait = TraitRequirement("ability", "PathOfTheHunter")

        result = calculate_trait_probability(trait, mother, father, 0.0)

        # Should match because normalized = "paththehunter"
        assert result.probability > 0.0


class TestClassFavoringAlgebra:
    """Tests verifying the corrected class-favoring math."""

    def test_class_favoring_100_percent(self):
        # At 100 stim, favor_chance = 1.0
        # mother_select should be 0.5 + 0.5*1.0 = 1.0
        mother = make_mock_cat(1, abilities=["PathOfTheHunter"])  # class spell
        father = make_mock_cat(2, abilities=["Swat"])  # generic spell
        trait = TraitRequirement("ability", "PathOfTheHunter")

        result = calculate_trait_probability(trait, mother, father, 100.0)

        # With 100% favor chance, should strongly favor mother (class spell holder)
        # At 100 stim, inherit chance is capped at 1.0
        assert result.parent_favor_chance == 1.0
