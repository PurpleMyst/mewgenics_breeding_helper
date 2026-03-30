"""Fast deterministic heuristic for approximating expected kittens in a breeding room.

This replaces the stochastic Monte Carlo simulation during the SA inner loop
with a closed-form algebraic approximation. The math is derived from analyzing
the game code in _simulate_day().
"""

from mewgenics_parser import Cat

from .monte_carlo import get_cached_compatibility, get_cached_fertility


def approximate_expected_kittens(
    cats: list[Cat],
    comfort: float,
) -> dict[tuple[int, int], float]:
    """Approximate expected kittens per day for each valid pair in the room.

    This is a deterministic O(N²) approximation of the stochastic Monte Carlo
    simulation. It's used during SA optimization to evaluate many room configurations
    quickly.

    The approximation models:
    1. Pair selection probability based on compatibility weighting
    2. Breeding success requires both rolls to succeed: (compat * sqrt(0.1 * comfort))^2
    3. Twin probability based on combined fertility

    Args:
        cats: List of cats in the room.
        comfort: Room comfort stat.

    Returns:
        Dict mapping (db_key_a, db_key_b) to expected kittens per day.
    """
    n = len(cats)
    if n < 2:
        return {}

    cats_by_idx = list(enumerate(cats))
    pair_keys: dict[tuple[int, int], tuple[int, int]] = {}

    compat_by_pair: dict[tuple[int, int], float] = {}
    fertility_by_pair: dict[tuple[int, int], float] = {}

    for i, cat_i in cats_by_idx:
        for j, cat_j in cats_by_idx:
            if j <= i:
                continue
            pair = (min(cat_i.db_key, cat_j.db_key), max(cat_i.db_key, cat_j.db_key))
            pair_keys[pair] = (i, j)

            compat = get_cached_compatibility(cat_i, cat_j)
            fertility = get_cached_fertility(cat_i, cat_j)

            compat_by_pair[pair] = compat
            fertility_by_pair[pair] = fertility

    total_compat = sum(compat_by_pair.values())
    if total_compat == 0:
        return {}

    expected_kittens: dict[tuple[int, int], float] = {}

    for pair, (i, j) in pair_keys.items():
        compat = compat_by_pair[pair]
        if compat <= 0:
            continue

        cat_i = cats[i]
        cat_j = cats[j]

        row_compat_i = 0.0
        row_compat_j = 0.0
        for other_pair, (a_idx, b_idx) in pair_keys.items():
            if a_idx == i or b_idx == i:
                row_compat_i += compat_by_pair[other_pair]
            if a_idx == j or b_idx == j:
                row_compat_j += compat_by_pair[other_pair]

        p_i_selects_j = compat / row_compat_i if row_compat_i > 0 else 0.0
        p_j_selects_i = compat / row_compat_j if row_compat_j > 0 else 0.0

        expected_attempts = p_i_selects_j + p_j_selects_i

        success_chance = (compat**2) * (0.1 * comfort)

        avg_success = expected_attempts * success_chance

        if avg_success <= 0:
            continue

        fertility = fertility_by_pair[pair]
        expected_twins = 0.0
        if fertility > 1.0:
            twin_chance = min(fertility - 1.0, 0.5625)
            expected_twins = twin_chance

        expected_kittens[pair] = avg_success * (1.0 + expected_twins)

    return expected_kittens
