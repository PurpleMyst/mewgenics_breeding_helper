"""Tests for mewgenics_scorer compatibility module."""

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender, CatStatus, CatBodyParts, Stats
from mewgenics_scorer.compatibility import (
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
    is_mutual_lovers,
)


def make_cat(
    db_key: int, gender: CatGender = CatGender.MALE, lover_id=None, hater_id=None
):
    return Cat(
        db_key=db_key,
        name=f"Cat_{db_key}",
        name_tag="",
        gender=gender,
        status=CatStatus.IN_HOUSE,
        room=None,
        stat_base=Stats(5, 5, 5, 5, 5, 5, 5),
        stat_total=Stats(5, 5, 5, 5, 5, 5, 5),
        age=0,
        aggression=0.5,
        libido=0.5,
        sexuality=None,
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
        parent_a=None,
        parent_b=None,
        lover_id=lover_id,
        hater_id=hater_id,
        lover=None,
        hater=None,
    )


class TestCanBreed:
    """Tests for can_breed function."""

    def test_male_female_can_breed(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        assert can_breed(a, b) is True

    def test_female_male_can_breed(self):
        a = make_cat(1, CatGender.FEMALE)
        b = make_cat(2, CatGender.MALE)
        assert can_breed(a, b) is True

    def test_male_male_cannot_breed(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.MALE)
        assert can_breed(a, b) is False

    def test_female_female_cannot_breed(self):
        a = make_cat(1, CatGender.FEMALE)
        b = make_cat(2, CatGender.FEMALE)
        assert can_breed(a, b) is False

    def test_unknown_gender_can_breed_with_any(self):
        a = make_cat(1, CatGender.DITTO)
        b = make_cat(2, CatGender.MALE)
        assert can_breed(a, b) is True
        assert can_breed(b, a) is True

    def test_unknown_gender_can_breed_with_unknown(self):
        a = make_cat(1, CatGender.DITTO)
        b = make_cat(2, CatGender.DITTO)
        assert can_breed(a, b) is True


class TestIsHaterConflict:
    """Tests for is_hater_conflict function."""

    def test_no_haters(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        assert is_hater_conflict(a, b) is False

    def test_a_hates_b(self):
        b = make_cat(2, CatGender.FEMALE)
        a = make_cat(1, CatGender.MALE, hater_id=2)
        assert is_hater_conflict(a, b) is True

    def test_b_hates_a(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE, hater_id=1)
        assert is_hater_conflict(a, b) is True

    def test_mutual_hate(self):
        a = make_cat(1, CatGender.MALE, hater_id=2)
        b = make_cat(2, CatGender.FEMALE, hater_id=1)
        assert is_hater_conflict(a, b) is True


class TestIsLoverConflict:
    """Tests for is_lover_conflict function."""

    def test_avoid_lovers_disabled(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE, lover_id=1)
        assert is_lover_conflict(a, b, avoid_lovers=False) is False

    def test_avoid_lovers_enabled_no_relationship(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        assert is_lover_conflict(a, b, avoid_lovers=True) is False

    def test_avoid_lovers_enabled_one_sided_lover(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE, lover_id=1)
        assert is_lover_conflict(a, b, avoid_lovers=True) is False

    def test_avoid_lovers_enabled_mutual_lovers(self):
        a = make_cat(1, CatGender.MALE, lover_id=2)
        b = make_cat(2, CatGender.FEMALE, lover_id=1)
        assert is_lover_conflict(a, b, avoid_lovers=True) is False

    def test_avoid_lovers_enabled_one_cheating(self):
        # When a has a lover c, but tries to breed with b (who is not that lover), it's a conflict
        a = make_cat(1, CatGender.MALE, lover_id=3)
        b = make_cat(2, CatGender.FEMALE)
        # a has lover c, but b is not c - this is a conflict
        assert is_lover_conflict(a, b, avoid_lovers=True) is True


class TestIsMutualLovers:
    """Tests for is_mutual_lovers function."""

    def test_no_lovers(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        assert is_mutual_lovers(a, b) is False

    def test_one_sided_lover(self):
        b = make_cat(2, CatGender.FEMALE, lover_id=1)
        a = make_cat(1, CatGender.MALE)
        assert is_mutual_lovers(a, b) is False

    def test_mutual_lovers(self):
        a = make_cat(1, CatGender.MALE, lover_id=2)
        b = make_cat(2, CatGender.FEMALE, lover_id=1)
        assert is_mutual_lovers(a, b) is True
