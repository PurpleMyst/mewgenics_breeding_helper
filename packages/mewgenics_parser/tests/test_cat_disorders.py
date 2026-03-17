"""Tests for mewgenics_parser cat module disorder separation."""

from mewgenics_parser.cat import _split_passives_and_disorders
from inline_snapshot import snapshot


class TestSplitPassivesAndDisorders:
    """Tests for _split_passives_and_disorders function."""

    def test_snapshot(self):
        traits = ["Sturdy", "Insomnia", "LongShot"]
        passives, disorders = _split_passives_and_disorders(traits)
        assert passives == snapshot(["Sturdy", "LongShot"])
        assert disorders == snapshot(["Insomnia"])
