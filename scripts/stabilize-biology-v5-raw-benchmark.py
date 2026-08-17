#!/usr/bin/env python3
"""Compute grouped-bootstrap coefficient stability for V5 raw/no-calendar."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core.mushroom_ml_biology_v3_evaluation import chronological_group_split
from rainmapper_core.mushroom_ml_sparse_group import SparseGroupLogisticClassifier


RESAMPLES = 25
PROFILE = "raw_primary_no_calendar"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_for(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def grouped_bootstrap_indices(samples: list[dict], rng: np.random.Generator) -> np.ndarray | None:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, sample in enumerate(samples):
        metadata = sample.get("metadata") or {}
        groups[str(metadata.get("validation_group_7d") or index)].append(index)
    values = list(groups.values())
    for _attempt in range(100):
        chosen = rng.integers(0, len(values), size=len(values))
        indices = np.asarray([index for group_index in chosen for index in values[int(group_index)]], dtype=int)
        targets = {samples[index]["prediction_target"] for index in indices}
        if targets == {"favorable", "unfavorable"}:
            return indices
    return None


def fit_coefficients(estimator_id: str, config: dict, X: np.ndarray, y: np.ndarray, columns: list[str]) -> np.ndarray:
    scaled, _unused, _imputer, _scaler = holdout._preprocess(X, X)
    if estimator_id == holdout.V5_ESTIMATORS[0]:
        model = LogisticRegression(
            solver="saga", max_iter=750, random_state=42, tol=1e-3, **config
        )
    else:
        model = SparseGroupLogisticClassifier(
            groups=holdout._groups(columns), max_iter=600, tolerance=1e-4, **config
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", (FutureWarning, ConvergenceWarning))
        model.fit(scaled, y)
    return np.asarray(model.coef_[0], dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--v5-dir", required=True, type=Path)
    args = parser.parse_args()
    output_rows = []
    context_reports = []
    for temporal in ("fixed", "lag"):
        v3 = load(args.snapshot / f"biology-v3-{temporal}.json")
        v5 = load(args.v5_dir / f"biology-v5-{temporal}.json")
        columns = list(v5["feature_set"]["profiles"][PROFILE])
        v5_by_key = {holdout.comparison_key(row): row for row in holdout.eligible_samples(v5)}
        reference = [row for row in holdout.eligible_samples(v3) if holdout.comparison_key(row) in v5_by_key]
        train, _test = chronological_group_split(reference, group_days=7)
        train_keys = {holdout.comparison_key(row) for row in train}
        v5_train = [row for key, row in v5_by_key.items() if key in train_keys]
        comparison = load(args.v5_dir / f"comparison-{temporal}-groups7.json")
        species_reports = comparison["reports"][f"biology_v5|{PROFILE}"]["species"]
        for species_id, species_report in sorted(species_reports.items()):
            samples = [row for row in v5_train if str((row.get("metadata") or {}).get("species_id")) == species_id]
            if not samples:
                continue
            X, y = holdout.matrix(samples, columns)
            for estimator_id in holdout.V5_ESTIMATORS:
                result = (species_report.get("estimators") or {}).get(estimator_id) or {}
                if not result.get("available"):
                    context_reports.append({"temporal": temporal, "species_id": species_id,
                                            "estimator_id": estimator_id, "available": False,
                                            "reason": result.get("reason") or "outer estimator unavailable"})
                    continue
                config = result.get("selected_config") or {}
                rng = np.random.default_rng(seed_for(temporal, species_id, estimator_id, PROFILE))
                fitted = []
                attempts = 0
                while len(fitted) < RESAMPLES and attempts < RESAMPLES * 4:
                    attempts += 1
                    indices = grouped_bootstrap_indices(samples, rng)
                    if indices is None:
                        break
                    try:
                        fitted.append(fit_coefficients(estimator_id, config, X[indices], y[indices], columns))
                    except (ValueError, FloatingPointError):
                        continue
                context_reports.append({
                    "temporal": temporal, "species_id": species_id, "estimator_id": estimator_id,
                    "available": bool(fitted), "requested_resamples": RESAMPLES,
                    "completed_resamples": len(fitted), "fit_attempts": attempts,
                    "selected_config": config,
                })
                if not fitted:
                    continue
                coefficients = np.vstack(fitted)
                selected = np.abs(coefficients) > 1e-10
                for index, column in enumerate(columns):
                    values = coefficients[:, index]
                    nonzero = values[selected[:, index]]
                    frequency = float(np.mean(selected[:, index]))
                    sign_fraction = (
                        max(float(np.mean(nonzero > 0)), float(np.mean(nonzero < 0))) if len(nonzero) else 0.0
                    )
                    output_rows.append({
                        "temporal_contract_id": (samples[0].get("metadata") or {}).get("temporal_contract_id"),
                        "profile_id": PROFILE, "species_id": species_id, "estimator_id": estimator_id,
                        "feature": column, "selection_frequency": round(frequency, 6),
                        "sign_concordance": round(sign_fraction, 6),
                        "coefficient_median": round(float(np.median(values)), 10),
                        "coefficient_q25": round(float(np.quantile(values, 0.25)), 10),
                        "coefficient_q75": round(float(np.quantile(values, 0.75)), 10),
                        "stable_selected": frequency >= 0.70 and sign_fraction >= 0.80,
                        "resamples": len(fitted),
                    })
                print(json.dumps({"temporal": temporal, "species": species_id,
                                  "estimator": estimator_id, "resamples": len(fitted)}), flush=True)
    path = args.v5_dir / "feature-stability.json"
    path.write_text(json.dumps({
        "kind": "biology_v5_grouped_bootstrap_stability", "seed": 42,
        "requested_resamples": RESAMPLES, "profile_id": PROFILE,
        "contexts": context_reports, "rows": output_rows,
        "model_artifact_written": False, "operational_candidate_trained": False,
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(path), "rows": len(output_rows), "contexts": len(context_reports)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
