"""Helper functions for UI rendering."""

from dataclasses import dataclass

from mewgenics_parser import GameData
from mewgenics_parser.traits import Trait
from mewgenics_room_optimizer import ScoredPair, OptimizationResult
from typing import TypeVar

from mewgenics_room_optimizer_ui.state import AppState

from .colors import COLOR_DANGER, COLOR_SUCCESS

LOCATION_COL_WIDTH = 125

T = TypeVar("T")


@dataclass
class PairSummaryData:
    """Common pair data for reuse in table and detail views."""

    names_display: str
    quality: float
    expected_disorders: float
    expected_defects: float
    expected_stats_sum: float
    universal_ev: float
    build_yields: dict[str, float]
    combined_malady_pct: float
    risk_color: tuple[int, int, int, int]


@dataclass(slots=True)
class TraitCountInfo:
    """Trait with count and source info for Overview tabs."""

    trait: Trait
    count: int
    sources: list[str]


def get_pair_summary_data(pair: ScoredPair, state: AppState) -> PairSummaryData:
    """Extract common pair data for reuse in table and detail views."""
    name_a = pair.cat_a.name or "Unnamed"
    name_b = pair.cat_b.name or "Unnamed"
    names_display = f"{name_a} + {name_b}"

    expected_disorders = pair.factors.expected_disorders
    expected_defects = pair.factors.expected_defects
    expected_stats_sum = sum(pair.factors.expected_stats)
    universal_ev = pair.factors.universal_ev
    build_yields = pair.factors.build_yields

    combined_malady_pct = expected_disorders * 5.0 + expected_defects * 1.0
    risk_color = COLOR_DANGER if combined_malady_pct > 15 else COLOR_SUCCESS

    return PairSummaryData(
        names_display=names_display,
        quality=pair.quality,
        expected_disorders=expected_disorders,
        expected_defects=expected_defects,
        expected_stats_sum=expected_stats_sum,
        universal_ev=universal_ev,
        build_yields=build_yields,
        combined_malady_pct=combined_malady_pct,
        risk_color=risk_color,
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


def get_all_favorable_keys(state: AppState) -> set[str]:
    """Collect all trait keys from universals AND TargetBuild requirements."""
    keys: set[str] = set()
    for universal in state.universals:
        keys.add(universal.trait.key)
    for build in state.target_builds:
        for tw in build.requirements:
            keys.add(tw.trait.key)
    return keys


def tuple_replace(tup: tuple[T, ...], index: int, new_value: T) -> tuple[T, ...]:
    """Returns a new tuple with the value at the specified index replaced."""
    return tup[:index] + (new_value,) + tup[index + 1 :]
