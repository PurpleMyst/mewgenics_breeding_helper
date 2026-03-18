# Agent Guidelines for mewgenics_breeding_helper

This project is a Python-based tool for parsing Mewgenics save files. It uses a monorepo structure with multiple packages under the `packages/` directory.

## Project Structure

```
mewgenics_breeding_helper/
├── pyproject.toml              # Root workspace config (uv)
├── packages/
│   ├── mewgenics_parser/        # Save file parsing, trait definitions
│   │   └── mewgenics_parser/
│   │       ├── __init__.py
│   │       ├── binary.py        # BinaryReader helper
│   │       ├── cat.py           # Cat data model (dataclass)
│   │       ├── constants.py     # Constants and regex patterns
│   │       ├── gpak.py         # GPAK file handling
│   │       ├── save.py         # Save file parsing
│   │       ├── traits.py       # Trait domain models
│   │       ├── trait_dictionary.py  # Trait constants
│   │       ├── visual.py       # Visual mutation handling
│   │       └── data/           # Static data (abilities, visual names)
│   ├── mewgenics_scorer/       # Trait scoring logic
│   ├── mewgenics_room_optimizer/   # Room optimization algorithm
│   └── mewgenics_room_optimizer_ui/ # DearPyGui UI application
└── MewgenicsBreedingManager/   # Submodule - reference only, do not modify
```

## Commands

### Development Environment
```bash
# Install dependencies (requires uv)
uv sync

# Install dev dependencies
uv sync --group dev

# Add a new dependency to a package
uv add <package> -p packages/mewgenics_parser

# Run the UI application
uv run room-optimizer
```

### Testing
```bash
# Run all tests (pytest)
uv run pytest

# Run a single test file
uv run pytest tests/test_cat.py

# Run a single test function
uv run pytest tests/test_cat.py::test_parse_cat

# Run tests with coverage
uv run pytest --cov=mewgenics_parser --cov=mewgenics_scorer
```

### Linting and Formatting
```bash
# Format code (ruff)
uv run ruff format .

# Lint code
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Type Checking
```bash
# Run type checker (ty)
uv run ty check .

# Type check a specific file
uv run ty check packages/mewgenics_parser/mewgenics_parser/cat.py
```

## Code Style Guidelines

### Type Hints
- Use Python 3.14+ type syntax (e.g., `list[Cat]`, `dict[str, int]`)
- Use union types: `str | None` is preferred over Optional[str]
- `from __future__ import annotations` is only for files ported from MewgenicsBreedingManager
- New code should use standard type hints

### Naming Conventions
- **Classes**: PascalCase (e.g., `Cat`, `BinaryReader`, `SaveData`)
- **Functions/variables**: snake_case (e.g., `parse_save`, `_valid_str`)
- **Private methods/attributes**: prefix with underscore (e.g., `_parent_uid_a`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `STAT_NAMES`, `ROOM_DISPLAY`)
- **Private module-level constants**: UPPER_SNAKE with underscore prefix (e.g., `_IDENT_RE`, `_JUNK_STRINGS`)

### Imports
- Use relative imports within packages: `from .binary import BinaryReader`
- Use absolute imports between packages: `from mewgenics_parser.cat import Cat`
- Group imports: stdlib first, then third-party, then local
- Use trailing commas in multi-line imports

### Dataclasses
- Use `@dataclass` for data models with `slots=True` for memory efficiency
- Use `init=False` when custom `__init__` is needed (see `cat.py`)
- Use `field(default=None, repr=False)` for computed/private fields
- Use `field(default_factory=list)` for mutable defaults
- Store raw/internal data with underscore prefix and `repr=False`

### Docstrings
- Use """triple quotes""" for module-level and public function docstrings
- Follow Google-style docstrings for functions with Args/Returns sections
- Keep docstrings concise but descriptive
- Omit docstrings for trivial getters/setters

### Error Handling
- Use broad `except Exception` sparingly, only when specific handling isn't possible
- Prefer specific exception types when known
- Use `try/except` blocks with clear fallbacks
- Avoid swallowing exceptions silently unless explicitly intended

### Formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (soft guideline)
- Use blank lines to separate logical sections within functions
- Use blank lines between top-level definitions (2 lines) and methods (1 line)
- Use underscores in large numeric literals: `4_294_967_296`

### Performance Considerations
- Use `frozenset` for constant lookup sets (e.g., `_JUNK_STRINGS`)
- Use `__slots__` on classes (via dataclass `slots=True`)
- Prefer dataclasses over dictionaries for structured data

## Key Patterns

### Binary Parsing
Use the `BinaryReader` class for reading binary data:
```python
r = BinaryReader(data)
value = r.u32()    # unsigned 32-bit
value = r.i32()    # signed 32-bit
value = r.u64()    # unsigned 64-bit
value = r.f64()    # 64-bit float
string = r.str()   # length-prefixed UTF-8 string
string = r.utf16str()  # length-prefixed UTF-16LE string
```

### Trait Operations
Use the traits module for working with cat traits:
```python
from mewgenics_parser.traits import extract_traits_from_cat, create_trait, TraitCategory

traits = extract_traits_from_cat(cat)  # Extract all traits as domain objects
trait = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")  # Create specific trait
name = trait.get_display_name(game_data)  # Get display name
desc = trait.get_description(game_data)  # Get description
```

### Property Methods
Use `@property` for computed attributes:
```python
@property
def room_display(self) -> str:
    return ROOM_DISPLAY.get(self.room, self.room)
```

## Mewgenics Reference Guide  Information

The core meta-progression of Mewgenics revolves around cultivating optimal genetics. Breeding relies on combining cats with high base stats and favorable traits while manipulating environmental variables (furniture) to control the RNG of inheritance.

#### 1. The House & Room Stats
The physical environment dictates breeding behavior and genetic transfer. Furniture modifies these parameters on a per-room basis (except Appeal, which is global).
* **Comfort:** The "Behavior" dial. High comfort increases breeding frequency and prevents cats from fighting. Negatively impacted by overcrowding (more than 4 cats) and uncleaned poop.
* **Stimulation:** The "Genetics" dial. This is the most critical stat for optimization. It directly scales the probability of kittens inheriting the *higher* of their parents' stats, spells, and passives.
* **Health:** The "Recovery" dial. Prevents diseases and cures injuries overnight. Low health risks hygiene-related disorders.
* **Mutation:** The "Chaos" dial. Increases the odds of a cat spontaneously mutating overnight. 
* **Appeal:** The "Stray Quality" dial (Global). Determines the base stat quality and trait loadout of stray cats that arrive at your house.

#### 2. Cat Stats & Breeding Prerequisites
* **Base Stats Only:** Kittens only inherit **Base Stats** (STR, DEX, CON, INT, SPD, CHA, LCK). Temporary modifications from items, injuries, or diseases are ignored.
* **Libido & Aggression:** Hidden stats (until unlocked via Tink) that dictate how often a cat initiates breeding or fighting.
* **Gender:** Cats are Male, Female, or Fluid (`?` / Spidercats). Gay/Same-sex pairs will happily partner up but cannot produce offspring unless one of the cats is Fluid (`?`).

#### 3. The Inheritance Math (Internal Engine Rules)
When the day ends and two cats breed, the game's engine (`glaiel::CatData::breed`) executes the following order of operations:

**A. Stat Inheritance**
For each of the 7 stats, the game picks either the mother's or father's base stat. The probability of inheriting the *higher* of the two stats scales with room Stimulation:
$$P(\text{Higher Stat}) = \frac{1.0 + 0.01 \times \text{Stimulation}}{2.0 + 0.01 \times \text{Stimulation}}$$
*Note:* Stimulation has diminishing returns for stats. At 0 Stimulation, it is a 50/50 coin flip. At 50 Stimulation, it is a 60% chance. At 100 Stimulation, it is roughly 66.6%.

**B. Spell Inheritance**
Parents pass down Active Abilities. If class spells are present, the game has a $0.01 \times \text{Stimulation}$ probability of forcing the selection from the parent with class spells.
* **First Spell Chance:** $0.2 + 0.025 \times \text{Stimulation}$ (Guaranteed at 32+ Stimulation).
* **Second Spell Chance:** $0.02 + 0.005 \times \text{Stimulation}$.

**C. Passive Inheritance**
* **Passive Chance:** $0.05 + 0.01 \times \text{Stimulation}$ (Guaranteed at 95+ Stimulation).
* **SkillShare+ Override:** If a parent has the upgraded *SkillShare+* ability, the game guarantees their *other* passive is passed down, bypassing standard inheritance logic.

**D. Disorders & Birth Defects (Inbreeding)**
* **Inherited Disorders:** There is a flat **15%** chance to inherit a random disorder from the mother, and a **15%** chance from the father. This is completely unaffected by room furniture.
* **Birth Defects:** If the kitten inherits fewer than 2 disorders, it rolls for a spontaneous birth defect based on the parents' Inbreeding Coefficient:
    $$P(\text{Birth Defect}) = 0.02 + 0.4 \times \max(\text{Inbreeding} - 0.2, 0.0)$$
    *If the inbreeding coefficient is >0.05, the kitten may also roll for physical deformed parts later in the generation step.*

**E. Body Parts & Mutations**
Mutations are treated as specific part variants (e.g., a mutated arm).
* There is an **80%** chance that all body parts are inherited perfectly from the parents. If this fails, a random part-set (e.g., both legs) is randomly generated.
* If only one parent has a mutated part, the game attempts to favor the mutation using the exact same formula as Stat Inheritance ($P(\text{Higher Stat})$). Otherwise, it is a 50/50 split between parents.

## Important Notes

1. **Do not modify MewgenicsBreedingManager submodule** - it's a reference for understanding the game data format
2. **Python 3.14+ required for all packages and root** - check `.python-version` for details
3. **Use uv for all package management** - don't use pip directly
4. **Use uv run for all tools** - ruff, ty, pytest, etc.
