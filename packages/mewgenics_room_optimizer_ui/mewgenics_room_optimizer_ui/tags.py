from enum import StrEnum


class Tags(StrEnum):
    """DPG tags for widgets and items."""

    # Inspector
    INSPECTOR_SECTION = "inspector_section"
    INSPECTOR_TAB_BAR = "inspector_tab_bar"
    INSPECTOR_CAT_TAB = "inspector_cat_tab"
    INSPECTOR_PAIR_TAB = "inspector_pair_tab"
    INSPECTOR_CONTAINER = "inspector_container"
    INSPECTOR_PLACEHOLDER = "inspector_placeholder"
    INSPECTOR_PAIR_CONTAINER = "inspector_pair_container"
    INSPECTOR_PAIR_PLACEHOLDER = "inspector_pair_placeholder"
