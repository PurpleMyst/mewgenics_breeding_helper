"""Monte Carlo simulation for room-level breeding."""

import math
import random
from collections import defaultdict
from dataclasses import dataclass

from mewgenics_parser import Cat
from mewgenics_parser.cat import CatGender, CatStatus


def _calc_directional_compatibility(father: Cat, mother: Cat) -> float:
    """Calculate one-way compatibility assuming father/mother roles."""
    if father.db_key == mother.db_key:
        return 0.0

    if father.has_eternal_youth():
        return 0.0

    if father.status != CatStatus.IN_HOUSE or mother.status != CatStatus.IN_HOUSE:
        return 0.0

    lover_mult = 1.0
    if mother.lover_id is not None:
        coeff = mother.lover_affinity
        if father.db_key == mother.lover_id:
            lover_mult = 1.0 + coeff
        else:
            lover_mult = 1.0 - coeff

    sexuality_mult = 1.0
    mother_sexuality = mother.sexuality if mother.sexuality is not None else 0.0

    father_is_ditto = father.gender == CatGender.DITTO
    mother_is_ditto = mother.gender == CatGender.DITTO

    if father_is_ditto or mother_is_ditto:
        sexuality_mult = 1.0
    elif father.gender != mother.gender:
        sexuality_mult = math.cos(0.5 * math.pi * mother_sexuality)
    else:
        sexuality_mult = math.sin(0.5 * math.pi * mother_sexuality)

    mother_libido = mother.libido if mother.libido is not None else 0.0
    father_charisma = father.total_stats.charisma

    raw_score = 0.15 * father_charisma * mother_libido * lover_mult * sexuality_mult
    return raw_score


def calc_compatibility(a: Cat, b: Cat) -> float:
    """Calculate bidirectional compatibility between two cats.

    Since the game assigns father/mother roles before breeding, we average
    both directional calculations.
    """
    if a.has_eternal_youth() or b.has_eternal_youth():
        return 0.0

    comp_ab = _calc_directional_compatibility(father=a, mother=b)
    comp_ba = _calc_directional_compatibility(father=b, mother=a)
    return (comp_ab + comp_ba) / 2.0


def calc_combined_fertility(a: Cat, b: Cat) -> float:
    """Calculate combined fertility for twin probability."""
    fert_a = a.fertility if a.fertility is not None else 1.0
    fert_b = b.fertility if b.fertility is not None else 1.0
    return fert_a * fert_b


def _simulate_day(
    cats: list[Cat],
    compat_matrix: dict[tuple[int, int], float],
    fertility_matrix: dict[tuple[int, int], float],
    comfort: float,
) -> dict[tuple[int, int], int]:
    """Simulate one day of breeding in the room.

    Returns a dict mapping (father_db_key, mother_db_key) to kitten count.
    """
    n = len(cats)
    if n < 2:
        return {}

    available = [True] * n
    indices = list(range(n))
    random.shuffle(indices)

    kittens: dict[tuple[int, int], int] = defaultdict(int)

    for i in indices:
        if not available[i]:
            continue

        current_cat = cats[i]

        valid_targets = []
        for j in range(n):
            if j == i or not available[j]:
                continue
            pair = (
                min(current_cat.db_key, cats[j].db_key),
                max(current_cat.db_key, cats[j].db_key),
            )
            compat = compat_matrix.get(pair, 0.0)
            if compat <= 0.0:
                continue
            valid_targets.append((j, compat))

        if not valid_targets:
            continue

        total_weight = sum(c for _, c in valid_targets)
        if total_weight == 0:
            continue

        probs = [c / total_weight for _, c in valid_targets]
        target_idx = random.choices([j for j, _ in valid_targets], weights=probs, k=1)[
            0
        ]
        target_cat = cats[target_idx]

        pair_key = (
            min(current_cat.db_key, target_cat.db_key),
            max(current_cat.db_key, target_cat.db_key),
        )
        compat = compat_matrix[pair_key]

        roll_prob = compat * math.sqrt(0.1 * comfort)

        if random.random() > roll_prob:
            continue

        if random.random() > roll_prob:
            available[i] = False
            available[target_idx] = False
            continue

        if compat < 0.05:
            available[i] = False
            available[target_idx] = False
            continue

        available[i] = False
        available[target_idx] = False

        combined_fertility = fertility_matrix[pair_key]
        kitten_count = 1
        if combined_fertility > 1.0:
            twin_chance = min(combined_fertility - 1.0, 0.5625)
            if random.random() < twin_chance:
                kitten_count = 2

        kittens[pair_key] += kitten_count

    return dict(kittens)


@dataclass
class SimulationResult:
    """Result of Monte Carlo room breeding simulation."""

    pair_kittens: dict[tuple[int, int], float]
    iterations_run: int
    converged: bool


def simulate_room_breeding(
    cats: list[Cat],
    comfort: float,
    max_iterations: int = 1_000_000,
    early_stop_rounds: int = 1_000,
    relative_tolerance: float = 0.001,
    seed: int | None = None,
) -> SimulationResult:
    """Simulate room breeding to estimate expected kittens per day per pair.

    Args:
        cats: List of cats in the room.
        comfort: Room comfort stat (0-10 typical, can exceed).
        max_iterations: Maximum number of Monte Carlo iterations.
        early_stop_rounds: Number of consecutive rounds of stability to wait before early stopping.
        relative_tolerance: Relative tolerance threshold for early stopping.
        seed: Random seed for reproducibility.

    Returns:
        SimulationResult with per-pair expected kitten counts and convergence info.
    """
    if seed is not None:
        random.seed(seed)

    if len(cats) < 2:
        return SimulationResult({}, 0, True)

    compat_matrix: dict[tuple[int, int], float] = {}
    fertility_matrix: dict[tuple[int, int], float] = {}

    n = len(cats)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = cats[i], cats[j]
            pair_key = (min(a.db_key, b.db_key), max(a.db_key, b.db_key))
            compat_matrix[pair_key] = calc_compatibility(a, b)
            fertility_matrix[pair_key] = calc_combined_fertility(a, b)

    pair_totals: dict[tuple[int, int], float] = defaultdict(float)
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)

    total_kittens = 0.0
    prev_total = 0.0
    stable_rounds = 0

    for iteration in range(1, max_iterations + 1):
        day_kittens = _simulate_day(cats, compat_matrix, fertility_matrix, comfort)

        for pair, count in day_kittens.items():
            pair_totals[pair] += count
            pair_counts[pair] += 1
            total_kittens += count

        if iteration % 1000 == 0 and iteration >= 10000:
            current_avg = total_kittens / iteration

            if prev_total > 0:
                relative_change = abs(current_avg - prev_total) / prev_total

                if relative_change < relative_tolerance:
                    stable_rounds += 1
                    if stable_rounds >= early_stop_rounds:
                        pair_kittens = {
                            p: t / iteration for p, t in pair_totals.items()
                        }
                        return SimulationResult(pair_kittens, iteration, True)
                else:
                    stable_rounds = 0

            prev_total = current_avg

    pair_kittens = {p: t / max_iterations for p, t in pair_totals.items()}
    return SimulationResult(pair_kittens, max_iterations, False)
