"""Tests for mewgenics_scorer ancestry module."""

import pytest
from unittest.mock import MagicMock

from mewgenics_scorer.ancestry import (
    _ancestor_contributions,
    build_ancestor_contribs,
    coi_from_contribs,
    risk_percent,
)


def make_mock_cat(db_key: int, generation: int = 0, parent_a=None, parent_b=None):
    cat = MagicMock()
    cat.db_key = db_key
    cat.generation = generation
    cat.parent_a = parent_a
    cat.parent_b = parent_b
    return cat


class TestAncestorContributions:
    """Tests for _ancestor_contributions function."""

    def test_no_parents(self):
        cat = make_mock_cat(1)
        result = _ancestor_contributions(cat)
        assert id(cat) in result
        assert result[id(cat)][1] == 1.0

    def test_single_parent(self):
        parent = make_mock_cat(1)
        cat = make_mock_cat(2, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert id(parent) in result
        assert result[id(parent)][1] == 0.5

    def test_two_parents(self):
        parent_a = make_mock_cat(1)
        parent_b = make_mock_cat(2)
        cat = make_mock_cat(3, parent_a=parent_a, parent_b=parent_b)
        result = _ancestor_contributions(cat)
        assert id(parent_a) in result
        assert id(parent_b) in result
        assert result[id(parent_a)][1] == 0.5
        assert result[id(parent_b)][1] == 0.5

    def test_grandparent_contribution(self):
        gp = make_mock_cat(1)
        parent = make_mock_cat(2, parent_a=gp)
        cat = make_mock_cat(3, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert id(gp) in result
        assert result[id(gp)][1] == 0.25

    def test_none_returns_empty(self):
        result = _ancestor_contributions(None)
        assert result == {}


class TestBuildAncestorContribs:
    """Tests for build_ancestor_contribs function."""

    def test_single_cat(self):
        cat = make_mock_cat(1)
        result = build_ancestor_contribs([cat])
        assert 1 in result

    def test_siblings_share_parents(self):
        parent_a = make_mock_cat(1)
        parent_b = make_mock_cat(2)
        cat1 = make_mock_cat(3, parent_a=parent_a, parent_b=parent_b)
        cat2 = make_mock_cat(4, parent_a=parent_a, parent_b=parent_b)
        result = build_ancestor_contribs([cat1, cat2])
        assert 3 in result
        assert 4 in result
        assert id(parent_a) in result[3]
        assert id(parent_a) in result[4]


class TestCoiFromContribs:
    """Tests for coi_from_contribs function."""

    def test_no_common_ancestors(self):
        ca = {id(make_mock_cat(1)): 0.5}
        cb = {id(make_mock_cat(2)): 0.5}
        result = coi_from_contribs(ca, cb)
        assert result == 0.0

    def test_common_ancestor_full_sibling(self):
        parent = make_mock_cat(1)
        ca = {id(parent): 0.5}
        cb = {id(parent): 0.5}
        result = coi_from_contribs(ca, cb)
        assert result == 0.125  # 0.5 * 0.5 * 0.5

    def test_empty_dicts(self):
        result = coi_from_contribs({}, {})
        assert result == 0.0

    def test_one_empty_dict(self):
        cat = make_mock_cat(1)
        result = coi_from_contribs({id(cat): 0.5}, {})
        assert result == 0.0


class TestRiskPercent:
    """Tests for risk_percent function."""

    def test_zero_coi(self):
        assert risk_percent(0.0) == 0.0

    def test_full_coi(self):
        assert risk_percent(0.25) == 100.0

    def test_half_coi(self):
        assert risk_percent(0.125) == 50.0

    def test_clamps_above_100(self):
        assert risk_percent(1.0) == 100.0

    def test_negative_clamps_to_zero(self):
        assert risk_percent(-0.1) == 0.0
