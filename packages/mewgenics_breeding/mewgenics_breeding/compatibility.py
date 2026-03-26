"""Compatibility checks for breeding pairs."""

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender


def can_breed(a: Cat, b: Cat) -> bool:
    """Check if two cats can produce offspring."""
    g_set = {a.gender, b.gender}
    return CatGender.DITTO in g_set or g_set == {CatGender.MALE, CatGender.FEMALE}
