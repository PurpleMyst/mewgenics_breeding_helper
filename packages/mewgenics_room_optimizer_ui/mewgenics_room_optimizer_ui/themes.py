import dearpygui.dearpygui as dpg


def build_themes() -> None:
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


