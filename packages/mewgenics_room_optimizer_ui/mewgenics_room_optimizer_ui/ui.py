"""DearPyGui UI components for room optimizer."""

import dearpygui.dearpygui as dpg
from mewgenics_parser.trait_dictionary import normalize_trait_name
from mewgenics_room_optimizer import RoomType
from mewgenics_scorer import ScoringPreferences

from .state import AppState

LOCATION_COL_WIDTH = 125


def substring_match(query: str, choices: list[str]) -> list[str]:
    """Return items containing query as substring (case-insensitive)."""
    if not query:
        return choices
    query_lower = query.lower()
    return [c for c in choices if query_lower in c.lower()]


def build_ui(state: AppState):
    """Build all DPG UI components."""

    with dpg.handler_registry():
        dpg.add_key_press_handler(
            dpg.mvKey_Return, callback=on_global_enter, user_data=state
        )

    with dpg.window(tag="main_window", label="Room Optimizer", width=1200, height=700):
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

    scan_and_load_saves(state)


def build_menu_bar(state: AppState):
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


def build_saves_section(state: AppState):
    """Build the saves selection section."""
    with dpg.collapsing_header(label="Available Saves", default_open=False):
        with dpg.child_window(height=100, border=True, tag="saves_section"):
            dpg.add_listbox(
                tag="saves_listbox",
                callback=on_save_selected,
                user_data=state,
                width=-1,
            )


def build_toolbar(state: AppState):
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


def build_room_config_section(state: AppState):
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
                dpg.add_table_column(label="Display Name")
                dpg.add_table_column(label="Type")
                dpg.add_table_column(label="Max Cats")
                dpg.add_table_column(label="Base Stim")

            room_types = ["breeding", "fighting", "general", "none"]
            for room in state.room_configs:
                with dpg.table_row(parent="room_config_table"):
                    dpg.add_text(room.key, tag=f"room_key_{room.key}")
                    dpg.add_input_text(
                        default_value=room.display_name,
                        tag=f"room_name_{room.key}",
                        width=120,
                        callback=on_room_config_changed,
                        user_data=state,
                    )
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


def build_params_section(state: AppState):
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
                dpg.add_checkbox(
                    label="Maximize Throughput",
                    tag="maximize_throughput",
                    default_value=state.maximize_throughput,
                    callback=on_param_changed,
                    user_data=state,
                )
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Prioritizes pairing cats in rooms with higher throughput caps for faster breeding."
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


def on_param_changed(sender, app_data, user_data: AppState):
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


def build_traits_section(state: AppState):
    """Build the favorable traits selection section."""
    with dpg.collapsing_header(label="Favorable Traits", default_open=True):
        with dpg.child_window(border=True, tag="traits_section"):
            with dpg.tab_bar():
                with dpg.tab(label="Mutations"):
                    dpg.add_input_text(
                        tag="mutation_filter",
                        hint="Filter...",
                        width=-1,
                        callback=on_mutation_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="mutation_listbox",
                        width=-1,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_mutation, user_data=state
                    )
                with dpg.tab(label="Passives"):
                    dpg.add_input_text(
                        tag="passive_filter",
                        hint="Filter...",
                        width=-1,
                        callback=on_passive_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="passive_listbox",
                        width=-1,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_passive, user_data=state
                    )
                with dpg.tab(label="Abilities"):
                    dpg.add_input_text(
                        tag="ability_filter",
                        hint="Filter...",
                        width=-1,
                        callback=on_ability_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="ability_listbox",
                        width=-1,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_ability, user_data=state
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


def _format_trait_with_description(
    trait_key: str, game_data, max_desc_len: int = 40
) -> str:
    """Format a trait with its description for display in listbox."""
    desc = game_data.ability_descriptions.get(trait_key.lower(), "")
    if desc:
        truncated = desc[:max_desc_len] + "..." if len(desc) > max_desc_len else desc
        return f"{trait_key} | {truncated}"
    return trait_key


def _extract_trait_key(formatted: str) -> str:
    """Extract the actual trait key from a formatted listbox string."""
    return formatted.split(" | ")[0].strip()


def on_mutation_filter(sender, app_data, user_data: AppState):
    """Filter mutations listbox with fuzzy matching."""
    filter_text = app_data or ""
    mutations = user_data.get_available_mutations()
    filtered = substring_match(filter_text, mutations)
    formatted = [
        _format_trait_with_description(m, user_data.game_data) for m in filtered
    ]
    dpg.configure_item("mutation_listbox", items=formatted)


def on_passive_filter(sender, app_data, user_data: AppState):
    """Filter passives listbox with fuzzy matching."""
    filter_text = app_data or ""
    passives = user_data.get_available_passives()
    filtered = substring_match(filter_text, passives)
    formatted = [
        _format_trait_with_description(p, user_data.game_data) for p in filtered
    ]
    dpg.configure_item("passive_listbox", items=formatted)


def on_ability_filter(sender, app_data, user_data: AppState):
    """Filter abilities listbox with fuzzy matching."""
    filter_text = app_data or ""
    abilities = user_data.get_available_abilities()
    filtered = substring_match(filter_text, abilities)
    formatted = [
        _format_trait_with_description(a, user_data.game_data) for a in filtered
    ]
    dpg.configure_item("ability_listbox", items=formatted)


def on_cat_name_filter(sender, app_data, user_data: AppState):
    """Filter All Cats table by name with fuzzy matching."""
    filter_text = app_data or ""
    update_all_cats_table(
        user_data, filter_text, dpg.get_value("cat_trait_filter") or ""
    )


def on_cat_trait_filter(sender, app_data, user_data: AppState):
    """Filter All Cats table by trait with fuzzy matching."""
    filter_text = app_data or ""
    update_all_cats_table(
        user_data, dpg.get_value("cat_name_filter") or "", filter_text
    )


def on_toggle_show_all_cats(sender, app_data, user_data: AppState):
    """Toggle showing non-In-House cats."""
    update_all_cats_table(
        user_data,
        dpg.get_value("cat_name_filter") or "",
        dpg.get_value("cat_trait_filter") or "",
    )


def on_add_mutation(sender, app_data, user_data: AppState):
    """Add selected mutation to favorable traits."""
    selected = dpg.get_value("mutation_listbox")

    if not selected:
        items = dpg.get_item_configuration("mutation_listbox").get("items", [])
        if items:
            selected = items[0]

    if selected:
        from mewgenics_scorer import TraitRequirement

        actual_key = _extract_trait_key(selected)
        user_data.planner_traits.append(
            TraitRequirement(category="mutation", key=actual_key, weight=5.0)
        )
        user_data.save()
        update_traits_display(user_data)


def on_add_passive(sender, app_data, user_data: AppState):
    """Add selected passive to favorable traits."""
    selected = dpg.get_value("passive_listbox")

    if not selected:
        items = dpg.get_item_configuration("passive_listbox").get("items", [])
        if items:
            selected = items[0]

    if selected:
        from mewgenics_scorer import TraitRequirement

        actual_key = _extract_trait_key(selected)
        user_data.planner_traits.append(
            TraitRequirement(category="passive", key=actual_key, weight=5.0)
        )
        user_data.save()
        update_traits_display(user_data)


def on_add_ability(sender, app_data, user_data: AppState):
    """Add selected ability to favorable traits."""
    selected = dpg.get_value("ability_listbox")

    if not selected:
        items = dpg.get_item_configuration("ability_listbox").get("items", [])
        if items:
            selected = items[0]

    if selected:
        from mewgenics_scorer import TraitRequirement

        actual_key = _extract_trait_key(selected)
        user_data.planner_traits.append(
            TraitRequirement(category="ability", key=actual_key, weight=5.0)
        )
        user_data.save()
        update_traits_display(user_data)


def on_clear_traits(sender, app_data, user_data: AppState):
    """Clear all favorable traits."""
    user_data.planner_traits.clear()
    user_data.save()
    update_traits_display(user_data)


def _is_favorable_trait(trait_key: str, planner_traits: list) -> bool:
    """Check if a trait is in the favorable traits list."""
    normalized = normalize_trait_name(trait_key).lower()
    return any(
        normalize_trait_name(t.key).lower() == normalized for t in planner_traits
    )


def on_toggle_gay(sender, app_data, user_data: tuple[int, AppState]):
    """Set gay flag for a cat based on checkbox state."""
    db_key, state = user_data
    state.gay_flags[db_key] = app_data
    state.save()
    cat = next((c for c in state.cats if c.db_key == db_key), None)
    if cat:
        show_cat_detail_window(cat, state)


def on_trait_weight_changed(sender, app_data, user_data: tuple[int, AppState]):
    """Handle trait weight change."""
    index, state = user_data
    new_weight = max(1, min(10, int(app_data)))
    state.planner_traits[index].weight = float(new_weight)
    state.save()


def on_remove_trait(sender, app_data, user_data: tuple[int, AppState]):
    """Remove a trait from favorable traits."""
    index, state = user_data
    state.planner_traits.pop(index)
    state.save()
    update_traits_display(state)


def update_traits_display(state: AppState):
    """Update the selected traits display."""
    container = "selected_traits_container"
    if not dpg.does_item_exist(container):
        return

    dpg.delete_item(container, children_only=True)

    for i, trait in enumerate(state.planner_traits):
        with dpg.group(horizontal=True, parent=container):
            trait_text = dpg.add_text(
                f"[{int(trait.weight):2}] {trait.category}: {trait.key}"
            )

            base_key = trait.key.lower()
            upgraded_key = base_key + "2"

            base_desc = state.game_data.ability_descriptions.get(base_key, "")
            upgraded_desc = state.game_data.ability_descriptions.get(upgraded_key, "")

            tooltip_lines = []
            if base_desc:
                tooltip_lines.append(f"Base: {base_desc}")
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


def _cat_has_favorable_trait(cat, planner_traits: list) -> bool:
    """Check if cat has any favorable trait from planner."""
    for trait in planner_traits:
        norm_trait_key = normalize_trait_name(trait.key).lower()
        if trait.category == "mutation":
            for m in cat.mutations or []:
                if normalize_trait_name(m).lower() == norm_trait_key:
                    return True
        if trait.category == "passive":
            for p in cat.passive_abilities or []:
                if normalize_trait_name(p).lower() == norm_trait_key:
                    return True
        if trait.category == "ability":
            for a in cat.abilities or []:
                if normalize_trait_name(a).lower() == norm_trait_key:
                    return True
    return False


def _get_assigned_room_key(cat_db_key: int, results) -> str | None:
    """Get the room key a cat is assigned to in optimization results."""
    if not results:
        return None
    for room in results.rooms:
        if any(c.db_key == cat_db_key for c in room.cats):
            return room.room.key
    return None


def update_all_cats_table(
    state: AppState, name_filter: str = "", trait_filter: str = ""
):
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
            all_traits = []
            all_traits.extend(cat.mutations or [])
            all_traits.extend(cat.passive_abilities or [])
            all_traits.extend(cat.abilities or [])
            if substring_match(trait_filter, all_traits):
                trait_filtered.append(cat)
        filtered_cats = trait_filtered

    if not filtered_cats:
        dpg.show_item(placeholder)
        return

    dpg.hide_item(placeholder)

    for cat in filtered_cats:
        total_stats = sum(cat.stat_base)
        sex_display = (
            cat.gender.value if hasattr(cat.gender, "value") else str(cat.gender)
        )

        age = cat.age
        if age is None:
            age = 0
        age = min(age, 100)
        if hasattr(cat, "eternal_youth") and cat.eternal_youth:
            age_display = f"{age} [EY]"
        else:
            age_display = str(age)

        status = cat.status if cat.status else "Unknown"

        # Get assigned room and determine location color
        assigned_room = _get_assigned_room_key(cat.db_key, state.results)
        current_room = cat.room
        if assigned_room is None:
            location_color = (255, 200, 100, 255)  # Yellow - not assigned
        elif current_room == assigned_room:
            location_color = (100, 255, 100, 255)  # Green - correct
        else:
            location_color = (255, 100, 100, 255)  # Red - wrong room

        # Get individual stats from total_stats dict
        stats = cat.total_stats
        stat_order = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]
        stat_values = [stats.get(s, 0) for s in stat_order]

        has_fav = _cat_has_favorable_trait(cat, state.planner_traits)
        trait_badge = "[*] " if has_fav else ""

        with dpg.table_row(parent=table):
            dpg.add_selectable(
                label=cat.name,
                span_columns=True,
                callback=on_all_cats_cat_selected,
                user_data=(cat.db_key, state),
                tag=f"all_cats_row_{cat.db_key}",
            )
            dpg.add_text(str(sex_display))
            dpg.add_text(age_display)
            dpg.add_text(cat.room_display or current_room, color=location_color)
            for sv in stat_values:
                dpg.add_text(str(sv))
            dpg.add_text(str(total_stats))
            dpg.add_text(trait_badge)


def on_decrement_weight(sender, app_data, user_data: tuple[int, AppState]):
    """Decrement trait weight."""
    index, state = user_data
    state.planner_traits[index].weight = max(1, state.planner_traits[index].weight - 1)
    state.save()
    update_traits_display(state)


def on_increment_weight(sender, app_data, user_data: tuple[int, AppState]):
    """Increment trait weight."""
    index, state = user_data
    state.planner_traits[index].weight = min(10, state.planner_traits[index].weight + 1)
    state.save()
    update_traits_display(state)


def build_results_tab(state: AppState):
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
                dpg.add_table_column(label="Avg Stats")
                dpg.add_table_column(label="Risk %")

            dpg.add_text("Run optimization to see results", tag="results_placeholder")

    with dpg.collapsing_header(label="Room Details", default_open=True):
        with dpg.child_window(height=200, border=True, tag="details_section"):
            dpg.add_text(
                "Select a room from results to see details", tag="details_placeholder"
            )


def build_all_cats_tab(state: AppState):
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
                dpg.add_table_column(label="Total", width_fixed=True)
                dpg.add_table_column(label="Traits", width_stretch=True)

            dpg.add_text("Load a save to see cats", tag="all_cats_placeholder")

    if state.cats:
        update_all_cats_table(state)


def build_inspector_section(state: AppState):
    """Build the inspector panel with tabs for cat and pair inspection."""
    with dpg.collapsing_header(label="Inspector", default_open=True):
        with dpg.child_window(border=True, tag="inspector_section"):
            dpg.add_tab_bar(tag="inspector_tab_bar")

            with dpg.tab(
                label="Cat", parent="inspector_tab_bar", tag="inspector_cat_tab"
            ):
                dpg.add_text("Select a cat to inspect", tag="inspector_placeholder")
                dpg.add_group(tag="inspector_container")

            with dpg.tab(
                label="Pair", parent="inspector_tab_bar", tag="inspector_pair_tab"
            ):
                dpg.add_text(
                    "Select a pair to view trait inheritance probabilities",
                    tag="inspector_pair_placeholder",
                )
                dpg.add_group(tag="inspector_pair_container")


def build_themes():
    """Build application themes."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (200, 200, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 120, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 140, 220, 255))

    with dpg.theme(tag="input_error_theme"):
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (150, 50, 50, 255))

    dpg.bind_theme(global_theme)


def on_global_enter(sender, app_data, user_data):
    """Check which filter is active when Enter is pressed and trigger add."""
    if dpg.is_item_active("mutation_filter"):
        on_add_mutation(None, None, user_data)
    elif dpg.is_item_active("passive_filter"):
        on_add_passive(None, None, user_data)
    elif dpg.is_item_active("ability_filter"):
        on_add_ability(None, None, user_data)


def scan_and_load_saves(sender=None, app_data=None, user_data: AppState | None = None):
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
            print(f"Error loading save: {e}")
    else:
        dpg.set_value("status_text", "No saves found")
        dpg.set_value("cat_count_text", "Cats: 0")


def init_traits_lists(state: AppState):
    """Initialize the trait filter listboxes with available traits from cats."""
    mutations = state.get_available_mutations()
    passives = state.get_available_passives()
    abilities = state.get_available_abilities()

    formatted_mutations = [
        _format_trait_with_description(m, state.game_data) for m in mutations
    ]
    formatted_passives = [
        _format_trait_with_description(p, state.game_data) for p in passives
    ]
    formatted_abilities = [
        _format_trait_with_description(a, state.game_data) for a in abilities
    ]

    dpg.configure_item("mutation_listbox", items=formatted_mutations)
    dpg.configure_item("passive_listbox", items=formatted_passives)
    dpg.configure_item("ability_listbox", items=formatted_abilities)

    update_traits_display(state)


def on_save_selected(sender, app_data, user_data: AppState):
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


def save_config_callback(sender, app_data, user_data: AppState):
    """Save configuration to disk."""
    user_data.save()


def on_room_config_changed(sender, app_data, user_data: AppState):
    """Handle room config change - auto-save immediately."""
    from mewgenics_room_optimizer import RoomConfig

    is_valid = True

    new_configs = []
    for room in user_data.room_configs:
        new_name = dpg.get_value(f"room_name_{room.key}")
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
                display_name=new_name,
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


def exit_callback(sender, app_data, user_data):
    """Exit the application."""
    dpg.destroy_context()


def run_optimization(sender, app_data, user_data: AppState):
    """Run the optimization."""
    from mewgenics_room_optimizer import optimize_sa
    from mewgenics_room_optimizer.types import OptimizationParams
    from mewgenics_scorer import ScoringPreferences, build_ancestor_contribs

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
        planner_traits=user_data.planner_traits,
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


def update_results_table(results, state):
    """Update the results table with optimization results."""
    clear_results_table()
    clear_details_section()
    clear_inspector(state)
    dpg.hide_item("results_placeholder")

    for i, room in enumerate(results.rooms):
        avg_stats = 0.0
        avg_risk = 0.0
        if room.pairs:
            avg_stats = sum(p.quality for p in room.pairs) / len(room.pairs)
            avg_risk = sum(
                p.factors.combined_malady_chance * 100 for p in room.pairs
            ) / len(room.pairs)

        row_color = (50, 30, 30, 255) if avg_risk > 15 else (0, 0, 0, 0)

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
                color=(100, 200, 255, 255) if ey_count > 0 else (200, 200, 200, 255),
            )
            dpg.add_text(f"{avg_stats:.1f}")
            dpg.add_text(
                f"{avg_risk:.0f}%",
                color=(255, 100, 100, 255) if avg_risk > 15 else (200, 200, 200, 255),
            )

        if avg_risk > 15:
            dpg.highlight_table_row("results_table", i, row_color)


def clear_results_table():
    """Clear the results table."""
    table = "results_table"
    if dpg.does_item_exist(table):
        children = dpg.get_item_children(table)
        if children and 1 in children:
            for row in children[1]:  # type: ignore[iterable]
                dpg.delete_item(row)
    dpg.show_item("results_placeholder")


def clear_details_section():
    """Clear the details section."""
    section = "details_section"
    if dpg.does_item_exist(section):
        children = dpg.get_item_children(section)
        if children and 1 in children:
            for child in children[1]:  # type: ignore[iterable]
                dpg.delete_item(child)


def clear_inspector(state: AppState | None = None):
    """Clear the inspector panel and show placeholder."""
    container = "inspector_container"
    if dpg.does_item_exist(container):
        dpg.delete_item(container, children_only=True)
    dpg.show_item("inspector_placeholder")
    dpg.hide_item(container)

    pair_container = "inspector_pair_container"
    if dpg.does_item_exist(pair_container):
        dpg.delete_item(pair_container, children_only=True)
    dpg.show_item("inspector_pair_placeholder")

    if state is not None:
        state.selected_pair = None
        state.selected_pair_index = None


def on_all_cats_cat_selected(sender, app_data, user_data):
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


def on_room_selected(sender, app_data, user_data):
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


def on_pair_selected(sender, app_data, user_data):
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


def build_details_tabs(selected_room, state):
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
                dpg.add_table_column(label="Badges", width_stretch=True)

                for i, pair in enumerate(selected_room.pairs):
                    name_a = pair.cat_a.name or "Unnamed"
                    name_b = pair.cat_b.name or "Unnamed"
                    disorder = pair.factors.expected_disorder_chance * 100
                    part_defect = pair.factors.expected_part_defect_chance * 100
                    combined = pair.factors.combined_malady_chance * 100
                    risk_color = (
                        (255, 100, 100, 255) if combined > 15 else (100, 255, 100, 255)
                    )

                    combined_traits = set()
                    for cat in (pair.cat_a, pair.cat_b):
                        combined_traits.update(
                            normalize_trait_name(t).lower()
                            for t in (cat.mutations or [])
                        )
                        combined_traits.update(
                            normalize_trait_name(t).lower()
                            for t in (cat.passive_abilities or [])
                        )
                        combined_traits.update(
                            normalize_trait_name(t).lower()
                            for t in (cat.abilities or [])
                        )

                    hits = sum(
                        1
                        for pt in state.planner_traits
                        if normalize_trait_name(pt.key).lower() in combined_traits
                    )
                    total = len(state.planner_traits)

                    with dpg.table_row():
                        dpg.add_selectable(
                            label=f"{name_a} + {name_b}",
                            callback=on_pair_selected,
                            user_data=(i, pair, state),
                            tag=f"pair_selectable_{i}",
                        )
                        dpg.add_text(f"{pair.quality:.1f}")
                        dpg.add_text(
                            f"D:{disorder:2.0f}% P:{part_defect:2.0f}% C:{combined:2.0f}%",
                            color=risk_color,
                        )

                        with dpg.group(horizontal=True):
                            if pair.factors.mutual_lovers:
                                badge = dpg.add_text("[<3]")
                                with dpg.tooltip(badge):
                                    dpg.add_text("Mutual Lovers")
                            libido = getattr(pair.factors, "libido_factor", 0)
                            if libido > 0.6:
                                badge = dpg.add_text("[+]", color=(255, 200, 100, 255))
                                with dpg.tooltip(badge):
                                    dpg.add_text("High Libido")
                            agg = getattr(pair.factors, "aggression_factor", 0)
                            if agg > 0.6:
                                badge = dpg.add_text("[-]", color=(100, 200, 255, 255))
                                with dpg.tooltip(badge):
                                    dpg.add_text("High Aggression")
                            if combined > 10:
                                badge = dpg.add_text("[!]", color=(255, 100, 100, 255))
                                with dpg.tooltip(badge):
                                    dpg.add_text("High Inbreeding Risk")
                            if hits > 0:
                                badge = dpg.add_text("[*]", color=(100, 255, 100, 255))
                                with dpg.tooltip(badge):
                                    dpg.add_text(f"{hits}/{total} Favorable Traits")
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
                dpg.add_table_column(label="Total", width_fixed=True)
                dpg.add_table_column(label="Traits", width_fixed=True)

                for cat in all_cats:
                    is_ey = cat in selected_room.eternal_youth_cats
                    cat_name = cat.name or "Unnamed"
                    if is_ey:
                        cat_name = f"{cat_name} [EY]"
                    total_stats = sum(cat.total_stats.values())
                    age = cat.age if cat.age is not None else "-"

                    # Get assigned room and determine location color
                    assigned_room = _get_assigned_room_key(cat.db_key, state.results)
                    current_room = cat.room
                    if assigned_room is None:
                        location_color = (255, 200, 100, 255)  # Yellow - not assigned
                    elif current_room == assigned_room:
                        location_color = (100, 255, 100, 255)  # Green - correct
                    else:
                        location_color = (255, 100, 100, 255)  # Red - wrong room

                    # Get individual stats from total_stats dict
                    stats = cat.total_stats
                    stat_order = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LCK"]
                    stat_values = [stats.get(s, 0) for s in stat_order]

                    name_color = (
                        (0, 255, 255, 255) if is_ey else (255, 255, 255, 255)
                    )  # Teal for EY

                    has_fav = _cat_has_favorable_trait(cat, state.planner_traits)
                    trait_badge = "[*]" if has_fav else ""

                    with dpg.table_row():
                        dpg.add_selectable(
                            label=cat_name,
                            span_columns=True,
                            callback=on_cat_selected,
                            user_data=(cat, state),
                            tag=f"cat_row_{cat.db_key}",
                        )
                        dpg.add_text(cat.gender)
                        dpg.add_text(str(age))
                        dpg.add_text(
                            cat.room_display or current_room, color=location_color
                        )
                        for sv in stat_values:
                            dpg.add_text(str(sv))
                        dpg.add_text(str(total_stats))
                        dpg.add_text(
                            trait_badge,
                            color=(100, 255, 100, 255)
                            if has_fav
                            else (150, 150, 150, 255),
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
                with dpg.table(
                    tag="misplaced_table",
                    header_row=True,
                    borders_innerH=True,
                    row_background=True,
                ):
                    dpg.add_table_column(label="Name", width_fixed=True)
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
                            dpg.add_text(selected_room.room.display_name)
                            dpg.add_text(item["assigned_room"])
            else:
                dpg.add_text("No misplaced cats in this room")

    # Sandbox tab - simulate breeding pairs
    with dpg.tab(label="Sandbox", parent="details_tab_bar"):
        dpg.add_text("Manually test breeding combinations for this room.")
        dpg.add_separator()

        cat_options = [
            f"{c.name or 'Unnamed'} (ID:{c.db_key})" for c in selected_room.cats
        ]

        if not cat_options:
            dpg.add_text("No cats in this room to simulate.")
        else:
            with dpg.group(horizontal=True):
                dpg.add_combo(
                    items=cat_options,
                    label="Parent A",
                    width=200,
                    callback=on_sandbox_changed,
                    user_data=(selected_room, state, "A"),
                    tag="sandbox_combo_a",
                )
                dpg.add_combo(
                    items=cat_options,
                    label="Parent B",
                    width=200,
                    callback=on_sandbox_changed,
                    user_data=(selected_room, state, "B"),
                    tag="sandbox_combo_b",
                )

            dpg.add_separator()
            dpg.add_group(tag="sandbox_results_container")


def show_pair_detail_window(pair, state):
    """Show pair details in the inspector panel with trait inheritance probabilities."""
    from mewgenics_scorer import calculate_trait_probability

    container = "inspector_pair_container"
    if not dpg.does_item_exist(container):
        return

    dpg.hide_item("inspector_pair_placeholder")
    dpg.show_item(container)

    dpg.delete_item(container, children_only=True)

    with dpg.group(parent=container):
        name_a = pair.cat_a.name or "Unnamed"
        name_b = pair.cat_b.name or "Unnamed"
        dpg.add_text(f"Pair: {name_a} + {name_b}", tag="pair_names")

        disorder = pair.factors.expected_disorder_chance * 100
        part_defect = pair.factors.expected_part_defect_chance * 100
        combined = pair.factors.combined_malady_chance * 100
        risk_color = (255, 100, 100, 255) if combined > 15 else (100, 255, 100, 255)

        dpg.add_text(
            f"Quality: {pair.quality:.1f} | Disorder: {disorder:.0f}% | Part Defect: {part_defect:.0f}% | Combined: {combined:.0f}%",
            color=risk_color,
        )

        if state.planner_traits:
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

                for trait in state.planner_traits:
                    prob_result = calculate_trait_probability(
                        trait, pair.cat_a, pair.cat_b, stimulation
                    )

                    if prob_result.probability >= 0.5:
                        color = (100, 255, 100, 255)
                    elif prob_result.probability >= 0.25:
                        color = (255, 200, 100, 255)
                    else:
                        color = (255, 100, 100, 255)

                    with dpg.table_row():
                        dpg.add_text(trait.key)
                        dpg.add_text(trait.category)
                        dpg.add_text(
                            f"{prob_result.probability * 100:.1f}%", color=color
                        )
                        dpg.add_text(prob_result.parent_source)

            hits = sum(1 for p in pair.factors.trait_probabilities if p.probability > 0)
            ev = (
                sum(
                    p.probability * p.trait.weight
                    for p in pair.factors.trait_probabilities
                )
                * 5.0
            )
            total = len(state.planner_traits)
            if ev >= 1:
                dpg.add_text(
                    f"[* EV: {ev:.2f} from {hits}/{total} traits]",
                    color=(100, 255, 100, 255),
                )
        else:
            dpg.add_text("No favorable traits configured", color=(150, 150, 150, 255))


def on_cat_selected(sender, app_data, user_data):
    """Handle cat selection - show detail window with radio behavior."""
    cat, state = user_data

    if (
        state.selected_cat_db_key is not None
        and state.selected_cat_db_key != cat.db_key
    ):
        old_item = f"cat_row_{state.selected_cat_db_key}"
        if dpg.does_item_exist(old_item):
            dpg.set_value(old_item, False)

    state.selected_cat_db_key = cat.db_key

    show_cat_detail_window(cat, state)


def show_cat_detail_window(cat, state):
    """Show cat details in the inspector panel."""
    from mewgenics_parser.constants import STAT_NAMES

    container = "inspector_container"
    if not dpg.does_item_exist(container):
        return

    if dpg.does_item_exist("inspector_tab_bar"):
        dpg.set_value("inspector_tab_bar", "inspector_cat_tab")

    dpg.hide_item("inspector_placeholder")
    dpg.show_item(container)

    dpg.delete_item(container, children_only=True)

    with dpg.group(parent=container):
        room_display = cat.room or "Unknown"
        if cat.room:
            for rc in state.room_configs:
                if rc.key == cat.room:
                    room_display = rc.display_name
                    break

        with dpg.table(
            tag="bio_table",
            header_row=False,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
        ):
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)
            dpg.add_table_column(width_fixed=True)

            with dpg.table_row():
                lover_names = []
                for lover in cat.lovers or []:
                    if lover is None:
                        lover_names.append("Unknown")
                    else:
                        name = lover.name or "Unnamed"
                        if lover.status and lover.status != "In House":
                            name = f"{name} ({lover.status})"
                        lover_names.append(name)
                lovers_str = ", ".join(lover_names) if lover_names else "-"

                hater_names = []
                for hater in cat.haters or []:
                    if hater is None:
                        hater_names.append("Unknown")
                    else:
                        name = hater.name or "Unnamed"
                        if hater.status and hater.status != "In House":
                            name = f"{name} ({hater.status})"
                        hater_names.append(name)
                haters_str = ", ".join(hater_names) if hater_names else "-"

                dpg.add_text(f"Name: {cat.name or 'Unnamed'}")
                dpg.add_text(f"Gender: {cat.gender}")
                dpg.add_text(f"Age: {cat.age if cat.age is not None else 'Unknown'}")
                dpg.add_text(f"Status: {cat.status}")
                dpg.add_text(f"Room: {room_display}")
                dpg.add_text(f"Lovers: {lovers_str}", color=(255, 150, 200, 255))
                dpg.add_text(f"Haters: {haters_str}", color=(255, 100, 100, 255))

        is_gay = state.gay_flags.get(cat.db_key, False)
        dpg.add_checkbox(
            label="Same-Sex Breeding Preference",
            default_value=is_gay,
            callback=on_toggle_gay,
            user_data=(cat.db_key, state),
        )

        with dpg.group(horizontal=True):
            for i, stat in enumerate(cat.stat_base):
                dpg.add_text(f"{STAT_NAMES[i]}: {stat}")

        dpg.add_separator()

        with dpg.tree_node(
            label=f"Active Abilities ({len(cat.abilities or [])})", default_open=True
        ):
            for ab in cat.abilities or []:
                desc = state.game_data.ability_descriptions.get(
                    ab.lower(), "No description"
                )
                is_fav = _is_favorable_trait(ab, state.planner_traits)
                color = (100, 255, 100, 255) if is_fav else (200, 200, 200, 255)
                prefix = "[*] " if is_fav else "  "
                dpg.add_text(f"{prefix}{ab}", color=color)
                if desc:
                    dpg.add_text(f"    {desc}", color=(180, 180, 180, 255))

        with dpg.tree_node(
            label=f"Passive Abilities ({len(cat.passive_abilities or [])})",
            default_open=True,
        ):
            for ab in cat.passive_abilities or []:
                desc = state.game_data.ability_descriptions.get(
                    ab.lower(), "No description"
                )
                is_fav = _is_favorable_trait(ab, state.planner_traits)
                color = (100, 255, 100, 255) if is_fav else (200, 200, 200, 255)
                prefix = "[*] " if is_fav else "  "
                dpg.add_text(f"{prefix}{ab}", color=color)
                if desc:
                    dpg.add_text(f"    {desc}", color=(180, 180, 180, 255))

        with dpg.tree_node(
            label=f"Mutations ({len(cat.mutations or [])})", default_open=True
        ):
            for mut in cat.mutations or []:
                is_fav = _is_favorable_trait(mut, state.planner_traits)
                color = (100, 255, 100, 255) if is_fav else (200, 200, 200, 255)
                prefix = "[*] " if is_fav else "  "
                dpg.add_text(f"{prefix}{mut}", color=color)


def on_sandbox_changed(sender, app_data, user_data):
    """Handle sandbox dropdown changes."""
    import re

    from mewgenics_room_optimizer import score_pair
    from mewgenics_room_optimizer.types import OptimizationParams
    from mewgenics_scorer import (
        build_ancestor_contribs,
        can_breed,
        is_hater_conflict,
        is_lover_conflict,
    )

    selected_room, state, parent_slot = user_data
    container = "sandbox_results_container"

    if not app_data:
        return

    match = re.search(r"\(ID:(\d+)\)", app_data)
    if not match:
        return

    db_key = int(match.group(1))

    if parent_slot == "A":
        state.sim_cat_a_key = db_key
    else:
        state.sim_cat_b_key = db_key

    if state.sim_cat_a_key is None or state.sim_cat_b_key is None:
        return

    dpg.delete_item(container, children_only=True)

    cat_a = next(
        (c for c in selected_room.cats if c.db_key == state.sim_cat_a_key), None
    )
    cat_b = next(
        (c for c in selected_room.cats if c.db_key == state.sim_cat_b_key), None
    )

    if not cat_a or not cat_b:
        return

    with dpg.group(parent=container):
        if cat_a.db_key == cat_b.db_key:
            dpg.add_text("Cannot breed a cat with itself.", color=(255, 100, 100, 255))
            return

        if not can_breed(cat_a, cat_b):
            dpg.add_text(
                "Incompatible pairing (Gender mismatch).",
                color=(255, 100, 100, 255),
            )
            return

        if is_hater_conflict(cat_a, cat_b):
            dpg.add_text(
                "Hater conflict - these cats refuse to breed.",
                color=(255, 100, 100, 255),
            )
            return

        if is_lover_conflict(cat_a, cat_b, state.avoid_lovers):
            dpg.add_text(
                "Lover conflict - pair excluded by settings.",
                color=(255, 100, 100, 255),
            )
            return

        is_a_gay = state.gay_flags.get(cat_a.db_key, False)
        is_b_gay = state.gay_flags.get(cat_b.db_key, False)
        if (
            (is_a_gay or is_b_gay)
            and cat_a.gender.lower() != "?"
            and cat_b.gender.lower() != "?"
        ):
            dpg.add_text(
                "Gay conflict - one or both cats have same-sex breeding preference but neither is genderless.",
                color=(255, 100, 100, 255),
            )
            return

        ancestor_contribs = build_ancestor_contribs(state.cats)

        params = OptimizationParams(
            min_stats=state.min_stats,
            max_risk=state.max_risk,
            avoid_lovers=state.avoid_lovers,
            scoring_prefs=ScoringPreferences(
                minimize_variance=state.minimize_variance,
                prefer_low_aggression=state.prefer_low_aggression,
                prefer_high_libido=state.prefer_high_libido,
                prefer_high_charisma=state.prefer_high_charisma,
                maximize_throughput=state.maximize_throughput,
            ),
            planner_traits=state.planner_traits,
            gay_flags=state.gay_flags,
        )

        pair_result = score_pair(
            cat_a, cat_b, ancestor_contribs, params, skip_risk_check=True
        )

        if not pair_result:
            dpg.add_text("Could not score this pair.", color=(255, 100, 100, 255))
            return

        if dpg.does_item_exist("inspector_tab_bar"):
            dpg.set_value("inspector_tab_bar", "inspector_pair_tab")

        show_pair_detail_window(pair_result, state)

        disorder = pair_result.factors.expected_disorder_chance * 100
        part_defect = pair_result.factors.expected_part_defect_chance * 100
        combined = pair_result.factors.combined_malady_chance * 100

        risk_color = (255, 100, 100, 255) if combined > 15 else (100, 255, 100, 255)
        dpg.add_text(
            f"Expected Quality: {pair_result.quality:.1f} | "
            f"Disorder: {disorder:.0f}% | Part Defect: {part_defect:.0f}% | Combined: {combined:.0f}%",
            color=risk_color,
        )

        with dpg.group(horizontal=True):
            if pair_result.factors.mutual_lovers:
                dpg.add_text("[<3 Lovers]", color=(255, 150, 150, 255))
            if pair_result.factors.libido_factor > 0.6:
                dpg.add_text("[+ Libido]", color=(255, 200, 100, 255))
            if pair_result.factors.aggression_factor > 0.6:
                dpg.add_text("[- Aggro]", color=(100, 200, 255, 255))
            if combined > 10:
                dpg.add_text("[! Inbred]", color=(255, 100, 100, 255))
            if pair_result.factors.combined_malady_chance > state.max_risk:
                dpg.add_text(
                    f"[! High Risk (>{state.max_risk * 100:.0f}%)]",
                    color=(255, 100, 100, 255),
                )

        if state.planner_traits:
            combined_traits = set()
            for cat in (cat_a, cat_b):
                combined_traits.update(
                    normalize_trait_name(t).lower() for t in (cat.mutations or [])
                )
                combined_traits.update(
                    normalize_trait_name(t).lower()
                    for t in (cat.passive_abilities or [])
                )
                combined_traits.update(
                    normalize_trait_name(t).lower() for t in (cat.abilities or [])
                )

            hits = sum(
                1
                for pt in state.planner_traits
                if normalize_trait_name(pt.key).lower() in combined_traits
            )
            total = len(state.planner_traits)

            if hits > 0:
                dpg.add_text(
                    f"[* {hits}/{total} Favorable Traits]", color=(100, 255, 100, 255)
                )
