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

## Important Notes

1. **Do not modify MewgenicsBreedingManager submodule** - it's a reference for understanding the game data format
2. **Python 3.14+ required for all packages and root** - check `.python-version` for details
3. **Use uv for all package management** - don't use pip directly
4. **Use uv run for all tools** - ruff, ty, pytest, etc.
