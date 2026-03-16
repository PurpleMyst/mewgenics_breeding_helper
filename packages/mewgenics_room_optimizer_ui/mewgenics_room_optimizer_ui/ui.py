"""DearPyGui UI components for room optimizer."""

import dearpygui.dearpygui as dpg

from mewgenics_room_optimizer import RoomType

from .state import AppState


def build_ui(state: AppState):
    """Build all DPG UI components."""

    with dpg.window(tag="main_window", label="Room Optimizer", width=1000, height=700):
        build_menu_bar(state)
        build_saves_section(state)
        build_toolbar(state)
        build_room_config_section(state)
        build_params_section(state)
        build_traits_section(state)
        build_optimize_button(state)
        build_results_section(state)
        build_details_section(state)

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
    with dpg.collapsing_header(label="Available Saves", default_open=True):
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
        dpg.add_text(f"Cats: {len(state.cats)}", tag="cat_count_text")


def build_room_config_section(state: AppState):
    """Build the room configuration section."""
    with dpg.collapsing_header(label="Room Configuration", default_open=True):
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

            room_types = ["breeding", "fighting", "general", "none"]
            for room in state.room_configs:
                with dpg.table_row(parent="room_config_table"):
                    dpg.add_text(room.key, tag=f"room_key_{room.key}")
                    dpg.add_input_text(
                        default_value=room.display_name,
                        tag=f"room_name_{room.key}",
                        width=150,
                    )
                    dpg.add_combo(
                        room_types,
                        default_value=room.room_type.value,
                        tag=f"room_type_{room.key}",
                        width=100,
                    )
                    max_cats_val = "" if room.max_cats is None else str(room.max_cats)
                    dpg.add_input_text(
                        default_value=max_cats_val,
                        tag=f"room_max_{room.key}",
                        width=100,
                        hint="empty=unlimited",
                    )

            dpg.add_button(
                label="Update Rooms",
                tag="update_rooms_button",
                callback=on_update_rooms,
                user_data=state,
            )


def build_params_section(state: AppState):
    """Build the optimization parameters section."""
    with dpg.collapsing_header(label="Optimization Parameters", default_open=True):
        with dpg.child_window(height=160, border=True, tag="params_section"):
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="Min Stats",
                    tag="min_stats",
                    default_value=state.min_stats,
                    width=100,
                )
                dpg.add_slider_float(
                    label="Max Risk %",
                    tag="max_risk",
                    default_value=state.max_risk,
                    max_value=100.0,
                    width=200,
                )
            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    label="Minimize Variance",
                    tag="minimize_variance",
                    default_value=state.minimize_variance,
                )
                dpg.add_checkbox(
                    label="Avoid Lovers",
                    tag="avoid_lovers",
                    default_value=state.avoid_lovers,
                )
            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    label="Prefer Low Aggression",
                    tag="prefer_low_aggression",
                    default_value=state.prefer_low_aggression,
                )
                dpg.add_checkbox(
                    label="Prefer High Libido",
                    tag="prefer_high_libido",
                    default_value=state.prefer_high_libido,
                )


def build_traits_section(state: AppState):
    """Build the favorable traits selection section."""
    with dpg.collapsing_header(label="Favorable Traits", default_open=True):
        with dpg.child_window(height=200, border=True, tag="traits_section"):
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text("Mutations")
                    dpg.add_input_text(
                        tag="mutation_filter",
                        hint="Filter...",
                        width=150,
                        callback=on_mutation_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="mutation_listbox",
                        width=150,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_mutation, user_data=state
                    )
                with dpg.group():
                    dpg.add_text("Passives")
                    dpg.add_input_text(
                        tag="passive_filter",
                        hint="Filter...",
                        width=150,
                        callback=on_passive_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="passive_listbox",
                        width=150,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_passive, user_data=state
                    )
                with dpg.group():
                    dpg.add_text("Abilities")
                    dpg.add_input_text(
                        tag="ability_filter",
                        hint="Filter...",
                        width=150,
                        callback=on_ability_filter,
                        user_data=state,
                    )
                    dpg.add_listbox(
                        tag="ability_listbox",
                        width=150,
                        num_items=5,
                    )
                    dpg.add_button(
                        label="Add", callback=on_add_ability, user_data=state
                    )

            dpg.add_separator()
            dpg.add_text("Selected Traits:")
            dpg.add_button(label="Clear All", callback=on_clear_traits, user_data=state)

            dpg.add_group(tag="selected_traits_container")


def on_mutation_filter(sender, app_data, user_data: AppState):
    """Filter mutations listbox."""
    filter_text = (app_data or "").lower()
    mutations = user_data.get_available_mutations()
    filtered = (
        [m for m in mutations if filter_text in m.lower()] if filter_text else mutations
    )
    dpg.configure_item("mutation_listbox", items=filtered)


def on_passive_filter(sender, app_data, user_data: AppState):
    """Filter passives listbox."""
    filter_text = (app_data or "").lower()
    passives = user_data.get_available_passives()
    filtered = (
        [p for p in passives if filter_text in p.lower()] if filter_text else passives
    )
    dpg.configure_item("passive_listbox", items=filtered)


def on_ability_filter(sender, app_data, user_data: AppState):
    """Filter abilities listbox."""
    filter_text = (app_data or "").lower()
    abilities = user_data.get_available_abilities()
    filtered = (
        [a for a in abilities if filter_text in a.lower()] if filter_text else abilities
    )
    dpg.configure_item("ability_listbox", items=filtered)


def on_add_mutation(sender, app_data, user_data: AppState):
    """Add selected mutation to favorable traits."""
    selected = dpg.get_value("mutation_listbox")

    if not selected:
        items = dpg.get_item_configuration("mutation_listbox").get("items", [])
        if items:
            selected = items[0]

    if selected:
        from mewgenics_scorer import TraitRequirement

        user_data.planner_traits.append(
            TraitRequirement(category="mutation", key=selected, weight=5.0)
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

        user_data.planner_traits.append(
            TraitRequirement(category="passive", key=selected, weight=5.0)
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

        user_data.planner_traits.append(
            TraitRequirement(category="ability", key=selected, weight=5.0)
        )
        user_data.save()
        update_traits_display(user_data)


def on_clear_traits(sender, app_data, user_data: AppState):
    """Clear all favorable traits."""
    user_data.planner_traits.clear()
    user_data.save()
    update_traits_display(user_data)


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
            dpg.add_text(f"[{int(trait.weight)}] {trait.category}: {trait.key}")
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


def build_optimize_button(state: AppState):
    """Build the optimize button."""
    dpg.add_button(
        label="Calculate Optimal Distribution",
        tag="optimize_button",
        callback=run_optimization,
        user_data=state,
    )


def build_results_section(state: AppState):
    """Build the results section."""
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
                dpg.add_table_column(label="Avg Stats")
                dpg.add_table_column(label="Risk %")

            dpg.add_text("Run optimization to see results", tag="results_placeholder")


def build_details_section(state: AppState):
    """Build the selected room details section."""
    with dpg.collapsing_header(label="Selected Room Details", default_open=True):
        with dpg.child_window(height=250, border=True, tag="details_section"):
            dpg.add_text(
                "Select a room from results to see details", tag="details_placeholder"
            )


def build_themes():
    """Build application themes."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (200, 200, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 120, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 140, 220, 255))

    dpg.bind_theme(global_theme)


def scan_and_load_saves(sender=None, app_data=None, user_data: AppState = None):
    """Scan for saves and auto-load the newest."""
    from mewgenics_parser import find_save_files, parse_save

    if user_data is None:
        user_data = sender

    save_paths = find_save_files()
    save_names = [s.split("\\")[-1].split("/")[-1] for s in save_paths]
    state = user_data

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
                "cat_count_text", f"Cats: {len(state.cats)} ({alive} in house)"
            )
            clear_results_table()
            init_traits_lists(state)
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

    dpg.configure_item("mutation_listbox", items=mutations)
    dpg.configure_item("passive_listbox", items=passives)
    dpg.configure_item("ability_listbox", items=abilities)

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
        clear_results_table()
        init_traits_lists(user_data)
    except Exception as e:
        print(f"Error loading save: {e}")


def save_config_callback(sender, app_data, user_data: AppState):
    """Save configuration to disk."""
    user_data.save()


def on_update_rooms(sender, app_data, user_data: AppState):
    """Handle update rooms button click."""
    from mewgenics_room_optimizer import RoomConfig, RoomType

    new_configs = []
    for room in user_data.room_configs:
        new_name = dpg.get_value(f"room_name_{room.key}")
        new_type_str = dpg.get_value(f"room_type_{room.key}")
        new_max_str = dpg.get_value(f"room_max_{room.key}")

        new_max = None
        if new_max_str.strip():
            try:
                new_max = int(new_max_str)
            except ValueError:
                pass

        new_configs.append(
            RoomConfig(
                key=room.key,
                display_name=new_name,
                room_type=RoomType(new_type_str),
                max_cats=new_max,
            )
        )

    user_data.room_configs = new_configs
    user_data.results = None
    user_data.save()
    clear_results_table()
    dpg.set_value("status_text", "Rooms updated and saved. Run optimization to apply.")


def exit_callback(sender, app_data, user_data):
    """Exit the application."""
    dpg.destroy_context()


def run_optimization(sender, app_data, user_data: AppState):
    """Run the optimization."""
    from mewgenics_room_optimizer import optimize
    from mewgenics_room_optimizer.types import OptimizationParams
    from mewgenics_scorer import build_ancestor_contribs

    if not user_data.cats:
        return

    min_stats = dpg.get_value("min_stats")
    max_risk = dpg.get_value("max_risk")
    minimize_variance = dpg.get_value("minimize_variance")
    avoid_lovers = dpg.get_value("avoid_lovers")
    prefer_low_aggression = dpg.get_value("prefer_low_aggression")
    prefer_high_libido = dpg.get_value("prefer_high_libido")

    params = OptimizationParams(
        min_stats=min_stats,
        max_risk=max_risk,
        minimize_variance=minimize_variance,
        avoid_lovers=avoid_lovers,
        prefer_low_aggression=prefer_low_aggression,
        prefer_high_libido=prefer_high_libido,
        planner_traits=user_data.planner_traits,
    )

    ancestor_contribs = build_ancestor_contribs(user_data.cats)
    results = optimize(
        user_data.cats, user_data.room_configs, params, ancestor_contribs
    )
    user_data.results = results

    update_results_table(results, user_data)


def update_results_table(results, state):
    """Update the results table with optimization results."""
    clear_results_table()

    for room in results.rooms:
        avg_stats = 0.0
        avg_risk = 0.0
        if room.pairs:
            avg_stats = sum(p.quality for p in room.pairs) / len(room.pairs)
            avg_risk = sum(p.factors.risk_percent for p in room.pairs) / len(room.pairs)

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
            dpg.add_text(f"{avg_stats:.1f}")
            dpg.add_text(f"{avg_risk:.0f}%")


def clear_results_table():
    """Clear the results table."""
    table = "results_table"
    if dpg.does_item_exist(table):
        children = dpg.get_item_children(table)
        if children and 1 in children:
            for row in children[1]:
                dpg.delete_item(row)


def clear_details_section():
    """Clear the details section."""
    section = "details_section"
    if dpg.does_item_exist(section):
        children = dpg.get_item_children(section)
        if children and 1 in children:
            for child in children[1]:
                dpg.delete_item(child)


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


def build_details_tabs(selected_room, state):
    """Build the tabbed details view for a selected room."""
    # Tab bar only (section title is already "Selected Room Details")
    dpg.add_tab_bar(parent="details_section", tag="details_tab_bar")

    # Pairs tab
    with dpg.tab(label="Pairs", parent="details_tab_bar"):
        if selected_room.pairs:
            for pair in selected_room.pairs:
                stats_a = sum(pair.cat_a.stat_base)
                stats_b = sum(pair.cat_b.stat_base)
                dpg.add_text(
                    f"{pair.cat_a.name or 'Unnamed'} (S:{stats_a}) + {pair.cat_b.name or 'Unnamed'} (S:{stats_b})"
                )
        else:
            dpg.add_text("No breeding pairs in this room")

    # Cats tab - clickable rows
    with dpg.tab(label="Cats", parent="details_tab_bar"):
        if selected_room.cats:
            for cat in selected_room.cats:
                cat_name = cat.name or "Unnamed"
                dpg.add_selectable(
                    label=f"{cat_name} [{cat.gender}] S:{sum(cat.stat_base)}",
                    callback=on_cat_selected,
                    user_data=(cat, state),
                    tag=f"cat_row_{cat.db_key}",
                )
        else:
            dpg.add_text("No unpaired cats in this room")


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
    """Show a window with full cat details."""
    from mewgenics_parser.constants import STAT_NAMES

    # Close existing window if open
    if dpg.does_item_exist("cat_detail_window"):
        dpg.delete_item("cat_detail_window")

    with dpg.window(
        label=f"Cat: {cat.name or 'Unnamed'}",
        width=450,
        height=550,
        tag="cat_detail_window",
    ):
        # Basic info
        dpg.add_text(f"Name: {cat.name or 'Unnamed'}")
        dpg.add_text(f"Gender: {cat.gender}")
        dpg.add_text(f"Age: {cat.age if cat.age is not None else 'Unknown'}")
        dpg.add_text(f"Status: {cat.status}")
        dpg.add_text(f"Room: {cat.room or 'Unknown'}")

        dpg.add_separator()

        # Stats
        dpg.add_text("Base Stats:")
        for i, stat in enumerate(cat.stat_base):
            dpg.add_text(f"  {STAT_NAMES[i]}: {stat}")

        dpg.add_separator()

        # Abilities
        dpg.add_text("Active Abilities:")
        for ab in cat.abilities or []:
            desc = state.game_data.ability_descriptions.get(
                ab.lower(), "No description"
            )
            dpg.add_text(f"  {ab}")
            if desc:
                dpg.add_text(f"    {desc}", color=(180, 180, 180, 255))

        dpg.add_separator()

        # Passive Abilities
        dpg.add_text("Passive Abilities:")
        for ab in cat.passive_abilities or []:
            desc = state.game_data.ability_descriptions.get(
                ab.lower(), "No description"
            )
            dpg.add_text(f"  {ab}")
            if desc:
                dpg.add_text(f"    {desc}", color=(180, 180, 180, 255))

        dpg.add_separator()

        # Mutations
        dpg.add_text("Mutations:")
        for mut in cat.mutations or []:
            dpg.add_text(f"  {mut}")
