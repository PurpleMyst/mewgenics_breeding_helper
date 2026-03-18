"""Tests for mewgenics_scorer ancestry module."""

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender, CatStatus, CatBodyParts, Stats
from mewgenics_scorer.ancestry import (
    _ancestor_contributions,
    build_ancestor_contribs,
    coi_from_contribs,
    AncestorData,
)


def make_cat(
    db_key: int,
    parent_a: Cat | None = None,
    parent_b: Cat | None = None,
    coi: float = 0.0,
) -> Cat:
    return Cat(
        db_key=db_key,
        name=f"Cat_{db_key}",
        gender=CatGender.MALE,
        status=CatStatus.IN_HOUSE,
        room=None,
        stat_base=Stats(5, 5, 5, 5, 5, 5, 5),
        stat_total=Stats(5, 5, 5, 5, 5, 5, 5),
        age=0,
        aggression=0.5,
        libido=0.5,
        coi=coi,
        active_abilities=[],
        passive_abilities=[],
        disorders=[],
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
        parent_a=parent_a,
        parent_b=parent_b,
        lovers=[],
        haters=[],
    )


class TestAncestorContributions:
    """Tests for _ancestor_contributions function."""

    def test_no_parents(self):
        cat = make_cat(1)
        result = _ancestor_contributions(cat)
        assert cat.db_key in result
        assert result[cat.db_key].prob == 1.0

    def test_single_parent(self):
        parent = make_cat(1)
        cat = make_cat(2, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert parent.db_key in result
        assert result[parent.db_key].prob == 0.5

    def test_two_parents(self):
        parent_a = make_cat(1)
        parent_b = make_cat(2)
        cat = make_cat(3, parent_a=parent_a, parent_b=parent_b)
        result = _ancestor_contributions(cat)
        assert parent_a.db_key in result
        assert parent_b.db_key in result
        assert result[parent_a.db_key].prob == 0.5
        assert result[parent_b.db_key].prob == 0.5

    def test_grandparent_contribution(self):
        gp = make_cat(1)
        parent = make_cat(2, parent_a=gp)
        cat = make_cat(3, parent_a=parent)
        result = _ancestor_contributions(cat)
        assert gp.db_key in result
        assert result[gp.db_key].prob == 0.25

    def test_none_returns_empty(self):
        result = _ancestor_contributions(None)
        assert result == {}


class TestCoiFromContribs:
    """Tests for coi_from_contribs function."""

    def test_no_common_ancestors(self):
        cat_1 = make_cat(1)
        cat_2 = make_cat(2)
        ca = {cat_1.db_key: AncestorData(cat_1, 0.5, 1)}
        cb = {cat_2.db_key: AncestorData(cat_2, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        assert result == 0.0

    def test_common_ancestor_full_sibling(self):
        parent = make_cat(1)
        ca = {parent.db_key: AncestorData(parent, 0.5, 1)}
        cb = {parent.db_key: AncestorData(parent, 0.5, 1)}
        result = coi_from_contribs(ca, cb)
        assert result == 0.125

    def test_empty_dicts(self):
        result = coi_from_contribs({}, {})
        assert result == 0.0

    def test_one_empty_dict(self):
        cat = make_cat(1)
        result = coi_from_contribs({cat.db_key: AncestorData(cat, 0.5, 1)}, {})
        assert result == 0.0


class TestBuildAncestorContribs:
    """Tests for build_ancestor_contribs function."""

    def test_single_cat(self):
        cat = make_cat(1)
        result = build_ancestor_contribs([cat])
        assert 1 in result

    def test_siblings_share_parents(self):
        parent_a = make_cat(1)
        parent_b = make_cat(2)
        cat1 = make_cat(3, parent_a=parent_a, parent_b=parent_b)
        cat2 = make_cat(4, parent_a=parent_a, parent_b=parent_b)
        result = build_ancestor_contribs([cat1, cat2])
        assert 3 in result
        assert 4 in result
        assert parent_a.db_key in result[3]
        assert parent_a.db_key in result[4]
