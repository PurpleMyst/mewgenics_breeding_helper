# Agent Guidelines for mewgenics_breeding_helper

This project is a Python-based tool for parsing Mewgenics save files. It uses a monorepo structure with multiple packages under the `packages/` directory.

## Project Structure

```
mewgenics_breeding_helper/
├── pyproject.toml              # Root workspace config (uv)
├── packages/
│   └── mewgenics_parser/       # Main parsing package
│       ├── pyproject.toml
│       └── mewgenics_parser/
│           ├── __init__.py
│           ├── binary.py       # BinaryReader helper
│           ├── cat.py          # Cat data model (dataclass)
│           ├── constants.py    # Constants and regex patterns
│           ├── gpak.py         # GPAK file handling
│           ├── save.py         # Save file parsing
│           ├── visual.py       # Visual mutation handling
│           └── data/           # Static data (abilities, visual names)
└── MewgenicsBreedingManager/   # Submodule - reference only, do not modify
```

## Commands

### Development Environment
```bash
# Install dependencies (requires uv)
uv sync

# Add a new dependency to a package
uv add <package> -p packages/mewgenics_parser

# Run the package (if it has a CLI entry point)
uv run -p packages/mewgenics_parser <module>
```

### Testing
This project currently has no test suite. When adding tests:
```bash
# Run all tests (pytest recommended)
pytest

# Run a single test file
pytest tests/test_cat.py

# Run a single test function
pytest tests/test_cat.py::test_parse_cat
```

### Linting and Formatting
No linting tools are currently configured. When adding them, use:
```bash
# Format code (ruff recommended)
ruff format .

# Lint code
ruff check .
```

## Code Style Guidelines

### Type Hints
- Use Python 3.14+ type syntax (e.g., `list[Cat]`, `dict[str, int]`)
- Use union types for complex scenarios: `str | None` is acceptable
- `from __future__ import annotations` is present in files that are straight ported from
  MewgenicsBreedingManager, but new code should use standard type hints without it and rely on
  Python 3.14's native deferred evaluation of annotations.

### Naming Conventions
- **Classes**: PascalCase (e.g., `Cat`, `BinaryReader`, `SaveData`)
- **Functions/variables**: snake_case (e.g., `parse_save`, `_valid_str`)
- **Private methods/attributes**: prefix with underscore (e.g., `_parent_uid_a`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `STAT_NAMES`, `ROOM_DISPLAY`)
- **Private module-level constants**: UPPER_SCANE with underscore prefix (e.g., `_IDENT_RE`, `_JUNK_STRINGS`)

### Imports
- Use relative imports within packages: `from .binary import BinaryReader`
- Use absolute imports between packages: `from mewgenics_parser.cat import Cat`
- Group imports: stdlib first, then third-party, then local
- Use trailing commas in multi-line imports

### Dataclasses
- Use `@dataclass` for data models
- Use `slots=True` for memory efficiency
- Use `init=False` when custom `__init__` is needed (see `cat.py`)
- Use `field(default=None, repr=False)` for computed/private fields
- Use `field(default_factory=list)` for mutable defaults

### Docstrings
- Use """triple quotes""" for module-level and public function docstrings
- Follow Google-style docstrings for functions with Args/Returns sections
- Keep docstrings concise but descriptive

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

### Private Attributes Pattern
For dataclasses, store raw/internal data with underscore prefix and `repr=False`:
```python
@dataclass(slots=True)
class Cat:
    name: str
    _raw: bytes = field(repr=False, default=b"")
    _uid_int: int = field(repr=False, default=0)
```

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

### Save File Parsing
Use SQLite read-only mode for .sav files:
```python
conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
```

### Property Methods
Use `@property` for computed attributes:
```python
@property
def room_display(self) -> str:
    """Return human-readable room name."""
    return ROOM_DISPLAY.get(self.room, self.room)
```

## Important Notes

1. **Do not modify MewgenicsBreedingManager submodule** - it's a reference for understanding the game data format
2. **This is a new project** with code adapted from MewgenicsBreedingManager, but with different conventions - follow the packages/ directory style
3. **Python 3.14+ required** - use the `.python-version` file as reference
