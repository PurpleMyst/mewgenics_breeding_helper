"""Tests for Monte Carlo room breeding simulation."""

import pytest
from inline_snapshot import snapshot
from mewgenics_parser.cat import Cat, CatBodySlot, CatGender, CatStatus, Stats

from mewgenics_breeding.monte_carlo import (
    calc_combined_fertility,
    calc_compatibility,
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

    def test_same_sex_with_sexuality_uses_sin_math(self) -> None:
        father = make_cat(1, charisma=10, sexuality=0.1)
        mother = make_cat(
            2, gender=CatGender.MALE, charisma=10, libido=1.0, sexuality=0.1
        )
        compat = calc_compatibility(father, mother)
        assert compat > 0

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


class TestSnapshotValues:
    def test_compatibility_values(self) -> None:
        high_char_male = make_cat(1, charisma=10)
        low_char_male = make_cat(2, charisma=3)
        high_libido_female = make_cat(
            3, gender=CatGender.FEMALE, charisma=7, libido=1.0
        )
        low_libido_female = make_cat(4, gender=CatGender.FEMALE, charisma=7, libido=0.1)
        straight_male = make_cat(5, charisma=7, sexuality=0.0)
        gay_male = make_cat(6, charisma=7, sexuality=1.0)
        lovers_male = make_cat(7, charisma=7, lover_id=8, lover_affinity=0.5)
        lovers_female = make_cat(
            8, gender=CatGender.FEMALE, charisma=7, lover_id=7, lover_affinity=0.5
        )

        assert calc_compatibility(high_char_male, low_libido_female) == snapshot(0.3375)
        assert calc_compatibility(low_char_male, high_libido_female) == snapshot(0.4875)
        assert calc_compatibility(straight_male, gay_male) == snapshot(0.2625)
        assert calc_compatibility(lovers_male, lovers_female) == snapshot(
            0.7875000000000001
        )

    def test_typical_room_output_snapshot(self) -> None:
        cats = [
            make_cat(1, charisma=7, libido=0.5, sexuality=0.0),
            make_cat(2, gender=CatGender.FEMALE, charisma=7, libido=0.5, sexuality=0.0),
            make_cat(3, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                4, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
        ]
        result = simulate_room_breeding(
            cats,
            comfort=5.0,
            max_iterations=10_000,
            seed=42,
        )
        assert result.pair_kittens == snapshot(
            {
                (1, 2): 0.1272,
                (1, 4): 0.2494,
                (2, 3): 0.2447,
                (3, 4): 0.5589,
            }
        )

    def test_high_stimulation_room_snapshot(self) -> None:
        cats = [
            make_cat(1, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                2, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
            make_cat(3, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                4, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
            make_cat(5, charisma=10, libido=1.0, sexuality=0.0),
            make_cat(
                6, gender=CatGender.FEMALE, charisma=10, libido=1.0, sexuality=0.0
            ),
        ]
        result = simulate_room_breeding(
            cats,
            comfort=10.0,
            max_iterations=20_000,
            early_stop_rounds=1000,
            relative_tolerance=0.005,
            seed=123,
        )
        total_expected_kittens = sum(result.pair_kittens.values())
        assert total_expected_kittens == snapshot(3.0)
        assert len(result.pair_kittens) == snapshot(9)

    def test_lover_boost_snapshot(self) -> None:
        male = make_cat(1, charisma=7, libido=0.5)
        female = make_cat(
            2,
            gender=CatGender.FEMALE,
            charisma=7,
            libido=0.5,
            lover_id=1,
            lover_affinity=0.8,
        )
        result = simulate_room_breeding(
            [male, female],
            comfort=5.0,
            max_iterations=5000,
            seed=42,
        )
        assert result.pair_kittens == snapshot({(1, 2): 0.3896})

    def test_twin_probability_snapshot(self) -> None:
        fertile_male = make_cat(1, charisma=10, libido=1.0, sexuality=0.0)
        fertile_female = make_cat(
            2,
            gender=CatGender.FEMALE,
            charisma=10,
            libido=1.0,
            sexuality=0.0,
            fertility=1.25,
        )
        infertile_male = make_cat(
            3, charisma=10, libido=1.0, sexuality=0.0, fertility=1.0
        )
        infertile_female = make_cat(
            4,
            gender=CatGender.FEMALE,
            charisma=10,
            libido=1.0,
            sexuality=0.0,
            fertility=1.0,
        )

        result_fertile = simulate_room_breeding(
            [fertile_male, fertile_female],
            comfort=10.0,
            max_iterations=10_000,
            seed=42,
        )
        result_infertile = simulate_room_breeding(
            [infertile_male, infertile_female],
            comfort=10.0,
            max_iterations=10_000,
            seed=42,
        )
        assert (
            result_fertile.pair_kittens[(1, 2)] > result_infertile.pair_kittens[(3, 4)]
        )


class TestComfortPenalty:
    def test_four_cats_no_penalty(self) -> None:
        from mewgenics_breeding.monte_carlo import _effective_comfort

        assert _effective_comfort(5.0, 4) == 5.0
        assert _effective_comfort(10.0, 4) == 10.0

    def test_five_cats_one_penalty(self) -> None:
        from mewgenics_breeding.monte_carlo import _effective_comfort

        assert _effective_comfort(5.0, 5) == 4.0
        assert _effective_comfort(10.0, 5) == 9.0

    def test_six_cats_two_penalty(self) -> None:
        from mewgenics_breeding.monte_carlo import _effective_comfort

        assert _effective_comfort(5.0, 6) == 3.0
        assert _effective_comfort(10.0, 6) == 8.0

    def test_overcrowding_reduces_kittens(self) -> None:
        cat1 = make_cat(1, charisma=10, libido=1.0)
        cat2 = make_cat(2, gender=CatGender.FEMALE, charisma=10, libido=1.0)
        cat3 = make_cat(3, charisma=10, libido=1.0)
        cat4 = make_cat(4, gender=CatGender.FEMALE, charisma=10, libido=1.0)
        cat5 = make_cat(5, charisma=10, libido=1.0)
        cat6 = make_cat(6, gender=CatGender.FEMALE, charisma=10, libido=1.0)

        result_4_unchanged = simulate_room_breeding(
            [cat1, cat2, cat3, cat4], comfort=5.0, max_iterations=5000, seed=42
        )
        result_6_with_penalty = simulate_room_breeding(
            [cat1, cat2, cat3, cat4, cat5, cat6],
            comfort=5.0,
            max_iterations=5000,
            seed=42,
        )
        result_6_no_penalty = simulate_room_breeding(
            [cat1, cat2, cat3, cat4, cat5, cat6],
            comfort=7.0,
            max_iterations=5000,
            seed=42,
        )
        avg_per_pair_4 = sum(result_4_unchanged.pair_kittens.values()) / len(
            result_4_unchanged.pair_kittens
        )
        avg_per_pair_6_penalty = sum(result_6_with_penalty.pair_kittens.values()) / len(
            result_6_with_penalty.pair_kittens
        )
        avg_per_pair_6_no_penalty = sum(
            result_6_no_penalty.pair_kittens.values()
        ) / len(result_6_no_penalty.pair_kittens)
        assert avg_per_pair_6_penalty < avg_per_pair_4
        assert avg_per_pair_6_no_penalty > avg_per_pair_6_penalty


class TestKittenExclusion:
    def test_kitten_excluded_from_breeding(self) -> None:
        adult_male = make_cat(1, charisma=10, libido=1.0)
        adult_female = make_cat(2, gender=CatGender.FEMALE, charisma=10, libido=1.0)
        kitten_male = make_cat(3, charisma=10, libido=1.0)
        kitten_male.age = 0
        kitten_female = make_cat(4, gender=CatGender.FEMALE, charisma=10, libido=1.0)
        kitten_female.age = 1

        result = simulate_room_breeding(
            [adult_male, adult_female, kitten_male, kitten_female],
            comfort=10.0,
            max_iterations=5000,
            seed=42,
        )
        assert (1, 2) in result.pair_kittens
        assert (1, 3) not in result.pair_kittens
        assert (1, 4) not in result.pair_kittens
        assert (2, 3) not in result.pair_kittens
        assert (2, 4) not in result.pair_kittens
        assert (3, 4) not in result.pair_kittens

    def test_only_kittens_no_breeding(self) -> None:
        kitten1 = make_cat(1, charisma=10, libido=1.0)
        kitten1.age = 0
        kitten2 = make_cat(2, gender=CatGender.FEMALE, charisma=10, libido=1.0)
        kitten2.age = 1

        result = simulate_room_breeding(
            [kitten1, kitten2], comfort=10.0, max_iterations=1000, seed=42
        )
        assert len(result.pair_kittens) == 0


class TestCompatibilityThreshold:
    def test_below_threshold_no_kittens(self) -> None:
        low_char_male = make_cat(1, charisma=1, libido=0.01)
        low_char_female = make_cat(2, gender=CatGender.FEMALE, charisma=1, libido=0.01)

        result = simulate_room_breeding(
            [low_char_male, low_char_female],
            comfort=10.0,
            max_iterations=5000,
            seed=42,
        )
        assert len(result.pair_kittens) == 0
