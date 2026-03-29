from dataclasses import replace

from inline_snapshot import snapshot
from mewgenics_parser.cat import Cat, CatBodySlot, CatGender, CatStatus, Stats
from pytest import approx

from mewgenics_breeding import (
    OffspringMarginalProbabilities,
    StatsProbabilityMass,
    simulate_breeding,
)

PARENT_A = Cat(
    db_key=1344,
    name="Midnight",
    name_tag="",
    gender=CatGender.MALE,
    status=CatStatus.IN_HOUSE,
    room="Floor1_Large",
    base_stats=Stats(7, 7, 7, 7, 7, 7, 6),
    total_stats=Stats(7, 7, 9, 7, 12, 8, 8),
    age=14,
    aggression=0.5895825765272176,
    libido=0.4709680696721758,
    fertility=0.5,
    sexuality=0.062250739760339104,
    active_abilities=[
        "DefaultMove",
        "BasicMelee_Fighter",
        "FistOfFate2",
        "Stick",
        "SideSlash",
        "FurySwipes",
    ],
    passive_abilities=["HamsterStyle2", "SkullSmash"],
    disorders=["Scatological"],
    body_parts={
        CatBodySlot.TEXTURE: 309,
        CatBodySlot.BODY: 410,
        CatBodySlot.HEAD: 60,
        CatBodySlot.TAIL: 143,
        CatBodySlot.LEFT_LEG: 900,
        CatBodySlot.RIGHT_LEG: 900,
        CatBodySlot.LEFT_ARM: 323,
        CatBodySlot.RIGHT_ARM: 323,
        CatBodySlot.LEFT_EYE: 429,
        CatBodySlot.RIGHT_EYE: 429,
        CatBodySlot.LEFT_EYEBROW: 314,
        CatBodySlot.RIGHT_EYEBROW: 314,
        CatBodySlot.LEFT_EAR: 700,
        CatBodySlot.RIGHT_EAR: 700,
        CatBodySlot.MOUTH: 409,
    },
    level=7,
    collar="Fighter",
    coi=0.29661053677926974,
)
PARENT_B = Cat(
    db_key=1347,
    name="Aila",
    name_tag="",
    gender=CatGender.FEMALE,
    status=CatStatus.IN_HOUSE,
    room="Floor1_Large",
    base_stats=Stats(7, 7, 6, 7, 7, 7, 6),
    total_stats=Stats(6, 10, 8, 7, 7, 7, 9),
    age=14,
    aggression=0.29696269433182465,
    libido=0.5763975568757957,
    fertility=0.5,
    sexuality=0.0993335265071858,
    active_abilities=[
        "DefaultMove",
        "BasicStraightShot_Thief",
        "FistOfFate2",
        "Stalk",
        "CutPurse",
        "MoveAgain",
    ],
    passive_abilities=["GoldenClaws", "Pinpoint2"],
    disorders=["SavantSyndrome"],
    body_parts={
        CatBodySlot.TEXTURE: 420,
        CatBodySlot.BODY: 410,
        CatBodySlot.HEAD: 307,
        CatBodySlot.TAIL: 417,
        CatBodySlot.LEFT_LEG: 900,
        CatBodySlot.RIGHT_LEG: 900,
        CatBodySlot.LEFT_ARM: 700,
        CatBodySlot.RIGHT_ARM: 700,
        CatBodySlot.LEFT_EYE: 429,
        CatBodySlot.RIGHT_EYE: 429,
        CatBodySlot.LEFT_EYEBROW: 900,
        CatBodySlot.RIGHT_EYEBROW: 900,
        CatBodySlot.LEFT_EAR: 416,
        CatBodySlot.RIGHT_EAR: 416,
        CatBodySlot.MOUTH: 304,
    },
    level=7,
    collar="Thief",
    coi=0.303021636682439,
)

COI = 0.3010


class TestBreedingSimulation:
    def test_breeding_simulation_zero_stim(self) -> None:
        assert simulate_breeding(
            PARENT_A, PARENT_B, stimulation=0.0, coi=COI
        ) == snapshot(
            OffspringMarginalProbabilities(
                stats=StatsProbabilityMass(
                    strength=[(7, 1.0)],
                    dexterity=[(7, 1.0)],
                    constitution=[(7, 0.5), (6, 0.5)],
                    intelligence=[(7, 1.0)],
                    speed=[(7, 1.0)],
                    charisma=[(7, 1.0)],
                    luck=[(6, 1.0)],
                ),
                passive_abilities={
                    "HamsterStyle": 0.0125,
                    "SkullSmash": 0.0125,
                    "GoldenClaws": 0.0125,
                    "Pinpoint": 0.0125,
                },
                active_abilities={
                    "CutPurse": 0.0274375,
                    "FistOfFate": 0.05475,
                    "SideSlash": 0.0274375,
                    "Stalk": 0.0274375,
                    "Stick": 0.0274375,
                    "MoveAgain": 0.0274375,
                    "FurySwipes": 0.0274375,
                },
                inherited_disorders={"Scatological": 0.15, "SavantSyndrome": 0.15},
                novel_disorder=0.059040999999999996,
                body_parts={
                    CatBodySlot.TEXTURE: {
                        309: 0.46787650000000003,
                        420: 0.46787650000000003,
                    },
                    CatBodySlot.BODY: {410: 0.9357530000000001},
                    CatBodySlot.HEAD: {
                        60: 0.46787650000000003,
                        307: 0.46787650000000003,
                    },
                    CatBodySlot.TAIL: {
                        143: 0.46787650000000003,
                        417: 0.46787650000000003,
                    },
                    CatBodySlot.MOUTH: {
                        409: 0.46787650000000003,
                        304: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.RIGHT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.LEFT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.RIGHT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.LEFT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                },
                novel_birth_defect=0.4515,
                expected_inherited_disorders=0.3,
                expected_inherited_defects=0.9357530000000001,
            )
        )

    def test_breeding_simulation_thirtytwo_stim(self) -> None:
        assert simulate_breeding(
            PARENT_A, PARENT_B, stimulation=32.0, coi=COI
        ) == snapshot(
            OffspringMarginalProbabilities(
                stats=StatsProbabilityMass(
                    strength=[(7, 1.0)],
                    dexterity=[(7, 1.0)],
                    constitution=[(7, 0.5689655172413793), (6, 0.43103448275862066)],
                    intelligence=[(7, 1.0)],
                    speed=[(7, 1.0)],
                    charisma=[(7, 1.0)],
                    luck=[(6, 1.0)],
                ),
                passive_abilities={
                    "HamsterStyle": 0.0925,
                    "SkullSmash": 0.0925,
                    "GoldenClaws": 0.0925,
                    "Pinpoint": 0.0925,
                },
                active_abilities={
                    "CutPurse": 0.1446875,
                    "FistOfFate": 0.28375,
                    "SideSlash": 0.1446875,
                    "Stalk": 0.1446875,
                    "Stick": 0.1446875,
                    "MoveAgain": 0.1446875,
                    "FurySwipes": 0.1446875,
                },
                inherited_disorders={"Scatological": 0.15, "SavantSyndrome": 0.15},
                novel_disorder=0.059040999999999996,
                body_parts={
                    CatBodySlot.TEXTURE: {
                        309: 0.46787650000000003,
                        420: 0.46787650000000003,
                    },
                    CatBodySlot.BODY: {410: 0.9357530000000001},
                    CatBodySlot.HEAD: {
                        60: 0.4033418103448276,
                        307: 0.5324111896551725,
                    },
                    CatBodySlot.TAIL: {
                        143: 0.4033418103448276,
                        417: 0.5324111896551725,
                    },
                    CatBodySlot.MOUTH: {
                        409: 0.46787650000000003,
                        304: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.RIGHT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.LEFT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.RIGHT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.LEFT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                },
                novel_birth_defect=0.4515,
                expected_inherited_disorders=0.3,
                expected_inherited_defects=0.9357530000000001,
            )
        )

    def test_breeding_simulation_ninetyfive_stim(self) -> None:
        assert simulate_breeding(
            PARENT_A, PARENT_B, stimulation=95.0, coi=COI
        ) == snapshot(
            OffspringMarginalProbabilities(
                stats=StatsProbabilityMass(
                    strength=[(7, 1.0)],
                    dexterity=[(7, 1.0)],
                    constitution=[(7, 0.6610169491525424), (6, 0.3389830508474576)],
                    intelligence=[(7, 1.0)],
                    speed=[(7, 1.0)],
                    charisma=[(7, 1.0)],
                    luck=[(6, 1.0)],
                ),
                passive_abilities={
                    "HamsterStyle": 0.25,
                    "SkullSmash": 0.25,
                    "GoldenClaws": 0.25,
                    "Pinpoint": 0.25,
                },
                active_abilities={
                    "CutPurse": 0.17914062500000003,
                    "FistOfFate": 0.3428125,
                    "SideSlash": 0.17914062500000003,
                    "Stalk": 0.17914062500000003,
                    "Stick": 0.17914062500000003,
                    "MoveAgain": 0.17914062500000003,
                    "FurySwipes": 0.17914062500000003,
                },
                inherited_disorders={"Scatological": 0.15, "SavantSyndrome": 0.15},
                novel_disorder=0.059040999999999996,
                body_parts={
                    CatBodySlot.TEXTURE: {
                        309: 0.46787650000000003,
                        420: 0.46787650000000003,
                    },
                    CatBodySlot.BODY: {410: 0.9357530000000001},
                    CatBodySlot.HEAD: {
                        60: 0.31720440677966105,
                        307: 0.6185485932203391,
                    },
                    CatBodySlot.TAIL: {
                        143: 0.31720440677966105,
                        417: 0.6185485932203391,
                    },
                    CatBodySlot.MOUTH: {
                        409: 0.46787650000000003,
                        304: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.RIGHT_LEG: {900: 0.9357530000000001},
                    CatBodySlot.LEFT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_ARM: {
                        323: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.RIGHT_EYE: {429: 0.9357530000000001},
                    CatBodySlot.LEFT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EYEBROW: {
                        314: 0.46787650000000003,
                        900: 0.46787650000000003,
                    },
                    CatBodySlot.LEFT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                    CatBodySlot.RIGHT_EAR: {
                        416: 0.46787650000000003,
                        700: 0.46787650000000003,
                    },
                },
                novel_birth_defect=0.4515,
                expected_inherited_disorders=0.3,
                expected_inherited_defects=0.9357530000000001,
            )
        )

    def test_breeding_only_one_parent_has_disorders(self) -> None:
        assert simulate_breeding(
            replace(PARENT_A, disorders=PARENT_A.disorders + PARENT_B.disorders),
            replace(PARENT_B, disorders=[]),
            stimulation=95.0,
            coi=COI,
        ).inherited_disorders == snapshot(
            {"Scatological": 0.075, "SavantSyndrome": 0.075}
        )

    def test_breeding_empty_trait_pools(self) -> None:
        """Ensure cats with no abilities or disorders don't cause ZeroDivisionErrors."""
        blank_cat_a = replace(
            PARENT_A, active_abilities=[], passive_abilities=[], disorders=[]
        )
        blank_cat_b = replace(
            PARENT_B, active_abilities=[], passive_abilities=[], disorders=[]
        )

        result = simulate_breeding(blank_cat_a, blank_cat_b, stimulation=50.0, coi=0.0)

        assert result.active_abilities == {}
        assert result.passive_abilities == {}
        assert result.inherited_disorders == {}

    def test_breeding_skillshare_exclusion(self) -> None:
        """Ensure SkillShare is stripped and doesn't break pool dilution."""
        cat_a = replace(PARENT_A, passive_abilities=["SkillShare", "Sturdy"])
        cat_b = replace(
            PARENT_B, passive_abilities=["SkillShare"]
        )  # Becomes empty pool

        result = simulate_breeding(cat_a, cat_b, stimulation=100.0, coi=COI)

        assert "SkillShare" not in result.passive_abilities
        # Since B has no inheritable passives, A's "Sturdy" should get 100% of the selection probability
        # At 100 stim, inherit_prob is 1.0. A is the only valid parent, so Sturdy = 1.0.
        assert result.passive_abilities["Sturdy"] == approx(1.0)

    def test_coi_threshold_zero(self) -> None:
        """At 0 CoI, there should be no novel birth defects and minimum novel disorder."""
        result = simulate_breeding(PARENT_A, PARENT_B, stimulation=50.0, coi=0.0)

        assert result.novel_birth_defect == 0.0
        # Base novel disorder is 0.02. Parent A & B both have 0.15 inherited chance.
        # P(Rolls novel) = 1.0 - (0.15 * 0.15) = 0.9775
        # 0.9775 * 0.02 = 0.01955
        assert result.novel_disorder == approx(0.01955)

    def test_coi_threshold_extreme(self) -> None:
        """At > 0.9 CoI, novel birth defect passes should double."""
        result = simulate_breeding(PARENT_A, PARENT_B, stimulation=50.0, coi=0.95)
        assert result.novel_birth_defect == approx(1.0)

    def test_class_favoring_skew(self) -> None:
        """If only one parent has a class ability, high stim should guarantee they are picked."""
        cat_a = replace(
            PARENT_A, active_abilities=["BasicMove", "DefaultAttack", "FistOfFate"]
        )  # Class spell
        cat_b = replace(
            PARENT_B, active_abilities=["BasicMove", "DefaultAttack", "Swat"]
        )  # Generic spells

        result = simulate_breeding(cat_a, cat_b, stimulation=100.0, coi=0.0)

        # At 100 stim, favor_class_prob = 1.0.
        # Parent A selection probability should be forced to 1.0.
        # Parent B selection probability should be forced to 0.0.
        assert result.active_abilities.get("Swat", 0.0) == approx(0.0)
        assert result.active_abilities.get("FistOfFate", 0.0) > 0.0

    def test_class_passive_favoring_regression(self) -> None:
        """Regression test: is_class_passive must be used, not is_class_active.

        "Lucky" is in _COLLARLESS_PASSIVES (generic), so is_class_passive returns False.
        But is_class_active checks _COLLARLESS_ACTIVES, not _COLLARLESS_PASSIVES,
        so is_class_active("Lucky") incorrectly returns True.

        At high stim, the bug causes no class favoring to be applied when one parent
        has a class-specific passive and the other has a generic passive.
        """
        cat_a = replace(PARENT_A, passive_abilities=["SkullSmash"])
        cat_b = replace(PARENT_B, passive_abilities=["Lucky"])

        result = simulate_breeding(cat_a, cat_b, stimulation=100.0, coi=0.0)

        # At 100 stim, inherit_passive_prob = 1.0 and favor_class_prob = 1.0.
        # Only Parent A has a class-specific passive (SkullSmash), so:
        # - Parent A select prob = 1.0 (forced by class favoring)
        # - Parent B select prob = 0.0
        # SkullSmash should be inherited with probability 1.0.
        # Lucky (generic) should have 0 probability since Parent B is never selected.
        assert result.passive_abilities.get("SkullSmash", 0.0) == approx(1.0)
        assert result.passive_abilities.get("Lucky", 0.0) == approx(0.0)

    def test_independent_union_overlap(self) -> None:
        """If both parents have the exact same disorder, it should use independent union math."""
        cat_a = replace(PARENT_A, disorders=["Blind"])
        cat_b = replace(PARENT_B, disorders=["Blind"])

        result = simulate_breeding(cat_a, cat_b, stimulation=0.0, coi=0.0)

        # Mom chance = 0.15, Dad chance = 0.15
        # Union = 0.15 + 0.15 - (0.15 * 0.15) = 0.2775
        assert result.inherited_disorders["Blind"] == approx(0.2775)
