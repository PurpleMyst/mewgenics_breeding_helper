"""CLI entry point for mewgenics_parser."""

import sys

from .gpak import GameData


def _extract_gpak_script():
    if len(sys.argv) < 3:
        print("Usage: uv run extract-gpak <path_to_gpak> <output_zip_path>")
        sys.exit(1)
    gpak_path = sys.argv[1]
    output_zip_path = sys.argv[2]
    GameData.extract_and_dump(gpak_path, output_zip_path)


if __name__ == "__main__":
    _extract_gpak_script()
