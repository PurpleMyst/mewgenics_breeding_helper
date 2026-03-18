"""Domain model for Mewgenics traits."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, override

from .cat import Cat
from .gpak import GameData
from .trait_dictionary import normalize_trait_name


class TraitCategory(StrEnum):
    ACTIVE_ABILITY = "active_ability"
    PASSIVE_ABILITY = "passive_ability"
    BODY_PART = "body_part"
    DISORDER = "disorder"
    MUTATION = "mutation"


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
    _category: TraitCategory = field(default=TraitCategory.ACTIVE_ABILITY)

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return self._category

    @override
    def get_display_name(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.name if nad else self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.description if nad else ""

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        upgraded_key = self._key + "2"
        nad = game_data.ability_text.get(upgraded_key)
        return nad.description if nad else None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(
            normalize_trait_name(a) == self._key for a in (cat.active_abilities or [])
        )


@dataclass(slots=True)
class PassiveAbilityTrait(Trait):
    """Trait representing a passive ability."""

    _key: str
    _category: TraitCategory = field(default=TraitCategory.PASSIVE_ABILITY)

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return self._category

    @override
    def get_display_name(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.name if nad else self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.description if nad else ""

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        upgraded_key = self._key + "2"
        nad = game_data.ability_text.get(upgraded_key)
        return nad.description if nad else None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(
            normalize_trait_name(p) == self._key for p in cat.inheritable_passives
        )


@dataclass(slots=True)
class BodyPartTrait(Trait):
    """Trait representing a body part mutation."""

    _key: str
    _category: TraitCategory = field(default=TraitCategory.BODY_PART)

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return self._category

    @override
    def get_display_name(self, game_data: GameData) -> str:
        import re

        match = re.fullmatch(r"(\D+)(\d+)", self._key)
        if not match:
            return self._key
        category, part_id = match.groups()
        category_lower = category.lower()
        part_id_int = int(part_id)
        nad = game_data.body_part_text.get(category_lower, {}).get(part_id_int)
        return nad.name if nad else self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        import re

        match = re.fullmatch(r"(\D+)(\d+)", self._key)
        if not match:
            return ""
        category, part_id = match.groups()
        category_lower = category.lower()
        part_id_int = int(part_id)
        nad = game_data.body_part_text.get(category_lower, {}).get(part_id_int)
        return nad.description if nad else ""

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        return None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return self._key in cat.body_part_keys


@dataclass(slots=True)
class DisorderTrait(Trait):
    """Trait representing a disorder."""

    _key: str
    _category: TraitCategory = field(default=TraitCategory.DISORDER)

    @property
    @override
    def key(self) -> str:
        return self._key

    @property
    @override
    def category(self) -> TraitCategory:
        return self._category

    @override
    def get_display_name(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.name if nad else self._key

    @override
    def get_description(self, game_data: GameData) -> str:
        nad = game_data.ability_text.get(self._key)
        return nad.description if nad else ""

    @override
    def get_upgraded_description(self, game_data: GameData) -> str | None:
        return None

    @override
    def is_possessed_by(self, cat: Cat) -> bool:
        return any(normalize_trait_name(d) == self._key for d in (cat.disorders or []))


def extract_traits_from_cat(cat: Cat) -> list[Trait]:
    """Extract all traits from a Cat DTO as domain objects."""
    traits: list[Trait] = []

    for ability in cat.active_abilities or []:
        normalized = normalize_trait_name(ability)
        if normalized and not any(
            t.key == normalized and t.category == "ability" for t in traits
        ):
            traits.append(ActiveAbilityTrait(_key=normalized))

    for passive in cat.passive_abilities or []:
        normalized = normalize_trait_name(passive)
        if normalized and not any(
            t.key == normalized and t.category == "passive" for t in traits
        ):
            traits.append(PassiveAbilityTrait(_key=normalized))

    for body_part_key in cat.body_part_keys:
        if not any(t.key == body_part_key for t in traits):
            traits.append(BodyPartTrait(_key=body_part_key))

    for disorder in cat.disorders or []:
        normalized = normalize_trait_name(disorder)
        if normalized and not any(
            t.key == normalized and t.category == TraitCategory.DISORDER for t in traits
        ):
            traits.append(DisorderTrait(_key=normalized))

    return traits


def create_trait(category: TraitCategory, key: str) -> Trait:
    """Factory function to create a Trait from category and key."""
    normalized_key = normalize_trait_name(key)

    match category:
        case TraitCategory.ACTIVE_ABILITY:
            return ActiveAbilityTrait(_key=normalized_key)
        case TraitCategory.PASSIVE_ABILITY:
            return PassiveAbilityTrait(_key=normalized_key)
        case TraitCategory.BODY_PART:
            return BodyPartTrait(_key=key)
        case TraitCategory.MUTATION:
            return BodyPartTrait(_key=key)
        case TraitCategory.DISORDER:
            return DisorderTrait(_key=normalized_key)
        case _:
            raise ValueError(f"Unknown trait category: {category}")
