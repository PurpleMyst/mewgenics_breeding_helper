# mewgenics_breeding_helper

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, Claude). Review all code before use.**

A Python-based tool for optimizing breeding operations in the game Mewgenics. Features a DearPyGui-based UI for room optimization, cat management, and breeding pair analysis.

## Features

- **Room Optimization**: Algorithm for optimal cat placement across breeding, general, and fighting rooms
- **Seed & Pull Algorithm**: Multi-partner breeding support with throughput caps (prevents gender imbalance)
- **EY Support**: Eternal Youth cats treated as free room buffs (+1 stim each, 0 capacity cost)
- **Risk Assessment**: Inbreeding risk calculation with configurable thresholds
- **Trait Planning**: Mark favorable traits for targeted breeding
- **Lover/Hater Tracking**: Visual display of relationships in cat inspector
- **Gay Marking**: Same-sex breeding preference support
- **Auto-save**: Configuration persistence across sessions

## Project Structure

```
mewgenics_breeding_helper/
├── packages/
│   ├── mewgenics_parser/           # Save file parsing
│   ├── mewgenics_scorer/           # Pair scoring logic
│   ├── mewgenics_room_optimizer/  # Optimization algorithm
│   └── mewgenics_room_optimizer_ui/  # DearPyGui UI
├── MewgenicsBreedingManager/       # Reference submodule (do not modify)
└── pyproject.toml                 # Workspace config
```

## Installation

```bash
# Install dependencies (requires uv)
uv sync

# Run the UI
uv run room-optimizer
```

## Algorithm

The optimizer uses a "Seed and Pull" clustering approach:

1. **EY Buff Placement**: All Eternal Youth cats are placed in the breeding room with highest base stimulation (they cost 0 capacity)

2. **True Stimulation**: Each room's final stimulation = base_stim + EY_cats_count

3. **Seed & Pull**: 
   - Score all valid pairs using baseline stimulation (50.0)
   - Sort pairs by quality
   - Seed unassigned pairs into rooms
   - Pull unpaired cats into existing rooms when compatible

4. **Throughput Cap**: Prevents gender imbalance (e.g., 4M/1F in 5-cat room). Each gender limited to max_cats - 2 in breeding rooms.

5. **Cross-Product Rescoring**: Final pairs re-scored with room's actual True Stimulation

## Configuration

### Optimization Parameters

| Parameter | Description |
|-----------|-------------|
| Min Stats | Minimum total base stats for breeding candidates |
| Max Risk % | Maximum inbreeding risk allowed (0-100) |
| Minimize Variance | Prioritize consistent offspring stats |
| Avoid Lovers | Exclude mutual lover pairs |
| Prefer High Libido | Favor high libido for faster breeding |
| Prefer High Charisma | Favor high charisma for better odds |

### Favorable Traits

Mark specific mutations, passives, or abilities to prioritize in breeding. Each trait has a weight (1-10) that affects pair scoring.

## Cat Inspector

The inspector shows:
- Name, Gender, Age, Status, Room
- Lovers and Haters (with status)
- Same-Sex Breeding Preference checkbox
- Base stats
- Active Abilities, Passive Abilities, Mutations

EY cats are displayed in teal color with [EY] badge.

## Sandbox Mode

Test any breeding combination in a room. Select two cats from dropdowns to see:
- Expected Quality
- Risk %
- Badges (Lovers, Libido, Aggression, Inbred, Favorable Traits)

## Known Issues

- Age parsing may occasionally show incorrect values (capped at 100 unless Eternal Youth)
- Large save files may take time to parse

## Credits

- Original idea and reference: [MewgenicsBreedingManager](https://github.com/frankieg33/mewgenics_breeding_manager) by frankieg33
- Developed with assistance from AI tools
