from typing import Any

import dearpygui.dearpygui as dpg
from mewgenics_parser import TraitCategory
from mewgenics_parser.gpak import GameData
from mewgenics_parser.traits import Trait, create_trait
from mewgenics_scorer import TraitRequirement

from ..helpers import trait_substring_match
from ..state import AppState


def build_traits_section(state: AppState) -> None:
    """Build the favorable traits selection section."""
    with dpg.collapsing_header(label="Favorable Traits", default_open=True):
        with dpg.child_window(border=True, tag="traits_section"):
            with dpg.tab_bar():
                for category in TraitCategory:
                    tab_label = category.display_name
                    with dpg.tab(label=tab_label):
                        listbox_tag = f"{category}_listbox"
                        filter_tag = f"{category}_filter"

                        dpg.add_input_text(
                            tag=filter_tag,
                            hint="Filter...",
                            width=-1,
                            callback=on_trait_filter,
                            user_data=(state, listbox_tag, category),
                        )
                        dpg.add_listbox(
                            tag=listbox_tag,
                            width=-1,
                            num_items=5,
                        )
                        dpg.add_button(
                            label="Add",
                            callback=on_add_trait,
                            user_data=(state, category, listbox_tag),
                        )

            dpg.add_separator()
            with dpg.table(
                header_row=False, borders_innerV=False, borders_outerV=False
            ):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=80)
                with dpg.table_row():
                    dpg.add_text("Selected Traits:")
                    dpg.add_button(
                        label="Clear All", callback=on_clear_traits, user_data=state
                    )

            dpg.add_group(tag="selected_traits_container")


def update_traits_display(state: AppState) -> None:
    """Update the selected traits display."""
    container = "selected_traits_container"
    if not dpg.does_item_exist(container):
        return

    dpg.delete_item(container, children_only=True)

    for i, trait_req in enumerate(state.trait_requirements):
        with dpg.group(horizontal=True, parent=container):
            trait = trait_req.trait

            display_name = trait.get_display_name(state.game_data)
            description = trait.get_description(state.game_data)
            upgraded_desc = trait.get_upgraded_description(state.game_data)

            trait_text = dpg.add_text(
                f"[{int(trait_req.weight):2}] {trait.category.display_name}: {display_name}"
            )

            tooltip_lines = []
            if description:
                tooltip_lines.append(f"Base: {description}")
            if upgraded_desc:
                tooltip_lines.append(f"Upgraded: {upgraded_desc}")

            tooltip_text = (
                "\n".join(tooltip_lines) if tooltip_lines else "No description"
            )

            with dpg.tooltip(trait_text):
                dpg.add_text(tooltip_text)
            # TODO: make these buttons flush with the right edge of the container instead of right
            # next to the text
            dpg.add_button(
                label="-",
                width=25,
                callback=on_decrement_weight,
                user_data=(i, state),
            )
            dpg.add_button(
                label="+",
                width=25,
                callback=on_increment_weight,
                user_data=(i, state),
            )
            dpg.add_button(
                label="X",
                width=25,
                callback=on_remove_trait,
                user_data=(i, state),
            )


def init_traits_lists(state: AppState) -> None:
    """Initialize the trait filter listboxes with available traits from cats."""
    for category in TraitCategory:
        traits = state.get_available_traits(category)
        formatted = [_format_trait_for_listbox(t, state.game_data) for t in traits]
        listbox_tag = f"{category.value}_listbox"
        if dpg.does_item_exist(listbox_tag):
            dpg.configure_item(listbox_tag, items=formatted)
        else:
            print(
                f"Warning: Tried to initialize traits listbox for {category.value} but it does not exist in the UI"
            )

    update_traits_display(state)


def on_trait_filter(
    sender: int, app_data: str, user_data: tuple[AppState, str, str]
) -> None:
    """Filter traits listbox with fuzzy matching."""
    state, listbox_tag, category = user_data
    filter_text = app_data or ""

    traits = state.get_available_traits(category)
    filtered = trait_substring_match(filter_text, traits, state.game_data)
    formatted = [_format_trait_for_listbox(t, state.game_data) for t in filtered]

    dpg.configure_item(listbox_tag, items=formatted)


def on_add_trait(
    sender: int | None, app_data: Any, user_data: tuple[AppState, TraitCategory, str]
) -> None:
    """Add selected trait to favorable traits."""
    state, category, listbox_tag = user_data
    selected = dpg.get_value(listbox_tag)

    if not selected:
        items = dpg.get_item_configuration(listbox_tag).get("items", [])
        if items:
            selected = items[0]

    if selected:
        actual_key = selected.split(" | ")[0].strip()
        state.trait_requirements.append(
            TraitRequirement(trait=create_trait(category, actual_key), weight=5.0)
        )
        state.save()
        update_traits_display(state)


def on_remove_trait(
    sender: int, app_data: Any, user_data: tuple[int, AppState]
) -> None:
    """Remove a trait from favorable traits."""
    index, state = user_data
    state.trait_requirements.pop(index)
    state.save()
    update_traits_display(state)


def on_clear_traits(sender: int, app_data: Any, user_data: AppState) -> None:
    """Clear all favorable traits."""
    user_data.trait_requirements.clear()
    user_data.save()
    update_traits_display(user_data)


def on_increment_weight(
    sender: int, app_data: Any, user_data: tuple[int, AppState]
) -> None:
    """Increment trait weight."""
    index, state = user_data
    state.trait_requirements[index].weight = min(
        10, state.trait_requirements[index].weight + 1
    )
    state.save()
    update_traits_display(state)


def on_decrement_weight(
    sender: int, app_data: Any, user_data: tuple[int, AppState]
) -> None:
    """Decrement trait weight."""
    index, state = user_data
    state.trait_requirements[index].weight = max(
        1, state.trait_requirements[index].weight - 1
    )
    state.save()
    update_traits_display(state)


def on_trait_weight_changed(
    sender: int, app_data: int, user_data: tuple[int, AppState]
) -> None:
    """Handle trait weight change."""
    index, state = user_data
    new_weight = max(1, min(10, int(app_data)))
    state.trait_requirements[index].weight = float(new_weight)
    state.save()


def _format_trait_for_listbox(trait: Trait, game_data: GameData) -> str:
    """Ensure consistent string formatting across all trait listboxes."""
    parts = [trait.key]
    display_name = trait.get_display_name(game_data)
    if display_name and display_name not in parts:
        parts.append(display_name)

    description = trait.get_description(game_data)
    if description and description not in parts:
        parts.append(description)

    return " | ".join(parts)
