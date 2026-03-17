"""Room optimization logic for Mewgenics breeding."""

from .types import (
    RoomType,
    RoomConfig,
    RoomAssignment,
    ScoredPair,
    OptimizationParams,
    OptimizationResult,
    OptimizationStats,
    DEFAULT_ROOM_CONFIGS,
)
from .optimizer import optimize, optimize_sa, score_pair, can_pair_gay

__all__ = [
    "RoomType",
    "RoomConfig",
    "RoomAssignment",
    "ScoredPair",
    "OptimizationParams",
    "OptimizationResult",
    "OptimizationStats",
    "DEFAULT_ROOM_CONFIGS",
    "optimize",
    "optimize_sa",
    "score_pair",
    "can_pair_gay",
]
