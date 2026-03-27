import dearpygui.dearpygui as dpg
from mewgenics_room_optimizer.types import ScoredPair

from ...colors import (
    COLOR_MUTED,
    COLOR_SUCCESS,
)
from ...helpers import get_pair_summary_data
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
            f"Quality: {summary.quality:.1f} | Stats: {summary.expected_stats_sum:.1f} ENS | Malady: {summary.combined_malady_pct:.1f}%",
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

        dpg.add_separator()
        dpg.add_text("Malady Penalties:")

        dpg.add_text(
            f"Disorders: {summary.expected_disorders:.2f} ({summary.expected_disorders * 5.0:.1f} ENS penalty)"
        )
        dpg.add_text(
            f"Defects: {summary.expected_defects:.2f} ({summary.expected_defects * 1.0:.1f} ENS penalty)"
        )

        if summary.universal_ev > 0:
            dpg.add_separator()
            dpg.add_text(
                f"Universal EV: {summary.universal_ev:.2f} ENS", color=COLOR_SUCCESS
            )

        if summary.build_yields:
            dpg.add_separator()
            dpg.add_text("Build Yields:")
            for build_name, yield_val in summary.build_yields.items():
                yield_color = COLOR_SUCCESS if yield_val > 0 else COLOR_MUTED
                dpg.add_text(f"  {build_name}: {yield_val:.2f} ENS", color=yield_color)


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
