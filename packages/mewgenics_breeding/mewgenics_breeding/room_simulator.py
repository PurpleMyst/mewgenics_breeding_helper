"""Room-level Monte Carlo simulation for breeding optimization."""

from dataclasses import dataclass, field

from mewgenics_parser import Cat

from .monte_carlo import SimulationResult, simulate_room_breeding


@dataclass(slots=True)
class RoomSimulator:
    """Cached room-level Monte Carlo simulator for breeding optimization.

    Provides fast repeated lookups of expected kittens per pair for the same
    room composition (set of cats with the same comfort level).
    """

    iterations: int
    early_stop_rounds: int
    relative_tolerance: float
    _cache: dict[tuple[frozenset[int], float], dict[tuple[int, int], float]] = field(
        default_factory=dict, init=False, repr=False
    )

    def get_expected_kittens(
        self,
        room_cats: list[Cat],
        comfort: float,
    ) -> dict[tuple[int, int], float]:
        """Get expected kittens per day for each pair in the room.

        Uses caching to avoid re-running Monte Carlo simulation for the same
        room composition and comfort level.

        Args:
            room_cats: List of cats in the room.
            comfort: Room comfort stat.

        Returns:
            Dict mapping (cat_a_db_key, cat_b_db_key) to expected kittens per day.
        """
        key = (frozenset(c.db_key for c in room_cats), comfort)
        if key not in self._cache:
            result: SimulationResult = simulate_room_breeding(
                cats=room_cats,
                comfort=comfort,
                max_iterations=self.iterations,
                early_stop_rounds=self.early_stop_rounds,
                relative_tolerance=self.relative_tolerance,
            )
            self._cache[key] = result.pair_kittens
        return self._cache[key]
