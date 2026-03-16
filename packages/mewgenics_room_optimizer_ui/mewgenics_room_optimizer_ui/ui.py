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
    with dpg.child_window(height=120, border=True, tag="saves_section"):
        dpg.add_text("Available Saves")
        dpg.add_separator()
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
    with dpg.child_window(height=180, border=True, tag="room_config_section"):
        dpg.add_text("Room Configuration")
        dpg.add_separator()
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
    with dpg.child_window(height=160, border=True, tag="params_section"):
        dpg.add_text("Optimization Parameters")
        dpg.add_separator()
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
    with dpg.child_window(height=200, border=True, tag="results_section"):
        dpg.add_text("Results")
        dpg.add_separator()
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
    with dpg.child_window(height=250, border=True, tag="details_section"):
        dpg.add_text("Selected Room Details")
        dpg.add_separator()
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
            state.set_rooms_from_cats()

            dpg.set_value("saves_listbox", save_names[0])
            dpg.set_value(
                "status_text", f"Loaded: {newest.split('\\')[-1].split('/')[-1]}"
            )
            alive = len(state.alive_cats)
            dpg.set_value(
                "cat_count_text", f"Cats: {len(state.cats)} ({alive} in house)"
            )
            rebuild_room_config_table(state)
            clear_results_table()
        except Exception as e:
            print(f"Error loading save: {e}")
    else:
        dpg.set_value("status_text", "No saves found")
        dpg.set_value("cat_count_text", "Cats: 0")


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
        user_data.set_rooms_from_cats()

        dpg.set_value("status_text", f"Loaded: {selected_name}")
        alive = len(user_data.alive_cats)
        dpg.set_value(
            "cat_count_text", f"Cats: {len(user_data.cats)} ({alive} in house)"
        )
        rebuild_room_config_table(user_data)
        clear_results_table()
    except Exception as e:
        print(f"Error loading save: {e}")


def save_config_callback(sender, app_data, user_data: AppState):
    """Save configuration to disk."""
    user_data.save()


def rebuild_room_config_table(state: AppState):
    """Rebuild the room config table with current room configs."""
    table = "room_config_table"
    if dpg.does_item_exist(table):
        children = dpg.get_item_children(table)
        if children and 1 in children:
            for row in children[1]:
                dpg.delete_item(row)

    room_types = ["breeding", "fighting", "general", "none"]
    for room in state.room_configs:
        with dpg.table_row(parent=table):
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
    clear_results_table()
    dpg.set_value("status_text", "Rooms updated. Run optimization to apply.")


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
    # Header
    dpg.add_text(f"Room: {selected_room.room.display_name}", parent="details_section")
    dpg.add_separator(parent="details_section")

    # Tab bar
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

    # Cats tab
    with dpg.tab(label="Cats", parent="details_tab_bar"):
        if selected_room.cats:
            # Build cats table
            with dpg.table(
                header_row=True,
                borders_innerH=True,
                row_background=True,
            ):
                dpg.add_table_column(label="Name")
                dpg.add_table_column(label="Age")
                dpg.add_table_column(label="Location")
                dpg.add_table_column(label="Abilities")

                for cat in selected_room.cats:
                    with dpg.table_row():
                        dpg.add_text(cat.name or "Unnamed")
                        dpg.add_text(str(cat.age) if cat.age else "Unknown")
                        dpg.add_text(cat.room or "Unknown")

                        # Abilities with tooltips
                        all_abilities = (cat.abilities or []) + (
                            cat.passive_abilities or []
                        )
                        if all_abilities:
                            ability_text = ", ".join(all_abilities)
                            ability_id = f"ability_{cat.db_key}_{all_abilities[0]}"
                            dpg.add_text(ability_text, tag=ability_id)

                            # Tooltip with description
                            for ab in all_abilities:
                                desc = state.game_data.ability_descriptions.get(ab, "")
                                if desc:
                                    with dpg.tooltip(parent=ability_id):
                                        dpg.add_text(desc)
                                        dpg.add_text(
                                            f"({ab})", color=(150, 150, 150, 255)
                                        )
                        else:
                            dpg.add_text("None")
        else:
            dpg.add_text("No unpaired cats in this room")
