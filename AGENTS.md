# Agent Guidelines for mewgenics_breeding_helper

This project is a Python-based tool for parsing Mewgenics save files and optimizing breeding strategies. It uses a monorepo structure with multiple packages under `packages/`.

## Project Structure

```
mewgenics_breeding_helper/
├── pyproject.toml              # Root workspace config (uv)
├── packages/
│   ├── mewgenics_parser/       # Save file parsing, trait definitions
│   │   └── mewgenics_parser/
│   │       ├── binary.py       # BinaryReader helper
│   │       ├── cat.py          # Cat data model (dataclass)
│   │       ├── constants.py     # Constants and regex patterns
│   │       ├── gpak.py         # GPAK file handling
│   │       ├── save.py         # Save file parsing
│   │       ├── traits.py       # Trait domain models
│   │       ├── trait_dictionary.py  # Trait constants
│   │       ├── visual.py       # Visual mutation handling
│   │       └── data/           # Static data (abilities, visual names)
│   ├── mewgenics_scorer/       # Trait scoring logic
│   ├── mewgenics_breeding/     # Breeding logic and algorithms
│   ├── mewgenics_room_optimizer/   # Room optimization algorithm
│   └── mewgenics_room_optimizer_ui/ # DearPyGui UI application
└── MewgenicsBreedingManager/   # Submodule - reference only, do not modify
```

## Commands

### Development
```bash
uv sync                     # Install dependencies
uv sync --group dev         # Install dev dependencies
uv add <package> -p packages/mewgenics_parser  # Add dependency
uv run room-optimizer       # Run the UI application
```

### Testing
```bash
uv run pytest                           # Run all tests
uv run pytest tests/test_cat.py         # Run single test file
uv run pytest tests/test_cat.py::test_parse_cat  # Run single test function
uv run pytest --cov=mewgenics_parser   # Run with coverage
```

### Linting and Formatting
```bash
uv run ruff format .      # Format code
uv run ruff check .       # Lint code
uv run ruff check --fix . # Fix auto-fixable issues
```

### Type Checking
```bash
uv run ty check .                         # Check all
uv run ty check packages/mewgenics_parser/mewgenics_parser/cat.py
```

## Code Style Guidelines

### Type Hints
- Use Python 3.13+ type syntax: `list[Cat]`, `dict[str, int]`
- Prefer `str | None` over `Optional[str]`
- `from __future__ import annotations` only for ported code

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `Cat`, `BinaryReader` |
| Functions/variables | snake_case | `parse_save`, `_valid_str` |
| Private methods | `_prefix` | `_parent_uid_a` |
| Constants | UPPER_SNAKE | `STAT_NAMES`, `ROOM_DISPLAY` |
| Private module constants | _UPPER_SNAKE | `_IDENT_RE`, `_JUNK_STRINGS` |

### Imports
- Relative within packages: `from .binary import BinaryReader`
- Absolute between packages: `from mewgenics_parser.cat import Cat`
- Group order: stdlib → third-party → local; use trailing commas

### Dataclasses
- Use `@dataclass(slots=True)` for data models
- Use `init=False` when custom `__init__` is needed
- Use `field(default=None, repr=False)` for computed/private fields
- Use `field(default_factory=list)` for mutable defaults
- Prefix raw/internal data with underscore, `repr=False`

### Error Handling
- Avoid broad `except Exception` unless specific handling isn't possible
- Prefer specific exception types when known
- Avoid silent exception swallowing unless explicitly intended

### Formatting
- 4 spaces indentation (no tabs)
- Max line length: 100 characters (soft guideline)
- Blank lines: 2 between top-level definitions, 1 between methods
- Use underscores in large numbers: `4_294_967_296`

### Performance
- Use `frozenset` for constant lookup sets
- Prefer dataclasses over dictionaries for structured data

## Key Patterns

### Binary Parsing
```python
r = BinaryReader(data)
value = r.u32()        # unsigned 32-bit
value = r.i32()        # signed 32-bit
value = r.u64()        # unsigned 64-bit
value = r.f64()        # 64-bit float
string = r.str()        # length-prefixed UTF-8 string
string = r.utf16str()  # length-prefixed UTF-16LE string
```

### Trait Operations
```python
from mewgenics_parser.traits import extract_traits_from_cat, create_trait, TraitCategory

traits = extract_traits_from_cat(cat)
trait = create_trait(TraitCategory.PASSIVE_ABILITY, "Sturdy")
name = trait.get_display_name(game_data)
desc = trait.get_description(game_data)
```

### Properties
```python
@property
def room_display(self) -> str:
    return ROOM_DISPLAY.get(self.room, self.room)
```

## Important Notes

1. **Do not modify MewgenicsBreedingManager submodule** - reference only
2. **Python 3.13+ required** - check `.python-version`
3. **Use uv for all package management** - never pip directly
4. **Use uv run for all tools** - ruff, ty, pytest, etc.

## Addendum: Shell Constraints (opencode / cmd.exe)

**CRITICAL INSTRUCTION FOR AGENTS:** The execution environment (`opencode`) uses `cmd.exe`, **not** `bash`, `zsh`, or `pwsh`. You must strictly adhere to the following `cmd.exe` limitations when generating shell commands, passing arguments, or writing scripts.

### 1. No Multiline Strings or Arguments
Unlike `bash`, `cmd.exe` cannot handle multiline strings passed as command-line arguments. If you attempt to pass an argument containing a newline character (`\n` or a literal line break), `cmd.exe` will immediately truncate the command at the first newline or throw a syntax error.
* **Bad (Bash style):** `uv run python script.py --desc "Line 1\nLine2"`
* **Bad (Bash style):** Passing a raw multiline JSON string directly into a CLI argument.
* **The Fix:** If a script requires complex or multiline string data (like a JSON payload or a long trait description), **write the data to a temporary file first**, and pass the file path to the command.

### 2. Single Quotes Do Not Group Arguments
In `bash` and PowerShell, single quotes (`'`) group arguments and treat the contents as literal strings. In `cmd.exe`, **single quotes have no special meaning** and are treated as literal characters passed directly to the underlying program. 
* **Bad:** `uv run python -c 'print("Hello")'` (Fails: `cmd.exe` passes the single quotes to Python, causing a syntax error).
* **Good:** `uv run python -c "print('Hello')"` (Always use double quotes to group arguments in `cmd.exe`).

### 3. Line Continuation
Do not use the bash backslash (`\`) or PowerShell backtick (`` ` ``) to split long commands across multiple lines. 
* **cmd.exe uses the caret (`^`):** ```cmd
  uv run ruff check ^
    --fix ^
    packages/mewgenics_parser
  ```
* *Warning:* Avoid trailing spaces after the `^`, as this will break the continuation. When in doubt, generate the command as a single, continuous line.

### 4. No Command Substitution
`cmd.exe` does not support `bash`-style command substitution like `$(command)` or `` `command` ``. You cannot dynamically pass the output of one command as an argument to another inline.
* **Bad:** `uv run script.py --id $(cat id.txt)`
* **The Fix:** You must use the `FOR /F` loop syntax, or much preferably, handle the logic inside a Python script rather than relying on the shell.

### 5. Variable Expansion and Delayed Expansion
Variables are expanded using `%VAR%`, not `$VAR`. Furthermore, `cmd.exe` evaluates variables at parse time, not execution time, which causes nested logic or loops to fail unless `EnableDelayedExpansion` is used.
* **Environment Variables:** Use `set VAR=value` (no quotes around the value unless you want the quotes included).
* **Inline usage:** `set MY_FILE=cat.json && uv run python parse.py %MY_FILE%`

### 6. Command Length Limits
`cmd.exe` has a strict hard limit of **8,191 characters** per command line. If you are chaining commands or passing massive base64-encoded strings directly in the terminal, the command will silently truncate or fail. Again, rely on file I/O for large data transfers.

### Quick Reference: Bash vs. cmd.exe

| Feature | Bash (Do Not Use) | cmd.exe (Required) |
| :--- | :--- | :--- |
| **Argument Grouping** | `"text"` or `'text'` | `"text"` **ONLY** |
| **Environment Variables** | `$VAR` or `${VAR}` | `%VAR%` |
| **Inline Env Assignment** | `VAR=val uv run ...` | `set VAR=val && uv run ...` |
| **Command Substitution** | `$(ls)` | Requires `FOR /F` |
| **Line Continuation** | `\` | `^` |
| **Path Separators** | `/` | `\` (Though `uv` and Python accept `/`) |
| **Null Output** | `> /dev/null` | `> NUL` |

**Agent Directive Summary:** Keep shell interactions as simple and atomic as possible. Rely on Python (`uv run python ...`) to do the heavy lifting for data parsing, file I/O, and string manipulation rather than attempting complex shell scripting in `cmd.exe`.

## Mewgenics Game Reference

Reference: https://mewgenics.wiki.gg/

### Cat Stats
- **Base Stats (3-7 range):** STR, DEX, CON, INT, SPD, CHA, LCK
- **Derived:** HP = CON × 4, Mana max = CHA × 3
- **Luck:** Each point from baseline (5) adds 10% chance for extra die roll (best result); +2% crit chance per point
- **Base stats only inherit** - temporary modifications from items/injuries are ignored in breeding

### Room Stats (House-wide or per-room)
| Stat | Effect |
|------|--------|
| **Appeal** | Stat quality/diversity of stray cats (global) |
| **Comfort** | Breeding frequency; -1 per cat above 4 in room |
| **Stimulation** | **Critical for breeding optimization** - higher = better inheritance |
| **Health** | Aging speed, injury/disorder recovery chance |
| **Mutation** | Chance for overnight mutations |

### Stat Inheritance Formula
```
P(higher stat) = (1.0 + 0.01 × Stimulation) / (2.0 + 0.01 × Stimulation)
```
At 0 Stimulation: 50% | At 50: ~60% | At 100: ~66.6%

### Ability Inheritance
- **First Spell:** 0.20 + 0.025 × Stimulation (guaranteed at 32+ Stimulation)
- **Second Spell:** 0.02 + 0.005 × Stimulation
- **Passive:** 0.05 + 0.01 × Stimulation (guaranteed at 95+ Stimulation)
- **Skill Share+** overrides: guarantees parent's "other passive" passes

### Disorder Inheritance
- **15% chance** from each parent (independent rolls)
- **Unaffected by furniture/Stimulation**
- Birth-defect disorders: 2% base + 0.4 × clamp(inbreeding - 0.2, 0, 1)

### Body Part/Mutation Inheritance
- **80%** chance all parts inherit normally
- **20%** chance one random part-set is randomly generated
- When only one parent has mutation: uses same P(higher) formula
- Max 10 mutations on bred kittens (symmetry enforcement)

### Inbreeding System
- **Strays always 0% inbred**
- Closeness 4 or closer raises coefficient; 5+ distance reduces it
- Birth defects only appear at >5% inbreeding coefficient
- Formula: f = sum of 0.5^(n+1) × (1 + f_ancestor)

### Gender/Reproduction
- **Male, Female, Neutral** (? / Spidercats)
- Neutral can breed with both; 10% of cats born Neutral
- Gayness/Libido/Aggression are hidden stats affecting breeding behavior

### Fertility
- Hidden stat (1.0-1.25) affecting twin probability
- Average twin chance: ~17.36%
- Twins guaranteed if combined_fertility > 1.0, with extra chance up to 56.25%

### Key Classes
Fighter, Hunter, Mage, Tank, Cleric, Thief, Necromancer, Tinkerer, Butcher, Druid, Psychic, Monk, Jester

### Disorders
- Similar to passive abilities but don't count toward passive cap
- Max 2 disorders per cat; some are contagious
- Can be removed by high Health room or events
