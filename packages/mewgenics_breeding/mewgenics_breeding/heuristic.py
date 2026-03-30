"""Fast deterministic heuristic for approximating expected kittens in a breeding room.

This replaces the stochastic Monte Carlo simulation during the SA inner loop
with a closed-form algebraic approximation. The math is derived from analyzing
the game code in _simulate_day().

The HeuristicCalculator class caches compat and fertility matrices by frozenset
of cat db_keys to avoid redundant O(N^2) recomputation when the same cat set
appears across SA iterations. The matrices are intrinsic pair properties
(depend only on the two cats, not on room parameters like comfort), so reuse
is always valid.
"""

from dataclasses import dataclass, field

from mewgenics_parser import Cat
from mewgenics_parser.constants import COMFORT_BASE_CAPACITY, MIN_BREEDING_COMPAT

from .monte_carlo import calc_compatibility, calc_combined_fertility


def _effective_comfort(base_comfort: float, n_cats: int) -> float:
    """Calculate effective comfort after overcrowding penalty.

    Comfort is reduced by 1 for each cat above COMFORT_BASE_CAPACITY (4).
    """
    return max(0.0, base_comfort - max(0, n_cats - COMFORT_BASE_CAPACITY))


@dataclass(slots=True)
class HeuristicCalculator:
    """Cached deterministic heuristic for approximating expected kittens per breeding room.

    Caches compat and fertility matrices by frozenset of cat db_keys to avoid
    redundant O(N^2) recomputation when the same cat set appears across SA
    iterations. The matrices are intrinsic pair properties (they depend only on
    the two cats, not on room parameters like comfort), so reuse is always valid.

    Usage:
        calc = HeuristicCalculator()
        room_kittens = calc.get_expected_kittens(cats_in_room, comfort=7.0)
    """

    _matrix_cache: dict[
        frozenset[int],
        tuple[dict[tuple[int, int], float], dict[tuple[int, int], float]],
    ] = field(default_factory=dict, init=False, repr=False)

    def get_expected_kittens(
        self,
        cats: list[Cat],
        comfort: float,
    ) -> dict[tuple[int, int], float]:
        """Approximate expected kittens per day for each valid pair in the room.

        Uses cached matrices when the same cat set (by db_key identity) appears
        across calls, avoiding O(N^2) recomputation each time.

        The approximation models:
        1. Pair selection probability based on compatibility weighting
        2. Breeding success requires both rolls to succeed:
           (compat * sqrt(0.1 * comfort))^2
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

        effective_comfort = _effective_comfort(comfort, n)
        cats_by_idx = list(enumerate(cats))

        key = frozenset(c.db_key for c in cats)
        if key in self._matrix_cache:
            compat_by_pair, fertility_by_pair = self._matrix_cache[key]
        else:
            compat_by_pair: dict[tuple[int, int], float] = {}
            fertility_by_pair: dict[tuple[int, int], float] = {}

            for i, cat_i in cats_by_idx:
                for j, cat_j in cats_by_idx:
                    if j <= i:
                        continue
                    pair = (
                        min(cat_i.db_key, cat_j.db_key),
                        max(cat_i.db_key, cat_j.db_key),
                    )

                    compat = calc_compatibility(cat_i, cat_j)
                    fertility = calc_combined_fertility(cat_i, cat_j)

                    compat_by_pair[pair] = compat
                    fertility_by_pair[pair] = fertility

            self._matrix_cache[key] = (compat_by_pair, fertility_by_pair)

        pair_keys: dict[tuple[int, int], tuple[int, int]] = {}
        for i, cat_i in cats_by_idx:
            for j, cat_j in cats_by_idx:
                if j <= i:
                    continue
                pair = (
                    min(cat_i.db_key, cat_j.db_key),
                    max(cat_i.db_key, cat_j.db_key),
                )
                pair_keys[pair] = (i, j)

        total_compat = sum(compat_by_pair.values())
        if total_compat == 0:
            return {}

        row_compat_sum = [0.0] * n
        for pair, (a_idx, b_idx) in pair_keys.items():
            row_compat_sum[a_idx] += compat_by_pair[pair]
            row_compat_sum[b_idx] += compat_by_pair[pair]

        expected_kittens: dict[tuple[int, int], float] = {}

        for pair, (i, j) in pair_keys.items():
            compat = compat_by_pair[pair]
            if compat < MIN_BREEDING_COMPAT:
                continue

            row_compat_i = row_compat_sum[i]
            row_compat_j = row_compat_sum[j]

            p_i_selects_j = compat / row_compat_i if row_compat_i > 0 else 0.0
            p_j_selects_i = compat / row_compat_j if row_compat_j > 0 else 0.0

            expected_attempts = p_i_selects_j + p_j_selects_i

            success_chance = (compat**2) * (0.1 * effective_comfort)

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
