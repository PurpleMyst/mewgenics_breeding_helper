"""UI display models - separate from domain trait models used for inheritance."""

from collections import defaultdict
from dataclasses import dataclass

from mewgenics_parser.cat import CatBodyPartCategory, CatBodySlot
from mewgenics_parser.gpak import GameData
from mewgenics_parser.trait_dictionary import normalize_ability_key


@dataclass(slots=True)
class AbilityDisplay:
    """UI-friendly ability."""

    base_key: str
    name: str
    description: str


@dataclass(slots=True)
class BodyPartDisplay:
    """UI-friendly body part with slot and grouping info."""

    part_id: int
    category: CatBodyPartCategory
    slots: list[CatBodySlot]
    slot_labels: list[str]
    display_name: str
    description: str
    is_mutation: bool
    is_negative: bool

    @property
    def key(self) -> str:
        """Key for matching against trait requirements."""
        return f"{self.category.name.title()}{self.part_id}"


def _format_slot_label(slot: CatBodySlot) -> str:
    """Format slot enum name to readable label."""
    return slot.name.replace("_", " ").title()


def create_ability_display(raw_key: str, game_data: GameData) -> AbilityDisplay:
    """Create AbilityDisplay with resolved upgrade description."""
    base_key = normalize_ability_key(raw_key)
    is_upgraded = raw_key != base_key and raw_key.endswith("2")

    name = game_data.ability_text[base_key].name or base_key
    if is_upgraded:
        name += "+"

    if is_upgraded:
        description = game_data.ability_text[base_key + "2"].description
        if not description:
            description = game_data.ability_text[base_key].description
    else:
        description = game_data.ability_text[base_key].description

    return AbilityDisplay(base_key=base_key, name=name, description=description)


def create_body_part_display(
    slots_to_parts: dict[CatBodySlot, int], game_data: GameData
) -> list[BodyPartDisplay]:
    """Create BodyPartDisplay list, grouped by symmetric slots.

    Parts with the same (category, part_id) are grouped together.
    """
    grouped: defaultdict[tuple[CatBodyPartCategory, int], list[CatBodySlot]] = (
        defaultdict(list)
    )
    for slot, part_id in slots_to_parts.items():
        grouped[(slot.category, part_id)].append(slot)

    displays = []
    for (category, part_id), slots in grouped.items():
        slots.sort(key=lambda s: s.name)
        slot_labels = [_format_slot_label(s) for s in slots]

        name_desc = game_data.body_part_text[category][part_id]
        display_name = name_desc.name or f"{category.name.title()}"
        description = name_desc.description or ""

        is_mutation = part_id >= 300
        is_negative = part_id == -2 or (700 <= part_id <= 710)

        displays.append(
            BodyPartDisplay(
                part_id=part_id,
                category=category,
                slots=slots,
                slot_labels=slot_labels,
                display_name=display_name,
                description=description,
                is_mutation=is_mutation,
                is_negative=is_negative,
            )
        )

    return displays
