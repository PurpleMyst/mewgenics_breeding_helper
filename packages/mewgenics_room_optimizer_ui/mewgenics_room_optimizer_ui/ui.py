"""DearPyGui UI components for room optimizer."""

import dearpygui.dearpygui as dpg

from mewgenics_room_optimizer import RoomType

from .state import AppState


def build_ui(state: AppState):
    """Build all DPG UI components."""

    with dpg.window(tag="main_window", label="Room Optimizer", width=1000, height=700):
        build_menu_bar(state)
        build_toolbar(state)
        build_room_config_section(state)
        build_params_section(state)
        build_optimize_button(state)
        build_results_section(state)
        build_details_section(state)

    build_file_dialogs(state)
    build_themes()


def build_menu_bar(state: AppState):
    """Build the menu bar."""
    with dpg.menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(
                label="Load Save", callback=show_load_dialog, user_data=state
            )
            dpg.add_menu_item(
                label="Save Config", callback=save_config_callback, user_data=state
            )
            dpg.add_menu_item(label="Exit", callback=exit_callback)


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
    with dpg.child_window(height=150, border=True, tag="room_config_section"):
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

            for room in state.room_configs:
                with dpg.table_row():
                    dpg.add_text(room.key)
                    dpg.add_text(room.display_name)
                    dpg.add_text(room.room_type.value)
                    dpg.add_text(
                        "Unlimited" if room.max_cats is None else str(room.max_cats)
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
    with dpg.child_window(height=150, border=True, tag="details_section"):
        dpg.add_text("Selected Room Details")
        dpg.add_separator()
        dpg.add_text(
            "Select a room from results to see details", tag="details_placeholder"
        )


def build_file_dialogs(state: AppState):
    """Build file dialogs (hidden by default)."""
    with dpg.file_dialog(
        directory_selector=False,
        show=False,
        callback=load_save_file,
        tag="load_file_dialog",
        width=600,
        height=400,
        user_data=state,
    ):
        dpg.add_file_extension(".*")
        dpg.add_file_extension(".sav", color=(0, 255, 0, 255))


def build_themes():
    """Build application themes."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (200, 200, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 120, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 140, 220, 255))

    dpg.bind_theme(global_theme)


def show_load_dialog(sender, app_data, user_data: AppState):
    """Show the load file dialog."""
    dpg.show_item("load_file_dialog")


def load_save_file(sender, app_data, user_data: AppState):
    """Handle file selection from dialog."""
    from mewgenics_parser import parse_save

    filepath = app_data["file_path_name"]
    try:
        save_data = parse_save(filepath)
        user_data.cats = save_data.cats
        user_data.last_save_path = filepath
        user_data.results = None
        user_data.save()

        dpg.set_value("status_text", f"Loaded: {filepath}")
        dpg.set_value("cat_count_text", f"Cats: {len(user_data.cats)}")
        clear_results_table()
    except Exception as e:
        print(f"Error loading save: {e}")


def save_config_callback(sender, app_data, user_data: AppState):
    """Save configuration to disk."""
    user_data.save()


def exit_callback(sender, app_data, user_data):
    """Exit the application."""
    dpg.destroy_context()


def run_optimization(sender, app_data, user_data: AppState):
    """Run the optimization."""
    from mewgenics_room_optimizer import optimize, build_ancestor_contribs
    from mewgenics_room_optimizer.types import OptimizationParams

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

    update_results_table(results)


def update_results_table(results):
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
                user_data=room.room.key,
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


def on_room_selected(sender, app_data, user_data):
    """Handle room selection in results table."""
    selected_key = user_data
    print(f"Selected room: {selected_key}")
