import dearpygui.dearpygui as dpg
from mewgenics_parser.cat import CatBodyPartCategory
from mewgenics_room_optimizer.types import ScoredPair

from ...colors import (
    COLOR_DANGER,
    COLOR_MUTED,
    COLOR_SUCCESS,
)
from ...helpers import PairSummaryData, get_all_favorable_keys, get_pair_summary_data
from ...state import AppState
from .cat import on_cat_selected

STAT_NAMES = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]


def show_pair_detail_window(pair: ScoredPair, state: AppState) -> None:
    """Show pair details in the inspector panel with ENS factors."""
    container = "inspector_pair_container"
    if not dpg.does_item_exist(container):
        return

    dpg.hide_item("inspector_pair_placeholder")
    dpg.show_item(container)

    dpg.delete_item(container, children_only=True)

    summary = get_pair_summary_data(pair, state)
    favorable_keys = get_all_favorable_keys(state)

    with dpg.group(parent=container):
        name_a = pair.cat_a.name or "Unnamed"
        name_b = pair.cat_b.name or "Unnamed"

        with dpg.group(horizontal=True):
            dpg.add_button(
                label=name_a,
                callback=on_cat_selected,
                user_data=(pair.cat_a, state),
            )
            dpg.add_text("+")
            dpg.add_button(
                label=name_b,
                callback=on_cat_selected,
                user_data=(pair.cat_b, state),
            )

        dpg.add_text(
            f"Quality: {summary.quality:.1f} | Stats: {summary.expected_stats_sum:.1f} | COI: {summary.coi * 100:.1f}%",
            color=summary.risk_color,
        )

        dpg.add_separator()
        dpg.add_text("Expected Stats:")

        with dpg.table(
            tag="pair_stats_table",
            header_row=True,
            borders_innerH=True,
            row_background=True,
        ):
            dpg.add_table_column(
                label="Stat", width_fixed=True, init_width_or_weight=50
            )
            dpg.add_table_column(
                label="Expected", width_fixed=True, init_width_or_weight=60
            )

            for i, stat_val in enumerate(pair.factors.expected_stats):
                with dpg.table_row():
                    dpg.add_text(STAT_NAMES[i])
                    dpg.add_text(f"{stat_val:.1f}")

        _show_trait_inheritance_section(summary, favorable_keys, state)
        _show_disorders_defects_section(summary, state)

        if summary.universal_ev > 0:
            dpg.add_separator()
            dpg.add_text(
                f"Universal EV: {summary.universal_ev:.2f}", color=COLOR_SUCCESS
            )

        if summary.build_yields:
            dpg.add_separator()
            dpg.add_text("Build Yields:")
            for build_name, yield_val in summary.build_yields.items():
                yield_color = COLOR_SUCCESS if yield_val > 0 else COLOR_MUTED
                dpg.add_text(f"  {build_name}: {yield_val:.2f}", color=yield_color)


def _show_trait_inheritance_section(
    summary: PairSummaryData, favorable_keys: set[str], state: AppState
) -> None:
    """Show trait inheritance probabilities for favorable traits."""
    game_data = state.game_data

    passives = [
        (key, prob)
        for key, prob in summary.passives_inheritance.items()
        if key in favorable_keys and prob > 0
    ]
    actives = [
        (key, prob)
        for key, prob in summary.actives_inheritance.items()
        if key in favorable_keys and prob > 0
    ]

    body_parts: list[tuple[str, int, float]] = []
    for part_id, prob in summary.body_parts_inheritance.items():
        if prob > 0:
            for category in CatBodyPartCategory:
                if part_id in game_data.body_part_text.get(category, {}):
                    trait_key = f"{category.name.title()}{part_id}"
                    if trait_key in favorable_keys:
                        name_desc = game_data.body_part_text[category][part_id]
                        display_name = name_desc.name or trait_key
                        body_parts.append((display_name, part_id, prob))
                    break

    if not passives and not actives and not body_parts:
        return

    dpg.add_separator()
    with dpg.tree_node(label="Trait Inheritance", default_open=True):
        if passives:
            with dpg.tree_node(label=f"Passives ({len(passives)})"):
                for key, prob in sorted(passives, key=lambda x: -x[1]):
                    name = game_data.ability_text.get(key)
                    display_name = name.name if name and name.name else key
                    dpg.add_text(f"  {display_name}: {prob * 100:.1f}%")

        if actives:
            with dpg.tree_node(label=f"Actives ({len(actives)})"):
                for key, prob in sorted(actives, key=lambda x: -x[1]):
                    name = game_data.ability_text.get(key)
                    display_name = name.name if name and name.name else key
                    dpg.add_text(f"  {display_name}: {prob * 100:.1f}%")

        if body_parts:
            with dpg.tree_node(label=f"Body Parts ({len(body_parts)})"):
                for display_name, part_id, prob in sorted(
                    body_parts, key=lambda x: -x[2]
                ):
                    dpg.add_text(f"  {display_name}: {prob * 100:.1f}%")


def _show_disorders_defects_section(summary: PairSummaryData, state: AppState) -> None:
    """Show disorders and defects breakdown."""
    game_data = state.game_data

    inherited_disorders = [
        (key, prob) for key, prob in summary.disorder_inheritance.items() if prob > 0
    ]

    combined_malady = summary.expected_disorders + summary.expected_defects

    with dpg.tree_node(label="Disorders & Defects", default_open=True):
        if inherited_disorders:
            dpg.add_text("Inherited Disorders:")
            for key, prob in sorted(inherited_disorders, key=lambda x: -x[1]):
                name = game_data.ability_text.get(key)
                display_name = name.name if name and name.name else key
                color = COLOR_DANGER
                dpg.add_text(f"  {display_name}: {prob * 100:.1f}%", color=color)
        else:
            dpg.add_text("  No inherited disorders")

        dpg.add_separator()
        dpg.add_text(
            f"Novel Disorder (birth defect): {summary.novel_disorder_prob * 100:.1f}%"
        )
        dpg.add_text(
            f"Birth Defect Parts: {summary.novel_defect_parts_prob * 100:.1f}%"
        )

        dpg.add_separator()
        combined_text = (
            f"Combined: {combined_malady:.2f} expected ({combined_malady:.2f})"
        )
        color = COLOR_DANGER if combined_malady > 0 else COLOR_MUTED
        dpg.add_text(combined_text, color=color)


def on_pair_selected(
    sender: int, app_data: bool, user_data: tuple[int, ScoredPair, AppState]
) -> None:
    """Handle pair selection with radio behavior - only one pair selected at a time."""
    pair_index, pair, state = user_data

    if state.selected_pair_index is not None:
        old_item = f"pair_selectable_{state.selected_pair_index}"
        if dpg.does_item_exist(old_item):
            dpg.set_value(old_item, False)

    state.selected_pair_index = pair_index
    state.selected_pair = pair

    dpg.set_value(sender, True)

    if dpg.does_item_exist("inspector_tab_bar"):
        dpg.set_value("inspector_tab_bar", "inspector_pair_tab")

    show_pair_detail_window(pair, state)
