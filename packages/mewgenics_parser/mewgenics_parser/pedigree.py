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


def parse_pedigree_blob(data: bytes) -> list[ChildPedigree]:
    """
    Parse the pedigree blob.

    Returns:
        List of ChildPedigree entries where both parents are known.

    Raises:
        ValueError: If child_to_parents HashMap version doesn't match.
    """
    hm1 = HashMapReader(data, struct_size=32)

    if hm1.version != HASH_VERSION:
        raise ValueError(
            f"Expected child_to_parents HashMap version {HASH_VERSION:#x}, "
            f"got {hm1.version:#x}"
        )

    return hm1.read_entries(_make_child_pedigree)
