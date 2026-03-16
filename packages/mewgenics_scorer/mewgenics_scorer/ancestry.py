"""Ancestry and inbreeding risk calculations."""
from dataclasses import dataclass

from mewgenics_parser import Cat

MIN_CONTRIB = 0.0001
MAX_DEPTH = 14
COI_THRESHOLD = 0.25


def _ancestor_contributions(cat: Cat | None) -> dict[Cat, float]:
    """Compute Σ(0.5^depth) for each ancestor of cat."""
    if cat is None:
        return {}
    contribs: dict[Cat, float] = {}
    stack: list[tuple[Cat, int, float]] = [(cat, 0, 1.0)]
    while stack:
        node, depth, prob = stack.pop()
        contribs[node] = contribs.get(node, 0.0) + prob
        if depth >= MAX_DEPTH:
            continue
        half_prob = prob * 0.5
        if half_prob < MIN_CONTRIB:
            continue
        for parent in (node.parent_a, node.parent_b):
            if parent is not None:
                stack.append((parent, depth + 1, half_prob))
    return contribs


def build_ancestor_contribs(cats: list[Cat]) -> dict[int, dict[Cat, float]]:
    """Batch compute ancestor contributions for all cats."""
    ordered = sorted(cats, key=lambda c: c.generation)
    memo: dict[int, dict[Cat, float]] = {}
    result: dict[int, dict[Cat, float]] = {}
    for cat in ordered:
        contribs: dict[Cat, float] = {cat: 1.0}
        for parent in (cat.parent_a, cat.parent_b):
            if parent is None:
                continue
            pc = memo.get(id(parent))
            if pc is None:
                pc = _ancestor_contributions(parent)
                memo[id(parent)] = pc
            for anc, prob in pc.items():
                new_prob = prob * 0.5
                if new_prob < MIN_CONTRIB:
                    continue
                contribs[anc] = contribs.get(anc, 0.0) + new_prob
        memo[id(cat)] = contribs
        result[cat.db_key] = contribs
    return result


def coi_from_contribs(ca: dict[Cat, float], cb: dict[Cat, float]) -> float:
    """Compute raw COI from two ancestor-contribution dicts."""
    if not ca or not cb:
        return 0.0
    if len(ca) > len(cb):
        ca, cb = cb, ca
    coi = 0.0
    for anc, prob_a in ca.items():
        prob_b = cb.get(anc)
        if prob_b is not None:
            coi += prob_a * prob_b
    return coi * 0.5


def risk_percent(coi: float) -> float:
    """Convert raw COI to risk percentage (0.25 CoI = 100%)."""
    return max(0.0, min(100.0, (coi / COI_THRESHOLD) * 100.0))
