import dearpygui.dearpygui as dpg
from mewgenics_parser import Cat
from mewgenics_room_optimizer import RoomAssignment

from ..colors import COLOR_MUTED, COLOR_SUCCESS
from ..components.cats_table import add_cat_table_cols, render_cat_table_rows
from ..components.inspector.base import clear_inspector
from ..components.inspector.cat import on_cat_selected
from ..components.inspector.pair import on_pair_selected
from ..helpers import LOCATION_COL_WIDTH, get_assigned_room_key, get_pair_summary_data
from ..state import AppState


def build_details_section(state: AppState) -> None:
    """Called once at startup. Creates the static shell only."""
    with dpg.collapsing_header(label="Room Details", default_open=True):
        with dpg.child_window(height=200, border=True, tag="details_section"):
            dpg.add_text(
                "Select a room from results to see details",
                tag="details_placeholder",
            )


def update_details_section(selected_room: RoomAssignment, state: AppState) -> None:
    """Called on room selection. Clears and repopulates the child window content."""
    clear_details_section()
    if dpg.does_item_exist("details_placeholder"):
        dpg.hide_item("details_placeholder")

    dpg.add_tab_bar(parent="details_section", tag="details_tab_bar")

    with dpg.tab(label="Pairs", parent="details_tab_bar"):
        _build_pairs_tab(selected_room, state)

    with dpg.tab(label="Cats", parent="details_tab_bar"):
        _build_cats_tab(selected_room, state)

    with dpg.tab(label="Misplaced", parent="details_tab_bar"):
        _build_misplaced_tab(selected_room, state)


def clear_details_section() -> None:
    """Clear content and restore the placeholder."""
    section = "details_section"
    if dpg.does_item_exist(section):
        children = dpg.get_item_children(section)
        if children and 1 in children:
            for child in children[1]:  # type: ignore[iterable]
                dpg.delete_item(child)
    if dpg.does_item_exist("details_placeholder"):
        dpg.show_item("details_placeholder")


def _build_pairs_tab(selected_room: RoomAssignment, state: AppState) -> None:
    if not selected_room.pairs:
        dpg.add_text("No breeding pairs in this room")
        return

    with dpg.table(
        tag="pairs_detail_table",
        header_row=True,
        borders_innerH=True,
        row_background=True,
    ):
        dpg.add_table_column(label="Names", width_fixed=True)
        dpg.add_table_column(label="Quality", width_fixed=True)
        dpg.add_table_column(label="Stats ENS", width_fixed=True)
        dpg.add_table_column(label="Universal EV", width_fixed=True)
        dpg.add_table_column(label="Disorders", width_fixed=True)
        dpg.add_table_column(label="Defects", width_fixed=True)

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
                dpg.add_text(f"{summary.expected_stats_sum:.1f}")
                dpg.add_text(
                    f"{summary.universal_ev:.2f}",
                    color=COLOR_SUCCESS if summary.universal_ev > 0 else COLOR_MUTED,
                )
                dpg.add_text(f"{summary.expected_disorders:.2f}")
                dpg.add_text(f"{summary.expected_defects:.2f}")


def _build_cats_tab(selected_room: RoomAssignment, state: AppState) -> None:
    all_cats: list[Cat] = sorted(
        list(selected_room.cats) + list(selected_room.eternal_youth_cats),
        key=lambda c: (c.age if c.age is not None else 999, c.name or ""),
    )

    if not all_cats:
        dpg.add_text("No cats in this room")
        return

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


def _build_misplaced_tab(selected_room: RoomAssignment, state: AppState) -> None:
    if not state.results:
        dpg.add_text("Run optimization first to see misplaced cats.")
        return

    misplaced = []
    for cat in state.alive_cats:
        if cat.room != selected_room.room.key:
            continue
        assigned_room = get_assigned_room_key(cat.db_key, state.results)
        if assigned_room is not None and assigned_room != selected_room.room.key:
            assigned_display = next(
                (r.display_name for r in state.room_configs if r.key == assigned_room),
                assigned_room,
            )
            misplaced.append({"cat": cat, "assigned_room": assigned_display})

    if not misplaced:
        dpg.add_text("No misplaced cats in this room")
        return

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
            with dpg.table_row():
                dpg.add_text(cat.name or "Unnamed")
                dpg.add_text(str(cat.age if cat.age is not None else 0))
                dpg.add_text(selected_room.room.display_name)
                dpg.add_text(item["assigned_room"])


def on_room_selected(
    sender: int, app_data: bool, user_data: tuple[str, AppState]
) -> None:
    """Handle room selection in results table."""
    selected_key, state = user_data

    if (
        state.selected_result_room_key
        and state.selected_result_room_key != selected_key
    ):
        old_item = f"row_selectable_{state.selected_result_room_key}"
        if dpg.does_item_exist(old_item):
            dpg.set_value(old_item, False)

    state.selected_result_room_key = selected_key

    clear_inspector(state)

    if not state.results:
        return

    selected_room = next(
        (room for room in state.results.rooms if room.room.key == selected_key),
        None,
    )
    if not selected_room:
        return

    update_details_section(selected_room, state)
