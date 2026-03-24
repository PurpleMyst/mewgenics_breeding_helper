from collections.abc import Callable

import dearpygui.dearpygui as dpg
from mewgenics_parser import Cat
from mewgenics_parser.traits import extract_traits_from_cat

from ..colors import COLOR_DANGER, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING
from ..helpers import (
    LOCATION_COL_WIDTH,
    get_assigned_room_key,
    plain_substring_match,
    trait_substring_match,
)
from ..state import AppState
from .inspector.cat import show_cat_detail_window


def add_cat_table_cols() -> None:
    dpg.add_table_column(label="Name", width_fixed=True)
    dpg.add_table_column(label="Sex", width_fixed=True)
    dpg.add_table_column(label="Age", width_fixed=True)
    dpg.add_table_column(
        label="Location",
        width_fixed=True,
        init_width_or_weight=LOCATION_COL_WIDTH,
    )
    dpg.add_table_column(label="STR", width_fixed=True)
    dpg.add_table_column(label="DEX", width_fixed=True)
    dpg.add_table_column(label="CON", width_fixed=True)
    dpg.add_table_column(label="INT", width_fixed=True)
    dpg.add_table_column(label="SPD", width_fixed=True)
    dpg.add_table_column(label="CHA", width_fixed=True)
    dpg.add_table_column(label="LCK", width_fixed=True)
    dpg.add_table_column(label="Sum", width_fixed=True)
    dpg.add_table_column(label="Traits", width_fixed=True)


def render_cat_table_rows(
    cats: list[Cat],
    state: AppState,
    parent_table_tag: str,
    row_tag_prefix: str = "row",
    *,
    row_callback: Callable,
) -> None:
    """Universal renderer for cat table rows to enforce consistent UI."""

    for cat in cats:
        sex_display = (
            cat.gender.value if hasattr(cat.gender, "value") else str(cat.gender)
        )
        age = cat.age if cat.age is not None else 0
        age_display = str(age)

        assigned_room = get_assigned_room_key(cat.db_key, state.results)
        current_room = cat.room
        if assigned_room is None:
            loc_color = COLOR_WARNING
        elif current_room == assigned_room:
            loc_color = COLOR_SUCCESS
        else:
            loc_color = COLOR_DANGER

        stat_values = cat.stat_total
        total = sum(stat_values)

        all_traits = extract_traits_from_cat(cat)
        trait_names = [t.get_display_name(state.game_data) for t in all_traits[:3]]
        trait_display = ", ".join(trait_names)

        callback = row_callback
        user_data = (cat, state)
        tag = f"{row_tag_prefix}_{parent_table_tag}_{cat.db_key}"

        with dpg.table_row(parent=parent_table_tag):
            dpg.add_selectable(
                label=cat.name,
                span_columns=True,
                callback=callback,
                user_data=user_data,
                tag=tag,
            )

            dpg.add_text(str(sex_display))
            dpg.add_text(age_display)

            display_room = current_room if current_room is not None else "Unassigned"
            dpg.add_text(cat.room_display or display_room, color=loc_color)

            for sv in stat_values:
                dpg.add_text(str(sv))
            dpg.add_text(str(total))
            dpg.add_text(
                trait_display, color=COLOR_MUTED if not trait_display else COLOR_SUCCESS
            )


def build_all_cats_tab(state: AppState) -> None:
    """Build the All Cats tab with searchable cat table."""
    with dpg.collapsing_header(label="All Cats", default_open=True):
        with dpg.child_window(height=350, border=True, tag="all_cats_section"):
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag="cat_name_filter",
                    hint="Filter by name...",
                    width=150,
                    callback=on_cat_name_filter,
                    user_data=state,
                )
                dpg.add_input_text(
                    tag="cat_trait_filter",
                    hint="Filter by trait...",
                    width=150,
                    callback=on_cat_trait_filter,
                    user_data=state,
                )
                dpg.add_checkbox(
                    tag="show_all_cats",
                    label="Show non-In-House",
                    default_value=False,
                    callback=on_toggle_show_all_cats,
                    user_data=state,
                )

            with dpg.table(
                tag="all_cats_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
                height=280,
            ):
                add_cat_table_cols()

            dpg.add_text("Load a save to see cats", tag="all_cats_placeholder")

    if state.cats:
        update_all_cats_table(state)


def update_all_cats_table(
    state: AppState, name_filter: str = "", trait_filter: str = ""
) -> None:
    """Update the All Cats table with filtered cats."""
    table = "all_cats_table"
    placeholder = "all_cats_placeholder"

    if not dpg.does_item_exist(table):
        return

    children = dpg.get_item_children(table)
    if children and 1 in children:
        for row in children[1]:  # type: ignore[iterable]
            dpg.delete_item(row)

    show_all = dpg.get_value("show_all_cats")
    cats = state.cats if show_all else state.alive_cats

    name_filtered = plain_substring_match(name_filter, [c.name or "" for c in cats])
    name_filtered_set = set(name_filtered)

    filtered_cats = [c for c in cats if (c.name or "") in name_filtered_set]

    if trait_filter:
        trait_filtered = []
        for cat in filtered_cats:
            traits = extract_traits_from_cat(cat)
            if trait_substring_match(trait_filter, traits, state.game_data):
                trait_filtered.append(cat)
        filtered_cats = trait_filtered

    if not filtered_cats:
        dpg.show_item(placeholder)
        return

    dpg.hide_item(placeholder)

    render_cat_table_rows(
        cats=filtered_cats,
        state=state,
        parent_table_tag=table,
        row_callback=lambda sender, app_data, user_data: on_all_cats_cat_selected(
            sender, app_data, (user_data[0].db_key, user_data[1])
        ),
        row_tag_prefix="all_cats_row",
    )


def on_cat_name_filter(sender: int, app_data: str, user_data: AppState) -> None:
    """Filter All Cats table by name with fuzzy matching."""
    filter_text = app_data or ""
    update_all_cats_table(
        user_data, filter_text, dpg.get_value("cat_trait_filter") or ""
    )


def on_cat_trait_filter(sender: int, app_data: str, user_data: AppState) -> None:
    """Filter All Cats table by trait with fuzzy matching."""
    filter_text = app_data or ""
    update_all_cats_table(
        user_data, dpg.get_value("cat_name_filter") or "", filter_text
    )


def on_toggle_show_all_cats(sender: int, app_data: bool, user_data: AppState) -> None:
    """Toggle showing non-In-House cats."""
    update_all_cats_table(
        user_data,
        dpg.get_value("cat_name_filter") or "",
        dpg.get_value("cat_trait_filter") or "",
    )


def on_all_cats_cat_selected(
    sender: int, app_data: bool, user_data: tuple[int, AppState]
) -> None:
    """Handle cat selection in All Cats table with radio behavior."""
    db_key, state = user_data

    if state.selected_cat_db_key is not None and state.selected_cat_db_key != db_key:
        old_item = f"all_cats_row_{state.selected_cat_db_key}"
        if dpg.does_item_exist(old_item):
            dpg.set_value(old_item, False)

    cat = None
    for c in state.cats:
        if c.db_key == db_key:
            cat = c
            break

    if not cat:
        return

    state.selected_cat_db_key = db_key
    show_cat_detail_window(cat, state)
