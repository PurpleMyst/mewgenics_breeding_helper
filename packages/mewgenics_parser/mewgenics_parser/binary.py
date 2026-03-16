"""Binary reading utilities for parsing Mewgenics save files."""
import struct


class BinaryReader:
    """Helper class for reading binary data from save file blobs."""

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def u32(self) -> int:
        """Read unsigned 32-bit integer (little-endian)."""
        v = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return v

    def i32(self) -> int:
        """Read signed 32-bit integer (little-endian)."""
        v = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return v

    def u64(self) -> int:
        """Read unsigned 64-bit integer (little-endian)."""
        lo, hi = struct.unpack_from('<II', self.data, self.pos)
        self.pos += 8
        return lo + hi * 4_294_967_296

    def f64(self) -> float:
        """Read 64-bit float (double)."""
        v = struct.unpack_from('<d', self.data, self.pos)[0]
        self.pos += 8
        return v

    def str(self) -> str | None:
        """Read length-prefixed UTF-8 string."""
        start = self.pos
        try:
            length = self.u64()
            if length < 0 or length > 10_000:
                self.pos = start
                return None
            s = self.data[self.pos:self.pos + int(length)].decode('utf-8', errors='ignore')
            self.pos += int(length)
            return s
        except Exception:
            self.pos = start
            return None

    def utf16str(self) -> str:
        """Read length-prefixed UTF-16LE string."""
        char_count = self.u64()
        byte_len = int(char_count * 2)
        s = self.data[self.pos:self.pos + byte_len].decode('utf-16le', errors='ignore')
        self.pos += byte_len
        return s

    def skip(self, n: int) -> None:
        """Skip n bytes."""
        self.pos += n

    def seek(self, n: int) -> None:
        """Seek to absolute position."""
        self.pos = n

    def remaining(self) -> int:
        """Get bytes remaining."""
        return len(self.data) - self.pos
