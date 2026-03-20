import dearpygui.dearpygui as dpg
from mewgenics_room_optimizer.types import ScoredPair

from ...colors import (
    COLOR_DANGER,
    COLOR_DEFAULT_TEXT,
    COLOR_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
)
from ...helpers import get_pair_summary_data
from ...state import AppState
from .cat import on_cat_selected


def show_pair_detail_window(pair: ScoredPair, state: AppState) -> None:
    """Show pair details in the inspector panel with trait inheritance probabilities."""
    from mewgenics_scorer import calculate_trait_probability

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

        with dpg.group(parent=container, horizontal=True):
            dpg.add_button(
                label=name_a,
                callback=on_cat_selected,
                user_data=(pair.cat_a, state),
            )
            dpg.add_text(" + ")
            dpg.add_button(
                label=name_b,
                callback=on_cat_selected,
                user_data=(pair.cat_b, state),
            )

        dpg.add_text(
            f"Quality: {summary.quality:.1f} | Disorder: {summary.disorder_pct:.0f}% | Part Defect: {summary.part_defect_pct:.0f}% | Combined: {summary.combined_pct:.0f}%",
            color=summary.risk_color,
        )

        if state.trait_requirements:
            stimulation = 50.0
            for rc in state.room_configs:
                if rc.room_type.value == "breeding":
                    stimulation = rc.base_stim
                    break

            dpg.add_separator()
            dpg.add_text("Trait Inheritance Probabilities:")

            with dpg.table(
                tag="pair_trait_prob_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                dpg.add_table_column(label="Trait", width_stretch=True)
                dpg.add_table_column(
                    label="Type", width_fixed=True, init_width_or_weight=80
                )
                dpg.add_table_column(
                    label="Probability", width_fixed=True, init_width_or_weight=90
                )
                dpg.add_table_column(label="Source", width_stretch=True)

                for trait_req in state.trait_requirements:
                    prob_result = calculate_trait_probability(
                        trait_req, pair.cat_a, pair.cat_b, stimulation
                    )

                    if prob_result.probability >= 0.5:
                        color = COLOR_SUCCESS
                    elif prob_result.probability >= 0.25:
                        color = COLOR_WARNING
                    else:
                        color = COLOR_DANGER

                    with dpg.table_row():
                        dpg.add_text(trait_req.trait.get_display_name(state.game_data))
                        dpg.add_text(trait_req.trait.category.display_name)
                        dpg.add_text(
                            f"{prob_result.probability * 100:.1f}%", color=color
                        )
                        source_color = (
                            COLOR_MUTED
                            if prob_result.parent_source == "Neither"
                            else COLOR_DEFAULT_TEXT
                        )
                        dpg.add_text(prob_result.parent_source, color=source_color)

            hits = sum(1 for p in pair.factors.trait_probabilities if p.probability > 0)
            ev = (
                sum(
                    p.probability * p.trait.weight
                    for p in pair.factors.trait_probabilities
                )
                * 5.0
            )
            total = len(state.trait_requirements)
            if ev >= 1:
                dpg.add_text(
                    f"[* EV: {ev:.2f} from {hits}/{total} traits]",
                    color=COLOR_SUCCESS,
                )
        else:
            dpg.add_text("No favorable traits configured", color=COLOR_MUTED)


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
