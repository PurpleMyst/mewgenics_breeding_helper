"""Compatibility checks for breeding pairs."""

from mewgenics_parser.cat import CatGender

from mewgenics_parser import Cat


def can_breed(a: Cat, b: Cat) -> bool:
    """Check if two cats can produce offspring."""
    g_set = {a.gender, b.gender}
    return CatGender.DITTO in g_set or g_set == {CatGender.MALE, CatGender.FEMALE}


def is_hater_conflict(a: Cat, b: Cat) -> bool:
    """Check if cats hate each other."""
    return a.hater_id == b.db_key or b.hater_id == a.db_key


def is_lover_conflict(a: Cat, b: Cat, avoid_lovers: bool = True) -> bool:
    """Check if pairing would break existing lover bonds. Excludes 'Gone' cats."""
    if not avoid_lovers:
        return False

    def _has_active_lover(cat: Cat) -> bool:
        lover = cat.lover
        if lover is None:
            return False
        if isinstance(lover, Cat):
            return lover.status != "Gone"
        return True

    a_has_lover = _has_active_lover(a)
    b_has_lover = _has_active_lover(b)

    return (a_has_lover and b.db_key != a.lover_id) or (
        b_has_lover and a.db_key != b.lover_id
    )


def is_mutual_lovers(a: Cat, b: Cat) -> bool:
    """Check if both cats love each other."""
    return a.lover_id == b.db_key and b.lover_id == a.db_key
