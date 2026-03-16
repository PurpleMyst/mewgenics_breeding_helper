# mewgenics_breeding_helper

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, Claude). Review all code before use.**

A Python-based tool for optimizing breeding operations in the game Mewgenics. Features a DearPyGui-based UI for room optimization, cat management, and breeding pair analysis.

![Main UI](/.github/screenshots/main.png?raw=true "Main UI")

## Features

- **Room Optimization**: Algorithm for optimal cat placement across breeding, general, and fighting rooms
- **Seed & Pull Algorithm**: Multi-partner breeding support with throughput caps (prevents gender imbalance)
- **EY Support**: Eternal Youth cats treated as free room buffs (+1 stim each, 0 capacity cost)
- **Risk Assessment**: Inbreeding risk calculation with configurable thresholds
- **Trait Planning**: Mark favorable traits for targeted breeding
- **Lover/Hater Tracking**: Visual display of relationships in cat inspector
- **Gay Marking**: Same-sex breeding preference support
- **Auto-save**: Configuration persistence across sessions

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Mewgenics game (for `resources.gpak`)

## Project Structure

```
mewgenics_breeding_helper/
├── packages/
│   ├── mewgenics_parser/           # Save file parsing
│   ├── mewgenics_scorer/           # Pair scoring logic
│   ├── mewgenics_room_optimizer/  # Optimization algorithm
│   └── mewgenics_room_optimizer_ui/  # DearPyGui UI
├── MewgenicsBreedingManager/       # Reference submodule (do not modify)
├── .github/screenshots/            # UI screenshots
└── pyproject.toml                 # Workspace config
```

## Installation

```bash
# Clone the repository
git clone https://github.com/PurpleMyst/mewgenics_breeding_helper.git
cd mewgenics_breeding_helper

# Install dependencies (requires uv)
uv sync

# Run the UI
uv run room-optimizer
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
| `[!]` | Inbred (shared ancestors) | Red |
| `[*]` | Favorable trait match | Green |
| `[EY]` | Eternal Youth passive | Teal |

## Configuration

### Optimization Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Min Stats | Minimum total base stats for breeding candidates | 0 |
| Max Risk % | Maximum inbreeding risk allowed (0-100) | 20.0 |
| Minimize Variance | Prioritize pairs with similar stats for consistent offspring | On |
| Avoid Lovers | Exclude mutual lover pairs from breeding | On |
| Prefer High Libido | Favor high libido cats for faster breeding cycles | On |
| Prefer High Charisma | Favor high charisma for better breeding odds | On |
| Base Stimulation | Default stimulation for unconfigured rooms | 50.0 |

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
- **Stats**: All 7 base stats
- **Abilities**: Active Abilities, Passive Abilities, Mutations
- **Options**: Same-Sex Breeder toggle

EY cats display with a teal `[EY]` badge and are excluded from capacity calculations.

## Sandbox Mode

The third tab in Room Details lets you test any breeding combination:

1. Select Parent A from dropdown
2. Select Parent B from dropdown
3. View results:
   - Expected Quality score
   - Risk %
   - Badges (Lovers, Libido, Aggression, Inbred, Favorable Traits)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No gpak found" | Copy `resources.gpak` to project root or install directory |
| "No cats loaded" | Verify the save file path is correct |
| Empty cat list | Ensure save file has cats with "In House" status |
| Age shows 100 | Age is capped at 100 unless cat has Eternal Youth passive |

## Algorithm

The optimizer uses a "Seed and Pull" clustering approach:

1. **EY Buff Placement**: All Eternal Youth cats are placed in the breeding room with highest base stimulation (they cost 0 capacity)

2. **True Stimulation**: Each room's final stimulation = base_stim + EY_cats_count

3. **Seed & Pull**:
   - Score all valid pairs using baseline stimulation (50.0)
   - Sort pairs by quality
   - Seed unassigned pairs into rooms
   - Pull unpaired cats into existing rooms when compatible

4. **Throughput Cap**: Each gender limited to max_cats - 2 in breeding rooms

5. **Cross-Product Rescoring**: Final pairs re-scored with room's actual True Stimulation

## Known Issues

- Age parsing may occasionally show incorrect values (capped at 100 unless Eternal Youth)
- Large save files may take time to parse

## Credits

- Original idea and reference: [MewgenicsBreedingManager](https://github.com/frankieg33/mewgenics_breeding_manager) by frankieg33
- Developed with assistance from AI tools
