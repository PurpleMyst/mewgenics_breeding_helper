"""Tests for mewgenics_scorer factors module."""

from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatBodySlot, CatGender, CatStatus, Stats
from mewgenics_parser.traits import (
    BodyPartTrait,
    cat_has_defect_in_slot,
    cat_has_mutation_in_slot,
)
from mewgenics_scorer.factors import (
    PairFactors,
    _aggression_factor,
    _libido_factor,
    _stat_variance,
    calculate_pair_factors,
)


def _default_body_parts() -> dict[CatBodySlot, int]:
    return {
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
    }


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    stat_base: list[int] | None = None,
    aggression: float | None = None,
    libido: float | None = None,
    passives: list | None = None,
    abilities: list | None = None,
    disorders: list | None = None,
    parent_a: Cat | None = None,
    parent_b: Cat | None = None,
    body_parts: dict[CatBodySlot, int] | None = None,
):
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        status=CatStatus.IN_HOUSE,
        gender=gender,
        stat_base=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        stat_total=Stats(*stat_base or [5, 5, 5, 5, 5, 5, 5]),
        aggression=aggression,
        libido=libido,
        sexuality=None,
        passive_abilities=passives or [],
        active_abilities=abilities or [],
        disorders=disorders or [],
        parent_a=parent_a,
        parent_b=parent_b,
        room="Test Room",
        age=5,
        body_parts=body_parts or _default_body_parts(),
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


class TestStatVariance:
    """Tests for stat_variance function."""

    def test_identical_stats(self):
        a = make_cat(1, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, stat_base=[5, 5, 5, 5, 5, 5, 5])
        assert _stat_variance(a, b) == 0.0

    def test_all_different(self):
        a = make_cat(1, stat_base=[10, 10, 10, 10, 10, 10, 10])
        b = make_cat(2, stat_base=[0, 0, 0, 0, 0, 0, 0])
        assert _stat_variance(a, b) == 70.0


class TestAggressionFactor:
    """Tests for aggression_factor function."""

    def test_both_low_aggression(self):
        a = make_cat(1, aggression=0.1)
        b = make_cat(2, aggression=0.1)
        result = _aggression_factor(a, b)
        assert result > 0.8

    def test_both_high_aggression(self):
        a = make_cat(1, aggression=0.9)
        b = make_cat(2, aggression=0.9)
        result = _aggression_factor(a, b)
        assert result < 0.2

    def test_unknown_aggression_defaults(self):
        a = make_cat(1, aggression=None)
        b = make_cat(2, aggression=None)
        assert _aggression_factor(a, b) == 0.5


class TestLibidoFactor:
    """Tests for libido_factor function."""

    def test_both_low_libido(self):
        a = make_cat(1, libido=0.1)
        b = make_cat(2, libido=0.1)
        result = _libido_factor(a, b)
        assert result < 0.2

    def test_both_high_libido(self):
        a = make_cat(1, libido=0.9)
        b = make_cat(2, libido=0.9)
        result = _libido_factor(a, b)
        assert result > 0.8

    def test_unknown_libido_defaults(self):
        a = make_cat(1, libido=None)
        b = make_cat(2, libido=None)
        assert _libido_factor(a, b) == 0.5


class TestCalculatePairFactors:
    """Tests for calculate_pair_factors function."""

    def test_basic_calculation(self):
        a = make_cat(1, CatGender.MALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, CatGender.FEMALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert isinstance(result, PairFactors)
        assert result.can_breed is True
        assert result.hater_conflict is False
        assert result.lover_conflict is False
        assert result.mutual_lovers is False

    def test_unrelated_cats_no_risk(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert result.novel_disorder_chance == 0.02
        assert result.novel_part_defect_chance == 0.0

    def test_total_expected_stats(self):
        a = make_cat(1, CatGender.MALE, stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_cat(2, CatGender.FEMALE, stat_base=[0, 10, 0, 0, 0, 0, 0])
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert len(result.expected_stats) == 7
        assert result.total_expected_stats == sum(result.expected_stats)


class TestBodyPartTraitHelpers:
    """Tests for BodyPartTrait helper functions."""

    def test_get_slot(self):
        from mewgenics_parser.cat import CatBodyPartCategory

        trait = BodyPartTrait(_key="Ears300")
        assert trait.body_part_category == CatBodyPartCategory.EARS

    def test_get_part_id(self):
        trait = BodyPartTrait(_key="Ears300")
        assert trait.part_id == 300

    def test_cat_has_mutation_in_slot_true(self):
        cat = make_cat(
            1,
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
                CatBodySlot.LEFT_EAR: 300,
                CatBodySlot.RIGHT_EAR: 0,
                CatBodySlot.MOUTH: 0,
            },
        )
        assert cat_has_mutation_in_slot(cat, CatBodySlot.LEFT_EAR) is True

    def test_cat_has_mutation_in_slot_true_for_defect(self):
        cat = make_cat(
            1,
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
                CatBodySlot.LEFT_EAR: 700,
                CatBodySlot.RIGHT_EAR: 0,
                CatBodySlot.MOUTH: 0,
            },
        )
        assert cat_has_mutation_in_slot(cat, CatBodySlot.LEFT_EAR) is True

    def test_cat_has_defect_in_slot_true(self):
        cat = make_cat(
            1,
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
                CatBodySlot.LEFT_EAR: 700,
                CatBodySlot.RIGHT_EAR: 0,
                CatBodySlot.MOUTH: 0,
            },
        )
        assert cat_has_defect_in_slot(cat, CatBodySlot.LEFT_EAR) is True

    def test_cat_has_defect_in_slot_false_for_mutation(self):
        cat = make_cat(
            1,
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
                CatBodySlot.LEFT_EAR: 300,
                CatBodySlot.RIGHT_EAR: 0,
                CatBodySlot.MOUTH: 0,
            },
        )
        assert cat_has_defect_in_slot(cat, CatBodySlot.LEFT_EAR) is False
