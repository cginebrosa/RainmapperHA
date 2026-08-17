"""Causal daily continuity diagnostics for Biology V4 benchmark sequences."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping, Sequence


CONTINUITY_DIAGNOSTIC_CONTRACT_ID = "species_area_daily_continuity_diagnostic_v1"


def _day(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def summarize_daily_sequence(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = 0.5,
) -> dict[str, object]:
    """Measure flicker without changing probabilities or observed labels."""

    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be strictly between zero and one")
    normalized: list[tuple[date, float, str | None]] = []
    for row in rows:
        day = _day(row.get("date"))
        probability = float(row.get("probability"))
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be between zero and one")
        raw_label = row.get("observed_label")
        label = str(raw_label) if raw_label in {"favorable", "unfavorable"} else None
        normalized.append((day, probability, label))
    normalized.sort(key=lambda item: item[0])
    dates = [item[0] for item in normalized]
    if len(set(dates)) != len(dates):
        raise ValueError("daily continuity sequence contains duplicate dates")

    predictions = [probability >= threshold for _day_value, probability, _label in normalized]
    isolated_positive = 0
    isolated_negative = 0
    total_variation = 0.0
    consecutive_transitions = 0
    gap_count = 0
    observed_label_reversals = 0
    run_lengths: list[dict[str, object]] = []
    run_value: bool | None = None
    run_length = 0

    for index, (day, probability, label) in enumerate(normalized):
        consecutive = index == 0 or day == normalized[index - 1][0] + timedelta(days=1)
        if index > 0:
            if consecutive:
                total_variation += abs(probability - normalized[index - 1][1])
                consecutive_transitions += 1
                previous_label = normalized[index - 1][2]
                if label is not None and previous_label is not None and label != previous_label:
                    observed_label_reversals += 1
            else:
                gap_count += 1
        value = predictions[index]
        if run_value is None or not consecutive or value != run_value:
            if run_value is not None:
                run_lengths.append({"prediction": "favorable" if run_value else "unfavorable", "days": run_length})
            run_value = value
            run_length = 1
        else:
            run_length += 1
        if 0 < index < len(normalized) - 1:
            previous_day = normalized[index - 1][0]
            next_day = normalized[index + 1][0]
            if day == previous_day + timedelta(days=1) and next_day == day + timedelta(days=1):
                triple = predictions[index - 1 : index + 2]
                isolated_positive += int(triple == [False, True, False])
                isolated_negative += int(triple == [True, False, True])
    if run_value is not None:
        run_lengths.append({"prediction": "favorable" if run_value else "unfavorable", "days": run_length})

    return {
        "predictive_features": {},
        "quality": {
            "daily_row_count": len(normalized),
            "consecutive_transition_count": consecutive_transitions,
            "date_gap_count": gap_count,
            "observed_label_count": sum(label is not None for _day_value, _probability, label in normalized),
        },
        "metadata": {
            "contract_id": CONTINUITY_DIAGNOSTIC_CONTRACT_ID,
            "threshold": threshold,
            "isolated_positive_days": isolated_positive,
            "isolated_negative_days": isolated_negative,
            "probability_total_variation": round(total_variation, 6),
            "prediction_run_lengths": run_lengths,
            "observed_label_reversals": observed_label_reversals,
            "probabilities_modified": False,
            "observed_labels_modified": False,
        },
    }


def evaluate_daily_continuity(
    benchmark: Mapping[str, object],
    daily_feature_rows: Sequence[Mapping[str, object]],
    *,
    group_days: int,
    estimator_ids: Sequence[str] | None = None,
    threshold: float = 0.5,
) -> dict[str, object]:
    """Fit transient benchmark models and diagnose causal daily probabilities.

    Daily rows contain weather-derived predictors for an area/date, not an
    observed target.  Observed hold-out labels are attached only after
    prediction so they cannot influence either the fit or the probability.
    """

    import numpy as np  # noqa: PLC0415

    from rainmapper_core import mushroom_ml_biology_v3_evaluation as evaluation  # noqa: PLC0415
    from rainmapper_core import mushroom_ml_experiment_trainer as trainer  # noqa: PLC0415

    normalized_benchmark = evaluation._eligible_samples(dict(benchmark))
    train, test = evaluation.chronological_group_split(
        normalized_benchmark, group_days=group_days
    )
    feature_set = benchmark.get("feature_set")
    feature_set = feature_set if isinstance(feature_set, Mapping) else {}
    columns = [
        str(value)
        for value in (
            feature_set.get("predictive_feature_cols")
            or feature_set.get("feature_cols")
            or []
        )
    ]
    if not columns:
        raise ValueError("continuity benchmark has no predictive columns")
    selected_estimators = tuple(estimator_ids or trainer.EXPERIMENT_ESTIMATOR_IDS)
    unknown = sorted(set(selected_estimators) - set(trainer.EXPERIMENT_ESTIMATOR_IDS))
    if unknown:
        raise ValueError("unknown continuity estimators: " + ", ".join(unknown))

    eligible_daily: list[dict[str, object]] = []
    exclusion_counts: dict[str, int] = {}
    for source in daily_feature_rows:
        quality = source.get("quality")
        quality = quality if isinstance(quality, Mapping) else {}
        predictive = source.get("predictive_features")
        predictive = predictive if isinstance(predictive, Mapping) else {}
        metadata = source.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        missing = [column for column in columns if predictive.get(column) is None]
        if not bool(quality.get("training_eligible", True)) or missing:
            code = "daily_quality_ineligible" if not bool(
                quality.get("training_eligible", True)
            ) else "daily_predictive_features_missing"
            exclusion_counts[code] = exclusion_counts.get(code, 0) + 1
            continue
        target_date = str(metadata.get("target_date") or source.get("date") or "")
        area_id = str(metadata.get("area_id") or "")
        if not target_date or not area_id:
            exclusion_counts["daily_identity_missing"] = (
                exclusion_counts.get("daily_identity_missing", 0) + 1
            )
            continue
        eligible_daily.append(
            {
                "target_date": target_date,
                "area_id": area_id,
                "predictive_features": dict(predictive),
            }
        )

    reports: dict[str, object] = {}
    species_ids = sorted(
        {
            str((row.get("metadata") or {}).get("species_id") or "")
            for row in test
            if str((row.get("metadata") or {}).get("species_id") or "")
        }
    )
    for species_id in species_ids:
        species_train = [
            row
            for row in train
            if str((row.get("metadata") or {}).get("species_id") or "") == species_id
        ]
        species_test = [
            row
            for row in test
            if str((row.get("metadata") or {}).get("species_id") or "") == species_id
        ]
        if not species_train or not species_test:
            continue
        X_train, y_train = evaluation._matrix(species_train, columns)
        if len(np.unique(y_train)) < 2:
            reports[species_id] = {
                "available": False,
                "reason": "chronological training partition has a single class",
            }
            continue
        first_test = min(
            _day((row.get("metadata") or {}).get("target_date")) for row in species_test
        )
        last_test = max(
            _day((row.get("metadata") or {}).get("target_date")) for row in species_test
        )
        test_areas = {
            str((row.get("metadata") or {}).get("area_id") or "")
            for row in species_test
        }
        candidate_rows = [
            row
            for row in eligible_daily
            if row["area_id"] in test_areas
            and first_test <= _day(row["target_date"]) <= last_test
        ]
        observed: dict[tuple[str, str], str] = {}
        for row in species_test:
            metadata = row.get("metadata") or {}
            key = (str(metadata.get("area_id") or ""), str(metadata.get("target_date") or ""))
            label = str(row.get("prediction_target") or "")
            if label == "favorable" or key not in observed:
                observed[key] = label

        estimator_reports: dict[str, object] = {}
        for estimator_id in selected_estimators:
            reason = trainer._estimator_unavailable_reason(estimator_id, y_train)
            if estimator_id == "knn_distance_v1" and len(y_train) < 7:
                reason = "KNN requires at least seven training samples"
            if reason is not None:
                estimator_reports[estimator_id] = {"available": False, "reason": reason}
                continue
            model = trainer._pipeline(estimator_id)
            model.fit(X_train, y_train)
            by_area: dict[str, list[dict[str, object]]] = {}
            daily_matrix = np.asarray(
                [
                    [float(row["predictive_features"][column]) for column in columns]
                    for row in candidate_rows
                ],
                dtype=float,
            )
            probabilities = (
                model.predict_proba(daily_matrix)[:, 1]
                if len(candidate_rows)
                else np.asarray([], dtype=float)
            )
            for row, raw_probability in zip(candidate_rows, probabilities, strict=True):
                probability = float(raw_probability)
                key = (str(row["area_id"]), str(row["target_date"]))
                by_area.setdefault(str(row["area_id"]), []).append(
                    {
                        "date": str(row["target_date"]),
                        "probability": round(probability, 8),
                        "observed_label": observed.get(key),
                    }
                )
            estimator_reports[estimator_id] = {
                "available": True,
                "areas": {
                    area_id: {
                        "daily_probabilities": sorted(rows, key=lambda item: str(item["date"])),
                        "diagnostic": summarize_daily_sequence(rows, threshold=threshold),
                    }
                    for area_id, rows in sorted(by_area.items())
                },
            }
        reports[species_id] = {
            "available": True,
            "training_sample_count": len(species_train),
            "held_out_sample_count": len(species_test),
            "held_out_date_range": [first_test.isoformat(), last_test.isoformat()],
            "estimators": estimator_reports,
        }

    return {
        "schema_version": "1.0",
        "kind": "biology_v4_daily_continuity_evaluation",
        "contract_id": CONTINUITY_DIAGNOSTIC_CONTRACT_ID,
        "feature_set_id": feature_set.get("id"),
        "group_days": group_days,
        "predictive_feature_cols": columns,
        "daily_input_row_count": len(daily_feature_rows),
        "daily_eligible_row_count": len(eligible_daily),
        "daily_exclusion_counts": dict(sorted(exclusion_counts.items())),
        "species": reports,
        "causality": {
            "fit_rows": "chronological training partition only",
            "daily_rows": "weather-derived features available at each row cutoff",
            "observed_labels": "attached after prediction for diagnostics only",
        },
        "probabilities_modified": False,
        "model_artifact_written": False,
    }
