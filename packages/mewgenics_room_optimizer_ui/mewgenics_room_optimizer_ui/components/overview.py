import dearpygui.dearpygui as dpg

from ..colors import COLOR_MUTED
from ..helpers import TraitCountInfo
from ..state import AppState


def build_overview_tab(state: AppState) -> None:
    """Build the Overview tab showing trait counts across cats."""
    with dpg.collapsing_header(label="Overview", default_open=True):
        with dpg.child_window(height=350, border=True, tag="overview_section"):
            dpg.add_text(
                "Favorable Trait Distribution (In House Cats)", color=(180, 180, 180)
            )

            with dpg.table(
                tag="overview_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
                height=300,
            ):
                dpg.add_table_column(label="Trait", width_fixed=True)
                dpg.add_table_column(label="Category", width_fixed=True)
                dpg.add_table_column(label="Count", width_fixed=True)

            dpg.add_text("Load a save to see trait counts", tag="overview_placeholder")


def update_overview_table(state: AppState) -> None:
    """Update the Overview table with trait counts."""
    table = "overview_table"
    placeholder = "overview_placeholder"

    if not dpg.does_item_exist(table):
        return

    children = dpg.get_item_children(table)
    if children and 1 in children:
        for row in children[1]:  # type: ignore[iterable]
            dpg.delete_item(row)

    if not state.alive_cats:
        dpg.show_item(placeholder)
        return

    dpg.hide_item(placeholder)

    trait_info = _get_favorable_traits_info(state)

    trait_info.sort(key=lambda x: (-x.count, x.trait.get_display_name(state.game_data)))

    for info in trait_info:
        with dpg.table_row(parent=table):
            dpg.add_text(info.trait.get_display_name(state.game_data))
            dpg.add_text(info.trait.category.display_name, color=COLOR_MUTED)
            dpg.add_text(str(info.count))


def _get_favorable_traits_info(state: AppState) -> list[TraitCountInfo]:
    """Collect favorable traits with counts and source labels."""
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

    for cat in state.alive_cats:
        for info in trait_map.values():
            if info.trait.is_possessed_by(cat):
                info.count += 1

    return list(trait_map.values())
