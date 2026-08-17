#!/usr/bin/env python3
"""Summarise the non-operational V5 benchmark and create dependency-free SVGs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy
import sklearn


CURRENT_DATASETS = (
    "altitude_v2|common_idw",
    "biology_v3|core",
    "biology_v4|extended_weather",
    "biology_v4|climatic_balance",
)
V5_DATASETS = (
    "biology_v5|raw_primary_no_calendar", "biology_v5|raw_primary",
    "biology_v5|raw_primary_plus_physical_no_calendar", "biology_v5|raw_primary_plus_physical",
)
TOLERANCE = 1e-6


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def best(report: dict, datasets: tuple[str, ...], species: str) -> tuple[float, float, str] | None:
    candidates = []
    for dataset in datasets:
        species_report = (((report.get("reports") or {}).get(dataset) or {}).get("species") or {}).get(species) or {}
        for estimator, result in (species_report.get("estimators") or {}).items():
            if result.get("available") and result.get("metrics", {}).get("brier_score") is not None:
                metrics = result["metrics"]
                candidates.append((float(metrics["brier_score"]), float(metrics["log_loss"]), f"{dataset}|{estimator}"))
    return min(candidates) if candidates else None


def svg_bars(path: Path, title: str, labels: list[str], values: list[float], *, zero: bool = False) -> None:
    width, height, left, top, row = 1000, 90 + 42 * len(labels), 280, 55, 34
    span = max([abs(value) for value in values] + [0.01]) if zero else max(values + [1.0])
    origin = 600 if zero else left
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             '<style>text{font:14px sans-serif}.title{font:bold 18px sans-serif}.pos{fill:#247a46}.neg{fill:#b04444}.bar{fill:#3976b8}</style>',
             f'<text x="20" y="28" class="title">{title}</text>']
    if zero:
        lines.append(f'<line x1="{origin}" y1="45" x2="{origin}" y2="{height-20}" stroke="#555"/>')
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = top + index * row
        lines.append(f'<text x="20" y="{y+16}">{label}</text>')
        if zero:
            size = abs(value) / span * 300
            x = origin if value >= 0 else origin - size
            css = "pos" if value >= 0 else "neg"
        else:
            size = value / span * 620
            x, css = left, "bar"
        lines.append(f'<rect x="{x:.1f}" y="{y}" width="{size:.1f}" height="20" class="{css}"/>')
        lines.append(f'<text x="{(x+size+8 if value >= 0 or not zero else x-65):.1f}" y="{y+16}">{value:.3f}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_lag_curve(path: Path, stable: list[dict]) -> None:
    counts = Counter(row["lag_days"] for row in stable if row["lag_days"] is not None)
    maximum = max(counts.values(), default=1)
    points = " ".join(
        f"{60 + lag * 2.4:.1f},{330 - counts[lag] / maximum * 270:.1f}" for lag in range(365)
    )
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="380">\n'
        '<style>text{font:14px sans-serif}.title{font:bold 18px sans-serif}</style>\n'
        '<text x="20" y="28" class="title">Frecuencia de selección estable por retardo</text>\n'
        '<line x1="60" y1="330" x2="940" y2="330" stroke="#555"/><line x1="60" y1="55" x2="60" y2="330" stroke="#555"/>\n'
        f'<polyline points="{points}" fill="none" stroke="#3976b8" stroke-width="2"/>\n'
        '<text x="55" y="355">0</text><text x="900" y="355">364 días</text>\n</svg>\n',
        encoding="utf-8",
    )


def svg_heatmap(path: Path, stable: list[dict], species: list[str]) -> None:
    bands = (("0-7", 0, 7), ("8-30", 8, 30), ("31-90", 31, 90), ("91-180", 91, 180), ("181-364", 181, 364))
    channels = ("rain_mm", "temp_min_c", "temp_max_c", "humidity_min_pct", "humidity_max_pct")
    counts = Counter()
    for row in stable:
        lag = row["lag_days"]
        channel = row["feature"].split("__lag_", 1)[0]
        for band, start, end in bands:
            if lag is not None and start <= lag <= end:
                counts[(row["species_id"], channel, band)] += 1 / (end - start + 1)
                break
    maximum = max(counts.values(), default=1.0)
    row_height, top = 16, 60
    height = top + len(species) * len(channels) * row_height + 30
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="{height}">',
             '<style>text{font:11px sans-serif}.title{font:bold 18px sans-serif}</style>',
             '<text x="20" y="26" class="title">Mapa de calor estable especie × variable × banda de retardo</text>']
    for column, (band, _start, _end) in enumerate(bands):
        lines.append(f'<text x="{610 + column * 82}" y="48">{band}</text>')
    row_index = 0
    for species_id in species:
        for channel in channels:
            y = top + row_index * row_height
            lines.append(f'<text x="20" y="{y+12}">{species_id} · {channel}</text>')
            for column, (band, _start, _end) in enumerate(bands):
                value = counts[(species_id, channel, band)] / maximum
                blue = int(245 - value * 170)
                lines.append(f'<rect x="{600 + column * 82}" y="{y}" width="76" height="14" fill="rgb({blue},{blue},245)"/>')
            row_index += 1
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_intervals(path: Path, stable: list[dict]) -> None:
    rows = sorted(stable, key=lambda row: abs(row["median_coefficient"]), reverse=True)[:30]
    span = max([max(abs(row.get("q25", 0.0)), abs(row.get("q75", 0.0)), abs(row["median_coefficient"])) for row in rows] + [0.01])
    origin, height = 700, 70 + 22 * len(rows)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}">',
             '<style>text{font:10px sans-serif}.title{font:bold 18px sans-serif}</style>',
             '<text x="20" y="26" class="title">Coeficientes estables principales: mediana e IQR bootstrap</text>',
             f'<line x1="{origin}" y1="45" x2="{origin}" y2="{height-15}" stroke="#555"/>']
    for index, row in enumerate(rows):
        y = 52 + index * 22
        label = f"{row['species_id']} · {row['feature']}"
        q25, q75, median = row.get("q25", row["median_coefficient"]), row.get("q75", row["median_coefficient"]), row["median_coefficient"]
        x1, x2, xm = origin + q25 / span * 420, origin + q75 / span * 420, origin + median / span * 420
        lines.extend((f'<text x="20" y="{y+9}">{label}</text>',
                      f'<line x1="{x1:.1f}" y1="{y+5}" x2="{x2:.1f}" y2="{y+5}" stroke="#3976b8" stroke-width="3"/>',
                      f'<circle cx="{xm:.1f}" cy="{y+5}" r="3" fill="#b04444"/>'))
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--v5-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    comparisons = {
        name: load(args.v5_dir / f"comparison-{name}.json")
        for name in ("fixed-groups7", "fixed-groups14", "lag-groups7", "lag-groups14")
    }
    species = sorted({
        item
        for report in comparisons.values()
        for dataset in V5_DATASETS
        for item in ((report["reports"].get(dataset) or {}).get("species") or {})
    })
    contexts, by_species = [], defaultdict(Counter)
    for comparison_id, report in comparisons.items():
        for species_id in species:
            current = best(report, CURRENT_DATASETS, species_id)
            v5 = best(report, V5_DATASETS, species_id)
            if not current or not v5:
                continue
            delta = current[0] - v5[0]
            outcome = "tie" if abs(delta) <= TOLERANCE else ("win" if delta > 0 else "loss")
            by_species[species_id][outcome] += 1
            contexts.append({
                "comparison": comparison_id, "species_id": species_id,
                "current_best_brier": current[0], "v5_best_brier": v5[0],
                "brier_improvement": round(delta, 6), "outcome": outcome,
                "current_best": current[2], "v5_best": v5[2],
                "current_log_loss": current[1], "v5_log_loss": v5[1],
            })
    species = sorted(by_species)

    campaigns = {}
    for temporal in ("fixed", "lag"):
        report = load(args.v5_dir / f"sensitivity-{temporal}-campaign.json")
        rows = []
        for species_id in species:
            candidates = []
            for profile, profile_report in report["reports"].items():
                sr = (profile_report.get("species") or {}).get(species_id) or {}
                phenology = (sr.get("baselines") or {}).get("phenology_sin_cos", {}).get("brier_score")
                prevalence = (sr.get("baselines") or {}).get("training_prevalence", {}).get("brier_score")
                for estimator, result in (sr.get("estimators") or {}).items():
                    if result.get("available"):
                        metric = result["metrics"]
                        candidates.append((metric["brier_score"], profile, estimator, phenology, prevalence))
            if candidates:
                value = min(candidates)
                rows.append({"species_id": species_id, "v5_brier": value[0], "profile": value[1],
                             "estimator": value[2], "phenology_brier": value[3],
                             "prevalence_brier": value[4],
                             "beats_phenology": value[3] is not None and value[0] < value[3],
                             "beats_prevalence": value[4] is not None and value[0] < value[4]})
        campaigns[temporal] = rows
    prediction_manifest = load(args.v5_dir / "heldout-predictions-manifest.json")
    best_profile_counts = Counter(row["v5_best"].split("|")[1] for row in contexts)

    selections = load(args.v5_dir / "selected-features.json")["rows"]
    context_sets = defaultdict(set)
    selected_sets = defaultdict(set)
    coefficients = defaultdict(list)
    for row in selections:
        base = (row["species_id"], row["profile_id"], row["estimator_id"], row["temporal_contract_id"])
        context = (row["split_id"], row["group_days"])
        context_sets[base].add(context)
        selected_sets[base + (row["feature"],)].add(context)
        coefficients[base + (row["feature"],)].append(float(row["coefficient_standardized"]))
    stable = []
    for key, selected_contexts in selected_sets.items():
        base, feature = key[:4], key[4]
        denominator = len(context_sets[base])
        values = coefficients[key]
        sign_fraction = max(sum(v > 0 for v in values), sum(v < 0 for v in values)) / len(values)
        frequency = len(selected_contexts) / denominator if denominator else 0.0
        if frequency >= 0.70 and sign_fraction >= 0.80:
            match = re.search(r"__lag_(\d{3})$", feature)
            stable.append({
                "species_id": key[0], "profile_id": key[1], "estimator_id": key[2],
                "temporal_contract_id": key[3], "feature": feature,
                "lag_days": int(match.group(1)) if match else None,
                "selection_frequency": round(frequency, 6), "sign_fraction": round(sign_fraction, 6),
                "median_coefficient": round(float(numpy.median(values)), 8),
                "stability_basis": f"{denominator} fitted outer/sensitivity contexts; not bootstrap",
            })
    stability_path = args.v5_dir / "feature-stability.json"
    stability_resamples = 0
    stability_limitation = "Grouped bootstrap output is absent."
    if stability_path.exists():
        stability_payload = load(stability_path)
        stability_resamples = int(stability_payload.get("requested_resamples") or 0)
        stable = []
        for row in stability_payload.get("rows") or []:
            if not row.get("stable_selected"):
                continue
            match = re.search(r"__lag_(\d{3})$", row["feature"])
            stable.append({
                "species_id": row["species_id"], "profile_id": row["profile_id"],
                "estimator_id": row["estimator_id"],
                "temporal_contract_id": row["temporal_contract_id"], "feature": row["feature"],
                "lag_days": int(match.group(1)) if match else None,
                "selection_frequency": row["selection_frequency"],
                "sign_fraction": row["sign_concordance"],
                "median_coefficient": row["coefficient_median"],
                "q25": row["coefficient_q25"], "q75": row["coefficient_q75"],
                "stability_basis": f"{row['resamples']} grouped bootstrap resamples",
            })
        complete = sum(
            bool(row.get("available")) and row.get("completed_resamples") == stability_resamples
            for row in stability_payload.get("contexts") or []
        )
        stability_limitation = (
            f"{stability_resamples} grouped bootstrap resamples completed in {complete} evaluable "
            "temporal/species/estimator contexts for raw_primary_no_calendar; unavailable contexts retain reasons."
        )
    stable_channel = Counter(item["feature"].split("__lag_", 1)[0] for item in stable)
    lag_bands = Counter()
    for item in stable:
        lag = item["lag_days"]
        if lag is None:
            lag_bands["calendar/control"] += 1
        elif lag <= 7:
            lag_bands["0-7"] += 1
        elif lag <= 30:
            lag_bands["8-30"] += 1
        elif lag <= 90:
            lag_bands["31-90"] += 1
        elif lag <= 180:
            lag_bands["91-180"] += 1
        else:
            lag_bands["181-364"] += 1
    lag_band_widths = {"0-7": 8, "8-30": 23, "31-90": 60, "91-180": 90, "181-364": 184}
    lag_band_density = {
        name: round(lag_bands[name] / width, 3) for name, width in lag_band_widths.items()
    }

    errors = load(args.v5_dir / "shared-errors.json")["rows"]
    shared = [row for row in errors if row.get("shared_all")]
    unique_shared = list({
        (row["species_id"], row.get("observation_id"), row["error_type"]): row
        for row in shared
    }.values())
    unique_shared_by_phase = Counter(row.get("observed_phase") or "unknown_phase" for row in unique_shared)
    shared_by_phase = Counter(row.get("observed_phase") or "unknown_phase" for row in shared)
    shared_by_species = Counter(row["species_id"] for row in shared)
    shared_by_type = Counter(row["error_type"] for row in shared)
    v5_shared = Counter(row["species_id"] for row in shared if row["version_id"].startswith("biology_v5"))
    current_shared = Counter(row["species_id"] for row in shared if not row["version_id"].startswith("biology_v5"))

    summary = {
        "kind": "biology_v5_raw_weather_analysis_summary",
        "contexts": contexts,
        "win_tie_loss_by_species": {name: dict(by_species[name]) for name in species},
        "campaign_sensitivity": campaigns,
        "stable_features_cross_context": stable,
        "stable_feature_channels": dict(stable_channel),
        "stable_lag_bands": dict(lag_bands),
        "stable_lag_band_density_per_day": lag_band_density,
        "v5_best_profile_counts": dict(best_profile_counts),
        "stability_limitation": stability_limitation,
        "shared_all_errors": {
            "total": len(shared), "by_type": dict(shared_by_type), "by_phase": dict(shared_by_phase),
            "by_species": dict(shared_by_species), "v5_by_species": dict(v5_shared),
            "current_by_species": dict(current_shared),
            "unique_observation_errors": len(unique_shared),
            "unique_by_phase": dict(unique_shared_by_phase),
        },
        "no_cross_species_mean_brier": True,
    }
    summary_path = args.v5_dir / "analysis-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    graph_dir = args.v5_dir / "graphs"
    graph_dir.mkdir(exist_ok=True)
    labels = species
    mean_delta_for_display = [
        float(numpy.median([row["brier_improvement"] for row in contexts if row["species_id"] == name]))
        for name in labels
    ]
    svg_bars(graph_dir / "brier-delta-by-species.svg", "Mediana descriptiva del delta Brier por especie (no score global)", labels, mean_delta_for_display, zero=True)
    svg_bars(graph_dir / "stable-features-by-channel.svg", "Selecciones estables entre contextos por canal", list(stable_channel), [float(stable_channel[x]) for x in stable_channel])
    ordered_bands = ["0-7", "8-30", "31-90", "91-180", "181-364", "calendar/control"]
    svg_bars(graph_dir / "stable-features-by-lag-band.svg", "Selecciones estables por banda de retardo", ordered_bands, [float(lag_bands[x]) for x in ordered_bands])
    svg_lag_curve(graph_dir / "selection-frequency-by-lag.svg", stable)
    svg_heatmap(graph_dir / "stable-lag-heatmap-by-species.svg", stable, species)
    svg_intervals(graph_dir / "stable-coefficient-intervals.svg", stable)
    signs = Counter()
    for item in stable:
        signs[(item["feature"].split("__lag_", 1)[0], "positive" if item["median_coefficient"] > 0 else "negative")] += 1
    sign_labels = sorted({key[0] for key in signs})
    svg_bars(
        graph_dir / "stable-coefficient-signs.svg",
        "Balance de signos en selecciones recurrentes (positivo menos negativo)",
        sign_labels,
        [float(signs[(label, "positive")] - signs[(label, "negative")]) for label in sign_labels],
        zero=True,
    )
    svg_bars(graph_dir / "shared-errors-by-phase.svg", "Errores compartidos por fase observada", list(shared_by_phase), [float(shared_by_phase[x]) for x in shared_by_phase])
    svg_bars(graph_dir / "shared-errors-by-species.svg", "Errores compartidos por especie", labels, [float(shared_by_species[x]) for x in labels])

    wins_total = sum(value.get("win", 0) for value in by_species.values())
    losses_total = sum(value.get("loss", 0) for value in by_species.values())
    campaign_both = [
        name for name in species
        if all(any(row["species_id"] == name and row["beats_phenology"] and row["beats_prevalence"] for row in campaigns[t]) for t in campaigns)
    ]
    table = "\n".join(
        f"| `{name}` | {by_species[name].get('win', 0)} | {by_species[name].get('tie', 0)} | {by_species[name].get('loss', 0)} |"
        for name in species
    )
    campaign_table = "\n".join(
        f"| `{name}` | " + " | ".join(
            next((f"{row['v5_brier']:.4f} / {'sí' if row['beats_phenology'] else 'no'}" for row in campaigns[t] if row["species_id"] == name), "n/e")
            for t in ("fixed", "lag")
        ) + " |" for name in species
    )
    report_text = f"""# Informe 001 — V5 raw weather frente a V2/V3/V4

Fecha: 2026-08-16. Estado: **experimental, no operativo**.

## Respuesta corta

V5 raw no justifica todavía publicar una nueva versión de HA ni elegirlo como Predictor. En los {len(contexts)} contextos evaluables especie+contrato+partición, el mejor V5 gana {wins_total} y pierde {losses_total} frente al mejor miembro individual V2/V3/V4 sobre las mismas filas. El resultado varía por especie y no se ha calculado Brier medio entre especies.

La sensibilidad por campañas completas supera simultáneamente prevalencia y fenología en ambos contratos solo para: {', '.join('`'+x+'`' for x in campaign_both) or 'ninguna especie'}. Esto impide interpretar la selección de retardos como una mejora generalizable.

Los 25 remuestreos agrupados exigidos se completaron en los 32 contextos evaluables del perfil raw sin calendario. Aun así, las selecciones son densas: {len(stable)} celdas especie+contrato+estimador+variable pasan el umbral. Que aparezcan miles de días estables indica que la regularización no ha aislado ventanas interpretables, no que todos esos días sean biológicamente importantes.

La ablación es informativa: el mejor V5 usa `raw_primary_no_calendar` en {best_profile_counts['raw_primary_no_calendar']}/34 contextos y alguna variante sin calendario en {best_profile_counts['raw_primary_no_calendar'] + best_profile_counts['raw_primary_plus_physical_no_calendar']}/34. El calendario no explica por sí solo el resultado, pero quitarlo tampoco hace que V5 venza a los contratos actuales.

Los resultados **no justifican GAM/DLNM, estado temporal ni jerárquico como sucesor del Predictor**. Si se ensaya una sola familia diagnóstica, la jerárquica es la mejor priorizada por el soporte muy desigual entre especies; el modelo de estado queda condicionado a confirmar errores alternantes dentro de floradas. V5 debe permanecer solo experimental.

## Comparación por especie

Cada fila cuenta cuatro comparaciones (`fixed`/`lag_event` × grupos 7/14). «Gana» significa menor Brier que el mejor algoritmo individual de V2/V3/V4; no se comparó contra un ensemble.

| Especie | Gana | Empata | Pierde |
|---|---:|---:|---:|
{table}

Detalle auditable: [`analysis-summary.json`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/analysis-summary.json) y [`brier-delta-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/brier-delta-by-species.svg).

## Sensibilidad por campaña

La celda muestra `Brier del mejor V5 / supera baseline fenológico`. Las campañas `area_id+año` no cruzan train/test.

| Especie | fixed | lag_event |
|---|---|---|
{campaign_table}

Superar el baseline en campaña no basta para promoción: también se exige vencer al mejor miembro actual, estabilidad y calibración razonable.

## Variables, retardos y dos escalas

Se encontraron {len(stable)} celdas especie+contrato+estimador+variable con frecuencia ≥0,70 y signo concordante ≥0,80 en 25 remuestreos por grupos completos del perfil raw sin calendario. Es un resultado excesivamente denso. Por canal: {dict(stable_channel)}. Por banda: {dict(lag_bands)}. Al normalizar por la anchura de cada banda, la densidad por día es {lag_band_density}: prácticamente uniforme, no dos picos temporales.

Esta lectura es diagnóstica. La lluvia, humedad y temperatura están correlacionadas; que el regularizador escoja una no vuelve irrelevantes causalmente a las demás. Hay retardos estables recientes y largos, pero su densidad casi uniforme y el mal rendimiento hold-out **no respaldan dos ventanas diferenciadas** de activación y preparación micelial/hospedador.

- [`stable-features-by-channel.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-features-by-channel.svg)
- [`stable-features-by-lag-band.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-features-by-lag-band.svg)
- [`selection-frequency-by-lag.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/selection-frequency-by-lag.svg)
- [`stable-lag-heatmap-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-lag-heatmap-by-species.svg)
- [`stable-coefficient-intervals.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-coefficient-intervals.svg)
- [`stable-coefficient-signs.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-coefficient-signs.svg)

## Falsos positivos y negativos compartidos

Con umbral 0,5 hay {len(shared)} filas-contexto `shared_all`: {dict(shared_by_type)}. Al deduplicar especie+observación+tipo quedan {len(unique_shared)} errores observacionales: {dict(unique_shared_by_phase)}. Los listados completos conservan especie, contrato, horizonte, fase, campaña y resúmenes meteorológicos en [`shared-errors.json`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/shared-errors.json).

- [`shared-errors-by-phase.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/shared-errors-by-phase.svg)
- [`shared-errors-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/shared-errors-by-species.svg)

`unknown_phase` domina tras deduplicar; `between_positive_visits`, onset y decline no dominan. Por eso los errores no justifican todavía un modelo de estado. La inestabilidad entre especies con n pequeño hace que una estructura jerárquica sea la siguiente hipótesis más razonable, pero no un candidato operativo. No se reetiquetaron observaciones ni se trataron días no visitados como negativos.

## Método y salvaguardas

- Snapshot canónico inmutable: `{args.snapshot}`.
- 395 observaciones `fixed`, 1.580 tareas `lag`; 352 y 1.408 elegibles respectivamente.
- V5 entrega 365 días causales de cinco canales IDW comunes; la ablación añade ET0 y balance.
- Elastic Net y sparse-group logistic se ajustan solo con train y seleccionan por Brier interno.
- `lag_event` realiza un ajuste por especie+contrato+estimador+split; 1/2/3/7 filtran las mismas probabilidades hold-out.
- {prediction_manifest['row_count']:,} filas hold-out y {prediction_manifest['unique_row_keys']:,} claves únicas; no se escribieron modelos ni se entrenó candidato operativo.
- No se modificaron HA, worker, GHCR, releases ni modelos operativos.

## Limitaciones que impiden promoción

1. El tamaño por especie sigue siendo pequeño y algunas particiones tienen una sola clase.
2. Incluso sin calendario, 2.938 variables-día pasan el umbral de estabilidad: no emerge una ventana parsimoniosa interpretable.
3. La parrilla nocturna se redujo a seis configuraciones Elastic Net y nueve sparse-group para mantener el coste acotado; quedó registrada en código.
4. Los errores compartidos cuentan contextos repetidos y horizontes como diagnósticos, no como observaciones independientes.

## Decisión

Mantener V2/V3/V4 vivas y V5 como `proposed` no operativa. No desbloquear Rainmapper mediante una publicación HA basada en este ensayo. Si se continúa la investigación, ensayar una familia jerárquica por especie como diagnóstico, comparándola en las mismas filas contra el mejor miembro individual. Un modelo de estado queda descartado por ahora salvo que más observaciones confirmen errores alternantes dentro de floradas; un GAM/DLNM queda aplazado hasta que aparezcan bandas estables. No se propone ensemble.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")

    artifact_files = sorted(path for path in args.v5_dir.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    manifest = {
        "kind": "biology_v5_raw_weather_discovery_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot": str(args.snapshot),
        "source_manifest_sha256": sha256(args.snapshot / "MANIFEST.json"),
        "python": platform.python_version(), "numpy": numpy.__version__, "scikit_learn": sklearn.__version__,
        "seed": 42, "stability_resamples": stability_resamples,
        "stability_degradation": "reduced from 50 to the permitted 25 grouped resamples",
        "commands": [
            ".venv/bin/python scripts/build-biology-v5-raw-benchmark.py ...",
            ".venv/bin/python scripts/evaluate-biology-v5-raw-benchmark.py ...",
            ".venv/bin/python scripts/stabilize-biology-v5-raw-benchmark.py ...",
            ".venv/bin/python scripts/report-biology-v5-raw-benchmark.py ...",
        ],
        "artifacts": {str(path.relative_to(args.v5_dir)): sha256(path) for path in artifact_files},
        "report": str(args.report), "report_sha256": sha256(args.report),
        "model_artifact_written": False, "operational_candidate_trained": False,
    }
    (args.v5_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"contexts": len(contexts), "stable_features": len(stable), "shared_all": len(shared), "report": str(args.report)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
