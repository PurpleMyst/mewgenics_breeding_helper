from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender, CatStatus, CatBodyParts, Stats
from mewgenics_scorer.ancestry import (
    build_ancestor_contribs,
    coi_from_contribs,
)


def make_cat(
    db_key: int,
    parent_a: Cat | None = None,
    parent_b: Cat | None = None,
    coi: float = 0.0,
) -> Cat:
    return Cat(
        db_key=db_key,
        name=f"Cat_{db_key}",
        gender=CatGender.MALE,
        status=CatStatus.IN_HOUSE,
        room=None,
        stat_base=Stats(5, 5, 5, 5, 5, 5, 5),
        stat_total=Stats(5, 5, 5, 5, 5, 5, 5),
        age=0,
        aggression=0.5,
        libido=0.5,
        coi=coi,
        active_abilities=[],
        passive_abilities=[],
        disorders=[],
        body_parts=CatBodyParts(
            texture=0,
            body=0,
            head=0,
            tail=0,
            legs=0,
            arms=0,
            eyes=0,
            eyebrows=0,
            ears=0,
            mouth=0,
        ),
        parent_a=parent_a,
        parent_b=parent_b,
        lovers=[],
        haters=[],
    )


class TestMewgenicsSpecificMechanics:
    """Tests designed to enforce the quirky rules of the Mewgenics universe."""

    def test_stray_always_zero_coi(self):
        """Strays have no parents (None). Breeding two strays must yield 0 COI."""
        stray_1 = make_cat(1)
        stray_2 = make_cat(2)

        ca = build_ancestor_contribs([stray_1])[1]
        cb = build_ancestor_contribs([stray_2])[2]

        assert coi_from_contribs(ca, cb) == 0.0

    def test_closeness_five_cutoff(self):
        """
        Tests the Mewgenics rule: "If that same parent breeds with the
        great-great-great-grandchild (Closeness of 5), the child... will not be Inbred."
        """
        # Generation 0
        stray_parent = make_cat(1)
        other_stray = make_cat(2)

        # Straight ladder down
        gen_1 = make_cat(3, parent_a=stray_parent, parent_b=other_stray)  # Child
        gen_2 = make_cat(4, parent_a=gen_1, parent_b=other_stray)  # Grandchild
        gen_3 = make_cat(5, parent_a=gen_2, parent_b=other_stray)  # Great-grandchild
        gen_4 = make_cat(
            6, parent_a=gen_3, parent_b=other_stray
        )  # Great-great-grandchild
        gen_5 = make_cat(
            7, parent_a=gen_4, parent_b=other_stray
        )  # Great-great-great-grandchild

        # Breeding Stray Parent with Gen 5 should result in a Closeness of 5.
        contribs = build_ancestor_contribs(
            [stray_parent, other_stray, gen_1, gen_2, gen_3, gen_4, gen_5]
        )

        coi_closeness_4 = coi_from_contribs(
            contribs[1], contribs[6]
        )  # Breeds with Gen 4
        coi_closeness_5 = coi_from_contribs(
            contribs[1], contribs[7]
        )  # Breeds with Gen 5

        assert coi_closeness_4 > 0.0, "Closeness 4 should be inbred."
        assert coi_closeness_5 == 0.0, (
            "Closeness 5 must drop off completely per Mewgenics rules."
        )

    def test_ancestor_inbreeding_multiplier_fa(self):
        """
        Tests the fA part of the equation.
        If the common ancestor is heavily inbred, the child's COI should be higher
        than if the common ancestor was a stray (twisted ladder vs straight ladder).
        """
        # Scenario A: Common ancestor is a Stray (fA = 0)
        pure_ancestor = make_cat(1, coi=0.0)
        pure_parent_a = make_cat(2, parent_a=pure_ancestor)
        pure_parent_b = make_cat(3, parent_a=pure_ancestor)

        # Scenario B: Common ancestor is highly inbred (fA > 0)
        inbred_ancestor = make_cat(4, coi=0.5)
        inbred_parent_a = make_cat(5, parent_a=inbred_ancestor)
        inbred_parent_b = make_cat(6, parent_a=inbred_ancestor)

        cats = [
            pure_ancestor,
            pure_parent_a,
            pure_parent_b,
            inbred_ancestor,
            inbred_parent_a,
            inbred_parent_b,
        ]
        contribs = build_ancestor_contribs(cats)

        coi_from_pure = coi_from_contribs(contribs[2], contribs[3])
        coi_from_inbred = coi_from_contribs(contribs[5], contribs[6])

        # The equation states: N * 0.5^(n-1) * (1 + fA)
        # Therefore, the COI from the inbred ancestor MUST be higher.
        assert coi_from_inbred > coi_from_pure, (
            "The fA multiplier is missing; heavily inbred ancestors should amplify the COI."
        )


class TestComplexFamilyTrees:
    """Tests for twisted ladders and multiple common ancestors."""

    def test_twisted_ladder_multiple_common_ancestors(self):
        """A child whose parents share MULTIPLE ancestors should sum the loops."""
        stray_1 = make_cat(1)
        stray_2 = make_cat(2)

        # Full siblings breeding
        sibling_1 = make_cat(3, parent_a=stray_1, parent_b=stray_2)
        sibling_2 = make_cat(4, parent_a=stray_1, parent_b=stray_2)

        contribs = build_ancestor_contribs([stray_1, stray_2, sibling_1, sibling_2])

        ca = contribs[3]
        cb = contribs[4]

        # They share TWO common ancestors (stray 1 and stray 2).
        # Calculation:
        # Loop 1 (Stray 1): depth_a=1, depth_b=1 -> n=4 -> 0.5^(3) * (1+0) = 0.125
        # Loop 2 (Stray 2): depth_a=1, depth_b=1 -> n=4 -> 0.5^(3) * (1+0) = 0.125
        # Total CoI = 0.25
        assert coi_from_contribs(ca, cb) == 0.25
