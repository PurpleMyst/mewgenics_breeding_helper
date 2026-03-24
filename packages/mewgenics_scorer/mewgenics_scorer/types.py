"""Type definitions for mewgenics_scorer."""

from dataclasses import dataclass
from mewgenics_parser.traits import Trait


@dataclass(slots=True)
class TraitRequirement:
    """A trait to score pair coverage for, with an associated weight."""

    trait: Trait
    weight: float = 5.0
