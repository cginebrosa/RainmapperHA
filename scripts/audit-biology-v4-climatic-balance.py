#!/usr/bin/env python3
"""Audit Biology V4 climatic balance over a local Biology V3 benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_climatic_water_balance as water_balance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 6)
    weight = position - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 6)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": round(min(values), 6) if values else None,
        "p05": percentile(values, 0.05),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": round(max(values), 6) if values else None,
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.benchmark.read_text(encoding="utf-8"))
    samples = payload.get("samples", [])
    window_complete = Counter()
    reason_counts = Counter()
    source_exclusions = Counter()
    source_gate_codes = Counter()
    sample_failures = Counter()
    eto_values: list[float] = []
    balance_values: list[float] = []
    max_mass_error = 0.0
    audited = 0
    unique_area_cutoffs: set[tuple[str, str]] = set()

    for sample in samples if isinstance(samples, list) else []:
        metadata = sample.get("metadata", {})
        weather = metadata.get("weather_series", {})
        location = metadata.get("area_representative_location", {})
        source_lengths = [
            len(weather.get(key, []))
            for key in (
                "daily_dates",
                "daily_area_rain_idw_mean_mm",
                "daily_temp_min_corrected_c",
                "daily_temp_max_corrected_c",
            )
        ]
        if len(set(source_lengths)) != 1 or source_lengths[0] == 0:
            source_exclusions["source_daily_series_missing_or_unaligned"] += 1
            for reason in sample.get("quality", {}).get("training_exclusion_reasons", []):
                if isinstance(reason, dict) and reason.get("code"):
                    source_gate_codes[str(reason["code"])] += 1
            continue
        try:
            result = water_balance.build_climatic_water_balance(
                dates=[date.fromisoformat(value) for value in weather["daily_dates"]],
                rain_idw_mm=weather["daily_area_rain_idw_mean_mm"],
                temp_min_corrected_c=weather["daily_temp_min_corrected_c"],
                temp_max_corrected_c=weather["daily_temp_max_corrected_c"],
                latitude_deg=location["lat"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            sample_failures[str(exc)] += 1
            continue

        audited += 1
        unique_area_cutoffs.add(
            (str(metadata.get("area_id") or ""), str(metadata.get("cutoff_date") or ""))
        )
        quality = result["quality"]
        for reason, count in quality["missing_input_reason_counts"].items():
            reason_counts[reason] += int(count)
        for label, window in quality["window_coverage"].items():
            if window["complete"]:
                window_complete[label] += 1
        max_mass_error = max(
            max_mass_error, float(quality["water_balance_mass_error_max_mm"])
        )
        eto_values.extend(
            float(value)
            for value in result["metadata"]["daily_reference_evapotranspiration_mm"]
            if value is not None
        )
        balance_values.extend(
            float(value)
            for value in result["metadata"]["daily_climatic_water_balance_mm"]
            if value is not None
        )

    sample_count = len(samples) if isinstance(samples, list) else 0
    report = {
        "kind": "mushroom_biology_v4_climatic_balance_audit",
        "schema_version": 1,
        "status": "pass" if audited and not sample_failures else "fail",
        "contract_id": water_balance.CLIMATIC_WATER_BALANCE_CONTRACT_ID,
        "evapotranspiration_method": water_balance.EVAPOTRANSPIRATION_METHOD_ID,
        "input": {
            "benchmark_path": str(args.benchmark),
            "benchmark_sha256": sha256(args.benchmark),
            "feature_set_id": payload.get("feature_set", {}).get("id"),
            "rainfall_contract_id": payload.get("area_rainfall_contract_id"),
        },
        "coverage": {
            "sample_count": sample_count,
            "audited_sample_count": audited,
            "unique_area_cutoff_count": len(unique_area_cutoffs),
            "source_excluded_sample_count": sum(source_exclusions.values()),
            "computational_failure_sample_count": sum(sample_failures.values()),
            "complete_window_sample_counts": dict(sorted(window_complete.items())),
            "complete_window_sample_fractions": {
                label: round(window_complete[label] / audited, 6) if audited else 0.0
                for label, _youngest, _oldest in water_balance.FEATURE_WINDOWS
            },
        },
        "quality": {
            "missing_input_reason_counts": dict(sorted(reason_counts.items())),
            "source_exclusion_counts": dict(sorted(source_exclusions.items())),
            "source_exclusion_v3_gate_counts": dict(sorted(source_gate_codes.items())),
            "sample_failure_counts": dict(sorted(sample_failures.items())),
            "water_balance_mass_error_max_mm": round(max_mass_error, 9),
        },
        "distributions": {
            "daily_reference_evapotranspiration_mm": distribution(eto_values),
            "daily_climatic_water_balance_mm": distribution(balance_values),
        },
        "interpretation_limits": [
            "This audit validates implementation, units, coverage and invariants; it does not prove predictive value.",
            "Humidity remains a separate V4 predictor and is not removed because Hargreaves-Samani does not consume it.",
            "With the shared area temperature contract, balance(mean microarea IDW rain) equals mean(microarea balances); the nonlinear soil reservoir must still be calculated per microarea.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
