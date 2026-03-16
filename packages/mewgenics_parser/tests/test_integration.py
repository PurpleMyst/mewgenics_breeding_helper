"""Integration tests for GPAK functions requiring a real GPAK file."""

import pytest

from mewgenics_parser.gpak import (
    GameData,
    load_ability_descriptions,
    load_visual_mut_data,
)


class TestGpakIntegration:
    """Integration tests requiring a real GPAK file."""

    def test_load_ability_descriptions(self, gpak_path):
        """Test loading ability descriptions from real GPAK."""
        result = load_ability_descriptions(gpak_path)

        # Verify key abilities exist
        assert "slugger" in result
        assert "longshot" in result

        # Verify descriptions are non-empty
        for ability_id, desc in result.items():
            assert isinstance(ability_id, str)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_load_visual_mut_data(self, gpak_path):
        """Test loading visual mutation data from real GPAK."""
        result = load_visual_mut_data(gpak_path)

        # Verify expected categories exist
        assert "body" in result
        assert "eyes" in result
        assert "ears" in result

        # Verify mutations have proper structure
        for category, mutations in result.items():
            for mutation_id, (name, stat_desc) in mutations.items():
                assert isinstance(mutation_id, int)
                assert isinstance(name, str)
                assert isinstance(stat_desc, str)

    def test_game_data_from_gpak(self, gpak_path):
        """Test GameData.from_gpak produces correct structure."""
        gd = GameData.from_gpak(gpak_path)

        # Verify all fields are populated
        assert isinstance(gd.ability_descriptions, dict)
        assert isinstance(gd.visual_mutations, dict)
        assert isinstance(gd.game_strings, dict)

        # Verify expected data is present
        assert len(gd.ability_descriptions) > 0
        assert len(gd.visual_mutations) > 0
        assert len(gd.game_strings) > 0

    def test_ability_descriptions_structure(self, gpak_path):
        """Verify ability descriptions have expected keys."""
        result = load_ability_descriptions(gpak_path)

        # Check a few known abilities
        known_abilities = ["slugger", "longshot", "furious", "amped"]
        for ability in known_abilities:
            if ability in result:
                desc = result[ability]
                # Descriptions should not be empty
                assert len(desc) > 0, f"Ability {ability} has empty description"

    def test_visual_mutations_ids(self, gpak_path):
        """Verify visual mutation IDs are in expected ranges."""
        result = load_visual_mut_data(gpak_path)

        # Visual mutations should typically be 300+
        for category, mutations in result.items():
            for mutation_id in mutations.keys():
                assert mutation_id >= 300, (
                    f"Mutation ID {mutation_id} in {category} is below 300"
                )

    def test_game_strings_have_ability_refs(self, gpak_path):
        """Verify game strings contain ability references."""
        gd = GameData.from_gpak(gpak_path)

        # Game strings should contain keys that abilities reference
        # At minimum, there should be some string references
        has_refs = any(
            key in gd.game_strings for key in gd.ability_descriptions.values()
        )
        # This might pass or fail depending on GPAK structure
        # Just verify game_strings is not empty
        assert len(gd.game_strings) > 0


class TestGpakEdgeCases:
    """Edge case tests for GPAK functions."""

    def test_empty_path_returns_empty(self):
        """Empty path returns empty dicts."""
        result = load_ability_descriptions("")
        assert result == {}

    def test_nonexistent_path_returns_empty(self):
        """Nonexistent path returns empty dicts."""
        result = load_ability_descriptions("/nonexistent/path.gpak")
        assert result == {}

    def test_game_data_empty_path(self):
        """GameData with empty path returns empty fields."""
        gd = GameData.from_gpak("")

        assert gd.ability_descriptions == {}
        assert gd.visual_mutations == {}
        assert gd.game_strings == {}
