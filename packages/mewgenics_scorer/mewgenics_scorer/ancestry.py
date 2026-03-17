"""Ancestry and inbreeding risk calculations."""

from dataclasses import dataclass

from mewgenics_parser import Cat

MIN_CONTRIB = 0.0001
MAX_DEPTH = 14
COI_THRESHOLD = 0.25


@dataclass
class AncestorData:
    """Tracks structural lineage data for Mewgenics-specific CoI calculations."""

    cat: Cat
    prob: float
    min_depth: int


def _ancestor_contributions(cat: Cat | None) -> dict[int, AncestorData]:
    """
    Compute Σ(0.5^depth) and track minimum depth for each ancestor of cat.
    Returns dict of id(cat) -> AncestorData.
    """
    if cat is None:
        return {}

    contribs: dict[int, AncestorData] = {}
    # Stack stores: (Node, Depth, Probability)
    stack: list[tuple[Cat, int, float]] = [(cat, 0, 1.0)]

    while stack:
        node, depth, prob = stack.pop()
        node_id = id(node)

        # Aggregate probabilities and keep the shortest path depth
        if node_id in contribs:
            existing = contribs[node_id]
            existing.prob += prob
            existing.min_depth = min(existing.min_depth, depth)
        else:
            contribs[node_id] = AncestorData(node, prob, depth)

        if depth >= MAX_DEPTH:
            continue

        half_prob = prob * 0.5
        if half_prob < MIN_CONTRIB:
            continue

        for parent in (node.parent_a, node.parent_b):
            if parent is not None:
                stack.append((parent, depth + 1, half_prob))

    return contribs


def build_ancestor_contribs(cats: list[Cat]) -> dict[int, dict[int, AncestorData]]:
    """
    Batch compute ancestor contributions for all cats.
    Returns dict[db_key, dict[id(cat), AncestorData]].
    """
    ordered = sorted(cats, key=lambda c: c.generation)
    memo: dict[int, dict[int, AncestorData]] = {}
    result: dict[int, dict[int, AncestorData]] = {}

    for cat in ordered:
        # Initialize the contribution dictionary with the cat itself
        contribs: dict[int, AncestorData] = {id(cat): AncestorData(cat, 1.0, 0)}

        for parent in (cat.parent_a, cat.parent_b):
            if parent is None:
                continue

            parent_id = id(parent)
            pc = memo.get(parent_id)

            # If parent isn't memoized yet, compute it (fallback for safety)
            if pc is None:
                pc = _ancestor_contributions(parent)
                memo[parent_id] = pc

            # Merge parent's ancestors into the current cat's ancestors
            for anc_id, anc_data in pc.items():
                new_prob = anc_data.prob * 0.5
                new_depth = anc_data.min_depth + 1

                if new_prob < MIN_CONTRIB:
                    continue

                if anc_id in contribs:
                    existing = contribs[anc_id]
                    existing.prob += new_prob
                    existing.min_depth = min(existing.min_depth, new_depth)
                else:
                    contribs[anc_id] = AncestorData(anc_data.cat, new_prob, new_depth)

        memo[id(cat)] = contribs
        result[cat.db_key] = contribs

    return result


def coi_from_contribs(
    ca: dict[int, AncestorData], cb: dict[int, AncestorData]
) -> float:
    """
    Compute Mewgenics-adjusted COI from two ancestor-contribution dicts.
    Applies the Closeness >= 5 cutoff and the (1 + fA) ancestor penalty.
    """
    if not ca or not cb:
        return 0.0

    if len(ca) > len(cb):
        ca, cb = cb, ca

    coi = 0.0
    for anc_id, data_a in ca.items():
        data_b = cb.get(anc_id)
        if data_b is not None:
            d_a = data_a.min_depth
            d_b = data_b.min_depth

            # Mewgenics logic: Condense sibling relations from 2 lines to 1
            if d_a == 0 or d_b == 0:
                closeness = d_a + d_b
            else:
                closeness = d_a + d_b - 1

            # Circuit breaker: Closeness of 5 or higher drops CoI to 0
            if closeness >= 5:
                continue

            # Fetch ancestor's CoI (fA). Default to 0.0 if not yet assigned.
            f_a = getattr(data_a.cat, "coi", 0.0)

            # Base probability overlap * Wright's 0.5 * Mewgenics Ancestor Multiplier
            coi += 0.5 * (data_a.prob * data_b.prob) * (1.0 + f_a)

    return coi
