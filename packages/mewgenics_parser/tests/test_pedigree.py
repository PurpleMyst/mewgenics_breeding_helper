"""Integration tests for pedigree parsing."""

from mewgenics_parser import parse_save
from mewgenics_scorer.ancestry import KinshipManager


class TestPedigreeParsing:
    """Verify pedigree parsing produces cycle-free data."""

    def test_no_pedigree_cycles(self, savefile_path):
        """KinshipManager raises ValueError on cycle detection."""
        save = parse_save(savefile_path)

        # KinshipManager._topological_sort raises ValueError if cycles exist
        km = KinshipManager(save.cats)

        assert len(km._processed_cats) > 0

    def test_pedigree_parent_resolution(self, savefile_path):
        """Verify known cat has expected parents resolved."""
        save = parse_save(savefile_path)

        myst = next(c for c in save.cats if "myst".casefold() in c.name.casefold())
        assert myst.parent_a is not None
        assert myst.parent_b is not None
        assert myst.parent_a.db_key == 700
        assert myst.parent_b.db_key == 781
