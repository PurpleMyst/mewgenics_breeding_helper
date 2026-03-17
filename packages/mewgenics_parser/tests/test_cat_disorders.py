"""Tests for mewgenics_parser cat module disorder separation."""


from mewgenics_parser.cat import _split_passives_and_disorders


class TestSplitPassivesAndDisorders:
    """Tests for _split_passives_and_disorders function."""

    def test_all_passives(self):
        traits = ["Sturdy", "Dumb", "LongShot"]
        passives, disorders = _split_passives_and_disorders(traits)

        assert passives == ["Sturdy", "Dumb", "LongShot"]
        assert disorders == []

    def test_all_disorders(self):
        traits = ["blind", "bentleg", "nomouth"]
        passives, disorders = _split_passives_and_disorders(traits)

        assert passives == []
        assert disorders == ["blind", "bentleg", "nomouth"]

    def test_mixed_passives_and_disorders(self):
        traits = ["Sturdy", "blind", "Dumb", "bentleg"]
        passives, disorders = _split_passives_and_disorders(traits)

        assert passives == ["Sturdy", "Dumb"]
        assert disorders == ["blind", "bentleg"]

    def test_case_insensitive(self):
        traits = ["Sturdy", "BLIND", "Blind", "sturdy"]
        passives, disorders = _split_passives_and_disorders(traits)

        assert passives == ["Sturdy", "sturdy"]
        assert disorders == ["BLIND", "Blind"]

    def test_empty_list(self):
        passives, disorders = _split_passives_and_disorders([])

        assert passives == []
        assert disorders == []
