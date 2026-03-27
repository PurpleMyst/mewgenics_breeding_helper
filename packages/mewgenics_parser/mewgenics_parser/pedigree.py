"""Pedigree blob parsing based on ImHex pattern analysis."""

import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

NULL = 0xFFFF_FFFF_FFFF_FFFF
HASH_VERSION = 0xFFFFFFFFFFFFFFF5

T = TypeVar("T")


@dataclass
class ChildPedigree:
    """Child entry with both parents and COI."""

    child_id: int
    parent_a_id: int
    parent_b_id: int
    coi: float


@dataclass
class ParentCOI:
    """Parent pair entry with COI for hypothetical offspring."""

    parent_a_id: int
    parent_b_id: int
    coi: float


class HashMapReader:
    """Parse parallel-hashmap format from ImHex pattern.

    Structure:
        u64 version
        u64 size
        u64 capacity
        u8 hash_table[capacity]
        u8 eot_marker (0xFF)
        u8 wide_load_rep[16]
        T data_table[capacity]
        u64 growth_left
    """

    def __init__(self, data: bytes, struct_size: int):
        self.data = data
        self.struct_size = struct_size
        self._parse_header()

    def _parse_header(self) -> None:
        self.version, self.size, self.capacity = struct.unpack_from(
            "<QQQ", self.data, 0
        )
        self.hash_start = 24
        self.data_start = self.hash_start + self.capacity + 1 + 16

    def read_entries(self, factory: Callable[[bytes, int], T | None]) -> list[T]:
        """Read entries where hash_table slot indicates occupied (0x00-0x7F)."""
        entries = []
        for i in range(self.capacity):
            hash_byte = self.data[self.hash_start + i]
            if hash_byte <= 0x7F:
                offset = self.data_start + (i * self.struct_size)
                entry = factory(self.data, offset)
                if entry is not None:
                    entries.append(entry)
        return entries


def _make_child_pedigree(data: bytes, offset: int) -> ChildPedigree | None:
    """Parse ChildPedigree: u64 child_id, u64 parent_a, u64 parent_b, double coi."""
    child_id, pa, pb, coi = struct.unpack_from("<QQQd", data, offset)

    if child_id == NULL or child_id == 0:
        return None
    if pa == NULL or pb == NULL:
        return None

    return ChildPedigree(int(child_id), int(pa), int(pb), coi)


def _make_parent_coi(data: bytes, offset: int) -> ParentCOI | None:
    """Parse ParentCOI: u64 parent_a_id, u64 parent_b_id, double coi."""
    pa, pb, coi = struct.unpack_from("<QQd", data, offset)

    if pa == NULL or pb == NULL:
        return None

    return ParentCOI(int(pa), int(pb), coi)


def _calc_hashmap_size(capacity: int, struct_size: int) -> int:
    """Calculate total size of a HashMap given capacity and struct size."""
    header = 24
    hash_table = capacity
    eot_marker = 1
    wide_load_rep = 16
    data_table = capacity * struct_size
    growth_left = 8
    return header + hash_table + eot_marker + wide_load_rep + data_table + growth_left


def parse_pedigree_blob(
    data: bytes,
) -> tuple[list[ChildPedigree], dict[tuple[int, int], float]]:
    """
    Parse the pedigree blob.

    Returns:
        Tuple of:
        - child_pedigrees: list of ChildPedigree for existing cats
        - parents_coi_memo: {(pa_id, pb_id): coi} for hypothetical offspring

    Raises:
        ValueError: If child_to_parents HashMap version doesn't match.
    """
    hm1 = HashMapReader(data, struct_size=32)

    if hm1.version != HASH_VERSION:
        raise ValueError(
            f"Expected child_to_parents HashMap version {HASH_VERSION:#x}, "
            f"got {hm1.version:#x}"
        )

    child_pedigrees = hm1.read_entries(_make_child_pedigree)

    hm1_size = _calc_hashmap_size(hm1.capacity, 32)
    hm2_data = data[hm1_size:]

    hm2 = HashMapReader(hm2_data, struct_size=24)
    parent_cois = hm2.read_entries(_make_parent_coi)

    parents_coi_memo: dict[tuple[int, int], float] = {}
    for pci in parent_cois:
        parents_coi_memo[(pci.parent_a_id, pci.parent_b_id)] = pci.coi

    return (child_pedigrees, parents_coi_memo)
