"""Type definitions for mewgenics_scorer ENS architecture."""

from dataclasses import dataclass
from uuid import UUID

from mewgenics_parser.traits import Trait


@dataclass(slots=True, frozen=True)
class TraitWeight:
    """A trait with an ENS weight for build evaluation."""

    trait: Trait
    weight_ens: float


@dataclass(slots=True, frozen=True)
class TargetBuild:
    """A named build with requirements, anti-synergies, and synergy bonus."""

    id: UUID
    name: str
    requirements: tuple[TraitWeight, ...]
    anti_synergies: tuple[TraitWeight, ...]
    synergy_bonus_ens: float = 0.0
