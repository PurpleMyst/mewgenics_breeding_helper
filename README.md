# Mewgenics Breeding Helper

[![Python 3.13+](https://img.shields.io/badge/Python-3\.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-orange)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/PurpleMyst/mewgenics_breeding_helper)](https://github.com/PurpleMyst/mewgenics_breeding_helper/issues)

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, MiniMax M2).
While every effort has been made to ensure accuracy and consistency with the game's mechanics,
there may be discrepancies or edge cases not fully captured. Please report any issues you
encounter. Your save files are fully safe—the tool operates in a read-only manner.**

A high-performance, Python-based tool for optimizing breeding operations in [Mewgenics](https://store.steampowered.com/app/686060/Mewgenics/).
It extracts data directly from your save files and utilizes a Parallel Simulated Annealing algorithm
to calculate the optimal distribution of cats across your house's rooms, maximizing high-quality
offspring while managing relationships and minimizing inbreeding risks.

![Main UI](/.github/screenshots/main.png?raw=true "Main UI")

## Core Features

### Game-Accurate Breeding Simulation

The breeding engine implements the full 12-step inheritance process from Mewgenics, calculating
**probability mass functions (PMFs)** for all offspring traits. This replaces the old "roll once"
approach with proper expected value math:

```
P(higher stat) = (1.0 + 0.01 × Stimulation) / (2.0 + 0.01 × Stimulation)
```

| Category | Base Chance | Formula |
|----------|-------------|---------|
| Stats | Varies | Stimulation-dependent |
| First Spell | 20% | +2.5% × Stimulation (guaranteed at 32+) |
| Second Spell | 2% | +0.5% × Stimulation |
| Passive | 5% | +1% × Stimulation (guaranteed at 95+) |
| SkillShare+ | 100% | Bypasses formula entirely |
| Disorder (inherited) | 15% | Per parent, pool-diluted |
| Disorder (novel) | 2% | +0.4 × max(CoI − 0.20, 0) |
| Body Parts | 80% | + symmetrization for left/right pairs |

### Expected Net Stats (ENS) Scoring

The optimizer evaluates breeding pairs using **Expected Net Stats (ENS)** — a unified
expected-value framework:

```
Quality = Σ(expected_stats) + universal_ev − (disorders × 5.0 + defects × 1.0)
```

**Components:**
- **Stats ENS** — Expected sum of 7 base stats (STR, DEX, CON, INT, SPD, CHA, LCK)
- **Malady Penalties** — Disorders (×5.0 ENS) and birth defects (×1.0 ENS)
- **Universal EV** — Expected value from traits you want in ALL kittens
- **Build Yields** — Synergy bonuses for named builds (see below)

### Universals & Target Builds

**Universals** are traits prioritized across every breeding pair. Add them via the left panel
trait selector, set a weight (0.5–10.0), and the optimizer maximizes their inheritance probability.

**Target Builds** are named build templates with:
- **Requirements** — Traits that contribute positively (weighted 0.5–10.0)
- **Anti-synergies** — Traits that penalize the build
- **Synergy Bonus** — ENS bonus awarded when ALL requirements are met
  - Calculated as: `P(at least one passive) × P(at least one active) × ∏P(at least one body part per slot)`
  - This is proper OR-probability math, not simple addition

### Smart Room Optimization

**Two-phase optimization:**
1. **Simulated Annealing (parallel)** — Finds optimal breeding pair assignments
2. **Greedy Allocation** — Routes remaining cats to appropriate rooms

**Room Types:**
| Type | Purpose |
|------|---------|
| `BREEDING` | Productive breeding pairs |
| `FIGHTING` | Low-value cats or those with conflicts |
| `GENERAL` | Healthy cats without specific room needs |
| `HEALTH` | Cats with disorders (higher recovery chance) |
| `MUTATION` | Cats with birth defects |
| `NONE` | Unassigned/empty |

**Eternal Youth (EY)** cats are treated as free room buffs (+1 Stimulation) that bypass
capacity limits, automatically assigned to the highest-stimulation breeding room.

## Installation

```bash
# Clone the repository
git clone https://github.com/PurpleMyst/mewgenics_breeding_helper.git
cd mewgenics_breeding_helper

# Install dependencies
uv sync

# Run the UI
uv run room-optimizer
```

> **Note:** The application will automatically attempt to locate `resources.gpak` in standard
> Steam installation paths or the current working directory.

## Usage Guide

### Loading Your Save

1. Find the **Available Saves** section in the left panel (collapsed by default, expand it)
2. Select your save from the listbox
3. The cats table will populate with all cats from your save file

### Configuring Rooms

1. Expand the **Room Configuration** section
2. For each room, set:
   - **Type** — Dropdown: breeding, fighting, general, health, mutation, none
   - **Max Cats** — Leave empty for unlimited, or enter a number
   - **Stimulation** — Base stimulation value for inheritance calculations

### Defining Trait Priorities

**To add a Universal:**
1. In **Universals & Builds**, use the trait selector above the tab bar
2. Filter by category (Passive Ability, Active Ability, Body Part, Disorder, etc.)
3. Select a trait and click **Add Universal**
4. Adjust the weight (0.5–10.0) using the input field

**To create a Target Build:**
1. Click **Add New Build** in the Target Builds tab
2. Enter a build name and synergy bonus (ENS awarded when requirements met)
3. Add requirements and anti-synergies using the trait selector
4. Set weights for each trait

### Optimizing

1. Click **Optimize** in the toolbar
2. Wait for the parallel simulated annealing to complete
3. Results appear in the **Results** tab

### Reviewing Results

**Results Tab:**
- Click a room row to see details
- **Overview** sub-tab: Favorable trait distribution in this room
- **Pairs** sub-tab: All breeding pairs with Stats ENS, Universal EV, disorder/defect counts
- **Cats** sub-tab: All cats in the room
- **Misplaced** sub-tab: Cats physically in this room but assigned elsewhere

**Inspector Panel:**
- Click any pair to see detailed ENS breakdown
- Click any cat to see full stats, abilities, and traits

### The Overview Tab (Global)

Shows favorable trait distribution across **all in-house cats**, sorted by count:
- Traits that appear in your Universals
- Traits that appear in your Target Build requirements

Use this to identify which traits are common vs. rare in your population.

## UI Reference

```
+------------------------------------------------------------------+
| Menu Bar + Toolbar (Optimize button)                              |
+----------------------------+-------------------------------------+
| LEFT PANEL (450px)         | RIGHT PANEL                         |
|----------------------------|-------------------------------------|
| Available Saves (listbox)  | [Overview] [Results] [All Cats]       |
|                            |                                      |
| Room Configuration (table) | Inspector (collapsing)                |
| - Type dropdown            | [Cat] [Pair] tabs                   |
| - Max Cats input           |                                      |
| - Stimulation input        |                                      |
|                            |                                      |
| Universals & Builds        |                                      |
| - Trait Selector           |                                      |
| - [Universals] [Builds]    |                                      |
+----------------------------+-------------------------------------+
```

## Development

```bash
# Run all tests
uv run pytest

# Run type checker
uv run ty check .

# Run linter
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .
```

## Contributing

Contributions are welcome! Please ensure:

1. **Tests pass** — Run `uv run pytest`
2. **Type check passes** — Run `uv run ty check .`
3. **Linting passes** — Run `uv run ruff check .`
4. **Formatting** — Code is formatted with `uv run ruff format .`

## Credits

- Original idea and reference: [MewgenicsBreedingManager](https://github.com/frankieg33/mewgenics_breeding_manager) by frankieg33
- Favicon is an emoji from Twemoji, licensed under CC-BY 4.0 and obtained from [favicon.io](https://favicon.io/emoji-favicons/cat)
- [Breeding notes by SciresM](https://gist.github.com/SciresM/95a9dbba22937420e75d4da617af1397)
- Reverse engineered ImHex patterns by p0lymeric from [mewgenics_analysis](https://github.com/p0lymeric/mewgenics_analysis)
- Developed with assistance from AI tools

---

## Technical Notes

### Package Architecture

```
packages/
├── mewgenics_breeding/       # PMF-based breeding simulation
│   ├── simulate.py            # 12-step inheritance engine
│   ├── compatibility.py      # Gender-based breeding checks
│   └── pairs.py              # Pair generation and filtering
├── mewgenics_parser/         # Save file parsing, trait models
├── mewgenics_scorer/         # ENS factor calculation
│   └── factors.py            # PairFactors, quality formula
├── mewgenics_room_optimizer/ # SA optimization + greedy allocation
│   ├── optimizer.py          # Simulated annealing workers
│   └── allocator.py          # Greedy room assignment
└── mewgenics_room_optimizer_ui/  # DearPyGui interface
```

### ENS Formula Details

**Pair Quality:**
```python
malady = expected_disorders * 5.0 + expected_defects * 1.0
base_quality = sum(expected_stats) + universal_ev - malady
return base_quality * breeding_prob
```

**Build Yield:**
```python
req_ev = Σ(P(trait) × weight) for requirements
anti_ev = Σ(P(trait) × weight) for anti_synergies
synergy_prob = P(at least one passive) × P(at least one active) × ∏P(body parts per slot)
yield = req_ev + synergy_prob × synergy_bonus - anti_ev
```

### Simulation Engine

The breeding simulation (`simulate_breeding()`) produces an `OffspringProbabilityMass` containing:
- `stats` — List of 7 `(value, probability)` tuples per stat
- `passive_abilities` — `{trait_key: probability}` dict
- `active_abilities` — `{trait_key: probability}` dict
- `inherited_disorders` — `{trait_key: probability}` dict
- `body_parts` — `{slot: {part_id: probability}}` dict

### Kinship & Inbreeding

Coefficient of Inbreeding (CoI) is calculated via pedigree blob lookup in `SaveData.get_offspring_coi(a, b)`,
replacing the old `KinshipManager` class. Stray cats always have CoI = 0.
