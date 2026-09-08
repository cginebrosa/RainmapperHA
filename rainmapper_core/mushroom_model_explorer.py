"""Read-only web explorer for model artifacts installed on a worker.

The catalog is cheap to inspect and never deserializes model bundles.  A single
hash-verified bundle is loaded only after the user explicitly asks to inspect
one model.
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlencode, urlsplit

import numpy as np

from rainmapper_core import mushroom_ml_model_catalog as model_catalog
from rainmapper_core import mushroom_ml_runtime_inference as runtime_inference
from rainmapper_core import mushroom_ml_version_registry as version_registry
from rainmapper_core import mushroom_predictor_runtime


EXPLORER_PATH = "/models"


@dataclass(frozen=True)
class ExplorerResponse:
    status: int
    content_type: str
    body: bytes


@dataclass(frozen=True)
class RuntimeChoice:
    runtime_id: str
    display_name: str
    root: Path


@dataclass(frozen=True)
class RuntimeCatalog:
    runtime: RuntimeChoice
    registry: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    manifests: Mapping[str, dict[str, Any]]
    species_names: Mapping[str, str]


def is_explorer_path(path: str) -> bool:
    return path.rstrip("/") == EXPLORER_PATH


def discover_runtimes(worker_data_dir: Path) -> list[RuntimeChoice]:
    """Find active worker runtimes without changing or repairing any of them."""
    base = Path(worker_data_dir).resolve() / "predictor-runtime"
    candidates = [("shared", "Runtime compartido", base)]
    coordinator_root = base / "coordinators"
    if coordinator_root.is_dir():
        candidates.extend(
            (path.name, f"Coordinador {path.name}", path)
            for path in sorted(coordinator_root.iterdir())
            if path.is_dir()
        )
    result: list[RuntimeChoice] = []
    for runtime_id, display_name, candidate in candidates:
        current = mushroom_predictor_runtime.current_runtime(candidate)
        if current is not None:
            result.append(RuntimeChoice(runtime_id, display_name, current))
    return result


def _load_json(path: Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _species_names(profiles_path: Path) -> dict[str, str]:
    try:
        payload = _load_json(profiles_path)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    profiles = payload.get("species_profiles")
    if not isinstance(profiles, list):
        return {}
    names: dict[str, str] = {}
    for row in profiles:
        if not isinstance(row, Mapping):
            continue
        species_id = str(row.get("species_id") or "")
        scientific_name = str(row.get("scientific_name") or species_id)
        common_names = row.get("common_names")
        common = ""
        if isinstance(common_names, list):
            common = next((str(value) for value in common_names if value), "")
        if species_id:
            names[species_id] = (
                f"{common} — {scientific_name}" if common else scientific_name
            )
    names["all_species"] = "Todas las especies (modelo compartido)"
    return names


def load_runtime_catalog(runtime: RuntimeChoice) -> RuntimeCatalog:
    """Validate catalog metadata without opening any joblib artifact."""
    paths = mushroom_predictor_runtime.service_paths(runtime.root)
    registry = version_registry.load_registry(paths["version_registry_path"])
    manifests: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    manifest_paths = sorted(paths["models_dir"].glob("batches/*/manifest.json"))
    for manifest_path in manifest_paths:
        checked = model_catalog.validate_batch_manifest(
            registry, _load_json(manifest_path)
        )
        batch_id = str(checked["batch_id"])
        manifests[batch_id] = checked
        for artifact in checked["artifacts"]:
            ref = model_catalog.ModelArtifactRef.from_mapping(
                artifact["artifact_ref"]
            )
            rows.append(
                {
                    "key": ref.key,
                    "artifact_ref": ref.as_dict(),
                    "supported_horizons": list(artifact["supported_horizons"]),
                    "path": str(artifact["path"]),
                    "sha256": str(artifact["sha256"]),
                }
            )
    rows.sort(key=lambda row: str(row["key"]))
    return RuntimeCatalog(
        runtime=runtime,
        registry=registry,
        rows=tuple(rows),
        manifests=manifests,
        species_names=_species_names(paths["profiles_path"]),
    )


def _class_name(value: object) -> str:
    cls = value.__class__
    return f"{cls.__module__}.{cls.__name__}"


def _feature_kind(name: str) -> str:
    normalized = name.lower()
    if normalized.startswith(("rain_", "rainfall_")):
        return "precipitación"
    if "climatic_water_balance" in normalized:
        return "balance hídrico"
    if normalized.startswith("temp_"):
        return "temperatura"
    if normalized.startswith("humidity_"):
        return "humedad"
    if normalized.startswith("soil_water_"):
        return "agua del suelo"
    if "altitude" in normalized or "elevation" in normalized:
        return "altitud"
    if normalized.startswith("target_day_"):
        return "estacionalidad"
    if normalized == "horizon_days":
        return "horizonte"
    if "species_intercept" in normalized or "species_deviation" in normalized:
        return "efecto de especie"
    return "otra"


def _pipeline_parts(model: object) -> tuple[object, list[dict[str, str]]]:
    named_steps = getattr(model, "named_steps", None)
    if not isinstance(named_steps, Mapping):
        return model, []
    steps = [
        {"name": str(name), "type": _class_name(step)}
        for name, step in named_steps.items()
    ]
    return named_steps.get("classifier", model), steps


def _v6_feature_names(bundle: Mapping[str, Any], base: list[str]) -> list[str]:
    artifact_ref = bundle.get("artifact_ref") or {}
    estimator_id = str(
        artifact_ref.get("estimator_id", "")
        if isinstance(artifact_ref, Mapping)
        else ""
    )
    species_order = [str(value) for value in bundle.get("species_order") or []]
    if estimator_id == "smooth_shared_logistic_v1":
        return base + [
            f"species_intercept::{species}" for species in species_order[1:]
        ]
    if estimator_id == "smooth_partial_pooling_logistic_v1":
        names = base + [
            f"species_intercept::{species}" for species in species_order[1:]
        ]
        names.extend(
            f"{feature}__species_deviation::{species}"
            for species in species_order
            for feature in base
        )
        return names
    return base


def _coefficient_feature_names(bundle: Mapping[str, Any]) -> list[str]:
    preprocessor = bundle.get("preprocessor")
    feature_names = getattr(preprocessor, "feature_names", None)
    if callable(feature_names):
        return _v6_feature_names(bundle, [str(value) for value in feature_names()])
    return [str(value) for value in bundle.get("feature_cols") or []]


def _numeric(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _support_rows(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    support = bundle.get("feature_support")
    if not isinstance(support, Mapping):
        return []
    result = []
    for name in bundle.get("feature_cols") or support:
        values = support.get(name)
        if not isinstance(values, Mapping):
            continue
        result.append(
            {
                "feature": str(name),
                "kind": _feature_kind(str(name)),
                "min": _numeric(values.get("min")),
                "mean": _numeric(values.get("mean")),
                "max": _numeric(values.get("max")),
                "std": _numeric(values.get("std")),
            }
        )
    return result


def summarize_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Extract native, exact model structure without inventing explanations."""
    model = bundle.get("model")
    if model is None:
        raise ValueError("El artefacto no contiene un modelo.")
    estimator, steps = _pipeline_parts(model)
    feature_cols = [str(value) for value in bundle.get("feature_cols") or []]
    weights: list[dict[str, Any]] = []
    measure = ""
    explanation = ""
    coefficient = getattr(estimator, "coef_", None)
    importance = getattr(estimator, "feature_importances_", None)
    if coefficient is not None:
        values = np.asarray(coefficient, dtype=float)
        if values.ndim == 2 and values.shape[0] == 1:
            values = values[0]
        elif values.ndim != 1:
            values = np.asarray([], dtype=float)
            explanation = (
                "El modelo tiene varios vectores de coeficientes; esta primera "
                "versión no los reduce a un único efecto."
            )
        names = _coefficient_feature_names(bundle)
        if len(names) == len(values):
            measure = "coeficiente"
            explanation = (
                "Coeficientes sobre las variables ya preprocesadas. El signo "
                "indica si empujan la probabilidad hacia arriba o hacia abajo; "
                "no implica causalidad."
            )
            weights = [
                {
                    "feature": name,
                    "kind": _feature_kind(name),
                    "value": float(value),
                    "magnitude": abs(float(value)),
                    "direction": "sube" if value > 0 else "baja" if value < 0 else "neutro",
                }
                for name, value in zip(names, values, strict=True)
            ]
        elif not explanation:
            explanation = (
                "El número de coeficientes no coincide con los nombres de "
                "variables almacenados; no se muestran asociaciones dudosas."
            )
    elif importance is not None:
        values = np.asarray(importance, dtype=float).reshape(-1)
        if len(feature_cols) == len(values):
            measure = "importancia"
            explanation = (
                "Importancia interna del bosque. Mide cuánto se usó una variable, "
                "pero no ofrece dirección ni demuestra causalidad."
            )
            weights = [
                {
                    "feature": name,
                    "kind": _feature_kind(name),
                    "value": float(value),
                    "magnitude": abs(float(value)),
                    "direction": "sin dirección",
                }
                for name, value in zip(feature_cols, values, strict=True)
            ]
        else:
            explanation = (
                "La importancia interna no coincide con las variables almacenadas; "
                "no se muestran asociaciones dudosas."
            )
    else:
        explanation = (
            "Este algoritmo no guarda un peso global fijo por variable. Se muestran "
            "sus entradas y rangos; una explicación local requerirá una consulta "
            "concreta en una fase posterior."
        )
    weights.sort(key=lambda row: (-row["magnitude"], row["feature"]))
    fit_config = bundle.get("fit_config")
    if not isinstance(fit_config, Mapping):
        fit_config = {}
    details: dict[str, Any] = {}
    for attribute in (
        "n_neighbors",
        "weights",
        "metric",
        "kernel",
        "n_estimators",
        "max_depth",
        "n_iter_",
    ):
        value = getattr(estimator, attribute, None)
        if isinstance(value, (str, int, float, bool)) or value is None:
            if value is not None:
                details[attribute] = value
    fit_x = getattr(estimator, "_fit_X", None)
    if fit_x is not None and hasattr(fit_x, "shape"):
        details["stored_training_vectors"] = int(fit_x.shape[0])
    return {
        "model_type": _class_name(estimator),
        "pipeline_steps": steps,
        "training_row_count": int(bundle.get("training_row_count") or 0),
        "training_species_ids": [
            str(value) for value in bundle.get("training_species_ids") or []
        ],
        "feature_count": len(feature_cols),
        "measure": measure,
        "explanation": explanation,
        "weights": weights,
        "support": _support_rows(bundle),
        "fit_config": dict(fit_config),
        "details": details,
    }


def inspect_catalog_row(catalog: RuntimeCatalog, row: Mapping[str, Any]) -> dict[str, Any]:
    ref = row["artifact_ref"]
    horizons = [int(value) for value in row["supported_horizons"]]
    model_ref = {**dict(ref), "horizon_days": min(horizons)}
    manifest = catalog.manifests[str(ref["batch_id"])]
    paths = mushroom_predictor_runtime.service_paths(catalog.runtime.root)
    bundle = runtime_inference.load_exact_artifact(
        catalog.registry,
        manifest,
        model_ref,
        root=paths["models_dir"],
        checked_manifest=manifest,
        artifact_row=row,
        cache=False,
    )
    return summarize_bundle(bundle)


def _label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()


def _selected_value(
    values: Sequence[str], requested: str, preferred: str = ""
) -> str:
    if requested in values:
        return requested
    if preferred in values:
        return preferred
    return values[0] if values else ""


def _options(
    values: Sequence[str], selected: str, labels: Mapping[str, str] | None = None
) -> str:
    labels = labels or {}
    return "".join(
        '<option value="{}"{}>{}</option>'.format(
            html.escape(value, quote=True),
            " selected" if value == selected else "",
            html.escape(labels.get(value) or _label(value)),
        )
        for value in values
    )


def _fmt(value: object) -> str:
    numeric = _numeric(value)
    if numeric is None:
        return "—"
    if numeric == 0:
        return "0"
    if abs(numeric) >= 1000 or abs(numeric) < 0.001:
        return f"{numeric:.3e}"
    return f"{numeric:.4f}".rstrip("0").rstrip(".")


def _json_text(value: object) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _page_shell(content: str, *, title: str = "Explorador de modelos") -> str:
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:#17212b;--muted:#647383;--line:#dce3e8;--paper:#fff;--bg:#f4f7f5;--accent:#176b55;--up:#16734f;--down:#a34a38}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:28px 20px 60px}} h1{{font-size:30px;margin:0 0 6px}} h2{{font-size:20px;margin:0 0 12px}} p{{margin:6px 0 16px}} .muted{{color:var(--muted)}}
.card{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px;margin-top:16px;box-shadow:0 2px 10px #18251b0a}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:12px}} label{{font-weight:650;font-size:13px}} select,button{{width:100%;margin-top:5px;padding:10px;border:1px solid #bac6cc;border-radius:8px;background:#fff;color:var(--ink)}} button{{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:700;cursor:pointer}}
.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}} .fact{{background:#f7f9f8;border-radius:9px;padding:10px}} .fact b{{display:block;font-size:12px;color:var(--muted);margin-bottom:3px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}} th{{position:sticky;top:0;background:#f7f9f8}} .scroll{{overflow:auto;max-height:620px;border:1px solid var(--line);border-radius:9px}} code{{font-size:12px}} .up{{color:var(--up);font-weight:700}} .down{{color:var(--down);font-weight:700}} details summary{{cursor:pointer;font-weight:700;padding:4px 0 10px}} .error{{border-color:#e2a89d;background:#fff8f6}}
@media(max-width:650px){{main{{padding:18px 10px}} th,td{{padding:7px 5px}}}}
</style></head><body><main>{content}</main></body></html>"""


def _render_summary(row: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    ref = row["artifact_ref"]
    weights = summary["weights"]
    max_magnitude = max((float(item["magnitude"]) for item in weights), default=0.0)
    weight_rows = "".join(
        "<tr><td><code>{}</code></td><td>{}</td><td class=\"{}\">{}</td>"
        "<td>{}</td><td><div style=\"height:7px;background:#dbe9e3;border-radius:5px;width:{}%\"></div></td></tr>".format(
            html.escape(item["feature"]),
            html.escape(item["kind"]),
            "up" if item["direction"] == "sube" else "down" if item["direction"] == "baja" else "",
            html.escape(item["direction"]),
            _fmt(item["value"]),
            round(100 * float(item["magnitude"]) / max_magnitude, 2) if max_magnitude else 0,
        )
        for item in weights
    )
    support_rows = "".join(
        "<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(item["feature"]), html.escape(item["kind"]),
            _fmt(item["min"]), _fmt(item["mean"]), _fmt(item["max"]), _fmt(item["std"]),
        )
        for item in summary["support"]
    )
    learned = (
        f"""<details open><summary>Variables aprendidas ({len(weights)})</summary>
        <p class="muted">{html.escape(str(summary['explanation']))}</p>
        <div class="scroll"><table><thead><tr><th>Variable exacta</th><th>Tipo</th><th>Dirección</th><th>{html.escape(str(summary['measure']))}</th><th>Magnitud relativa</th></tr></thead><tbody>{weight_rows}</tbody></table></div></details>"""
        if weights
        else f"<p>{html.escape(str(summary['explanation']))}</p>"
    )
    return f"""<section class="card"><h2>Qué contiene este modelo</h2>
    <div class="facts">
      <div class="fact"><b>Especie del artefacto</b>{html.escape(str(ref['species_id']))}</div>
      <div class="fact"><b>Versión</b>{html.escape(str(ref['version_id']))}</div>
      <div class="fact"><b>Contrato temporal</b>{html.escape(str(ref['temporal_contract_id']))}</div>
      <div class="fact"><b>Perfil</b>{html.escape(str(ref['profile_id']))}</div>
      <div class="fact"><b>Algoritmo</b>{html.escape(str(ref['estimator_id']))}</div>
      <div class="fact"><b>Clase real</b><code>{html.escape(str(summary['model_type']))}</code></div>
      <div class="fact"><b>Filas de entrenamiento</b>{summary['training_row_count']}</div>
      <div class="fact"><b>Entradas originales</b>{summary['feature_count']}</div>
    </div>
    <p class="muted">Horizontes admitidos: {', '.join(str(value) for value in row['supported_horizons'])} días. El modelo se ha cargado después de verificar su SHA-256.</p></section>
    <section class="card">{learned}</section>
    <section class="card"><details><summary>Rangos observados durante el entrenamiento ({len(summary['support'])})</summary>
      <p class="muted">Son estadísticas del conjunto usado al entrenar, no umbrales de recomendación.</p>
      <div class="scroll"><table><thead><tr><th>Entrada original</th><th>Tipo</th><th>Mínimo</th><th>Media</th><th>Máximo</th><th>Desv. típica</th></tr></thead><tbody>{support_rows}</tbody></table></div>
    </details></section>
    <section class="card"><details><summary>Configuración y estructura técnica</summary>
      <p><b>Pipeline:</b> <code>{_json_text(summary['pipeline_steps'])}</code></p>
      <p><b>Ajuste:</b> <code>{_json_text(summary['fit_config'])}</code></p>
      <p><b>Detalles:</b> <code>{_json_text(summary['details'])}</code></p>
      <p><b>Especies de entrenamiento:</b> <code>{_json_text(summary['training_species_ids'])}</code></p>
    </details></section>"""


def render_page(worker_data_dir: Path, request_target: str) -> str:
    query = parse_qs(urlsplit(request_target).query, keep_blank_values=False)
    requested = {key: values[-1] for key, values in query.items() if values}
    runtimes = discover_runtimes(worker_data_dir)
    intro = """<h1>Explorador de modelos</h1>
    <p class="muted">Inspección de solo lectura de los modelos instalados en este worker. El catálogo no abre modelos; solo se carga el artefacto elegido al pulsar el botón.</p>"""
    if not runtimes:
        return _page_shell(
            intro + '<section class="card"><h2>No hay un runtime activo</h2><p>El worker todavía no tiene modelos instalados que se puedan inspeccionar.</p></section>'
        )
    runtime_ids = [item.runtime_id for item in runtimes]
    runtime_id = _selected_value(runtime_ids, requested.get("runtime", ""), "shared")
    runtime = next(item for item in runtimes if item.runtime_id == runtime_id)
    catalog = load_runtime_catalog(runtime)
    if not catalog.rows:
        return _page_shell(
            intro + '<section class="card"><h2>Catálogo vacío</h2><p>El runtime activo no contiene artefactos multiversión.</p></section>'
        )
    rows = list(catalog.rows)
    batches = sorted({str(row["artifact_ref"]["batch_id"]) for row in rows}, reverse=True)
    batch = _selected_value(batches, requested.get("batch", ""))
    rows = [row for row in rows if row["artifact_ref"]["batch_id"] == batch]
    species_values = sorted({str(row["artifact_ref"]["species_id"]) for row in rows})
    species = _selected_value(species_values, requested.get("species", ""), "lactarius_deliciosus")
    rows = [row for row in rows if row["artifact_ref"]["species_id"] == species]
    versions = sorted({str(row["artifact_ref"]["version_id"]) for row in rows})
    version = _selected_value(versions, requested.get("version", ""), "biology_v3")
    rows = [row for row in rows if row["artifact_ref"]["version_id"] == version]
    contracts = sorted({str(row["artifact_ref"]["temporal_contract_id"]) for row in rows})
    contract = _selected_value(contracts, requested.get("contract", ""), "lag_event_biology_v3")
    rows = [row for row in rows if row["artifact_ref"]["temporal_contract_id"] == contract]
    profiles = sorted({str(row["artifact_ref"]["profile_id"]) for row in rows})
    profile = _selected_value(profiles, requested.get("profile", ""), "common_idw_plus_physical_state")
    rows = [row for row in rows if row["artifact_ref"]["profile_id"] == profile]
    estimators = sorted({str(row["artifact_ref"]["estimator_id"]) for row in rows})
    estimator = _selected_value(estimators, requested.get("estimator", ""), "logistic_regression_reduced_v1")
    rows = [row for row in rows if row["artifact_ref"]["estimator_id"] == estimator]
    selected = rows[0]
    runtime_labels = {item.runtime_id: item.display_name for item in runtimes}
    form = f"""<section class="card"><h2>Elegir un modelo</h2>
    <form method="get" action="{EXPLORER_PATH}"><div class="grid">
      <label>Runtime<select name="runtime" onchange="this.form.submit()">{_options(runtime_ids, runtime_id, runtime_labels)}</select></label>
      <label>Entrenamiento<select name="batch" onchange="this.form.submit()">{_options(batches, batch)}</select></label>
      <label>Especie<select name="species" onchange="this.form.submit()">{_options(species_values, species, catalog.species_names)}</select></label>
      <label>Versión biológica<select name="version" onchange="this.form.submit()">{_options(versions, version)}</select></label>
      <label>Contrato temporal<select name="contract" onchange="this.form.submit()">{_options(contracts, contract)}</select></label>
      <label>Perfil de variables<select name="profile" onchange="this.form.submit()">{_options(profiles, profile)}</select></label>
      <label>Algoritmo<select name="estimator" onchange="this.form.submit()">{_options(estimators, estimator)}</select></label>
      <label>&nbsp;<button type="submit" name="inspect" value="1">Inspeccionar este modelo</button></label>
    </div></form>
    <p class="muted">{len(catalog.rows)} artefactos disponibles. Cambiar un selector solo vuelve a leer el catálogo; el modelo no se abre hasta solicitar la inspección.</p></section>"""
    result = ""
    if requested.get("inspect") == "1":
        try:
            result = _render_summary(selected, inspect_catalog_row(catalog, selected))
        except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
            result = (
                '<section class="card error"><h2>No se pudo inspeccionar el modelo</h2><p>'
                + html.escape(str(exc))
                + "</p></section>"
            )
    return _page_shell(intro + form + result)


class ModelExplorerApp:
    """Small embeddable HTTP application mounted by the worker status server."""

    def __init__(self, worker_data_dir: Path) -> None:
        self.worker_data_dir = Path(worker_data_dir).resolve()

    def get(self, request_target: str) -> ExplorerResponse:
        path = urlsplit(request_target).path
        if not is_explorer_path(path):
            body = b'{"status":"not_found"}\n'
            return ExplorerResponse(404, "application/json; charset=utf-8", body)
        try:
            page = render_page(self.worker_data_dir, request_target)
        except Exception as exc:  # Keep a damaged optional UI away from worker health.
            content = (
                '<h1>Explorador de modelos</h1><section class="card error">'
                "<h2>No se pudo leer el catálogo</h2><p>"
                + html.escape(str(exc))
                + "</p></section>"
            )
            page = _page_shell(content)
            return ExplorerResponse(
                500, "text/html; charset=utf-8", page.encode("utf-8")
            )
        return ExplorerResponse(
            200, "text/html; charset=utf-8", page.encode("utf-8")
        )


def model_url(query: Mapping[str, object]) -> str:
    """Build a relative explorer URL suitable for a future HA link."""
    return EXPLORER_PATH + ("?" + urlencode(query) if query else "")


def serve(worker_data_dir: Path, *, host: str = "127.0.0.1", port: int = 8097) -> None:
    """Run the explorer as a standalone app when process isolation is useful."""
    app = ModelExplorerApp(worker_data_dir)

    class Handler(BaseHTTPRequestHandler):
        server_version = "RainmapperModelExplorer/0.1"

        def do_GET(self) -> None:  # noqa: N802
            response = app.get(self.path)
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explore worker model artifacts")
    parser.add_argument("--worker-data-dir", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8097)
    args = parser.parse_args(argv)
    serve(args.worker_data_dir, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through HTTP tests.
    raise SystemExit(main())
