"""Room optimization logic for Mewgenics breeding with ENS architecture."""

from concurrent.futures import Future

import math
import random
from collections import defaultdict
from dataclasses import replace, dataclass

from mewgenics_breeding.pairs import (
    filter_hater_conflicts,
    filter_lover_exclusivity,
    generate_pairs,
)
from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatGender, CatStatus
from mewgenics_scorer import (
    TargetBuild,
    TraitWeight,
)

from .types import (
    OptimizationResult,
    RoomConfig,
    RoomType,
    ScoredPair,
)
from .allocator import RoomAllocator, CachingScorer, compute_ey_assignments

MOVE_PENALTY = 0.5


@dataclass(slots=True)
class _AnnealingWorker:
    initial_state: dict[int, str]
    original_state: dict[int, str]
    room_configs: list[RoomConfig]
    save_data: SaveData
    universals: list[TraitWeight] | None
    target_builds: list[TargetBuild] | None
    _allocator: RoomAllocator
    _scorer: CachingScorer

    def _evaluate_state(
        self,
        state_dict: dict[int, str],
    ) -> float:
        """Evaluate total quality for a room assignment state using ENS math.

        Returns the total quality score
        """
        house_build_yields: dict[str, float] = defaultdict(float)
        total_base_quality = 0.0
        rooms_content: dict[str, list[Cat]] = {r.key: [] for r in self.room_configs}

        for cat_id, room_key in state_dict.items():
            if room_key in rooms_content:
                rooms_content[room_key].append(self.save_data.cats_by_id[cat_id])

        for room in self.room_configs:
            if room.room_type != RoomType.BREEDING:
                continue

            cats_in_room = rooms_content[room.key]

            # Penalize over-capacity rooms heavily to steer SA away from invalid states, but allow them
            # to be explored as part of the search.
            if room.max_cats is not None and len(cats_in_room) > room.max_cats:
                excess = len(cats_in_room) - room.max_cats
                total_base_quality -= 1000.0 * (excess**2)

            # Lone cats don't breed :p
            if len(cats_in_room) < 2:
                continue

            # Generate pairs and filter to valid pairs based on lover exclusivity and hater conflicts;
            # while those are sometimes violated in the game, I don't know the exact mechanics and I'd
            # rather exclude them outright to avoid overestimating breeding potential of certain room
            # comps.
            pairs = generate_pairs(cats_in_room)
            pairs = filter_lover_exclusivity(pairs, cats_in_room)
            pairs = filter_hater_conflicts(pairs, cats_in_room)

            # Score every possible pair and aggregate total quality and build yields.
            # Also keep track of which cats are actually contributing to breeding.
            total_pair_quality = 0.0
            useful_pair_count = 0
            build_yields = defaultdict(lambda: 0.0)
            useful_cats = set()
            for a, b in pairs:
                scored = self._scorer.score_pair(a, b, room.stimulation)
                if scored is not None:
                    total_pair_quality += scored.quality
                    useful_pair_count += 1
                    for build_name, yield_value in scored.factors.build_yields.items():
                        build_yields[build_name] += yield_value
                    useful_cats.add(a.db_key)
                    useful_cats.add(b.db_key)
            if not useful_pair_count:
                continue

            # Calculate the total pairs possible in the room to correctly consider dilution of
            # non-offspring-producing pairs when estimating the room's contribution to the overall
            # score, which is important for steering towards comps where more cats are contributing
            # to breeding.
            total_pair_count = len(cats_in_room) * (len(cats_in_room) - 1) / 2

            useful_males, useful_females, useful_dittos = 0, 0, 0
            for c in cats_in_room:
                if c.db_key not in useful_cats:
                    continue
                match c.gender:
                    case CatGender.MALE:
                        useful_males += 1
                    case CatGender.FEMALE:
                        useful_females += 1
                    case CatGender.DITTO:
                        useful_dittos += 1

            # Estimate the contribution of a room to the overall score by multiplying the average pair
            # quality by the number of concurrent breeds that can happen in this room, i.e. avoid
            # situations where a single stud contributes morbillion quality points but can only breed
            # with one partner while the rest are just dead weight.
            concurrent_breeds = min(
                len(useful_cats) // 2,
                useful_males + useful_dittos,
                useful_females + useful_dittos,
                room.max_cats // 2 if room.max_cats else float("inf"),
            )
            avg_pair_quality = total_pair_quality / total_pair_count
            pair_quality_total = concurrent_breeds * avg_pair_quality
            for build_name, total_yield in build_yields.items():
                house_build_yields[build_name] += concurrent_breeds * (
                    total_yield / total_pair_count
                )
            total_base_quality += pair_quality_total

        # Apply a diversity bonus for builds present in the house to encourage solutions that produce a
        # variety of builds, which is generally desirable for long-term progression and player
        # enjoyment. The bonus is based on the square root of the total yield for each build to provide
        # diminishing returns and prevent over-prioritization of a single build.
        house_diversity_bonus = sum(math.sqrt(y) for y in house_build_yields.values())

        # Heavily penalize states that have zero yield for any target build to avoid extinction of a
        # particular build in the population.
        if self.target_builds is not None:
            for build in self.target_builds:
                if house_build_yields[build.name] < 1e-6:
                    house_diversity_bonus -= 1000.0

        # Penalize moving cats from their original rooms to account for player effort and to steer
        # towards solutions that are closer to the original state, but allow moves to be explored as
        # part of the search.
        cats_moved = sum(
            1
            for cid, r in state_dict.items()
            if r != self.original_state.get(cid) and r
        )
        total_base_quality -= cats_moved * MOVE_PENALTY

        return total_base_quality + house_diversity_bonus

    def __call__(self) -> tuple[OptimizationResult, float]:
        """Run simulated annealing worker on a single state."""

        T_MIN = 0.1
        COOLING_RATE = 0.95
        NEIGHBORS_PER_TEMP = 200

        current_state = self.initial_state.copy()
        current_score = self._evaluate_state(
            current_state,
        )

        positive_deltas: list[float] = []
        test_state = current_state.copy()
        test_score = current_score

        for _ in range(100):
            neighbor = _get_neighbor(test_state, self.room_configs)
            n_score = self._evaluate_state(
                neighbor,
            )
            if n_score > test_score:
                positive_deltas.append(n_score - test_score)
            test_state = neighbor
            test_score = n_score

        avg_delta = (
            sum(positive_deltas) / len(positive_deltas) if positive_deltas else 1.0
        )
        T = -avg_delta / math.log(0.8)

        best_state = current_state.copy()
        best_score = current_score

        iteration = 0
        while T > T_MIN:
            for _ in range(NEIGHBORS_PER_TEMP):
                neighbor = _get_neighbor(current_state, self.room_configs)
                neighbor_score = self._evaluate_state(
                    neighbor,
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

        return self._allocator.allocate(
            best_state, self.save_data, self._scorer
        ), best_score


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
) -> OptimizationResult:
    """Optimize using Parallel Simulated Annealing."""
    import concurrent.futures
    import multiprocessing

    cats = save_data.cats
    house_cats = [c for c in cats if c.status == CatStatus.IN_HOUSE]

    if not house_cats:
        return OptimizationResult(
            rooms=[],
        )

    sa_cats = [c for c in house_cats if not c.has_eternal_youth()]
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
        for i in range(num_workers)
    ]
    for state in initial_states:
        assert frozenset(state.keys()) == frozenset(c.db_key for c in sa_cats)

    best_overall_state = None
    best_overall_score = -float("inf")

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures: list[Future[tuple[OptimizationResult, float]]] = [
            executor.submit(
                _AnnealingWorker(
                    initial_state=state,
                    original_state=original_state,
                    room_configs=sa_room_configs,
                    save_data=save_data,
                    universals=universals,
                    target_builds=target_builds,
                    _allocator=RoomAllocator(
                        room_configs=sa_room_configs,
                        ey_assignments=ey_assignments,
                        universals=universals,
                        target_builds=target_builds,
                    ),
                    _scorer=CachingScorer(
                        save_data=save_data,
                        universals=universals,
                        target_builds=target_builds,
                    ),
                )
            )
            for state in initial_states
        ]

        for future in concurrent.futures.as_completed(futures):
            final_state, final_score = future.result()

            if final_score > best_overall_score:
                best_overall_score = final_score
                best_overall_state = final_state

    if best_overall_state is None:
        raise RuntimeError("SA optimization failed to produce any valid states.")

    return best_overall_state
