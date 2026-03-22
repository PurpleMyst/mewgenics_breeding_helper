"""Mewgenics save file parsing."""

import sqlite3
import struct
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .cat import Cat
from .constants import APPDATA_SAVE_DIR


@dataclass
class SaveData:
    cats: list[Cat]
    current_day: int | None
    house_count: int
    adventure_count: int
    gone_count: int


def _get_house_info(conn) -> dict:
    row = conn.execute("SELECT data FROM files WHERE key = 'house_state'").fetchone()
    if not row or len(row[0]) < 8:
        return {}
    data = row[0]
    count = struct.unpack_from("<I", data, 4)[0]
    pos = 8
    result = {}
    for _ in range(count):
        if pos + 8 > len(data):
            break
        cat_key = struct.unpack_from("<I", data, pos)[0]
        pos += 8
        room_len = struct.unpack_from("<I", data, pos)[0]
        pos += 8
        room_name = ""
        if room_len > 0:
            room_name = data[pos : pos + room_len].decode("ascii", errors="ignore")
            pos += room_len
        pos += 24
        result[cat_key] = room_name
    return result


def _get_adventure_keys(conn) -> set:
    keys = set()
    try:
        row = conn.execute(
            "SELECT data FROM files WHERE key = 'adventure_state'"
        ).fetchone()
        if not row or len(row[0]) < 8:
            return keys
        data = row[0]
        count = struct.unpack_from("<I", data, 4)[0]
        pos = 8
        for _ in range(count):
            if pos + 8 > len(data):
                break
            val = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            cat_key = (val >> 32) & 0xFFFF_FFFF
            if cat_key:
                keys.add(cat_key)
    except Exception:
        pass
    return keys


def _parse_pedigree(conn) -> dict:
    """
    Parse the pedigree blob from the files table.
    Each 32-byte entry: u64 cat_key, u64 parent_a_key, u64 parent_b_key, u64 extra.
    0xFFFFFFFFFFFFFFFF means null/unknown for parent fields.

    Returns ped_map: db_key -> (parent_a_db_key | None, parent_b_db_key | None).

    NOTE: children are NOT derived from this map because the pedigree blob
    appears to store more than just direct parent-child pairs (possibly full
    lineage chains), which causes circular references when used for children.
    Children are instead computed bottom-up from resolved parent fields.
    """
    try:
        row = conn.execute("SELECT data FROM files WHERE key='pedigree'").fetchone()
        if not row:
            return {}
        data = row[0]
    except Exception:
        return {}

    NULL = 0xFFFF_FFFF_FFFF_FFFF
    MAX_KEY = 1_000_000
    ped_map: dict = {}

    for pos in range(8, len(data) - 31, 32):
        cat_k, pa_k, pb_k, extra = struct.unpack_from("<QQQQ", data, pos)
        if cat_k == 0 or cat_k == NULL or cat_k > MAX_KEY:
            continue
        pa = int(pa_k) if pa_k != NULL and 0 < pa_k <= MAX_KEY else None
        pb = int(pb_k) if pb_k != NULL and 0 < pb_k <= MAX_KEY else None
        cat_key = int(cat_k)

        if pa is None or pb is None:
            continue

        existing = ped_map.get(cat_key)
        if existing is None:
            ped_map[cat_key] = (pa, pb)
        elif existing[0] is None or existing[1] is None:
            ped_map[cat_key] = (pa, pb)

    return ped_map


def _break_pedigree_cycles(cats: list[Cat]) -> list[Cat]:
    """
    Detect and break cycles in the pedigree graph by setting parent references to None.

    When a cycle is detected, both parent_a and parent_b of the cat at the cycle point
    are set to None.

    Returns list of cats that had their parents cleared due to cycle detection.
    """
    affected = []

    def dfs(cat: Cat, path: set[int]) -> bool:
        if cat.db_key in path:
            return True

        path.add(cat.db_key)

        if cat.parent_a and dfs(cat.parent_a, path):
            affected.append(cat)
            cat.parent_a = None
            cat.parent_b = None

        if cat.parent_b and dfs(cat.parent_b, path):
            affected.append(cat)
            cat.parent_a = None
            cat.parent_b = None

        path.remove(cat.db_key)
        return False

    for cat in cats:
        dfs(cat, set())

    return affected


def parse_save(path: str) -> SaveData:
    """
    Parse a Mewgenics save file (.sav).

    Args:
        path: Path to the .sav file

    Returns:
        SaveData containing parsed cats and metadata
    """
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        house = _get_house_info(conn)
        adv = _get_adventure_keys(conn)
        rows = conn.execute("SELECT key, data FROM cats").fetchall()
        ped_map = _parse_pedigree(conn)
        current_day_row = conn.execute(
            "SELECT data FROM properties WHERE key='current_day'"
        ).fetchone()
        current_day = current_day_row[0] if current_day_row else None
    finally:
        conn.close()

    cats: list[Cat] = []
    for key, blob in rows:
        cat = Cat.from_save_data(blob, key, house, adv, current_day)
        cats.append(cat)

    cats_by_key: dict = {c.db_key: c for c in cats}
    for cat in cats:
        pa: Optional[Cat] = None
        pb: Optional[Cat] = None
        if cat.db_key in ped_map:
            pa_k, pb_k = ped_map[cat.db_key]
            pa = cats_by_key.get(pa_k)
            pb = cats_by_key.get(pb_k)
            if pa is cat:
                pa = None
            if pb is cat:
                pb = None
        cat.parent_a = pa
        cat.parent_b = pb

        if isinstance(cat.lover, int):
            lover = cats_by_key.get(cat.lover)
            if lover is not None and lover is not cat:
                cat.lover = lover

        if isinstance(cat.hater, int):
            hater = cats_by_key.get(cat.hater)
            if hater is not None and hater is not cat:
                cat.hater = hater

    affected = _break_pedigree_cycles(cats)
    if affected:
        print(f"Broke {len(affected)} pedigree cycles")

    house_count = sum(1 for c in cats if c.status == "In House")
    adventure_count = sum(1 for c in cats if c.status == "Adventure")
    gone_count = sum(1 for c in cats if c.status == "Gone")

    return SaveData(
        cats=cats,
        current_day=current_day,
        house_count=house_count,
        adventure_count=adventure_count,
        gone_count=gone_count,
    )


def find_save_files() -> list[str]:
    """
    Discover .sav files in standard Mewgenics save locations.

    Returns:
        List of absolute paths to .sav files, sorted by modification time (newest first)
    """
    saves = []
    base = Path(APPDATA_SAVE_DIR)
    if not base.is_dir():
        return saves
    for profile in base.iterdir():
        saves_dir = profile / "saves"
        if saves_dir.is_dir():
            saves.extend(str(p) for p in saves_dir.glob("*.sav"))
    saves.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return saves
