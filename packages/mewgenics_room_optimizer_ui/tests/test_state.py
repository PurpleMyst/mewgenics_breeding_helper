"""Tests for state module."""

import json
import tempfile
from pathlib import Path

from mewgenics_parser.traits import TraitCategory, create_trait
from mewgenics_scorer import ScoringPreferences, TraitRequirement

from mewgenics_room_optimizer_ui.state import ConfigModel


class TestConfigModelTraitRequirements:
    """Tests for ConfigModel trait_requirements parsing and serialization."""

    def test_parse_trait_requirements_from_dict(self) -> None:
        """Test parsing trait_requirements from list of dicts."""
        data = {
            "version": 1,
            "rooms": [],
            "trait_requirements": [
                {"category": "passive_ability", "key": "Sturdy", "weight": 7.0},
                {"category": "active_ability", "key": "PathOfTheHunter"},
            ],
            "min_stats": 0,
            "max_risk": 20.0,
        }
        config = ConfigModel.model_validate(data)

        assert len(config.trait_requirements) == 2
        assert (
            config.trait_requirements[0].trait.category == TraitCategory.PASSIVE_ABILITY
        )
        assert config.trait_requirements[0].trait.key == "Sturdy"
        assert config.trait_requirements[0].weight == 7.0
        assert (
            config.trait_requirements[1].trait.category == TraitCategory.ACTIVE_ABILITY
        )
        assert config.trait_requirements[1].trait.key == "PathOfTheHunter"
        assert config.trait_requirements[1].weight == 5.0

    def test_serialize_trait_requirements_to_dict(self) -> None:
        """Test serializing trait_requirements back to dicts."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        config = ConfigModel(
            trait_requirements=[
                TraitRequirement(trait=trait1, weight=7.0),
                TraitRequirement(trait=trait2, weight=3.0),
            ],
        )

        serialized = config.model_dump()
        assert len(serialized["trait_requirements"]) == 2
        assert serialized["trait_requirements"][0] == {
            "category": "passive_ability",
            "key": "Sturdy",
            "weight": 7.0,
        }
        assert serialized["trait_requirements"][1] == {
            "category": "active_ability",
            "key": "PathOfTheHunter",
            "weight": 3.0,
        }

    def test_serialize_trait_requirements_to_json(self) -> None:
        """Test serializing to JSON (used by save())."""
        trait = create_trait(TraitCategory.DISORDER, "Fading")
        config = ConfigModel(
            trait_requirements=[TraitRequirement(trait=trait, weight=10.0)],
        )

        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["trait_requirements"][0]["category"] == "disorder"
        assert data["trait_requirements"][0]["key"] == "Fading"
        assert data["trait_requirements"][0]["weight"] == 10.0

    def test_roundtrip_trait_requirements(self) -> None:
        """Test full load/save roundtrip of trait_requirements."""
        trait1 = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
        trait2 = create_trait(TraitCategory.BODY_PART, " CURLICUE ")
        original = ConfigModel(
            trait_requirements=[
                TraitRequirement(trait=trait1, weight=7.0),
                TraitRequirement(trait=trait2, weight=2.5),
            ],
        )

        json_str = original.model_dump_json()
        reloaded = ConfigModel.model_validate_json(json_str)

        assert len(reloaded.trait_requirements) == 2
        assert (
            reloaded.trait_requirements[0].trait.category
            == TraitCategory.PASSIVE_ABILITY
        )
        assert reloaded.trait_requirements[0].trait.key == "Sturdy"
        assert reloaded.trait_requirements[0].weight == 7.0
        assert reloaded.trait_requirements[1].trait.category == TraitCategory.BODY_PART
        assert reloaded.trait_requirements[1].trait.key == " CURLICUE "
        assert reloaded.trait_requirements[1].weight == 2.5

    def test_empty_trait_requirements(self) -> None:
        """Test handling empty trait_requirements list."""
        config = ConfigModel.model_validate({"version": 1, "rooms": []})
        assert config.trait_requirements == []

    def test_trait_requirements_default_weight(self) -> None:
        """Test that missing weight defaults to 5.0."""
        data = {
            "version": 1,
            "rooms": [],
            "trait_requirements": [{"category": "passive_ability", "key": "Sturdy"}],
        }
        config = ConfigModel.model_validate(data)
        assert config.trait_requirements[0].weight == 5.0

    def test_arbitrary_types_allowed(self) -> None:
        """Test that arbitrary_types_allowed allows Trait objects."""
        trait = create_trait(TraitCategory.ACTIVE_ABILITY, "PathOfTheHunter")
        config = ConfigModel(
            trait_requirements=[TraitRequirement(trait=trait, weight=5.0)],
        )
        assert config.trait_requirements[0].trait.key == "PathOfTheHunter"


class TestConfigModelFullRoundtrip:
    """Tests for full ConfigModel save/load with temp file."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading a complete ConfigModel."""
        from mewgenics_room_optimizer import DEFAULT_ROOM_CONFIGS

        original = ConfigModel(
            version=1,
            rooms=list(DEFAULT_ROOM_CONFIGS),
            trait_requirements=[
                TraitRequirement(
                    trait=create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy"),
                    weight=8.0,
                ),
            ],
            last_save_path="test.gpak",
            min_stats=10,
            max_risk=25.0,
            scoring_prefs=ScoringPreferences(
                minimize_variance=True,
                prefer_high_libido=True,
            ),
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=tmp_path
        ) as f:
            f.write(original.model_dump_json(indent=2))
            temp_path = Path(f.name)

        loaded = ConfigModel.model_validate_json(temp_path.read_text())

        assert loaded.version == original.version
        assert loaded.min_stats == original.min_stats
        assert loaded.max_risk == original.max_risk
        assert loaded.last_save_path == original.last_save_path
        assert (
            loaded.scoring_prefs.minimize_variance
            == original.scoring_prefs.minimize_variance
        )
        assert len(loaded.trait_requirements) == 1
        assert loaded.trait_requirements[0].trait.key == "Sturdy"
        assert loaded.trait_requirements[0].weight == 8.0
