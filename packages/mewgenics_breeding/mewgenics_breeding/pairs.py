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


def filter_lover_exclusivity(
    pairs: list[tuple[Cat, Cat]],
    room_cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Filter pairs that violate per-room lover exclusivity.

    Rule: If a cat's lover is in this room, they can only breed with that lover.
    Cats with lovers in different rooms can breed with anyone here.
    """
    room_cat_ids = {c.db_key for c in room_cats}
    lover_lookup: dict[int, int | None] = {
        c.db_key: c.lover_id
        for c in room_cats
        if c.lover is not None and c.lover_id in room_cat_ids
    }

    filtered: list[tuple[Cat, Cat]] = []
    for a, b in pairs:
        a_lover = lover_lookup.get(a.db_key)
        b_lover = lover_lookup.get(b.db_key)

        if a_lover is not None and b.db_key != a_lover:
            continue
        if b_lover is not None and a.db_key != b_lover:
            continue

        filtered.append((a, b))

    return filtered


def filter_hater_conflicts(
    pairs: list[tuple[Cat, Cat]],
    room_cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Filter pairs that have hater conflicts within the room.

    Rule: If cat A hates cat B and both are in this room, they can't breed.
    Cats with haters in different rooms can breed with anyone here.
    """
    room_cat_ids = {c.db_key for c in room_cats}
    hater_lookup: dict[int, set[int]] = {c.db_key: set() for c in room_cats}

    for c in room_cats:
        if c.hater is not None and c.hater_id in room_cat_ids:
            hater_lookup[c.db_key].add(c.hater_id)

    filtered: list[tuple[Cat, Cat]] = []
    for a, b in pairs:
        a_hates_b = b.db_key in hater_lookup.get(a.db_key, set())
        b_hates_a = a.db_key in hater_lookup.get(b.db_key, set())

        if a_hates_b or b_hates_a:
            continue

        filtered.append((a, b))

    return filtered
