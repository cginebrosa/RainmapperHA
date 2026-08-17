#!/usr/bin/env python3
"""Evaluate V4 blocks on strictly matched rows without writing model artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core.mushroom_ml_biology_v3_evaluation import evaluate_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--group-days", required=True, type=int, choices=(7, 14))
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def materialize_samples(
    payload: dict[str, object],
    *,
    block: str,
    eligibility_block: str,
    soil_variant_id: str | None = None,
    columns: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    columns = list(columns) if columns is not None else payload["feature_blocks"][block]
    variant = payload.get("soil_variants", {}).get(soil_variant_id, {}) if soil_variant_id else {}
    state_catalog = variant.get("area_state_catalog", {}) if isinstance(variant, dict) else {}
    rows: list[dict[str, object]] = []
    for source in payload.get("samples", []):
        quality = source.get("quality", {})
        eligible = bool(quality.get("eligibility_by_block", {}).get(eligibility_block))
        predictive = dict(source.get("predictive_features", {}))
        state = None
        if soil_variant_id:
            key = source.get("metadata", {}).get("soil_state_key")
            state = state_catalog.get(key)
            if isinstance(state, dict):
                predictive.update(state.get("predictive_features", {}))
            if eligibility_block == "soil_water":
                eligible = (
                    bool(quality.get("eligibility_by_block", {}).get("climatic_balance"))
                    and isinstance(state, dict)
                    and bool(state.get("quality", {}).get("training_eligible"))
                    and all(predictive.get(name) is not None for name in payload["feature_blocks"]["soil_water"])
                )
        source_metadata = deepcopy(source.get("metadata", {}).get("source_v3_metadata", {}))
        rows.append(
            {
                "sample_id": source.get("sample_id"),
                "prediction_target": source.get("prediction_target"),
                "predictive_features": {name: predictive.get(name) for name in columns},
                "quality": {"training_eligible": eligible},
                "metadata": source_metadata,
            }
        )
    return rows


def evaluate_profile(
    payload: dict[str, object],
    *,
    blocks: list[str],
    matched_to: str,
    group_days: int,
    soil_variant_id: str | None = None,
) -> dict[str, object]:
    reports: dict[str, object] = {}
    for block in blocks:
        benchmark = {
            "samples": materialize_samples(
                payload,
                block=block,
                eligibility_block=matched_to,
                soil_variant_id=soil_variant_id,
            ),
            "feature_set": {
                "predictive_feature_cols": payload["feature_blocks"][block]
            },
        }
        reports[block] = evaluate_benchmark(
            benchmark,
            group_days=group_days,
            feature_families={"active_full": lambda _name: True},
        )
    return {
        "matched_to_block": matched_to,
        "soil_variant_id": soil_variant_id,
        "blocks": reports,
    }


def evaluate_extended_weather_contributions(
    payload: dict[str, object],
    *,
    group_days: int,
) -> dict[str, object]:
    temporal_id = str(payload.get("temporal_contract_id") or "")
    reports: dict[str, object] = {}
    contribution_ids = tuple(biology_v4.EXTENDED_WEATHER_CONTRIBUTION_GROUPS) + (
        "extended_weather_all",
    )
    for contribution_id in contribution_ids:
        columns = biology_v4.extended_weather_contribution_columns(
            temporal_id, contribution_id
        )
        benchmark = {
            "samples": materialize_samples(
                payload,
                block="extended_weather",
                eligibility_block="climatic_balance",
                columns=columns,
            ),
            "feature_set": {"predictive_feature_cols": list(columns)},
        }
        reports[contribution_id] = evaluate_benchmark(
            benchmark,
            group_days=group_days,
            feature_families={"active_full": lambda _name: True},
        )
    return {
        "matched_to_block": "climatic_balance",
        "profiles": reports,
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.benchmark.read_text(encoding="utf-8"))
    report = {
        "kind": "mushroom_biology_v4_matched_block_evaluation",
        "schema_version": 1,
        "temporal_contract_id": payload.get("temporal_contract_id"),
        "group_days": args.group_days,
        "climate_matched": evaluate_profile(
            payload,
            blocks=["core", "extended_weather", "climatic_balance"],
            matched_to="climatic_balance",
            group_days=args.group_days,
        ),
        "extended_weather_contributions_climate_matched": (
            evaluate_extended_weather_contributions(
                payload,
                group_days=args.group_days,
            )
        ),
        "soil_variant_matched": {
            variant_id: evaluate_profile(
                payload,
                blocks=["core", "extended_weather", "climatic_balance", "soil_water"],
                matched_to="soil_water",
                group_days=args.group_days,
                soil_variant_id=variant_id,
            )
            for variant_id in sorted(payload.get("soil_variants", {}))
        },
        "model_artifact_written": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "temporal_contract_id": report["temporal_contract_id"], "group_days": args.group_days}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
