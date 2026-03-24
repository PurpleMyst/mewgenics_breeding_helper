"""Tests for mewgenics_scorer factors module with ENS architecture."""

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


class TestBodyPartTraitHelpers:
    """Tests for BodyPartTrait helper functions."""

    def test_get_slot(self):
        from mewgenics_parser.cat import CatBodyPartCategory

        trait = BodyPartTrait(_key="Ears300")
        assert trait.body_part_category == CatBodyPartCategory.EARS

    def test_get_part_id(self):
        trait = BodyPartTrait(_key="Ears300")
        assert trait.part_id == 300
