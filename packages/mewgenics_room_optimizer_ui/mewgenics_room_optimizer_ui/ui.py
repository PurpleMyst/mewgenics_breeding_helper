"""DearPyGui UI components for room optimizer."""

import traceback
from collections.abc import Callable
from typing import Any

import dearpygui.dearpygui as dpg
from mewgenics_parser import Cat, TraitCategory
from mewgenics_parser.traits import extract_traits_from_cat
from mewgenics_room_optimizer import OptimizationResult, RoomAssignment, RoomType
from mewgenics_scorer import ScoringPreferences, TraitRequirement

from .themes import build_themes
from .colors import (
    COLOR_DANGER,
    COLOR_EY_TEAL,
    COLOR_HIGH_RISK_ROW,
    COLOR_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
)
from .components.inspector.base import build_inspector_section, clear_inspector
from .components.inspector.cat import (
    on_all_cats_cat_selected,
    on_cat_selected,
)
from .components.inspector.pair import on_pair_selected
from .components.traits import init_traits_lists, on_add_trait, build_traits_section
from .helpers import get_favorable_trait_names, get_pair_summary_data, trait_substring_match
from .state import AppState

LOCATION_COL_WIDTH = 125


def render_cat_table_rows(
    cats: list[Cat],
    state: AppState,
    parent_table_tag: str,
    show_location: bool = True,
    is_ey_check: bool = False,
    eternal_youth_cats: list[Cat] | None = None,
    name_callback: Callable | None = None,
    row_callback: Callable | None = None,
    row_tag_prefix: str = "row",
) -> None:
    """Universal renderer for cat table rows to enforce consistent UI."""

    for cat in cats:
        if is_ey_check and eternal_youth_cats:
            is_ey = cat in eternal_youth_cats
        else:
            is_ey = cat.has_eternal_youth()

        cat_name = name_callback(cat) if name_callback else (cat.name or "Unnamed")

        sex_display = (
            cat.gender.value if hasattr(cat.gender, "value") else str(cat.gender)
        )
        age = cat.age if cat.age is not None else 0
        age = min(age, 100)
        age_display = f"{age} [EY]" if is_ey else str(age)

        assigned_room = _get_assigned_room_key(cat.db_key, state.results)
        current_room = cat.room
        if assigned_room is None:
            loc_color = COLOR_WARNING
        elif current_room == assigned_room:
            loc_color = COLOR_SUCCESS
        else:
            loc_color = COLOR_DANGER

        stat_values = cat.stat_total
        total = sum(stat_values)

        favorable_names = get_favorable_trait_names(
            cat, state.trait_requirements, state.game_data
        )
        trait_display = ", ".join(favorable_names)

        callback = row_callback or on_cat_selected
        user_data = (cat, state)
        tag = f"{row_tag_prefix}_{parent_table_tag}_{cat.db_key}"

        with dpg.table_row(parent=parent_table_tag):
            dpg.add_selectable(
                label=cat_name,
                span_columns=True,
                callback=callback,
                user_data=user_data,
                tag=tag,
            )

            dpg.add_text(str(sex_display))
            dpg.add_text(age_display)

            if show_location:
                display_room = (
                    current_room if current_room is not None else "Unassigned"
                )
                dpg.add_text(cat.room_display or display_room, color=loc_color)

            for sv in stat_values:
                dpg.add_text(str(sv))
            dpg.add_text(str(total))
            dpg.add_text(
                trait_display, color=COLOR_SUCCESS if favorable_names else COLOR_MUTED
            )


def substring_match(query: str, choices: list[str]) -> list[str]:
    """Return items containing query as substring (case-insensitive)."""
    if not query:
        return choices
    return [c for c in choices if query.casefold() in c.casefold()]


def build_ui(state: AppState) -> None:
    """Build all DPG UI components."""

    with dpg.handler_registry():
        dpg.add_key_press_handler(
            dpg.mvKey_Return, callback=on_global_enter, user_data=state
        )

    with dpg.window(tag="main_window", label="Breeding Helper", width=1200, height=700):
        build_menu_bar(state)
        build_toolbar(state)

        with dpg.group(horizontal=True):
            with dpg.child_window(width=450, border=False):
                build_saves_section(state)
                build_room_config_section(state)
                build_params_section(state)
                build_traits_section(state)

            with dpg.child_window(border=False):
                with dpg.tab_bar():
                    with dpg.tab(label="Results"):
                        build_results_tab(state)
                    with dpg.tab(label="All Cats"):
                        build_all_cats_tab(state)

                build_inspector_section(state)

    build_themes()

    scan_and_load_saves(user_data=state)


def build_menu_bar(state: AppState) -> None:
    """Build the menu bar."""
    with dpg.menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(
                label="Reload Saves", callback=scan_and_load_saves, user_data=state
            )
            dpg.add_menu_item(
                label="Save Config", callback=save_config_callback, user_data=state
            )
            dpg.add_menu_item(label="Exit", callback=exit_callback)


def build_saves_section(state: AppState) -> None:
    """Build the saves selection section."""
    with dpg.collapsing_header(label="Available Saves", default_open=False):
        with dpg.child_window(height=100, border=True, tag="saves_section"):
            dpg.add_listbox(
                tag="saves_listbox",
                callback=on_save_selected,
                user_data=state,
                width=-1,
            )


def build_toolbar(state: AppState) -> None:
    """Build the toolbar area."""
    with dpg.group(horizontal=True):
        dpg.add_text(
            "No save loaded"
            if not state.last_save_path
            else f"Loaded: {state.last_save_path}",
            tag="status_text",
        )
        dpg.add_text("|")
        dpg.add_text(f"Cats: {len(state.cats)}", tag="cat_count_text")
        dpg.add_button(
            label="Calculate Optimal Distribution",
            tag="optimize_button",
            callback=run_optimization,
            user_data=state,
            enabled=False,
        )


def build_room_config_section(state: AppState) -> None:
    """Build the room configuration section."""
    with dpg.collapsing_header(label="Room Configuration", default_open=False):
        with dpg.child_window(height=180, border=True, tag="room_config_section"):
            with dpg.table(
                tag="room_config_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                dpg.add_table_column(label="Room Key")
                dpg.add_table_column(label="Type")
                dpg.add_table_column(label="Max Cats")
                dpg.add_table_column(label="Base Stim")

            room_types = ["breeding", "fighting", "general", "none"]
            for room in state.room_configs:
                with dpg.table_row(parent="room_config_table"):
                    dpg.add_text(room.display_name, tag=f"room_name_{room.key}")
                    dpg.add_combo(
                        room_types,
                        default_value=room.room_type.value,
                        tag=f"room_type_{room.key}",
                        width=80,
                        callback=on_room_config_changed,
                        user_data=state,
                    )
                    max_cats_val = "" if room.max_cats is None else str(room.max_cats)
                    dpg.add_input_text(
                        default_value=max_cats_val,
                        tag=f"room_max_{room.key}",
                        width=80,
                        hint="empty=unlimited",
                        callback=on_room_config_changed,
                        user_data=state,
                    )
                    dpg.add_input_text(
                        default_value=str(room.base_stim),
                        tag=f"room_stim_{room.key}",
                        width=80,
                        callback=on_room_config_changed,
                        user_data=state,
                    )


def build_params_section(state: AppState) -> None:
    """Build the optimization parameters section."""
    with dpg.collapsing_header(label="Optimization Parameters", default_open=True):
        with dpg.child_window(height=180, border=True, tag="params_section"):
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="Min Stats",
                    tag="min_stats",
                    default_value=state.min_stats,
                    width=100,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Minimum total base stats required for a cat to be considered for breeding."
                    )
                dpg.add_slider_float(
                    label="Max Risk %",
                    tag="max_risk",
                    default_value=state.max_risk
                    * 100,  # Convert probability to percentage for display
                    max_value=100.0,
                    width=200,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Maximum inbreeding risk percentage allowed for breeding pairs."
                    )
            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    label="Minimize Variance",
                    tag="minimize_variance",
                    default_value=state.minimize_variance,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Prioritizes consistent stat lines across offspring rather than gambling for single high-stat spikes."
                    )
                dpg.add_checkbox(
                    label="Avoid Lovers",
                    tag="avoid_lovers",
                    default_value=state.avoid_lovers,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Excludes pairs that are mutual lovers to prevent relationship conflicts."
                    )
            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    label="Prefer High Libido",
                    tag="prefer_high_libido",
                    default_value=state.prefer_high_libido,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Favors pairs with higher combined libido for faster breeding."
                    )
                dpg.add_checkbox(
                    label="Prefer High Charisma",
                    tag="prefer_high_charisma",
                    default_value=state.prefer_high_charisma,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Favors pairs with higher combined charisma for better breeding odds."
                    )

            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    label="Maximize Throughput",
                    tag="maximize_throughput",
                    default_value=state.maximize_throughput,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Favors having many distinct pairs to maximize the number of offspring produced per generation."
                    )

            with dpg.group(horizontal=True):
                dpg.add_text("SA Temperature:")
                dpg.add_input_float(
                    tag="sa_temperature",
                    default_value=100.0,
                    min_value=1.0,
                    max_value=500.0,
                    step=1.0,
                    width=100,
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Cooling Rate:")
                dpg.add_input_float(
                    tag="sa_cooling_rate",
                    default_value=0.95,
                    min_value=0.8,
                    max_value=0.99,
                    step=0.01,
                    width=100,
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Neighbors/Temp:")
                dpg.add_input_int(
                    tag="sa_neighbors",
                    default_value=200,
                    min_value=50,
                    max_value=1000,
                    step=10,
                    width=100,
                )


def on_param_changed(sender: int, app_data: Any, user_data: AppState) -> None:
    """Handle parameter change - update state and auto-save."""
    tag = dpg.get_item_alias(sender) or dpg.get_item_label(sender)
    if not tag:
        tag = sender

    if tag == "min_stats":
        user_data.min_stats = app_data
    elif tag == "max_risk":
        user_data.max_risk = app_data / 100.0  # Convert percentage to probability
    elif tag == "minimize_variance":
        user_data.minimize_variance = app_data
    elif tag == "avoid_lovers":
        user_data.avoid_lovers = app_data
    elif tag == "prefer_high_libido":
        user_data.prefer_high_libido = app_data
    elif tag == "prefer_high_charisma":
        user_data.prefer_high_charisma = app_data
    elif tag == "maximize_throughput":
        user_data.maximize_throughput = app_data

    user_data.save()


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


def _cat_has_favorable_trait(
    cat: Cat, trait_requirements: list[TraitRequirement]
) -> bool:
    """Check if cat has any favorable trait from planner."""
    return any(req.trait.is_possessed_by(cat) for req in trait_requirements)


def _get_assigned_room_key(
    cat_db_key: int, results: OptimizationResult | None
) -> str | None:
    """Get the room key a cat is assigned to in optimization results."""
    if not results:
        return None
    for room in results.rooms:
        if any(c.db_key == cat_db_key for c in room.cats):
            return room.room.key
    return None


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

    name_filtered = substring_match(name_filter, [c.name or "" for c in cats])
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

    def all_cats_row_callback(
        sender: int, app_data: bool, user_data: tuple[Cat, AppState]
    ) -> None:
        cat, state = user_data
        on_all_cats_cat_selected(sender, app_data, (cat.db_key, state))

    render_cat_table_rows(
        cats=filtered_cats,
        state=state,
        parent_table_tag=table,
        row_callback=all_cats_row_callback,
        row_tag_prefix="all_cats_row",
    )


def build_results_tab(state: AppState) -> None:
    """Build the results tab with room summary and details."""
    with dpg.collapsing_header(label="Results", default_open=True):
        with dpg.child_window(height=200, border=True, tag="results_section"):
            with dpg.table(
                tag="results_table",
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                dpg.add_table_column(label="Room")
                dpg.add_table_column(label="Cats")
                dpg.add_table_column(label="Pairs")
                dpg.add_table_column(label="EY")
                dpg.add_table_column(label="Avg Quality")
                dpg.add_table_column(label="Risk %")

            dpg.add_text("Run optimization to see results", tag="results_placeholder")

    with dpg.collapsing_header(label="Room Details", default_open=True):
        with dpg.child_window(height=200, border=True, tag="details_section"):
            dpg.add_text(
                "Select a room from results to see details", tag="details_placeholder"
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
                dpg.add_table_column(label="Traits", width_stretch=True)

            dpg.add_text("Load a save to see cats", tag="all_cats_placeholder")

    if state.cats:
        update_all_cats_table(state)


def on_global_enter(sender: int, app_data: Any, user_data: AppState) -> None:
    """Check which filter is active when Enter is pressed and trigger add."""
    if dpg.is_item_active("body_part_filter"):
        on_add_trait(
            None, None, (user_data, TraitCategory.BODY_PART, "body_part_listbox")
        )
    elif dpg.is_item_active("passive_filter"):
        on_add_trait(
            None, None, (user_data, TraitCategory.PASSIVE_ABILITY, "passive_listbox")
        )
    elif dpg.is_item_active("ability_filter"):
        on_add_trait(
            None, None, (user_data, TraitCategory.ACTIVE_ABILITY, "ability_listbox")
        )


def scan_and_load_saves(
    sender: int | None = None, app_data: Any = None, user_data: AppState | None = None
) -> None:
    """Scan for saves and auto-load the newest."""
    from mewgenics_parser import find_save_files, parse_save

    save_paths = find_save_files()
    save_names = [s.split("\\")[-1].split("/")[-1] for s in save_paths]
    if isinstance(sender, AppState):
        state = sender
    elif isinstance(app_data, AppState):
        state = app_data
    elif isinstance(user_data, AppState):
        state = user_data
    else:
        raise ValueError("No AppState provided to scan_and_load_saves")

    dpg.configure_item("saves_listbox", items=save_names)

    if save_paths:
        newest = save_paths[0]
        try:
            save_data = parse_save(newest)
            state.cats = save_data.cats
            state.last_save_path = newest
            state.results = None

            dpg.set_value("saves_listbox", save_names[0])
            dpg.set_value(
                "status_text", f"Loaded: {newest.split('\\')[-1].split('/')[-1]}"
            )
            alive = len(state.alive_cats)
            dpg.set_value(
                "cat_count_text",
                f"Cats: {len(state.cats)} ({alive} in house)",
            )
            dpg.configure_item("optimize_button", enabled=True)
            clear_results_table()
            init_traits_lists(state)
            update_all_cats_table(state)
        except Exception as e:
            with dpg.window(label="Error", id="error_modal", modal=True):
                dpg.add_text("Error loading save!")
                dpg.add_separator()
                dpg.add_text(str(e))
                dpg.add_input_text(
                    multiline=True, readonly=True, default_value=traceback.format_exc()
                )
                dpg.add_button(
                    label="Close", callback=lambda: dpg.delete_item("error_modal")
                )
    else:
        dpg.set_value("status_text", "No saves found")
        dpg.set_value("cat_count_text", "Cats: 0")


def on_save_selected(sender: int, app_data: str, user_data: AppState) -> None:
    """Handle save selection from listbox."""
    from mewgenics_parser import find_save_files, parse_save

    selected_name = app_data
    save_paths = find_save_files()
    save_names = [s.split("\\")[-1].split("/")[-1] for s in save_paths]

    idx = save_names.index(selected_name)
    filepath = save_paths[idx]

    try:
        save_data = parse_save(filepath)
        user_data.cats = save_data.cats
        user_data.last_save_path = filepath
        user_data.results = None

        dpg.set_value("status_text", f"Loaded: {selected_name}")
        alive = len(user_data.alive_cats)
        dpg.set_value(
            "cat_count_text", f"Cats: {len(user_data.cats)} ({alive} in house)"
        )
        dpg.configure_item("optimize_button", enabled=True)
        clear_results_table()
        init_traits_lists(user_data)
        update_all_cats_table(user_data)
    except Exception as e:
        print(f"Error loading save: {e}")


def save_config_callback(sender: int, app_data: Any, user_data: AppState) -> None:
    """Save configuration to disk."""
    user_data.save()


def on_room_config_changed(sender: int, app_data: Any, user_data: AppState) -> None:
    """Handle room config change - auto-save immediately."""
    from mewgenics_room_optimizer import RoomConfig

    is_valid = True

    new_configs = []
    for room in user_data.room_configs:
        new_type_str = dpg.get_value(f"room_type_{room.key}")
        new_max_str = dpg.get_value(f"room_max_{room.key}")
        new_stim_str = dpg.get_value(f"room_stim_{room.key}")

        new_max = None
        if new_max_str.strip():
            try:
                new_max = int(new_max_str)
                dpg.bind_item_theme(f"room_max_{room.key}", 0)
            except ValueError:
                dpg.bind_item_theme(f"room_max_{room.key}", "input_error_theme")
                is_valid = False
        else:
            dpg.bind_item_theme(f"room_max_{room.key}", 0)

        new_stim = 50.0
        if new_stim_str.strip():
            try:
                new_stim = float(new_stim_str)
                dpg.bind_item_theme(f"room_stim_{room.key}", 0)
            except ValueError:
                dpg.bind_item_theme(f"room_stim_{room.key}", "input_error_theme")
                is_valid = False
        else:
            dpg.bind_item_theme(f"room_stim_{room.key}", 0)

        new_configs.append(
            RoomConfig(
                key=room.key,
                room_type=RoomType(new_type_str),
                max_cats=new_max,
                base_stim=new_stim,
            )
        )

    if is_valid:
        user_data.room_configs = new_configs
        user_data.results = None
        user_data.save()
        clear_results_table()
    else:
        dpg.set_value("status_text", "Invalid room config - fix errors and try again")


def exit_callback(sender: int, app_data: Any, user_data: Any) -> None:
    """Exit the application."""
    dpg.destroy_context()


def run_optimization(sender: int, app_data: Any, user_data: AppState) -> None:
    """Run the optimization."""
    from mewgenics_room_optimizer import optimize_sa
    from mewgenics_room_optimizer.types import OptimizationParams
    from mewgenics_scorer import build_ancestor_contribs

    if not user_data.cats:
        return

    dpg.set_value("status_text", "Calculating...")
    dpg.configure_item("optimize_button", enabled=False)
    dpg.render_dearpygui_frame()

    min_stats = dpg.get_value("min_stats")
    max_risk = dpg.get_value("max_risk") / 100.0  # Convert percentage to probability
    avoid_lovers = dpg.get_value("avoid_lovers")

    # SA Parameters
    sa_temp = dpg.get_value("sa_temperature")
    sa_cooling = dpg.get_value("sa_cooling_rate")
    sa_neighbors = dpg.get_value("sa_neighbors")

    # Scoring Preferences
    minimize_variance = dpg.get_value("minimize_variance")
    prefer_low_aggression = dpg.get_value("prefer_low_aggression")
    prefer_high_libido = dpg.get_value("prefer_high_libido")
    prefer_high_charisma = dpg.get_value("prefer_high_charisma")
    maximize_throughput = dpg.get_value("maximize_throughput")

    scoring_prefs = ScoringPreferences(
        minimize_variance=minimize_variance,
        prefer_low_aggression=prefer_low_aggression,
        prefer_high_libido=prefer_high_libido,
        prefer_high_charisma=prefer_high_charisma,
        maximize_throughput=maximize_throughput,
    )

    params = OptimizationParams(
        min_stats=min_stats,
        max_risk=max_risk,
        avoid_lovers=avoid_lovers,
        scoring_prefs=scoring_prefs,
        trait_requirements=user_data.trait_requirements,
        gay_cats_by_id=user_data.gay_cats_by_id,
        sa_temperature=sa_temp,
        sa_cooling_rate=sa_cooling,
        sa_neighbors_per_temp=sa_neighbors,
    )

    ancestor_contribs = build_ancestor_contribs(user_data.cats)
    results = optimize_sa(
        user_data.cats, user_data.room_configs, params, ancestor_contribs
    )
    user_data.results = results

    dpg.set_value("status_text", "Optimization Complete")
    dpg.configure_item("optimize_button", enabled=True)

    update_results_table(results, user_data)


def update_results_table(results: OptimizationResult, state: AppState) -> None:
    """Update the results table with optimization results."""
    clear_results_table()
    clear_details_section()
    clear_inspector(state)
    dpg.hide_item("results_placeholder")

    for i, room in enumerate(results.rooms):
        avg_quality = 0.0
        avg_risk = 0.0
        if room.pairs:
            avg_quality = sum(p.quality for p in room.pairs) / len(room.pairs)
            avg_risk = sum(
                p.factors.combined_malady_chance * 100 for p in room.pairs
            ) / len(room.pairs)

        row_color = COLOR_HIGH_RISK_ROW if avg_risk > 15 else (0, 0, 0, 0)

        with dpg.table_row(parent="results_table"):
            dpg.add_selectable(
                label=room.room.display_name,
                span_columns=True,
                callback=on_room_selected,
                user_data=(room.room.key, state),
                tag=f"row_selectable_{room.room.key}",
            )
            dpg.add_text(str(len(room.cats)))
            dpg.add_text(str(len(room.pairs)))
            ey_count = len(room.eternal_youth_cats)
            dpg.add_text(
                f"{ey_count}",
                color=COLOR_EY_TEAL if ey_count > 0 else COLOR_MUTED,
            )
            dpg.add_text(f"{avg_quality:.1f}")
            dpg.add_text(
                f"{avg_risk:2.0f}%",
                color=COLOR_DANGER if avg_risk > 15 else COLOR_MUTED,
            )

        if avg_risk > 15:
            dpg.highlight_table_row("results_table", i, row_color)


def clear_results_table() -> None:
    """Clear the results table."""
    table = "results_table"
    if dpg.does_item_exist(table):
        children = dpg.get_item_children(table)
        if children and 1 in children:
            for row in children[1]:  # type: ignore[iterable]
                dpg.delete_item(row)
    dpg.show_item("results_placeholder")


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

                def details_name_callback(cat: Cat) -> str:
                    is_ey = cat in selected_room.eternal_youth_cats
                    cat_name = cat.name or "Unnamed"
                    if is_ey:
                        return f"{cat_name} [EY]"
                    return cat_name

                render_cat_table_rows(
                    cats=all_cats,
                    state=state,
                    parent_table_tag="cats_detail_table",
                    is_ey_check=True,
                    eternal_youth_cats=list(selected_room.eternal_youth_cats),
                    name_callback=details_name_callback,
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
                    assigned_room = _get_assigned_room_key(cat.db_key, state.results)

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
