"""Room optimization logic for Mewgenics breeding."""

from mewgenics_parser import Cat
from mewgenics_scorer import (
    calculate_pair_factors,
    can_breed,
    is_hater_conflict,
    is_lover_conflict,
)

from .types import (
    RoomType,
    RoomConfig,
    RoomAssignment,
    ScoredPair,
    OptimizationParams,
    OptimizationResult,
    OptimizationStats,
)


def _has_eternalyouth(cat: Cat) -> bool:
    """Check if cat has EternalYouth passive."""
    return any(p.lower() == "eternalyouth" for p in (cat.passive_abilities or []))


def _can_pair_gay(cat_a: Cat, cat_b: Cat, gay_flags: dict[int, bool]) -> bool:
    """Check if gay cats can breed based on gender restrictions."""
    is_a_gay = gay_flags.get(cat_a.db_key, False)
    is_b_gay = gay_flags.get(cat_b.db_key, False)

    if not is_a_gay and not is_b_gay:
        return True

    if is_a_gay and cat_b.gender.lower() != "female":
        return False
    if is_b_gay and cat_a.gender.lower() != "female":
        return False

    return True


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


def _score_pair(
    cat_a: Cat,
    cat_b: Cat,
    ancestor_contribs: dict[int, dict[Cat, float]],
    params: OptimizationParams,
) -> ScoredPair | None:
    """Score a pair, returning None if they can't be paired."""
    if not can_breed(cat_a, cat_b):
        return None

    if is_hater_conflict(cat_a, cat_b):
        return None

    if is_lover_conflict(cat_a, cat_b, params.avoid_lovers):
        return None

    if not _can_pair_gay(cat_a, cat_b, params.gay_flags):
        return None

    factors = calculate_pair_factors(
        cat_a,
        cat_b,
        ancestor_contribs,
        stimulation=params.stimulation,
        avoid_lovers=params.avoid_lovers,
        planner_traits=params.planner_traits,
    )

    if factors.risk_percent > params.max_risk:
        return None

    quality = _calculate_quality(factors, params)

    return ScoredPair(
        cat_a=cat_a,
        cat_b=cat_b,
        factors=factors,
        quality=quality,
    )


def _calculate_quality(factors, params: OptimizationParams) -> float:
    """Calculate quality score from pair factors."""
    avg_stats = factors.total_expected_stats / 7.0

    risk_factor = 1.0 - factors.risk_percent / 200.0

    variance_penalty = 0.0
    if params.minimize_variance:
        for diff in [
            abs(a - b)
            for a, b in zip(factors.expected_stats[:3], factors.expected_stats[3:])
        ]:
            if diff > 2:
                variance_penalty += diff * 2.0

    personality_bonus = 0.0
    if params.prefer_low_aggression:
        personality_bonus += factors.aggression_factor * 2.5
    if params.prefer_high_libido:
        personality_bonus += factors.libido_factor * 2.5

    trait_bonus = sum(t.weight for t in factors.trait_matches) * 5.0

    quality = (
        (avg_stats + risk_factor * 20)
        - variance_penalty
        + personality_bonus
        + trait_bonus
    )

    return quality


def _has_planner_trait(cat: Cat, params: OptimizationParams) -> bool:
    """Check if cat has any planner-selected traits."""
    for trait in params.planner_traits:
        for mutation in cat.mutations or []:
            if mutation.lower() == trait.key.lower():
                return True
        for passive in cat.passive_abilities or []:
            if passive.lower() == trait.key.lower():
                return True
        for ability in cat.abilities or []:
            if ability.lower() == trait.key.lower():
                return True
    return False


def _can_fit_pair(
    pair: ScoredPair,
    room: RoomConfig,
    assigned_cats: set[int],
    pair_cats_in_room: set[int],
) -> bool:
    """Check if a pair can fit in a room."""
    if room.max_cats is not None:
        if len(pair_cats_in_room) + 2 > room.max_cats:
            return False

    if pair.cat_a.db_key in assigned_cats or pair.cat_b.db_key in assigned_cats:
        return False

    return True


def _can_fit_single(
    cat: Cat,
    room: RoomConfig,
    assigned_cats: set[int],
    current_count: int,
) -> bool:
    """Check if a single cat can fit in a room."""
    if room.max_cats is not None:
        if current_count + 1 > room.max_cats:
            return False

    if cat.db_key in assigned_cats:
        return False

    return True


def optimize(
    cats: list[Cat],
    room_configs: list[RoomConfig],
    params: OptimizationParams,
    ancestor_contribs: dict[int, dict[Cat, float]],
) -> OptimizationResult:
    """Main optimization entry point."""

    filtered_cats = _filter_cats(cats, params.min_stats)

    eternal_youth_cats = [c for c in filtered_cats if _has_eternalyouth(c)]
    breeding_cats = [c for c in filtered_cats if not _has_eternalyouth(c)]

    pairs = _generate_pairs(breeding_cats)

    scored_pairs: list[ScoredPair] = []
    for cat_a, cat_b in pairs:
        scored = _score_pair(cat_a, cat_b, ancestor_contribs, params)
        if scored is not None:
            scored_pairs.append(scored)

    scored_pairs.sort(key=lambda p: p.quality, reverse=True)

    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    general_rooms = [r for r in room_configs if r.room_type == RoomType.GENERAL]
    fighting_rooms = [r for r in room_configs if r.room_type == RoomType.FIGHTING]

    room_assignments: dict[str, list[Cat]] = {r.key: [] for r in room_configs}
    room_pairs: dict[str, list[ScoredPair]] = {r.key: [] for r in room_configs}
    room_eternal_youth: dict[str, list[Cat]] = {r.key: [] for r in room_configs}
    assigned_cats: set[int] = set()

    for pair in scored_pairs:
        if pair.cat_a.db_key in assigned_cats or pair.cat_b.db_key in assigned_cats:
            continue

        for room in breeding_rooms:
            current_cats = set(c.db_key for c in room_assignments[room.key])
            if _can_fit_pair(pair, room, assigned_cats, current_cats):
                room_assignments[room.key].extend([pair.cat_a, pair.cat_b])
                room_pairs[room.key].append(pair)
                assigned_cats.add(pair.cat_a.db_key)
                assigned_cats.add(pair.cat_b.db_key)
                break

    unassigned = [c for c in filtered_cats if c.db_key not in assigned_cats]

    for ey_cat in eternal_youth_cats:
        for room in breeding_rooms + general_rooms:
            current_count = len(room_assignments[room.key]) + len(
                room_eternal_youth[room.key]
            )
            if _can_fit_single(ey_cat, room, assigned_cats, current_count):
                room_eternal_youth[room.key].append(ey_cat)
                assigned_cats.add(ey_cat.db_key)
                break

    unassigned = [c for c in filtered_cats if c.db_key not in assigned_cats]

    trait_cats = [c for c in unassigned if _has_planner_trait(c, params)]
    non_trait_cats = [c for c in unassigned if c not in trait_cats]

    for cat in trait_cats:
        for room in general_rooms:
            current_count = len(room_assignments[room.key])
            if _can_fit_single(cat, room, assigned_cats, current_count):
                room_assignments[room.key].append(cat)
                assigned_cats.add(cat.db_key)
                break

    trait_assigned = [c for c in trait_cats if c.db_key in assigned_cats]
    remaining = [c for c in unassigned if c.db_key not in assigned_cats]

    for cat in remaining + non_trait_cats:
        for room in fighting_rooms + general_rooms:
            current_count = len(room_assignments[room.key])
            if _can_fit_single(cat, room, assigned_cats, current_count):
                room_assignments[room.key].append(cat)
                assigned_cats.add(cat.db_key)
                break

    excluded = [c for c in filtered_cats if c.db_key not in assigned_cats]

    room_results: list[RoomAssignment] = []
    breeding_rooms_used = 0
    general_rooms_used = 0
    total_pair_quality = 0.0
    total_risk = 0.0
    total_pairs = 0

    for config in room_configs:
        cats_in_room = room_assignments[config.key]
        pairs_in_room = room_pairs[config.key]
        ey_cats_in_room = room_eternal_youth[config.key]

        if cats_in_room or pairs_in_room or ey_cats_in_room:
            room_results.append(
                RoomAssignment(
                    room=config,
                    cats=cats_in_room,
                    pairs=pairs_in_room,
                    eternal_youth_cats=ey_cats_in_room,
                )
            )

            if config.room_type == RoomType.BREEDING:
                breeding_rooms_used += 1
            elif config.room_type == RoomType.GENERAL:
                general_rooms_used += 1

            total_pairs += len(pairs_in_room)
            for p in pairs_in_room:
                total_pair_quality += p.quality
                total_risk += p.factors.risk_percent

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
