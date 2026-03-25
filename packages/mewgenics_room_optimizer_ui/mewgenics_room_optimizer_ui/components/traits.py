from typing import Any
from dataclasses import replace
from uuid import UUID

import dearpygui.dearpygui as dpg
from mewgenics_parser import TraitCategory
from mewgenics_parser.gpak import GameData
from mewgenics_parser.traits import Trait, create_trait
from mewgenics_scorer.types import TargetBuild, TraitWeight
from uuid import uuid4

from ..helpers import trait_substring_match
from ..state import AppState


def _build_header_label(build: TargetBuild) -> str:
    """Build the collapsing header label from a build."""
    return build.name


def _configure_build_header_label(build_id_hex: str, build: TargetBuild) -> None:
    """Update the header label for a build without rebuilding."""
    dpg.configure_item(f"build_{build_id_hex}_header", label=_build_header_label(build))


def _find_build_index(state: AppState, build_id: UUID) -> int | None:
    """Find the index of a build by its UUID."""
    for i, b in enumerate(state.target_builds):
        if b.id == build_id:
            return i
    return None


def build_traits_section(state: AppState) -> None:
    """Build the universals and target builds selection section."""
    with dpg.collapsing_header(label="Universals & Builds", default_open=True):
        with dpg.child_window(border=True, tag="traits_section"):
            _build_shared_trait_selector(state)
            with dpg.tab_bar():
                with dpg.tab(label="Universals"):
                    _build_universals_tab(state)
                with dpg.tab(label="Target Builds"):
                    _build_target_builds_tab(state)


def _build_shared_trait_selector(state: AppState) -> None:
    """Build the shared trait selector visible to all tabs."""
    dpg.add_text("Trait Selector:", color=(180, 180, 180))
    with dpg.tab_bar(tag="trait_selector_tabs"):
        for category in TraitCategory:
            tab_label = category.display_name
            with dpg.tab(label=tab_label, tag=f"selector_tab_{category.value}"):
                listbox_tag = f"universal_{category.value}_listbox"
                filter_tag = f"universal_{category.value}_filter"

                dpg.add_input_text(
                    tag=filter_tag,
                    hint="Filter...",
                    width=-1,
                    callback=on_universal_filter,
                    user_data=(state, listbox_tag, category),
                )
                dpg.add_listbox(
                    tag=listbox_tag,
                    width=-1,
                    num_items=5,
                )


def _build_universals_tab(state: AppState) -> None:
    """Build the universals tab."""
    with dpg.table(header_row=False, borders_innerV=False, borders_outerV=False):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True)
        dpg.add_table_column(width_fixed=True)
        with dpg.table_row():
            dpg.add_text("Selected Universals:")
            dpg.add_button(
                label="Add Universal",
                callback=on_add_universal,
                user_data=state,
            )
            dpg.add_button(
                label="Clear All", callback=on_clear_universals, user_data=state
            )

    dpg.add_group(tag="selected_universals_container")


def _build_target_builds_tab(state: AppState) -> None:
    """Build the target builds tab."""
    with dpg.group():
        dpg.add_button(
            label="Add New Build",
            callback=on_add_build,
            user_data=state,
        )
        dpg.add_separator()
        dpg.add_group(tag="builds_container")


def update_traits_display(state: AppState) -> None:
    """Update the selected universals and builds display."""
    _update_universals_display(state)
    _update_builds_display(state)


def _update_universals_display(state: AppState) -> None:
    """Update the selected universals display."""
    container = "selected_universals_container"
    if not dpg.does_item_exist(container):
        return

    dpg.delete_item(container, children_only=True)

    dpg.add_table(
        tag="universals_table",
        parent=container,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerV=False,
        header_row=False,
    )
    dpg.add_table_column(width_stretch=True, parent="universals_table")
    dpg.add_table_column(
        width_fixed=True, init_width_or_weight=120, parent="universals_table"
    )
    dpg.add_table_column(
        width_fixed=True, init_width_or_weight=80, parent="universals_table"
    )
    dpg.add_table_column(
        width_fixed=True, init_width_or_weight=25, parent="universals_table"
    )

    for i, universal in enumerate(state.universals):
        trait = universal.trait
        display_name = trait.get_display_name(state.game_data)
        description = trait.get_description(state.game_data)
        upgraded_desc = trait.get_upgraded_description(state.game_data)

        tooltip_lines = []
        if description:
            if upgraded_desc:
                tooltip_lines.append(f"Base: {description}")
            else:
                tooltip_lines.append(description)
        if upgraded_desc:
            tooltip_lines.append(f"Upgraded: {upgraded_desc}")
        tooltip_text = "\n".join(tooltip_lines) if tooltip_lines else "No description"

        with dpg.table_row(parent="universals_table"):
            trait_text = dpg.add_text(display_name)
            with dpg.tooltip(trait_text):
                dpg.add_text(tooltip_text)
            dpg.add_text(trait.category.display_name, color=(150, 150, 150))
            dpg.add_input_float(
                tag=f"universal_{i}_weight",
                default_value=universal.weight_ens,
                min_value=0.5,
                max_value=10.0,
                step=1.0,
                format="%.0f",
                width=80,
                callback=on_universal_weight_changed,
                user_data=(i, state),
            )
            dpg.add_button(
                label="X",
                width=25,
                callback=on_remove_universal,
                user_data=(i, state),
            )


def _update_builds_display(state: AppState) -> None:
    """Update the builds display."""
    container = "builds_container"
    if not dpg.does_item_exist(container):
        return

    open_states = {
        build.id.hex: dpg.get_value(f"build_{build.id.hex}_header")
        for build in state.target_builds
        if dpg.does_item_exist(f"build_{build.id.hex}_header")
    }

    dpg.delete_item(container, children_only=True)

    for build in state.target_builds:
        bid_hex = build.id.hex
        header_tag = f"build_{bid_hex}_header"
        with dpg.collapsing_header(
            label=_build_header_label(build),
            tag=header_tag,
            parent=container,
            default_open=open_states.get(bid_hex, False),
        ):
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=f"build_{bid_hex}_name",
                    default_value=build.name,
                    width=150,
                    callback=on_build_name_edited,
                    user_data=(build.id, state),
                )
                dpg.add_input_float(
                    tag=f"build_{bid_hex}_synergy",
                    default_value=build.synergy_bonus_ens,
                    step=1.0,
                    min_value=0.0,
                    max_value=100.0,
                    width=80,
                    format="%.0f",
                    callback=on_build_synergy_edited,
                    user_data=(build.id, state),
                )
                dpg.add_button(
                    label="X",
                    width=25,
                    callback=on_remove_build,
                    user_data=(build.id, state),
                )

            dpg.add_spacer(height=5)

            dpg.add_text("Requirements:", color=(150, 150, 150))

            req_table = f"build_{bid_hex}_req_table"
            dpg.add_table(
                tag=req_table,
                borders_innerH=False,
                borders_innerV=False,
                borders_outerV=False,
                header_row=False,
            )
            dpg.add_table_column(width_stretch=True, parent=req_table)
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=120, parent=req_table
            )
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=80, parent=req_table
            )
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=25, parent=req_table
            )

            for j, tw in enumerate(build.requirements):
                display_name = tw.trait.get_display_name(state.game_data)
                description = tw.trait.get_description(state.game_data)
                upgraded_desc = tw.trait.get_upgraded_description(state.game_data)
                tooltip_lines = []
                if description:
                    if upgraded_desc:
                        tooltip_lines.append(f"Base: {description}")
                    else:
                        tooltip_lines.append(description)
                if upgraded_desc:
                    tooltip_lines.append(f"Upgraded: {upgraded_desc}")
                tooltip_text = (
                    "\n".join(tooltip_lines) if tooltip_lines else "No description"
                )
                with dpg.table_row(parent=req_table):
                    trait_text = dpg.add_text(f"  {display_name}")
                    with dpg.tooltip(trait_text):
                        dpg.add_text(tooltip_text)
                    dpg.add_text(tw.trait.category.display_name, color=(150, 150, 150))
                    dpg.add_input_float(
                        tag=f"build_{bid_hex}_req_{j}_weight",
                        default_value=tw.weight_ens,
                        min_value=0.5,
                        max_value=10.0,
                        step=1.0,
                        format="%.0f",
                        width=80,
                        callback=on_build_trait_weight_changed,
                        user_data=(build.id, j, "requirements", state),
                    )
                    dpg.add_button(
                        label="X",
                        width=25,
                        callback=on_remove_build_trait,
                        user_data=(build.id, j, "requirements", state),
                    )
            dpg.add_button(
                label="[+] Add Requirement",
                callback=on_add_build_requirement,
                user_data=(build.id, state),
            )

            dpg.add_spacer(height=5)

            dpg.add_text("Anti-Synergies:", color=(150, 150, 150))

            anti_table = f"build_{bid_hex}_anti_table"
            dpg.add_table(
                tag=anti_table,
                borders_innerH=False,
                borders_innerV=False,
                borders_outerV=False,
                header_row=False,
            )
            dpg.add_table_column(width_stretch=True, parent=anti_table)
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=120, parent=anti_table
            )
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=80, parent=anti_table
            )
            dpg.add_table_column(
                width_fixed=True, init_width_or_weight=25, parent=anti_table
            )

            for j, tw in enumerate(build.anti_synergies):
                display_name = tw.trait.get_display_name(state.game_data)
                description = tw.trait.get_description(state.game_data)
                upgraded_desc = tw.trait.get_upgraded_description(state.game_data)
                tooltip_lines = []
                if description:
                    if upgraded_desc:
                        tooltip_lines.append(f"Base: {description}")
                    else:
                        tooltip_lines.append(description)
                if upgraded_desc:
                    tooltip_lines.append(f"Upgraded: {upgraded_desc}")
                tooltip_text = (
                    "\n".join(tooltip_lines) if tooltip_lines else "No description"
                )
                with dpg.table_row(parent=anti_table):
                    trait_text = dpg.add_text(f"  {display_name}")
                    with dpg.tooltip(trait_text):
                        dpg.add_text(tooltip_text)
                    dpg.add_text(tw.trait.category.display_name, color=(150, 150, 150))
                    dpg.add_input_float(
                        tag=f"build_{bid_hex}_anti_{j}_weight",
                        default_value=tw.weight_ens,
                        min_value=0.5,
                        max_value=10.0,
                        step=1.0,
                        format="%.0f",
                        width=80,
                        callback=on_build_trait_weight_changed,
                        user_data=(build.id, j, "anti_synergies", state),
                    )
                    dpg.add_button(
                        label="X",
                        width=25,
                        callback=on_remove_build_trait,
                        user_data=(build.id, j, "anti_synergies", state),
                    )
            dpg.add_button(
                label="[+] Add Anti-Synergy",
                callback=on_add_build_anti_synergy,
                user_data=(build.id, state),
            )


def init_traits_lists(state: AppState) -> None:
    """Initialize the trait filter listboxes with available traits from cats."""
    for category in TraitCategory:
        traits = state.get_available_traits(category)
        formatted = [_format_trait_for_listbox(t, state.game_data) for t in traits]
        listbox_tag = f"universal_{category.value}_listbox"
        if dpg.does_item_exist(listbox_tag):
            dpg.configure_item(listbox_tag, items=formatted)

    update_traits_display(state)


def on_universal_filter(
    sender: int, app_data: str, user_data: tuple[AppState, str, str]
) -> None:
    """Filter universals listbox with fuzzy matching."""
    state, listbox_tag, category = user_data
    filter_text = app_data or ""

    traits = state.get_available_traits(category)
    filtered = trait_substring_match(filter_text, traits, state.game_data)
    formatted = [_format_trait_for_listbox(t, state.game_data) for t in filtered]

    dpg.configure_item(listbox_tag, items=formatted)


def on_add_universal(sender: int | None, app_data: Any, user_data: AppState) -> None:
    """Add selected trait to universals from the shared trait selector."""
    state = user_data
    category, trait_key = _get_active_listbox_selection()

    if category and trait_key:
        state.universals.append(
            TraitWeight(trait=create_trait(category, trait_key), weight_ens=1.0)
        )
        state.save()
        update_traits_display(state)


def on_remove_universal(
    sender: int, app_data: Any, user_data: tuple[int, AppState]
) -> None:
    """Remove a universal from universals."""
    index, state = user_data
    state.universals.pop(index)
    state.save()
    update_traits_display(state)


def on_clear_universals(sender: int, app_data: Any, user_data: AppState) -> None:
    """Clear all universals."""
    user_data.universals.clear()
    user_data.save()
    update_traits_display(user_data)


def on_universal_weight_changed(
    sender: int, app_data: float, user_data: tuple[int, AppState]
) -> None:
    """Handle input_float change for universal trait weight."""
    index, state = user_data
    state.universals[index] = replace(state.universals[index], weight_ens=app_data)
    state.save()


def on_add_build(sender: int, app_data: Any, user_data: AppState) -> None:
    """Add a new target build."""
    state = user_data
    new_build = TargetBuild(
        id=uuid4(),
        name=f"Build {len(state.target_builds) + 1}",
        requirements=(),
        anti_synergies=(),
        synergy_bonus_ens=0.0,
    )
    state.target_builds.append(new_build)
    state.save()
    update_traits_display(state)


def on_remove_build(
    sender: int, app_data: Any, user_data: tuple[UUID, AppState]
) -> None:
    """Remove a target build."""
    build_id, state = user_data
    state.target_builds = [b for b in state.target_builds if b.id != build_id]
    state.save()
    update_traits_display(state)


def _get_active_listbox_selection() -> tuple[TraitCategory | None, str | None]:
    """Get selected trait strictly from the currently visible tab's listbox."""
    active_tab_id = dpg.get_value("trait_selector_tabs")
    if not active_tab_id:
        return None, None

    tab_label = dpg.get_item_label(active_tab_id)
    if not tab_label:
        return None, None
    category_map = {cat.display_name: cat for cat in TraitCategory}
    category = category_map.get(tab_label)
    if not category:
        return None, None

    listbox_tag = f"universal_{category.value}_listbox"
    selected_val = dpg.get_value(listbox_tag)

    if not selected_val:
        items = dpg.get_item_configuration(listbox_tag).get("items", [])
        if items:
            selected_val = items[0]

    if not selected_val:
        return None, None

    actual_key = selected_val.split(" | ")[0].strip()
    return category, actual_key


def on_build_name_edited(
    sender: int, app_data: str, user_data: tuple[UUID, AppState]
) -> None:
    """Handle build name input - update label directly without rebuild."""
    build_id, state = user_data
    new_name = app_data.strip()
    if not new_name:
        return
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    state.target_builds[idx] = replace(state.target_builds[idx], name=new_name)
    state.save()
    _configure_build_header_label(build_id.hex, state.target_builds[idx])


def on_build_synergy_edited(
    sender: int, app_data: float, user_data: tuple[UUID, AppState]
) -> None:
    """Handle build synergy bonus input - update label directly without rebuild."""
    build_id, state = user_data
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    state.target_builds[idx] = replace(
        state.target_builds[idx], synergy_bonus_ens=app_data
    )
    state.save()
    _configure_build_header_label(build_id.hex, state.target_builds[idx])


def on_add_build_requirement(
    sender: int, app_data: Any, user_data: tuple[UUID, AppState]
) -> None:
    """Add selected trait as a requirement to the build."""
    build_id, state = user_data
    category, trait_key = _get_active_listbox_selection()
    if not category or not trait_key:
        return
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    trait = create_trait(category, trait_key)
    tw = TraitWeight(trait=trait, weight_ens=1.0)
    state.target_builds[idx] = replace(
        state.target_builds[idx],
        requirements=state.target_builds[idx].requirements + (tw,),
    )
    state.save()
    update_traits_display(state)


def on_add_build_anti_synergy(
    sender: int, app_data: Any, user_data: tuple[UUID, AppState]
) -> None:
    """Add selected trait as an anti-synergy to the build."""
    build_id, state = user_data
    category, trait_key = _get_active_listbox_selection()
    if not category or not trait_key:
        return
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    trait = create_trait(category, trait_key)
    tw = TraitWeight(trait=trait, weight_ens=1.0)
    state.target_builds[idx] = replace(
        state.target_builds[idx],
        anti_synergies=state.target_builds[idx].anti_synergies + (tw,),
    )
    state.save()
    update_traits_display(state)


def on_remove_build_trait(
    sender: int, app_data: Any, user_data: tuple[UUID, int, str, AppState]
) -> None:
    """Remove a trait from a build's requirements or anti-synergies list."""
    build_id, trait_index, list_type, state = user_data
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    build = state.target_builds[idx]
    target_list = (
        build.requirements if list_type == "requirements" else build.anti_synergies
    )
    if not (0 <= trait_index < len(target_list)):
        return
    if list_type == "requirements":
        state.target_builds[idx] = replace(
            state.target_builds[idx],
            requirements=build.requirements[:trait_index]
            + build.requirements[trait_index + 1 :],
        )
    else:
        state.target_builds[idx] = replace(
            state.target_builds[idx],
            anti_synergies=build.anti_synergies[:trait_index]
            + build.anti_synergies[trait_index + 1 :],
        )
    state.save()
    update_traits_display(state)


def on_build_trait_weight_changed(
    sender: int, app_data: float, user_data: tuple[UUID, int, str, AppState]
) -> None:
    """Handle input_float change for build trait weight."""
    build_id, trait_index, list_type, state = user_data
    idx = _find_build_index(state, build_id)
    if idx is None:
        return
    build = state.target_builds[idx]
    target_list = (
        build.requirements if list_type == "requirements" else build.anti_synergies
    )
    if not (0 <= trait_index < len(target_list)):
        return
    updated_trait = replace(target_list[trait_index], weight_ens=app_data)
    if list_type == "requirements":
        state.target_builds[idx] = replace(
            state.target_builds[idx],
            requirements=build.requirements[:trait_index]
            + (updated_trait,)
            + build.requirements[trait_index + 1 :],
        )
    else:
        state.target_builds[idx] = replace(
            state.target_builds[idx],
            anti_synergies=build.anti_synergies[:trait_index]
            + (updated_trait,)
            + build.anti_synergies[trait_index + 1 :],
        )
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


def on_trait_filter(
    sender: int, app_data: str, user_data: tuple[AppState, str, str]
) -> None:
    """Legacy callback - redirects to universal filter."""
    on_universal_filter(sender, app_data, user_data)


def on_add_trait(
    sender: int | None, app_data: Any, user_data: tuple[AppState, TraitCategory, str]
) -> None:
    """Legacy callback - redirects to add universal."""
    state = user_data[0]
    on_add_universal(sender, app_data, state)


def on_remove_trait(
    sender: int, app_data: Any, user_data: tuple[int, AppState]
) -> None:
    """Legacy callback - redirects to remove universal."""
    on_remove_universal(sender, app_data, user_data)


def on_clear_traits(sender: int, app_data: Any, user_data: AppState) -> None:
    """Legacy callback - redirects to clear universals."""
    on_clear_universals(sender, app_data, user_data)
