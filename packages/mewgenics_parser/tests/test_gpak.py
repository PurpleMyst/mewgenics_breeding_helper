"""Tests for GPAK parsing functions."""

import io

from inline_snapshot import snapshot

from mewgenics_parser.gpak import (
    _clean_game_text,
    _resolve_game_string,
    _parse_gon_abilities,
    load_gpak_text_strings,
)


class TestCleanGameText:
    """Tests for _clean_game_text function."""

    def test_remove_image_tags(self):
        """Remove [img:...] tags."""
        assert _clean_game_text("Hello [img:icon] World") == snapshot("Hello World")

    def test_remove_size_tags(self):
        """Remove [s:...] and [/s] tags."""
        assert _clean_game_text("[s:bold]text[/s] more") == snapshot("text more")

    def test_remove_color_tags(self):
        """Remove [c:...] and [/c] tags."""
        assert _clean_game_text("[c:red]text[/c]") == snapshot("text")

    def test_normalize_whitespace(self):
        """Normalize multiple spaces to single space."""
        assert _clean_game_text("a    b   c") == snapshot("a b c")

    def test_strip_whitespace(self):
        """Strip leading and trailing whitespace."""
        assert _clean_game_text("  hello  ") == snapshot("hello")

    def test_empty_string(self):
        """Handle empty string."""
        assert _clean_game_text("") == snapshot("")

    def test_no_tags(self):
        """Pass through text without tags."""
        assert _clean_game_text("Hello World") == snapshot("Hello World")

    def test_multiple_tags(self):
        """Handle multiple different tags."""
        input_text = "[img:icon] [s:bold]important[/s] [c:red]text[/c]"
        assert _clean_game_text(input_text) == snapshot("important text")


class TestResolveGameString:
    """Tests for _resolve_game_string function."""

    def test_simple_chain(self):
        """Resolve a single level chain."""
        game_strings = {"ABILITY_001": "ABILITY_002", "ABILITY_002": "+1 Damage."}
        result = _resolve_game_string("ABILITY_001", game_strings)
        assert result == snapshot("+1 Damage.")

    def test_deep_chain(self):
        """Resolve a multi-level chain."""
        game_strings = {
            "A": "B",
            "B": "C",
            "C": "Final Value",
        }
        result = _resolve_game_string("A", game_strings)
        assert result == snapshot("Final Value")

    def test_no_chain(self):
        """Return value as-is if not in game_strings."""
        result = _resolve_game_string("direct_value", {})
        assert result == snapshot("direct_value")

    def test_empty_chain(self):
        """Handle empty string as target."""
        game_strings = {"KEY": ""}
        result = _resolve_game_string("KEY", game_strings)
        assert result == snapshot("KEY")

    def test_circular_reference(self):
        """Protect against circular references."""
        game_strings = {"A": "B", "B": "A"}
        result = _resolve_game_string("A", game_strings)
        assert result == snapshot("A")

    def test_self_reference(self):
        """Handle self-referencing key."""
        game_strings = {"KEY": "KEY"}
        result = _resolve_game_string("KEY", game_strings)
        assert result == snapshot("KEY")

    def test_whitespace_handling(self):
        """Handle whitespace in resolved values."""
        game_strings = {"KEY": "  value  "}
        result = _resolve_game_string("KEY", game_strings)
        assert result == snapshot("value")


class TestParseGonAbilities:
    """Tests for _parse_gon_abilities function."""

    def test_simple_ability(self):
        """Parse a simple ability with desc."""
        gon = """Slugger {
    desc "slugger_desc"
    damage 1
}
"""
        result = _parse_gon_abilities(gon, {})
        assert result == snapshot({"slugger": "slugger_desc"})

    def test_ability_with_game_string_reference(self):
        """Parse ability with game string reference."""
        game_strings = {"slugger_desc": "Final description"}
        gon = 'Slugger { desc "slugger_desc" }'
        result = _parse_gon_abilities(gon, game_strings)
        assert result == snapshot({"slugger": "Final description"})

    def test_ignores_nothing_desc(self):
        """Ignore abilities with 'nothing' desc."""
        gon = 'Junk { desc "nothing" }'
        result = _parse_gon_abilities(gon, {})
        assert result == snapshot({})

    def test_multiple_abilities(self):
        """Parse multiple abilities."""
        gon = """
Slugger {
    desc "slugger_desc"
    damage 1
}
Longshot {
    desc "longshot_desc"
    range 1
}
"""
        result = _parse_gon_abilities(gon, {})
        assert result == snapshot(
            {
                "slugger": "slugger_desc",
                "longshot": "longshot_desc",
            }
        )

    def test_empty_content(self):
        """Handle empty GON content."""
        result = _parse_gon_abilities("", {})
        assert result == snapshot({})

    def test_no_desc_field(self):
        """Ignore blocks without desc field."""
        gon = "Slugger { damage 1 }"
        result = _parse_gon_abilities(gon, {})
        assert result == snapshot({})

    def test_case_preservation(self):
        """Ability IDs should be lowercased."""
        gon = 'Slugger { desc "desc" }\nFURIOUS { desc "desc2" }'
        result = _parse_gon_abilities(gon, {})
        keys = list(result.keys())
        assert keys == snapshot(["slugger", "furious"])


class TestLoadGpakTextStrings:
    """Tests for load_gpak_text_strings function."""

    def test_simple_csv(self):
        """Parse simple CSV file."""
        csv_content = "key,value\nABILITY_001,+1 Damage."
        file_offsets = {"data/text/strings.csv": (0, len(csv_content))}

        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        result = load_gpak_text_strings(file_obj, file_offsets)
        assert result == snapshot({"key": "value", "ABILITY_001": "+1 Damage."})

    def test_ignores_non_csv_files(self):
        """Ignore non-CSV files."""
        file_offsets = {"data/abilities/slugger.gon": (0, 100)}

        file_obj = io.BytesIO(b"some content")
        result = load_gpak_text_strings(file_obj, file_offsets)
        assert result == snapshot({})

    def test_ignores_comment_lines(self):
        """Ignore comment lines starting with //."""
        csv_content = "//comment\nkey,value\nABILITY_001,desc"
        file_offsets = {"data/text/strings.csv": (0, len(csv_content))}

        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        result = load_gpak_text_strings(file_obj, file_offsets)
        assert result == snapshot({"key": "value", "ABILITY_001": "desc"})

    def test_ignores_empty_keys(self):
        """Ignore rows with empty keys."""
        csv_content = ",value\nkey,value"
        file_offsets = {"data/text/strings.csv": (0, len(csv_content))}

        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        result = load_gpak_text_strings(file_obj, file_offsets)
        assert result == snapshot({"key": "value"})
