"""
Mewgenics Save Parser - Standalone module for parsing Mewgenics save files.

This package provides a clean API for parsing Mewgenics game save files (.sav)
and extracting cat data, breeding information, and game state. It is designed
to be independent of any UI framework and can be used in scripts, tools, or
other applications.

Requirements:
    pip install lz4

Basic Usage:
    from mewgenics_parser import parse_save, find_save_files

    # Find all save files in standard locations
    saves = find_save_files()
    latest_save = saves[0] if saves else None

    # Parse a save file
    save_data = parse_save(latest_save)

    # Access parsed data
    print(f"Current day: {save_data.current_day}")
    print(f"Total cats: {len(save_data.cats)}")
    print(f"In house: {save_data.house_count}")
    print(f"Adventuring: {save_data.adventure_count}")
    print(f"Gone: {save_data.gone_count}")

    # Iterate through all cats
    for cat in save_data.cats:
        print(f"{cat.name} - {cat.gender} - Age {cat.age}")

Finding Specific Cats:
    # Find cats by name
    for cat in save_data.cats:
        if "angelica" in cat.name.lower():
            print(f"Found: {cat.name}")

    # Find cats by gender
    females = [c for c in save_data.cats if c.gender == "female"]

    # Find cats by status
    in_house = [c for c in save_data.cats if c.status == "In House"]

    # Find cats by room
    attic_cats = [c for c in save_data.cats if c.room == "Attic"]

Cat Object Attributes:
    The Cat object contains all parsed data for a single cat:

    Identification:
        - name: Cat's name (string)
        - unique_id: Unique seed identifier (hex string)
        - breed_id: Breed identifier (int)
        - gender: "male", "female", or "?"
        - gender_source: Where gender was read from ("sex_code" or "token_fallback")

    Location/Status:
        - status: "In House", "Adventure", or "Gone"
        - room: Room identifier (e.g., "Floor1_Large", "Attic")
        - room_display: Human-readable room name

    Stats:
        - stat_base: Base stats dict {"STR": int, "DEX": int, ...}
        - stat_mod: Modifier stats dict
        - stat_sec: Secondary stats dict
        - total_stats: Combined stats (base + mod + sec)

    Personality:
        - age: Age in days (int or None)
        - aggression: 0.0-1.0 float (or None if unknown)
        - libido: 0.0-1.0 float (or None)
        - inbredness: 0.0-1.0 float (or None)

    Relationships:
        - parent_a: Parent Cat object (or None)
        - parent_b: Parent Cat object (or None)
        - children: List of child Cat objects
        - lovers: List of lover Cat objects
        - haters: List of hater Cat objects
        - generation: Generation depth (0 for strays)

    Abilities:
        - abilities: List of active ability names
        - passive_abilities: List of passive ability names
        - equipment: List of equipped items

    Visual/Mutations:
        - mutations: List of mutation display names
        - visual_mutation_entries: List of mutation entry dicts
        - visual_mutation_ids: List of mutation IDs
        - visual_mutation_slots: Dict of slot key to mutation ID
        - body_parts: Dict of body part IDs

    Other:
        - collar: Collar name (string)
        - gender_token_fields: Tuple of gender token values
        - gender_token: Raw gender token string
        - db_key: Database key (int)

Cat Properties:
    The Cat class provides several convenience properties:
        - room_display: Human-readable room name
        - gender_display: Short gender ("M", "F", or "?")
        - can_move: True if cat is in house and can be moved
        - short_name: First word of cat's name

Parsing with GPAK (Optional):
    For ability descriptions and visual mutation data from the game files,
    you can load the resources.gpak:

    from mewgenics_parser import parse_save, GameData

    # Load game data (requires resources.gpak file)
    # GPAK is usually found in the game installation directory
    game_data = GameData.from_gpak("/path/to/resources.gpak")

    # Get ability description
    if "slugger" in game_data.ability_descriptions:
        print(game_data.ability_descriptions["slugger"])
        # Output: "+1 Damage."

    # Get visual mutation data
    if "body" in game_data.visual_mutations:
        print(game_data.visual_mutations["body"])
        # Output: {300: ("Rock Bod", ""), 301: ("Cactus Bod", ""), ...}

    # The GameData object also contains:
    #   - game_strings: Full dictionary of game text strings

Finding Save Files:
    The find_save_files() function searches standard save locations:
        - Windows: %APPDATA%\\Glaiel Games\\Mewgenics\\
        - Steam Cloud saves

    Returns a list of absolute paths, sorted by modification time
    (newest first).

Error Handling:
    The parser uses fail-fast error handling. If parsing fails, an exception
    is raised with details about what went wrong. Common exceptions:
        - FileNotFoundError: Save file doesn't exist
        - sqlite3.DatabaseError: Invalid save file format
        - lz4.block.LZ4DecompressError: Corrupted cat data
        - struct.error: Binary parsing error

Example: Complete Script
    #!/usr/bin/env python3
    \"\"\"List all cats in the attic.\"\"\"
    from mewgenics_parser import parse_save, find_save_files

    saves = find_save_files()
    if not saves:
        print("No save files found!")
        exit(1)

    save_data = parse_save(saves[0])
    print(f"Current day: {save_data.current_day}")
    print(f"\\nCats in Attic:")

    for cat in save_data.cats:
        if cat.room == "Attic":
            stats = ", ".join(f"{k}:{v}" for k, v in cat.total_stats.items())
            print(f"  {cat.name} ({cat.gender}) - Age {cat.age} - {stats}")

Example: Find Best Breeders
    #!/usr/bin/env python3
    \"\"\"Find cats with high total stats.\"\"\"
    from mewgenics_parser import parse_save, find_save_files

    save_data = parse_save(find_save_files()[0])

    # Calculate total base stats
    def total_base(cat):
        return sum(cat.stat_base.values())

    # Sort by total stats
    sorted_cats = sorted(save_data.cats, key=total_base, reverse=True)

    print("Top 10 cats by base stats:")
    for cat in sorted_cats[:10]:
        total = total_base(cat)
        print(f"  {cat.name}: {total} ({cat.gender}, {cat.age}y)")

Example: Breeding Analysis
    #!/usr/bin/env python3
    \"\"\"Analyze parent-child relationships.\"\"\"
    from mewgenics_parser import parse_save, find_save_files

    save_data = parse_save(find_save_files()[0])

    # Find cats with both parents present
    cats_with_parents = [c for c in save_data.cats
                         if c.parent_a is not None and c.parent_b is not None]

    print(f"Cats with both parents: {len(cats_with_parents)}")

    # Find cats with no parents (strays)
    strays = [c for c in save_data.cats
              if c.parent_a is None and c.parent_b is None]

    print(f"Strays (no parents): {len(strays)}")

    # Count children per cat
    parent_counts = {}
    for cat in save_data.cats:
        for parent in [cat.parent_a, cat.parent_b]:
            if parent is not None:
                parent_counts[parent.name] = parent_counts.get(parent.name, 0) + 1

    # Top parents
    top_parents = sorted(parent_counts.items(), key=lambda x: x[1], reverse=True)
    print("\\nTop parents:")
    for name, count in top_parents[:5]:
        print(f"  {name}: {count} children")

Room Names:
    The parser uses raw room identifiers from the game. Use cat.room_display
    for human-readable names:

    Raw -> Display:
        "Floor1_Large"   -> "Ground Floor Left"
        "Floor1_Small"   -> "Ground Floor Right"
        "Floor2_Large"   -> "Second Floor Right"
        "Floor2_Small"   -> "Second Floor Left"
        "Attic"          -> "Attic"

Stat Names:
    Stats are stored in this order: STR, DEX, CON, INT, SPD, CHA, LCK
"""

from .save import parse_save, find_save_files, SaveData
from .cat import Cat
from .gpak import GameData

__all__ = [
    "parse_save",
    "find_save_files",
    "SaveData",
    "Cat",
    "GameData",
]
