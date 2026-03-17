"""Entry point for room optimizer UI."""

import argparse

import dearpygui.dearpygui as dpg

from mewgenics_room_optimizer_ui.state import AppState
from mewgenics_room_optimizer_ui.ui import build_ui


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Mewgenics Room Optimizer")
    parser.add_argument(
        "save_file", nargs="?", help="Path to .sav file to load on startup"
    )
    return parser.parse_args()


def load_startup_save(filepath: str, state: AppState) -> bool:
    """Load a save file at startup."""
    from mewgenics_parser import parse_save

    try:
        save_data = parse_save(filepath)
        state.cats = save_data.cats
        state.last_save_path = filepath
        return True
    except Exception as e:
        print(f"Error loading save file: {e}")
        return False


def main():
    """Main entry point."""
    args = parse_args()

    dpg.create_context()

    state = AppState.from_config()

    if args.save_file:
        load_startup_save(args.save_file, state)

    build_ui(state)

    dpg.create_viewport(title="Room Optimizer", width=1000, height=700)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    dpg.start_dearpygui()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
