"""Room optimization logic for Mewgenics breeding."""

import math
import random
from dataclasses import replace
from typing import Callable

from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatGender
from mewgenics_scorer import (
    TraitRequirement,
    calculate_pair_factors,
    calculate_pair_quality,
    can_breed,
)

from .types import (
    OptimizationResult,
    OptimizationStats,
    RoomAssignment,
    RoomConfig,
    RoomType,
    ScoredPair,
)

MOVE_PENALTY = 0.5

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


def _cat_stats_sum(cat: Cat) -> int:
    """Calculate total base stats for a cat."""
    return sum(cat.stat_base)


def _calculate_trait_weight_sum(
    cat: Cat,
    trait_requirements: list[TraitRequirement],
) -> float:
    """Calculate sum of weights of favorable traits possessed by a cat."""
    if not trait_requirements:
        return 0.0
    return sum(tr.weight for tr in trait_requirements if tr.trait.is_possessed_by(cat))


def _filter_cats(cats: list[Cat]) -> list[Cat]:
    """Filter cats to only include valid breeding candidates."""
    return [c for c in cats if c.status == "In House"]


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


def _filter_lover_exclusivity(
    pairs: list[tuple[Cat, Cat]],
    room_cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Filter pairs that violate per-room lover exclusivity.

    Rule: If a cat's lover is in this room, they can only breed with that lover.
    Cats with lovers in different rooms can breed with anyone here.
    """
    room_cat_ids = {c.db_key for c in room_cats}
    lover_lookup: dict[int, int | None] = {
        c.db_key: c.lover_id
        for c in room_cats
        if c.lover is not None and c.lover_id in room_cat_ids
    }

    filtered = []
    for a, b in pairs:
        a_lover = lover_lookup.get(a.db_key)
        b_lover = lover_lookup.get(b.db_key)

        if a_lover is not None and b.db_key != a_lover:
            continue
        if b_lover is not None and a.db_key != b_lover:
            continue

        filtered.append((a, b))

    return filtered


def _filter_hater_conflicts(
    pairs: list[tuple[Cat, Cat]],
    room_cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Filter pairs that have hater conflicts within the room.

    Rule: If cat A hates cat B and both are in this room, they can't breed.
    Cats with haters in different rooms can breed with anyone here.
    """
    room_cat_ids = {c.db_key for c in room_cats}
    hater_lookup: dict[int, set[int]] = {c.db_key: set() for c in room_cats}

    for c in room_cats:
        if c.hater is not None and c.hater_id in room_cat_ids:
            hater_lookup[c.db_key].add(c.hater_id)

    filtered = []
    for a, b in pairs:
        a_hates_b = b.db_key in hater_lookup.get(a.db_key, set())
        b_hates_a = a.db_key in hater_lookup.get(b.db_key, set())

        if a_hates_b or b_hates_a:
            continue

        filtered.append((a, b))

    return filtered


def score_pair(
    save_data: SaveData,
    cat_a: Cat,
    cat_b: Cat,
    trait_requirements: list[TraitRequirement],
    stimulation: float,
) -> ScoredPair | None:
    """Score a pair, returning None if they can't be paired."""
    if not can_breed(cat_a, cat_b):
        return None

    factors = calculate_pair_factors(
        save_data,
        cat_a,
        cat_b,
        stimulation=stimulation,
        trait_requirements=trait_requirements,
    )

    quality = calculate_pair_quality(factors)

    sex_a = cat_a.sexuality or 0.0
    sex_b = cat_b.sexuality or 0.0
    breeding_prob = (1 - sex_a) * (1 - sex_b)
    quality = quality * breeding_prob

    return ScoredPair(
        cat_a=cat_a,
        cat_b=cat_b,
        factors=factors,
        quality=quality,
    )


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
    original_state: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    save_data: SaveData,
    traits_requirements: list[TraitRequirement],
) -> float:
    """Evaluate total quality for a room assignment state using pure EV math."""
    total_quality = 0.0
    rooms_content: dict[str, list[Cat]] = {r.key: [] for r in room_configs}

    for cat_id, room_key in state_dict.items():
        if room_key in rooms_content and cat_id in cats_by_id:
            rooms_content[room_key].append(cats_by_id[cat_id])

    for room in room_configs:
        if room.room_type != RoomType.BREEDING:
            continue

        cats_in_room = rooms_content[room.key]
        N_r = len(cats_in_room)

        if room.max_cats is not None and N_r > room.max_cats:
            excess = N_r - room.max_cats
            total_quality -= 1000.0 * (excess**2)

        if N_r < 2:
            continue

        true_stim = room.base_stim
        pairs = _generate_pairs(cats_in_room)
        pairs = _filter_lover_exclusivity(pairs, cats_in_room)
        pairs = _filter_hater_conflicts(pairs, cats_in_room)

        sum_quality = 0.0
        valid_pairs = 0
        valid_cats = set()

        for a, b in pairs:
            scored = pair_cache.get_score(
                a,
                b,
                true_stim,
                lambda: score_pair(save_data, a, b, traits_requirements, true_stim),
            )
            if scored:
                sum_quality += scored.quality
                valid_pairs += 1
                valid_cats.add(a.db_key)
                valid_cats.add(b.db_key)

        if valid_pairs == 0:
            continue

        total_possible_pairs = (N_r * (N_r - 1)) / 2.0
        expected_quality_per_tick = sum_quality / total_possible_pairs

        males, females, dittos = 0, 0, 0
        for c in cats_in_room:
            if c.db_key not in valid_cats:
                continue
            match c.gender:
                case CatGender.MALE:
                    males += 1
                case CatGender.FEMALE:
                    females += 1
                case CatGender.DITTO:
                    dittos += 1

        concurrent_breeds = min(
            len(valid_cats) // 2,
            males + dittos,
            females + dittos,
            room.max_cats // 2 if room.max_cats else float("inf"),
        )

        room_quality = concurrent_breeds * expected_quality_per_tick

        total_quality += room_quality

    cats_moved = sum(
        1 for cid, r in state_dict.items() if r != original_state.get(cid) and r
    )
    total_quality -= cats_moved * MOVE_PENALTY

    return total_quality


def _get_neighbor(
    state: dict[int, str], room_configs: list[RoomConfig]
) -> dict[int, str]:
    """Generate a neighboring state by moving one cat or swapping two cats.

    Uses biased room selection to favor under-capacity rooms.
    """
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


def _run_sa_worker(
    initial_state: dict[int, str],
    original_state: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    save_data: SaveData,
    trait_requirements: list[TraitRequirement],
    seed: int | None = None,
) -> tuple[dict[int, str], float]:
    """Run simulated annealing worker on a single state."""
    if seed is not None:
        random.seed(seed)

    T_MIN = 0.1
    COOLING_RATE = 0.95
    NEIGHBORS_PER_TEMP = 200

    current_state = initial_state.copy()
    current_score = _evaluate_state(
        current_state,
        original_state,
        cats_by_id,
        room_configs,
        pair_cache,
        save_data,
        trait_requirements,
    )

    positive_deltas: list[float] = []
    test_state = current_state.copy()
    test_score = current_score

    for _ in range(100):
        neighbor = _get_neighbor(test_state, room_configs)
        n_score = _evaluate_state(
            neighbor,
            original_state,
            cats_by_id,
            room_configs,
            pair_cache,
            save_data,
            trait_requirements,
        )
        if n_score > test_score:
            positive_deltas.append(n_score - test_score)
        test_state = neighbor
        test_score = n_score

    avg_delta = sum(positive_deltas) / len(positive_deltas) if positive_deltas else 1.0
    T = -avg_delta / math.log(0.8)

    best_state = current_state.copy()
    best_score = current_score

    iteration = 0
    while T > T_MIN:
        for _ in range(NEIGHBORS_PER_TEMP):
            neighbor = _get_neighbor(current_state, room_configs)
            neighbor_score = _evaluate_state(
                neighbor,
                original_state,
                cats_by_id,
                room_configs,
                pair_cache,
                save_data,
                trait_requirements,
            )

            delta = neighbor_score - current_score

            if delta > 0 or math.exp(delta / T) > random.random():
                current_state = neighbor
                current_score = neighbor_score

                if current_score > best_score:
                    best_state = current_state.copy()
                    best_score = current_score

        T *= COOLING_RATE
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
    save_data: SaveData,
    room_configs: list[RoomConfig],
    trait_requirements: list[TraitRequirement],
) -> OptimizationResult:
    """Optimize using Parallel Simulated Annealing."""
    import concurrent.futures
    import multiprocessing

    cats = save_data.cats
    filtered_cats = _filter_cats(cats)

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

    sa_cats = [c for c in filtered_cats if not c.has_eternal_youth()]
    ey_cats = [c for c in filtered_cats if c.has_eternal_youth()]

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

    # Build original state from save file (current room assignments)
    original_state = {c.db_key: c.room or "" for c in cats}

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
                original_state,
                cats_by_id,
                sa_room_configs,
                pair_cache,
                save_data,
                trait_requirements,
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
        save_data,
        trait_requirements,
        sa_cats,
        ey_assignments,
        filtered_cats,
    )


def _build_results_from_state_dict(
    state_dict: dict[int, str],
    cats_by_id: dict[int, Cat],
    room_configs: list[RoomConfig],
    pair_cache: PairCache,
    save_data: SaveData,
    trait_requirements: list[TraitRequirement],
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
            scored = pair_cache.get_score(
                a,
                b,
                room.base_stim,
                lambda: score_pair(save_data, a, b, trait_requirements, room.base_stim),
            )
            if scored:
                room_pairs[room.key].append(scored)

    # --- POST-PROCESSING CLEANUP ---
    unassigned = [c for c in sa_cats if c.db_key not in assigned_cats]
    general_rooms = [r for r in room_configs if r.room_type == RoomType.GENERAL]
    fighting_rooms = [r for r in room_configs if r.room_type == RoomType.FIGHTING]

    # Sort descending by (trait_weight_sum, stat_sum) - higher value = more desirable
    unassigned.sort(
        key=lambda c: (
            _calculate_trait_weight_sum(c, trait_requirements),
            sum(c.stat_base),
        ),
        reverse=True,
    )

    for cat in unassigned:
        trait_weight = _calculate_trait_weight_sum(cat, trait_requirements)
        rooms_to_try = (
            (general_rooms + fighting_rooms)
            if trait_weight > 0
            else (fighting_rooms + general_rooms)
        )

        for room in rooms_to_try:
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
