"""Comparable hold-out evidence for the non-operational V2--V6 catalog."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score

from rainmapper_core import mushroom_ml_reliability_audit
from rainmapper_core.mushroom_prediction_interpretation import (
    FAVORABLE_THRESHOLD,
    UNFAVORABLE_THRESHOLD,
)


SCHEMA_VERSION = "1.3"
KIND = "mushroom_ml_quality_catalog"
DEFAULT_LOOKUP_SPLIT_ID = "fruiting_groups_7d"

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


def _operational_classification(
    y: np.ndarray, probabilities: np.ndarray
) -> dict[str, Any]:
    """Summarize untouched hold-out rows with the Predictor's real cut-offs."""
    predicted_favorable = probabilities >= FAVORABLE_THRESHOLD
    predicted_unfavorable = probabilities <= UNFAVORABLE_THRESHOLD
    actual_favorable = y == 1
    actual_unfavorable = y == 0

    true_favorable = int(np.sum(predicted_favorable & actual_favorable))
    false_favorable = int(np.sum(predicted_favorable & actual_unfavorable))
    true_unfavorable = int(np.sum(predicted_unfavorable & actual_unfavorable))
    false_unfavorable = int(np.sum(predicted_unfavorable & actual_favorable))
    uncertain = int(np.sum(~predicted_favorable & ~predicted_unfavorable))

    return {
        "evaluated_count": int(len(y)),
        "true_favorable_count": true_favorable,
        "false_favorable_count": false_favorable,
        "true_unfavorable_count": true_unfavorable,
        "false_unfavorable_count": false_unfavorable,
        "uncertain_count": uncertain,
    }


def _build_catalog_bundle(
    v2_v5_path: Path,
    v6_path: Path,
    *,
    snapshot_id: str,
    profile_keys: list[str] | None = None,
    expected_estimators: Mapping[str, list[str]] | None = None,
    include_audit_catalog: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Aggregate hold-out predictions without averaging species or splits."""
    grouped: dict[tuple[str, ...], list[tuple[int, float, float]]] = defaultdict(list)
    row_groups: dict[tuple[str, ...], int] = defaultdict(int)
    split_ids: set[str] = set()
    operational_species_areas: set[tuple[str, str]] = set()
    selection_holdout_rows: list[dict[str, Any]] = []
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
            area_id = str(row.get("area_id") or "")
            split_id = str(row.get("split_id") or "")
            if not split_id:
                raise ValueError("Hold-out row is missing split_id")
            temporal_contract_id = str(row.get("temporal_contract_id") or "")
            family = _family(temporal_contract_id)
            horizon = str(int(row.get("horizon_days") or 0))
            probabilities = row.get("estimator_probabilities") or {}
            profile_key = f"{version_id}/{profile_id}"
            if (
                not all((version_id, profile_id, species_id))
                or family == "unknown"
                or (selected and profile_key not in selected)
            ):
                continue
            if area_id:
                operational_species_areas.add((species_id, area_id))
            split_ids.add(split_id)
            try:
                y_true = int(row["y_true"])
                prevalence = float(row["train_prevalence_probability"])
            except (KeyError, TypeError, ValueError):
                continue
            if (
                split_id
                == mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID
            ):
                selection_probabilities = (
                    dict(probabilities) if isinstance(probabilities, Mapping) else {}
                )
                if expected_estimators is not None:
                    allowed = set(expected_estimators.get(profile_key, []))
                    selection_probabilities = {
                        estimator_id: probability
                        for estimator_id, probability in selection_probabilities.items()
                        if estimator_id in allowed
                    }
                selection_holdout_rows.append(
                    {
                        "version_id": version_id,
                        "profile_id": profile_id,
                        "species_id": species_id,
                        "area_id": area_id,
                        "split_id": split_id,
                        "observation_id": row.get("observation_id"),
                        "validation_group_id": row.get("validation_group_id"),
                        "y_true": y_true,
                        "train_prevalence_probability": prevalence,
                        "temporal_contract_id": row.get("temporal_contract_id"),
                        "horizon_days": row.get("horizon_days"),
                        "estimator_probabilities": selection_probabilities,
                    }
                )
            base_key = (
                split_id,
                version_id,
                profile_id,
                temporal_contract_id,
                family,
                horizon,
                species_id,
            )
            row_groups[base_key] += 1
            estimator_ids = set(probabilities)
            if expected_estimators is not None:
                estimator_ids.update(expected_estimators.get(profile_key, []))
            for estimator_id in estimator_ids:
                metric_key = (
                    split_id,
                    version_id,
                    profile_id,
                    temporal_contract_id,
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
    split_entries = []
    for key, values in sorted(grouped.items()):
        (
            split_id,
            version_id,
            profile_id,
            temporal_contract_id,
            family,
            horizon,
            species_id,
            estimator_id,
        ) = key
        total_rows = row_groups[
            (
                split_id,
                version_id,
                profile_id,
                temporal_contract_id,
                family,
                horizon,
                species_id,
            )
        ]
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
        operational_classification = _operational_classification(y, probabilities)
        if len(values) < 8 or not both_classes or delta is None:
            evidence = "insufficient"
        elif delta > 0:
            evidence = "better_than_prevalence"
        else:
            evidence = "worse_than_prevalence"
        split_entries.append(
            {
                "split_id": split_id,
                "version_id": version_id,
                "profile_id": profile_id,
                "temporal_contract_id": temporal_contract_id,
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
                "operational_classification": operational_classification,
                "evidence": evidence,
            }
        )
    default_split_id = (
        DEFAULT_LOOKUP_SPLIT_ID
        if DEFAULT_LOOKUP_SPLIT_ID in split_ids
        else (next(iter(split_ids)) if len(split_ids) == 1 else "")
    )
    entries = [
        row for row in split_entries if row.get("split_id") == default_split_id
    ]
    alternate_split_entries = [
        row for row in split_entries if row.get("split_id") != default_split_id
    ]
    selection_report = mushroom_ml_reliability_audit.audit_rows(
        selection_holdout_rows,
        split_ids={mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID},
        top=1,
        include_candidates=True,
        include_stability=True,
    )
    selections = mushroom_ml_reliability_audit.build_selection_catalog(
        selection_report,
        operational_species_areas=operational_species_areas,
    )
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "snapshot_id": snapshot_id,
        "split_id": default_split_id,
        "split_ids": sorted(split_ids),
        "entries": entries,
        "alternate_split_entries": alternate_split_entries,
        "selection_schema_version": selections["schema_version"],
        "selection_status": selections["status"],
        "selection_id": selections["selection_id"],
        "selection_split_id": selections["official_split_id"],
        "selection_prediction_days": selections["prediction_days"],
        "selection_policy": selections["selection_policy"],
        "selection_counts": selections["counts"],
        "species_selections": selections["species_selections"],
        "species_area_selections": selections["species_area_selections"],
        "version_cautions": dict(VERSION_CAUTIONS),
        "species_metrics_are_never_averaged": True,
    }
    validated = validate_catalog(catalog)
    audit_catalog = (
        mushroom_ml_reliability_audit.build_quality_audit_catalog(
            selection_report,
            selections,
            snapshot_id=snapshot_id,
        )
        if include_audit_catalog
        else None
    )
    return validated, audit_catalog


def build_catalog(
    v2_v5_path: Path,
    v6_path: Path,
    *,
    snapshot_id: str,
    profile_keys: list[str] | None = None,
    expected_estimators: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build the compact catalog consumed by the operational precompute."""
    catalog, _ = _build_catalog_bundle(
        v2_v5_path,
        v6_path,
        snapshot_id=snapshot_id,
        profile_keys=profile_keys,
        expected_estimators=expected_estimators,
        include_audit_catalog=False,
    )
    return catalog


def build_catalog_bundle(
    v2_v5_path: Path,
    v6_path: Path,
    *,
    snapshot_id: str,
    profile_keys: list[str] | None = None,
    expected_estimators: Mapping[str, list[str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build compact operational and extended on-demand audit catalogs together."""
    catalog, audit_catalog = _build_catalog_bundle(
        v2_v5_path,
        v6_path,
        snapshot_id=snapshot_id,
        profile_keys=profile_keys,
        expected_estimators=expected_estimators,
        include_audit_catalog=True,
    )
    if audit_catalog is None:  # pragma: no cover - guarded by the flag above
        raise RuntimeError("Quality audit catalog was not produced")
    return catalog, audit_catalog


def _selection_payload(catalog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": catalog.get("selection_schema_version"),
        "kind": mushroom_ml_reliability_audit.SELECTION_KIND,
        "status": catalog.get("selection_status"),
        "official_split_id": catalog.get("selection_split_id"),
        "prediction_days": catalog.get("selection_prediction_days"),
        "selection_policy": catalog.get("selection_policy"),
        "species_selections": catalog.get("species_selections"),
        "species_area_selections": catalog.get("species_area_selections"),
        "counts": catalog.get("selection_counts"),
    }


def _validate_resolution(
    row: Mapping[str, Any],
    *,
    prediction_day: int,
    allowed_scopes: set[str],
) -> list[tuple[str, ...]]:
    status = str(row.get("selection_status") or "")
    scope = str(row.get("selection_scope") or "")
    evidence_by_scope = row.get("evidence_by_scope")
    if (
        not isinstance(evidence_by_scope, Mapping)
        or set(evidence_by_scope) != {"area", "species"}
        or any(
            value is not None and not isinstance(value, Mapping)
            for value in evidence_by_scope.values()
        )
    ):
        raise ValueError("Quality catalog scoped evidence is invalid")
    if status == "abstain":
        if (
            scope != "none"
            or row.get("candidate") is not None
            or any(value is not None for value in evidence_by_scope.values())
        ):
            raise ValueError("Quality catalog abstention is invalid")
        chain = row.get("candidate_chain")
        if chain not in (None, []):
            raise ValueError("Quality catalog abstention has a candidate chain")
        return []
    if status != "winner" or scope not in allowed_scopes:
        raise ValueError("Quality catalog selection status or scope is invalid")
    candidate = row.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("Quality catalog winner is missing its candidate")
    version_id = str(candidate.get("version_id") or "")
    profile_id = str(candidate.get("profile_id") or "")
    contract_id = str(candidate.get("temporal_contract_id") or "")
    family = _family(contract_id)
    estimator_id = str(candidate.get("estimator_id") or "")
    try:
        horizon = int(candidate.get("horizon_days") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Quality catalog candidate horizon is invalid") from exc
    expected_horizon = 7 if family == "fixed" else prediction_day
    if (
        not all((version_id, profile_id, contract_id, estimator_id))
        or family == "unknown"
        or str(candidate.get("temporal_family") or "") != family
        or horizon != expected_horizon
    ):
        raise ValueError("Quality catalog candidate identity is invalid")
    evidence = row.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("Quality catalog winner evidence is invalid")
    for evidence_scope, scoped_evidence in evidence_by_scope.items():
        if scoped_evidence is None:
            continue
        if scoped_evidence.get("candidate") != candidate:
            raise ValueError(
                f"Quality catalog {evidence_scope} evidence targets another candidate"
            )
    selected_evidence_scope = "area" if scope == "area" else "species"
    selected_evidence = evidence_by_scope.get(selected_evidence_scope)
    if (
        not isinstance(selected_evidence, Mapping)
        or not selected_evidence.get("eligible")
        or any(
            selected_evidence.get(field) != evidence.get(field)
            for field in mushroom_ml_reliability_audit.EVIDENCE_KEYS
        )
    ):
        raise ValueError("Quality catalog selected scoped evidence is inconsistent")
    if scope == "species" and evidence_by_scope.get("area") is not None:
        raise ValueError("Quality catalog species evidence contains an area scope")
    if scope == "area" and not isinstance(evidence_by_scope.get("species"), Mapping):
        raise ValueError("Quality catalog area winner lacks species evidence")
    primary_key = (
        version_id,
        profile_id,
        contract_id,
        family,
        str(horizon),
        estimator_id,
    )
    raw_chain = row.get("candidate_chain")
    if raw_chain is None:
        # Backward compatibility with already installed 1.3 catalogs.
        return [primary_key]
    if not isinstance(raw_chain, list) or not raw_chain:
        raise ValueError("Quality catalog winner candidate chain is invalid")
    chain_keys: list[tuple[str, ...]] = []
    for rank, raw_entry in enumerate(raw_chain):
        if not isinstance(raw_entry, Mapping):
            raise ValueError("Quality catalog candidate chain entry is invalid")
        chain_candidate = raw_entry.get("candidate")
        if not isinstance(chain_candidate, Mapping):
            raise ValueError("Quality catalog candidate chain identity is invalid")
        chain_contract = str(chain_candidate.get("temporal_contract_id") or "")
        chain_family = _family(chain_contract)
        try:
            chain_horizon = int(chain_candidate.get("horizon_days") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Quality catalog candidate chain horizon is invalid") from exc
        chain_key = (
            str(chain_candidate.get("version_id") or ""),
            str(chain_candidate.get("profile_id") or ""),
            chain_contract,
            chain_family,
            str(chain_horizon),
            str(chain_candidate.get("estimator_id") or ""),
        )
        expected_chain_horizon = 7 if chain_family == "fixed" else prediction_day
        if (
            not all((chain_key[0], chain_key[1], chain_key[2], chain_key[5]))
            or chain_family == "unknown"
            or str(chain_candidate.get("temporal_family") or "") != chain_family
            or chain_horizon != expected_chain_horizon
            or chain_key in chain_keys
        ):
            raise ValueError("Quality catalog candidate chain identity is invalid")
        chain_evidence = raw_entry.get("evidence")
        chain_scoped = raw_entry.get("evidence_by_scope")
        selected_scope_evidence = (
            chain_scoped.get(selected_evidence_scope)
            if isinstance(chain_scoped, Mapping)
            else None
        )
        if (
            not isinstance(chain_evidence, Mapping)
            or not isinstance(chain_scoped, Mapping)
            or set(chain_scoped) != {"area", "species"}
            or not isinstance(selected_scope_evidence, Mapping)
            or selected_scope_evidence.get("candidate") != chain_candidate
            or not selected_scope_evidence.get("eligible")
            or any(
                selected_scope_evidence.get(field) != chain_evidence.get(field)
                for field in mushroom_ml_reliability_audit.EVIDENCE_KEYS
            )
        ):
            raise ValueError("Quality catalog candidate chain evidence is invalid")
        if rank == 0 and (
            chain_candidate != candidate or chain_evidence != evidence
        ):
            raise ValueError("Quality catalog candidate chain does not start at winner")
        chain_keys.append(chain_key)
    return chain_keys


def validate_catalog(
    catalog: Mapping[str, Any],
    *,
    require_selections: bool = False,
) -> dict[str, Any]:
    """Validate the catalog and its sealed operational reliability decisions."""
    if catalog.get("kind") != KIND or catalog.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Quality catalog contract is invalid")
    snapshot_id = str(catalog.get("snapshot_id") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
        raise ValueError("Quality catalog snapshot_id is invalid")
    status = str(catalog.get("selection_status") or "")
    if status not in {"complete", "unavailable"}:
        raise ValueError("Quality catalog selection_status is invalid")
    if require_selections and status != "complete":
        raise ValueError("Operational quality catalog has no sealed reliability selections")
    if catalog.get("selection_schema_version") != (
        mushroom_ml_reliability_audit.SELECTION_SCHEMA_VERSION
    ):
        raise ValueError("Quality catalog selection schema is invalid")
    if catalog.get("selection_split_id") != (
        mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID
    ):
        raise ValueError("Quality catalog selection split is invalid")
    if catalog.get("selection_prediction_days") != list(range(1, 8)):
        raise ValueError("Quality catalog prediction days are invalid")
    selection_policy = catalog.get("selection_policy")
    if (
        not isinstance(selection_policy, Mapping)
        or selection_policy.get("ranking_primary_metric")
        != "wilson_lower_95_observations"
        or selection_policy.get("territorial_resolution_rule")
        != "highest_wilson_lower_95_between_area_and_species;ties_prefer_area"
    ):
        raise ValueError("Quality catalog territorial selection policy is invalid")

    species_rows = catalog.get("species_selections")
    area_rows = catalog.get("species_area_selections")
    if not isinstance(species_rows, list) or not isinstance(area_rows, list):
        raise ValueError("Quality catalog selections must be lists")
    species_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    candidate_keys: set[tuple[str, ...]] = set()
    for raw in species_rows:
        if not isinstance(raw, Mapping):
            raise ValueError("Quality catalog species selection is invalid")
        species_id = str(raw.get("species_id") or "")
        prediction_day = int(raw.get("prediction_day") or 0)
        key = (species_id, prediction_day)
        if not species_id or prediction_day not in range(1, 8) or key in species_by_key:
            raise ValueError("Quality catalog species selection key is invalid")
        resolution_candidate_keys = _validate_resolution(
            raw, prediction_day=prediction_day, allowed_scopes={"species"}
        )
        for candidate_key in resolution_candidate_keys:
            candidate_keys.add((species_id, *candidate_key))
        species_by_key[key] = raw

    area_keys: set[tuple[str, str, int]] = set()
    for raw in area_rows:
        if not isinstance(raw, Mapping):
            raise ValueError("Quality catalog area selection is invalid")
        species_id = str(raw.get("species_id") or "")
        area_id = str(raw.get("area_id") or "")
        prediction_day = int(raw.get("prediction_day") or 0)
        key = (species_id, area_id, prediction_day)
        if (
            not species_id
            or not area_id
            or prediction_day not in range(1, 8)
            or key in area_keys
        ):
            raise ValueError("Quality catalog area selection key is invalid")
        resolution_candidate_keys = _validate_resolution(
            raw,
            prediction_day=prediction_day,
            allowed_scopes={"area", "species_fallback"},
        )
        for candidate_key in resolution_candidate_keys:
            candidate_keys.add((species_id, *candidate_key))
        if raw.get("selection_scope") == "species_fallback":
            fallback = species_by_key.get((species_id, prediction_day))
            if fallback is None or any(
                fallback.get(field) != raw.get(field)
                for field in (
                    "selection_status",
                    "candidate",
                    "evidence",
                    "population",
                    "stability",
                )
            ):
                raise ValueError("Quality catalog species fallback is inconsistent")
        area_keys.add(key)

    for species_id in {key[0] for key in species_by_key}:
        if {key[1] for key in species_by_key if key[0] == species_id} != set(
            range(1, 8)
        ):
            raise ValueError("Quality catalog species days are incomplete")
    for species_id, area_id in {(key[0], key[1]) for key in area_keys}:
        if {
            key[2]
            for key in area_keys
            if key[0] == species_id and key[1] == area_id
        } != set(range(1, 8)):
            raise ValueError("Quality catalog area days are incomplete")

    expected_counts = {
        "species": len({key[0] for key in species_by_key}),
        "species_days": len(species_rows),
        "species_areas": len({(key[0], key[1]) for key in area_keys}),
        "species_area_days": len(area_rows),
        "area_winners": sum(
            row.get("selection_scope") == "area" for row in area_rows
        ),
        "species_fallbacks": sum(
            row.get("selection_scope") == "species_fallback" for row in area_rows
        ),
        "abstentions": sum(
            row.get("selection_status") == "abstain" for row in area_rows
        ),
    }
    if catalog.get("selection_counts") != expected_counts:
        raise ValueError("Quality catalog selection counts are invalid")
    expected_status = "complete" if area_rows else "unavailable"
    if status != expected_status:
        raise ValueError("Quality catalog selection availability is inconsistent")

    quality_candidate_keys = {
        (
            str(row.get("species_id") or ""),
            str(row.get("version_id") or ""),
            str(row.get("profile_id") or ""),
            str(row.get("temporal_contract_id") or ""),
            str(row.get("temporal_family") or ""),
            str(int(row.get("horizon_days") or 0)),
            str(row.get("estimator_id") or ""),
        )
        for row in list(catalog.get("entries") or [])
        + list(catalog.get("alternate_split_entries") or [])
        if isinstance(row, Mapping)
        and str(row.get("split_id") or "")
        == mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID
    }
    if not candidate_keys.issubset(quality_candidate_keys):
        raise ValueError("Quality catalog selection references unevaluated candidates")

    selection_payload = _selection_payload(catalog)
    canonical = json.dumps(
        selection_payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    expected_selection_id = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    if catalog.get("selection_id") != expected_selection_id:
        raise ValueError("Quality catalog selection_id is invalid")
    return dict(catalog)


def lookup(
    catalog: Mapping[str, Any],
    model_ref: Mapping[str, object],
    *,
    split_id: str | None = None,
) -> dict[str, Any]:
    family = _family(model_ref.get("temporal_contract_id"))
    wanted_split_id = str(split_id or catalog.get("split_id") or "")
    wanted = (
        wanted_split_id,
        str(model_ref.get("version_id") or ""),
        str(model_ref.get("profile_id") or ""),
        str(model_ref.get("temporal_contract_id") or ""),
        family,
        int(model_ref.get("horizon_days") or 0),
        str(model_ref.get("species_id") or ""),
        str(model_ref.get("estimator_id") or ""),
    )
    rows = catalog.get("entries", [])
    if wanted_split_id != str(catalog.get("split_id") or ""):
        rows = catalog.get("alternate_split_entries", [])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        actual = (
            str(row.get("split_id") or catalog.get("split_id") or ""),
            str(row.get("version_id") or ""),
            str(row.get("profile_id") or ""),
            str(row.get("temporal_contract_id") or ""),
            str(row.get("temporal_family") or ""),
            int(row.get("horizon_days") or 0),
            str(row.get("species_id") or ""),
            str(row.get("estimator_id") or ""),
        )
        if actual == wanted:
            return dict(row)
    return {"evidence": "not_evaluated", "reason": "no_comparable_holdout_result"}
