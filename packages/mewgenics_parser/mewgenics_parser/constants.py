"""Constants used throughout the parser."""

import os
import re

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_JUNK_STRINGS = frozenset({"none", "null", "", "defaultmove", "default_move"})

STAT_NAMES = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]

ROOM_DISPLAY = {
    "Floor1_Large": "Bot. Floor Left",
    "Floor1_Small": "Bot. Floor Right",
    "Floor2_Large": "Top Floor Right",
    "Floor2_Small": "Top Floor Left",
    "Attic": "Attic",
}

APPDATA_SAVE_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "Glaiel Games",
    "Mewgenics",
)
