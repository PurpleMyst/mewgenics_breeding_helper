"""Benchmarks for room optimizer and Monte Carlo simulation."""

import os
import sys
from pathlib import Path

import pytest

# Sample cat db_keys from save file, stratified by ENS (38-49)
SAMPLED_CAT_IDS = [
    1805,  # ENS 38.0
    2025,  # ENS 44.0
    1773,  # ENS 47.0
    1963,  # ENS 47.0
    1758,  # ENS 48.0
    1792,  # ENS 48.0
    1877,  # ENS 48.0
    1898,  # ENS 48.0
    1928,  # ENS 48.0
    1987,  # ENS 48.0
    2013,  # ENS 48.0
    2037,  # ENS 48.0
    1808,  # ENS 49.0
    1891,  # ENS 49.0
    1926,  # ENS 49.0
    1961,  # ENS 49.0
    1975,  # ENS 49.0
    1999,  # ENS 49.0
    2004,  # ENS 49.0
    2017,  # ENS 49.0
]


def _get_save_path() -> str | None:
    """Get save file path from env or default location."""
    path = os.environ.get("MEWGENICS_SAVEFILE_PATH")
    if path and Path(path).exists():
        return path
    if sys.platform == "win32" and (appdata := os.getenv("APPDATA")):
        default = (
            appdata
            + r"\Glaiel Games\Mewgenics\76561198044230461\saves\steamcampaign01.sav"
        )
        if Path(default).exists():
            return default
    return None


@pytest.fixture(scope="module")
def benchmark_cats():
    """Load benchmark cats from save file."""
    save_path = _get_save_path()
    if not save_path:
        pytest.skip("No save file available for benchmarks")

    from mewgenics_parser import parse_save

    save = parse_save(save_path)
    cats_by_id = {c.db_key: c for c in save.cats}
    cats = [cats_by_id[db_key] for db_key in SAMPLED_CAT_IDS if db_key in cats_by_id]

    if len(cats) < len(SAMPLED_CAT_IDS):
        pytest.skip(
            f"Could not load all benchmark cats: {len(cats)}/{len(SAMPLED_CAT_IDS)}"
        )

    return cats


@pytest.fixture(scope="module")
def benchmark_save_data(benchmark_cats):
    """Create SaveData object with benchmark cats."""
    from mewgenics_parser import SaveData

    return SaveData(
        cats=benchmark_cats,
        current_day=0,
        house_count=len(benchmark_cats),
        adventure_count=0,
        gone_count=0,
    )


@pytest.fixture(scope="module")
def benchmark_room_configs():
    """Create benchmark room configs."""
    from mewgenics_room_optimizer import RoomConfig, RoomType

    return [
        RoomConfig("Floor1_Large", RoomType.FIGHTING, None, 50.0, 5.0),
        RoomConfig("Floor1_Small", RoomType.BREEDING, 6, 50.0, 5.0),
        RoomConfig("Floor2_Small", RoomType.BREEDING, 4, 30.0, 3.0),
    ]


class TestMonteCarloBenchmark:
    """Benchmarks for Monte Carlo simulation."""

    def test_mc_4_cats_comfort5(self, benchmark, benchmark_cats):
        """Benchmark MC with 4 cats at comfort 5."""
        from mewgenics_breeding import simulate_room_breeding

        cats = benchmark_cats[:4]
        result = benchmark(
            simulate_room_breeding,
            cats,
            comfort=5.0,
            max_iterations=10_000,
        )
        assert result.pair_kittens is not None

    def test_mc_6_cats_comfort5(self, benchmark, benchmark_cats):
        """Benchmark MC with 6 cats at comfort 5."""
        from mewgenics_breeding import simulate_room_breeding

        cats = benchmark_cats[:6]
        result = benchmark(
            simulate_room_breeding,
            cats,
            comfort=5.0,
            max_iterations=10_000,
        )
        assert result.pair_kittens is not None

    def test_mc_10_cats_comfort5(self, benchmark, benchmark_cats):
        """Benchmark MC with 10 cats at comfort 5."""
        from mewgenics_breeding import simulate_room_breeding

        cats = benchmark_cats[:10]
        result = benchmark(
            simulate_room_breeding,
            cats,
            comfort=5.0,
            max_iterations=10_000,
        )
        assert result.pair_kittens is not None

    def test_mc_20_cats_comfort5(self, benchmark, benchmark_cats):
        """Benchmark MC with 20 cats at comfort 5."""
        from mewgenics_breeding import simulate_room_breeding

        result = benchmark(
            simulate_room_breeding,
            benchmark_cats,
            comfort=5.0,
            max_iterations=10_000,
        )
        assert result.pair_kittens is not None

    @pytest.mark.parametrize("iterations", [1_000, 5_000, 10_000, 50_000])
    def test_mc_iterations_scaling(self, benchmark, benchmark_cats, iterations):
        """Benchmark MC with varying iteration counts."""
        from mewgenics_breeding import simulate_room_breeding

        cats = benchmark_cats[:6]
        result = benchmark(
            simulate_room_breeding,
            cats,
            comfort=5.0,
            max_iterations=iterations,
        )
        assert result.pair_kittens is not None


class TestOptimizerBenchmark:
    """Benchmarks for full optimizer."""

    def test_optimize_sa_small(
        self, benchmark, benchmark_save_data, benchmark_room_configs
    ):
        """Benchmark SA on small cat set."""
        from mewgenics_room_optimizer import optimize_sa

        result = benchmark(
            optimize_sa,
            benchmark_save_data,
            benchmark_room_configs[:1],  # Single breeding room
        )
        assert result.rooms is not None

    def test_optimize_sa_multi_room(
        self, benchmark, benchmark_save_data, benchmark_room_configs
    ):
        """Benchmark SA with 2 breeding rooms."""
        from mewgenics_room_optimizer import optimize_sa

        result = benchmark(
            optimize_sa,
            benchmark_save_data,
            benchmark_room_configs[:2],
        )
        assert result.rooms is not None


class TestRoomSimulatorBenchmark:
    """Benchmarks for RoomSimulator caching."""

    def test_room_simulator_first_run(self, benchmark, benchmark_cats):
        """Benchmark RoomSimulator first run (no cache)."""
        from mewgenics_breeding import RoomSimulator

        def run_mc(cats, comfort):
            # Always create fresh simulator to measure true cold performance
            sim = RoomSimulator(
                iterations=10_000, early_stop_rounds=500, relative_tolerance=0.01
            )
            return sim.get_expected_kittens(cats, comfort)

        cats = benchmark_cats[:6]
        result = benchmark(run_mc, cats, 5.0)
        assert result is not None

    def test_room_simulator_cached(self, benchmark, benchmark_cats):
        """Benchmark RoomSimulator cached runs (should be very fast)."""
        from mewgenics_breeding import RoomSimulator

        cats = benchmark_cats[:6]
        sim = RoomSimulator(
            iterations=10_000, early_stop_rounds=500, relative_tolerance=0.01
        )

        # Pre-populate cache
        sim.get_expected_kittens(cats, 5.0)

        result = benchmark(sim.get_expected_kittens, cats, 5.0)
        assert result is not None
