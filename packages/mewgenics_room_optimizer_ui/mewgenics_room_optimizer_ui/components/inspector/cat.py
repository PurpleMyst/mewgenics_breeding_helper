from mewgenics_room_optimizer_ui.display_models import AbilityDisplay
import dearpygui.dearpygui as dpg
from mewgenics_parser.cat import Cat, CatStatus
from mewgenics_parser.traits import Trait, TraitCategory, extract_traits_from_cat

from ...colors import (
    COLOR_DANGER,
    COLOR_DEFAULT_TEXT,
    COLOR_LOVER,
    COLOR_MUTED,
    COLOR_SUCCESS,
)
from ...display_helpers import get_cat_abilities, get_cat_body_parts, get_cat_passives
from ...state import AppState


def show_cat_detail_window(cat: Cat, state: AppState) -> None:
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
                if isinstance(lover := cat.lover, Cat):
                    lover_name = lover.name
                    if lover.status and lover.status != CatStatus.IN_HOUSE:
                        lover_name += f" ({lover.status})"
                    lover_names.append(lover_name)
                lovers_str = ", ".join(lover_names) if lover_names else "-"

                hater_names = []
                if isinstance(hater := cat.hater, Cat):
                    hater_name = hater.name
                    if hater.status and hater.status != CatStatus.IN_HOUSE:
                        hater_name += f" ({hater.status})"
                    hater_names.append(hater_name)
                haters_str = ", ".join(hater_names) if hater_names else "-"

                dpg.add_text(f"Name: {cat.name or 'Unnamed'}")
                dpg.add_text(f"Gender: {cat.gender}")
                dpg.add_text(f"Age: {cat.age if cat.age is not None else 'Unknown'}")
                dpg.add_text(f"Status: {cat.status}")
                dpg.add_text(f"Room: {room_display}")
                dpg.add_text(f"Lover: {lovers_str}", color=COLOR_LOVER)
                dpg.add_text(f"Hater: {haters_str}", color=COLOR_DANGER)

            with dpg.table_row():
                for i, stat in enumerate(cat.stat_base):
                    dpg.add_text(f"{STAT_NAMES[i]}: {stat}")

        sexuality = cat.sexuality
        if sexuality is not None:
            sexuality_pct = int(sexuality * 100)
            dpg.add_text(f"Sexuality: {sexuality_pct}% same-sex preference")

        dpg.add_separator()

        all_traits = extract_traits_from_cat(cat)
        disorder_traits = [
            t for t in all_traits if t.category == TraitCategory.DISORDER
        ]

        _render_ability_list(
            "Active Abilities",
            get_cat_abilities(cat, state.game_data),
            state,
        )
        _render_ability_list(
            "Passive Abilities",
            get_cat_passives(cat, state.game_data),
            state,
        )
        _render_trait_tree_node("Disorders", disorder_traits, state)
        _render_body_part_list(
            "Body Parts",
            get_cat_body_parts(cat, state.game_data),
            state,
        )


def on_cat_selected(
    sender: int, app_data: bool, user_data: tuple[Cat, AppState]
) -> None:
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


def _render_trait_tree_node(label: str, traits: list[Trait], state: AppState) -> None:
    """Reusable component for rendering a collapsable list of traits in the inspector."""
    with dpg.tree_node(label=f"{label} ({len(traits)})", default_open=bool(traits)):
        if not traits:
            dpg.add_text("  None", color=COLOR_MUTED)
            return

        for trait in traits:
            name = trait.get_display_name(state.game_data)
            desc = trait.get_description(state.game_data)
            if not name and not desc:
                print(trait)

            is_fav = any(trait.key == u.trait.key for u in state.universals)

            if trait.is_negative():
                color = COLOR_DANGER
            else:
                color = COLOR_SUCCESS if is_fav else COLOR_DEFAULT_TEXT

            dpg.add_text(f"  {name}", color=color)
            if desc:
                dpg.add_text(f"    {desc}", color=COLOR_MUTED)


def _render_ability_list(
    label: str, abilities: list[AbilityDisplay], state: AppState
) -> None:
    """Render abilities with upgrade indicator (+ suffix) and favorable trait highlighting."""
    with dpg.tree_node(
        label=f"{label} ({len(abilities)})", default_open=bool(abilities)
    ):
        if not abilities:
            dpg.add_text("  None", color=COLOR_MUTED)
            return

        req_keys = {u.trait.key for u in state.universals}

        for ability in abilities:
            color = (
                COLOR_SUCCESS if ability.base_key in req_keys else COLOR_DEFAULT_TEXT
            )
            dpg.add_text(f"  {ability.name}", color=color)
            if ability.description:
                dpg.add_text(f"    {ability.description}", color=COLOR_MUTED)


def _render_body_part_list(label: str, body_parts: list, state: AppState) -> None:
    """Render body parts grouped by symmetric slots with favorable trait highlighting."""
    with dpg.tree_node(
        label=f"{label} ({len(body_parts)})", default_open=bool(body_parts)
    ):
        if not body_parts:
            dpg.add_text("  None", color=COLOR_MUTED)
            return

        req_keys = {u.trait.key for u in state.universals}

        for bp in body_parts:
            is_fav = bp.key in req_keys

            slots_str = ", ".join(bp.slot_labels)
            text = f"{bp.display_name} [{slots_str}]"

            color = (
                COLOR_SUCCESS
                if is_fav
                else (COLOR_DANGER if bp.is_negative else COLOR_DEFAULT_TEXT)
            )

            dpg.add_text(f"  {text}", color=color)
            if bp.description:
                dpg.add_text(f"    {bp.description}", color=COLOR_MUTED)
