"""Tests for cat breeding eligibility methods."""

import pytest
from mewgenics_parser.cat import Cat, CatBodySlot, CatGender, CatStatus, Stats


def make_cat(
    db_key: int,
    age: int | None = 14,
    eternal_youth: bool = False,
) -> Cat:
    disorders: list[str] = []
    if eternal_youth:
        disorders.append("eternalyouth")
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        gender=CatGender.MALE,
        status=CatStatus.IN_HOUSE,
        room="Floor1_Large",
        base_stats=Stats(7, 7, 7, 7, 7, 7, 7),
        total_stats=Stats(7, 7, 7, 7, 7, 7, 7),
        age=age,
        aggression=0.5,
        libido=0.5,
        fertility=1.0,
        sexuality=0.0,
        active_abilities=["DefaultMove", "BasicMelee_Fighter"],
        passive_abilities=["Sturdy"],
        disorders=disorders,
        body_parts={CatBodySlot.TEXTURE: 309, CatBodySlot.BODY: 410},
        level=7,
        collar="Fighter",
        coi=0.0,
        lover=None,
        lover_affinity=1.0,
        hater=None,
        hater_affinity=1.0,
    )


class TestIsKitten:
    def test_age_zero_is_kitten(self) -> None:
        cat = make_cat(1, age=0)
        assert cat.is_kitten() is True

    def test_age_one_is_kitten(self) -> None:
        cat = make_cat(1, age=1)
        assert cat.is_kitten() is True

    def test_age_two_not_kitten(self) -> None:
        cat = make_cat(1, age=2)
        assert cat.is_kitten() is False

    def test_age_fourteen_not_kitten(self) -> None:
        cat = make_cat(1, age=14)
        assert cat.is_kitten() is False

    def test_age_none_not_kitten(self) -> None:
        cat = make_cat(1, age=None)
        assert cat.is_kitten() is False

    def test_custom_max_age(self) -> None:
        cat_age_2 = make_cat(1, age=2)
        assert cat_age_2.is_kitten(max_age=2) is True
        assert cat_age_2.is_kitten(max_age=1) is False


class TestCanBreed:
    def test_adult_can_breed(self) -> None:
        cat = make_cat(1, age=14)
        assert cat.can_breed() is True

    def test_kitten_cannot_breed(self) -> None:
        cat = make_cat(1, age=0)
        assert cat.can_breed() is False

    def test_age_one_cannot_breed(self) -> None:
        cat = make_cat(1, age=1)
        assert cat.can_breed() is False

    def test_eternal_youth_cannot_breed(self) -> None:
        cat = make_cat(1, age=14, eternal_youth=True)
        assert cat.can_breed() is False

    def test_age_none_can_breed(self) -> None:
        cat = make_cat(1, age=None)
        assert cat.can_breed() is True

    def test_kitten_with_eternal_youth_cannot_breed(self) -> None:
        cat = make_cat(1, age=0, eternal_youth=True)
        assert cat.can_breed() is False
