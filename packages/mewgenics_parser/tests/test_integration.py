"""Integration tests for GPAK functions requiring a real GPAK file."""

from inline_snapshot import snapshot
from dirty_equals import IsInt

from mewgenics_parser import parse_save
from mewgenics_parser.cat import CatGender, CatStatus
from mewgenics_parser.gpak import GameData
from mewgenics_parser.utils import NameAndDescription

from mewgenics_parser.cat import CatBodyParts


class TestParseSaveIntegration:
    """Integration tests for parse_save requiring a real save file."""

    def test_cat_from_save(self, savefile_path):
        """Test Cat.from_gpak produces correct structure."""
        save = parse_save(savefile_path)
        cat = save.cats[0]
        assert cat.db_key == snapshot(1)
        assert cat.name == snapshot("Andrzej")
        assert cat.gender == snapshot(CatGender.MALE)
        assert cat.status == snapshot(CatStatus.GONE)
        assert cat.room == snapshot(None)
        assert cat.stat_base == snapshot((6, 4, 7, 5, 6, 3, 4))
        assert cat.stat_total == snapshot((6, 4, 7, 6, 6, 3, 4))
        assert cat.age == snapshot(IsInt())
        assert cat.aggression == snapshot(0.47115162183106574)
        assert cat.libido == snapshot(0.5)
        assert cat.coi == snapshot(0.05)
        assert cat.active_abilities == snapshot(["BasicMelee", "Spit", "Block"])
        assert cat.passive_abilities == snapshot(["SelfAssured"])
        assert cat.disorders == snapshot([])
        assert cat.body_parts == snapshot(
            CatBodyParts(
                texture=54,
                body=19,
                head=46,
                tail=153,
                legs=45,
                arms=45,
                eyes=133,
                eyebrows=26,
                ears=7,
                mouth=50,
            )
        )
        assert cat.parent_a == snapshot(None)
        assert cat.parent_b == snapshot(None)
        assert cat.lovers == snapshot([])
        assert cat.haters == snapshot([])


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
                "body",
                "ears",
                "eyebrows",
                "eyes",
                "head",
                "legs",
                "mouth",
                "tail",
                "texture",
                "arms",
            ]
        )

    def test_known_visual_mutation(self, gpak_path):
        """Verify known visual mutation has expected description from real GPAK."""
        gd = GameData.from_gpak(gpak_path)
        result = gd.body_part_text

        assert result["eyes"][303] == snapshot(
            NameAndDescription(name="Gem Eyes", description="+1 INT, +1 CHA")
        )
        assert result["eyes"][306] == snapshot(
            NameAndDescription(
                name="Confusing Eyes",
                description="Your basic attack has a 10% chance to inflict Confusion 3.",
            )
        )
        assert result["eyes"][706] == snapshot(
            NameAndDescription(
                name="Crossed Eyes", description="Start each battle with Confusion 2."
            )
        )
