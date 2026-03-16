"""Compatibility checks for breeding pairs."""

from mewgenics_parser import Cat


def can_breed(a: Cat, b: Cat) -> bool:
    """Check if two cats can produce offspring."""
    ga = (a.gender or "?").strip().lower()
    gb = (b.gender or "?").strip().lower()
    if ga == "?" or gb == "?":
        return True
    if ga != gb and {ga, gb} == {"male", "female"}:
        return True
    return False


def is_hater_conflict(a: Cat, b: Cat) -> bool:
    """Check if cats hate each other."""
    return b in a.haters or a in b.haters


def is_lover_conflict(a: Cat, b: Cat, avoid_lovers: bool = True) -> bool:
    """Check if pairing would break existing lover bonds."""
    if not avoid_lovers:
        return False
    a_loves = {c.db_key for c in a.lovers}
    b_loves = {c.db_key for c in b.lovers}
    a_has_lover = bool(a_loves)
    b_has_lover = bool(b_loves)
    return (a_has_lover and b.db_key not in a_loves) or (
        b_has_lover and a.db_key not in b_loves
    )


def is_mutual_lovers(a: Cat, b: Cat) -> bool:
    """Check if both cats love each other."""
    return b in a.lovers and a in b.lovers
