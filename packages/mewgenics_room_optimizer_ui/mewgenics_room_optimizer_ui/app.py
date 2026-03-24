"""Entry point for room optimizer UI."""

import argparse
import multiprocessing
import sys
from pathlib import Path
from typing import Any

# Restore standard Windows DLL search path before loading DearPyGui.
# PyInstaller's bootloader calls SetDllDirectoryW(_internal) which
# replaces the standard search path, preventing system DLLs like
# d3d11.dll and dxgi.dll from being found in System32.
if sys.platform == "win32":
    import ctypes

    ctypes.windll.kernel32.SetDllDirectoryW(None)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Mewgenics Breeding Helper")
    parser.add_argument(
        "save_file", nargs="?", help="Path to .sav file to load on startup"
    )
    return parser.parse_args()


def load_startup_save(filepath: str, state: Any) -> bool:
    """Load a save file at startup."""
    from mewgenics_parser import parse_save

    try:
        save_data = parse_save(filepath)
        state.cats = save_data.cats
        state.save_data = save_data
        state.last_save_path = filepath
        return True
    except Exception as e:
        print(f"Error loading save file: {e}")
        return False


def main() -> None:
    """Main entry point."""

    import dearpygui.dearpygui as dpg

    from mewgenics_room_optimizer_ui.ui import build_ui
    from mewgenics_room_optimizer_ui.state import AppState

    args = parse_args()

    dpg.create_context()

    state = AppState.from_config()

    if args.save_file:
        load_startup_save(args.save_file, state)

    build_ui(state)

    bundle_dir = getattr(sys, "_MEIPASS", Path(__file__).parent)
    icon_path = str(Path(bundle_dir) / "favicon.ico")
    dpg.create_viewport(
        title="Breeding Helper",
        width=1000,
        height=700,
        small_icon=icon_path,
        large_icon=icon_path,
    )
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)

    dpg.show_viewport()

    dpg.start_dearpygui()

    dpg.destroy_context()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # For PyInstaller on Windows
    main()
