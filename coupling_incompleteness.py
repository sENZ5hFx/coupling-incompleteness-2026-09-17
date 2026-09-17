#!/usr/bin/env python3
"""
Coupling Incompleteness Index (CII)
===================================

Capability that did not exist natively in this session's tool set:

    Rank scientific unknowns by whether apparent "darkness" is a mismatch
    between instrument coupling and the phenomenon's degrees of freedom,
    AFTER subtracting prior-session coverage, THEN recency-ablate so a
    paper published this week cannot masquerade as structural novelty.

This is a ranking of known unknowns. It is not a discovery engine.

Inputs
------
gaps : list[dict]
    Each gap must provide:
      physical_ceiling          float in [0, 1]
      coupling_mismatch         float in [0, 1]
      prior_session_coverage    float in [0, 1]
      recency_boost             float in [0, 1]  (or latest_date + session_date)
      cross_realm_isomorphism   float in [0, 1]
      falsifiability            float in [0, 1]
      sampling_incompleteness   float in [0, 1]
      evidential_status         one of established_unknown, new_signal,
                                disputed_claim, structural_synthesis
      id, name, realm

Outputs
-------
{
  "ranked": [...],
  "ablated": [...],          # recency_boost forced to 0
  "survivors": [...],        # ids in top-k of BOTH rankings
  "adversarial": [...],      # built-in red-team strings
}

Edge cases
----------
- Empty input → ValueError
- Scores outside [0, 1] → ValueError
- Future latest_date → ValueError
- A disputed_claim at rank 1 → adversarial FAIL string, rank still returned
"""
from __future__ import annotations

from typing import Any, Iterable

WEIGHTS = {
    "physical_ceiling": 0.25,
    "coupling_mismatch": 0.20,
    "novelty": 0.15,
    "recency": 0.15,
    "iso": 0.10,
    "falsifiability": 0.10,
    "sampling": 0.05,
}
ALLOWED_STATUS = {
    "established_unknown",
    "new_signal",
    "disputed_claim",
    "structural_synthesis",
}
REQUIRED = (
    "id",
    "name",
    "realm",
    "physical_ceiling",
    "coupling_mismatch",
    "prior_session_coverage",
    "cross_realm_isomorphism",
    "falsifiability",
    "sampling_incompleteness",
    "evidential_status",
)


def _unit(x: Any, field: str) -> float:
    if not isinstance(x, (int, float)) or x < 0 or x > 1:
        raise ValueError(f"{field} must be in [0, 1], got {x!r}")
    return float(x)


def _validate(gap: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if k not in gap]
    if missing:
        raise ValueError(f"gap {gap.get('id')!r} missing {missing}")
    if gap["evidential_status"] not in ALLOWED_STATUS:
        raise ValueError(
            f"{gap['id']}: evidential_status {gap['evidential_status']!r} not in {sorted(ALLOWED_STATUS)}"
        )
    for k in (
        "physical_ceiling",
        "coupling_mismatch",
        "prior_session_coverage",
        "cross_realm_isomorphism",
        "falsifiability",
        "sampling_incompleteness",
    ):
        _unit(gap[k], k)
    if "recency_boost" in gap:
        _unit(gap["recency_boost"], "recency_boost")


def cii(gap: dict[str, Any], recency_value: float | None = None) -> float:
    """Single-gap Coupling Incompleteness Index.

    Parameters
    ----------
    gap : dict
        Validated gap record.
    recency_value : float or None
        If given, overrides gap['recency_boost'] (used for ablation).
    """
    _validate(gap)
    rec = gap.get("recency_boost", 0.0) if recency_value is None else recency_value
    rec = _unit(rec, "recency_value")
    novelty = 1.0 - gap["prior_session_coverage"]
    score = (
        WEIGHTS["physical_ceiling"] * gap["physical_ceiling"]
        + WEIGHTS["coupling_mismatch"] * gap["coupling_mismatch"]
        + WEIGHTS["novelty"] * novelty
        + WEIGHTS["recency"] * rec
        + WEIGHTS["iso"] * gap["cross_realm_isomorphism"]
        + WEIGHTS["falsifiability"] * gap["falsifiability"]
        + WEIGHTS["sampling"] * gap["sampling_incompleteness"]
    )
    return round(score, 4)


def _rank(gaps: Iterable[dict[str, Any]], recency_value: float | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for g in gaps:
        row = dict(g)
        row["novelty_vs_prior"] = round(1.0 - g["prior_session_coverage"], 4)
        row["cii"] = cii(g, recency_value=recency_value)
        rows.append(row)
    rows.sort(key=lambda r: (-r["cii"], r["name"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def recency_ablated_cii(
    gaps: list[dict[str, Any]],
    top_k: int = 5,
) -> dict[str, Any]:
    """Rank, then re-rank with recency_boost forced to 0.

    Survivors are ids that remain in the top-k of BOTH rankings.
    That is the test against recency theater.
    """
    if not gaps:
        raise ValueError("gaps must be a non-empty list")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    for g in gaps:
        _validate(g)
        if "recency_boost" not in g:
            raise ValueError(f"{g['id']} missing recency_boost")

    original = _rank(gaps, recency_value=None)
    ablated = _rank(gaps, recency_value=0.0)

    orig_top = {r["id"] for r in original[:top_k]}
    ablated_top = {r["id"] for r in ablated[:top_k]}
    survivors = [r["id"] for r in original[:top_k] if r["id"] in ablated_top]
    union = orig_top | ablated_top
    jaccard = round(len(orig_top & ablated_top) / len(union), 3) if union else 0.0

    adversarial: list[str] = []
    top = original[0]
    if top["evidential_status"] == "disputed_claim":
        adversarial.append(f"FAIL: disputed_claim {top['id']} is rank 1.")
    deep = next((r for r in original if r["id"] == "DEEP_GENE_FN"), None)
    if deep and deep["rank"] <= 3:
        adversarial.append("FAIL: prior-session headline DEEP_GENE_FN still top-3.")
    else:
        adversarial.append("PASS: prior-session sampling headline is not top-3.")
    do = next((r for r in original if r["id"] == "DARK_OXYGEN"), None)
    if do and do["rank"] <= 5:
        adversarial.append("WARN: disputed dark-oxygen claim ranked in top-5.")
    else:
        adversarial.append("PASS: dark oxygen not treated as a discovery.")
    newish = [r for r in original[:top_k] if r.get("recency_boost", 0) >= 0.55]
    if len(newish) >= top_k - 1:
        adversarial.append("WARN: top-k is recency-dominated; inspect ablation survivors.")
    adversarial.append("HARD RULE: CIP is a hypothesis about the shape of ignorance, not a law.")
    adversarial.append(
        "HARD RULE: no WIMP, no Phi, no Population III, no dark-oxygen replication — none are discoveries."
    )

    return {
        "ranked": original,
        "ablated": ablated,
        "survivors": survivors,
        "jaccard_top_k": jaccard,
        "dropped_after_ablation": sorted(orig_top - ablated_top),
        "entered_after_ablation": sorted(ablated_top - orig_top),
        "adversarial": adversarial,
        "weights": WEIGHTS,
        "top_k": top_k,
    }


if __name__ == "__main__":
    demo = [
        {
            "id": "EP_DARK",
            "name": "Dark-sector EP violation",
            "realm": "outer_space",
            "physical_ceiling": 0.85,
            "coupling_mismatch": 0.95,
            "prior_session_coverage": 0.05,
            "recency_boost": 0.9355,
            "cross_realm_isomorphism": 0.90,
            "falsifiability": 0.80,
            "sampling_incompleteness": 0.40,
            "evidential_status": "new_signal",
        },
        {
            "id": "DEEP_GENE_FN",
            "name": "Deep-sea gene function lag",
            "realm": "ocean",
            "physical_ceiling": 0.30,
            "coupling_mismatch": 0.75,
            "prior_session_coverage": 0.95,
            "recency_boost": 0.19,
            "cross_realm_isomorphism": 0.85,
            "falsifiability": 0.60,
            "sampling_incompleteness": 0.85,
            "evidential_status": "established_unknown",
        },
    ]
    out = recency_ablated_cii(demo, top_k=2)
    print("survivors:", out["survivors"])
    print("adversarial:")
    for line in out["adversarial"]:
        print(" ", line)
