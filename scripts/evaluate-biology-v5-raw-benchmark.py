#!/usr/bin/env python3
"""Evaluate V2/V3/V4/V5 locally and retain every held-out probability."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_biology_v3_physical as biology_v3_physical
from rainmapper_core import mushroom_ml_error_analysis as error_analysis
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_raw_weather as raw_weather
from rainmapper_core.mushroom_ml_biology_v3_evaluation import (
    build_observation_altitude_v2_common_idw_benchmark,
    chronological_group_split,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--v5-dir", required=True, type=Path)
    parser.add_argument("--profile-key", action="append")
    parser.add_argument("--tuning-catalog", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _campaign_split(samples: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        metadata = sample.get("metadata") or {}
        species = str(metadata.get("species_id") or "")
        campaign = f"{metadata.get('area_id')}|{str(metadata.get('target_date'))[:4]}"
        grouped[species][campaign].append(sample)
    train, test = [], []
    for campaigns in grouped.values():
        ordered = sorted(
            campaigns.values(),
            key=lambda rows: max(str((row.get("metadata") or {}).get("target_date")) for row in rows),
        )
        if len(ordered) < 2:
            train.extend(item for rows in ordered for item in rows)
            continue
        boundary = max(1, min(len(ordered) - 1, int(len(ordered) * 0.7)))
        train.extend(item for rows in ordered[:boundary] for item in rows)
        test.extend(item for rows in ordered[boundary:] for item in rows)
    return train, test


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "row_key", "sample_id", "observation_id", "species_id", "area_id",
        "micro_area_id", "target_date", "cutoff_date", "horizon_days",
        "temporal_contract_id", "validation_group_id", "campaign_block_id",
        "version_id", "profile_id", "group_days", "split_id",
        "prediction_target", "y_true", "train_prevalence_probability",
        "observed_phase", "estimator_probabilities", "diagnostic_weather_summary", "coverage",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: json.dumps(row.get(field), ensure_ascii=False, sort_keys=True)
                if isinstance(row.get(field), (dict, list))
                else row.get(field)
                for field in fields
            })


def main() -> int:
    args = parse_args()
    args.v5_dir.mkdir(parents=True, exist_ok=True)
    selected = {str(value) for value in (args.profile_key or [])}
    tuning_catalog = _load(args.tuning_catalog) if args.tuning_catalog else None
    needs_v4 = (
        not selected
        or any(key.startswith("biology_v4/") for key in selected)
        or "biology_v3/common_idw_plus_physical_state" in selected
    )
    needs_v5 = not selected or any(
        key.startswith("biology_v5_raw_weather_discovery/")
        or key.startswith(f"{raw_weather.WINDOWED_VERSION_ID}/")
        for key in selected
    )
    sources = {
        "fixed": {
            "v3": _load(args.snapshot / "biology-v3-fixed.json"),
            "v4": _load(args.snapshot / "biology-v4-fixed.json") if needs_v4 else None,
            "v5": _load(args.v5_dir / "biology-v5-fixed.json") if needs_v5 else None,
        },
        "lag": {
            "v3": _load(args.snapshot / "biology-v3-lag.json"),
            "v4": _load(args.snapshot / "biology-v4-lag.json") if needs_v4 else None,
            "v5": _load(args.v5_dir / "biology-v5-lag.json") if needs_v5 else None,
        },
    }
    all_reports: dict[str, object] = {}
    all_rows: list[dict] = []
    all_selections: list[dict] = []
    for temporal_name, source in sources.items():
        v2 = build_observation_altitude_v2_common_idw_benchmark(source["v3"])
        available_datasets = {
            "altitude_v2|common_idw": (v2, "altitude_v2", "common_idw", "current"),
            "biology_v3|core": (source["v3"], "biology_v3", "core", "current"),
        }
        if source["v4"] is not None:
            available_datasets.update(
                {
                    "biology_v3|common_idw_plus_physical_state": (
                        biology_v3_physical.materialize_benchmark(source["v4"]),
                        "biology_v3",
                        biology_v3_physical.PROFILE_ID,
                        "current",
                    ),
                    "biology_v4|extended_weather": (
                        biology_v4.materialize_comparison_benchmark(
                            source["v4"], profile_id="extended_weather"
                        ),
                        "biology_v4", "extended_weather", "current",
                    ),
                    "biology_v4|climatic_balance": (
                        biology_v4.materialize_comparison_benchmark(
                            source["v4"], profile_id="climatic_balance"
                        ),
                        "biology_v4", "climatic_balance", "current",
                    ),
                }
            )
        if source["v5"] is not None:
            for profile_id in (
                "raw_primary", "raw_primary_no_calendar", "raw_primary_plus_physical",
                "raw_primary_plus_physical_no_calendar", "raw_primary_plus_physical_state",
                "raw_primary_plus_physical_state_no_calendar",
            ):
                available_datasets[f"biology_v5|{profile_id}"] = (
                    source["v5"], "biology_v5_raw_weather_discovery", profile_id, "v5"
                )
            for window_days in raw_weather.WINDOW_DAYS_OPTIONS:
                profile_id = raw_weather.windowed_profile_id(window_days)
                available_datasets[f"biology_v5_windowed|{profile_id}"] = (
                    source["v5"], raw_weather.WINDOWED_VERSION_ID, profile_id, "v5"
                )
        datasets = {
            name: dataset
            for name, dataset in available_datasets.items()
            if not selected or f"{dataset[1]}/{dataset[2]}" in selected
        }
        if not datasets:
            continue
        eligible_maps = {
            name: {holdout.comparison_key(row): row for row in holdout.eligible_samples(dataset[0])}
            for name, dataset in datasets.items()
        }
        common = set.intersection(*(set(rows) for rows in eligible_maps.values()))
        reference_name = (
            "biology_v3|core" if "biology_v3|core" in eligible_maps else next(iter(eligible_maps))
        )
        reference = [row for key, row in eligible_maps[reference_name].items() if key in common]
        for group_days in (7, 14):
            train, test = chronological_group_split(reference, group_days=group_days)
            train_keys = {holdout.comparison_key(row) for row in train}
            test_keys = {holdout.comparison_key(row) for row in test}
            comparison_id = f"{temporal_name}-groups{group_days}"
            reports = {}
            for name, (benchmark, version_id, profile_id, mode) in datasets.items():
                print(json.dumps({"comparison": comparison_id, "dataset": name}), flush=True)
                report, rows, selections = holdout.evaluate_dataset(
                    benchmark,
                    version_id=version_id,
                    profile_id=profile_id,
                    group_days=group_days,
                    train_keys=train_keys,
                    test_keys=test_keys,
                    mode=mode,
                    tuning_catalog=tuning_catalog,
                )
                reports[name] = report
                all_rows.extend(rows)
                all_selections.extend(selections)
            comparison = {
                "kind": "biology_v2_v3_v4_v5_row_level_comparison",
                "temporal_contract": temporal_name,
                "group_days": group_days,
                "jointly_eligible": len(common),
                "train_rows": len(train_keys),
                "test_rows": len(test_keys),
                "reports": reports,
                "model_artifact_written": False,
                "operational_candidate_trained": False,
            }
            path = args.v5_dir / f"comparison-{comparison_id}.json"
            path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            all_reports[comparison_id] = {"path": path.name, "sha256": sha256(path)}

        campaign_train, campaign_test = _campaign_split(reference)
        campaign_train_keys = {holdout.comparison_key(row) for row in campaign_train}
        campaign_test_keys = {holdout.comparison_key(row) for row in campaign_test}
        campaign_reports = {}
        campaign_profiles = (
            (
                "raw_primary_no_calendar", "raw_primary", "raw_primary_plus_physical_no_calendar",
                "raw_primary_plus_physical", "raw_primary_plus_physical_state_no_calendar",
                "raw_primary_plus_physical_state",
            )
            if not selected
            else (
                ("raw_primary_plus_physical_state",)
                if "biology_v5_raw_weather_discovery/raw_primary_plus_physical_state" in selected
                else ()
            )
        )
        for profile in campaign_profiles:
            report, rows, selections = holdout.evaluate_dataset(
                source["v5"],
                version_id="biology_v5_raw_weather_discovery",
                profile_id=profile,
                group_days=14,
                train_keys=campaign_train_keys,
                test_keys=campaign_test_keys,
                mode="v5",
                split_id="campaign_area_year_70_30",
                tuning_catalog=tuning_catalog,
            )
            campaign_reports[profile] = report
            all_rows.extend(rows)
            all_selections.extend(selections)
        if campaign_profiles:
            campaign_path = args.v5_dir / f"sensitivity-{temporal_name}-campaign.json"
            campaign_path.write_text(
                json.dumps({
                    "kind": "biology_v5_campaign_sensitivity",
                    "temporal_contract": temporal_name,
                    "train_rows": len(campaign_train_keys),
                    "test_rows": len(campaign_test_keys),
                    "reports": campaign_reports,
                    "model_artifact_written": False,
                    "operational_candidate_trained": False,
                }, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            all_reports[f"{temporal_name}-campaign"] = {"path": campaign_path.name, "sha256": sha256(campaign_path)}

    phases = error_analysis.assign_observed_phases(all_rows)
    error_rows = []
    for row in all_rows:
        row["observed_phase"] = phases.get(row["row_key"], "unknown_phase")
        estimator_ids = list(holdout.V5_ESTIMATORS if row["version_id"].startswith("biology_v5") else holdout.CURRENT_ESTIMATORS)
        diagnosed = error_analysis.shared_error_record(row, estimator_ids)
        if diagnosed["wrong_count"]:
            error_rows.append(diagnosed)

    jsonl_path = args.v5_dir / "heldout-predictions.jsonl"
    jsonl_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_rows), encoding="utf-8")
    csv_path = args.v5_dir / "heldout-predictions.csv"
    _write_csv(csv_path, all_rows)
    selected_path = args.v5_dir / "selected-features.json"
    selected_path.write_text(json.dumps({"rows": all_selections}, ensure_ascii=False) + "\n", encoding="utf-8")
    errors_path = args.v5_dir / "shared-errors.json"
    errors_path.write_text(json.dumps({"rows": error_rows}, ensure_ascii=False) + "\n", encoding="utf-8")
    prediction_manifest = {
        "kind": "biology_v5_heldout_predictions_manifest",
        "row_count": len(all_rows),
        "unique_row_keys": len({row["row_key"] for row in all_rows}),
        "jsonl_sha256": sha256(jsonl_path),
        "csv_sha256": sha256(csv_path),
        "selected_features_sha256": sha256(selected_path),
        "shared_errors_sha256": sha256(errors_path),
        "comparisons": all_reports,
        "lag_horizon_policy": "one fit then filter same heldout probabilities",
        "model_artifact_written": False,
        "operational_candidate_trained": False,
    }
    manifest_path = args.v5_dir / "heldout-predictions-manifest.json"
    manifest_path.write_text(json.dumps(prediction_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"heldout_rows": len(all_rows), "shared_error_rows": len(error_rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
