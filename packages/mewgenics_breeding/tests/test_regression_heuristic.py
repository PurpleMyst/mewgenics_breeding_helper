"""Regression tests for potential bugs in heuristic caching and room optimization."""

import pytest
from mewgenics_breeding import HeuristicCalculator, RoomSimulator
from mewgenics_parser.cat import Cat, CatGender, CatStatus, CatBodySlot, Stats


def make_cat(
    db_key: int,
    gender: CatGender = CatGender.MALE,
    charisma: int = 10,
    libido: float = 0.5,
    sexuality: float = 0.0,
    fertility: float = 1.0,
    status: CatStatus = CatStatus.IN_HOUSE,
    eternal_youth: bool = False,
) -> Cat:
    disorders = ["eternalyouth"] if eternal_youth else []
    return Cat(
        db_key=db_key,
        name=f"Cat{db_key}",
        name_tag="",
        gender=gender,
        status=status,
        room="Room",
        base_stats=Stats(7, 7, 7, 7, 7, charisma, 7),
        total_stats=Stats(7, 7, 7, 7, 7, charisma, 7),
        age=14,
        aggression=0.5,
        libido=libido,
        fertility=fertility,
        sexuality=sexuality,
        active_abilities=[],
        passive_abilities=[],
        disorders=disorders,
        body_parts={CatBodySlot.TEXTURE: 1},
        level=7,
        collar="",
        coi=0.0,
        lover=None,
        lover_affinity=1.0,
        hater=None,
        hater_affinity=1.0,
    )


class TestHeuristicCacheBug:
    """Tests for potential cache-related bugs in HeuristicCalculator.

    BUG UNDER TEST: When cache hits, pair_keys dict is empty, causing
    row_compat_sum to remain all zeros, leading to division by zero (NaN).
    """

    def test_first_call_no_cache(self):
        """Basic sanity: first call works and returns valid numbers."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
        ]
        calc = HeuristicCalculator()
        result = calc.get_expected_kittens(cats, 5.0)

        assert len(result) > 0, "Expected at least one pair"
        for pair, value in result.items():
            assert value == value, f"NaN detected for pair {pair}"
            assert value >= 0, f"Negative value {value} for pair {pair}"

    def test_cache_hit_returns_same_as_miss(self):
        """Verify cache hit returns same values as cache miss."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
            make_cat(3, CatGender.MALE, 10),
            make_cat(4, CatGender.FEMALE, 10),
        ]
        calc = HeuristicCalculator()

        result1 = calc.get_expected_kittens(cats, 5.0)
        result2 = calc.get_expected_kittens(cats, 5.0)

        assert len(result1) == len(result2), "Cache hit changed result length"
        for pair in result1:
            assert pair in result2, f"Pair {pair} missing in cache hit result"
            v1, v2 = result1[pair], result2[pair]
            assert v1 == v1 and v2 == v2, f"NaN in results for pair {pair}"
            assert abs(v1 - v2) < 1e-10, (
                f"Cache hit changed value for pair {pair}: {v1} -> {v2}"
            )

    def test_multiple_cats_all_pairs_valid(self):
        """Test with 4 cats to ensure pair_keys is populated correctly."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
            make_cat(3, CatGender.MALE, 10),
            make_cat(4, CatGender.FEMALE, 10),
        ]
        calc = HeuristicCalculator()
        result = calc.get_expected_kittens(cats, 5.0)

        expected_pairs = 4
        assert len(result) >= expected_pairs, (
            f"Expected at least {expected_pairs} pairs, got {len(result)}"
        )

        for pair, value in result.items():
            assert value == value, f"NaN for pair {pair}"
            assert value >= 0, f"Negative value {value} for pair {pair}"

    def test_cache_hit_with_different_comfort(self):
        """Test that cache hit returns same compat matrix but different results for different comfort.

        This test exposes the BUG: the cache key only includes cat db_keys,
        not comfort. So different comfort values will return the same cached
        compat/fertility matrices but should compute different expected_kittens.
        """
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
            make_cat(3, CatGender.MALE, 10),
            make_cat(4, CatGender.FEMALE, 10),
        ]
        calc = HeuristicCalculator()

        result_low = calc.get_expected_kittens(cats, 1.0)
        result_high = calc.get_expected_kittens(cats, 10.0)

        for pair in result_low:
            v_low = result_low[pair]
            v_high = result_high.get(pair, v_low)
            assert v_low == v_low and v_high == v_high, f"NaN for pair {pair}"
            if pair in result_high:
                assert v_high >= v_low, (
                    f"Higher comfort should give equal or higher kittens for pair {pair}"
                )

    def test_consecutive_calls_produce_consistent_results(self):
        """Stress test: multiple consecutive calls should always return same values."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
            make_cat(3, CatGender.MALE, 10),
            make_cat(4, CatGender.FEMALE, 10),
        ]
        calc = HeuristicCalculator()

        results = []
        for i in range(10):
            result = calc.get_expected_kittens(cats, 5.0)
            results.append(result)

        for pair in results[0]:
            first_value = results[0][pair]
            assert first_value == first_value, f"NaN for pair {pair}"
            for i, result in enumerate(results[1:], 1):
                if pair in result:
                    assert abs(result[pair] - first_value) < 1e-10, (
                        f"Inconsistent value for pair {pair}: "
                        f"call 0 = {first_value}, call {i} = {result[pair]}"
                    )


class TestRoomSimulatorCache:
    """Tests for RoomSimulator caching behavior."""

    def test_simulator_cache_produces_valid_results(self):
        """Verify RoomSimulator returns valid results and uses cache."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
            make_cat(3, CatGender.MALE, 10),
            make_cat(4, CatGender.FEMALE, 10),
        ]
        sim = RoomSimulator(
            iterations=1000, early_stop_rounds=100, relative_tolerance=0.01
        )

        result1 = sim.get_expected_kittens(cats, 5.0)
        result2 = sim.get_expected_kittens(cats, 5.0)

        assert len(sim._cache) == 1, f"Expected 1 cache entry, got {len(sim._cache)}"

        for pair in result1:
            v1, v2 = result1[pair], result2[pair]
            assert v1 == v1 and v2 == v2, f"NaN for pair {pair}"
            assert abs(v1 - v2) < 1e-10, (
                f"Inconsistent MC results for pair {pair}: {v1} vs {v2}"
            )

    def test_simulator_different_comfort_different_cache_entry(self):
        """Verify different comfort creates different cache entry."""
        cats = [
            make_cat(1, CatGender.MALE, 10),
            make_cat(2, CatGender.FEMALE, 10),
        ]
        sim = RoomSimulator(
            iterations=1000, early_stop_rounds=100, relative_tolerance=0.01
        )

        sim.get_expected_kittens(cats, 1.0)
        sim.get_expected_kittens(cats, 10.0)

        assert len(sim._cache) == 2, (
            f"Expected 2 cache entries (one per comfort), got {len(sim._cache)}"
        )


class TestMonteCarloVsHeuristic:
    """Compare Monte Carlo simulation with heuristic approximation."""

    def test_heuristic_vs_mc_order_of_magnitude(self):
        """Heuristic and MC should be within reasonable order of magnitude."""
        cats = [
            make_cat(1, CatGender.MALE, 10, libido=1.0, sexuality=0.0),
            make_cat(2, CatGender.FEMALE, 10, libido=1.0, sexuality=0.0),
        ]

        calc = HeuristicCalculator()
        heuristic_result = calc.get_expected_kittens(cats, 5.0)

        from mewgenics_breeding import simulate_room_breeding

        mc_result = simulate_room_breeding(cats, 5.0, max_iterations=50000, seed=42)

        if heuristic_result and mc_result.pair_kittens:
            h_total = sum(heuristic_result.values())
            mc_total = sum(mc_result.pair_kittens.values())

            assert h_total > 0 and mc_total > 0, "Both should produce positive kittens"
            ratio = h_total / mc_total if mc_total > 0 else float("inf")
            assert 0.1 < ratio < 10.0, (
                f"Heuristic/MC ratio {ratio:.2f} outside reasonable range [0.1, 10]"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
