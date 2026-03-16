"""Tests for mewgenics_scorer factors module."""

import pytest
from unittest.mock import MagicMock

from mewgenics_scorer.factors import (
    _better_chance,
    _default_01,
    expected_stats,
    stat_variance,
    aggression_factor,
    libido_factor,
    trait_coverage,
    calculate_pair_factors,
    PairFactors,
    DEFAULT_STIMULATION,
)
from mewgenics_scorer.types import TraitRequirement


def make_mock_cat(
    db_key: int,
    gender: str = "male",
    stat_base: list[int] = None,
    aggression: float | None = None,
    libido: float | None = None,
    mutations: list = None,
    passive_abilities: list = None,
    abilities: list = None,
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
    cat.mutations = mutations or []
    cat.passive_abilities = passive_abilities or []
    cat.abilities = abilities or []
    cat.lovers = lovers or []
    cat.haters = haters or []
    cat.parent_a = parent_a
    cat.parent_b = parent_b
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
        a = make_mock_cat(1, mutations=["Frostbit"])
        b = make_mock_cat(2)
        traits = [TraitRequirement("mutation", "Frostbit")]
        result = trait_coverage(a, b, traits)
        assert "Frostbit" in result

    def test_b_has_trait(self):
        a = make_mock_cat(1)
        b = make_mock_cat(2, mutations=["Frostbit"])
        traits = [TraitRequirement("mutation", "Frostbit")]
        result = trait_coverage(a, b, traits)
        assert "Frostbit" in result

    def test_neither_has_trait(self):
        a = make_mock_cat(1)
        b = make_mock_cat(2)
        traits = [TraitRequirement("mutation", "Frostbit")]
        result = trait_coverage(a, b, traits)
        assert len(result) == 0

    def test_passive_ability(self):
        a = make_mock_cat(1, passive_abilities=["Sturdy"])
        b = make_mock_cat(2)
        traits = [TraitRequirement("passive", "Sturdy")]
        result = trait_coverage(a, b, traits)
        assert "Sturdy" in result


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

        assert result.risk_percent == 0.0

    def test_total_expected_stats(self):
        a = make_mock_cat(1, gender="male", stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_mock_cat(2, gender="female", stat_base=[0, 10, 0, 0, 0, 0, 0])
        contribs = {1: {}, 2: {}}

        result = calculate_pair_factors(a, b, contribs)

        # Should be 7 values that sum to something based on better_chance
        assert len(result.expected_stats) == 7
        assert result.total_expected_stats == sum(result.expected_stats)
