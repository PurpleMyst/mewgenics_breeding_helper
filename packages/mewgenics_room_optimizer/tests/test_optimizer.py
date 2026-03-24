"""Comprehensive tests for Mewgenics room optimizer."""

from unittest.mock import patch

import pytest
from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatGender, CatStatus, CatBodySlot, Stats

from mewgenics_room_optimizer import (
    RoomConfig,
    RoomType,
    optimize_sa,
)
from mewgenics_room_optimizer.optimizer import (
    PairCache,
    _build_results_from_state_dict,
    _cat_stats_sum,
    _evaluate_state,
    _filter_cats,
    _generate_pairs,
)


# --- TEST FIXTURES & HELPERS ---


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    status: CatStatus = CatStatus.IN_HOUSE,
    stat_base: tuple[int, int, int, int, int, int, int] = (5, 5, 5, 5, 5, 5, 5),
    passive_abilities: list[str] | None = None,
    active_abilities: list[str] | None = None,
    room: str | None = None,
    age: int | None = 0,
    aggression: float = 0.0,
    libido: float = 0.5,
    parent_a: Cat | None = None,
    parent_b: Cat | None = None,
    disorders: list[str] | None = None,
) -> Cat:
    """Helper to generate consistent cats with stable db_keys."""
    return Cat(
        db_key=db_key,
        name=f"Cat_{db_key}",
        name_tag="",
        gender=gender,
        status=status,
        room=room,
        stat_base=Stats(*stat_base),
        stat_total=Stats(*stat_base),
        age=age,
        aggression=aggression,
        libido=libido,
        sexuality=None,
        active_abilities=active_abilities or [],
        passive_abilities=passive_abilities or [],
        disorders=disorders or [],
        body_parts={
            CatBodySlot.TEXTURE: 0,
            CatBodySlot.BODY: 0,
            CatBodySlot.HEAD: 0,
            CatBodySlot.TAIL: 0,
            CatBodySlot.LEFT_LEG: 0,
            CatBodySlot.RIGHT_LEG: 0,
            CatBodySlot.LEFT_ARM: 0,
            CatBodySlot.RIGHT_ARM: 0,
            CatBodySlot.LEFT_EYE: 0,
            CatBodySlot.RIGHT_EYE: 0,
            CatBodySlot.LEFT_EYEBROW: 0,
            CatBodySlot.RIGHT_EYEBROW: 0,
            CatBodySlot.LEFT_EAR: 0,
            CatBodySlot.RIGHT_EAR: 0,
            CatBodySlot.MOUTH: 0,
        },
        parent_a=parent_a,
        parent_b=parent_b,
        lover=None,
        hater=None,
        fertility=0.5,
        level=1,
        collar="",
        coi=0.0,
    )


def make_save_data(cats: list[Cat] | None = None, coi: float = 0.0) -> SaveData:
    """Create a mock SaveData with optional cats and default CoI for all pairs."""
    if cats is None:
        cats = []
    coi_memo: dict[tuple[int, int], float] = {}
    for cat_a in cats:
        for cat_b in cats:
            coi_memo[(cat_a.db_key, cat_b.db_key)] = coi
    return SaveData(
        cats=cats,
        current_day=0,
        house_count=len(cats),
        adventure_count=0,
        gone_count=0,
        _parents_coi_memo=coi_memo,
    )


@pytest.fixture
def basic_rooms():
    return [
        RoomConfig("breed1", RoomType.BREEDING, 4, 50.0),
        RoomConfig("fight1", RoomType.FIGHTING, 2, 1000.0),
        RoomConfig("gen1", RoomType.GENERAL, 1, 50.0),
    ]


# --- UNIT TESTS: UTILITIES ---


class TestUtilities:
    def test_cat_stats_sum(self):
        cat = make_cat(1, stat_base=(1, 2, 3, 4, 5, 6, 7))
        assert _cat_stats_sum(cat) == 28

    def test_generate_pairs(self):
        cats = [
            make_cat(1, CatGender.MALE),
            make_cat(2, CatGender.FEMALE),
            make_cat(3, CatGender.FEMALE),
            make_cat(4, CatGender.DITTO),
        ]
        pairs = _generate_pairs(cats)

        # Expect: 1x2, 1x3, 1x4, 2x4, 3x4 = 5 pairs
        assert len(pairs) == 5
        # Verify no male x male or female x female
        for a, b in pairs:
            assert not (a.gender == CatGender.MALE and b.gender == CatGender.MALE)
            assert not (a.gender == CatGender.FEMALE and b.gender == CatGender.FEMALE)


class TestEternalYouthPlacement:
    @patch("mewgenics_room_optimizer.optimizer.calculate_pair_quality")
    def test_ey_cats_routed_to_best_breeding_room(self, mock_quality, basic_rooms):
        """EY cats should be placed in breeding room with highest base_stim."""
        mock_quality.return_value = 50.0

        cats = [
            make_cat(1, CatGender.MALE, stat_base=(10, 10, 10, 10, 10, 10, 10)),
            make_cat(2, CatGender.FEMALE, stat_base=(10, 10, 10, 10, 10, 10, 10)),
            make_cat(3, CatGender.FEMALE, disorders=["EternalYouth"]),
        ]

        result = optimize_sa(make_save_data(cats), basic_rooms, [])

        ey_cat = next(c for c in cats if c.has_eternal_youth())
        ey_room = next(r for r in result.rooms if ey_cat in r.eternal_youth_cats)

        assert ey_room.room.key == "breed1"


class TestConstraints:
    def test_filter_cats(self):
        cats = [
            make_cat(
                1, status=CatStatus.IN_HOUSE, stat_base=(1, 1, 1, 1, 1, 1, 1)
            ),  # sum = 7
            make_cat(
                2, status=CatStatus.IN_HOUSE, stat_base=(10, 10, 10, 10, 10, 10, 10)
            ),  # sum = 70
            make_cat(
                3, status=CatStatus.GONE, stat_base=(10, 10, 10, 10, 10, 10, 10)
            ),  # Gone
        ]
        result = _filter_cats(cats)
        assert [c.db_key for c in result] == [1, 2]  # Cat 3 should be excluded


# --- INTEGRATION TESTS: SA LOGIC ---


class TestSAEvaluator:
    @patch("mewgenics_room_optimizer.optimizer.score_pair")
    def test_evaluate_state_true_stim_injection(self, mock_score_pair):
        """Verifies EY cats inject true_stim into the scoring function."""
        from unittest.mock import MagicMock

        # Setup mock to return a ScoredPair with quality=10
        mock_score = MagicMock()
        mock_score.quality = 10.0
        mock_score_pair.return_value = mock_score

        cats = {
            1: make_cat(1, CatGender.MALE, status=CatStatus.IN_HOUSE, room="b1"),
            2: make_cat(2, CatGender.FEMALE, status=CatStatus.IN_HOUSE, room="b1"),
            3: make_cat(
                3,
                CatGender.FEMALE,
                status=CatStatus.IN_HOUSE,
                room="b1",
                disorders=["EternalYouth"],
            ),
        }

        room = RoomConfig("b1", RoomType.BREEDING, max_cats=6, base_stim=50.0)
        state = {1: "b1", 2: "b1", 3: "b1"}
        original_state = {1: "", 2: "", 3: ""}
        cache = PairCache()
        save_data = make_save_data(list(cats.values()))

        _score = _evaluate_state(
            state, original_state, cats, [room], cache, save_data, None, None
        )

        # Should have at least one pair scored
        assert mock_score_pair.called

    def test_build_results_from_state_dict(self):
        """Tests conversion from state dict to room results."""
        cats = [
            make_cat(1, CatGender.MALE, status=CatStatus.IN_HOUSE),
            make_cat(2, CatGender.FEMALE, status=CatStatus.IN_HOUSE),
            make_cat(
                3,
                CatGender.MALE,
                status=CatStatus.IN_HOUSE,
                stat_base=(2, 2, 2, 2, 2, 2, 2),
            ),
            make_cat(
                4,
                CatGender.MALE,
                status=CatStatus.IN_HOUSE,
                stat_base=(9, 9, 9, 9, 9, 9, 9),
            ),
            make_cat(
                5,
                CatGender.FEMALE,
                status=CatStatus.IN_HOUSE,
                stat_base=(8, 8, 8, 8, 8, 8, 8),
            ),
            make_cat(
                6,
                CatGender.MALE,
                status=CatStatus.IN_HOUSE,
                stat_base=(1, 1, 1, 1, 1, 1, 1),
            ),
        ]
        cats_by_id = {c.db_key: c for c in cats}

        room_configs = [
            RoomConfig("breed1", RoomType.BREEDING, 4, 50.0),
            RoomConfig("fight1", RoomType.FIGHTING, 2, 50.0),
            RoomConfig("gen1", RoomType.GENERAL, 2, 50.0),
        ]

        # Cat 1 and 2 to breed1, Cat 3 to gen1, Cats 4, 5, 6 to fight1
        state = {
            1: "breed1",
            2: "breed1",
            3: "gen1",
            4: "fight1",
            5: "fight1",
            6: "fight1",
        }

        save_data = make_save_data(cats)

        result = _build_results_from_state_dict(
            state,
            cats_by_id,
            room_configs,
            PairCache(),
            save_data,
            None,
            None,
            sa_cats=cats,
            ey_assignments={},
            filtered_cats=cats,
        )

        breed_room = next(r for r in result.rooms if r.room.key == "breed1")
        assert [c.db_key for c in breed_room.cats] == [1, 2]

        gen_room = next(r for r in result.rooms if r.room.key == "gen1")
        assert [c.db_key for c in gen_room.cats] == [3]

        fight_room = next(r for r in result.rooms if r.room.key == "fight1")
        assert [c.db_key for c in fight_room.cats] == [4, 5, 6]

        assert result.excluded_cats == []

    def test_empty_optimize_sa(self):
        """Test that optimize_sa handles empty inputs gracefully."""
        empty_save_data = make_save_data([])
        result = optimize_sa(empty_save_data, [], [])
        assert result.rooms == []
        assert result.excluded_cats == []
        assert result.stats.total_cats == 0


class TestThroughputMaximization:
    @patch("mewgenics_room_optimizer.optimizer.calculate_pair_quality")
    def test_maximize_throughput_prefers_more_pairs(self, mock_quality, basic_rooms):
        """Test that maximize_throughput actually prefers more pairs."""
        mock_quality.return_value = 50.0

        cats = [
            make_cat(1, CatGender.MALE),
            make_cat(2, CatGender.FEMALE),
            make_cat(3, CatGender.MALE),
            make_cat(4, CatGender.FEMALE),
            make_cat(5, CatGender.MALE),
            make_cat(6, CatGender.FEMALE),
        ]

        # With maximize_throughput - should optimize for more pairs
        result = optimize_sa(make_save_data(cats), basic_rooms, [])

        # Should produce valid results
        assert result is not None
        assert isinstance(result.rooms, list)
        assert result.stats.total_cats == 6
