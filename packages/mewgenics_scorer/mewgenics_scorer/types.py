"""Type definitions for mewgenics_scorer ENS architecture."""

from dataclasses import dataclass

from mewgenics_parser.traits import Trait


@dataclass(slots=True)
class TraitWeight:
    """A trait with an ENS weight for build evaluation."""

    trait: Trait
    weight_ens: float


@dataclass(slots=True)
class TargetBuild:
    """A named build with requirements, anti-synergies, and synergy bonus."""

    name: str
    requirements: list[TraitWeight]
    anti_synergies: list[TraitWeight]
    synergy_bonus_ens: float


@dataclass(slots=True)
class UniversalTrait:
    """A universal trait that applies to all kittens with an ENS weight."""

    trait: Trait
    weight_ens: float
