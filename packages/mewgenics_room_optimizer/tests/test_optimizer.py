"""Tests for room optimizer."""

import pytest
from unittest.mock import MagicMock, patch

from mewgenics_room_optimizer import (
    RoomType,
    RoomConfig,
    OptimizationParams,
    DEFAULT_ROOM_CONFIGS,
    optimize,
)
from mewgenics_room_optimizer.optimizer import (
    _cat_stats_sum,
    _filter_cats,
    _generate_pairs,
)


def make_mock_cat(
    db_key: int,
    gender: str = "male",
    status: str = "In House",
    stat_base: list[int] = None,
    mutations: list = None,
    passive_abilities: list = None,
    abilities: list = None,
    lovers=None,
    haters=None,
    parent_a=None,
    parent_b=None,
):
    cat = MagicMock()
    cat.db_key = db_key
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
        assert len(DEFAULT_ROOM_CONFIGS) == 3

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

    @pytest.fixture
    def mock_scorer(self):
        with patch("mewgenics_room_optimizer.optimizer.calculate_pair_factors") as mock:
            mock_factors = MagicMock()
            mock_factors.risk_percent = 0.0
            mock_factors.total_expected_stats = 35.0
            mock_factors.expected_stats = [5.0] * 7
            mock_factors.aggression_factor = 0.5
            mock_factors.libido_factor = 0.5
            mock_factors.trait_matches = []
            mock.return_value = mock_factors
            yield mock

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

        result = optimize(cats, rooms, params, {})

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

        result = optimize(cats, rooms, params, {})

        assert result.stats.total_cats == 2
        assert result.stats.assigned_cats == 2

    def test_respects_max_risk(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams(max_risk=0.0)

        mock_scorer.return_value.risk_percent = 50.0

        result = optimize(cats, rooms, params, {})

        assert result.stats.total_pairs == 0


class TestOptimizationResultSchema:
    """Snapshot-style tests for result schema."""

    @pytest.fixture
    def mock_scorer(self):
        with patch("mewgenics_room_optimizer.optimizer.calculate_pair_factors") as mock:
            mock_factors = MagicMock()
            mock_factors.risk_percent = 5.0
            mock_factors.total_expected_stats = 35.0
            mock_factors.expected_stats = [5.0] * 7
            mock_factors.aggression_factor = 0.5
            mock_factors.libido_factor = 0.5
            mock_factors.trait_matches = []
            mock.return_value = mock_factors
            yield mock

    def test_result_has_required_fields(self, mock_scorer):
        cats = [
            make_mock_cat(1, gender="male"),
            make_mock_cat(2, gender="female"),
        ]
        rooms = [
            RoomConfig("test1", "Test 1", RoomType.BREEDING, 6),
        ]
        params = OptimizationParams()

        result = optimize(cats, rooms, params, {})

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

        result = optimize(cats, rooms, params, {})

        for room_result in result.rooms:
            assert hasattr(room_result, "room")
            assert hasattr(room_result, "cats")
            assert hasattr(room_result, "pairs")
            assert isinstance(room_result.room, RoomConfig)
            assert isinstance(room_result.cats, list)
            assert isinstance(room_result.pairs, list)
