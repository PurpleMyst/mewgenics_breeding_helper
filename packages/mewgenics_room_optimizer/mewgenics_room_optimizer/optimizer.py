"""Room optimization logic for Mewgenics breeding with ENS architecture."""

from concurrent.futures import ProcessPoolExecutor, as_completed

import math
import random
from collections import defaultdict
from dataclasses import replace

from mewgenics_breeding import RoomSimulator, HeuristicCalculator
from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatStatus
from mewgenics_scorer import (
    TargetBuild,
    TraitWeight,
)

from .types import (
    OptimizationResult,
    RoomConfig,
    RoomType,
)
from .allocator import RoomAllocator, CachingScorer, compute_ey_assignments

MOVE_PENALTY = 0.5


def _score_state_with_mc(
    state_dict: dict[int, str],
    room_configs: list[RoomConfig],
    save_data: SaveData,
    universals: list[TraitWeight] | None,
    target_builds: list[TargetBuild] | None,
    original_state: dict[int, str],
    mc_iterations: int,
    mc_early_stop_rounds: int,
    mc_relative_tolerance: float,
) -> float:
    """Evaluate total quality for a room assignment state using Monte Carlo simulation."""
    scorer = CachingScorer(
        save_data=save_data,
        universals=universals,
        target_builds=target_builds,
    )
    room_simulator = RoomSimulator(
        iterations=mc_iterations,
        early_stop_rounds=mc_early_stop_rounds,
        relative_tolerance=mc_relative_tolerance,
    )

    house_build_yields: dict[str, float] = defaultdict(float)
    total_base_quality = 0.0
    rooms_content: dict[str, list[Cat]] = {r.key: [] for r in room_configs}

    for cat_id, room_key in state_dict.items():
        if room_key in rooms_content:
            rooms_content[room_key].append(save_data.cats_by_id[cat_id])

    for room in room_configs:
        if room.room_type != RoomType.BREEDING:
            continue

        cats_in_room = rooms_content[room.key]

        if room.max_cats is not None and len(cats_in_room) > room.max_cats:
            excess = len(cats_in_room) - room.max_cats
            total_base_quality -= 1000.0 * (excess**2)

        if len(cats_in_room) < 2:
            continue

        room_kittens = room_simulator.get_expected_kittens(cats_in_room, room.comfort)

        cats_by_id = {c.db_key: c for c in cats_in_room}
        pair_quality_total = 0.0
        for (a_key, b_key), expected_kittens in room_kittens.items():
            if expected_kittens <= 0:
                continue
            a = cats_by_id.get(a_key)
            b = cats_by_id.get(b_key)
            if a is None or b is None:
                continue
            scored = scorer.score_pair(a, b, room.stimulation)
            if scored is None:
                continue
            pair_quality_total += expected_kittens * scored.quality
            for build_name, yield_value in scored.factors.build_yields.items():
                house_build_yields[build_name] += expected_kittens * yield_value

        if pair_quality_total == 0.0:
            continue

        total_base_quality += pair_quality_total

    house_diversity_bonus = sum(math.sqrt(y) for y in house_build_yields.values())

    if target_builds is not None:
        for build in target_builds:
            if house_build_yields[build.name] < 1e-6:
                house_diversity_bonus -= 1000.0

    cats_moved = sum(
        1 for cid, r in state_dict.items() if r != original_state.get(cid) and r
    )
    total_base_quality -= cats_moved * MOVE_PENALTY

    return total_base_quality + house_diversity_bonus


def _run_sa_worker(
    initial_state: dict[int, str],
    original_state: dict[int, str],
    room_configs: list[RoomConfig],
    save_data: SaveData,
    universals: list[TraitWeight] | None,
    target_builds: list[TargetBuild] | None,
    ey_assignments: dict[str, list[Cat]],
) -> tuple[dict[int, str], float]:
    """Run simulated annealing worker, return (best_state_dict, heuristic_score)."""
    scorer = CachingScorer(
        save_data=save_data,
        universals=universals,
        target_builds=target_builds,
    )
    heuristic_calc = HeuristicCalculator()

    def evaluate_state(state: dict[int, str]) -> float:
        house_build_yields: dict[str, float] = defaultdict(float)
        total_base_quality = 0.0
        rooms_content: dict[str, list[Cat]] = {r.key: [] for r in room_configs}

        for cat_id, room_key in state.items():
            if room_key in rooms_content:
                rooms_content[room_key].append(save_data.cats_by_id[cat_id])

        for room in room_configs:
            if room.room_type != RoomType.BREEDING:
                continue

            cats_in_room = rooms_content[room.key]

            if room.max_cats is not None and len(cats_in_room) > room.max_cats:
                excess = len(cats_in_room) - room.max_cats
                total_base_quality -= 1000.0 * (excess**2)

            if len(cats_in_room) < 2:
                continue

            room_kittens = heuristic_calc.get_expected_kittens(
                cats_in_room, room.comfort
            )

            cats_by_id = {c.db_key: c for c in cats_in_room}
            pair_quality_total = 0.0
            for (a_key, b_key), expected_kittens in room_kittens.items():
                if expected_kittens <= 0:
                    continue
                a = cats_by_id.get(a_key)
                b = cats_by_id.get(b_key)
                if a is None or b is None:
                    continue
                scored = scorer.score_pair(a, b, room.stimulation)
                if scored is None:
                    continue
                pair_quality_total += expected_kittens * scored.quality
                for build_name, yield_value in scored.factors.build_yields.items():
                    house_build_yields[build_name] += expected_kittens * yield_value

            if pair_quality_total == 0.0:
                continue

            total_base_quality += pair_quality_total

        house_diversity_bonus = sum(math.sqrt(y) for y in house_build_yields.values())

        if target_builds is not None:
            for build in target_builds:
                if house_build_yields[build.name] < 1e-6:
                    house_diversity_bonus -= 1000.0

        cats_moved = sum(
            1 for cid, r in state.items() if r != original_state.get(cid) and r
        )
        total_base_quality -= cats_moved * MOVE_PENALTY

        return total_base_quality + house_diversity_bonus

    T_MIN = 0.1
    COOLING_RATE = 0.95
    NEIGHBORS_PER_TEMP = 200

    current_state = initial_state.copy()
    current_score = evaluate_state(current_state)

    positive_deltas: list[float] = []
    test_state = current_state.copy()
    test_score = current_score

    for _ in range(100):
        neighbor = _get_neighbor(test_state, room_configs)
        n_score = evaluate_state(neighbor)
        if n_score > test_score:
            positive_deltas.append(n_score - test_score)
        test_state = neighbor
        test_score = n_score

    avg_delta = sum(positive_deltas) / len(positive_deltas) if positive_deltas else 1.0
    T = -avg_delta / math.log(0.8)

    best_state = current_state.copy()
    best_score = current_score

    while T > T_MIN:
        for _ in range(NEIGHBORS_PER_TEMP):
            neighbor = _get_neighbor(current_state, room_configs)
            neighbor_score = evaluate_state(neighbor)

            delta = neighbor_score - current_score

            if delta > 0 or math.exp(delta / T) > random.random():
                current_state = neighbor
                current_score = neighbor_score

                if current_score > best_score:
                    best_state = current_state.copy()
                    best_score = current_score

        T *= COOLING_RATE

    return best_state, best_score


def _get_neighbor(
    state: dict[int, str], room_configs: list[RoomConfig]
) -> dict[int, str]:
    """Generate a neighboring state by moving one cat or swapping two cats."""
    new_state = state.copy()
    keys = list(new_state.keys())

    if not keys:
        return new_state

    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    if not breeding_rooms:
        return new_state

    if random.random() < 0.5:
        cat_to_move = random.choice(keys)

        room_counts: dict[str, int] = {r.key: 0 for r in breeding_rooms}
        for r_key in new_state.values():
            if r_key in room_counts:
                room_counts[r_key] += 1

        weights: list[float] = []
        valid_keys: list[str] = []
        for r in breeding_rooms:
            valid_keys.append(r.key)
            if r.max_cats is None:
                weights.append(1.0)
            else:
                remaining = max(0.1, r.max_cats - room_counts[r.key])
                weights.append(remaining)

        valid_keys.append("")
        weights.append(0.5)

        new_state[cat_to_move] = random.choices(valid_keys, weights=weights, k=1)[0]
    else:
        if len(keys) >= 2:
            c1, c2 = random.sample(keys, 2)
            new_state[c1], new_state[c2] = new_state[c2], new_state[c1]

    return new_state


def _generate_random_valid_state(
    cats: list[Cat],
    room_configs: list[RoomConfig],
) -> dict[int, str]:
    """Generate a random valid state for SA initialization."""
    valid_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]

    if not valid_rooms:
        return {c.db_key: "" for c in cats}

    state: dict[int, str] = {cat.db_key: "" for cat in cats}
    room_cats: dict[str, list[Cat]] = {r.key: [] for r in valid_rooms}

    shuffled_cats = cats[:]
    random.shuffle(shuffled_cats)
    for cat in shuffled_cats:
        available_rooms = []
        for room in valid_rooms:
            if RoomAllocator.can_fit_single(room, len(room_cats[room.key])):
                available_rooms.append(room.key)

        if available_rooms:
            chosen_room = random.choice(available_rooms)
            state[cat.db_key] = chosen_room
            room_cats[chosen_room].append(cat)

    return state


def optimize_sa(
    save_data: SaveData,
    room_configs: list[RoomConfig],
    universals: list[TraitWeight] | None = None,
    target_builds: list[TargetBuild] | None = None,
    mc_iterations: int = 10_000,
    mc_early_stop_rounds: int = 500,
    mc_relative_tolerance: float = 0.01,
) -> OptimizationResult:
    """Optimize using Parallel Simulated Annealing with Monte Carlo final selection.

    Args:
        save_data: Save data containing cats.
        room_configs: Room configurations.
        universals: Optional trait weights for universals.
        target_builds: Optional target builds to optimize for.
        mc_iterations: Iterations for Monte Carlo simulation during final selection.
        mc_early_stop_rounds: Early stop rounds for MC convergence.
        mc_relative_tolerance: Relative tolerance for MC early stopping.
    """
    import multiprocessing

    cats = save_data.cats
    house_cats = [c for c in cats if c.status == CatStatus.IN_HOUSE]

    if not house_cats:
        return OptimizationResult(rooms=[])

    sa_cats = [c for c in house_cats if c.can_breed()]
    ey_cats = [c for c in house_cats if c.has_eternal_youth()]

    ey_assignments = compute_ey_assignments(ey_cats, room_configs)

    sa_room_configs = []
    for r in room_configs:
        if r.room_type == RoomType.BREEDING:
            bonus = len(ey_assignments.get(r.key, []))
            sa_room_configs.append(replace(r, stimulation=r.stimulation + bonus))
        else:
            sa_room_configs.append(r)

    original_state = {c.db_key: c.room or "" for c in cats}

    num_workers = max(1, multiprocessing.cpu_count() - 1)
    initial_states = [
        _generate_random_valid_state(sa_cats, sa_room_configs)
        for _ in range(num_workers)
    ]
    for state in initial_states:
        assert frozenset(state.keys()) == frozenset(c.db_key for c in sa_cats)

    print(f"Running SA with {num_workers} workers...")
    sa_results: list[tuple[dict[int, str], float]] = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _run_sa_worker,
                state,
                original_state,
                sa_room_configs,
                save_data,
                universals,
                target_builds,
                ey_assignments,
            ): i
            for i, state in enumerate(initial_states)
        }

        for future in as_completed(futures):
            worker_id = futures[future]
            best_state, h_score = future.result()
            sa_results.append((best_state, h_score))
            print(f"  Worker {worker_id}: heuristic_score={h_score:.4f}")

    print(f"Re-evaluating {len(sa_results)} states with Monte Carlo...")
    mc_results: list[tuple[dict[int, str], float, float]] = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _score_state_with_mc,
                state_dict,
                sa_room_configs,
                save_data,
                universals,
                target_builds,
                original_state,
                mc_iterations,
                mc_early_stop_rounds,
                mc_relative_tolerance,
            ): (state_dict, h_score)
            for state_dict, h_score in sa_results
        }

        for future in as_completed(futures):
            state_dict, h_score = futures[future]
            mc_score = future.result()
            mc_results.append((state_dict, mc_score, h_score))
            diff = mc_score - h_score
            diff_pct = (diff / h_score * 100) if h_score != 0 else 0
            print(
                f"  heuristic={h_score:.4f}, mc={mc_score:.4f}, "
                f"diff={diff:+.4f} ({diff_pct:+.1f}%)"
            )

    mc_results.sort(key=lambda x: x[1], reverse=True)
    best_state_dict, best_mc_score, best_h_score = mc_results[0]
    print(
        f"MC selection: mc_score={best_mc_score:.4f} "
        f"(heuristic had it at {best_h_score:.4f})"
    )

    allocator = RoomAllocator(
        room_configs=sa_room_configs,
        ey_assignments=ey_assignments,
        universals=universals,
        target_builds=target_builds,
    )
    scorer = CachingScorer(
        save_data=save_data,
        universals=universals,
        target_builds=target_builds,
    )

    best_overall_state = allocator.allocate(best_state_dict, save_data, scorer)

    return best_overall_state
