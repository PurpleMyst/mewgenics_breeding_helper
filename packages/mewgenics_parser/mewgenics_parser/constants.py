"""Constants used throughout the parser."""
import os
import re
from pathlib import Path

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

_JUNK_STRINGS = frozenset({"none", "null", "", "defaultmove", "default_move"})

STAT_NAMES = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]

ROOM_DISPLAY = {
    "Floor1_Large":   "Ground Floor Left",
    "Floor1_Small":   "Ground Floor Right",
    "Floor2_Large":   "Second Floor Right",
    "Floor2_Small":   "Second Floor Left",
    "Attic":          "Attic",
}

APPDATA_SAVE_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "Glaiel Games", "Mewgenics",
)
