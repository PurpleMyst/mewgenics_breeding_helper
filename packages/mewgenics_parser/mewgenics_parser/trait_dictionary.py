"""Static trait dictionaries for breeding probability calculations."""

from __future__ import annotations

__all__ = [
    "BASIC_ATTACK_TYPES",
    "COLLARLESS_SPELLS",
    "COLLARLESS_PASSIVES",
    "DISORDERS",
    "SKILLSHARE_PLUS_ID",
    "is_class_spell",
    "is_class_passive",
    "has_skillshare_plus",
]

# Basic attacks (not inheritable as spells)
BASIC_ATTACK_TYPES = frozenset(
    {
        "basicmelee",
        "basicshortlobbed",
        "basicshortranged",
        "defaultmove",
        "default_move",
    }
)

# Generic spells available to all cats (collarless/generic)
COLLARLESS_SPELLS = frozenset(
    {
        "swat",
        "blowkiss",
        "featherfeet",
        "soulreap",
        "minihook",
        "wethairball",
        "preparetojump",
        "subwayride",
        "gainthorns",
        "brace",
        "zap",
        "blow",
        "smack",
        "reach",
        "taint",
    }
)

# Generic passives available to all cats (collarless/generic)
COLLARLESS_PASSIVES = frozenset(
    {
        "sturdy",
        "dumb",
        "longrange",
        "fancy",
        "beads",
        "unburdenedthoughts",
        "latentenergy",
        "one",
    }
)

# Birth defects (NOT passives, NOT inheritable via passive mechanics)
DISORDERS = frozenset(
    {
        "twoedarm",
        "twotoedarm",
        "bentarm",
        "conjoinedbody",
        "lumpybody",
        "malnourishedbody",
        "turnersyndrome",
        "birdbeakears",
        "floppyears",
        "inwardeyes",
        "redeyes",
        "blind",
        "bushyeyebrow",
        "noeyebrows",
        "sloth",
        "conjoinedtwin",
        "bentleg",
        "duckleg",
        "twoedleg",
        "twotoedleg",
        "nomouth",
        "cleftlip",
        "lumpytail",
        "notail",
        "tailsack",
    }
)

# Only the UPGRADED SkillShare+ triggers guaranteed inheritance
# TODO: Verify exact internal ID from game data
SKILLSHARE_PLUS_ID = "skillshare_plus"


def is_class_spell(spell_id: str) -> bool:
    """Returns True if spell is class-specific (NOT generic/collarless)."""
    sid = spell_id.lower().strip()
    if sid in BASIC_ATTACK_TYPES or sid in COLLARLESS_SPELLS:
        return False
    return True


def is_class_passive(passive_id: str) -> bool:
    """Returns True if passive is class-specific."""
    pid = passive_id.lower().strip()
    if pid in DISORDERS or pid in COLLARLESS_PASSIVES:
        return False
    return True


def has_skillshare_plus(cat) -> bool:
    """Check if cat has the upgraded SkillShare+ passive."""
    return any(p.lower() == SKILLSHARE_PLUS_ID for p in (cat.passive_abilities or []))
