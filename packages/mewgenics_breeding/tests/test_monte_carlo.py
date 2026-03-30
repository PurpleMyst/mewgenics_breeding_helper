"""Tests for Monte Carlo room breeding simulation."""

import pytest
from mewgenics_parser.cat import Cat, CatBodySlot, CatGender, CatStatus, Stats

from mewgenics_breeding.monte_carlo import (
    calc_combined_fertility,
    calc_compatibility,
    can_breed_pair,
    simulate_room_breeding,
)


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    charisma: int = 7,
    libido: float = 0.5,
    sexuality: float | None = 0.0,
    fertility: float | None = 1.0,
    lover_id: int | None = None,
    lover_affinity: float = 1.0,
    status: CatStatus = CatStatus.IN_HOUSE,
    eternal_youth: bool = False,
) -> Cat:
    disorders: list[str] = []
    if eternal_youth:
        disorders.append("eternalyouth")
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        gender=gender,
        status=status,
        room="Floor1_Large",
        base_stats=Stats(7, 7, 7, 7, 7, charisma, 7),
        total_stats=Stats(7, 7, 7, 7, 7, charisma, 7),
        age=14,
        aggression=0.5,
        libido=libido,
        fertility=fertility,
        sexuality=sexuality,
        active_abilities=["DefaultMove", "BasicMelee_Fighter"],
        passive_abilities=["Sturdy"],
        disorders=disorders,
        body_parts={CatBodySlot.TEXTURE: 309, CatBodySlot.BODY: 410},
        level=7,
        collar="Fighter",
        coi=0.0,
        lover=lover_id,
        lover_affinity=lover_affinity,
        hater=None,
        hater_affinity=1.0,
    )


class TestCompatibilityCalculation:
    def test_zero_for_same_cat(self) -> None:
        cat = make_cat(1)
        assert calc_compatibility(cat, cat) == 0.0

    def test_zero_for_eternal_youth(self) -> None:
        father = make_cat(1, charisma=10, eternal_youth=True)
        mother = make_cat(2, gender=CatGender.FEMALE)
        assert calc_compatibility(father, mother) == 0.0

    def test_zero_for_non_in_house(self) -> None:
        father = make_cat(1, charisma=10, status=CatStatus.ADVENTURE)
        mother = make_cat(2, gender=CatGender.FEMALE)
        assert calc_compatibility(father, mother) == 0.0

    def test_lover_boost(self) -> None:
        father = make_cat(1, charisma=7)
        mother = make_cat(
            2, gender=CatGender.FEMALE, libido=0.5, lover_id=1, lover_affinity=0.5
        )
        compat = calc_compatibility(father, mother)
        assert compat > 0

    def test_lover_penalty(self) -> None:
        father = make_cat(1, charisma=7)
        mother = make_cat(
            2, gender=CatGender.FEMALE, libido=0.5, lover_id=999, lover_affinity=0.5
        )
        compat = calc_compatibility(father, mother)
        base = 0.15 * 7 * 0.5
        assert compat < base

    def test_opposite_sex_straight(self) -> None:
        father = make_cat(1, charisma=7, sexuality=0.0)
        mother = make_cat(2, gender=CatGender.FEMALE, libido=0.5, sexuality=0.0)
        compat = calc_compatibility(father, mother)
        assert compat > 0

    def test_same_sex_straight_gives_zero(self) -> None:
        father = make_cat(1, charisma=7, sexuality=0.0)
        mother = make_cat(2, gender=CatGender.MALE, libido=0.5, sexuality=0.0)
        compat = calc_compatibility(father, mother)
        assert compat == 0.0

    def test_ditto_bypasses_sexuality(self) -> None:
        ditto = make_cat(1, gender=CatGender.DITTO, charisma=7)
        female = make_cat(2, gender=CatGender.FEMALE, libido=0.5, sexuality=0.0)
        compat = calc_compatibility(ditto, female)
        assert compat > 0


class TestFertilityCalculation:
    def test_default_fertility(self) -> None:
        a = make_cat(1, fertility=None)
        b = make_cat(2, fertility=None)
        assert calc_combined_fertility(a, b) == 1.0

    def test_fertility_multiplication(self) -> None:
        a = make_cat(1, fertility=1.1)
        b = make_cat(2, fertility=1.2)
        assert calc_combined_fertility(a, b) == pytest.approx(1.32)


class TestCanBreedPair:
    def test_male_female(self) -> None:
        male = make_cat(1, gender=CatGender.MALE)
        female = make_cat(2, gender=CatGender.FEMALE)
        assert can_breed_pair(male, female)

    def test_male_ditto(self) -> None:
        male = make_cat(1, gender=CatGender.MALE)
        ditto = make_cat(2, gender=CatGender.DITTO)
        assert can_breed_pair(male, ditto)

    def test_same_sex_no_ditto(self) -> None:
        male1 = make_cat(1, gender=CatGender.MALE)
        male2 = make_cat(2, gender=CatGender.MALE)
        assert not can_breed_pair(male1, male2)


class TestSimulateRoomBreeding:
    def test_empty_room(self) -> None:
        result = simulate_room_breeding([], comfort=5.0)
        assert result.pair_kittens == {}
        assert result.converged

    def test_single_cat(self) -> None:
        cat = make_cat(1)
        result = simulate_room_breeding([cat], comfort=5.0)
        assert result.pair_kittens == {}
        assert result.converged

    def test_zero_comfort_zero_kittens(self) -> None:
        male = make_cat(1, charisma=10, libido=1.0, sexuality=0.0)
        female = make_cat(
            2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
        )
        result = simulate_room_breeding(
            [male, female], comfort=0.0, max_iterations=1000
        )
        assert all(v == 0.0 for v in result.pair_kittens.values())

    def test_high_comfort_nonzero_kittens(self) -> None:
        male = make_cat(1, charisma=10, libido=1.0, sexuality=0.0)
        female = make_cat(
            2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
        )
        result = simulate_room_breeding(
            [male, female], comfort=10.0, max_iterations=10000, seed=42
        )
        pair_key = (1, 2)
        assert result.pair_kittens[pair_key] > 0.0

    def test_early_stopping(self) -> None:
        male = make_cat(1, charisma=10, libido=1.0, sexuality=0.0)
        female = make_cat(
            2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
        )
        result = simulate_room_breeding(
            [male, female],
            comfort=10.0,
            max_iterations=1_000_000,
            early_stop_rounds=100,
            relative_tolerance=0.01,
            seed=42,
        )
        assert result.iterations_run < 1_000_000

    def test_seed_reproducibility(self) -> None:
        male = make_cat(1, charisma=10, libido=1.0, sexuality=0.0)
        female = make_cat(
            2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
        )
        result1 = simulate_room_breeding(
            [male, female], comfort=10.0, max_iterations=1000, seed=123
        )
        result2 = simulate_room_breeding(
            [male, female], comfort=10.0, max_iterations=1000, seed=123
        )
        assert result1.pair_kittens == result2.pair_kittens

    def test_multiple_cats(self) -> None:
        cats = [
            make_cat(1, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
            make_cat(3, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                4, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
        ]
        result = simulate_room_breeding(
            cats, comfort=10.0, max_iterations=5000, seed=42
        )
        assert len(result.pair_kittens) >= 2

    def test_ditto_pair(self) -> None:
        ditto1 = make_cat(1, gender=CatGender.DITTO, charisma=10, libido=1.0)
        ditto2 = make_cat(2, gender=CatGender.DITTO, charisma=10, libido=1.0)
        result = simulate_room_breeding(
            [ditto1, ditto2], comfort=10.0, max_iterations=5000, seed=42
        )
        pair_key = (1, 2)
        assert pair_key in result.pair_kittens
