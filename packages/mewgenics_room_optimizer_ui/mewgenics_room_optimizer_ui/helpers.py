"""Helper functions for UI rendering."""

from dataclasses import dataclass

from mewgenics_parser import GameData
from mewgenics_parser.traits import Trait
from mewgenics_room_optimizer import ScoredPair, OptimizationResult
from mewgenics_room_optimizer.types import TraitRequirement

from mewgenics_room_optimizer_ui.state import AppState

from .colors import COLOR_DANGER, COLOR_SUCCESS

LOCATION_COL_WIDTH = 125


def get_favorable_trait_names(
    cat, trait_requirements: list[TraitRequirement], game_data: GameData
) -> list[str]:
    """Get list of favorable trait display names possessed by cat.

    Uses domain method trait.get_display_name() for proper names.
    """
    return [
        req.trait.get_display_name(game_data)
        for req in trait_requirements
        if req.trait.is_possessed_by(cat)
    ]


@dataclass
class PairSummaryData:
    """Common pair data for reuse in table and detail views."""

    names_display: str
    quality: float
    disorder_pct: float
    part_defect_pct: float
    combined_pct: float
    risk_color: tuple[int, int, int, int]
    mutual_lovers: bool
    libido_factor: float
    aggression_factor: float
    charisma_factor: float
    stat_variance: float
    trait_ev: float


def get_pair_summary_data(pair: ScoredPair, state: AppState) -> PairSummaryData:
    """Extract common pair data for reuse in table and detail views."""
    name_a = pair.cat_a.name or "Unnamed"
    name_b = pair.cat_b.name or "Unnamed"
    names_display = f"{name_a} + {name_b}"

    disorder = pair.factors.combined_disorder_chance * 100
    part_defect = pair.factors.combined_part_defect_chance * 100
    combined = pair.factors.combined_malady_chance * 100
    risk_color = COLOR_DANGER if combined > 15 else COLOR_SUCCESS

    mutual_lovers = pair.factors.mutual_lovers
    libido_factor = pair.factors.libido_factor
    aggression_factor = pair.factors.aggression_factor
    charisma_factor = pair.factors.charisma_factor
    stat_variance = pair.factors.stat_variance

    trait_ev = (
        sum(p.probability * p.trait.weight for p in pair.factors.trait_probabilities)
        * 5.0
    )

    return PairSummaryData(
        names_display=names_display,
        quality=pair.quality,
        disorder_pct=disorder,
        part_defect_pct=part_defect,
        combined_pct=combined,
        risk_color=risk_color,
        mutual_lovers=mutual_lovers,
        libido_factor=libido_factor,
        aggression_factor=aggression_factor,
        charisma_factor=charisma_factor,
        stat_variance=stat_variance,
        trait_ev=trait_ev,
    )


def plain_substring_match(query: str, choices: list[str]) -> list[str]:
    """Return items containing query as substring (case-insensitive)."""
    if not query:
        return choices
    return [c for c in choices if query.casefold() in c.casefold()]


def trait_substring_match(
    query: str, choices: list[Trait], game_data: GameData
) -> list[Trait]:
    """Return trait items containing query as substring (case-insensitive)."""
    if not query:
        return choices
    result = []
    for t in choices:
        display = f"{t.key} | {t.get_display_name(game_data)} | {t.get_description(game_data)}"
        if query.casefold() in display.casefold():
            result.append(t)
    return result


def get_assigned_room_key(
    cat_db_key: int, results: OptimizationResult | None
) -> str | None:
    """Get the room key a cat is assigned to in optimization results."""
    if not results:
        return None
    for room in results.rooms:
        if any(c.db_key == cat_db_key for c in room.cats):
            return room.room.key
    return None
