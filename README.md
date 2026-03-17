# mewgenics_breeding_helper

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, Claude). Review all code before use.**

A Python-based tool for optimizing breeding operations in the game Mewgenics. Features a DearPyGui-based UI for room optimization, cat management, and breeding pair analysis.

![Main UI](/.github/screenshots/main.png?raw=true "Main UI")

## Features

- **Room Optimization**: Parallel Simulated Annealing optimizer with Metropolis acceptance
- **SA Optimizer**: Configurable temperature, cooling rate, and neighbor evaluation
- **EY Support**: Eternal Youth cats treated as free room buffs (+1 stim each, 0 capacity cost)
- **Risk Assessment**: Game-accurate inbreeding risk calculation with configurable thresholds
  - **Disorder Chance**: Probability of birth defect disorder (base 2% + CoI penalty)
  - **Part Defect Chance**: Probability of mutated part defects (1.5 × CoI)
  - **Combined Malady**: Union probability of any birth defect
- **Trait Planning**: Mark favorable traits for targeted breeding
- **Lover/Hater Tracking**: Visual display of relationships in cat inspector
- **Gay Marking**: Same-sex breeding preference support
- **Auto-save**: Configuration persistence across sessions

## Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Mewgenics game (for `resources.gpak`)

## Project Structure

```
mewgenics_breeding_helper/
├── pyproject.toml                 # Root workspace config (uv)
├── justfile                       # Development commands
├── packages/
│   ├── mewgenics_parser/          # Save file parsing
│   ├── mewgenics_scorer/          # Pair scoring logic
│   ├── mewgenics_room_optimizer/ # Optimization algorithm
│   └── mewgenics_room_optimizer_ui/  # DearPyGui UI
├── MewgenicsBreedingManager/      # Reference submodule (do not modify)
├── .github/screenshots/           # UI screenshots
└── tests/                        # Test suites
```

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

## Quick Start

1. **Load a save file**: Click "Load Save" and select your `.sav` file
2. **Configure rooms**: Adjust room types, capacities, and base stimulation in the Rooms tab
3. **Set parameters**: Configure breeding parameters in the Optimization tab
4. **Mark traits**: Add favorable traits in the Planner tab (optional)
5. **Mark gay cats**: Toggle same-sex breeding preference in the Inspector (optional)
6. **Optimize**: Click "Optimize Rooms" to generate breeding pairs

## Room Types

| Type | Purpose | Capacity Limit |
|------|---------|----------------|
| Breeding | Optimized for kitten production | Yes (configurable) |
| Fighting | Defensive cats for expeditions | No limit |
| General | Mixed use / storage | Yes (configurable) |
| None | Disabled / unused | - |

### Misplaced Tab

The Room Details panel includes a "Misplaced" tab showing cats currently in a room but assigned to a different room by the optimizer. Use this to identify cats that weren't moved to their optimal locations.

## Stimulation

- **Base Stimulation**: Default 50.0, configurable per room
- **True Stimulation**: `base_stim + Eternal_Youth_cats` in the room
- Higher stimulation increases the chance offspring inherit higher stats from parents

## Badge Legend

| Badge | Meaning | Color |
|-------|---------|-------|
| `[<3]` | Mutual lovers (breeding pair) | Pink |
| `[+]` | High libido bonus | Gold |
| `[-]` | Low aggression bonus | Blue |
| `[!]` | High inbreeding risk (50%+ combined malady) | Red |
| `[*]` | Favorable trait match | Green |
| `[EY]` | Eternal Youth passive | Teal |

### Location Colors (in tables)

| Color | Meaning |
|-------|---------|
| Green | Cat is in the correct assigned room |
| Red | Cat is in the wrong room |
| Yellow | Cat is not assigned to any room |

## Configuration

### Optimization Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Min Stats | Minimum total base stats for breeding candidates | 0 |
| Max Risk % | Maximum combined malady probability allowed (0-100) | 20 |
| Minimize Variance | Prioritize pairs with similar stats for consistent offspring | On |
| Avoid Lovers | Exclude mutual lover pairs from breeding | On |
| Prefer High Libido | Favor high libido cats for faster breeding cycles | On |
| Prefer High Charisma | Favor high charisma for better breeding odds | On |
| Base Stimulation | Default stimulation for unconfigured rooms | 50.0 |
| Density Bonus | Apply exponent boost (`concurrent_breeds ^ 1.5`) to room quality | Off |

### SA Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Temperature | Initial temperature for SA (higher = more exploration) | 100.0 |
| Cooling Rate | Temperature multiplier per step (0.8-0.99) | 0.95 |
| Neighbors/Temp | Number of neighbor states evaluated per temperature | 200 |

### Favorable Traits (Breeding Planner)

Mark specific mutations, passives, or abilities you want to propagate through your breeding program.

- Select traits from alive ("In House") cats only
- Each trait has a weight (1-10) that affects pair scoring
- Higher weight = higher priority for that trait in breeding decisions
- Traits are displayed in the Inspector with `[*]` prefix when marked as favorable

### Gay Marking

Some cats prefer same-sex breeding. To mark a cat as gay:

1. Select the cat in the Cats tab
2. Open the Inspector panel
3. Check "Same-Sex Breeder"

Gay cats will only breed with Female cats (not other gay cats).

### Throughput Cap

To prevent gender imbalance in breeding rooms, each gender is limited to `max_cats - 2` cats per breeding room. This prevents scenarios like 5 males / 1 female in a 6-cat room.

## Cat Inspector

Click any cat to view detailed information:

- **Bio**: Name, Gender, Age, Status, Room, Lovers, Haters
- **Stats**: All 7 base stats (STR, DEX, CON, INT, SPD, CHA, LCK)
- **Abilities**: Active Abilities, Passive Abilities, Mutations
- **Options**: Same-Sex Breeder toggle

EY cats display with a teal `[EY]` badge and are excluded from capacity calculations.

## Sandbox Mode

The third tab in Room Details lets you test any breeding combination:

1. Select Parent A from dropdown
2. Select Parent B from dropdown
3. View results:
   - Expected Quality score
   - Risk breakdown: Disorder %, Part Defect %, Combined %
   - Badges (Lovers, Libido, Aggression, Inbred, Favorable Traits)

## Algorithm

The optimizer uses Parallel Simulated Annealing:

1. **Parallel Workers**: Uses `cpu_count() - 1` workers running independent SA searches

2. **Temperature Schedule**: Exponential cooling from configured temperature (default 100.0) down to 0.1

3. **Neighbor Generation**: 
   - 50% move operation: Move one cat to a different room
   - 50% swap operation: Swap two cats between rooms

4. **Metropolis Acceptance**: Accepts worse solutions with probability `exp(delta / T)`

5. **Evaluation**:
   - Expected breed quality = average quality per valid pair
   - Dilution penalty = `valid_cats / total_cats` (penalizes gender imbalance)
   - Density bonus (when enabled) = `concurrent_breeds ^ 1.5`

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
| Age shows 100 | Age is capped at 100 unless cat has Eternal Youth passive |

## Known Issues

- Large save files may take time to parse

## Credits

- Original idea and reference: [MewgenicsBreedingManager](https://github.com/frankieg33/mewgenics_breeding_manager) by frankieg33
- Developed with assistance from AI tools
