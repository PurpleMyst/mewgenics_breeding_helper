"""Tests for mewgenics_parser trait_dictionary module."""


from mewgenics_parser.trait_dictionary import (
    BASIC_ATTACK_TYPES,
    COLLARLESS_SPELLS,
    DISORDERS,
    is_class_spell,
    is_class_passive,
)


class TestBasicAttackTypes:
    """Tests for BASIC_ATTACK_TYPES set."""

    def test_contains_basic_melee(self):
        assert "basicmelee" in BASIC_ATTACK_TYPES

    def test_contains_basic_short_ranged(self):
        assert "basicshortranged" in BASIC_ATTACK_TYPES


class TestCollarlessSpells:
    """Tests for COLLARLESS_SPELLS set."""

    def test_contains_common_spells(self):
        assert "swat" in COLLARLESS_SPELLS
        assert "zap" in COLLARLESS_SPELLS


class TestDisorders:
    """Tests for DISORDERS set."""

    def test_contains_birth_defects(self):
        assert "blind" in DISORDERS
        assert "bentleg" in DISORDERS
        assert "nomouth" in DISORDERS


class TestIsClassSpell:
    """Tests for is_class_spell function."""

    def test_basic_attacks_not_class(self):
        assert is_class_spell("BasicMelee") is False
        assert is_class_spell("basicmelee") is False

    def test_collarless_spells_not_class(self):
        assert is_class_spell("Swat") is False
        assert is_class_spell("swat") is False

    def test_class_spells_are_class(self):
        assert is_class_spell("PathOfTheHunter") is True
        assert is_class_spell("PathOfTheButcher") is True


class TestIsClassPassive:
    """Tests for is_class_passive function."""

    def test_disorders_not_passives(self):
        assert is_class_passive("blind") is False
        assert is_class_passive("bentleg") is False

    def test_collarless_passives_not_class(self):
        assert is_class_passive("sturdy") is False
        assert is_class_passive("dumb") is False

    def test_class_passives_are_class(self):
        assert is_class_passive("frenzy") is True
        assert is_class_passive("avenger") is True
