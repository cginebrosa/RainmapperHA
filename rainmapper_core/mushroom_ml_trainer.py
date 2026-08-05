"""Train ML predictor models from mushroom observation features.

Reads mushroom_observation_features_v0.json, filters eligible episodes,
builds a feature matrix, trains logistic regression + random forest per
species, and saves joblib artifacts + a JSON report.

Usage:
    python -m rainmapper_core.mushroom_ml_trainer
    python -m rainmapper_core.mushroom_ml_trainer --species boletus_aereus
    python -m rainmapper_core.mushroom_ml_trainer --min-rows 20 --cv-folds 5
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_paths


# ---------------------------------------------------------------------------
# Feature columns used in the ML model
# Daily series arrays (daily_rain_mm etc.) are NOT included here — they live
# in the JSON artifact for future sequence models, but 30×7=210 features would
# overfit on the ~50-row training sets we currently have.
# ---------------------------------------------------------------------------
FEATURE_COLS: list[str] = [
    # Rain accumulation windows
    "rain_1d_mm",
    "rain_7d_mm",
    "rain_14d_mm",
    "rain_21d_mm",
    "rain_30d_mm",
    # Temperature windows
    "temp_min_7d_c",
    "temp_max_7d_c",
    "temp_mean_7d_c",
    "temp_min_14d_c",
    "temp_max_14d_c",
    "temp_mean_14d_c",
    "temp_min_21d_c",
    "temp_max_21d_c",
    "temp_mean_21d_c",
    "temp_min_30d_c",
    "temp_max_30d_c",
    "temp_mean_30d_c",
    # Humidity windows
    "humidity_min_7d_pct",
    "humidity_max_7d_pct",
    "humidity_mean_7d_pct",
    "humidity_min_14d_pct",
    "humidity_max_14d_pct",
    "humidity_mean_14d_pct",
    "humidity_min_21d_pct",
    "humidity_max_21d_pct",
    "humidity_mean_21d_pct",
    "humidity_min_30d_pct",
    "humidity_max_30d_pct",
    "humidity_mean_30d_pct",
    # Derived scalar features (computed in mushroom_observation_context.py)
    "dry_spell_days",
    "days_since_significant_rain",
    "rainy_days_14d",
    "thermal_amplitude_mean_7d",
    "thermal_amplitude_mean_14d",
    "thermal_trend",
    "heat_stress_days",
    "high_humidity_days_14d",
    # GIS
    "gis_altitude_m",
    # Calendar (numeric month 1-12; the model can learn seasonal patterns)
    "month",
]

MIN_ROWS_DEFAULT = 20
CV_FOLDS_DEFAULT = 5
TRAIN_RATIO = 0.70  # fraction of rows used for training (temporal split)

# Label thresholds — must stay in sync with mushroom_ml_predictor.py
_LABEL_FAVORABLE_THRESHOLD = 0.60
_LABEL_UNFAVORABLE_THRESHOLD = 0.40


def _require_sklearn() -> None:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        sys.exit(
            "scikit-learn is not installed. Run: .venv/bin/python -m pip install scikit-learn"
        )


def load_features(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"Expected list of rows in {path}")
    return rows


def filter_eligible(rows: list[dict[str, Any]], species_id: str) -> list[dict[str, Any]]:
    return [
        r for r in rows
        if r.get("species_id") == species_id
        and r.get("validation_status") == "valid"
        and r.get("calibration_use") == "include"
        and r.get("prediction_target") in ("favorable", "unfavorable")
        and r.get("micro_area_id") is not None
    ]


def load_micro_area_to_area(known_sites_path: Path) -> dict[str, str]:
    """Return {micro_area_id: area_id} from mushroom_known_sites.json."""
    if not known_sites_path.exists():
        return {}
    payload = json.loads(known_sites_path.read_text(encoding="utf-8"))
    return {
        ma["micro_area_id"]: ma["area_id"]
        for ma in payload.get("micro_areas", [])
        if ma.get("micro_area_id") and ma.get("area_id")
    }


def aggregate_to_area_episodes(
    rows: list[dict[str, Any]],
    micro_area_to_area: dict[str, str],
) -> list[dict[str, Any]]:
    """Aggregate observation rows to (species, area, date) episodes.

    Episode target is favorable if ANY micro_area in the area was favorable
    that day. Weather features come from the row with the fewest gaps.
    Altitude is averaged across micro_areas present that day.
    """
    from collections import defaultdict  # noqa: PLC0415

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        area_id = micro_area_to_area.get(r.get("micro_area_id", ""))
        if not area_id:
            continue
        key = (r["species_id"], area_id, r["observed_at"])
        groups[key].append(r)

    episodes = []
    for (species_id, area_id, observed_at), group in groups.items():
        any_favorable = any(r["prediction_target"] == "favorable" for r in group)
        # Pick row with fewest weather gaps for features
        best = min(group, key=lambda r: len(r.get("weather_gaps") or []))
        episode = dict(best)
        episode["area_id"] = area_id
        episode["prediction_target"] = "favorable" if any_favorable else "unfavorable"
        episode["n_micro_areas_in_episode"] = len(group)
        # Average altitude across micro_areas present that day
        alts = [r["gis_altitude_m"] for r in group if r.get("gis_altitude_m") is not None]
        episode["gis_altitude_m"] = sum(alts) / len(alts) if alts else best.get("gis_altitude_m")
        episodes.append(episode)

    return sorted(episodes, key=lambda e: e["observed_at"])


def build_X_y(rows: list[dict[str, Any]]) -> tuple[Any, Any, list[str], list[float]]:
    """Return (X_raw, y, feature_cols, missing_fractions)."""
    import numpy as np  # noqa: PLC0415

    X_raw = []
    y = []
    for r in rows:
        X_raw.append([r.get(col) for col in FEATURE_COLS])
        y.append(1 if r.get("prediction_target") == "favorable" else 0)

    X_np = np.array(
        [[v if v is not None else float("nan") for v in row] for row in X_raw],
        dtype=float,
    )
    y_np = np.array(y, dtype=int)

    missing_fracs = [
        float(np.isnan(X_np[:, i]).mean()) for i in range(len(FEATURE_COLS))
    ]
    return X_np, y_np, FEATURE_COLS, missing_fracs


def _temporal_split(
    rows: list[dict[str, Any]],
) -> tuple[list[int], list[int]]:
    """Return (train_indices, test_indices) sorted by observed_at."""
    dated = sorted(enumerate(rows), key=lambda x: x[1].get("observed_at", ""))
    n_train = max(1, int(len(dated) * TRAIN_RATIO))
    train_idx = [i for i, _ in dated[:n_train]]
    test_idx = [i for i, _ in dated[n_train:]]
    return train_idx, test_idx


def _safe_round(v: float, digits: int = 4) -> float | None:
    try:
        return round(float(v), digits)
    except (TypeError, ValueError):
        return None


def train_species(
    species_id: str,
    rows: list[dict[str, Any]],
    models_dir: Path,
    cv_folds: int = CV_FOLDS_DEFAULT,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Train LR + RF for one species. Returns a dict with metrics and paths."""
    import joblib  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from sklearn.ensemble import RandomForestClassifier  # noqa: PLC0415
    from sklearn.impute import SimpleImputer  # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.metrics import (  # noqa: PLC0415
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_score  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415

    def _cb(pct: int, msg: str) -> None:
        if progress_callback:
            progress_callback(pct, msg)

    _cb(5, f"{species_id}: construyendo matriz de features")

    X_raw, y, feature_cols, missing_fracs = build_X_y(rows)
    n_total = len(rows)
    n_favorable = int(y.sum())
    n_unfavorable = n_total - n_favorable

    train_idx, test_idx = _temporal_split(rows)
    X_train_raw = X_raw[train_idx]
    X_test_raw = X_raw[test_idx]
    y_train = y[train_idx]
    y_test = y[test_idx]

    _cb(15, f"{species_id}: imputando valores faltantes")

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train_raw)
    X_test_imp = imputer.transform(X_test_raw) if len(X_test_raw) > 0 else X_test_raw

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_imp)
    X_test = scaler.transform(X_test_imp) if len(X_test_imp) > 0 else X_test_imp

    _cb(25, f"{species_id}: entrenando regresión logística")

    lr = LogisticRegression(C=1.0, max_iter=2000, random_state=42, class_weight="balanced")
    lr.fit(X_train, y_train)

    _cb(45, f"{species_id}: entrenando random forest")

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    _cb(65, f"{species_id}: calculando métricas holdout")

    def _metrics(clf: Any, X: Any, y_true: Any, label: str) -> dict[str, Any]:
        if len(X) == 0 or len(np.unique(y_true)) < 2:
            return {"note": f"no {label} set or single class — skipped"}
        y_pred = clf.predict(X)
        y_prob = clf.predict_proba(X)[:, 1]
        return {
            "n": int(len(y_true)),
            "auc_roc": _safe_round(roc_auc_score(y_true, y_prob)),
            "accuracy": _safe_round(accuracy_score(y_true, y_pred)),
            "precision": _safe_round(precision_score(y_true, y_pred, zero_division=0)),
            "recall": _safe_round(recall_score(y_true, y_pred, zero_division=0)),
            "f1": _safe_round(f1_score(y_true, y_pred, zero_division=0)),
        }

    lr_train_metrics = _metrics(lr, X_train, y_train, "train")
    lr_test_metrics = _metrics(lr, X_test, y_test, "test")
    rf_train_metrics = _metrics(rf, X_train, y_train, "train")
    rf_test_metrics = _metrics(rf, X_test, y_test, "test")

    _cb(75, f"{species_id}: cross-validación estratificada ({cv_folds} folds)")

    cv_scores_lr: list[float] = []
    cv_scores_rf: list[float] = []
    if len(np.unique(y_train)) >= 2 and len(y_train) >= cv_folds:
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_lr_raw = cross_val_score(
            LogisticRegression(C=1.0, max_iter=2000, random_state=42, class_weight="balanced"),
            X_train, y_train, cv=skf, scoring="roc_auc",
        )
        cv_rf_raw = cross_val_score(
            RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced", n_jobs=-1),
            X_train, y_train, cv=skf, scoring="roc_auc",
        )
        cv_scores_lr = [_safe_round(v) for v in cv_lr_raw]
        cv_scores_rf = [_safe_round(v) for v in cv_rf_raw]

    _cb(88, f"{species_id}: guardando modelos")

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib_path = models_dir / f"mushroom_ml_v0_{species_id}.joblib"
    joblib.dump(
        {
            "species_id": species_id,
            "feature_cols": feature_cols,
            "imputer": imputer,
            "scaler": scaler,
            "lr": lr,
            "rf": rf,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        joblib_path,
    )

    # Coefficients (LR) and importances (RF) — top features only in report
    coef_map = {col: _safe_round(coef) for col, coef in zip(feature_cols, lr.coef_[0])}
    importance_map = {col: _safe_round(imp) for col, imp in zip(feature_cols, rf.feature_importances_)}

    # Sort by absolute value for readability
    coef_sorted = dict(sorted(coef_map.items(), key=lambda kv: abs(kv[1] or 0), reverse=True))
    imp_sorted = dict(sorted(importance_map.items(), key=lambda kv: kv[1] or 0, reverse=True))

    missing_by_col = {
        col: _safe_round(frac)
        for col, frac in zip(feature_cols, missing_fracs)
        if frac > 0
    }

    # Date range
    dates = sorted(r.get("observed_at", "") for r in rows if r.get("observed_at"))
    date_range = {"first": dates[0], "last": dates[-1]} if dates else {}

    train_dates = sorted(rows[i].get("observed_at", "") for i in train_idx if rows[i].get("observed_at"))
    test_dates = sorted(rows[i].get("observed_at", "") for i in test_idx if rows[i].get("observed_at"))

    _cb(93, f"{species_id}: calculando backtest sobre todos los episodios")
    backtest_stats: dict[str, Any] = {}
    try:
        # Holdout test accuracy (honest — model never saw these during training)
        holdout_test_accuracy: float | None = None
        if len(X_test) > 0:
            lr_test_probs = lr.predict_proba(X_test)[:, 1]
            rf_test_probs = rf.predict_proba(X_test)[:, 1]
            ens_test_probs = (lr_test_probs + rf_test_probs) / 2.0
            correct_test = sum(
                1 for i, yi in enumerate(y_test)
                if (
                    (ens_test_probs[i] >= _LABEL_FAVORABLE_THRESHOLD and int(yi) == 1)
                    or (ens_test_probs[i] <= _LABEL_UNFAVORABLE_THRESHOLD and int(yi) == 0)
                )
            )
            holdout_test_accuracy = _safe_round(correct_test / len(y_test))

        X_all_imp = imputer.transform(X_raw)
        X_all_scaled = scaler.transform(X_all_imp)
        lr_probs_all = lr.predict_proba(X_all_scaled)[:, 1]
        rf_probs_all = rf.predict_proba(X_all_scaled)[:, 1]
        ensemble_probs_all = (lr_probs_all + rf_probs_all) / 2.0

        total_bt = 0
        correct_bt = 0
        fn_bt = 0
        fp_bt = 0
        by_area_bt: dict[str, dict[str, int]] = {}

        for i, ep in enumerate(rows):
            prob = float(ensemble_probs_all[i])
            if prob >= _LABEL_FAVORABLE_THRESHOLD:
                pred_label = "favorable"
            elif prob <= _LABEL_UNFAVORABLE_THRESHOLD:
                pred_label = "unfavorable"
            else:
                pred_label = "uncertain"
            actual = "favorable" if int(y[i]) == 1 else "unfavorable"
            is_correct = pred_label == actual
            is_fn = actual == "favorable" and pred_label != "favorable"
            is_fp = actual == "unfavorable" and pred_label == "favorable"

            total_bt += 1
            if is_correct:
                correct_bt += 1
            if is_fn:
                fn_bt += 1
            if is_fp:
                fp_bt += 1

            area_id = str(ep.get("area_id") or "")
            if area_id:
                a = by_area_bt.setdefault(area_id, {"episodes": 0, "correct": 0, "fn": 0, "fp": 0})
                a["episodes"] += 1
                if is_correct:
                    a["correct"] += 1
                if is_fn:
                    a["fn"] += 1
                if is_fp:
                    a["fp"] += 1

        by_area_stats = {
            area: {
                "episodes": d["episodes"],
                "backtest_accuracy": _safe_round(d["correct"] / d["episodes"]) if d["episodes"] else None,
                "false_negatives": d["fn"],
                "false_positives": d["fp"],
            }
            for area, d in sorted(by_area_bt.items())
        }
        backtest_stats = {
            "total_episodes": total_bt,
            "n_test": len(test_idx),
            "holdout_test_accuracy": holdout_test_accuracy,
            "favorable_ratio": _safe_round(n_favorable / total_bt) if total_bt else None,
            "date_range": date_range,
            "by_area": by_area_stats,
        }
    except Exception as _exc_bt:
        backtest_stats = {"error": str(_exc_bt)}

    _cb(100, f"{species_id}: listo")

    return {
        "species_id": species_id,
        "n_total": n_total,
        "n_favorable": n_favorable,
        "n_unfavorable": n_unfavorable,
        "n_train": len(train_idx),
        "n_test": len(test_idx),
        "train_date_range": {
            "first": train_dates[0] if train_dates else None,
            "last": train_dates[-1] if train_dates else None,
        },
        "test_date_range": {
            "first": test_dates[0] if test_dates else None,
            "last": test_dates[-1] if test_dates else None,
        },
        "date_range": date_range,
        "feature_cols": feature_cols,
        "missing_fraction_by_feature": missing_by_col,
        "models": {
            "logistic_regression": {
                "train": lr_train_metrics,
                "test": lr_test_metrics,
                "cv_auc_roc": cv_scores_lr,
                "cv_auc_roc_mean": _safe_round(float(sum(cv_scores_lr) / len(cv_scores_lr))) if cv_scores_lr else None,
                "coefficients_sorted_by_abs": coef_sorted,
            },
            "random_forest": {
                "train": rf_train_metrics,
                "test": rf_test_metrics,
                "cv_auc_roc": cv_scores_rf,
                "cv_auc_roc_mean": _safe_round(float(sum(cv_scores_rf) / len(cv_scores_rf))) if cv_scores_rf else None,
                "feature_importances_sorted": imp_sorted,
                "n_estimators": rf.n_estimators,
            },
        },
        "joblib_path": str(joblib_path),
        "backtest_stats": backtest_stats,
    }


def run(
    species_ids: list[str] | None = None,
    features_path: Path | None = None,
    known_sites_path: Path | None = None,
    models_dir: Path | None = None,
    report_path: Path | None = None,
    min_rows: int = MIN_ROWS_DEFAULT,
    cv_folds: int = CV_FOLDS_DEFAULT,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Train models for the given species (or all species with enough area episodes)."""
    _require_sklearn()

    features_path = features_path or mushroom_paths.mushroom_observation_features_json_path()
    known_sites_path = known_sites_path or mushroom_paths.mushroom_known_sites_path()
    models_dir = models_dir or mushroom_paths.mushroom_ml_models_dir()
    report_path = report_path or mushroom_paths.mushroom_ml_report_json_path()

    if not features_path.exists():
        raise FileNotFoundError(f"Features artifact not found: {features_path}")

    rows = load_features(features_path)
    ma_to_area = load_micro_area_to_area(known_sites_path)

    # Discover species if not specified
    if not species_ids:
        from collections import Counter  # noqa: PLC0415
        counts = Counter(
            r.get("species_id")
            for r in rows
            if r.get("validation_status") == "valid"
            and r.get("calibration_use") == "include"
            and r.get("prediction_target") in ("favorable", "unfavorable")
            and r.get("micro_area_id") is not None
        )
        species_ids = [sp for sp, cnt in counts.most_common() if cnt >= min_rows]

    if not species_ids:
        raise ValueError(f"No species with >= {min_rows} eligible rows found.")

    species_results: list[dict[str, Any]] = []
    for idx, sp in enumerate(species_ids):
        sp_rows = filter_eligible(rows, sp)
        episodes = aggregate_to_area_episodes(sp_rows, ma_to_area)
        if len(episodes) < min_rows:
            species_results.append({
                "species_id": sp,
                "skipped": True,
                "reason": f"only {len(episodes)} area episodes after aggregation (min={min_rows})",
            })
            continue

        def _sp_progress(pct: int, msg: str, sp_idx: int = idx, n_sp: int = len(species_ids)) -> None:
            if progress_callback:
                overall = int(sp_idx / n_sp * 100 + pct / n_sp)
                progress_callback(overall, msg)

        result = train_species(
            sp,
            episodes,
            models_dir=models_dir,
            cv_folds=cv_folds,
            progress_callback=_sp_progress,
        )
        species_results.append(result)

    report = {
        "schema_version": "0.1",
        "kind": "mushroom_ml_v0_report",
        "generated_at": datetime.now(UTC).isoformat(),
        "episode_unit": "species_area_date",
        "features_source": str(features_path),
        "min_rows": min_rows,
        "cv_folds": cv_folds,
        "train_ratio": TRAIN_RATIO,
        "feature_cols": FEATURE_COLS,
        "species_results": species_results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report saved to: {report_path}", file=sys.stderr)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train ML predictor models from mushroom observation features."
    )
    parser.add_argument(
        "--species",
        nargs="+",
        metavar="SPECIES_ID",
        help="Species to train (default: all with enough rows)",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=MIN_ROWS_DEFAULT,
        help=f"Minimum eligible rows per species (default: {MIN_ROWS_DEFAULT})",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=CV_FOLDS_DEFAULT,
        help=f"Cross-validation folds (default: {CV_FOLDS_DEFAULT})",
    )
    parser.add_argument(
        "--features",
        metavar="PATH",
        help="Path to mushroom_observation_features_v0.json",
    )
    args = parser.parse_args()

    features_path = Path(args.features) if args.features else None

    report = run(
        species_ids=args.species,
        features_path=features_path,
        min_rows=args.min_rows,
        cv_folds=args.cv_folds,
    )

    for result in report["species_results"]:
        sp = result["species_id"]
        if result.get("skipped"):
            print(f"  SKIP {sp}: {result['reason']}")
            continue

        lr_cv = result["models"]["logistic_regression"].get("cv_auc_roc_mean")
        rf_cv = result["models"]["random_forest"].get("cv_auc_roc_mean")
        lr_test = result["models"]["logistic_regression"]["test"].get("auc_roc")
        rf_test = result["models"]["random_forest"]["test"].get("auc_roc")
        n = result["n_total"]
        fav = result["n_favorable"]
        unfav = result["n_unfavorable"]

        print(f"\n{'='*60}")
        print(f"  {sp}  ({n} rows: {fav}+ / {unfav}-)")
        print(f"  train: {result['n_train']} rows ({result['train_date_range']['first']} .. {result['train_date_range']['last']})")
        print(f"  test:  {result['n_test']} rows  ({result['test_date_range']['first']} .. {result['test_date_range']['last']})")
        print(f"  LR  CV-AUC: {lr_cv}  holdout-AUC: {lr_test}")
        print(f"  RF  CV-AUC: {rf_cv}  holdout-AUC: {rf_test}")

        print("\n  LR top-5 coefficients (signed):")
        for i, (feat, coef) in enumerate(result["models"]["logistic_regression"]["coefficients_sorted_by_abs"].items()):
            if i >= 5:
                break
            print(f"    {feat:40s}  {coef:+.4f}")

        print("\n  RF top-5 importances:")
        for i, (feat, imp) in enumerate(result["models"]["random_forest"]["feature_importances_sorted"].items()):
            if i >= 5:
                break
            print(f"    {feat:40s}  {imp:.4f}")

        print(f"\n  Model saved: {result['joblib_path']}")


if __name__ == "__main__":
    main()
