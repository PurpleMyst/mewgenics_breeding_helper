"""Room optimization logic for Mewgenics breeding with ENS architecture."""

from concurrent.futures import Future

import math
import random
from collections import defaultdict
from dataclasses import replace, dataclass, field

from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatGender, CatStatus
from mewgenics_scorer import (
    TargetBuild,
    TraitWeight,
    calculate_pair_factors,
    calculate_pair_quality,
    can_breed,
)

from .types import (
    OptimizationResult,
    RoomAssignment,
    RoomConfig,
    RoomType,
    ScoredPair,
)

MOVE_PENALTY = 0.5


def _generate_pairs(
    cats: list[Cat],
) -> list[tuple[Cat, Cat]]:
    """Generate all valid pairs of cats which could potentially produce offspring."""
    males = [c for c in cats if c.gender == CatGender.MALE]
    females = [c for c in cats if c.gender == CatGender.FEMALE]
    dittos = [c for c in cats if c.gender == CatGender.DITTO]

    pairs = []
    pairs.extend((a, b) for a in males for b in females)
    pairs.extend((a, b) for a in males for b in dittos)
    pairs.extend((a, b) for a in females for b in dittos)
    pairs.extend((a, b) for i, a in enumerate(dittos) for b in dittos[i + 1 :])

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


@dataclass(slots=True)
class _AnnealingWorker:
    initial_state: dict[int, str]
    original_state: dict[int, str]
    room_configs: list[RoomConfig]
    save_data: SaveData
    universals: list[TraitWeight] | None
    target_builds: list[TargetBuild] | None
    ey_assignments: dict[str, list[Cat]]

    _memo: dict[tuple[int, int, float], ScoredPair | None] = field(
        default_factory=dict, init=False, repr=False
    )

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
            pairs = _generate_pairs(cats_in_room)
            pairs = _filter_lover_exclusivity(pairs, cats_in_room)
            pairs = _filter_hater_conflicts(pairs, cats_in_room)

            # Score every possible pair and aggregate total quality and build yields.
            # Also keep track of which cats are actually contributing to breeding.
            total_pair_quality = 0.0
            useful_pair_count = 0
            build_yields = defaultdict(lambda: 0.0)
            useful_cats = set()
            for a, b in pairs:
                scored = self._score_pair(a, b, room.stimulation)
                if scored is not None:
                    total_pair_quality += scored.quality
                    useful_pair_count += 1
                    for build_name, yield_value in scored.factors.build_yields.items():
                        build_yields[build_name] += yield_value
                    useful_cats.add(a.db_key)
                    useful_cats.add(b.db_key)
            if not useful_pair_count:
                continue

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
            avg_pair_quality = total_pair_quality / useful_pair_count
            pair_quality_total = concurrent_breeds * avg_pair_quality
            for build_name, total_yield in build_yields.items():
                house_build_yields[build_name] += concurrent_breeds * (
                    total_yield / useful_pair_count
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

        return self._build_results(best_state), best_score

    def _score_pair_internal(
        self,
        cat_a: Cat,
        cat_b: Cat,
        stimulation: float,
    ) -> ScoredPair | None:
        """Score a pair, returning None if they can't be paired."""
        if not can_breed(cat_a, cat_b):
            return None

        try:
            factors = calculate_pair_factors(
                self.save_data,
                cat_a,
                cat_b,
                stimulation=stimulation,
                universals=self.universals,
                target_builds=self.target_builds,
            )
        except KeyError:
            return None

        return ScoredPair(
            cat_a=cat_a,
            cat_b=cat_b,
            factors=factors,
            quality=calculate_pair_quality(factors),
        )

    def _score_pair(
        self,
        cat_a: Cat,
        cat_b: Cat,
        stimulation: float,
    ) -> ScoredPair | None:
        """Score a pair with memoization."""
        key = (
            min(cat_a.db_key, cat_b.db_key),
            max(cat_a.db_key, cat_b.db_key),
            stimulation,
        )
        if key in self._memo:
            return self._memo[key]
        scored = self._score_pair_internal(cat_a, cat_b, stimulation)
        self._memo[key] = scored
        return scored

    def _build_results(
        self,
        state_dict: dict[int, str],
    ) -> OptimizationResult:
        """Build OptimizationResult from a state dictionary."""
        rooms_content: dict[str, list[Cat]] = {r.key: [] for r in self.room_configs}
        assigned_cats: set[int] = set()

        for cat_id, room_key in state_dict.items():
            if room_key in rooms_content:
                rooms_content[room_key].append(self.save_data.cats_by_id[cat_id])
                assigned_cats.add(cat_id)

        breeding_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.BREEDING
        ]
        room_pairs: dict[str, list[ScoredPair]] = {r.key: [] for r in self.room_configs}

        for room in breeding_rooms:
            cats_in_room = rooms_content[room.key]
            if len(cats_in_room) < 2:
                continue

            pairs = _generate_pairs(cats_in_room)
            for a, b in pairs:
                scored = self._score_pair(a, b, room.stimulation)
                if scored:
                    room_pairs[room.key].append(scored)

        sa_cats = [
            c
            for c in self.save_data.cats
            if c.status == CatStatus.IN_HOUSE and not c.has_eternal_youth()
        ]
        unassigned = [c for c in sa_cats if c.db_key not in assigned_cats]
        general_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.GENERAL
        ]
        fighting_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.FIGHTING
        ]
        health_rooms = [r for r in self.room_configs if r.room_type == RoomType.HEALTH]
        mutation_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.MUTATION
        ]

        def _cat_ens_value(cat: Cat) -> float:
            val = sum(cat.base_stats)
            if self.universals:
                val += sum(
                    u.weight_ens
                    for u in self.universals
                    if u.trait.is_possessed_by(cat)
                )
            if self.target_builds:
                for b in self.target_builds:
                    val += sum(
                        req.weight_ens
                        for req in b.requirements
                        if req.trait.is_possessed_by(cat)
                    )
            return val

        # Sort unassigned cats by their ENS value to try to fit higher-value cats first.
        # TODO: Improve this aspect, namely:
        # * Raw ENS sum tends to reduce diversity;
        # * Fighting rooms should prioritize high total stat sum cats, since they're not breeding and
        # just want strong stats.
        unassigned.sort(key=_cat_ens_value, reverse=True)
        for cat in unassigned:
            has_disorders = bool(cat.disorders)
            has_defects = cat.has_birth_defects()

            if has_disorders and has_defects:
                rooms_to_try = (
                    mutation_rooms + health_rooms + general_rooms + fighting_rooms
                )
            elif has_disorders:
                rooms_to_try = health_rooms + general_rooms + fighting_rooms
            elif has_defects:
                rooms_to_try = mutation_rooms + general_rooms + fighting_rooms
            else:
                cat_value = _cat_ens_value(cat)
                rooms_to_try = (
                    (general_rooms + fighting_rooms)
                    if cat_value > 0
                    else (fighting_rooms + general_rooms)
                )

            for room in rooms_to_try:
                if _can_fit_single(room, len(rooms_content[room.key])):
                    rooms_content[room.key].append(cat)
                    assigned_cats.add(cat.db_key)
                    break

        excluded = [c for c in sa_cats if c.db_key not in assigned_cats]

        room_results: list[RoomAssignment] = []
        if excluded:
            room_results.append(
                RoomAssignment(
                    room=RoomConfig(
                        key="Unassigned (donate perhaps)",
                        room_type=RoomType.NONE,
                        max_cats=None,
                        stimulation=0.0,
                    ),
                    cats=excluded,
                    pairs=[],
                    eternal_youth_cats=[],
                )
            )

        for config in self.room_configs:
            cats_in_room = rooms_content[config.key]
            pairs_in_room = room_pairs[config.key]
            ey_cats = self.ey_assignments.get(config.key, [])

            if cats_in_room or pairs_in_room or ey_cats:
                room_results.append(
                    RoomAssignment(
                        room=config,
                        cats=cats_in_room,
                        pairs=pairs_in_room,
                        eternal_youth_cats=ey_cats,
                    )
                )

        return OptimizationResult(
            rooms=room_results,
        )


def _can_fit_single(
    room: RoomConfig,
    current_count: int,
) -> bool:
    """Check if a single cat can fit in a room. EY cats are invisible to capacity."""
    if room.max_cats is None:
        return True
    return (current_count + 1) <= room.max_cats


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
            state[cat.db_key] = ""

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

    # Statically assign Eternal Youth cats to the breeding room with the highest base stimulation to
    # boost it further.
    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    ey_assignments: dict[str, list[Cat]] = {r.key: [] for r in breeding_rooms}
    if breeding_rooms and ey_cats:
        best_room = max(breeding_rooms, key=lambda r: r.stimulation)
        ey_assignments[best_room.key] = ey_cats

    # Adjust breeding room stim based on EY assignments since they boost the room's effective
    # stimulation.
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
                    ey_assignments=ey_assignments,
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
