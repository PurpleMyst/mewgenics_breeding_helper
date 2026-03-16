"""Pytest configuration and shared fixtures."""

import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--gpak-path",
        action="store",
        default=None,
        help="Path to resources.gpak file for integration tests",
    )


@pytest.fixture
def gpak_path(request):
    """Path to GPAK file for integration tests."""
    path = request.config.getoption("--gpak-path")
    if path is None:
        path = os.environ.get("MEWGENICS_GPAK_PATH")

    if path and Path(path).exists():
        return path

    pytest.skip(
        f"No GPAK file provided. Use --gpak-path or MEWGENICS_GPAK_PATH env var."
    )


@pytest.fixture
def sample_gpak_bytes():
    """Minimal GPAK-like binary structure for testing header parsing."""
    import struct

    files = {
        "data/text/strings.csv": "key,value\nABILITY_001,+1 Damage.",
        "data/abilities/slugger.gon": 'Slugger { desc "ABILITY_001" }',
    }

    entries = []
    data_parts = []
    current_offset = 4 + len(files) * (2 + 4)  # count + entries

    for fname, content in files.items():
        name_bytes = fname.encode("utf-8")
        entries.append((name_bytes, len(content.encode("utf-8"))))
        current_offset += len(content.encode("utf-8"))

    buffer = bytearray()
    buffer.extend(struct.pack("<I", len(files)))

    for name_bytes, size in entries:
        buffer.extend(struct.pack("<H", len(name_bytes)))
        buffer.extend(name_bytes)
        buffer.extend(struct.pack("<I", size))

    for fname, content in files.items():
        buffer.extend(content.encode("utf-8"))

    return bytes(buffer)
