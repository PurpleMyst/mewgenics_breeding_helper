import dearpygui.dearpygui as dpg

from ...state import AppState
from ...tags import Tags
from ...colors import COLOR_MUTED


def clear_inspector(state: AppState) -> None:
    """Clear the inspector panel and show placeholder."""
    container = "inspector_container"
    if dpg.does_item_exist(container):
        dpg.delete_item(container, children_only=True)
    dpg.show_item(Tags.INSPECTOR_PLACEHOLDER)
    dpg.hide_item(container)

    if dpg.does_item_exist(Tags.INSPECTOR_PAIR_CONTAINER):
        dpg.delete_item(Tags.INSPECTOR_PAIR_CONTAINER, children_only=True)
    dpg.show_item(Tags.INSPECTOR_PAIR_PLACEHOLDER)

    state.selected_pair = None
    state.selected_pair_index = None


def build_inspector_section(state: AppState) -> None:
    """Build the inspector panel with tabs for cat and pair inspection."""
    with dpg.collapsing_header(label="Inspector", default_open=True):
        with dpg.child_window(border=True, tag=Tags.INSPECTOR_SECTION):
            dpg.add_tab_bar(tag=Tags.INSPECTOR_TAB_BAR)

            with dpg.tab(
                label="Cat", parent=Tags.INSPECTOR_TAB_BAR, tag=Tags.INSPECTOR_CAT_TAB
            ):
                dpg.add_text(
                    "Select a cat to inspect",
                    color=COLOR_MUTED,
                    tag=Tags.INSPECTOR_PLACEHOLDER,
                )
                dpg.add_group(tag=Tags.INSPECTOR_CONTAINER)

            with dpg.tab(
                label="Pair", parent=Tags.INSPECTOR_TAB_BAR, tag=Tags.INSPECTOR_PAIR_TAB
            ):
                dpg.add_text(
                    "Select a pair to view trait inheritance probabilities",
                    tag=Tags.INSPECTOR_PAIR_PLACEHOLDER,
                    color=COLOR_MUTED,
                )
                dpg.add_group(tag=Tags.INSPECTOR_PAIR_CONTAINER)
