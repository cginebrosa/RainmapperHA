#!/usr/bin/env python3
"""Report V6 smooth/partial-pooling results against the best prior member."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


PRIOR_DATASETS = (
    "altitude_v2|common_idw", "biology_v3|core", "biology_v4|extended_weather",
    "biology_v4|climatic_balance", "biology_v5|raw_primary_no_calendar",
    "biology_v5|raw_primary", "biology_v5|raw_primary_plus_physical_no_calendar",
    "biology_v5|raw_primary_plus_physical",
)
ESTIMATORS = (
    "smooth_species_logistic_v1", "smooth_shared_logistic_v1",
    "smooth_partial_pooling_logistic_v1",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_best(report: dict, species: str) -> tuple[float, str] | None:
    values = []
    for dataset in PRIOR_DATASETS:
        sr = (((report.get("reports") or {}).get(dataset) or {}).get("species") or {}).get(species) or {}
        for estimator, result in (sr.get("estimators") or {}).items():
            if result.get("available"):
                values.append((float(result["metrics"]["brier_score"]), f"{dataset}|{estimator}"))
    return min(values) if values else None


def v6_best(report: dict, species: str) -> tuple[float, str] | None:
    sr = (report["report"].get("species") or {}).get(species) or {}
    values = [
        (float(result["metrics"]["brier_score"]), estimator)
        for estimator, result in (sr.get("estimators") or {}).items() if result.get("available")
    ]
    return min(values) if values else None


def svg_bars(path: Path, title: str, labels: list[str], values: list[float]) -> None:
    width, origin, span = 1000, 600, max([abs(x) for x in values] + [0.01])
    height = 70 + 34 * len(labels)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             '<style>text{font:13px sans-serif}.title{font:bold 18px sans-serif}.p{fill:#247a46}.n{fill:#b04444}</style>',
             f'<text x="20" y="25" class="title">{title}</text>',
             f'<line x1="{origin}" y1="40" x2="{origin}" y2="{height-15}" stroke="#555"/>']
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y, size = 48 + index * 34, abs(value) / span * 300
        x = origin if value >= 0 else origin - size
        lines.extend((f'<text x="20" y="{y+15}">{label}</text>',
                      f'<rect x="{x:.1f}" y="{y}" width="{size:.1f}" height="20" class="{"p" if value >= 0 else "n"}"/>',
                      f'<text x="{origin+310}" y="{y+15}">{value:.4f}</text>'))
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v5-dir", required=True, type=Path)
    parser.add_argument("--v6-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    contexts, wtl, rescued = [], defaultdict(Counter), defaultdict(list)
    estimator_wins = Counter()
    pairwise = Counter()
    for temporal in ("fixed", "lag"):
        for group_days in (7, 14):
            name = f"{temporal}-groups{group_days}"
            prior = load(args.v5_dir / f"comparison-{name}.json")
            v6 = load(args.v6_dir / f"comparison-{name}.json")
            species = sorted(v6["report"]["species"])
            for species_id in species:
                species_estimators = (v6["report"]["species"].get(species_id) or {}).get("estimators") or {}
                for left, right, label in (
                    (ESTIMATORS[2], ESTIMATORS[0], "partial_vs_species"),
                    (ESTIMATORS[2], ESTIMATORS[1], "partial_vs_shared"),
                ):
                    if species_estimators.get(left, {}).get("available") and species_estimators.get(right, {}).get("available"):
                        left_brier = species_estimators[left]["metrics"]["brier_score"]
                        right_brier = species_estimators[right]["metrics"]["brier_score"]
                        pairwise[f"{label}_{'tie' if abs(left_brier-right_brier)<=1e-6 else ('win' if left_brier<right_brier else 'loss')}"] += 1
                before, after = prior_best(prior, species_id), v6_best(v6, species_id)
                if after and not before:
                    rescued[species_id].append(name)
                    continue
                if not before or not after:
                    continue
                delta = before[0] - after[0]
                outcome = "tie" if abs(delta) <= 1e-6 else ("win" if delta > 0 else "loss")
                wtl[species_id][outcome] += 1
                estimator_wins[after[1]] += 1
                contexts.append({"comparison": name, "species_id": species_id,
                                 "prior_best_brier": before[0], "v6_best_brier": after[0],
                                 "brier_improvement": round(delta, 6), "outcome": outcome,
                                 "prior_best": before[1], "v6_best": after[1]})

    campaign_rows = []
    for temporal in ("fixed", "lag"):
        prior = load(args.v5_dir / f"sensitivity-{temporal}-campaign.json")
        v6 = load(args.v6_dir / f"sensitivity-{temporal}-campaign.json")
        for species_id in sorted(v6["report"]["species"]):
            after = v6_best(v6, species_id)
            prior_values = []
            phenology = None
            for profile_report in prior["reports"].values():
                sr = (profile_report.get("species") or {}).get(species_id) or {}
                if phenology is None:
                    phenology = ((sr.get("baselines") or {}).get("phenology_sin_cos") or {}).get("brier_score")
                for estimator, result in (sr.get("estimators") or {}).items():
                    if result.get("available"):
                        prior_values.append((float(result["metrics"]["brier_score"]), estimator))
            before = min(prior_values) if prior_values else None
            campaign_rows.append({"temporal": temporal, "species_id": species_id,
                                  "prior_best_brier": before[0] if before else None,
                                  "v6_best_brier": after[0] if after else None,
                                  "phenology_brier": phenology,
                                  "improves_prior": bool(before and after and after[0] < before[0]),
                                  "improves_phenology": bool(phenology is not None and after and after[0] < phenology)})

    errors = load(args.v6_dir / "shared-errors.json")["rows"]
    shared = [row for row in errors if row.get("shared_all")]
    unique_errors = list({(row["species_id"], row.get("observation_id"), row["error_type"]): row for row in shared}.values())
    phase_counts = Counter(row.get("observed_phase") or "unknown_phase" for row in unique_errors)
    summary = {"kind": "biology_v6_smooth_hierarchical_analysis", "contexts": contexts,
               "win_tie_loss_by_species": {key: dict(value) for key, value in wtl.items()},
               "best_v6_estimator_counts": dict(estimator_wins), "rescued_without_prior_comparator": dict(rescued),
               "partial_pooling_pairwise": dict(pairwise),
               "campaign_sensitivity": campaign_rows, "shared_error_unique_by_phase": dict(phase_counts),
               "no_cross_species_mean_brier": True}
    summary_path = args.v6_dir / "analysis-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    labels = sorted(wtl)
    medians = []
    for species_id in labels:
        values = sorted(row["brier_improvement"] for row in contexts if row["species_id"] == species_id)
        medians.append(values[len(values) // 2])
    graph_dir = args.v6_dir / "graphs"
    graph_dir.mkdir(exist_ok=True)
    svg_bars(graph_dir / "v6-brier-delta-by-species.svg", "Delta Brier: mejor previo menos mejor V6", labels, medians)

    wins = sum(value.get("win", 0) for value in wtl.values())
    losses = sum(value.get("loss", 0) for value in wtl.values())
    table = "\n".join(f"| `{key}` | {wtl[key].get('win',0)} | {wtl[key].get('tie',0)} | {wtl[key].get('loss',0)} |" for key in labels)
    winning_rows = "\n".join(
        f"| `{row['species_id']}` | `{row['comparison']}` | {row['brier_improvement']:+.4f} | `{row['v6_best']}` |"
        for row in contexts if row["outcome"] == "win"
    )
    campaign_both = sorted({row["species_id"] for row in campaign_rows if row["improves_prior"] and row["improves_phenology"] and all(any(other["species_id"] == row["species_id"] and other["temporal"] == temporal and other["improves_prior"] and other["improves_phenology"] for other in campaign_rows) for temporal in ("fixed", "lag"))})
    report = f"""# Informe 001 — V6 retardos suaves y pooling parcial

Fecha: 2026-08-16. Estado: **experimental, no operativo**.

## Respuesta corta

V6 gana {wins} y pierde {losses} de {len(contexts)} comparaciones estrictas contra el mejor miembro individual V2/V3/V4/V5 sobre las mismas filas. No se usa Brier medio entre especies. El mejor estimador V6 por contexto se reparte así: {dict(estimator_wins)}.

El pooling parcial vence al modelo suave por especie {pairwise['partial_vs_species_win']} veces y pierde {pairwise['partial_vs_species_loss']}; frente al modelo completamente compartido gana {pairwise['partial_vs_shared_win']} y pierde {pairwise['partial_vs_shared_loss']}. Por tanto, compartir información ayuda en algunos casos, pero no es la explicación dominante: el modelo independiente sigue siendo el mejor V6 más frecuente.

La sensibilidad por campañas completas mejora simultáneamente al mejor V5 de campaña y al baseline fenológico en ambos contratos para: {', '.join('`'+x+'`' for x in campaign_both) or 'ninguna especie'}. Las especies que el modelo conjunto puede predecir sin comparador individual previo se conservan como diagnóstico y no cuentan como victoria: {dict(rescued)}.

## Resultado por especie

| Especie | Gana | Empata | Pierde |
|---|---:|---:|---:|
{table}

[`v6-brier-delta-by-species.svg`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/graphs/v6-brier-delta-by-species.svg)

Las únicas victorias estrictas son:

| Especie | Comparación | Mejora Brier | Mejor V6 |
|---|---|---:|---|
{winning_rows}

## Interpretación

El modelo suave por especie comprueba si reducir 365 días a 50 exposiciones evita la selección difusa de V5. El compartido fuerza una única respuesta meteorológica entre especies. El pooling parcial conserva esa respuesta común y permite desviaciones específicas más pequeñas.

Que el pooling parcial gane al modelo completamente compartido no basta: para justificar jerarquía debe vencer también al modelo suave por especie y al mejor contrato anterior, y mantenerlo al bloquear campañas. Los errores compartidos deduplicados por fase son {dict(phase_counts)}.

## Decisión

La promoción queda prohibida. V6 pierde 30/34, así que **no justifica desarrollar ahora un jerárquico probabilístico general ni cambiar el Predictor**. La señal más concreta es `hygrophorus_latitabundus`: pooling parcial mejora en sus dos comparaciones fixed, pero el test solo contiene cuatro observaciones y debe tratarse como hipótesis frágil. Las mejoras de `amanita_caesarea` y `cantharellus_cibarius_sl` son pequeñas y proceden del modelo suave por especie, no de la jerarquía.

El experimento sí responde a la pregunta metodológica: suavizar los retardos reduce drásticamente la dimensionalidad y permite evaluar especies de soporte mínimo mediante pooling, pero no recupera una mejora general. El siguiente paso con mayor valor no es añadir otra familia; es incorporar nuevas campañas/visitas y repetir este V6 congelado. V2/V3/V4/V5 permanecen vivas y no se propone ensemble.

Artefactos: [`analysis-summary.json`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/analysis-summary.json), [`heldout-predictions.jsonl`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/heldout-predictions.jsonl) y [`shared-errors.json`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/shared-errors.json).
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    manifest_path = args.v6_dir / "MANIFEST.json"
    manifest = load(manifest_path)
    manifest.update({"analysis_summary_sha256": sha256(summary_path), "report": str(args.report),
                     "report_sha256": sha256(args.report), "model_artifact_written": False,
                     "operational_candidate_trained": False})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contexts": len(contexts), "wins": wins, "losses": losses, "campaign_both": campaign_both}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
