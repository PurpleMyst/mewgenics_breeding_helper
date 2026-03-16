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
from .optimizer import optimize, score_pair, can_pair_gay

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
    "score_pair",
    "can_pair_gay",
]
