"""Application state for room optimizer UI."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from mewgenics_parser import Cat
from mewgenics_parser.gpak import GameData
from mewgenics_parser.traits import Trait, create_trait, extract_traits_from_cat
from mewgenics_room_optimizer import (
    DEFAULT_ROOM_CONFIGS,
    OptimizationResult,
    RoomConfig,
    RoomType,
)
from mewgenics_room_optimizer.types import ScoredPair
from mewgenics_scorer import TraitRequirement

CONFIG_DIR = Path.home() / ".mewgenics_room_optimizer"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _find_gpak_path() -> str:
    """Find resources.gpak from common paths."""
    candidates = [
        "resources.gpak",
        os.path.join(os.getcwd(), "resources.gpak"),
        r"C:\Program Files (x86)\Steam\steamapps\common\Mewgenics\resources.gpak",
        os.path.expanduser("~/Mewgenics/resources.gpak"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""


def _ensure_config_dir() -> None:
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


def save_config(config: dict) -> None:
    """Save configuration to disk."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def room_configs_from_dict(data: list[dict]) -> list[RoomConfig]:
    """Convert dictionary list to RoomConfig objects."""
    return [
        RoomConfig(
            key=r["key"],
            room_type=RoomType(r["room_type"]),
            max_cats=r.get("max_cats"),
            base_stim=r.get("base_stim", 50.0),
        )
        for r in data
    ]


def room_configs_to_dict(configs: list[RoomConfig]) -> list[dict]:
    """Convert RoomConfig objects to dictionary list."""
    return [
        {
            "key": r.key,
            "room_type": r.room_type.value,
            "max_cats": r.max_cats,
            "base_stim": r.base_stim,
        }
        for r in configs
    ]


def trait_requirements_from_dict(data: list[dict]) -> list[TraitRequirement]:
    """Convert dictionary list to TraitRequirement objects with normalized keys."""
    return [
        TraitRequirement(
            trait=create_trait(t["category"], t["key"]),
            weight=t.get("weight", 5.0),
        )
        for t in data
    ]


def migrate_trait_requirements(
    traits: list[TraitRequirement],
) -> list[TraitRequirement]:
    """Migrate traits to normalized form and deduplicate.

    If a user had both 'sturdy' and 'sturdy2', this will merge them
    into a single normalized entry.
    """
    seen: dict[tuple[str, str], TraitRequirement] = {}

    for t in traits:
        trait_key = t.trait.key
        category = t.trait.category
        key = (category, trait_key)

        if key not in seen:
            seen[key] = TraitRequirement(
                trait=create_trait(category, trait_key),
                weight=t.weight,
            )
        else:
            existing = seen[key]
            seen[key] = TraitRequirement(
                trait=create_trait(category, trait_key),
                weight=max(existing.weight, t.weight),
            )

    return list(seen.values())


def trait_requirements_to_dict(traits: list[TraitRequirement]) -> list[dict]:
    """Convert TraitRequirement objects to dictionary list."""
    return [
        {
            "category": t.trait.category,
            "key": t.trait.key,
            "weight": t.weight,
        }
        for t in traits
    ]


@dataclass
class AppState:
    """Application state - pure Python, DPG-agnostic."""

    cats: list[Cat] = field(default_factory=list)
    room_configs: list[RoomConfig] = field(default_factory=list)
    results: OptimizationResult | None = None
    selected_result_room_key: str | None = None
    selected_cat_db_key: int | None = None
    last_save_path: str | None = None
    game_data: GameData = field(
        default_factory=lambda: (
            GameData.from_gpak(p) if (p := _find_gpak_path()) else GameData.empty()
        )
    )

    min_stats: int = 0
    max_risk: float = 0.2  # Probability (0.0-1.0), displayed as percentage in UI
    minimize_variance: bool = True
    prefer_low_aggression: bool = True
    prefer_high_libido: bool = True
    prefer_high_charisma: bool = True
    maximize_throughput: bool = False

    trait_requirements: list[TraitRequirement] = field(default_factory=list)

    sim_cat_a_key: int | None = None
    sim_cat_b_key: int | None = None
    selected_pair: ScoredPair | None = None
    selected_pair_index: int | None = None

    is_loading: bool = False

    @staticmethod
    def _convert_max_risk(value: float) -> float:
        """Convert saved max_risk from percentage (0-100) to probability (0-1)."""
        if value > 1.0:
            return value / 100.0
        return value

    @classmethod
    def from_config(cls) -> Self:
        """Create AppState from saved configuration."""
        config = load_config()
        saved_rooms = {r["key"]: r for r in config.get("rooms", [])}

        room_configs = []
        for default in DEFAULT_ROOM_CONFIGS:
            if default.key in saved_rooms:
                saved = saved_rooms[default.key]
                room_configs.append(
                    RoomConfig(
                        key=default.key,
                        room_type=RoomType(
                            saved.get("room_type", default.room_type.value)
                        ),
                        max_cats=saved.get("max_cats", default.max_cats),
                        base_stim=saved.get("base_stim", default.base_stim),
                    )
                )
            else:
                room_configs.append(default)

        return cls(
            room_configs=room_configs,
            trait_requirements=migrate_trait_requirements(
                trait_requirements_from_dict(config.get("trait_requirements", []))
            ),
            last_save_path=config.get("last_save_path"),
            min_stats=config.get("min_stats", 0),
            max_risk=cls._convert_max_risk(config.get("max_risk", 0.2)),
            minimize_variance=config.get("minimize_variance", True),
            prefer_low_aggression=config.get("prefer_low_aggression", True),
            prefer_high_libido=config.get("prefer_high_libido", True),
            prefer_high_charisma=config.get("prefer_high_charisma", True),
            maximize_throughput=config.get("maximize_throughput", False),
        )

    def to_config(self) -> dict:
        """Convert state to configuration dictionary for saving."""
        return {
            "rooms": room_configs_to_dict(self.room_configs),
            "trait_requirements": trait_requirements_to_dict(self.trait_requirements),
            "last_save_path": self.last_save_path,
            "min_stats": self.min_stats,
            "max_risk": self.max_risk
            * 100,  # Convert probability to percentage for backwards compatibility
            "minimize_variance": self.minimize_variance,
            "prefer_low_aggression": self.prefer_low_aggression,
            "prefer_high_libido": self.prefer_high_libido,
            "prefer_high_charisma": self.prefer_high_charisma,
            "maximize_throughput": self.maximize_throughput,
        }

    def save(self) -> None:
        """Save current state to disk."""
        save_config(self.to_config())

    @property
    def has_cats(self) -> bool:
        return len(self.cats) > 0

    @property
    def has_results(self) -> bool:
        return self.results is not None

    @property
    def alive_cats(self) -> list[Cat]:
        """Return only cats with In House status."""
        return [c for c in self.cats if c.status == "In House"]

    def get_available_traits(self, category: str) -> list[Trait]:
        """Extract unique traits from alive cats for a given category."""
        traits: list[Trait] = []
        seen_keys: set[str] = set()

        for cat in self.alive_cats:
            for trait in extract_traits_from_cat(cat):
                if trait.category == category and trait.key not in seen_keys:
                    traits.append(trait)
                    seen_keys.add(trait.key)

        return sorted(traits, key=lambda t: t.key)
