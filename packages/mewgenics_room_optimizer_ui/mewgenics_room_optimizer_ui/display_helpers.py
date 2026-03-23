"""Helpers for converting Cat data to UI display models."""

from mewgenics_parser.cat import Cat
from mewgenics_parser.gpak import GameData

from .display_models import (
    AbilityDisplay,
    BodyPartDisplay,
    create_ability_display,
    create_body_part_display,
)


def get_cat_abilities(cat: Cat, game_data: GameData) -> list[AbilityDisplay]:
    """Get UI display models for all active abilities on a cat."""
    return [create_ability_display(key, game_data) for key in cat.active_abilities]


def get_cat_passives(cat: Cat, game_data: GameData) -> list[AbilityDisplay]:
    """Get UI display models for all passive abilities on a cat."""
    return [create_ability_display(key, game_data) for key in cat.passive_abilities]


def get_cat_body_parts(cat: Cat, game_data: GameData) -> list[BodyPartDisplay]:
    """Get UI display models for all body parts on a cat, grouped by symmetric slots."""
    return create_body_part_display(cat.body_parts, game_data)
