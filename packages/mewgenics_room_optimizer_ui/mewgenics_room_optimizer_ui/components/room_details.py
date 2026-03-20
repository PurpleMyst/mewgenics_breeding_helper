import dearpygui.dearpygui as dpg
from mewgenics_room_optimizer import RoomAssignment

from ..colors import COLOR_DANGER, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING
from ..components.cats_table import add_cat_table_cols, render_cat_table_rows
from ..components.inspector.base import clear_inspector
from ..components.inspector.cat import on_cat_selected
from ..components.inspector.pair import on_pair_selected
from ..helpers import LOCATION_COL_WIDTH, get_assigned_room_key, get_pair_summary_data
from ..state import AppState


def build_details_tabs(selected_room: RoomAssignment, state: AppState) -> None:
    """Build the tabbed details view for a selected room."""
    dpg.add_tab_bar(parent="details_section", tag="details_tab_bar")

    with dpg.tab(label="Pairs", parent="details_tab_bar"):
        if selected_room.pairs:
            with dpg.table(
                tag="pairs_detail_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                dpg.add_table_column(label="Names", width_fixed=True)
                dpg.add_table_column(label="Quality", width_fixed=True)
                dpg.add_table_column(label="Risk", width_fixed=True)
                dpg.add_table_column(label="Lovers", width_fixed=True)
                dpg.add_table_column(label="Libido", width_fixed=True)
                dpg.add_table_column(label="Aggr", width_fixed=True)
                dpg.add_table_column(label="Char", width_fixed=True)
                dpg.add_table_column(label="Var", width_fixed=True)
                dpg.add_table_column(label="Trait EV", width_fixed=True)

                for i, pair in enumerate(selected_room.pairs):
                    summary = get_pair_summary_data(pair, state)

                    with dpg.table_row():
                        dpg.add_selectable(
                            label=summary.names_display,
                            callback=on_pair_selected,
                            user_data=(i, pair, state),
                            tag=f"pair_selectable_{i}",
                        )
                        dpg.add_text(f"{summary.quality:.1f}")
                        dpg.add_text(
                            f"D:{summary.disorder_pct:2.0f}% P:{summary.part_defect_pct:2.0f}% C:{summary.combined_pct:2.0f}%",
                            color=summary.risk_color,
                        )

                        lovers_color = (
                            COLOR_SUCCESS if summary.mutual_lovers else COLOR_MUTED
                        )
                        dpg.add_text(
                            "Y" if summary.mutual_lovers else "N", color=lovers_color
                        )

                        libido_color = (
                            COLOR_SUCCESS
                            if summary.libido_factor >= 0.6
                            else COLOR_MUTED
                        )
                        dpg.add_text(f"{summary.libido_factor:.2f}", color=libido_color)

                        aggr_color = (
                            COLOR_SUCCESS
                            if summary.aggression_factor <= 0.4
                            else COLOR_DANGER
                        )
                        dpg.add_text(
                            f"{summary.aggression_factor:.2f}", color=aggr_color
                        )

                        char_color = (
                            COLOR_SUCCESS
                            if summary.charisma_factor >= 0.4
                            else COLOR_MUTED
                        )
                        dpg.add_text(f"{summary.charisma_factor:.2f}", color=char_color)

                        var_color = (
                            COLOR_SUCCESS
                            if summary.stat_variance <= 5.0
                            else (
                                COLOR_DANGER
                                if summary.stat_variance > 10.0
                                else COLOR_WARNING
                            )
                        )
                        dpg.add_text(f"{summary.stat_variance:.1f}", color=var_color)

                        ev_color = (
                            COLOR_SUCCESS if summary.trait_ev > 0 else COLOR_MUTED
                        )
                        dpg.add_text(f"{summary.trait_ev:.2f}", color=ev_color)
        else:
            dpg.add_text("No breeding pairs in this room")

    # Cats tab - high-density table
    with dpg.tab(label="Cats", parent="details_tab_bar"):
        all_cats = list(selected_room.cats) + list(selected_room.eternal_youth_cats)
        # Sort by age then name
        all_cats.sort(key=lambda c: (c.age if c.age is not None else 999, c.name or ""))
        if all_cats:
            with dpg.table(
                tag="cats_detail_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                add_cat_table_cols()
                render_cat_table_rows(
                    cats=all_cats,
                    state=state,
                    parent_table_tag="cats_detail_table",
                    row_callback=on_cat_selected,
                    row_tag_prefix="cat_row",
                )
        else:
            dpg.add_text("No cats in this room")

    # Misplaced tab - show cats in this room that shouldn't be here
    with dpg.tab(label="Misplaced", parent="details_tab_bar"):
        if not state.results:
            dpg.add_text("Run optimization first to see misplaced cats.")
        else:
            # Find cats currently physically in this room that the optimizer assigned elsewhere
            misplaced = []
            for cat in state.alive_cats:
                # Check if the cat is actually living in this room right now
                if cat.room == selected_room.room.key:
                    assigned_room = get_assigned_room_key(cat.db_key, state.results)

                    # If the optimizer put them in a different room, flag them as misplaced
                    if (
                        assigned_room is not None
                        and assigned_room != selected_room.room.key
                    ):
                        misplaced.append(
                            {
                                "cat": cat,
                                "assigned_room": next(
                                    (
                                        r.display_name
                                        for r in state.room_configs
                                        if r.key == assigned_room
                                    ),
                                    assigned_room,
                                ),
                            }
                        )

            if misplaced:
                # Sort by age then name
                misplaced.sort(
                    key=lambda x: (
                        x["cat"].age if x["cat"].age is not None else 999,
                        x["cat"].name or "",
                    )
                )

                with dpg.table(
                    tag="misplaced_table",
                    header_row=True,
                    borders_innerH=True,
                    row_background=True,
                ):
                    dpg.add_table_column(label="Name", width_fixed=True)
                    dpg.add_table_column(label="Age", width_fixed=True)
                    dpg.add_table_column(
                        label="In Save",
                        width_fixed=True,
                        init_width_or_weight=LOCATION_COL_WIDTH,
                    )
                    dpg.add_table_column(
                        label="Assigned",
                        width_fixed=True,
                        init_width_or_weight=LOCATION_COL_WIDTH,
                    )

                    for item in misplaced:
                        cat = item["cat"]
                        age = cat.age if cat.age is not None else 0
                        with dpg.table_row():
                            dpg.add_text(cat.name or "Unnamed")
                            dpg.add_text(str(age))
                            dpg.add_text(selected_room.room.display_name)
                            dpg.add_text(item["assigned_room"])
            else:
                dpg.add_text("No misplaced cats in this room")


def clear_details_section() -> None:
    """Clear the details section."""
    section = "details_section"
    if dpg.does_item_exist(section):
        children = dpg.get_item_children(section)
        if children and 1 in children:
            for child in children[1]:  # type: ignore[iterable]
                dpg.delete_item(child)


def on_room_selected(
    sender: int, app_data: bool, user_data: tuple[str, AppState]
) -> None:
    """Handle room selection in results table."""
    selected_key, state = user_data

    # Deselect old selection visually
    if (
        state.selected_result_room_key
        and state.selected_result_room_key != selected_key
    ):
        old_item = f"row_selectable_{state.selected_result_room_key}"
        if dpg.does_item_exist(old_item):
            dpg.set_value(old_item, False)

    # Update state
    state.selected_result_room_key = selected_key
    state.sim_cat_a_key = None
    state.sim_cat_b_key = None

    # Clear inspector when room is selected
    clear_inspector(state)

    if not state.results:
        return

    selected_room = None
    for room in state.results.rooms:
        if room.room.key == selected_key:
            selected_room = room
            break

    if not selected_room:
        return

    clear_details_section()
    build_details_tabs(selected_room, state)
