"""Comparable hold-out evidence for the non-operational V2--V6 catalog."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


SCHEMA_VERSION = "1.0"
KIND = "mushroom_ml_quality_catalog"

VERSION_CAUTIONS = {
    "altitude_v2": (
        "Referencia histórica del predictor actual; no es una versión validada ni "
        "se presupone superior. Usa ventanas meteorológicas cortas diseñadas a mano."
    ),
    "biology_v3": (
        "Añade estructura biológica, pero la muestra independiente sigue siendo pequeña "
        "y la mejora no es uniforme entre especies."
    ),
    "biology_v4": (
        "Representa mejor continuidad y balance climático; esas mejoras físicas no han "
        "producido una mejora estable del error predictivo."
    ),
    "biology_v5_raw_weather_discovery": (
        "Deja seleccionar historia meteorológica cruda regularizada; con pocos episodios "
        "puede elegir retardos correlacionados e inestables."
    ),
    "biology_v6_smooth_hierarchical": (
        "Suaviza retardos y comparte información entre especies; el pooling puede dar una "
        "señal aparentemente firme a especies con poco soporte propio."
    ),
    "biology_v5_windowed_raw_weather": (
        "Sucesora de V5 con ventana predictiva de 30/60/90 días en vez de 365; con pocos "
        "episodios puede elegir retardos correlacionados e inestables dentro de la ventana."
    ),
    "biology_v6_windowed_smooth_hierarchical": (
        "Sucesora de V6 con ventana predictiva de 30/60/90 días en vez de 365; el pooling "
        "puede dar una señal aparentemente firme a especies con poco soporte propio."
    ),
}


def _rows(path: Path, *, version_id: str = "", profile_id: str = "") -> Iterable[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            if version_id:
                row.setdefault("version_id", version_id)
            if profile_id:
                row.setdefault("profile_id", profile_id)
            yield row


def _family(contract_id: object) -> str:
    value = str(contract_id or "")
    if value.startswith("fixed_gap_"):
        return "fixed"
    if value.startswith("lag_event_"):
        return "lag"
    return "unknown"


def _calibration(y: np.ndarray, probabilities: np.ndarray) -> tuple[float, list[dict[str, Any]]]:
    bins: list[dict[str, Any]] = []
    error = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        mask = (probabilities >= lower) & (
            probabilities <= upper if upper >= 1.0 else probabilities < upper
        )
        if not np.any(mask):
            continue
        predicted = float(np.mean(probabilities[mask]))
        observed = float(np.mean(y[mask]))
        error += float(np.mean(mask)) * abs(predicted - observed)
        bins.append(
            {
                "lower": lower,
                "upper": round(upper, 1),
                "n": int(np.sum(mask)),
                "predicted_mean": round(predicted, 6),
                "observed_mean": round(observed, 6),
            }
        )
    return round(error, 6), bins


def build_catalog(
    v2_v5_path: Path,
    v6_path: Path,
    *,
    snapshot_id: str,
    profile_keys: list[str] | None = None,
    expected_estimators: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Aggregate row-level hold-out predictions without averaging species."""
    grouped: dict[tuple[str, ...], list[tuple[int, float, float]]] = defaultdict(list)
    row_groups: dict[tuple[str, ...], int] = defaultdict(int)
    selected = set(profile_keys or [])
    sources = (
        _rows(v2_v5_path),
        _rows(
            v6_path,
            version_id="biology_v6_smooth_hierarchical",
            profile_id="smooth_weather_physical_state",
        ),
    )
    for source in sources:
        for row in source:
            version_id = str(row.get("version_id") or "")
            profile_id = str(row.get("profile_id") or "")
            species_id = str(row.get("species_id") or "")
            family = _family(row.get("temporal_contract_id"))
            horizon = str(int(row.get("horizon_days") or 0))
            probabilities = row.get("estimator_probabilities") or {}
            profile_key = f"{version_id}/{profile_id}"
            if (
                not all((version_id, profile_id, species_id))
                or family == "unknown"
                or (selected and profile_key not in selected)
            ):
                continue
            try:
                y_true = int(row["y_true"])
                prevalence = float(row["train_prevalence_probability"])
            except (KeyError, TypeError, ValueError):
                continue
            base_key = (version_id, profile_id, family, horizon, species_id)
            row_groups[base_key] += 1
            estimator_ids = set(probabilities)
            if expected_estimators is not None:
                estimator_ids.update(expected_estimators.get(profile_key, []))
            for estimator_id in estimator_ids:
                metric_key = (
                    version_id,
                    profile_id,
                    family,
                    horizon,
                    species_id,
                    str(estimator_id),
                )
                grouped[metric_key]
                raw_probability = probabilities.get(estimator_id)
                try:
                    probability = float(raw_probability)
                except (TypeError, ValueError):
                    continue
                grouped[metric_key].append((y_true, probability, prevalence))
    entries = []
    for key, values in sorted(grouped.items()):
        version_id, profile_id, family, horizon, species_id, estimator_id = key
        total_rows = row_groups[(version_id, profile_id, family, horizon, species_id)]
        y = np.asarray([value[0] for value in values], dtype=int)
        probabilities = np.asarray([value[1] for value in values], dtype=float)
        prevalence = np.asarray([value[2] for value in values], dtype=float)
        brier = float(brier_score_loss(y, probabilities)) if len(values) else None
        baseline = float(brier_score_loss(y, prevalence)) if len(values) else None
        both_classes = len(np.unique(y)) == 2
        delta = baseline - brier if brier is not None and baseline is not None else None
        calibration_error, calibration_bins = (
            _calibration(y, probabilities) if len(values) else (None, [])
        )
        if len(values) < 8 or not both_classes or delta is None:
            evidence = "insufficient"
        elif delta > 0:
            evidence = "better_than_prevalence"
        else:
            evidence = "worse_than_prevalence"
        entries.append(
            {
                "version_id": version_id,
                "profile_id": profile_id,
                "temporal_family": family,
                "horizon_days": int(horizon),
                "species_id": species_id,
                "estimator_id": estimator_id,
                "n_test": len(values),
                "n_test_total": total_rows,
                "abstention_count": total_rows - len(values),
                "test_positive_count": int(y.sum()),
                "test_negative_count": int(len(y) - y.sum()),
                "both_test_classes": both_classes,
                "brier_score": round(brier, 6) if brier is not None else None,
                "prevalence_brier_score": round(baseline, 6) if baseline is not None else None,
                "brier_delta_vs_prevalence": round(delta, 6) if delta is not None else None,
                "roc_auc": round(float(roc_auc_score(y, probabilities)), 6) if both_classes else None,
                "expected_calibration_error": calibration_error,
                "calibration_bins": calibration_bins,
                "evidence": evidence,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "snapshot_id": snapshot_id,
        "split_id": "fruiting_groups_7d",
        "entries": entries,
        "version_cautions": dict(VERSION_CAUTIONS),
        "species_metrics_are_never_averaged": True,
    }


def lookup(catalog: Mapping[str, Any], model_ref: Mapping[str, object]) -> dict[str, Any]:
    family = _family(model_ref.get("temporal_contract_id"))
    wanted = (
        str(model_ref.get("version_id") or ""),
        str(model_ref.get("profile_id") or ""),
        family,
        int(model_ref.get("horizon_days") or 0),
        str(model_ref.get("species_id") or ""),
        str(model_ref.get("estimator_id") or ""),
    )
    for row in catalog.get("entries", []):
        if not isinstance(row, Mapping):
            continue
        actual = (
            str(row.get("version_id") or ""),
            str(row.get("profile_id") or ""),
            str(row.get("temporal_family") or ""),
            int(row.get("horizon_days") or 0),
            str(row.get("species_id") or ""),
            str(row.get("estimator_id") or ""),
        )
        if actual == wanted:
            return dict(row)
    return {"evidence": "not_evaluated", "reason": "no_comparable_holdout_result"}
