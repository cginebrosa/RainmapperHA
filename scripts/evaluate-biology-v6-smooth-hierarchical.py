#!/usr/bin/env python3
"""Evaluate smooth-lag and partial-pooling V6 without writing model artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import brier_score_loss

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_error_analysis as error_analysis
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_raw_weather as raw_weather
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_ml_tuning_catalog
from rainmapper_core.mushroom_ml_biology_v3_evaluation import chronological_group_split


ESTIMATORS = (
    "smooth_species_logistic_v1",
    "smooth_shared_logistic_v1",
    "smooth_partial_pooling_logistic_v1",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_split(samples: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        metadata = sample.get("metadata") or {}
        grouped[str(metadata.get("species_id"))][f"{metadata.get('area_id')}|{str(metadata.get('target_date'))[:4]}"] .append(sample)
    train, test = [], []
    for campaigns in grouped.values():
        ordered = sorted(campaigns.values(), key=lambda rows: max(str((row.get("metadata") or {}).get("target_date")) for row in rows))
        if len(ordered) < 2:
            train.extend(item for rows in ordered for item in rows)
            continue
        boundary = max(1, min(len(ordered) - 1, int(len(ordered) * 0.7)))
        train.extend(item for rows in ordered[:boundary] for item in rows)
        test.extend(item for rows in ordered[boundary:] for item in rows)
    return train, test


def species_ids(samples: list[dict]) -> list[str]:
    return [str((sample.get("metadata") or {}).get("species_id")) for sample in samples]


def select_joint_config(
    Z: np.ndarray, y: np.ndarray, species: list[str], samples: list[dict], *, partial: bool, group_days: int
) -> dict:
    inner = holdout._inner_splits(samples, group_days)
    if not inner:
        return {"C": 0.1, "deviation_scale": 4.0 if partial else None, "inner_selection_available": False}
    configs = [
        {"C": C, "deviation_scale": scale if partial else None}
        for C in (0.01, 0.1, 1.0)
        for scale in ((2.0, 4.0, 8.0) if partial else (None,))
    ]
    wins = Counter()
    details = {}
    order = sorted(set(species))
    for fold_index, (train_index, valid_index) in enumerate(inner):
        fold_scores = defaultdict(dict)
        for config_index, config in enumerate(configs):
            design_train = smooth.pooled_design(Z[train_index], [species[i] for i in train_index], species_order=order, deviation_scale=config["deviation_scale"])
            design_valid = smooth.pooled_design(Z[valid_index], [species[i] for i in valid_index], species_order=order, deviation_scale=config["deviation_scale"])
            try:
                model = smooth.fit_logistic(design_train, y[train_index], C=config["C"])
            except ValueError:
                continue
            probabilities = model.predict_proba(design_valid)[:, 1]
            for value in sorted(set(species[i] for i in valid_index)):
                indices = np.asarray([offset for offset, index in enumerate(valid_index) if species[index] == value], dtype=int)
                if len(indices):
                    fold_scores[value][config_index] = float(brier_score_loss(y[valid_index][indices], probabilities[indices]))
        for value, scores in fold_scores.items():
            if scores:
                best_score = min(scores.values())
                for config_index, score in scores.items():
                    if abs(score - best_score) <= 1e-6:
                        wins[config_index] += 1
        details[fold_index] = {value: scores for value, scores in fold_scores.items()}
    if not wins:
        return {"C": 0.1, "deviation_scale": 4.0 if partial else None, "inner_selection_available": False}
    selected_index = min(wins, key=lambda index: (-wins[index], configs[index]["C"], -(configs[index]["deviation_scale"] or 0)))
    return {**configs[selected_index], "inner_selection_available": True, "species_fold_wins": wins[selected_index]}


def evaluate_split(
    benchmark: dict,
    train: list[dict],
    test: list[dict],
    *,
    split_id: str,
    group_days: int,
    version_id: str = "biology_v6_smooth_hierarchical",
    profile_id: str = "smooth_weather_physical_state",
    window_days: int | None = None,
    tuning_catalog: dict | None = None,
) -> tuple[dict, list[dict]]:
    source_contracts = {
        str((sample.get("metadata") or {}).get("temporal_contract_id") or "")
        for sample in train + test
    }
    include_horizon = any(value.startswith("lag_event") for value in source_contracts)
    if len(source_contracts) != 1:
        raise ValueError("V6 evaluation requires one temporal contract")
    source_temporal_contract_id = next(iter(source_contracts))
    tuning_temporal_contract_id = (
        mushroom_ml_tuning_catalog.resolve_temporal_contract(
            tuning_catalog,
            version_id=version_id,
            profile_id=profile_id,
            source_temporal_contract_id=source_temporal_contract_id,
        )
        if tuning_catalog is not None
        else source_temporal_contract_id
    )
    if window_days is None:
        columns = smooth.raw_columns(include_phenology=True, include_horizon=include_horizon)
        preprocessor = smooth.SmoothLagPreprocessor()
    else:
        columns = smooth.raw_columns(
            include_phenology=True,
            include_horizon=include_horizon,
            channels=raw_weather.RAW_CHANNELS,
            window_days=window_days,
        )
        preprocessor = smooth.SmoothLagPreprocessor(
            channels=raw_weather.RAW_CHANNELS, window_days=window_days
        )
    X_train, y_train = holdout.matrix(train, columns)
    X_test, y_test = holdout.matrix(test, columns)
    preprocessor = preprocessor.fit(X_train)
    Z_train, Z_test = preprocessor.transform(X_train), preprocessor.transform(X_test)
    train_species, test_species = species_ids(train), species_ids(test)
    order = sorted(set(train_species))
    probabilities: dict[str, np.ndarray] = {}
    availability: dict[str, dict] = {}

    species_probabilities = np.full(len(test), np.nan)
    species_configs: dict[str, dict] = {}
    for value in order:
        train_index = np.asarray([i for i, item in enumerate(train_species) if item == value], dtype=int)
        test_index = np.asarray([i for i, item in enumerate(test_species) if item == value], dtype=int)
        if not len(test_index) or len(np.unique(y_train[train_index])) < 2:
            continue
        config = {"C": 0.1, "deviation_scale": None}
        if tuning_catalog is not None:
            config = dict(
                mushroom_ml_tuning_catalog.lookup(
                    tuning_catalog,
                    {
                        "version_id": version_id,
                        "temporal_contract_id": tuning_temporal_contract_id,
                        "profile_id": profile_id,
                        "estimator_id": ESTIMATORS[0],
                        "species_id": value,
                    },
                )["fit_config"]
            )
        species_configs[value] = config
        model = smooth.fit_logistic(
            Z_train[train_index], y_train[train_index], C=config["C"]
        )
        species_probabilities[test_index] = model.predict_proba(Z_test[test_index])[:, 1]
    probabilities[ESTIMATORS[0]] = species_probabilities
    availability[ESTIMATORS[0]] = {
        "configs_by_species": species_configs,
        "selection": "frozen tuning catalog" if tuning_catalog is not None else "predeclared conservative",
    }

    for estimator_id, partial in ((ESTIMATORS[1], False), (ESTIMATORS[2], True)):
        if tuning_catalog is None:
            config = select_joint_config(
                Z_train, y_train, train_species, train,
                partial=partial, group_days=group_days,
            )
        else:
            config = dict(
                mushroom_ml_tuning_catalog.lookup(
                    tuning_catalog,
                    {
                        "version_id": version_id,
                        "temporal_contract_id": tuning_temporal_contract_id,
                        "profile_id": profile_id,
                        "estimator_id": estimator_id,
                        "species_id": "all_species",
                    },
                )["fit_config"]
            )
        design_train = smooth.pooled_design(Z_train, train_species, species_order=order, deviation_scale=config["deviation_scale"])
        design_test = smooth.pooled_design(Z_test, test_species, species_order=order, deviation_scale=config["deviation_scale"])
        model = smooth.fit_logistic(design_train, y_train, C=config["C"])
        probabilities[estimator_id] = model.predict_proba(design_test)[:, 1]
        availability[estimator_id] = config

    report = {"split_id": split_id, "group_days": group_days, "species": {}, "selected_configs": availability}
    rows = []
    for value in sorted(set(test_species)):
        train_index = np.asarray([i for i, item in enumerate(train_species) if item == value], dtype=int)
        test_index = np.asarray([i for i, item in enumerate(test_species) if item == value], dtype=int)
        if not len(train_index) or not len(test_index):
            continue
        prevalence = float(np.mean(y_train[train_index]))
        species_report = {"n_train": len(train_index), "n_test": len(test_index), "estimators": {}}
        for estimator_id in ESTIMATORS:
            values = probabilities[estimator_id][test_index]
            if np.any(~np.isfinite(values)):
                species_report["estimators"][estimator_id] = {"available": False, "reason": "species training partition has one class"}
                continue
            metric = holdout.metrics(y_test[test_index], values)
            baseline = float(brier_score_loss(y_test[test_index], np.full(len(test_index), prevalence)))
            metric["brier_delta_vs_prevalence"] = round(baseline - metric["brier_score"], 6)
            species_report["estimators"][estimator_id] = {"available": True, "metrics": metric}
        report["species"][value] = species_report
        for index in test_index:
            sample = test[index]
            metadata = sample.get("metadata") or {}
            source_sample_id = str(sample.get("sample_id"))
            source_contract = str(metadata.get("temporal_contract_id") or "")
            v6_contract = (
                "lag_event_biology_v6_smooth_hierarchical_v2"
                if source_contract.startswith("lag_event")
                else "fixed_gap_7d_biology_v6_smooth_hierarchical_v2"
            )
            sample_id = f"{metadata.get('observation_id')}|{v6_contract}|h{int(metadata.get('horizon_days') or 7)}|{profile_id}"
            row_key = "|".join((version_id, profile_id, split_id, str(group_days), sample_id))
            rows.append({
                "row_key": row_key, "sample_id": sample_id, "source_sample_id": source_sample_id,
                "observation_id": metadata.get("observation_id"),
                "species_id": value, "area_id": metadata.get("area_id"), "micro_area_id": metadata.get("micro_area_id"),
                "target_date": metadata.get("target_date"), "cutoff_date": metadata.get("cutoff_date"),
                "horizon_days": int(metadata.get("horizon_days") or 7),
                "version_id": version_id,
                "profile_id": profile_id,
                "temporal_contract_id": v6_contract, "group_days": group_days,
                "split_id": split_id, "validation_group_id": metadata.get(f"validation_group_{group_days}d"),
                "campaign_block_id": f"{metadata.get('area_id')}|{str(metadata.get('target_date'))[:4]}" if split_id.startswith("campaign") else None,
                "prediction_target": sample.get("prediction_target"), "y_true": int(y_test[index]),
                "train_prevalence_probability": round(prevalence, 10),
                "estimator_probabilities": {
                    estimator_id: round(float(values[index]), 10)
                    for estimator_id, values in probabilities.items() if np.isfinite(values[index])
                },
                "diagnostic_weather_summary": metadata.get("diagnostic_weather_summary", {}),
            })
    return report, rows


def _selected_profiles(profile_keys: set[str]) -> list[dict]:
    """Resolve which V6 (version_id, profile_id, window_days) triples to evaluate."""
    windowed = [
        {
            "version_id": smooth.WINDOWED_VERSION_ID,
            "profile_id": smooth.windowed_profile_id(window_days),
            "window_days": window_days,
        }
        for window_days in raw_weather.WINDOW_DAYS_OPTIONS
    ]
    old = [
        {
            "version_id": "biology_v6_smooth_hierarchical",
            "profile_id": "smooth_weather_physical_state",
            "window_days": None,
        }
    ]
    if not profile_keys:
        return old
    selected = [
        profile
        for profile in old + windowed
        if f"{profile['version_id']}/{profile['profile_id']}" in profile_keys
    ]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--v5-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--profile-key", action="append")
    parser.add_argument("--tuning-catalog", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    profiles = _selected_profiles({str(value) for value in (args.profile_key or [])})
    tuning_catalog = load(args.tuning_catalog) if args.tuning_catalog else None
    all_rows, artifacts = [], {}
    for profile in profiles:
        version_id = profile["version_id"]
        profile_id = profile["profile_id"]
        window_days = profile["window_days"]
        for temporal in ("fixed", "lag"):
            benchmark = load(args.v5_dir / f"biology-v5-{temporal}.json")
            reference = holdout.eligible_samples(benchmark)
            for group_days in (7, 14):
                train, test = chronological_group_split(reference, group_days=group_days)
                split_id = f"fruiting_groups_{group_days}d"
                print(json.dumps({"temporal": temporal, "split": split_id, "profile_id": profile_id}), flush=True)
                report, rows = evaluate_split(
                    benchmark, train, test, split_id=split_id, group_days=group_days,
                    version_id=version_id, profile_id=profile_id, window_days=window_days,
                    tuning_catalog=tuning_catalog,
                )
                path = args.output_dir / f"comparison-{profile_id}-{temporal}-groups{group_days}.json"
                path.write_text(json.dumps({"kind": "biology_v6_smooth_hierarchical_comparison", "temporal": temporal,
                    "report": report, "model_artifact_written": False, "operational_candidate_trained": False}, indent=2) + "\n", encoding="utf-8")
                artifacts[path.name] = sha256(path)
                all_rows.extend(rows)
            train, test = campaign_split(reference)
            print(json.dumps({"temporal": temporal, "split": "campaign_area_year_70_30", "profile_id": profile_id}), flush=True)
            report, rows = evaluate_split(
                benchmark, train, test, split_id="campaign_area_year_70_30", group_days=14,
                version_id=version_id, profile_id=profile_id, window_days=window_days,
                tuning_catalog=tuning_catalog,
            )
            path = args.output_dir / f"sensitivity-{profile_id}-{temporal}-campaign.json"
            path.write_text(json.dumps({"kind": "biology_v6_campaign_sensitivity", "temporal": temporal,
                "report": report, "model_artifact_written": False, "operational_candidate_trained": False}, indent=2) + "\n", encoding="utf-8")
            artifacts[path.name] = sha256(path)
            all_rows.extend(rows)

    phases = error_analysis.assign_observed_phases(all_rows)
    errors = []
    for row in all_rows:
        row["observed_phase"] = phases.get(row["row_key"], "unknown_phase")
        diagnosed = error_analysis.shared_error_record(row, ESTIMATORS)
        if diagnosed["wrong_count"]:
            errors.append(diagnosed)
    predictions = args.output_dir / "heldout-predictions.jsonl"
    predictions.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in all_rows), encoding="utf-8")
    error_path = args.output_dir / "shared-errors.json"
    error_path.write_text(json.dumps({"rows": errors}) + "\n", encoding="utf-8")
    manifest = {
        "kind": "biology_v6_smooth_hierarchical_manifest", "source_snapshot": str(args.snapshot),
        "source_snapshot_manifest_sha256": sha256(args.snapshot / "MANIFEST.json"),
        "source_v5_manifest_sha256": sha256(args.v5_dir / "MANIFEST.json"),
        "row_count": len(all_rows), "unique_row_keys": len({row["row_key"] for row in all_rows}),
        "artifacts": artifacts, "predictions_sha256": sha256(predictions), "shared_errors_sha256": sha256(error_path),
        "lag_horizon_policy": "one fit then filter same heldout probabilities",
        "model_artifact_written": False, "operational_candidate_trained": False,
    }
    (args.output_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(all_rows), "unique": manifest["unique_row_keys"], "errors": len(errors)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
