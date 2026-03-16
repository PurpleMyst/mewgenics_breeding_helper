"""Tests for visual mutation parsing functions."""

from inline_snapshot import snapshot

from mewgenics_parser.visual import (
    _parse_mutation_gon,
    _read_visual_mutation_entries,
    _visual_mutation_chip_items,
)


class TestParseMutationGon:
    """Tests for _parse_mutation_gon function."""

    def test_simple_mutation(self):
        """Parse simple mutation with comment."""
        gon = """300 {
    // Rock Bod
    str 2
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({300: ("Rock Bod", "+2 STR")})

    def test_multiple_stats(self):
        """Parse mutation with multiple stats."""
        gon = """301 {
    // Cactus Bod
    str 1
    dex -1
    con 2
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({301: ("Cactus Bod", "+1 STR, +2 CON, -1 DEX")})

    def test_ignores_below_300(self):
        """Ignore mutations below ID 300."""
        gon = """100 {
    // Too low
    str 1
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({})

    def test_with_game_string_reference(self):
        """Resolve mutation stats from game strings."""
        game_strings = {"MUTATION_BODY_300_DESC": "MUTATION_BODY_300_FINAL"}
        game_strings["MUTATION_BODY_300_FINAL"] = "+2 STR, +1 DEX"
        gon = """300 {
    // Rock Bod
    str 2
    dex 1
}
"""
        result = _parse_mutation_gon(gon, game_strings, "body")
        assert result == snapshot({300: ("Rock Bod", "+2 STR, +1 DEX")})

    def test_no_comment_uses_default_name(self):
        """Use default name when no comment."""
        gon = """300 {
    str 2
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({300: ("Mutation 300", "+2 STR")})

    def test_empty_stat_list(self):
        """Handle mutation with no stats."""
        gon = """300 {
    // Just a name
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({300: ("Just A Name", "")})

    def test_category_in_csv_key(self):
        """Use correct CSV key for category."""
        game_strings = {"MUTATION_EYES_500_DESC": "Night Vision"}
        gon = """500 {
    // Night Eyes
}
"""
        result = _parse_mutation_gon(gon, game_strings, "eyes")
        assert result == snapshot({500: ("Night Eyes", "Night Vision")})

    def test_multiple_mutations(self):
        """Parse multiple mutations in one file."""
        gon = """300 {
    // Rock Bod
    str 2
}
301 {
    // Cactus Bod
    dex 1
}
302 {
    // Turtle Bod
    con 3
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot(
            {
                300: ("Rock Bod", "+2 STR"),
                301: ("Cactus Bod", "+1 DEX"),
                302: ("Turtle Bod", "+3 CON"),
            }
        )

    def test_negative_stats(self):
        """Handle negative stat values."""
        gon = """300 {
    // Weak Bod
    str -2
    dex -1
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot({300: ("Weak Bod", "-2 STR, -1 DEX")})

    def test_all_stats(self):
        """Handle all stat types."""
        gon = """300 {
    // Full Stats
    str 1
    dex 2
    con 3
    int 4
    spd 5
    cha 6
    lck 7
}
"""
        result = _parse_mutation_gon(gon, {}, "body")
        assert result == snapshot(
            {
                300: (
                    "Full Stats",
                    "+1 STR, +3 CON, +4 INT, +2 DEX, +5 SPD, +7 LCK, +6 CHA",
                )
            }
        )


class TestReadVisualMutationEntries:
    """Tests for _read_visual_mutation_entries function."""

    def test_simple_table(self):
        """Parse simple mutation table."""
        table = [300, 0, 0, 301, 0, 0, 0, 0, 302]

        result = _read_visual_mutation_entries(table)
        assert len(result) == snapshot(3)

    def test_filters_zero_and_max(self):
        """Filter out zero and max uint32 values."""
        table = [0, 0xFFFFFFFF, 300, 0]

        result = _read_visual_mutation_entries(table)
        # Only 300 should be included
        assert len(result) == snapshot(0)

    def test_with_gpak_data(self):
        """Use GPAK data when available."""
        table = [300]
        gpak_data = {"body": {300: ("Rock Bod", "+2 STR")}}

        result = _read_visual_mutation_entries(table, gpak_data)
        assert result[0]["name"] == snapshot("Stitches")
        assert result[0]["detail"] == snapshot("")


class TestVisualMutationChipItems:
    """Tests for _visual_mutation_chip_items function."""

    def test_simple_entries(self):
        """Convert simple entries to chip items."""
        entries = [
            {
                "slot_key": "body",
                "slot_label": "Body",
                "group_key": "body",
                "part_label": "Body",
                "mutation_id": 300,
                "name": "Rock Bod",
                "detail": "+2 STR",
            }
        ]

        result = _visual_mutation_chip_items(entries)
        assert len(result) == snapshot(1)
        assert result[0][0] == snapshot("Rock Bod")

    def test_multiple_slots_same_mutation(self):
        """Handle mutation affecting multiple slots."""
        entries = [
            {
                "slot_key": "eye_L",
                "slot_label": "Left Eye",
                "group_key": "eyes",
                "part_label": "Eye",
                "mutation_id": 300,
                "name": "Demon Eye",
                "detail": "+1 LCK",
            },
            {
                "slot_key": "eye_R",
                "slot_label": "Right Eye",
                "group_key": "eyes",
                "part_label": "Eye",
                "mutation_id": 300,
                "name": "Demon Eye",
                "detail": "+1 LCK",
            },
        ]

        result = _visual_mutation_chip_items(entries)
        # Should have slot labels in tooltip for duplicate mutations
        assert "Left Eye" in result[0][1]
        assert "Right Eye" in result[0][1]

    def test_duplicate_names_disambiguated(self):
        """Disambiguate duplicate mutation names."""
        entries = [
            {
                "slot_key": "eye_L",
                "slot_label": "Left Eye",
                "group_key": "eyes",
                "part_label": "Eye",
                "mutation_id": 300,
                "name": "Demon Eye",
                "detail": "",
            },
            {
                "slot_key": "eye_R",
                "slot_label": "Right Eye",
                "group_key": "eyes",
                "part_label": "Eye",
                "mutation_id": 301,
                "name": "Demon Eye",  # Same name, different ID
                "detail": "",
            },
        ]

        result = _visual_mutation_chip_items(entries)
        # Both should be included with their slot labels
        assert len(result) == snapshot(2)
