"""Application state for room optimizer UI."""

import platformdirs
from typing import Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    field_serializer,
)

from mewgenics_parser import Cat, SaveData
from mewgenics_parser.gpak import GameData
from mewgenics_parser.traits import (
    Trait,
    TraitCategory,
    create_trait,
    extract_traits_from_cat,
)
from mewgenics_room_optimizer import (
    DEFAULT_ROOM_CONFIGS,
    OptimizationResult,
    RoomConfig,
)
from mewgenics_room_optimizer.types import ScoredPair
from mewgenics_scorer.types import TargetBuild, TraitWeight, UniversalTrait

CONFIG_DIR = platformdirs.user_config_path(
    "mewgenics_breeding_helper", appauthor="PurpleMyst"
)
CONFIG_FILE = CONFIG_DIR / "config.json"


def _find_gpak_path() -> str:
    """Find resources.gpak from common paths."""
    import os

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


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    version: int = 1
    rooms: list[RoomConfig] = Field(default_factory=lambda: list(DEFAULT_ROOM_CONFIGS))
    universals: list[Any] = Field(default_factory=list)
    target_builds: list[Any] = Field(default_factory=list)
    last_save_path: str | None = None

    @field_validator("universals", mode="before")
    @classmethod
    def parse_universals(cls, v: list[Any]) -> list[Any]:
        if not isinstance(v, list):
            return v
        parsed = []
        for t in v:
            if isinstance(t, dict):
                trait = create_trait(TraitCategory(t["category"]), t["key"])
                parsed.append(
                    UniversalTrait(trait=trait, weight_ens=t.get("weight_ens", 1.0))
                )
            elif isinstance(t, UniversalTrait):
                parsed.append(t)
            else:
                parsed.append(t)
        return parsed

    @field_serializer("universals", mode="wrap")
    def serialize_universals(self, v: list[Any], handler: Any) -> list[dict]:
        return [
            {
                "category": t.trait.category.value
                if hasattr(t.trait.category, "value")
                else t.trait.category,
                "key": t.trait.key,
                "weight_ens": t.weight_ens,
            }
            for t in v
        ]

    @field_validator("target_builds", mode="before")
    @classmethod
    def parse_target_builds(cls, v: list[Any]) -> list[Any]:
        if not isinstance(v, list):
            return v
        parsed = []
        for t in v:
            if isinstance(t, dict):
                build = TargetBuild(
                    name=t.get("name", "Unnamed Build"),
                    requirements=[
                        TraitWeight(
                            trait=create_trait(TraitCategory(b["category"]), b["key"]),
                            weight_ens=b.get("weight_ens", 1.0),
                        )
                        for b in t.get("requirements", [])
                    ],
                    anti_synergies=[
                        TraitWeight(
                            trait=create_trait(TraitCategory(b["category"]), b["key"]),
                            weight_ens=b.get("weight_ens", 1.0),
                        )
                        for b in t.get("anti_synergies", [])
                    ],
                    synergy_bonus_ens=t.get("synergy_bonus_ens", 0.0),
                )
                parsed.append(build)
            elif isinstance(t, TargetBuild):
                parsed.append(t)
            else:
                parsed.append(t)
        return parsed

    @field_serializer("target_builds", mode="wrap")
    def serialize_target_builds(self, v: list[Any], handler: Any) -> list[dict]:
        return [
            {
                "name": b.name,
                "requirements": [
                    {
                        "category": tw.trait.category.value
                        if hasattr(tw.trait.category, "value")
                        else tw.trait.category,
                        "key": tw.trait.key,
                        "weight_ens": tw.weight_ens,
                    }
                    for tw in b.requirements
                ],
                "anti_synergies": [
                    {
                        "category": tw.trait.category.value
                        if hasattr(tw.trait.category, "value")
                        else tw.trait.category,
                        "key": tw.trait.key,
                        "weight_ens": tw.weight_ens,
                    }
                    for tw in b.anti_synergies
                ],
                "synergy_bonus_ens": b.synergy_bonus_ens,
            }
            for b in v
        ]

    @classmethod
    def load(cls) -> Self:
        """Load configuration from disk or return defaults."""
        if CONFIG_FILE.exists():
            try:
                return cls.model_validate_json(CONFIG_FILE.read_text())
            except (ValueError, OSError):
                pass
        return cls()

    def save(self) -> None:
        """Save configuration to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(self.model_dump_json(indent=2))


class AppState:
    """Application state - runtime only, not persisted."""

    cats: list[Cat] = []
    save_data: SaveData | None = None
    room_configs: list[RoomConfig] = []
    results: OptimizationResult | None = None
    last_save_path: str | None = None
    game_data: GameData

    universals: list[UniversalTrait] = []
    target_builds: list[TargetBuild] = []

    selected_pair: ScoredPair | None = None
    selected_pair_index: int | None = None
    selected_result_room_key: str | None = None
    selected_cat_db_key: int | None = None

    def __init__(self) -> None:
        self.game_data = (
            GameData.from_gpak(p) if (p := _find_gpak_path()) else GameData.empty()
        )

    @classmethod
    def from_config(cls) -> Self:
        """Create AppState from persisted configuration."""
        config = ConfigModel.load()
        state = cls()
        state.room_configs = config.rooms
        state.universals = config.universals
        state.target_builds = config.target_builds
        state.last_save_path = config.last_save_path
        return state

    def save(self) -> None:
        """Persist current state to disk."""
        config = ConfigModel(
            rooms=self.room_configs,
            universals=self.universals,
            target_builds=self.target_builds,
            last_save_path=self.last_save_path,
        )
        config.save()

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
