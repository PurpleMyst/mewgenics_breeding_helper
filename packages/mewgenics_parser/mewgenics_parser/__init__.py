from .save import parse_save, find_save_files, SaveData
from .cat import Cat
from .gpak import GameData
from .trait_dictionary import normalize_trait_name

__all__ = [
    "parse_save",
    "find_save_files",
    "SaveData",
    "Cat",
    "GameData",
    "normalize_trait_name",
]


def _extract_gpak_script():
    import sys

    if len(sys.argv) < 3:
        print("Usage: uv run extract-gpak <path_to_gpak> <output_zip_path>")
        sys.exit(1)
    gpak_path = sys.argv[1]
    output_zip_path = sys.argv[2]
    GameData.extract_and_dump(gpak_path, output_zip_path)
