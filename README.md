# Mewgenics Breeding Helper

[![Python 3\.13+](https://img.shields.io/badge/Python-3\.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-orange)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/PurpleMyst/mewgenics_breeding_helper)](https://github.com/PurpleMyst/mewgenics_breeding_helper/issues)

**Disclaimer: This project was developed with assistance from AI tools (OpenCode, MiniMax M2.5).
While every effort has been made to ensure accuracy and consistency with the game's code, there may
be discrepancies or edge cases not fully captured. Please report any issues or inaccuracies you
encounter. Rest assured your save files are fully safe, as the tool operates in a read-only
manner.**

A high-performance, Python-based tool for optimizing breeding operations in [Mewgenics](https://store.steampowered.com/app/686060/Mewgenics/). It extracts data directly from your save files and utilizes a Parallel Simulated Annealing algorithm to calculate the optimal distribution of cats across your house's rooms. The objective is to maximize high-quality offspring, manage relationships, and minimize inbreeding risks.

![Main UI](/.github/screenshots/main.png?raw=true "Main UI")

## Core Features & System Architecture

* **Game-Accurate Inheritance Engine:** Fully replicates the internal Mewgenics RNG mechanics. This includes CoI (Coefficient of Inbreeding) penalties, Stimulation scaling, pool dilution, and the guaranteed inheritance of `SkillShare+`.
* **Comprehensive Risk Assessment:** We separate the risk factors to evaluate the union probability of birth maladies, independently calculating **inherited** defects from parents and **novel** defects generated strictly by high inbreeding coefficients.
* **Smart Room Optimization:** Leverages multi-processing to rapidly evaluate thousands of room state permutations. The algorithm introduces a movement penalty, actively preferring optimal solutions that require you to manually move fewer cats in-game.
* **Targeted Trait EV:** Mark specific mutations, passives, or abilities as favorable and assign them user-defined weights (1-10). The optimizer then calculates the Expected Value (EV) of these traits passing down to a pair's kittens.
* **Eternal Youth Mechanics:** Accurately treats EY cats as free room buffs (+1 Stimulation) that bypass standard room capacity limits.
* **Same-Sex Preference Tracking:** Supports marking cats with same-sex preferences, properly restricting their valid breeding partners to Fluid (`?` / Spidercats) per game rules.

## Performance & Known Limitations

* **Execution Time:** While save file parsing and data loading are near-instantaneous, the **Parallel Simulated Annealing** optimization evaluates a massive state space. Consequently, it can take several seconds to minutes depending on your CPU, cat population, and configured SA parameters (Temperature and Neighbors).
* **Same-Sex Preference (SSP) Extraction:** While a cat's SSP status is technically stored within the `.sav` file, the parser cannot currently extract it. You must manually flag SSP cats in the UI's Cat Inspector for the optimizer to recognize their preferences.
* **GPAK Dependency:** Requires a local installation of Mewgenics to parse `resources.gpak` for current ability descriptions and names.
* **UI Parsing Limits:** The Cat Inspector currently does not perfectly display all upgraded abilities as their higher-tier variants in the UI, though the underlying inheritance math handles them correctly.

## Installation

This project utilizes `uv` for dependency management. 

```bash
# Clone the repository
git clone https://github.com/PurpleMyst/mewgenics_breeding_helper.git
cd mewgenics_breeding_helper

# Install dependencies
uv sync

# Run the UI
uv run room-optimizer
```

> **Note:** The application will automatically attempt to locate `resources.gpak` in standard Steam installation paths or the current working directory.

## Principle of Operation: Inheritance Math

The optimizer evaluates breeding pairs based on the exact formulas used by the Mewgenics engine (`glaiel::CatData::breed`). 

* **Base Stats & Mutations:** The probability of inheriting the higher of two parent stats (or favoring a mutated body part) scales with room Stimulation:
  $$P(\text{Higher / Mutated}) = \frac{1.0 + 0.01 \times \text{Stimulation}}{2.0 + 0.01 \times \text{Stimulation}}$$
* **Active Abilities:** Base inheritance chance is **20%** + **2.5%** per Stimulation point. Class-specific spells have an additional favoring chance. The final probability is diluted by the parent's total inheritable spell pool.
* **Passive Abilities:** Base inheritance chance is **5%** + **1%** per Stimulation point. **Exception:** The upgraded `SkillShare+` bypasses this formula entirely and ensures inheritance of the parent's other passive.
* **Disorders (Negative Traits):**
  * *Inherited:* **15%** flat chance to inherit from a parent, diluted by the total number of disorders that parent possesses.
  * *Novel (Inbreeding):* Spontaneous disorders have a base **2%** chance, plus a CoI penalty: 
  $$P(\text{Novel Disorder}) = 0.02 + 0.4 \times \max(\text{CoI} - 0.20, 0.0)$$
* **Body Parts & Defects:** Parts have an **80%** base inheritance rate. Novel physical birth defects trigger if CoI > 0.05, scaling rapidly at $1.5 \times \text{CoI}$ (capped at 1.0).

By combining these factors, we obtain a highly accurate quality value for any given pair.

## Usage Guide

1.  **Load Save:** Select your latest `.sav` file from the sidebar.
2.  **Configure Rooms:** Set your room capacities and base stimulation levels.
3.  **Set Constraints:** Adjust your risk tolerance (Max Risk %) and stat thresholds. 
4.  **Target Traits:** (Optional) Add favorable traits and adjust their weights in the Planner tab.
5.  **Mark Gay Cats:** (Optional) Select a cat and check "Same-Sex Breeding Preference" in the Inspector.
6.  **Optimize:** Click "Calculate Optimal Distribution." 
7.  **Review Misplaced Cats:** Check the "Misplaced" tab to easily see which cats need to be physically moved in-game to match the optimized layout.

## Configuration Parameters

| Parameter | Impact |
| :--- | :--- |
| **Min Stats** | Excludes cats below this total base stat threshold. |
| **Max Risk %** | Hard cap on the combined probability of any birth malady (Novel or Inherited). |
| **Minimize Variance** | Penalizes pairs with highly divergent stats to secure mathematically consistent litters. |
| **Avoid Lovers** | Prevents breaking existing Lover bonds to avoid in-house fighting. |
| **Maximize Throughput** | Applies an exponential density bonus to favor layouts with the highest number of simultaneous valid pairs. |

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
