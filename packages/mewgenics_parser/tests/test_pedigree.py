"""Integration tests for pedigree parsing."""

import pytest
from mewgenics_parser import Cat, SaveData, parse_save
from mewgenics_parser.cat import CatGender, CatStatus, Stats


class TestPedigreeParsing:
    """Verify pedigree parsing produces cycle-free data."""

    def test_pedigree_parent_resolution(self, savefile_path):
        """Verify known cat has expected parents resolved."""
        save = parse_save(savefile_path)

        myst = next(c for c in save.cats if "myst".casefold() in c.name.casefold())
        assert myst.parent_a is not None
        assert myst.parent_b is not None
        assert myst.parent_a.db_key == 700
        assert myst.parent_b.db_key == 781


def _make_test_cat(db_key: int) -> Cat:
    """Helper to create a minimal Cat for testing."""
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        status=CatStatus.IN_HOUSE,
        gender=CatGender.MALE,
        room="Test",
        base_stats=Stats(5, 5, 5, 5, 5, 5, 5),
        total_stats=Stats(5, 5, 5, 5, 5, 5, 5),
        age=1,
        aggression=0.0,
        libido=0.5,
        fertility=0.5,
        sexuality=0.0,
        active_abilities=[],
        passive_abilities=[],
        disorders=[],
        body_parts={},
        level=1,
        collar="",
        coi=0.0,
        parent_a=None,
        parent_b=None,
        lover=None,
        hater=None,
        lover_coefficient=1.0,
        hater_coefficient=1.0,
    )


class TestGetOffspringCoi:
    """Tests for SaveData.get_offspring_coi."""

    def test_get_offspring_coi_raises_keyerror_for_unknown_pair(self):
        """get_offspring_coi raises KeyError when pair not in memo map."""
        cat_a = _make_test_cat(1)
        cat_b = _make_test_cat(2)
        save_data = SaveData(
            cats=[cat_a, cat_b],
            current_day=0,
            house_count=2,
            adventure_count=0,
            gone_count=0,
            _parents_coi_memo={},
        )

        with pytest.raises(KeyError):
            save_data.get_offspring_coi(cat_a, cat_b)

    def test_get_offspring_coi_checks_both_orderings(self):
        """get_offspring_coi finds CoI regardless of which cat is first."""
        cat_a = _make_test_cat(1)
        cat_b = _make_test_cat(2)
        save_data = SaveData(
            cats=[cat_a, cat_b],
            current_day=0,
            house_count=2,
            adventure_count=0,
            gone_count=0,
            _parents_coi_memo={(2, 1): 0.25},
        )

        assert save_data.get_offspring_coi(cat_a, cat_b) == 0.25
        assert save_data.get_offspring_coi(cat_b, cat_a) == 0.25
