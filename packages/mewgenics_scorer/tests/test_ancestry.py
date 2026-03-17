"""Tests for mewgenics_scorer ancestry module."""

from unittest.mock import MagicMock


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
        assert cat.db_key in result
        assert result[cat.db_key].prob == 1.0

    def test_single_parent(self):
        parent = make_mock_cat(1)
        cat = make_mock_cat(2, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert parent.db_key in result
        assert result[parent.db_key].prob == 0.5

    def test_two_parents(self):
        parent_a = make_mock_cat(1)
        parent_b = make_mock_cat(2)
        cat = make_mock_cat(3, parent_a=parent_a, parent_b=parent_b)
        result = _ancestor_contributions(cat)
        assert parent_a.db_key in result
        assert parent_b.db_key in result
        assert result[parent_a.db_key].prob == 0.5
        assert result[parent_b.db_key].prob == 0.5

    def test_grandparent_contribution(self):
        gp = make_mock_cat(1)
        parent = make_mock_cat(2, parent_a=gp)
        cat = make_mock_cat(3, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert gp.db_key in result
        assert result[gp.db_key].prob == 0.25

    def test_none_returns_empty(self):
        result = _ancestor_contributions(None)
        assert result == {}


class TestCoiFromContribs:
    """Tests for coi_from_contribs function."""

    def test_no_common_ancestors(self):
        cat_1 = make_mock_cat(1)
        cat_2 = make_mock_cat(2)
        ca = {cat_1.db_key: AncestorData(cat_1, 0.5, 1)}
        cb = {cat_2.db_key: AncestorData(cat_2, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        assert result == 0.0

    def test_common_ancestor_full_sibling(self):
        parent = make_mock_cat(1)
        ca = {parent.db_key: AncestorData(parent, 0.5, 1)}
        cb = {parent.db_key: AncestorData(parent, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        assert result == 0.125

    def test_empty_dicts(self):
        result = coi_from_contribs({}, {})
        assert result == 0.0

    def test_one_empty_dict(self):
        cat = make_mock_cat(1)
        result = coi_from_contribs({cat.db_key: AncestorData(cat, 0.5, 1)}, {})
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
        assert parent_a.db_key in result[3]
        assert parent_a.db_key in result[4]
