"""Tests for room optimizer."""

import random
from unittest.mock import MagicMock, patch

import pytest
from dirty_equals import HasAttributes
from inline_snapshot import snapshot

from mewgenics_room_optimizer import (
    DEFAULT_ROOM_CONFIGS,
    OptimizationParams,
    OptimizationStats,
    RoomConfig,
    RoomType,
    optimize_sa,
)
from mewgenics_room_optimizer.optimizer import (
    _cat_stats_sum,
    _filter_cats,
    _generate_pairs,
    _generate_random_valid_state,
    _get_neighbor,
)


@pytest.fixture
def mock_scorer():
    with patch("mewgenics_room_optimizer.optimizer.calculate_pair_factors") as mock:
        mock_factors = MagicMock()
        mock_factors.can_breed = True
        mock_factors.hater_conflict = False
        mock_factors.lover_conflict = False
        mock_factors.mutual_lovers = False
        mock_factors.expected_disorder_chance = 0.02
        mock_factors.expected_part_defect_chance = 0.03
        mock_factors.expected_stats = [5.0] * 7
        mock_factors.total_expected_stats = 35.0
        mock_factors.stat_variance = 0.0
        mock_factors.aggression_factor = 0.5
        mock_factors.libido_factor = 0.5
        mock_factors.charisma_factor = 0.5
        mock_factors.trait_matches = []
        mock_factors.combined_malady_chance = 0.05
        mock.return_value = mock_factors
        yield mock


def make_mock_cat(
    db_key: int,
    gender: str = "male",
    status: str = "In House",
    stat_base: list[int] | None = None,
    mutations: list | None = None,
    passive_abilities: list | None = None,
    abilities: list | None = None,
    lovers=None,
    haters=None,
    parent_a=None,
    parent_b=None,
):
    cat = MagicMock()
    cat.db_key = db_key
    cat.name = f"Cat{db_key}"
    cat.gender = gender
    cat.status = status
    cat.stat_base = stat_base or [5, 5, 5, 5, 5, 5, 5]
    cat.mutations = mutations or []
    cat.passive_abilities = passive_abilities or []
    cat.abilities = abilities or []
    cat.lovers = lovers or []
    cat.haters = haters or []
    cat.parent_a = parent_a
    cat.parent_b = parent_b
    return cat


class TestCatStatsSum:
    """Tests for _cat_stats_sum function."""

    def test_all_fives(self):
        cat = make_mock_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        assert _cat_stats_sum(cat) == 35

    def test_mixed_stats(self):
        cat = make_mock_cat(1, stat_base=[10, 8, 6, 4, 2, 0, 0])
        assert _cat_stats_sum(cat) == 30


class TestFilterCats:
    """Tests for _filter_cats function."""

    def test_filters_gone_cats(self):
        cats = [
            make_mock_cat(1, status="In House"),
            make_mock_cat(2, status="Gone"),
            make_mock_cat(3, status="Adventure"),
        ]
        result = _filter_cats(cats, 0)
        assert len(result) == 1
        assert result[0].db_key == 1

    def test_filters_by_min_stats(self):
        cats = [
            make_mock_cat(1, stat_base=[10, 10, 10, 10, 10, 10, 10]),
            make_mock_cat(2, stat_base=[1, 1, 1, 1, 1, 1, 1]),
        ]
        result = _filter_cats(cats, 35)
        assert len(result) == 1
        assert result[0].db_key == 1


class TestGeneratePairs:
    """Tests for _generate_pairs function."""

    def test_male_female_pairs(self):
        males = [make_mock_cat(1, gender="male"), make_mock_cat(2, gender="male")]
        females = [make_mock_cat(3, gender="female")]
        cats = males + females
        pairs = _generate_pairs(cats)
        assert len(pairs) == 2

    def test_no_pairs_same_gender(self):
        males = [make_mock_cat(1, gender="male"), make_mock_cat(2, gender="male")]
        cats = males
        pairs = _generate_pairs(cats)
        assert len(pairs) == 0

    def test_unknown_gender_pairs(self):
        unknown = [make_mock_cat(1, gender="?"), make_mock_cat(2, gender="?")]
        cats = unknown
        pairs = _generate_pairs(cats)
        assert len(pairs) == 1


class TestDefaultRoomConfigs:
    """Tests for default room configurations."""

    def test_has_three_rooms(self):
        assert len(DEFAULT_ROOM_CONFIGS) == 5

    def test_fighting_room(self):
        fighting = [r for r in DEFAULT_ROOM_CONFIGS if r.room_type == RoomType.FIGHTING]
        assert len(fighting) == 1
        assert fighting[0].max_cats is None

    def test_breeding_room(self):
        breeding = [r for r in DEFAULT_ROOM_CONFIGS if r.room_type == RoomType.BREEDING]
        assert len(breeding) == 1
        assert breeding[0].max_cats == 6

    def test_general_room(self):
        general = [r for r in DEFAULT_ROOM_CONFIGS if r.room_type == RoomType.GENERAL]
        assert len(general) == 1
        assert general[0].key == "Attic"
        assert general[0].display_name == "Top Floor"
        assert general[0].max_cats == 6


class TestOptimize:
    """Tests for optimize function."""

    def test_basic_optimization(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
            make_mock_cat(3, gender="male"),
            make_mock_cat(4, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
            RoomConfig("test2", "Test 2", RoomType.FIGHTING, None),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        assert result.stats.total_cats == 4
        assert isinstance(result.rooms, list)

    def test_excludes_adventure_cats(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male", status="In House"),
            make_mock_cat(2, gender="female", status="In House"),
            make_mock_cat(3, gender="female", status="Adventure"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        assert result.stats.total_cats == 2

    def test_respects_max_risk(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams(max_risk=0.0)

        mock_scorer.return_value.combined_malady_chance = 0.5  # 50% = 0.5 probability

        result = optimize_sa(cats, rooms, params, {})

        assert result.stats.total_pairs == 0


class TestOptimizationResultSchema:
    """Snapshot-style tests for result schema."""

    def test_result_has_required_fields(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        assert hasattr(result, "rooms")
        assert hasattr(result, "excluded_cats")
        assert hasattr(result, "stats")
        assert hasattr(result.stats, "total_cats")
        assert hasattr(result.stats, "assigned_cats")
        assert hasattr(result.stats, "total_pairs")
        assert hasattr(result.stats, "breeding_rooms_used")
        assert hasattr(result.stats, "general_rooms_used")
        assert hasattr(result.stats, "avg_pair_quality")
        assert hasattr(result.stats, "avg_risk_percent")

    def test_room_assignment_structure(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        for room_result in result.rooms:
            assert hasattr(room_result, "room")
            assert hasattr(room_result, "cats")
            assert hasattr(room_result, "pairs")
            assert isinstance(room_result.room, RoomConfig)
            assert isinstance(room_result.cats, list)
            assert isinstance(room_result.pairs, list)


class TestSnapshotResults:
    """Snapshot tests for optimization results."""

    def test_optimization_stats_snapshot(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
            make_mock_cat(3, gender="male"),
            make_mock_cat(4, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
            RoomConfig("test2", "Test 2", RoomType.FIGHTING, None),
            RoomConfig("test3", "Test 3", RoomType.GENERAL, 6),
        ]
        params = OptimizationParams(min_stats=10)

        result = optimize_sa(cats, rooms, params, {})

        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=4,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )

    def test_optimization_rooms_snapshot(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
            make_mock_cat(3, gender="male"),
            make_mock_cat(4, gender="female"),
        ]
        rooms = [
            RoomConfig("breeding", "Breeding Room", RoomType.BREEDING, 6),
            RoomConfig("fighting", "Fighting Room", RoomType.FIGHTING, None),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        room_summaries = [
            {
                "room_key": r.room.key,
                "room_type": r.room.room_type.value,
                "num_cats": len(r.cats),
                "num_pairs": len(r.pairs),
            }
            for r in result.rooms
        ]
        assert room_summaries == snapshot([])

    def test_default_room_configs_snapshot(self):
        assert DEFAULT_ROOM_CONFIGS == snapshot(
            [
                RoomConfig(
                    key="Floor1_Large",
                    display_name="Ground Floor Left",
                    room_type=RoomType.FIGHTING,
                ),
                RoomConfig(
                    key="Floor1_Small",
                    display_name="Ground Floor Right",
                    room_type=RoomType.BREEDING,
                    max_cats=6,
                ),
                RoomConfig(
                    key="Attic",
                    display_name="Top Floor",
                    room_type=RoomType.GENERAL,
                    max_cats=6,
                ),
                RoomConfig(
                    key="Floor2_Large",
                    display_name="Second Floor Left",
                    room_type=RoomType.NONE,
                ),
                RoomConfig(
                    key="Floor2_Small",
                    display_name="Second Floor Right",
                    room_type=RoomType.NONE,
                ),
            ]
        )

    def test_empty_cats_result_snapshot(self, mock_scorer):
        cats = []
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams()

        result = optimize_sa(cats, rooms, params, {})

        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=0,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )


class TestGetNeighbor:
    """Tests for _get_neighbor function."""

    def test_returns_dict(self):
        state = {1: "room_a", 2: "room_a"}
        rooms = ["room_a", "room_b"]
        random.seed(42)
        result = _get_neighbor(state, rooms)
        assert isinstance(result, dict)

    def test_preserves_all_keys(self):
        state = {1: "room_a", 2: "room_b", 3: "room_c"}
        rooms = ["room_a", "room_b", "room_c"]
        random.seed(42)
        result = _get_neighbor(state, rooms)
        assert result == snapshot({1: "room_b", 2: "room_a", 3: "room_c"})

    def test_empty_state_returns_empty(self):
        result = _get_neighbor({}, ["room_a"])
        assert result == snapshot({})


class TestGenerateRandomValidState:
    """Tests for _generate_random_valid_state."""

    def test_returns_dict(self):
        cats = [make_mock_cat(1), make_mock_cat(2)]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 6)]
        random.seed(42)
        result = _generate_random_valid_state(cats, rooms)
        assert result == snapshot({1: "test", 2: "test"})

    def test_respects_capacity(self):
        cats = [make_mock_cat(i, gender="male") for i in range(10)]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 4)]
        assert _generate_random_valid_state(cats, rooms) == snapshot(
            {0: "test", 1: "test", 2: "test", 3: "test"}
        )

    def test_empty_cats_returns_empty(self):
        result = _generate_random_valid_state([], [])
        assert result == snapshot({})

    def test_all_cats_assigned_when_possible(self):
        cats = [make_mock_cat(1, gender="male"), make_mock_cat(2, gender="female")]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 6)]
        random.seed(42)
        result = _generate_random_valid_state(cats, rooms)
        assert result == snapshot({1: "test", 2: "test"})


class TestOptimizeSA:
    """Integration tests for optimize_sa."""

    def test_returns_optimization_result(self):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 6)]
        params = OptimizationParams()
        result = optimize_sa(cats, rooms, params, {})
        assert result.rooms == snapshot([])
        assert result.excluded_cats == snapshot(
            [HasAttributes(db_key=1), HasAttributes(db_key=2)]
        )
        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=2,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )

    def test_empty_cats_returns_empty_result(self):
        result = optimize_sa([], [], OptimizationParams(), {})
        assert result.rooms == snapshot([])
        assert result.excluded_cats == snapshot([])
        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=0,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )

    def test_filters_gone_cats(self):
        cats = [
            make_mock_cat(1, gender="male", status="In House"),
            make_mock_cat(2, gender="female", status="Gone"),
        ]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 6)]
        params = OptimizationParams()
        result = optimize_sa(cats, rooms, params, {})
        assert result.rooms == snapshot([])
        assert result.excluded_cats[0].db_key == snapshot(1)
        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=1,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )

    def test_respects_min_stats(self):
        cats = [
            make_mock_cat(1, gender="male", stat_base=[10] * 7),
            make_mock_cat(2, gender="female", stat_base=[1] * 7),
        ]
        rooms = [RoomConfig("test", "Test", RoomType.BREEDING, 6)]
        params = OptimizationParams(min_stats=35)
        result = optimize_sa(cats, rooms, params, {})
        assert result.rooms == snapshot([])
        assert result.excluded_cats[0].db_key == snapshot(1)
        assert result.stats == snapshot(
            OptimizationStats(
                total_cats=1,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            )
        )

    def test_excludes_none_type_rooms(self):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("breeding", "Breeding", RoomType.BREEDING, 6),
            RoomConfig("floor2_none1", "Floor 2 Left", RoomType.NONE),
            RoomConfig("floor2_none2", "Floor 2 Right", RoomType.NONE),
        ]
        params = OptimizationParams()
        result = optimize_sa(cats, rooms, params, {})
        for room in result.rooms:
            assert room.room.room_type != RoomType.NONE
