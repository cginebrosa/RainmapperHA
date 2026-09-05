#!/usr/bin/env python3
"""Compare rainfall applicability gates on frozen external hold-out groups.

No estimator is fitted and no operational artifact is written.  Training-side
feature support is rebuilt after excluding the exact archived hold-out cases.
The current raw min/max gate is compared with two diagnostics:

* ``rain_log_tail``: rainfall above the observed maximum is a caution unless
  it is also at least three standard deviations away in ``log1p(mm)`` space;
* ``rain_never_vetoes``: rainfall excursions remain visible as cautions but
  can never cause abstention by themselves.

All non-rainfall features retain the current raw rule in every variant.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gc
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import joblib
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core.mushroom_ml_biology_v3_evaluation import (
    chronological_group_split,
)


TARGET_SPECIES = {
    "lactarius_deliciosus",
    "boletus_edulis",
    "boletus_pinophilus",
    "boletus_aereus",
    "amanita_caesarea",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--quality-catalog", required=True, type=Path)
    parser.add_argument("--artifacts-root", required=True, type=Path)
    parser.add_argument("--v3-fixed", required=True, type=Path)
    parser.add_argument("--v3-lag", required=True, type=Path)
    parser.add_argument("--v4-fixed", required=True, type=Path)
    parser.add_argument("--v4-lag", required=True, type=Path)
    parser.add_argument("--v5-fixed", required=True, type=Path)
    parser.add_argument("--v5-lag", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _candidate_key(row: Mapping[str, Any], estimator_id: object = None) -> tuple[Any, ...]:
    return (
        str(row.get("version_id") or ""),
        str(row.get("profile_id") or ""),
        str(row.get("temporal_contract_id") or ""),
        int(row.get("horizon_days") or 0),
        str(estimator_id if estimator_id is not None else row.get("estimator_id") or ""),
        str(row.get("species_id") or ""),
    )


def _selected_candidates(catalog: Mapping[str, Any]) -> set[tuple[Any, ...]]:
    result = set()
    for row in catalog.get("species_selections") or []:
        if not isinstance(row, Mapping) or row.get("species_id") not in TARGET_SPECIES:
            continue
        candidate = row.get("candidate")
        if not isinstance(candidate, Mapping):
            continue
        result.add(
            _candidate_key(
                {**candidate, "species_id": row.get("species_id")},
                candidate.get("estimator_id"),
            )
        )
    return result


def _source_name(candidate: tuple[Any, ...]) -> str:
    version, _profile, contract, _horizon, _estimator, _species = candidate
    family = "fixed" if str(contract).startswith("fixed_gap_") else "lag"
    if version in {"altitude_v2", "biology_v3"}:
        return f"v3_{family}"
    if version == "biology_v4":
        return f"v4_{family}"
    return f"v5_{family}"


def _feature_columns(root: Path, candidate: tuple[Any, ...]) -> list[str]:
    version, profile, contract, _horizon, estimator, _species = candidate
    generation = next(root.glob(f"{version}_*"))
    directory = generation / str(version) / str(contract) / str(profile) / str(estimator)
    artifact = next(directory.glob("*.joblib"))
    bundle = joblib.load(artifact)
    return [str(value) for value in bundle["feature_cols"]]


def _finite_values(samples: Iterable[Mapping[str, Any]], column: str) -> np.ndarray:
    values = []
    for sample in samples:
        value = (sample.get("predictive_features") or {}).get(column)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            values.append(numeric)
    return np.asarray(values, dtype=float)


def _support(samples: list[Mapping[str, Any]], columns: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in columns:
        values = _finite_values(samples, column)
        if not len(values):
            continue
        rain = column.startswith(("rain_", "rainfall_")) or "rain_mm" in column
        logs = np.log1p(np.maximum(values, 0.0)) if rain else values
        result[column] = {
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "log_mean": float(np.mean(logs)) if rain else None,
            "log_std": float(np.std(logs)) if rain else None,
        }
    return result


def _applicability(
    features: Mapping[str, Any],
    columns: list[str],
    support: Mapping[str, Mapping[str, Any]],
    policy: str,
) -> tuple[str, list[dict[str, Any]], int, int]:
    outside: list[dict[str, Any]] = []
    severe: list[dict[str, Any]] = []
    for column in columns:
        bounds = support.get(column)
        value = features.get(column)
        if bounds is None or value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric):
            continue
        minimum = float(bounds["min"])
        maximum = float(bounds["max"])
        if minimum <= numeric <= maximum:
            continue
        std = float(bounds["std"])
        raw_z = abs(numeric - float(bounds["mean"])) / std if std > 0 else None
        rain = column.startswith(("rain_", "rainfall_")) or "rain_mm" in column
        log_z = None
        if rain and numeric >= 0 and float(bounds.get("log_std") or 0) > 0:
            log_z = abs(
                math.log1p(numeric) - float(bounds.get("log_mean") or 0)
            ) / float(bounds["log_std"])
        detail = {
            "feature": column,
            "value": numeric,
            "training_min": minimum,
            "training_max": maximum,
            "raw_standard_deviations": raw_z,
            "log1p_standard_deviations": log_z,
            "rainfall": rain,
        }
        outside.append(detail)
        if policy == "current_raw":
            severe.append(detail)
        elif not rain:
            severe.append(detail)
        elif policy == "rain_log_tail" and (
            numeric < minimum or (log_z is not None and log_z >= 3.0)
        ):
            severe.append(detail)

    if policy == "current_raw":
        extreme = any(
            float(row.get("raw_standard_deviations") or 0.0) >= 3.0
            for row in severe
        )
    elif policy == "rain_log_tail":
        extreme = any(
            (
                float(row.get("log1p_standard_deviations") or 0.0)
                if row["rainfall"]
                else float(row.get("raw_standard_deviations") or 0.0)
            )
            >= 3.0
            for row in severe
        )
    else:
        extreme = any(
            float(row.get("raw_standard_deviations") or 0.0) >= 3.0
            for row in severe
        )
    status = (
        "outside_domain"
        if len(severe) / len(columns) >= 0.05 or extreme
        else "caution"
        if outside
        else "within_observed_range"
    )
    outside.sort(
        key=lambda row: float(
            row.get("log1p_standard_deviations")
            if row["rainfall"] and policy == "rain_log_tail"
            else row.get("raw_standard_deviations")
            or 0.0
        ),
        reverse=True,
    )
    rain_count = sum(1 for row in outside if row["rainfall"])
    return status, outside[:5], rain_count, len(outside) - rain_count


def _metrics(cases: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"count": 0, "coverage": 0.0, "brier_score": None}
    accepted = [case for case in cases if case["status"] != "outside_domain"]
    rejected = [case for case in cases if case["status"] == "outside_domain"]

    def brier(values: list[Mapping[str, Any]]) -> float | None:
        return (
            sum((float(row["probability"]) - int(row["y_true"])) ** 2 for row in values)
            / len(values)
            if values
            else None
        )

    return {
        "count": len(cases),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "coverage": len(accepted) / len(cases),
        "brier_score_accepted": brier(accepted),
        "brier_score_rejected": brier(rejected),
        "rejected_positive_count": sum(int(row["y_true"]) for row in rejected),
        "rejected_negative_count": sum(1 - int(row["y_true"]) for row in rejected),
        "rejected_examples": [dict(row) for row in rejected[:20]],
    }


def _released(
    current: list[Mapping[str, Any]], alternative: list[Mapping[str, Any]]
) -> dict[str, Any]:
    released = [
        alternative[index]
        for index, row in enumerate(current)
        if row["status"] == "outside_domain"
        and alternative[index]["status"] != "outside_domain"
    ]
    return {
        "count": len(released),
        "positive_count": sum(int(row["y_true"]) for row in released),
        "negative_count": sum(1 - int(row["y_true"]) for row in released),
        "brier_score": (
            sum(
                (float(row["probability"]) - int(row["y_true"])) ** 2
                for row in released
            )
            / len(released)
            if released
            else None
        ),
        "rain_only_count": sum(
            int(row.get("outside_nonrain_feature_count") or 0) == 0
            and int(row.get("outside_rain_feature_count") or 0) > 0
            for row in released
        ),
        "examples": [dict(row) for row in released[:20]],
    }


def main() -> int:
    args = _parser().parse_args()
    catalog = json.loads(args.quality_catalog.read_text(encoding="utf-8"))
    candidates = _selected_candidates(catalog)
    archived: dict[tuple[str, tuple[Any, ...]], list[dict[str, Any]]] = defaultdict(list)
    with args.holdout.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            probabilities = row.get("estimator_probabilities") or {}
            for candidate in candidates:
                if _candidate_key(row, candidate[4]) != candidate:
                    continue
                probability = probabilities.get(candidate[4])
                if probability is not None:
                    archived[(str(row.get("split_id") or ""), candidate)].append(
                        {**row, "probability": float(probability)}
                    )

    sources = {
        "v3_fixed": args.v3_fixed,
        "v3_lag": args.v3_lag,
        "v4_fixed": args.v4_fixed,
        "v4_lag": args.v4_lag,
        "v5_fixed": args.v5_fixed,
        "v5_lag": args.v5_lag,
    }
    split_cases: dict[str, dict[str, list[dict[str, Any]]]] = {
        split: {policy: [] for policy in ("current_raw", "rain_log_tail", "rain_never_vetoes")}
        for split in ("fruiting_groups_14d", "fruiting_groups_7d")
    }
    candidate_reports = []
    for source_name, source_path in sources.items():
        source_candidates = sorted(c for c in candidates if _source_name(c) == source_name)
        if not source_candidates:
            continue
        benchmark = json.loads(source_path.read_text(encoding="utf-8"))
        eligible = holdout.eligible_samples(benchmark)
        for candidate in source_candidates:
            version, profile, contract, horizon, estimator, species = candidate
            columns = _feature_columns(args.artifacts_root, candidate)
            shared = str(estimator).startswith(("smooth_shared", "smooth_partial"))
            population = (
                eligible
                if shared
                else [
                    sample
                    for sample in eligible
                    if str((sample.get("metadata") or {}).get("species_id")) == species
                ]
            )
            report = {"candidate": list(candidate), "feature_count": len(columns), "splits": {}}
            for split_id, group_days in (("fruiting_groups_14d", 14), ("fruiting_groups_7d", 7)):
                archive = archived.get((split_id, candidate), [])
                if not archive:
                    continue
                if shared:
                    train, _test = chronological_group_split(population, group_days=group_days)
                else:
                    test_keys = {
                        (str(row["observation_id"]), int(row["horizon_days"]))
                        for row in archive
                    }
                    train = [
                        sample
                        for sample in population
                        if holdout.comparison_key(sample) not in test_keys
                    ]
                support = _support(train, columns)
                sample_index = {
                    holdout.comparison_key(sample): sample for sample in population
                }
                policy_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in archive:
                    sample = sample_index.get(
                        (str(row["observation_id"]), int(row["horizon_days"]))
                    )
                    if sample is None:
                        continue
                    features = sample.get("predictive_features") or {}
                    for policy in ("current_raw", "rain_log_tail", "rain_never_vetoes"):
                        status, extremes, rain_count, nonrain_count = _applicability(
                            features, columns, support, policy
                        )
                        case = {
                            "species_id": species,
                            "area_id": row.get("area_id"),
                            "observation_id": row.get("observation_id"),
                            "target_date": row.get("target_date"),
                            "version_id": version,
                            "profile_id": profile,
                            "horizon_days": horizon,
                            "estimator_id": estimator,
                            "probability": row["probability"],
                            "y_true": int(row["y_true"]),
                            "status": status,
                            "outside_rain_feature_count": rain_count,
                            "outside_nonrain_feature_count": nonrain_count,
                            "most_extreme": extremes,
                        }
                        policy_cases[policy].append(case)
                        split_cases[split_id][policy].append(case)
                report["splits"][split_id] = {
                    **{
                        policy: _metrics(values)
                        for policy, values in policy_cases.items()
                    },
                    "released_vs_current": {
                        policy: _released(policy_cases["current_raw"], values)
                        for policy, values in policy_cases.items()
                        if policy != "current_raw"
                    },
                }
            candidate_reports.append(report)
        del benchmark, eligible
        gc.collect()

    output = {
        "schema_version": "1.0",
        "kind": "mushroom_rain_applicability_holdout_audit",
        "operational_artifacts_written": False,
        "target_species": sorted(TARGET_SPECIES),
        "selected_candidate_count": len(candidates),
        "policies": {
            "current_raw": "current min/max, 5% outside or any raw z >= 3",
            "rain_log_tail": (
                "rain above max is caution unless log1p(mm) z >= 3; non-rain unchanged"
            ),
            "rain_never_vetoes": "rain excursions are caution only; non-rain unchanged",
        },
        "aggregate": {
            split: {
                **{policy: _metrics(cases) for policy, cases in policies.items()},
                "released_vs_current": {
                    policy: _released(policies["current_raw"], cases)
                    for policy, cases in policies.items()
                    if policy != "current_raw"
                },
            }
            for split, policies in split_cases.items()
        },
        "candidates": candidate_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output.resolve()), "candidates": len(candidates)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
