# Mewgenics Breeding Helper

[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-orange)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub
Issues](https://img.shields.io/github/issues/PurpleMyst/mewgenics_breeding_helper)](https://github.com/PurpleMyst/mewgenics_breeding_helper/issues)

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, Claude). Review all code before use.**

A Python-based tool for optimizing breeding operations in the game [Mewgenics](https://store.steampowered.com/app/686060/Mewgenics/). Features a DearPyGui-based UI for room optimization, cat management, and breeding pair analysis.

![Main UI](/.github/screenshots/main.png?raw=true "Main UI")

## Features

- **Room Optimization**: Parallel Simulated Annealing optimizer with Metropolis acceptance
- **Save File Parsing**: Parse Mewgenics `.sav` files and `resources.gpak` for game data
- **Cat Management**: View detailed stats, traits, and relationships
- **Breeding Planner**: Mark favorable traits for targeted breeding
- **Risk Assessment**: Game-accurate inbreeding risk calculation with configurable thresholds
  - **Disorder Chance**: Probability of birth defect disorder (base 2% + CoI penalty)
  - **Part Defect Chance**: Probability of mutated part defects (1.5 × CoI)
  - **Combined Malady**: Union probability of any birth defect
- **Lover/Hater Tracking**: Visual display of relationships in cat inspector
- **Gay Marking**: Same-sex breeding preference support
- **Eternal Youth Support**: EY cats treated as free room buffs (+1 stim each, 0 capacity cost)
- **Auto-save**: Configuration persistence across sessions

## System Architecture

```
mewgenics_breeding_helper/
├── packages/
│   ├── mewgenics_parser/           # Save file parsing, trait definitions
│   │   ├── binary.py              # BinaryReader for parsing binary data
│   │   ├── cat.py                 # Cat data model
│   │   ├── gpak.py                # GPAK file handling
│   │   ├── save.py                # Save file parsing
│   │   ├── traits.py              # Trait domain models
│   │   └── trait_dictionary.py    # Trait constants
│   ├── mewgenics_scorer/          # Pair scoring logic
│   │   ├── factors.py             # Breeding factor calculations
│   │   ├── ancestry.py            # Ancestry and inbreeding calculations
│   │   ├── compatibility.py       # Pair compatibility scoring
│   │   ├── inheritance.py         # Game-accurate inheritance simulation
│   │   └── types.py               # Type definitions
│   ├── mewgenics_room_optimizer/  # Optimization algorithm
│   │   └── optimizer.py           # Parallel Simulated Annealing implementation
│   └── mewgenics_room_optimizer_ui/ # DearPyGui UI application
│       └── ui.py                  # Main UI implementation
└── MewgenicsBreedingManager/       # Reference submodule (do not modify)
```

### Algorithm

The optimizer uses **Parallel Simulated Annealing**:

1. **Parallel Workers**: Uses `cpu_count() - 1` workers running independent SA searches
2. **Temperature Schedule**: Exponential cooling from configured temperature (default 100.0) down to 0.1
3. **Neighbor Generation**: 
   - 50% move operation: Move one cat to a different room
   - 50% swap operation: Swap two cats between rooms
4. **Metropolis Acceptance**: Accepts worse solutions with probability `exp(delta / T)`
5. **Evaluation**:
   - Expected breed quality = average quality per valid pair
   - Dilution penalty = `valid_cats / total_cats` (penalizes gender imbalance)
   - Throughput boost (when Maximize Throughput enabled) = `concurrent_breeds ^ 1.5`

### Inheritance Math (Game-accurate)

The scorer implements the exact game mechanics:

- **Stat Inheritance**: `P(higher) = (1.0 + 0.01*Stimulation) / (2.0 + 0.01*Stimulation)`
- **Spell Chance**: `0.2 + 0.025*Stimulation` (guaranteed at 32+)
- **Passive Chance**: `0.05 + 0.01*Stimulation` (guaranteed at 95+)
- **Disorder Inheritance**: 15% from each parent (flat rate)
- **Birth Defect**: `0.02 + 0.4 * max(Inbreeding - 0.2, 0.0)`

See [docs/breeding_notes.txt](docs/breeding_notes.txt) for complete details.

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Mewgenics game (for `resources.gpak`)

## Installation

```bash
# Clone the repository
git clone https://github.com/PurpleMyst/mewgenics_breeding_helper.git
cd mewgenics_breeding_helper

# Install dependencies (requires uv)
uv sync

# Run the UI
just run
# Or: uv run room-optimizer
```

The application will look for `resources.gpak` in:
1. The current directory
2. The game default location: `C:\Program Files (x86)\Steam\steamapps\common\Mewgenics\resources.gpak`

## Usage

### Quick Start

1. **Load a save file**: Click "Load Save" and select your `.sav` file
2. **Configure rooms**: Adjust room types, capacities, and base stimulation in the Rooms tab
3. **Set parameters**: Configure breeding parameters in the Optimization tab
4. **Mark traits**: Add favorable traits in the Planner tab (optional)
5. **Mark gay cats**: Toggle same-sex breeding preference in the Inspector (optional)
6. **Optimize**: Click "Optimize Rooms" to generate breeding pairs

### Room Types

| Type | Purpose | Capacity Limit |
|------|---------|----------------|
| Breeding | Optimized for kitten production | Yes (configurable) |
| Fighting | Defensive cats for expeditions | No limit |
| General | Mixed use / storage | Yes (configurable) |
| None | Disabled / unused | - |

### Misplaced Tab

The Room Details panel includes a "Misplaced" tab showing cats currently in a room but assigned to a different room by the optimizer. Use this to identify cats that weren't moved to their optimal locations.

### Stimulation

- **Base Stimulation**: Default 50.0, configurable per room
- **True Stimulation**: `base_stim + Eternal_Youth_cats` in the room
- Higher stimulation increases the chance offspring inherit higher stats from parents

### Factor Columns

The Pairs table displays individual columns for each breeding factor:

| Column | Description | Color Coding |
|--------|-------------|--------------|
| **Lovers** | Whether both cats are mutual lovers | Green = Yes, Gray = No |
| **Libido** | Combined libido factor (0.0-1.0) | Green >= 0.6 |
| **Aggr** | Combined aggression factor (0.0-1.0) | Green <= 0.4, Red > 0.4 |
| **Char** | Combined charisma factor (0.0-1.0) | Green >= 0.4 |
| **Var** | Stat variance (lower = more consistent) | Green <= 5, Red > 10, Yellow 5-10 |
| **Trait EV** | Trait Expected Value | Green > 0, Gray = 0 |

### Location Colors (in tables)

| Color | Meaning |
|-------|---------|
| Green | Cat is in the correct assigned room |
| Red | Cat is in the wrong room |
| Yellow | Cat is not assigned to any room |

### Cat Inspector

Click any cat to view detailed information:

- **Bio**: Name, Gender, Age, Status, Room, Lovers, Haters
- **Stats**: All 7 base stats (STR, DEX, CON, INT, SPD, CHA, LCK)
- **Traits**: Active Abilities, Passive Abilities, Disorders, Body Parts
- **Options**: Same-Sex Breeder toggle

## Configuration

### Optimization Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Min Stats | Minimum total base stats for breeding candidates | 0 |
| Max Risk % | Maximum combined malady probability allowed (0-100) | 20 |
| Minimize Variance | Prioritize pairs with similar stats | On |
| Avoid Lovers | Exclude mutual lover pairs from breeding | On |
| Prefer High Libido | Favor high libido cats for faster cycles | On |
| Prefer High Charisma | Favor high charisma for better odds | On |
| Base Stimulation | Default stimulation for unconfigured rooms | 50.0 |
| Maximize Throughput | Apply density exponent and maximize pairs | Off |

### SA Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Temperature | Initial temperature for SA (higher = more exploration) | 100.0 |
| Cooling Rate | Temperature multiplier per step (0.8-0.99) | 0.95 |
| Neighbors/Temp | Number of neighbor states evaluated per temperature | 200 |

### Favorable Traits (Breeding Planner)

Mark specific mutations, passives, abilities, or body parts you want to propagate:

- Select traits from alive ("In House") cats only
- Supports active abilities, passive abilities, body parts, and disorders
- Each trait has a weight (1-10) that affects pair scoring
- Traits display with `[*]` prefix when marked as favorable

### Gay Marking

Some cats prefer same-sex breeding. To mark a cat as gay:

1. Select the cat in the Cats tab
2. Open the Inspector panel
3. Check "Same-Sex Breeder"

Gay cats will only breed with Female cats (not other gay cats).

## Development

```bash
# Run all tests
just test-all

# Run type checker
just ty

# Run linter
just lint

# Auto-fix lint issues
just fix
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No gpak found" | Copy `resources.gpak` to project root or install directory |
| "No cats loaded" | Verify the save file path is correct |
| Empty cat list | Ensure save file has cats with "In House" status |
| Age shows 100 | Age is capped at 100 unless cat has Eternal Youth passive (500 cap) |

## Known Issues

- Large save files may take time to parse
- Cat Inspector does not display abilities as upgraded even when the cat has the upgraded version

## Contributing

Contributions are welcome! Please ensure:

1. **Tests pass**: Run `just test-all`
2. **Type check passes**: Run `just ty`
3. **Linting passes**: Run `just lint` and `just fix` if needed
4. **Formatting**: Code is formatted with `ruff format .`

## Credits

- Original idea and reference: [MewgenicsBreedingManager](https://github.com/frankieg33/mewgenics_breeding_manager) by frankieg33
- Favicon is an emoji from Twemoji, licensed under CC-BY 4.0 and obtained from [favicon.io](https://favicon.io/emoji-favicons/cat)
- [Breeding notes by the excellent SciresM](https://gist.github.com/SciresM/95a9dbba22937420e75d4da617af1397)
- Developed with assistance from AI tools
