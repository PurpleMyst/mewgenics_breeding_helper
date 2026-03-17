"""Room optimization logic for Mewgenics breeding."""

import math
import random
from dataclasses import replace
from typing import Callable

from mewgenics_parser import Cat
from mewgenics_parser.trait_dictionary import normalize_trait_name
from mewgenics_scorer import (
    AncestorData,
    ScoringPreferences,
    calculate_pair_factors,
    calculate_pair_quality,
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
)

from .types import (
    OptimizationParams,
    OptimizationResult,
    OptimizationStats,
    RoomAssignment,
    RoomConfig,
    RoomType,
    ScoredPair,
)

PairCacheKey = tuple[int, int, float]


class PairCache:
    def __init__(self):
        self._cache: dict[PairCacheKey, ScoredPair | None] = {}

    def get_score(
        self,
        cat_a: Cat,
        cat_b: Cat,
        stim: float,
        scorer_func: Callable[[], ScoredPair | None],
    ) -> ScoredPair | None:
        key = (min(cat_a.db_key, cat_b.db_key), max(cat_a.db_key, cat_b.db_key), stim)
        if key not in self._cache:
            self._cache[key] = scorer_func()
        return self._cache[key]

    def clear(self):
        self._cache.clear()


def _has_eternalyouth(cat: Cat) -> bool:
    """Check if cat has EternalYouth passive."""
    return any(p.lower() == "eternalyouth" for p in (cat.passive_abilities or []))


def can_pair_gay(cat_a: Cat, cat_b: Cat, gay_flags: dict[int, bool]) -> bool:
    """Check if gay cats can breed based on gender restrictions."""
    is_a_gay = gay_flags.get(cat_a.db_key, False)
    is_b_gay = gay_flags.get(cat_b.db_key, False)

    return (not (is_a_gay or is_b_gay)) or "?" in {cat_a.gender, cat_b.gender}


def _cat_stats_sum(cat: Cat) -> int:
    """Calculate total base stats for a cat."""
    return sum(cat.stat_base)


def _filter_cats(cats: list[Cat], min_stats: int) -> list[Cat]:
    """Filter cats to only include valid breeding candidates."""
    return [
        c for c in cats if c.status == "In House" and _cat_stats_sum(c) >= min_stats
    ]


def _generate_pairs(
    cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Generate all valid male x female pairs."""
    males = [c for c in cats if c.gender == "male"]
    females = [c for c in cats if c.gender == "female"]
    unknown = [c for c in cats if c.gender == "?"]

    pairs = []
    pairs.extend((a, b) for a in males for b in females)
    pairs.extend((a, b) for a in males for b in unknown)
    pairs.extend((a, b) for a in females for b in unknown)
    pairs.extend((a, b) for i, a in enumerate(unknown) for b in unknown[i + 1 :])

    return pairs


def score_pair(
    cat_a: Cat,
    cat_b: Cat,
    ancestor_contribs: dict[int, dict[int, AncestorData]],
    params: OptimizationParams,
    skip_risk_check: bool = False,
) -> ScoredPair | None:
    """Score a pair, returning None if they can't be paired."""
    if not can_breed(cat_a, cat_b):
        return None

    if is_hater_conflict(cat_a, cat_b):
        return None

    if is_lover_conflict(cat_a, cat_b, params.avoid_lovers):
        return None

    if not can_pair_gay(cat_a, cat_b, params.gay_flags):
        return None

    factors = calculate_pair_factors(
        cat_a,
        cat_b,
        ancestor_contribs,
        stimulation=params.stimulation,
        avoid_lovers=params.avoid_lovers,
        planner_traits=params.planner_traits,
    )

    if not skip_risk_check and factors.combined_malady_chance > params.max_risk:
        return None

    scoring_prefs = params.scoring_prefs or ScoringPreferences()
    quality = calculate_pair_quality(factors, scoring_prefs)

    return ScoredPair(
        cat_a=cat_a,
        cat_b=cat_b,
        factors=factors,
        quality=quality,
    )


def _has_planner_trait(cat: Cat, params: OptimizationParams) -> bool:
    """Check if cat has any planner-selected traits."""
    for trait in params.planner_traits:
        for passive in cat.passive_abilities or []:
            if normalize_trait_name(passive) == trait.key:
                return True
        for ability in cat.active_abilities or []:
            if normalize_trait_name(ability) == trait.key:
                return True
    return False


def _can_fit_single(
    room: RoomConfig,
    current_count: int,
) -> bool:
    """Check if a single cat can fit in a room. EY cats are invisible to capacity."""
    if room.max_cats is None:
        return True
    return (current_count + 1) <= room.max_cats


def _evaluate_state(
    state_dict: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    ancestor_contribs: dict[int, dict[int, AncestorData]],
    params: OptimizationParams,
) -> float:
    """Evaluate total quality for a room assignment state."""
    total_quality = 0.0
    rooms_content: dict[str, list[Cat]] = {r.key: [] for r in room_configs}

    for cat_id, room_key in state_dict.items():
        if room_key in rooms_content and cat_id in cats_by_id:
            rooms_content[room_key].append(cats_by_id[cat_id])

    for room in room_configs:
        if room.room_type != RoomType.BREEDING:
            continue

        cats_in_room = rooms_content[room.key]

        # Hard capacity constraint
        if room.max_cats is not None and len(cats_in_room) > room.max_cats:
            return -float("inf")

        if len(cats_in_room) < 2:
            continue

        true_stim = room.base_stim
        pairs = _generate_pairs(cats_in_room)

        sum_quality = 0.0
        valid_pairs = 0
        valid_cats = set()

        for a, b in pairs:
            effective_params = replace(params, stimulation=true_stim)
            scored = pair_cache.get_score(
                a,
                b,
                true_stim,
                lambda: score_pair(a, b, ancestor_contribs, effective_params),
            )
            if scored:
                sum_quality += scored.quality
                valid_pairs += 1
                valid_cats.add(a.db_key)
                valid_cats.add(b.db_key)

        if valid_pairs == 0:
            continue

        # Expected quality of a single random breeding event in this room
        expected_breed_quality = sum_quality / valid_pairs

        # Percentage-based dilution penalty (1.0 = perfect, 0.5 = half the cats are useless)
        dilution_penalty = len(valid_cats) / len(cats_in_room)

        # --- Throughput Soft Constraint ---
        scoring_prefs = params.scoring_prefs or ScoringPreferences()
        if scoring_prefs.maximize_throughput:
            # Only count cats that actually form valid pairs towards the multiplier
            males = sum(
                1 for c in cats_in_room if c.gender == "male" and c.db_key in valid_cats
            )
            females = sum(
                1
                for c in cats_in_room
                if c.gender == "female" and c.db_key in valid_cats
            )
            spiders = sum(
                1 for c in cats_in_room if c.gender == "?" and c.db_key in valid_cats
            )

            # Calculate max simultaneous breeding pairs
            concurrent_breeds = min(
                len(valid_cats) // 2, males + spiders, females + spiders
            )

            # Apply an exponent to artificially inflate the value of high-capacity rooms.
            density_bonus = concurrent_breeds**1.5

            room_quality = expected_breed_quality * density_bonus * dilution_penalty
        else:
            room_quality = expected_breed_quality * dilution_penalty

        total_quality += room_quality

    return total_quality


def _get_neighbor(state: dict[int, str], rooms: list[str]) -> dict[int, str]:
    """Generate a neighboring state by moving one cat or swapping two cats."""
    new_state = state.copy()
    keys = list(new_state.keys())

    if not keys or not rooms:
        return new_state

    if random.random() < 0.5:
        new_state[random.choice(keys)] = random.choice(rooms)
    else:
        if len(keys) >= 2:
            c1, c2 = random.sample(keys, 2)
            new_state[c1], new_state[c2] = new_state[c2], new_state[c1]

    return new_state


def _run_sa_worker(
    initial_state: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    ancestor_contribs: dict[int, dict[int, AncestorData]],
    params: OptimizationParams,
    seed: int | None = None,
) -> tuple[dict[int, str], float]:
    """Run simulated annealing worker on a single state."""
    if seed is not None:
        random.seed(seed)

    T = params.sa_temperature
    T_min = 0.1
    cooling_rate = params.sa_cooling_rate
    neighbors_per_temp = params.sa_neighbors_per_temp

    current_state = initial_state.copy()
    current_score = _evaluate_state(
        current_state, cats_by_id, room_configs, pair_cache, ancestor_contribs, params
    )

    best_state = current_state.copy()
    best_score = current_score

    iteration = 0
    valid_rooms = [r.key for r in room_configs if r.room_type == RoomType.BREEDING] + [
        ""
    ]
    while T > T_min:
        for _ in range(neighbors_per_temp):
            neighbor = _get_neighbor(current_state, valid_rooms)
            neighbor_score = _evaluate_state(
                neighbor,
                cats_by_id,
                room_configs,
                pair_cache,
                ancestor_contribs,
                params,
            )

            if neighbor_score == -float("inf"):
                continue

            delta = neighbor_score - current_score

            if delta > 0 or math.exp(delta / T) > random.random():
                current_state = neighbor
                current_score = neighbor_score

                if current_score > best_score:
                    best_state = current_state.copy()
                    best_score = current_score

        T *= cooling_rate
        iteration += 1

    return best_state, best_score


def _generate_random_valid_state(
    cats: list[Cat],
    room_configs: list[RoomConfig],
    seed: int | None = None,
) -> dict[int, str]:
    """Generate a random valid state for SA initialization."""
    if seed is not None:
        random.seed(seed)

    # Initialize only into Breeding rooms
    valid_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]

    if not valid_rooms:
        return {c.db_key: "" for c in cats}

    state: dict[int, str] = {}
    room_cats: dict[str, list[Cat]] = {r.key: [] for r in valid_rooms}

    for cat in cats:
        available_rooms = []
        for room in valid_rooms:
            if _can_fit_single(room, len(room_cats[room.key])):
                available_rooms.append(room.key)

        if available_rooms:
            chosen_room = random.choice(available_rooms)
            state[cat.db_key] = chosen_room
            room_cats[chosen_room].append(cat)
        else:
            state[cat.db_key] = ""  # Leave unassigned if no breeding rooms fit

    return state


def optimize_sa(
    cats: list[Cat],
    room_configs: list[RoomConfig],
    params: OptimizationParams,
    ancestor_contribs: dict[int, dict[int, AncestorData]],
) -> OptimizationResult:
    """Optimize using Parallel Simulated Annealing."""
    import concurrent.futures
    import multiprocessing

    filtered_cats = _filter_cats(cats, params.min_stats)

    if not filtered_cats:
        return OptimizationResult(
            rooms=[],
            excluded_cats=[],
            stats=OptimizationStats(
                total_cats=0,
                assigned_cats=0,
                total_pairs=0,
                breeding_rooms_used=0,
                general_rooms_used=0,
                avg_pair_quality=0.0,
                avg_risk_percent=0.0,
            ),
        )

    sa_cats = [c for c in filtered_cats if not _has_eternalyouth(c)]
    ey_cats = [c for c in filtered_cats if _has_eternalyouth(c)]

    # Deterministically place EY cats into the best breeding room
    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    ey_assignments: dict[str, list[Cat]] = {r.key: [] for r in breeding_rooms}
    if breeding_rooms and ey_cats:
        best_room = max(breeding_rooms, key=lambda r: r.base_stim)
        ey_assignments[best_room.key] = ey_cats

    # Create boosted configs for the SA loop
    sa_room_configs = []
    for r in room_configs:
        if r.room_type == RoomType.BREEDING:
            bonus = len(ey_assignments.get(r.key, []))
            sa_room_configs.append(replace(r, base_stim=r.base_stim + bonus))
        else:
            sa_room_configs.append(r)

    cats_by_id = {c.db_key: c for c in sa_cats}
    pair_cache = PairCache()

    num_workers = max(1, multiprocessing.cpu_count() - 1)
    initial_states = [
        _generate_random_valid_state(sa_cats, sa_room_configs, seed=i)
        for i in range(num_workers)
    ]

    best_overall_state = None
    best_overall_score = -float("inf")

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                _run_sa_worker,
                state,
                cats_by_id,
                sa_room_configs,
                pair_cache,
                ancestor_contribs,
                params,
                i,
            )
            for i, state in enumerate(initial_states)
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                final_state, final_score = future.result()
                if final_score > best_overall_score:
                    best_overall_score = final_score
                    best_overall_state = final_state
            except Exception:
                pass

    if best_overall_state is None:
        best_overall_state = {}

    return _build_results_from_state_dict(
        best_overall_state,
        cats_by_id,
        sa_room_configs,
        pair_cache,
        ancestor_contribs,
        params,
        sa_cats,
        ey_assignments,
        filtered_cats,
    )


def _build_results_from_state_dict(
    state_dict: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    ancestor_contribs: dict[int, dict[int, AncestorData]],
    params: OptimizationParams,
    sa_cats: list[Cat],
    ey_assignments: dict[str, list[Cat]],
    filtered_cats: list[Cat],
) -> OptimizationResult:
    """Build OptimizationResult from a state dictionary."""
    rooms_content: dict[str, list[Cat]] = {r.key: [] for r in room_configs}
    assigned_cats: set[int] = set()

    for cat_id, room_key in state_dict.items():
        if room_key in rooms_content and cat_id in cats_by_id:
            rooms_content[room_key].append(cats_by_id[cat_id])
            assigned_cats.add(cat_id)

    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    room_pairs: dict[str, list[ScoredPair]] = {r.key: [] for r in room_configs}

    for room in breeding_rooms:
        cats_in_room = rooms_content[room.key]
        if len(cats_in_room) < 2:
            continue

        pairs = _generate_pairs(cats_in_room)
        for a, b in pairs:
            effective_params = replace(params, stimulation=room.base_stim)
            scored = pair_cache.get_score(
                a,
                b,
                room.base_stim,
                lambda: score_pair(a, b, ancestor_contribs, effective_params),
            )
            if scored:
                room_pairs[room.key].append(scored)

    # --- POST-PROCESSING CLEANUP ---
    # Pack remaining cats into Fighting and General rooms deterministically
    unassigned = [c for c in sa_cats if c.db_key not in assigned_cats]
    general_rooms = [r for r in room_configs if r.room_type == RoomType.GENERAL]
    fighting_rooms = [r for r in room_configs if r.room_type == RoomType.FIGHTING]

    # Trait carriers to General rooms first
    trait_cats = [c for c in unassigned if _has_planner_trait(c, params)]
    for cat in trait_cats:
        for room in general_rooms:
            if _can_fit_single(room, len(rooms_content[room.key])):
                rooms_content[room.key].append(cat)
                assigned_cats.add(cat.db_key)
                break

    # Remaining high-stat cats to Fighting, then General
    remaining = [c for c in unassigned if c.db_key not in assigned_cats]
    remaining.sort(key=lambda c: sum(c.stat_base), reverse=True)
    for cat in remaining:
        for room in fighting_rooms + general_rooms:
            if _can_fit_single(room, len(rooms_content[room.key])):
                rooms_content[room.key].append(cat)
                assigned_cats.add(cat.db_key)
                break

    excluded = [c for c in sa_cats if c.db_key not in assigned_cats]

    room_results: list[RoomAssignment] = []
    breeding_rooms_used = 0
    general_rooms_used = 0
    total_pair_quality = 0.0
    total_risk = 0.0
    total_pairs = 0

    for config in room_configs:
        cats_in_room = rooms_content[config.key]
        pairs_in_room = room_pairs[config.key]
        ey_cats = ey_assignments.get(config.key, [])

        if cats_in_room or pairs_in_room or ey_cats:
            room_results.append(
                RoomAssignment(
                    room=config,
                    cats=cats_in_room,
                    pairs=pairs_in_room,
                    eternal_youth_cats=ey_cats,
                )
            )

            if config.room_type == RoomType.BREEDING:
                breeding_rooms_used += 1
            elif config.room_type == RoomType.GENERAL:
                general_rooms_used += 1

            total_pairs += len(pairs_in_room)
            for p in pairs_in_room:
                total_pair_quality += p.quality
                total_risk += p.factors.combined_malady_chance * 100

    avg_quality = total_pair_quality / total_pairs if total_pairs > 0 else 0.0
    avg_risk = total_risk / total_pairs if total_pairs > 0 else 0.0

    stats = OptimizationStats(
        total_cats=len(filtered_cats),
        assigned_cats=len(filtered_cats) - len(excluded),
        total_pairs=total_pairs,
        breeding_rooms_used=breeding_rooms_used,
        general_rooms_used=general_rooms_used,
        avg_pair_quality=avg_quality,
        avg_risk_percent=avg_risk,
    )

    return OptimizationResult(
        rooms=room_results,
        excluded_cats=excluded,
        stats=stats,
    )
