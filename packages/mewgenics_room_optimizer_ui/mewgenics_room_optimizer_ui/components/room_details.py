import dearpygui.dearpygui as dpg
from mewgenics_parser import Cat, GameData
from mewgenics_parser.cat import CatBodyPartCategory
from mewgenics_room_optimizer import RoomAssignment

from ..colors import COLOR_MUTED, COLOR_SUCCESS, ROOM_TYPE_COLORS
from ..components.cats_table import add_cat_table_cols, render_cat_table_rows
from ..components.inspector.base import clear_inspector
from ..components.inspector.cat import on_cat_selected
from ..components.inspector.pair import on_pair_selected
from ..helpers import (
    TraitCountInfo,
    get_all_favorable_keys,
    get_assigned_room_key,
    get_pair_summary_data,
)
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

    with dpg.tab(label="Overview", parent="details_tab_bar"):
        _build_overview_tab(selected_room, state)

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


def _format_body_part_display_name(
    part_id: int, category: CatBodyPartCategory, game_data: GameData
) -> str:
    """Get display name for a body part from part_id and category."""
    name_desc = game_data.body_part_text[category].get(part_id)
    if name_desc and name_desc.name:
        return name_desc.name
    return f"{category.name.title()}"


def _format_trait_column(
    inheritance_dict: dict[str, float],
    favorable_keys: set[str],
    game_data: GameData,
    max_items: int = 3,
) -> str:
    """Format trait inheritance dict as comma-separated string for table display."""
    items = []
    for key, prob in sorted(inheritance_dict.items(), key=lambda x: -x[1]):
        if key in favorable_keys and prob > 0:
            trait_display = game_data.ability_text.get(key)
            if trait_display and trait_display.name:
                name = trait_display.name
            else:
                name = key
            items.append(f"{name} {prob * 100:.0f}%")
            if len(items) >= max_items:
                break
    return ", ".join(items) if items else ""


def _format_body_parts_column(
    body_parts_dict: dict[int, float],
    favorable_keys: set[str],
    game_data: GameData,
    max_items: int = 3,
) -> str:
    """Format body parts inheritance dict as comma-separated string for table display."""
    items = []
    for part_id, prob in sorted(body_parts_dict.items(), key=lambda x: -x[1]):
        if prob > 0:
            for category in CatBodyPartCategory:
                display_name = _format_body_part_display_name(
                    part_id, category, game_data
                )
                trait_key = f"{category.name.title()}{part_id}"
                if trait_key in favorable_keys:
                    items.append(f"{display_name} {prob * 100:.0f}%")
                    break
        if len(items) >= max_items:
            break
    return ", ".join(items) if items else ""


def _build_pairs_tab(selected_room: RoomAssignment, state: AppState) -> None:
    if not selected_room.pairs:
        dpg.add_text("No breeding pairs in this room")
        return

    favorable_keys = get_all_favorable_keys(state)

    with dpg.table(
        tag="pairs_detail_table",
        header_row=True,
        borders_innerH=True,
        row_background=True,
        resizable=False,
    ):
        dpg.add_table_column(label="Names", width_fixed=True)
        dpg.add_table_column(label="Stats", width_fixed=True)
        dpg.add_table_column(label="Passives", width_stretch=True)
        dpg.add_table_column(label="Actives", width_stretch=True)
        dpg.add_table_column(label="Body Parts", width_stretch=True)
        dpg.add_table_column(label="COI", width_fixed=True)
        dpg.add_table_column(label="Quality", width_fixed=True)

        for i, pair in enumerate(selected_room.pairs):
            summary = get_pair_summary_data(pair, state)
            combined_malady = summary.expected_disorders + summary.expected_defects

            passives_str = _format_trait_column(
                summary.passives_inheritance, favorable_keys, state.game_data
            )
            actives_str = _format_trait_column(
                summary.actives_inheritance, favorable_keys, state.game_data
            )
            body_parts_str = _format_body_parts_column(
                summary.body_parts_inheritance, favorable_keys, state.game_data
            )

            coi_str = f"{summary.coi * 100:.1f}% COI ({combined_malady:.2f})"

            with dpg.table_row():
                dpg.add_selectable(
                    label=summary.names_display,
                    callback=on_pair_selected,
                    user_data=(i, pair, state),
                    tag=f"pair_selectable_{i}",
                )
                dpg.add_text(f"{summary.expected_stats_sum:.1f}")
                dpg.add_text(
                    passives_str, color=COLOR_SUCCESS if passives_str else COLOR_MUTED
                )
                dpg.add_text(
                    actives_str, color=COLOR_SUCCESS if actives_str else COLOR_MUTED
                )
                dpg.add_text(
                    body_parts_str,
                    color=COLOR_SUCCESS if body_parts_str else COLOR_MUTED,
                )
                dpg.add_text(coi_str)
                dpg.add_text(f"{summary.quality:.1f}")


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
            assigned_config = next(
                (r for r in state.room_configs if r.key == assigned_room),
                None,
            )
            assigned_display = (
                assigned_config.display_name if assigned_config else assigned_room
            )
            assigned_color = (
                ROOM_TYPE_COLORS.get(assigned_config.room_type.value, COLOR_MUTED)
                if assigned_config
                else COLOR_MUTED
            )
            misplaced.append(
                {
                    "cat": cat,
                    "assigned_room": assigned_display,
                    "assigned_color": assigned_color,
                }
            )

    if not misplaced:
        dpg.add_text("No misplaced cats in this room")
        return

    misplaced.sort(
        key=lambda x: (
            x["cat"].age if x["cat"].age is not None else 999,
            -x["cat"].db_key,
        )
    )

    with dpg.table(
        tag="misplaced_table",
        header_row=True,
        borders_innerH=True,
        row_background=True,
        resizable=False,
    ):
        dpg.add_table_column(label="Name", width_fixed=True)
        dpg.add_table_column(label="Age", width_fixed=True)
        dpg.add_table_column(
            label="In Save",
            width_fixed=True,
        )
        dpg.add_table_column(
            label="Assigned",
            width_fixed=True,
        )
        for item in misplaced:
            cat = item["cat"]
            with dpg.table_row():
                dpg.add_text(cat.name or "Unnamed")
                dpg.add_text(str(cat.age if cat.age is not None else 0))
                dpg.add_text(selected_room.room.display_name)
                dpg.add_text(item["assigned_room"], color=item["assigned_color"])


def _get_room_favorable_traits_info(
    selected_room: RoomAssignment, state: AppState
) -> list[TraitCountInfo]:
    """Collect favorable traits with counts for cats in a specific room."""
    trait_map: dict[str, TraitCountInfo] = {}

    for universal in state.universals:
        key = universal.trait.key
        if key not in trait_map:
            trait_map[key] = TraitCountInfo(
                trait=universal.trait, count=0, sources=["Universal"]
            )
        else:
            trait_map[key].sources.append("Universal")

    for build in state.target_builds:
        for tw in build.requirements:
            key = tw.trait.key
            if key not in trait_map:
                trait_map[key] = TraitCountInfo(
                    trait=tw.trait, count=0, sources=[build.name]
                )
            elif build.name not in trait_map[key].sources:
                trait_map[key].sources.append(build.name)

    room_cats = list(selected_room.cats) + list(selected_room.eternal_youth_cats)
    for cat in room_cats:
        for info in trait_map.values():
            if info.trait.is_possessed_by(cat):
                info.count += 1

    return list(trait_map.values())


def _build_overview_tab(selected_room: RoomAssignment, state: AppState) -> None:
    """Build the Overview tab for a specific room."""
    room_cats = list(selected_room.cats) + list(selected_room.eternal_youth_cats)

    if not room_cats:
        dpg.add_text("No cats in this room")
        return

    trait_info = _get_room_favorable_traits_info(selected_room, state)
    trait_info.sort(key=lambda x: (-x.count, x.trait.get_display_name(state.game_data)))

    with dpg.table(
        tag="room_overview_table",
        header_row=True,
        borders_innerH=True,
        row_background=True,
    ):
        dpg.add_table_column(label="Trait", width_fixed=True)
        dpg.add_table_column(label="Category", width_fixed=True)
        dpg.add_table_column(label="Count", width_fixed=True)

    for info in trait_info:
        with dpg.table_row(parent="room_overview_table"):
            dpg.add_text(info.trait.get_display_name(state.game_data))
            dpg.add_text(info.trait.category.display_name, color=COLOR_MUTED)
            dpg.add_text(str(info.count))


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
