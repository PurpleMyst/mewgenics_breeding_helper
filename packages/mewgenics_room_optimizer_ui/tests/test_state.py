"""Tests for state module."""

import tempfile
from pathlib import Path

from mewgenics_parser.traits import TraitCategory, create_trait
from mewgenics_scorer.types import TargetBuild, TraitWeight

from mewgenics_room_optimizer_ui.state import ConfigModel


class TestConfigModelUniversals:
    """Tests for ConfigModel universals parsing and serialization."""

    def test_parse_universals_from_dict(self) -> None:
        """Test parsing universals from list of dicts."""
        data = {
            "version": 1,
            "rooms": [],
            "universals": [
                {"category": "passive_ability", "key": "Sturdy", "weight_ens": 7.0},
                {
                    "category": "active_ability",
                    "key": "PathOfTheHunter",
                    "weight_ens": 2.0,
                },
            ],
            "target_builds": [],
            "last_save_path": None,
        }
        config = ConfigModel.model_validate(data)

        assert len(config.universals) == 2
        assert config.universals[0].trait.category == TraitCategory.PASSIVE_ABILITY
        assert config.universals[0].trait.key == "Sturdy"
        assert config.universals[0].weight_ens == 7.0
        assert config.universals[1].trait.category == TraitCategory.ACTIVE_ABILITY
        assert config.universals[1].trait.key == "PathOfTheHunter"
        assert config.universals[1].weight_ens == 2.0

    def test_serialize_universals_to_dict(self) -> None:
        """Test serializing universals back to dicts."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        config = ConfigModel(
            universals=[
                TraitWeight(trait=trait1, weight_ens=7.0),
                TraitWeight(trait=trait2, weight_ens=3.0),
            ],
            target_builds=[],
        )

        serialized = config.model_dump()
        assert len(serialized["universals"]) == 2
        assert serialized["universals"][0] == {
            "category": "passive_ability",
            "key": "Sturdy",
            "weight_ens": 7.0,
        }
        assert serialized["universals"][1] == {
            "category": "active_ability",
            "key": "PathOfTheHunter",
            "weight_ens": 3.0,
        }

    def test_roundtrip_universals(self) -> None:
        """Test full load/save roundtrip of universals."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.BODY_PART, "Eyes300")
        original = ConfigModel(
            universals=[
                TraitWeight(trait=trait1, weight_ens=7.0),
                TraitWeight(trait=trait2, weight_ens=2.5),
            ],
            target_builds=[],
        )

        json_str = original.model_dump_json()
        reloaded = ConfigModel.model_validate_json(json_str)

        assert len(reloaded.universals) == 2
        assert reloaded.universals[0].trait.category == TraitCategory.PASSIVE_ABILITY
        assert reloaded.universals[0].trait.key == "Sturdy"
        assert reloaded.universals[0].weight_ens == 7.0
        assert reloaded.universals[1].trait.category == TraitCategory.BODY_PART
        assert reloaded.universals[1].trait.key == "Eyes300"
        assert reloaded.universals[1].weight_ens == 2.5

    def test_empty_universals(self) -> None:
        """Test handling empty universals list."""
        config = ConfigModel.model_validate(
            {"version": 1, "rooms": [], "universals": [], "target_builds": []}
        )
        assert config.universals == []

    def test_universals_default_weight(self) -> None:
        """Test that missing weight_ens defaults to 1.0."""
        data = {
            "version": 1,
            "rooms": [],
            "universals": [{"category": "passive_ability", "key": "Sturdy"}],
            "target_builds": [],
        }
        config = ConfigModel.model_validate(data)
        assert config.universals[0].weight_ens == 1.0


class TestConfigModelTargetBuilds:
    """Tests for ConfigModel target_builds parsing and serialization."""

    def test_parse_target_builds_from_dict(self) -> None:
        """Test parsing target_builds from list of dicts."""
        data = {
            "version": 1,
            "rooms": [],
            "universals": [],
            "target_builds": [
                {
                    "name": "Tank Build",
                    "requirements": [
                        {
                            "category": "passive_ability",
                            "key": "Sturdy",
                            "weight_ens": 3.0,
                        },
                    ],
                    "anti_synergies": [
                        {"category": "disorder", "key": "Fading", "weight_ens": 5.0},
                    ],
                    "synergy_bonus_ens": 2.0,
                },
            ],
            "last_save_path": None,
        }
        config = ConfigModel.model_validate(data)

        assert len(config.target_builds) == 1
        assert config.target_builds[0].name == "Tank Build"
        assert len(config.target_builds[0].requirements) == 1
        assert config.target_builds[0].requirements[0].trait.key == "Sturdy"
        assert config.target_builds[0].requirements[0].weight_ens == 3.0
        assert len(config.target_builds[0].anti_synergies) == 1
        assert config.target_builds[0].anti_synergies[0].trait.key == "Fading"
        assert config.target_builds[0].synergy_bonus_ens == 2.0

    def test_serialize_target_builds_to_dict(self) -> None:
        """Test serializing target_builds back to dicts."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.DISORDER, "Fading")
        config = ConfigModel(
            universals=[],
            target_builds=[
                TargetBuild(
                    name="Tank Build",
                    requirements=[TraitWeight(trait=trait1, weight_ens=3.0)],
                    anti_synergies=[TraitWeight(trait=trait2, weight_ens=5.0)],
                    synergy_bonus_ens=2.0,
                ),
            ],
        )

        serialized = config.model_dump()
        assert len(serialized["target_builds"]) == 1
        assert serialized["target_builds"][0]["name"] == "Tank Build"
        assert serialized["target_builds"][0]["requirements"][0] == {
            "category": "passive_ability",
            "key": "Sturdy",
            "weight_ens": 3.0,
        }
        assert serialized["target_builds"][0]["anti_synergies"][0] == {
            "category": "disorder",
            "key": "Fading",
            "weight_ens": 5.0,
        }
        assert serialized["target_builds"][0]["synergy_bonus_ens"] == 2.0

    def test_roundtrip_target_builds(self) -> None:
        """Test full load/save roundtrip of target_builds."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        original = ConfigModel(
            universals=[],
            target_builds=[
                TargetBuild(
                    name="Tank Build",
                    requirements=[TraitWeight(trait=trait1, weight_ens=3.0)],
                    anti_synergies=[],
                    synergy_bonus_ens=2.0,
                ),
            ],
        )

        json_str = original.model_dump_json()
        reloaded = ConfigModel.model_validate_json(json_str)

        assert len(reloaded.target_builds) == 1
        assert reloaded.target_builds[0].name == "Tank Build"
        assert reloaded.target_builds[0].requirements[0].trait.key == "Sturdy"
        assert reloaded.target_builds[0].requirements[0].weight_ens == 3.0
        assert reloaded.target_builds[0].synergy_bonus_ens == 2.0

    def test_empty_target_builds(self) -> None:
        """Test handling empty target_builds list."""
        config = ConfigModel.model_validate(
            {"version": 1, "rooms": [], "universals": [], "target_builds": []}
        )
        assert config.target_builds == []


class TestConfigModelFullRoundtrip:
    """Tests for full ConfigModel save/load with temp file."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading a complete ConfigModel."""
        from mewgenics_room_optimizer import DEFAULT_ROOM_CONFIGS

        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.BODY_PART, "Eyes300")
        original = ConfigModel(
            version=1,
            rooms=list(DEFAULT_ROOM_CONFIGS),
            universals=[
                TraitWeight(trait=trait1, weight_ens=8.0),
            ],
            target_builds=[
                TargetBuild(
                    name="Build 1",
                    requirements=[TraitWeight(trait=trait2, weight_ens=2.0)],
                    anti_synergies=[],
                    synergy_bonus_ens=1.0,
                ),
            ],
            last_save_path="test.gpak",
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=tmp_path
        ) as f:
            f.write(original.model_dump_json(indent=2))
            temp_path = Path(f.name)

        loaded = ConfigModel.model_validate_json(temp_path.read_text())

        assert loaded.version == original.version
        assert loaded.last_save_path == original.last_save_path
        assert len(loaded.universals) == 1
        assert loaded.universals[0].trait.key == "Sturdy"
        assert loaded.universals[0].weight_ens == 8.0
        assert len(loaded.target_builds) == 1
        assert loaded.target_builds[0].name == "Build 1"
        assert loaded.target_builds[0].requirements[0].trait.key == "Eyes300"
