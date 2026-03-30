"""Greedy room allocation for cats not placed by the SA optimizer."""

from __future__ import annotations

from dataclasses import dataclass

from mewgenics_breeding.pairs import generate_pairs
from mewgenics_parser import Cat, SaveData
from mewgenics_parser.cat import CatStatus
from mewgenics_scorer import TargetBuild, TraitWeight, evaluate_cat_ens

from .types import (
    OptimizationResult,
    RoomAssignment,
    RoomConfig,
    RoomType,
    ScoredPair,
)
from .scorer import CachingScorer


@dataclass(slots=True)
class RoomAllocator:
    """Handles non-SA room assignment for cats not placed by the optimizer."""

    room_configs: list[RoomConfig]
    ey_assignments: dict[str, list[Cat]]
    universals: list[TraitWeight] | None
    target_builds: list[TargetBuild] | None

    def allocate(
        self,
        state_dict: dict[int, str],
        save_data: SaveData,
        scorer: CachingScorer,
    ) -> OptimizationResult:
        """Build OptimizationResult from SA state, performing greedy allocation for unassigned cats."""
        rooms_content: dict[str, list[Cat]] = {r.key: [] for r in self.room_configs}
        assigned_cats: set[int] = set()

        for cat_id, room_key in state_dict.items():
            if room_key in rooms_content:
                rooms_content[room_key].append(save_data.cats_by_id[cat_id])
                assigned_cats.add(cat_id)

        breeding_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.BREEDING
        ]
        room_pairs: dict[str, list[ScoredPair]] = {r.key: [] for r in self.room_configs}

        for room in breeding_rooms:
            cats_in_room = rooms_content[room.key]
            if len(cats_in_room) < 2:
                continue

            pairs = generate_pairs(cats_in_room)
            for a, b in pairs:
                scored = scorer.score_pair(a, b, room.stimulation)
                if scored:
                    room_pairs[room.key].append(scored)

        sa_cats = [
            c
            for c in save_data.cats
            if c.status == CatStatus.IN_HOUSE and c.can_breed()
        ]
        kittens = [
            c
            for c in save_data.cats
            if c.status == CatStatus.IN_HOUSE and c.is_kitten()
        ]
        unassigned = [c for c in sa_cats if c.db_key not in assigned_cats]

        nursery_rooms = [
            r for r in self.room_configs if r.room_type == RoomType.NURSERY
        ]
        nursery_assignments: dict[str, list[Cat]] = {r.key: [] for r in nursery_rooms}

        kittens.sort(
            key=lambda c: evaluate_cat_ens(c, self.universals, self.target_builds),
            reverse=True,
        )
        for kitten in kittens:
            placed = False
            for room in nursery_rooms:
                if RoomAllocator.can_fit_single(
                    room, len(nursery_assignments[room.key])
                ):
                    nursery_assignments[room.key].append(kitten)
                    placed = True
                    break
            if not placed:
                unassigned.append(kitten)
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

        unassigned.sort(
            key=lambda c: evaluate_cat_ens(c, self.universals, self.target_builds),
            reverse=True,
        )
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
                cat_value = evaluate_cat_ens(cat, self.universals, self.target_builds)
                rooms_to_try = (
                    (general_rooms + fighting_rooms)
                    if cat_value > 0
                    else (fighting_rooms + general_rooms)
                )

            for room in rooms_to_try:
                if RoomAllocator.can_fit_single(room, len(rooms_content[room.key])):
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
            nursery_cats = nursery_assignments.get(config.key, [])

            if cats_in_room or pairs_in_room or ey_cats or nursery_cats:
                room_results.append(
                    RoomAssignment(
                        room=config,
                        cats=cats_in_room,
                        pairs=pairs_in_room,
                        eternal_youth_cats=ey_cats,
                        nursery_cats=nursery_cats,
                    )
                )

        return OptimizationResult(
            rooms=room_results,
        )

    @staticmethod
    def can_fit_single(
        room: RoomConfig,
        current_count: int,
    ) -> bool:
        """Check if a single cat can fit in a room. EY cats are invisible to capacity."""
        if room.max_cats is None:
            return True
        return (current_count + 1) <= room.max_cats


def compute_ey_assignments(
    ey_cats: list[Cat],
    room_configs: list[RoomConfig],
) -> dict[str, list[Cat]]:
    """Assign Eternal Youth cats to the breeding room with the highest stimulation."""
    breeding_rooms = [r for r in room_configs if r.room_type == RoomType.BREEDING]
    ey_assignments: dict[str, list[Cat]] = {r.key: [] for r in breeding_rooms}
    if breeding_rooms and ey_cats:
        best_room = max(breeding_rooms, key=lambda r: r.stimulation)
        ey_assignments[best_room.key] = ey_cats
    return ey_assignments
