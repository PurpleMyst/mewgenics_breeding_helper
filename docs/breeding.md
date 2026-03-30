# Breeding

**Breeding** is a core gameplay pillar in _Mewgenics_.

## House Stats

| Name | Description |
|------|-------------|
| **Appeal** | Increases the stat quality and ability diversity of new strays. This applies to the entire house, not just to a single room. See [Stray Cats](https://mewgenics.wiki.gg/wiki/Stray_Cats) for more info. |
| **Comfort** | If high, increases odds of breeding overnight. If low, increases odds of fighting overnight. Comfort is lowered by 1 for each cat in a room above 4. |
| **Stimulation** | If high, kittens will inherit more and better things from their parents. If low, kittens have a lower chance of inheriting anything. |
| **Health** | If high: cats take longer to become old and are less likely to die of old age; cats have a chance of recovering from Injuries and Disorders overnight. If low: cats become old sooner; cats have a chance of developing hygiene disorders overnight. |
| **Mutation** | Increases the chance for cats to develop Mutations overnight. (Also known as Evolution internally) |

## Inbreeding

Each cat has an Inbreeding coefficient (between 0-1) that is correlated to their parents' coefficient and how familiarly close they are.

- Strays will always have coefficient of 0.
- Any breeding between relative cats, who have a **closeness** of 4 or closer, will raise that coefficient.
  - Closeness can be determined by tracing along the lines of the family tree; count how many lines separate the couple, condensing sibling relations from two lines to one:
    - 1: parent and child, siblings
    - 2: grandparent and grandchild, aunts/uncles and nieces/nephews
    - 3: great-grandparent and great-grandchild, great-aunt/great-uncle and grandniece/grandnephew, first cousins
    - 4: great-great-grandparent and great-great-grandchild, great-great-aunt/great-great-uncle and great-grandniece/great-grandnephew, first cousins once removed
  - The Inbreeding coefficient increases somewhat slowly. Coefficients beyond "Slightly Inbred" are typically the result of two-or-more consecutive generations of inbreeding.
- Breeding with cats who have a Closeness of 5 or higher lowers the coefficient, even if the two cats have notable Inbreeding coefficients of their own.
  - Breeding with a Stray Cat produces a kitty-cat who is **not** inbred, due to the Stray having no common ancestors with the other cat (unless the other parent is a descendant of the Stray).

**Closeness** (C) is a variable used for finding the **Coefficient of Relatedness** (r): `r = 2^-C`

### Math

The Coefficient of Inbreeding (_f_) of Cat X would be determined by:

```
f_X = Σ 0.5^(n+1) × (1 + f_A)
```

- N is the number of common ancestors between both of X's parents
- n is amount of people in the familial loop connecting X's parents and one of their common ancestors (including both parents)
- f_A is the Coefficient of Inbreeding of the ancestor

To simplify, the Coefficient of Inbreeding for parents whose Coefficients of Inbreeding are zero is half of the parents' **Coefficient of Relatedness**.

The Inbredness levels:

- ≤ 0.1: Not Inbred
- 0.10 - 0.25: Slightly Inbred
- 0.25 - 0.50: Moderately Inbred
- 0.50 - 0.80: Highly Inbred
- > 0.80: Extremely Inbred

### Closeness Limits

- If the original breeding pair are both Strays (**Closeness** of infinity), the child will not be Inbred.
- If one of the parents breeds with the child (**Closeness** of 1), the child will be **25%** Inbred.
- If that same parent breeds with the grandchild (**Closeness** of 2), the great-grandchild will be **37.5%** Inbred.
- If that same parent breeds with the great-grandchild (**Closeness** of 3), the great-great-grandchild will be **43.75%** Inbred.
- If that same parent breeds with the great-great-grandchild (**Closeness** of 4), the great-great-great-grandchild will be **46.875%** Inbred.
- If that same parent breeds with the great-great-great-grandchild (**Closeness** of 5), the great-great-great-great-grandchild will **not** be Inbred.

This happens because **Closeness** of 5 or higher is considered negligible, while the offending Stray doesn't have closer relationships with their partners further down the tree.

To achieve higher Inbredness, players must create incestuous relationships between two cats who are Inbred (using the f_A part of the equation).

## Kitten Birth Process

When a kitten is born, 13 steps are performed:

### 1. Furniture Effects

All furniture effects are calculated (most are unused).

### 2. Inheriting Stats

For each of the 7 core stats, one parent's value is inherited.

**Chance (higher stat is chosen):**
```
Probability = (1 + 0.01 × Stimulation) / (2 + 0.01 × Stimulation)
```

| Chance | Stimulation |
|--------|-------------|
| 50%    | 0           |
| 60%    | 50          |
| 70%    | 133         |
| 80%    | 300         |
| 90%    | 800         |
| 99%    | 9800        |

Stimulation has diminishing returns as it approaches infinity (probability approaches 1 but never reaches it).

**Chance of inheriting the better value for all X stats:**

| Stats | 0   | 20  | 40  | 60  | 80  | 100 | 120 | 140 | 160 | 180 | 200 |
|-------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| 1     | 50% | 55% | 58% | 62% | 64% | 67% | 69% | 71% | 72% | 74% | 75% |
| 2     | 25% | 30% | 34% | 38% | 41% | 44% | 47% | 50% | 52% | 54% | 56% |
| 3     | 13% | 16% | 20% | 23% | 27% | 30% | 33% | 35% | 38% | 40% | 42% |
| 4     | 6%  | 9%  | 12% | 14% | 17% | 20% | 22% | 25% | 27% | 29% | 32% |
| 5     | 3%  | 5%  | 7%  | 9%  | 11% | 13% | 15% | 18% | 20% | 22% | 24% |
| 6     | 2%  | 3%  | 4%  | 5%  | 7%  | 9%  | 11% | 12% | 14% | 16% | 18% |
| 7     | 1%  | 1%  | 2%  | 3%  | 5%  | 6%  | 7%  | 9%  | 10% | 12% | 13% |

### 3. Skill Share

- If either parent has Skill Share+, that parent's **other passive** is guaranteed to be passed to the kitten.

### 4. Inheriting Active Abilities

**How the parent is chosen:**
- Default: 50% between parents
- Bias attempt chance: `min(0.01 × Stimulation, 1)` — if triggered and only one parent has class abilities, the other parent's selection chance becomes 0.

**What happens:**
- After a parent is chosen, one of that parent's active abilities is selected at random.
- If a second active ability is inherited, the parent-selection process is repeated.

**Chance:**
- First active ability: `0.20 + 0.025 × Stimulation` — **Guaranteed at Stimulation ≥ 32**
- Second active ability: `0.02 + 0.005 × Stimulation` — **Guaranteed at Stimulation ≥ 196**

### 5. Inheriting Passive Abilities

**How the parent is chosen:**
- Default: 50% between parents
- Bias attempt chance: `min(0.01 × Stimulation, 1)` — if triggered and only one parent has class passives, the other parent's selection chance becomes 0.

**What happens:**
- After a parent is chosen, one of that parent's passives is selected at random.
- Skill Share cannot be inherited.

**Chance:**
- Probability: `0.05 + 0.01 × Stimulation` — At 0 Stimulation, exactly 5%
- **Guaranteed at Stimulation ≥ 95**

### 6. Inheriting Disorders

**Chance:**
- Inherit one random disorder from the mother: 15%
- Inherit one random disorder from the father: 15%

These rolls are independent. This is **not affected** by Furniture or Stimulation.

### 7. Birth-defect Disorders Roll

Only applies if fewer than 2 disorders were inherited from the parents.

**Chance:**
```
0.02 + 0.4 × clamp(inbreeding_coefficient − 0.2, 0, 1)
```

- Minimum chance is always 2%.
- Chance increases linearly once `inbreeding_coefficient > 0.2`, up to a maximum of 42%.

### 8. Birth Defects Check

**Roll:**
- Generate a random number.

**Condition:**
- If `random < (inbreeding_coefficient × 1.5)` and `inbreeding_coefficient > 0.05`

**What happens:**
- The kitten is flagged to receive birth-defect parts in step 13.

### 9. Body Parts

**What happens:**
- Body parts are inherited from the parents (mutations are part variants).

**Chance:**
- All part-sets are inherited: 80%
- One random part-set is **not** inherited and is instead randomly assigned: 20% (all other part-sets are still inherited normally).

**How each inherited part is chosen:**
- For each inherited part, either mother's or father's version is selected.
- If only one parent's version is mutated, the mutated version is favored:
  ```
  (1 + 0.01 × Stimulation) / (2 + 0.01 × Stimulation)
  ```
  At 0 Stimulation, exactly 50%.
- If both parents' versions are mutated, or neither is mutated, selection is 50% between parents.

**Notes:**
- Cannot be guaranteed: as Stimulation approaches infinity, probability approaches 1 but never reaches it.

### 10. Body Part Symmetrization

**What happens:**
- For left/right parts that must match, symmetry is enforced by copying one side to the other (Leg, Arm, Eye, Eyebrow, Ear).

**Chance:**
- Left replaced with right: 50%
- Right replaced with left: 50%

**Notes:**
- Maximum number of mutations on a **bred** kitten is 10 due to symmetrization (Body, Head, Tail, Leg, Arm, Eye, Eyebrow, Ear, Mouth, Fur).

### 11. Unknown

**What happens:**
- An additional value is inherited from the parents: 98%

**How the parent is chosen:**
- Default: 50% between parents

**Notes:**
- The associated field/purpose is currently undocumented.

### 12. Inheriting Voice

**What happens:**
- Voice is usually inherited from the parents, with a small chance to reroll.

**Chance:**
- Inherited from parents: ~98%
- Rerolled: ~2%

### 13. Generating Birth Defects

Only if the birth defects check in step 8 succeeded.

**What happens:**
- Birth-defect parts are applied in one or more passes.

**Number of passes:**
- If `inbreeding coefficient ≤ 0.9`: 1 pass
- If `inbreeding coefficient > 0.9`: 2 passes

Birth-defect parts are applied after normal part inheritance and may replace already-inherited parts.

## Pairing

Cats are paired for breeding attempts with the following process:

1. Shuffle all cats into a list, removing kittens and hungry cats.
2. For each cat in the list:
   - Calculate its room's `BreedSuppression` furniture effect (e.g., Idol of Chastity). If present, skip this.
   - Otherwise choose a cat randomly, weighted by their **compatibility** (see Compatibility below).
   - Once chosen, two rolls occur with probability `compatibility × √(0.1 × comfort + 0.1 × x)` where x is undocumented:
     - If first roll fails: skip this cat (partner may still choose this cat on its turn).
     - If second roll fails: remove both cats from the list (no other cat can choose them that day).
     - If both succeed: cats initiate their breeding attempt.
   - Assign "father" and "mother" roles (neutral gender cats fill any role; if same gender, chosen at random).
   - If `compatibility > 0.05`, they will successfully have a kitten.

## Lover

Each cat can have a lover, indicated by an icon next to their name if the player has donated enough cats to Tink. This affects their `lover_coeff`, a hidden value between 0-1 used for calculating **compatibility**.

- **lover_coeff:**
  - If a cat has no lover but is chosen for a breeding attempt, the other cat immediately becomes its lover and sets `lover_coeff = 1.25`.
  - Every breeding attempt with its lover increases: `lover_coeff → 0.9 × lover_coeff + 0.1`
  - If the cat has a lover but was chosen in a breeding attempt not with their lover: `lover_coeff → 0.9 × lover_coeff`

- **Rivals:**
  - When cats are paired for a breeding attempt, their respective lover will change its current Rival to the other cat (to prevent "cheating").
  - Every breeding attempt like this increases the rival's `hater_coeff` towards 100%.
  - This happens regardless of whether the breeding attempt was successful or rejected.
  - Rivals are more likely to start fights with each other.

## Compatibility

When two cats are paired for a breeding attempt:

1. Check requirements:
   - Father and mother cannot be the same cat.
   - Father can't be a kitten.
   - Both parents must not be blocked from breeding.

2. Calculate values:

**lover_mult:**
- From the mother, take its `lover_coeff` (0.25 by default).
- If mother has no lover: `lover_mult = 1`
- If father is the lover: `lover_mult = 1 + lover_coeff`
- Otherwise: `lover_mult = 1 - lover_coeff`

**sexuality_mult:**
- From the mother, take its `sexuality_coeff`.
- If parents are male-female pair: `sexuality_mult = Cos(0.5π × sexuality_coeff)`
- If parents are both male or both female: `sexuality_mult = Sin(0.5π × sexuality_coeff)`
- If there's a neutral parent, this has no effect.

**Final compatibility:**
```
0.15 × father_charisma × mother_libido × lover_mult × sexuality_mult
```

## Sexuality

Each cat has a Sexuality coefficient (0-1):

- < 0.1: Straight
- 0.1 - 0.9: Bisexual
- > 0.9: Gay

**Stat Distribution:**
- 81.9% Straight
- 7.2% Bisexual
- 10.9% Gay

The true sexuality coefficient is uniformly random within these bounds.

## Libido

Each cat has a Libido coefficient (0-1):

- < 0.3: Low
- 0.3 - 0.7: Mid
- > 0.7: High

**Stat Distribution:**
Libido is calculated by taking the larger of four random numbers between 0 and 0.5. There is a further 50% chance to flip it above 0.5.

Mathematically: `Libido = M` or `1 - M`, where `M = max(U1, U2, U3, U4)` and `Ui ~ Uniform[0, 0.5]`

| Top% of cats | Libido ≥ |
|--------------|----------|
| 50%          | 0.500    |
| 25%          | 0.580    |
| 10%          | 0.666    |
| 6.5%         | 0.700    |
| 5%           | 0.719    |
| 2%           | 0.776    |
| 1%           | 0.812    |
| 0.1%         | 0.894    |

## Aggression

Each cat has an Aggression coefficient (0-1):

- < 0.3: Low
- 0.3 - 0.7: Mid
- > 0.7: High

**Stat Distribution:**
Aggression is uniformly distributed from 0-1.

## Fertility

Each cat has a hidden Fertility coefficient (1.0-1.25) controlling twin probability. Each parent contributes their own fertility, which are multiplied together for `combined_fertility`.

- If `combined_fertility > 1`: 1 kitten is guaranteed, with `(combined_fertility - 1) × 100%` chance of twins (max 56.25%).

**Stat Distribution:**
Fertility is calculated by taking the smaller of two random numbers between 1 and 1.25:

`Fertility = min(U1, U2)` where `U1, U2 ~ Uniform[1, 1.25]`

Average fertility: 1.0833 (average twin chance: 17.36%)

| Top% of cats | Fertility ≥ |
|--------------|--------------|
| 50%          | 1.0732       |
| 25%          | 1.125        |
| 10%          | 1.171        |
| 5%           | 1.194        |
| 2%           | 1.214        |
| 1%           | 1.224        |
| 0.1%         | 1.242        |

## References

- [Mewgenics Decompilation Gist](https://gist.github.com/SciresM/95a9dbba22937420e75d4da617af1397)
