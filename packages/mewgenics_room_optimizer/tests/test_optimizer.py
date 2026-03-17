"""Comprehensive tests for Mewgenics room optimizer."""

from unittest.mock import MagicMock, patch

import pytest
from mewgenics_scorer import TraitRequirement

from mewgenics_room_optimizer import (
    OptimizationParams,
    RoomConfig,
    RoomType,
    can_pair_gay,
    optimize_sa,
    score_pair,
)
from mewgenics_room_optimizer.optimizer import (
    PairCache,
    _build_results_from_state_dict,
    _cat_stats_sum,
    _evaluate_state,
    _filter_cats,
    _generate_pairs,
    _has_eternalyouth,
    _passes_throughput_cap,
)

# --- TEST FIXTURES & HELPERS ---


def make_mock_cat(
    db_key: int,
    gender: str = "male",
    status: str = "In House",
    stat_base: list[int] | None = None,
    mutations: list[str] | None = None,
    passive_abilities: list[str] | None = None,
    abilities: list[str] | None = None,
) -> MagicMock:
    """Helper to generate consistent mock cats with stable db_keys."""
    cat = MagicMock()
    cat.db_key = db_key
    cat.name = f"Cat_{db_key}"
    cat.gender = gender
    cat.status = status
    cat.stat_base = stat_base or [5, 5, 5, 5, 5, 5, 5]
    cat.mutations = mutations or []
    cat.passive_abilities = passive_abilities or []
    cat.abilities = abilities or []
    cat.lovers = []
    cat.haters = []
    cat.aggression = 0.0
    cat.libido = 0.5
    return cat


@pytest.fixture
def basic_rooms():
    return [
        RoomConfig("breed1", "Breeding 1", RoomType.BREEDING, 4, 50.0),
        RoomConfig("fight1", "Fighting 1", RoomType.FIGHTING, 2, 50.0),
        RoomConfig("gen1", "General 1", RoomType.GENERAL, 1, 50.0),
    ]


# --- UNIT TESTS: UTILITIES ---


class TestUtilities:
    def test_cat_stats_sum(self):
        cat = make_mock_cat(1, stat_base=[1, 2, 3, 4, 5, 6, 7])
        assert _cat_stats_sum(cat) == 28

    def test_has_eternalyouth(self):
        cat_with = make_mock_cat(1, passive_abilities=["Sturdy", "EternalYouth"])
        cat_without = make_mock_cat(2, passive_abilities=["Sturdy"])
        assert _has_eternalyouth(cat_with) is True
        assert _has_eternalyouth(cat_without) is False

    def test_can_pair_gay(self):
        gay_flags = {1: True, 2: False, 3: True}
        cat1, cat2, cat3 = make_mock_cat(1), make_mock_cat(2), make_mock_cat(3)
        cat_spider = make_mock_cat(4, gender="?")

        # Standard straight pair (no flags)
        assert can_pair_gay(make_mock_cat(9), make_mock_cat(10), gay_flags) is True
        # One gay cat, one straight (conflict)
        assert can_pair_gay(cat1, cat2, gay_flags) is False
        # Two gay cats (not allowed since there's no spider)
        assert can_pair_gay(cat1, cat3, gay_flags) is False
        # Gay cat with spidercat (always allowed)
        assert can_pair_gay(cat1, cat_spider, gay_flags) is True

    def test_generate_pairs(self):
        cats = [
            make_mock_cat(1, "male"),
            make_mock_cat(2, "female"),
            make_mock_cat(3, "female"),
            make_mock_cat(4, "?"),
        ]
        pairs = _generate_pairs(cats)  # ty:ignore[invalid-argument-type]

        # Expect: 1x2, 1x3, 1x4, 2x4, 3x4 = 5 pairs
        assert len(pairs) == 5
        # Verify no male x male or female x female
        for a, b in pairs:
            assert not (a.gender == "male" and b.gender == "male")
            assert not (a.gender == "female" and b.gender == "female")


class TestConstraints:
    def test_filter_cats(self):
        cats = [
            make_mock_cat(1, status="In House", stat_base=[1] * 7),  # sum = 7
            make_mock_cat(2, status="In House", stat_base=[10] * 7),  # sum = 70
            make_mock_cat(3, status="Gone", stat_base=[10] * 7),  # Gone
        ]
        result = _filter_cats(cats, min_stats=35)  # ty:ignore[invalid-argument-type]
        assert len(result) == 1
        assert result[0].db_key == 2

    def test_throughput_cap_harem_prevention(self):
        room = RoomConfig("b1", "B1", RoomType.BREEDING, max_cats=5)
        # Cap should be 5 - 2 = 3 max per gender
        cats_in_room = [make_mock_cat(i, "male") for i in range(3)]

        # Adding a 4th male should fail
        assert (
            _passes_throughput_cap(room, cats_in_room, make_mock_cat(4, "male"))  # ty:ignore[invalid-argument-type]
            is False
        )
        # Adding a female should succeed
        assert (
            _passes_throughput_cap(room, cats_in_room, make_mock_cat(5, "female"))  # ty:ignore[invalid-argument-type]
            is True
        )
        # Adding a spidercat should succeed
        assert _passes_throughput_cap(room, cats_in_room, make_mock_cat(6, "?")) is True  # ty:ignore[invalid-argument-type]


# --- INTEGRATION TESTS: SA LOGIC ---


class TestSAEvaluator:
    @patch("mewgenics_room_optimizer.optimizer.score_pair")
    def test_evaluate_state_true_stim_injection(self, mock_score_pair):
        """Verifies EY cats inject true_stim into the scoring function."""
        # Setup mock to return a ScoredPair with quality=10
        mock_score = MagicMock()
        mock_score.quality = 10.0
        mock_score_pair.return_value = mock_score

        cats = {
            1: make_mock_cat(1, "male"),
            2: make_mock_cat(2, "female"),
            3: make_mock_cat(3, "female", passive_abilities=["EternalYouth"]),
        }
        room = RoomConfig("b1", "B1", RoomType.BREEDING, max_cats=6, base_stim=50.0)
        state = {1: "b1", 2: "b1", 3: "b1"}
        params = OptimizationParams(stimulation=50.0)
        cache = PairCache()

        score = _evaluate_state(state, cats, [room], cache, {}, params)  # ty:ignore[invalid-argument-type]

        assert score == 10.0  # 1 pair (1x2)

        # Verify score_pair was called with params holding 51.0 stimulation
        call_args = mock_score_pair.call_args[0]
        passed_params = call_args[3]
        assert passed_params.stimulation == 51.0


# --- INTEGRATION TESTS: FULL PIPELINE ---


class TestOptimizePipeline:
    def test_post_processing_cleanup(self, basic_rooms):
        """Verifies the deterministic routing of utility cats after SA finishes."""

        # We simulate SA returning a state with cats 1 and 2 in a breeding room
        simulated_best_state = {1: "breed1", 2: "breed1"}

        # 8 Cats total
        cats = [
            make_mock_cat(1, "male", stat_base=[10] * 7),  # SA assigned
            make_mock_cat(2, "female", stat_base=[10] * 7),  # SA assigned
            make_mock_cat(
                3, "male", stat_base=[2] * 7, mutations=["Horns"]
            ),  # Trait carrier! (Should go General)
            make_mock_cat(
                4, "male", stat_base=[9] * 7
            ),  # High stats (Should go Fighting)
            make_mock_cat(
                5, "female", stat_base=[8] * 7
            ),  # High stats (Should go Fighting)
            make_mock_cat(
                6, "male", stat_base=[1] * 7
            ),  # Low stats, no traits (Excluded)
        ]
        cats_by_id = {c.db_key: c for c in cats}

        params = OptimizationParams(
            planner_traits=[TraitRequirement("mutation", "Horns", 5.0)]
        )

        result = _build_results_from_state_dict(
            simulated_best_state,
            cats_by_id,
            basic_rooms,
            PairCache(),
            {},
            params,
            cats,  # ty:ignore[invalid-argument-type]
        )

        # Assert Breeding
        breed_room = next(r for r in result.rooms if r.room.key == "breed1")
        assert [c.db_key for c in breed_room.cats] == [1, 2]

        # Assert General (Got the trait carrier)
        gen_room = next(r for r in result.rooms if r.room.key == "gen1")
        assert [c.db_key for c in gen_room.cats] == [3]

        # Assert Fighting (Got the high stat leftovers, up to cap of 2)
        fight_room = next(r for r in result.rooms if r.room.key == "fight1")
        assert [c.db_key for c in fight_room.cats] == [4, 5]

        # Assert Excluded
        assert [c.db_key for c in result.excluded_cats] == [6]

    def test_empty_input_handled_gracefully(self):
        result = optimize_sa([], [], OptimizationParams(), {})
        assert result.rooms == []
        assert result.excluded_cats == []
        assert result.stats.total_cats == 0

    @patch("mewgenics_room_optimizer.optimizer.calculate_pair_quality")
    def test_full_run_no_crashes(self, mock_quality, basic_rooms):
        """Runs the actual parallel pipeline with a small dataset to ensure no syntax/pickling crashes."""
        mock_quality.return_value = 50.0

        cats = [
            make_mock_cat(1, "male"),
            make_mock_cat(2, "female"),
            make_mock_cat(3, "male"),
        ]

        # Override temp and iterations so the test runs instantly
        params = OptimizationParams(sa_temperature=1.0, sa_neighbors_per_temp=2)

        result = optimize_sa(cats, basic_rooms, params, {})  # ty:ignore[invalid-argument-type]

        assert result is not None
        assert isinstance(result.rooms, list)
        assert result.stats.total_cats == 3
