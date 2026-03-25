"""Constants used throughout the parser."""

import os
from pathlib import Path

STAT_NAMES = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]

ROOM_DISPLAY = {
    "Floor1_Large": "Bot. Floor Left",
    "Floor1_Small": "Bot. Floor Right",
    "Floor2_Large": "Top Floor Right",
    "Floor2_Small": "Top Floor Left",
    "Attic": "Attic",
}

APPDATA_SAVE_DIR = Path(os.environ.get("APPDATA", "")) / "Glaiel Games" / "Mewgenics"
