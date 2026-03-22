"""Integration tests for GPAK functions requiring a real GPAK file."""

from inline_snapshot import snapshot
from dirty_equals import IsInt

from mewgenics_parser import parse_save
from mewgenics_parser.cat import CatBodyPartCategory, CatGender, CatStatus, CatBodySlot
from mewgenics_parser.gpak import GameData
from mewgenics_parser.utils import NameAndDescription

from mewgenics_parser.cat import Stats


class TestParseSaveIntegration:
    """Integration tests for parse_save requiring a real save file."""

    def test_cat_from_save(self, savefile_path):
        """Test Cat.from_gpak produces correct structure."""
        save = parse_save(savefile_path)
        cat = next(c for c in save.cats if "myst".casefold() in c.name.casefold())
        assert cat.db_key == snapshot(819)
        assert cat.name == snapshot("Myst")
        assert cat.gender == snapshot(CatGender.FEMALE)
        assert cat.sexuality == snapshot(0.08160075767255394)
        assert cat.libido == snapshot(0.6100491969838884)
        assert cat.status == snapshot(CatStatus.GONE)
        assert cat.room == snapshot(None)
        assert cat.stat_base == snapshot(
            Stats(
                strength=7,
                dexterity=7,
                constitution=6,
                intelligence=7,
                speed=7,
                charisma=7,
                luck=6,
            )
        )
        assert cat.stat_total == snapshot(
            Stats(
                strength=12,
                dexterity=9,
                constitution=11,
                intelligence=8,
                speed=10,
                charisma=8,
                luck=9,
            )
        )
        assert cat.age == snapshot(IsInt())
        assert cat.aggression == snapshot(0.9648030361579043)
        assert cat.libido == snapshot(0.6100491969838884)
        assert cat.active_abilities == snapshot(
            ["BasicButcherMelee", "Burp2", "Rally", "Grill", "Butcher"]
        )
        assert cat.passive_abilities == snapshot(["Masochist", "DukeOfFlies"])
        assert cat.disorders == snapshot([])
        assert cat.body_parts == snapshot(
            {
                CatBodySlot.TEXTURE: 304,
                CatBodySlot.BODY: 900,
                CatBodySlot.HEAD: 900,
                CatBodySlot.TAIL: 900,
                CatBodySlot.LEFT_LEG: 900,
                CatBodySlot.RIGHT_LEG: 900,
                CatBodySlot.LEFT_ARM: 900,
                CatBodySlot.RIGHT_ARM: 900,
                CatBodySlot.LEFT_EYE: 900,
                CatBodySlot.RIGHT_EYE: 900,
                CatBodySlot.LEFT_EYEBROW: 900,
                CatBodySlot.RIGHT_EYEBROW: 900,
                CatBodySlot.LEFT_EAR: 900,
                CatBodySlot.RIGHT_EAR: 900,
                CatBodySlot.MOUTH: 900,
            }
        )
        assert cat.parent_a is not None
        assert cat.parent_b is not None
        assert cat.parent_a.db_key == snapshot(700)
        assert cat.parent_b.db_key == snapshot(781)
        assert cat.lover_id == snapshot(821)
        assert cat.hater_id == snapshot(766)


class TestGpakIntegration:
    """Integration tests requiring a real GPAK file."""

    def test_game_data_from_gpak(self, gpak_path):
        """Test GameData.from_gpak produces correct structure."""
        gd = GameData.from_gpak(gpak_path)

        # Verify all fields are populated
        assert isinstance(gd.ability_text, dict)
        assert isinstance(gd.body_part_text, dict)
        assert isinstance(gd.game_strings, dict)

        # Verify expected data is present
        assert len(gd.ability_text) > 0
        assert len(gd.body_part_text) > 0
        assert len(gd.game_strings) > 0

    def test_known_abilities(self, gpak_path):
        """Verify known abilities have expected descriptions from real GPAK."""
        gd = GameData.from_gpak(gpak_path)
        result = gd.ability_text

        assert result["Slugger"] == snapshot(
            NameAndDescription(name="Slugger", description="+1 Damage.")
        )
        assert result["LongShot"] == snapshot(
            NameAndDescription(name="Longshot", description="+1 Range.")
        )
        assert result["Furious"] == snapshot(
            NameAndDescription(
                name="Furious",
                description="Gain +1 Damage each time you land a critical hit. +5% critical hit chance.",
            )
        )
        assert result["Amped"] == snapshot(
            NameAndDescription(
                name="Amped", description="Gain +1 SPD at the end of your turn."
            )
        )

    def test_visual_mutations_structure(self, gpak_path):
        """Test visual mutation data from real GPAK."""
        gd = GameData.from_gpak(gpak_path)
        result = gd.body_part_text
        assert list(result.keys()) == snapshot(
            [
                CatBodyPartCategory.BODY,
                CatBodyPartCategory.EARS,
                CatBodyPartCategory.EYEBROWS,
                CatBodyPartCategory.EYES,
                CatBodyPartCategory.HEAD,
                CatBodyPartCategory.LEGS,
                CatBodyPartCategory.MOUTH,
                CatBodyPartCategory.TAIL,
                CatBodyPartCategory.TEXTURE,
            ]
        )

    def test_known_visual_mutation(self, gpak_path):
        """Verify known visual mutation has expected description from real GPAK."""
        gd = GameData.from_gpak(gpak_path)
        result = gd.body_part_text

        assert result[CatBodyPartCategory.EYES][303] == snapshot(
            NameAndDescription(name="Gem Eyes", description="+1 INT, +1 CHA")
        )
        assert result[CatBodyPartCategory.EYES][306] == snapshot(
            NameAndDescription(
                name="Confusing Eyes",
                description="Your basic attack has a 10% chance to inflict Confusion 3.",
            )
        )
        assert result[CatBodyPartCategory.EYES][706] == snapshot(
            NameAndDescription(
                name="Crossed Eyes", description="Start each battle with Confusion 2."
            )
        )
