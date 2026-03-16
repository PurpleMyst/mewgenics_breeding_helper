"""Application state for room optimizer UI."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

from mewgenics_parser import Cat
from mewgenics_room_optimizer import (
    OptimizationResult,
    RoomConfig,
    RoomType,
    DEFAULT_ROOM_CONFIGS,
)


CONFIG_DIR = Path.home() / ".mewgenics_room_optimizer"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_default_config() -> dict:
    return {
        "rooms": [
            {
                "key": r.key,
                "display_name": r.display_name,
                "room_type": r.room_type.value,
                "max_cats": r.max_cats,
            }
            for r in DEFAULT_ROOM_CONFIGS
        ],
        "last_save_path": None,
    }


def load_config() -> dict:
    """Load configuration from disk or return defaults."""
    _ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return _load_default_config()
    return _load_default_config()


def save_config(config: dict):
    """Save configuration to disk."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def room_configs_from_dict(data: list[dict]) -> list[RoomConfig]:
    """Convert dictionary list to RoomConfig objects."""
    return [
        RoomConfig(
            key=r["key"],
            display_name=r["display_name"],
            room_type=RoomType(r["room_type"]),
            max_cats=r.get("max_cats"),
        )
        for r in data
    ]


def room_configs_to_dict(configs: list[RoomConfig]) -> list[dict]:
    """Convert RoomConfig objects to dictionary list."""
    return [
        {
            "key": r.key,
            "display_name": r.display_name,
            "room_type": r.room_type.value,
            "max_cats": r.max_cats,
        }
        for r in configs
    ]


@dataclass
class AppState:
    """Application state - pure Python, DPG-agnostic."""

    cats: list[Cat] = field(default_factory=list)
    room_configs: list[RoomConfig] = field(default_factory=list)
    results: OptimizationResult | None = None
    selected_room_key: str | None = None
    last_save_path: str | None = None

    min_stats: int = 0
    max_risk: float = 20.0
    minimize_variance: bool = True
    avoid_lovers: bool = True
    prefer_low_aggression: bool = True
    prefer_high_libido: bool = True

    is_loading: bool = False

    @classmethod
    def from_config(cls) -> "AppState":
        """Create AppState from saved configuration."""
        config = load_config()
        room_configs = room_configs_from_dict(config.get("rooms", []))
        return cls(
            room_configs=room_configs,
            last_save_path=config.get("last_save_path"),
        )

    def to_config(self) -> dict:
        """Convert state to configuration dictionary for saving."""
        return {
            "rooms": room_configs_to_dict(self.room_configs),
            "last_save_path": self.last_save_path,
        }

    def save(self):
        """Save current state to disk."""
        save_config(self.to_config())

    @property
    def has_cats(self) -> bool:
        return len(self.cats) > 0

    @property
    def has_results(self) -> bool:
        return self.results is not None
