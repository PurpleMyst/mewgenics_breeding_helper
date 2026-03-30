"""Cached scoring for breeding pair evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from mewgenics_parser import Cat, SaveData
from mewgenics_scorer import (
    TargetBuild,
    TraitWeight,
    calculate_pair_factors,
    calculate_pair_quality,
)

from .types import ScoredPair


@dataclass(slots=True)
class CachingScorer:
    """Thread-safe cached pair scorer for reuse across modules."""

    save_data: SaveData
    universals: list[TraitWeight] | None
    target_builds: list[TargetBuild] | None
    _memo: dict[tuple[int, int, float], ScoredPair | None] = field(
        default_factory=dict, init=False, repr=False
    )

    def score_pair(
        self,
        cat_a: Cat,
        cat_b: Cat,
        stimulation: float,
    ) -> ScoredPair | None:
        """Score a pair with memoization.

        Returns None if pair cannot be scored (e.g., missing trait data).
        Breeding compatibility is handled at the room level via Monte Carlo.
        """
        key = (
            min(cat_a.db_key, cat_b.db_key),
            max(cat_a.db_key, cat_b.db_key),
            stimulation,
        )
        if key in self._memo:
            return self._memo[key]

        try:
            factors = calculate_pair_factors(
                self.save_data,
                cat_a,
                cat_b,
                stimulation=stimulation,
                universals=self.universals,
                target_builds=self.target_builds,
            )
        except KeyError:
            self._memo[key] = None
            return None

        scored = ScoredPair(
            cat_a=cat_a,
            cat_b=cat_b,
            factors=factors,
            quality=calculate_pair_quality(factors),
            omp=factors.omp,
        )
        self._memo[key] = scored
        return scored
