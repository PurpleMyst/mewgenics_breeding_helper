"""Breeding pair generation and filtering."""

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender


def generate_pairs(cats: list[Cat]) -> list[tuple[Cat, Cat]]:
    """Generate all valid pairs of cats which could potentially produce offspring."""
    males = [c for c in cats if c.gender == CatGender.MALE]
    females = [c for c in cats if c.gender == CatGender.FEMALE]
    dittos = [c for c in cats if c.gender == CatGender.DITTO]

    pairs: list[tuple[Cat, Cat]] = []
    pairs.extend((a, b) for a in males for b in females)
    pairs.extend((a, b) for a in males for b in dittos)
    pairs.extend((a, b) for a in females for b in dittos)
    pairs.extend((a, b) for i, a in enumerate(dittos) for b in dittos[i + 1 :])

    return pairs
