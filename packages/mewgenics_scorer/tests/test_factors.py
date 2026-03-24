"""Tests for mewgenics_scorer factors module with ENS architecture."""

import pytest
from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatBodySlot, CatGender, CatStatus, Stats
from mewgenics_parser.traits import (
    BodyPartTrait,
    TraitCategory,
    create_trait,
)
from mewgenics_scorer.factors import (
    PairFactors,
    calculate_pair_factors,
    calculate_pair_quality,
    _get_marginal_prob,
    _evaluate_build,
)
from mewgenics_scorer.types import (
    TraitWeight,
    TargetBuild,
    UniversalTrait,
)
from mewgenics_breeding import simulate_breeding


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
    passives: list | None = None,
    abilities: list | None = None,
    disorders: list | None = None,
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
        aggression=None,
        libido=None,
        sexuality=None,
        passive_abilities=passives or [],
        active_abilities=abilities or [],
        disorders=disorders or [],
        parent_a=None,
        parent_b=None,
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


class TestCalculatePairFactors:
    """Tests for calculate_pair_factors function with ENS architecture."""

    def test_basic_calculation(self):
        a = make_cat(1, CatGender.MALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, CatGender.FEMALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert isinstance(result, PairFactors)
        assert len(result.expected_stats) == 7
        assert result.expected_disorders >= 0
        assert result.expected_defects >= 0
        assert result.universal_ev == 0.0
        assert result.build_yields == {}

    def test_unrelated_cats_no_inherited_disorders(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert result.expected_defects == 0.0

    def test_cats_with_disorders_inherit_probability(self):
        a = make_cat(1, CatGender.MALE, disorders=["Scatological"])
        b = make_cat(2, CatGender.FEMALE, disorders=["SavantSyndrome"])
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert result.expected_disorders > 0

    def test_expected_stats_sum(self):
        a = make_cat(1, CatGender.MALE, stat_base=[10, 0, 0, 0, 0, 0, 0])
        b = make_cat(2, CatGender.FEMALE, stat_base=[0, 10, 0, 0, 0, 0, 0])
        save_data = make_save_data([a, b])

        result = calculate_pair_factors(save_data, a, b)

        assert len(result.expected_stats) == 7
        assert sum(result.expected_stats) > 0

    def test_universal_ev_with_universal_trait(self):
        a = make_cat(1, CatGender.MALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, CatGender.FEMALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        save_data = make_save_data([a, b])

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        universals = [UniversalTrait(trait=sturdy, weight_ens=2.0)]

        result = calculate_pair_factors(save_data, a, b, universals=universals)

        assert result.universal_ev >= 0

    def test_build_yields_with_target_build(self):
        a = make_cat(1, CatGender.MALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        b = make_cat(2, CatGender.FEMALE, stat_base=[5, 5, 5, 5, 5, 5, 5])
        save_data = make_save_data([a, b])

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        target_builds = [
            TargetBuild(
                name="Tank Build",
                requirements=[TraitWeight(trait=sturdy, weight_ens=3.0)],
                anti_synergies=[],
                synergy_bonus_ens=1.0,
            )
        ]

        result = calculate_pair_factors(save_data, a, b, target_builds=target_builds)

        assert "Tank Build" in result.build_yields
        assert result.build_yields["Tank Build"] >= 0


class TestCalculatePairQuality:
    """Tests for calculate_pair_quality function."""

    def test_quality_formula_no_malady(self):
        factors = PairFactors(
            expected_stats=[5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            expected_disorders=0.0,
            expected_defects=0.0,
            universal_ev=0.0,
            build_yields={},
        )

        quality = calculate_pair_quality(factors)

        assert quality == sum(factors.expected_stats)

    def test_quality_with_disorders_penalized(self):
        factors = PairFactors(
            expected_stats=[5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            expected_disorders=1.0,
            expected_defects=0.0,
            universal_ev=0.0,
            build_yields={},
        )

        quality = calculate_pair_quality(factors)

        assert quality == 35.0 - 5.0

    def test_quality_with_defects_penalized(self):
        factors = PairFactors(
            expected_stats=[5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            expected_disorders=0.0,
            expected_defects=2.0,
            universal_ev=0.0,
            build_yields={},
        )

        quality = calculate_pair_quality(factors)

        assert quality == 35.0 - 2.0

    def test_quality_with_universal_ev(self):
        factors = PairFactors(
            expected_stats=[5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            expected_disorders=0.0,
            expected_defects=0.0,
            universal_ev=10.0,
            build_yields={},
        )

        quality = calculate_pair_quality(factors)

        assert quality == 45.0


class TestGetMarginalProb:
    """Tests for _get_marginal_prob helper."""

    def test_passive_ability_probability(self):
        a = make_cat(1, CatGender.MALE, passives=["Sturdy", "Frenzy"])
        b = make_cat(2, CatGender.FEMALE, passives=[])
        coi = 0.0

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=coi)

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        prob = _get_marginal_prob(pmf, sturdy)

        assert 0 <= prob <= 1.0

    def test_body_part_only_checks_first_slot(self):
        body_parts = {
            CatBodySlot.LEFT_EAR: 300,
            CatBodySlot.RIGHT_EAR: 400,
        }
        a = make_cat(1, CatGender.MALE, body_parts=body_parts)
        b = make_cat(2, CatGender.FEMALE)
        coi = 0.0

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=coi)

        ear_trait = create_trait(TraitCategory.BODY_PART, "Ears300")
        prob = _get_marginal_prob(pmf, ear_trait)

        assert 0 <= prob <= 1.0


class TestEvaluateBuild:
    """Tests for _evaluate_build helper."""

    def test_build_with_single_requirement(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=0.0)

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        build = TargetBuild(
            name="Test Build",
            requirements=[TraitWeight(trait=sturdy, weight_ens=2.0)],
            anti_synergies=[],
            synergy_bonus_ens=0.0,
        )

        yield_value = _evaluate_build(pmf, build)

        assert yield_value >= 0

    def test_build_yield_clamped_at_zero(self):
        a = make_cat(1, CatGender.MALE)
        b = make_cat(2, CatGender.FEMALE)

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=0.0)

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        build = TargetBuild(
            name="Anti Build",
            requirements=[TraitWeight(trait=sturdy, weight_ens=2.0)],
            anti_synergies=[TraitWeight(trait=sturdy, weight_ens=10.0)],
            synergy_bonus_ens=0.0,
        )

        yield_value = _evaluate_build(pmf, build)

        assert yield_value >= 0

    def test_multiple_passives_synergy_not_zero(self):
        a = make_cat(1, CatGender.MALE, passives=["Sturdy", "Hunter"])
        b = make_cat(2, CatGender.FEMALE)

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=0.0)

        sturdy = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        hunter = create_trait(TraitCategory.PASSIVE_ABILITY, "Hunter")
        build = TargetBuild(
            name="Multi Passive Build",
            requirements=[
                TraitWeight(trait=sturdy, weight_ens=1.0),
                TraitWeight(trait=hunter, weight_ens=1.0),
            ],
            anti_synergies=[],
            synergy_bonus_ens=2.0,
        )

        yield_value = _evaluate_build(pmf, build)

        p_sturdy = _get_marginal_prob(pmf, sturdy)
        p_hunter = _get_marginal_prob(pmf, hunter)
        p_at_least_one = 1.0 - (1.0 - p_sturdy) * (1.0 - p_hunter)
        expected_synergy = p_at_least_one * 2.0
        expected_yield = (p_sturdy + p_hunter) + expected_synergy

        assert yield_value == pytest.approx(expected_yield, rel=1e-9)

    def test_body_parts_same_category(self):
        body_parts_a = {CatBodySlot.LEFT_EAR: 300}
        body_parts_b = {CatBodySlot.LEFT_EAR: 400}
        a = make_cat(1, CatGender.MALE, body_parts=body_parts_a)
        b = make_cat(2, CatGender.FEMALE, body_parts=body_parts_b)

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=0.0)

        ear_300 = create_trait(TraitCategory.BODY_PART, "Ears300")
        ear_400 = create_trait(TraitCategory.BODY_PART, "Ears400")
        build = TargetBuild(
            name="Same Category Build",
            requirements=[
                TraitWeight(trait=ear_300, weight_ens=1.0),
                TraitWeight(trait=ear_400, weight_ens=1.0),
            ],
            anti_synergies=[],
            synergy_bonus_ens=1.0,
        )

        yield_value = _evaluate_build(pmf, build)

        p_300 = _get_marginal_prob(pmf, ear_300)
        p_400 = _get_marginal_prob(pmf, ear_400)
        p_at_least_one = 1.0 - (1.0 - p_300) * (1.0 - p_400)
        expected_yield = (p_300 + p_400) + p_at_least_one * 1.0

        assert yield_value == pytest.approx(expected_yield, rel=1e-9)

    def test_body_parts_different_categories(self):
        body_parts_a = {CatBodySlot.LEFT_EAR: 300, CatBodySlot.TAIL: 300}
        body_parts_b = {CatBodySlot.LEFT_EAR: 400, CatBodySlot.TAIL: 400}
        a = make_cat(1, CatGender.MALE, body_parts=body_parts_a)
        b = make_cat(2, CatGender.FEMALE, body_parts=body_parts_b)

        pmf = simulate_breeding(a, b, stimulation=50.0, coi=0.0)

        ear_trait = create_trait(TraitCategory.BODY_PART, "Ears300")
        tail_trait = create_trait(TraitCategory.BODY_PART, "Tail300")
        build = TargetBuild(
            name="Different Category Build",
            requirements=[
                TraitWeight(trait=ear_trait, weight_ens=1.0),
                TraitWeight(trait=tail_trait, weight_ens=1.0),
            ],
            anti_synergies=[],
            synergy_bonus_ens=1.0,
        )

        yield_value = _evaluate_build(pmf, build)

        p_ear = _get_marginal_prob(pmf, ear_trait)
        p_tail = _get_marginal_prob(pmf, tail_trait)
        p_at_least_one_ear = 1.0 - (1.0 - p_ear)
        p_at_least_one_tail = 1.0 - (1.0 - p_tail)
        expected_yield = (p_ear + p_tail) + (
            p_at_least_one_ear * p_at_least_one_tail * 1.0
        )

        assert yield_value == pytest.approx(expected_yield, rel=1e-9)


class TestBodyPartTraitHelpers:
    """Tests for BodyPartTrait helper functions."""

    def test_get_slot(self):
        from mewgenics_parser.cat import CatBodyPartCategory

        trait = BodyPartTrait(_key="Ears300")
        assert trait.body_part_category == CatBodyPartCategory.EARS

    def test_get_part_id(self):
        trait = BodyPartTrait(_key="Ears300")
        assert trait.part_id == 300
