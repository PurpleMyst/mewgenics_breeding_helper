"""Tests for mewgenics_scorer compatibility module."""

import pytest
from unittest.mock import MagicMock

from mewgenics_scorer.compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)


def make_mock_cat(db_key: int, gender: str = "male", lovers=None, haters=None):
    cat = MagicMock()
    cat.db_key = db_key
    cat.gender = gender
    cat.lovers = lovers or []
    cat.haters = haters or []
    return cat


class TestCanBreed:
    """Tests for can_breed function."""

    def test_male_female_can_breed(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female")
        assert can_breed(a, b) is True

    def test_female_male_can_breed(self):
        a = make_mock_cat(1, "female")
        b = make_mock_cat(2, "male")
        assert can_breed(a, b) is True

    def test_male_male_cannot_breed(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "male")
        assert can_breed(a, b) is False

    def test_female_female_cannot_breed(self):
        a = make_mock_cat(1, "female")
        b = make_mock_cat(2, "female")
        assert can_breed(a, b) is False

    def test_unknown_gender_can_breed_with_any(self):
        a = make_mock_cat(1, "?")
        b = make_mock_cat(2, "male")
        assert can_breed(a, b) is True
        assert can_breed(b, a) is True

    def test_unknown_gender_can_breed_with_unknown(self):
        a = make_mock_cat(1, "?")
        b = make_mock_cat(2, "?")
        assert can_breed(a, b) is True


class TestIsHaterConflict:
    """Tests for is_hater_conflict function."""

    def test_no_haters(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female")
        assert is_hater_conflict(a, b) is False

    def test_a_hates_b(self):
        b = make_mock_cat(2, "female")
        a = make_mock_cat(1, "male", haters=[b])
        assert is_hater_conflict(a, b) is True

    def test_b_hates_a(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female", haters=[a])
        assert is_hater_conflict(a, b) is True

    def test_mutual_hate(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female", haters=[a])
        a.haters = [b]
        assert is_hater_conflict(a, b) is True


class TestIsLoverConflict:
    """Tests for is_lover_conflict function."""

    def test_no_lovers_no_conflict(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female")
        assert is_lover_conflict(a, b, avoid_lovers=True) is False

    def test_avoid_lovers_disabled(self):
        b = make_mock_cat(2, "female", lovers=[make_mock_cat(3, "male")])
        a = make_mock_cat(1, "male")
        assert is_lover_conflict(a, b, avoid_lovers=False) is False

    def test_a_has_lover_b_not_lover(self):
        lover = make_mock_cat(3, "female")
        a = make_mock_cat(1, "male", lovers=[lover])
        b = make_mock_cat(2, "female")
        assert is_lover_conflict(a, b, avoid_lovers=True) is True

    def test_b_has_lover_a_not_lover(self):
        lover = make_mock_cat(3, "male")
        b = make_mock_cat(2, "female", lovers=[lover])
        a = make_mock_cat(1, "male")
        assert is_lover_conflict(a, b, avoid_lovers=True) is True


class TestIsMutualLovers:
    """Tests for is_mutual_lovers function."""

    def test_no_lovers(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female")
        assert is_mutual_lovers(a, b) is False

    def test_one_sided_love(self):
        b = make_mock_cat(2, "female")
        a = make_mock_cat(1, "male", lovers=[b])
        assert is_mutual_lovers(a, b) is False

    def test_mutual_lovers(self):
        a = make_mock_cat(1, "male")
        b = make_mock_cat(2, "female", lovers=[a])
        a.lovers = [b]
        assert is_mutual_lovers(a, b) is True
