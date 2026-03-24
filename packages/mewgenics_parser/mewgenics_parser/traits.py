"""Domain model for Mewgenics traits."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, override

from .cat import Cat, CatBodyPartCategory, CatBodySlot
from .gpak import GameData
from .trait_dictionary import normalize_ability_key


class TraitCategory(StrEnum):
    ACTIVE_ABILITY = "active_ability"
    PASSIVE_ABILITY = "passive_ability"
    BODY_PART = "body_part"
    DISORDER = "disorder"

    @property
    def display_name(self) -> str:
        return _DISPLAY_NAMES.get(self, self.value.title())


_DISPLAY_NAMES: dict[TraitCategory, str] = {
    TraitCategory.ACTIVE_ABILITY: "Active Ability",
    TraitCategory.PASSIVE_ABILITY: "Passive Ability",
    TraitCategory.BODY_PART: "Body Part",
    TraitCategory.DISORDER: "Disorder",
}


class Trait(Protocol):
    """Protocol defining the interface for all traits in Mewgenics."""

    @property
    def key(self) -> str:
        """Unique identifier for this trait."""
        ...

    @property
    def category(self) -> TraitCategory:
        """Category of this trait."""
        ...

    def is_negative(self) -> bool:
        """Whether this trait is considered negative (e.g., a disorder or defect)."""
        ...

    def get_display_name(self, game_data: GameData) -> str:
        """Get the human-readable display name for this trait."""
        ...

    def get_description(self, game_data: GameData) -> str:
        """Get the description for this trait."""
        ...

    def get_upgraded_description(self, game_data: GameData) -> str | None:
        """Get the description for the upgraded version of this trait, if it exists."""
        ...

    def is_possessed_by(self, cat: Cat) -> bool:
        """Check if the given cat possesses this trait."""
        ...


@dataclass(slots=True)
class ActiveAbilityTrait(Trait):
    """Trait representing an active ability."""

    _key: str

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return TraitCategory.ACTIVE_ABILITY

    @override
    def is_negative(self) -> bool:
        return False

    @override
    def get_display_name(self, game_data: GameData) -> str:
        nad = game_data.ability_text[self._key]
        return nad.name or self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        nad = game_data.ability_text[self._key]
        return nad.description

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        upgraded_key = self._key + "2"
        desc = game_data.ability_text[upgraded_key].description
        return desc if desc else None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(normalize_ability_key(a) == self._key for a in cat.active_abilities)


@dataclass(slots=True)
class PassiveAbilityTrait(Trait):
    """Trait representing a passive ability."""

    _key: str

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return TraitCategory.PASSIVE_ABILITY

    @override
    def is_negative(self) -> bool:
        return False

    @override
    def get_display_name(self, game_data: GameData) -> str:
        nad = game_data.ability_text[self._key]
        return nad.name or self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        nad = game_data.ability_text[self._key]
        return nad.description

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        upgraded_key = self._key + "2"
        desc = game_data.ability_text[upgraded_key].description
        return desc if desc else None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(
            normalize_ability_key(p) == self._key for p in cat.inheritable_passives
        )


@dataclass(slots=True)
class BodyPartTrait(Trait):
    """Trait representing a body part."""

    _key: str
    _bp_category: CatBodyPartCategory = field(init=False, repr=False)
    _part_id: int = field(init=False, repr=False)

    def __post_init__(self):
        import re

        match = re.fullmatch(r"(\D+)(\d+)", self._key)
        if not match:
            raise ValueError(f"Invalid body part key format: {self._key}")
        bp_category, part_id = match.groups()
        part_id = int(part_id)
        if bp_category.endswith("-"):
            bp_category = bp_category[:-1]
            part_id = -part_id
        self._bp_category = CatBodyPartCategory(bp_category.lower())
        self._part_id = part_id

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return TraitCategory.BODY_PART

    @override
    def is_negative(self) -> bool:
        return self._part_id == -2 or (self._part_id >= 700 and self._part_id <= 710)

    def is_mutation(self) -> bool:
        return self._part_id >= 300

    @override
    def get_display_name(self, game_data: GameData) -> str:
        name_desc = game_data.body_part_text[self._bp_category][self._part_id]
        return name_desc.name or self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        name_desc = game_data.body_part_text[self._bp_category][self._part_id]
        return name_desc.description

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        return None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        """Check if the cat has this body part trait in ANY slot of the category."""
        return any(
            cat.body_parts.get(slot) == self._part_id
            for slot in get_slots_for_category(self._bp_category)
        )

    @property
    def body_part_category(self) -> CatBodyPartCategory:
        """Return the body part category (e.g., ears, tail) for this trait."""
        return self._bp_category

    @property
    def part_id(self) -> int:
        """Return the part ID number."""
        return self._part_id


def get_slots_for_category(category: CatBodyPartCategory) -> list[CatBodySlot]:
    """Get all slots belonging to a category (e.g., [LEFT_EAR, RIGHT_EAR] for EARS)."""
    return [slot for slot in CatBodySlot if slot.category == category]


@dataclass(slots=True)
class DisorderTrait(Trait):
    """Trait representing a disorder."""

    _key: str

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return TraitCategory.DISORDER

    @override
    def is_negative(self) -> bool:
        return True

    @override
    def get_display_name(self, game_data: GameData) -> str:
        name_desc = game_data.ability_text[self._key]
        return name_desc.name or self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        name_desc = game_data.ability_text[self._key]
        return name_desc.description

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        return None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(normalize_ability_key(d) == self._key for d in cat.disorders)


def extract_traits_from_cat(cat: Cat) -> list[Trait]:
    """Extract all traits from a Cat DTO as domain objects."""
    traits: list[Trait] = []

    for ability in cat.active_abilities:
        traits.append(create_trait(TraitCategory.ACTIVE_ABILITY, ability))

    for passive in cat.passive_abilities:
        traits.append(create_trait(TraitCategory.PASSIVE_ABILITY, passive))

    for slot, part_id in cat.body_parts.items():
        key = f"{slot.category.name.title()}{part_id}"
        traits.append(create_trait(TraitCategory.BODY_PART, key))

    for disorder in cat.disorders:
        traits.append(create_trait(TraitCategory.DISORDER, disorder))

    return traits


def create_trait(category: TraitCategory, key: str) -> Trait:
    """Factory function to create a Trait from category and key."""

    match category:
        case TraitCategory.ACTIVE_ABILITY:
            return ActiveAbilityTrait(_key=normalize_ability_key(key))
        case TraitCategory.PASSIVE_ABILITY:
            return PassiveAbilityTrait(_key=normalize_ability_key(key))
        case TraitCategory.BODY_PART:
            return BodyPartTrait(_key=key)
        case TraitCategory.DISORDER:
            return DisorderTrait(_key=key)
        case _:
            raise ValueError(f"Unknown trait category: {category}")
