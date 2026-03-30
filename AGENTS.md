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

## Addendum: Shell Constraints (opencode / PowerShell)

**CRITICAL INSTRUCTION FOR AGENTS:** The execution environment (`opencode`) uses **PowerShell (`pwsh.exe`)**, not `bash`, `zsh`, or `cmd.exe`. You must strictly adhere to the following PowerShell conventions when generating shell commands, passing arguments, or writing scripts.

### 1. Use PowerShell Syntax
PowerShell uses different syntax than `bash` or `cmd.exe`:
* **Variables:** `$VAR` (not `%VAR%` like cmd.exe)
* **String Grouping:** Both `"double"` and `'single'` quotes work for strings
* **Command Separation:** Use `;` for multiple commands on one line
* **Line Continuation:** Use backtick (`` ` ``) to continue long commands across lines```powershell
uv run ruff check `
  --fix `
  packages/mewgenics_parser
```

### 2. Comparison Operators in PowerShell
PowerShell uses different comparison operators than Python or bash:
* **Equality:** `-eq` (not `==`)
* **Inequality:** `-ne` (not `!=`)
* **Greater/Less:** `-gt`, `-lt`, `-ge`, `-le`
* **String matching:** `-like`, `-match`, `-contains`
* **Boolean operators:** `-and`, `-or`, `-not` (or `!`)

### 3. Pipe and Redirection
PowerShell has powerful pipe capabilities:
* **Pipe output:** `|` works like bash, but objects flow through, not just text
* **To file:** `| Out-File -FilePath output.txt` or `> output.txt`
* **Null output:** `| Out-Null` or `> $null`
* **Append:** `>> output.txt` or `| Add-Content output.txt`

### 4. Environment Variables
* **Set inline:** `$env:VAR = "value"`
* **Use in command:** `$env:VAR` or `${env:VAR}`
* **Example:** `$env:PYTHONPATH = "src"; uv run pytest`

### 5. Working Directory
PowerShell uses `Set-Location` or `cd` for changing directories:
* `cd packages/mewgenics_parser` - works like bash
* `Push-Location` / `Pop-Location` - save/restore directory stack

### 6. Command Substitution
PowerShell supports command substitution with `$()`:
```powershell
$files = Get-ChildItem -Filter *.py
uv run ruff check $files
```

### Quick Reference: Bash vs. PowerShell

| Feature | Bash (Do Not Use) | PowerShell (Use This) |
| :--- | :--- | :--- |
| **Variables** | `$VAR` or `${VAR}` | `$VAR` or `${VAR}` |
| **String Quotes** | `"double"` or `'single'` | `"double"` or `'single'` |
| **Line Continuation** | `\` | `` ` `` (backtick) |
| **Command Separation** | `;` or `&&` | `;` (use `;` for chaining) |
| **Null Output** | `> /dev/null` | `| Out-Null` or `> $null` |
| **Path Separators** | `/` preferred | Both `/` and `\` work |
| **Environment Vars** | `$VAR` | `$env:VAR` |
| **Array/List** | `arr=(a b c)` | `$arr = @('a', 'b', 'c')`|

**Agent Directive Summary:** Use PowerShell syntax for all shell commands. When in doubt, prefer Python scripts (`uv run python ...`) for complex logic, file I/O, and string manipulation rather than complex shell scripting.

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

### Breeding Ineligibility
- Cats with `age <= 1` are kittens and cannot breed
- Cats with Eternal Youth disorder cannot breed
- Use `cat.can_breed()` to check eligibility (returns `True` for adults without EY)
- Use `cat.is_kitten()` to check if cat is a kitten (default max_age=1)

### Room Comfort Penalty
- Comfort is reduced by 1 for each cat above 4 in a room
- Formula: `effective_comfort = max(0, comfort - max(0, n_cats - 4))`
- Use `_effective_comfort(base_comfort, n_cats)` from `mewgenics_breeding.monte_carlo` or `mewgenics_breeding.heuristic`

### Minimum Compatibility Threshold
- Breeding requires compatibility >= 0.05 (defined in `MIN_BREEDING_COMPAT`)
- Pairs with compatibility below this threshold cannot produce kittens

### NURSERY Room Type
- Kittens (age <= 1) are assigned to NURSERY rooms
- Assigned by descending ENS (Expected Net Score) value
- Overflow kittens use adult placement logic (GENERAL/FIGHTING/etc.)
- Use `RoomType.NURSERY` in room configurations
