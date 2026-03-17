"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def savefile_path(request):
    """Path to save file for integration tests."""
    path = os.environ.get("MEWGENICS_SAVEFILE_PATH")
    if not path and sys.platform == "win32" and (appdata := os.getenv("APPDATA")):
        path = (
            appdata
            + r"\Glaiel Games\Mewgenics\76561198044230461\saves\steamcampaign01.sav"
        )

    if path and Path(path).exists():
        return path

    pytest.skip(
        "No save file provided. Populate MEWGENICS_SAVEFILE_PATH env var or place save file in default location."
    )


@pytest.fixture
def gpak_path(request):
    """Path to GPAK file for integration tests."""
    path = os.environ.get("MEWGENICS_GPAK_PATH")
    if not path and sys.platform == "win32":
        path = r"C:\Program Files (x86)\Steam\steamapps\common\Mewgenics\resources.gpak"

    if path and Path(path).exists():
        return path

    pytest.skip(
        "No GPAK file provided. Populate MEWGENICS_GPAK_PATH env var or place resources.gpak in default location."
    )
