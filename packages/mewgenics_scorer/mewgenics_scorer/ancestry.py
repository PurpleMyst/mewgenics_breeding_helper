"""Ancestry and inbreeding risk calculations."""

from dataclasses import dataclass

from mewgenics_parser import Cat

MIN_CONTRIB = 0.0001
MAX_DEPTH = 14
COI_THRESHOLD = 0.25


def _ancestor_contributions(cat: Cat | None) -> dict[int, tuple[Cat, float]]:
    """Compute Σ(0.5^depth) for each ancestor of cat. Returns dict of id(cat) -> (cat, contribution)."""
    if cat is None:
        return {}
    contribs: dict[int, tuple[Cat, float]] = {}
    stack: list[tuple[Cat, int, float]] = [(cat, 0, 1.0)]
    while stack:
        node, depth, prob = stack.pop()
        node_id = id(node)
        existing = contribs.get(node_id)
        if existing:
            contribs[node_id] = (existing[0], existing[1] + prob)
        else:
            contribs[node_id] = (node, prob)
        if depth >= MAX_DEPTH:
            continue
        half_prob = prob * 0.5
        if half_prob < MIN_CONTRIB:
            continue
        for parent in (node.parent_a, node.parent_b):
            if parent is not None:
                stack.append((parent, depth + 1, half_prob))
    return contribs


def build_ancestor_contribs(cats: list[Cat]) -> dict[int, dict[int, float]]:
    """Batch compute ancestor contributions for all cats.

    Returns dict[db_key, dict[id(cat), contribution]].
    """
    ordered = sorted(cats, key=lambda c: c.generation)
    memo: dict[int, dict[int, float]] = {}
    result: dict[int, dict[int, float]] = {}
    for cat in ordered:
        contribs: dict[int, float] = {id(cat): 1.0}
        for parent in (cat.parent_a, cat.parent_b):
            if parent is None:
                continue
            parent_id = id(parent)
            pc = memo.get(parent_id)
            if pc is None:
                raw_contribs = _ancestor_contributions(parent)
                pc = {cid: prob for cid, (_, prob) in raw_contribs.items()}
                memo[parent_id] = pc
            for anc_id, prob in pc.items():
                new_prob = prob * 0.5
                if new_prob < MIN_CONTRIB:
                    continue
                contribs[anc_id] = contribs.get(anc_id, 0.0) + new_prob
        memo[id(cat)] = contribs
        result[cat.db_key] = contribs
    return result


def coi_from_contribs(ca: dict[int, float], cb: dict[int, float]) -> float:
    """Compute raw COI from two ancestor-contribution dicts."""
    if not ca or not cb:
        return 0.0
    if len(ca) > len(cb):
        ca, cb = cb, ca
    coi = 0.0
    for anc_id, prob_a in ca.items():
        prob_b = cb.get(anc_id)
        if prob_b is not None:
            coi += prob_a * prob_b
    return coi * 0.5


def risk_percent(coi: float) -> float:
    """Convert raw COI to risk percentage (0.25 CoI = 100%)."""
    return max(0.0, min(100.0, (coi / COI_THRESHOLD) * 100.0))
