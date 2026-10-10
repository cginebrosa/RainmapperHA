"""Three-way accounting and the predeclared development-only threshold rule."""
from collections import Counter

GRID = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


def decision(row, threshold=0.60):
    answer = row["decision_a"]
    if answer not in {"favorable", "unfavorable", "abstain"}:
        raise ValueError("Unknown recommendation")
    if answer == "favorable":
        probability = row["probability"]
        if probability is None or not 0.60 <= probability <= 1:
            raise ValueError("Favorable A without a valid favorable probability")
        if probability < threshold:
            return "abstain"
    return answer


def validate_rows(rows):
    by_observation = {}
    for row in rows:
        identity = row["observation_id"]
        value = by_observation.setdefault(identity, {"y": row["y"], "episode": row["episode_id"], "h": set()})
        if row["y"] not in (0, 1) or row["y"] != value["y"] or row["episode_id"] != value["episode"]:
            raise ValueError("Inconsistent observation labels/episodes")
        if row["horizon"] in value["h"]:
            raise ValueError("Duplicate observation/horizon")
        value["h"].add(row["horizon"])
    if any(value["h"] != set(range(1, 8)) for value in by_observation.values()):
        raise ValueError("Every observation must retain all seven horizons, including abstentions")


def confusion(rows, threshold=0.60, *, weight=1.0):
    cells = {f"{label}_{answer}": 0 for label in ("positive", "negative") for answer in ("favorable", "unfavorable", "abstain")}
    for row in rows:
        cells[("positive" if row["y"] else "negative") + "_" + decision(row, threshold)] += weight
    return cells


def select_threshold(rows):
    validate_rows(rows)
    observations = {r["observation_id"]: r for r in rows}
    support = Counter(r["y"] for r in observations.values())
    groups = {y: {r["episode_id"] for r in observations.values() if r["y"] == y} for y in (0, 1)}
    sufficient = all(support[y] >= 5 and len(groups[y]) >= 3 for y in (0, 1))
    baseline = confusion(rows, weight=1/7)
    curve = []
    for threshold in GRID:
        counts = confusion(rows, threshold, weight=1/7)
        favored_groups = {r["episode_id"] for r in rows if decision(r, threshold) == "favorable"}
        tp, fp = counts["positive_favorable"], counts["negative_favorable"]
        useful = (tp + 1e-9 >= 0.8 * baseline["positive_favorable"] and
                  tp + 1e-9 >= 0.25 * support[1] and tp+fp + 1e-9 >= 5 and len(favored_groups) >= 3)
        improved = fp < baseline["negative_favorable"] - 1e-9
        curve.append({"threshold": threshold, **counts, "favored_groups": len(favored_groups),
                      "admissible": sufficient and useful and improved and threshold > .60})
    candidates = [r for r in curve if r["admissible"]]
    winner = min(candidates, key=lambda r: (round(r["negative_favorable"], 10),
        -round(r["positive_favorable"], 10), r["threshold"])) if candidates else None
    return {"threshold": winner["threshold"] if winner else .60,
            "reason": "development_rule_selected" if winner else "insufficient_development_support" if not sufficient else "no_admissible_strict_improvement",
            "support": {"positive_observations": support[1], "negative_observations": support[0],
                        "positive_groups": len(groups[1]), "negative_groups": len(groups[0])},
            "curve": curve}
