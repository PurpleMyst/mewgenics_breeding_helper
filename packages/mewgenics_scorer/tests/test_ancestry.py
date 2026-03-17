"""Tests for mewgenics_scorer ancestry module."""

from unittest.mock import MagicMock

import pytest

from mewgenics_scorer.ancestry import (
    _ancestor_contributions,
    build_ancestor_contribs,
    coi_from_contribs,
    AncestorData,
)


def make_mock_cat(
    db_key: int, generation: int = 0, parent_a=None, parent_b=None, coi=0.0
):
    cat = MagicMock()
    cat.db_key = db_key
    cat.generation = generation
    cat.parent_a = parent_a
    cat.parent_b = parent_b
    cat.coi = coi
    return cat


class TestAncestorContributions:
    """Tests for _ancestor_contributions function."""

    def test_no_parents(self):
        cat = make_mock_cat(1)
        result = _ancestor_contributions(cat)
        assert id(cat) in result
        assert result[id(cat)].prob == 1.0  # Changed from [1] to .prob

    def test_single_parent(self):
        parent = make_mock_cat(1)
        cat = make_mock_cat(2, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert id(parent) in result
        assert result[id(parent)].prob == 0.5

    def test_two_parents(self):
        parent_a = make_mock_cat(1)
        parent_b = make_mock_cat(2)
        cat = make_mock_cat(3, parent_a=parent_a, parent_b=parent_b)
        result = _ancestor_contributions(cat)
        assert id(parent_a) in result
        assert id(parent_b) in result
        assert result[id(parent_a)].prob == 0.5
        assert result[id(parent_b)].prob == 0.5

    def test_grandparent_contribution(self):
        gp = make_mock_cat(1)
        parent = make_mock_cat(2, parent_a=gp)
        cat = make_mock_cat(3, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert id(gp) in result
        assert result[id(gp)].prob == 0.25

    def test_none_returns_empty(self):
        result = _ancestor_contributions(None)
        assert result == {}


class TestCoiFromContribs:
    """Tests for coi_from_contribs function."""

    def test_no_common_ancestors(self):
        cat_1 = make_mock_cat(1)
        cat_2 = make_mock_cat(2)
        # Wrap mock data in AncestorData
        ca = {id(cat_1): AncestorData(cat_1, 0.5, 1)}
        cb = {id(cat_2): AncestorData(cat_2, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        assert result == 0.0

    def test_common_ancestor_full_sibling(self):
        parent = make_mock_cat(1)
        # Wrap mock data in AncestorData
        ca = {id(parent): AncestorData(parent, 0.5, 1)}
        cb = {id(parent): AncestorData(parent, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        # With the new formula: 0.5 * (0.5 * 0.5) * (1 + 0.0) = 0.125
        assert result == 0.125

    def test_empty_dicts(self):
        result = coi_from_contribs({}, {})
        assert result == 0.0

    def test_one_empty_dict(self):
        cat = make_mock_cat(1)
        # Wrap mock data in AncestorData
        result = coi_from_contribs({id(cat): AncestorData(cat, 0.5, 1)}, {})
        assert result == 0.0


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
