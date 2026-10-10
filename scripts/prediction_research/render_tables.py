"""Render only aggregate, publishable tables from the closed study analysis."""
from common import OUTPUT, load

NAMES = {"boletus_aereus": "Boletus aereus", "amanita_caesarea": "Amanita caesarea"}


def number(x):
    return "—" if x is None else f"{x:.2f}".rstrip("0").rstrip(".")


def percent(x):
    return "—" if x is None else f"{100*x:.1f} %"


def interval(x, *, percentage=True):
    render = percent if percentage else number
    return f"{render(x['lower'])} a {render(x['upper'])} ({x['finite_replicates']}/2000)"


def render(results):
    lines = ["# Tablas agregadas de la investigación — 03/10/2026", "",
        "Generadas con `scripts/prediction_research/render_tables.py` desde el análisis",
        "privado sellado. No contienen identificadores, coordenadas ni resultados por caso.", "",
        "A reproduce selección y consejo actuales con modelos experimentales; B aplica",
        "el umbral elegido exclusivamente en desarrollo. `Abs` es abstención, no desfavorable.",
        "Los promedios de horizontes reparten peso 1 entre las siete emisiones de cada",
        "observación. Los decimales de las matrices representan ese promedio, no personas",
        "o visitas fraccionarias. Por horizonte los recuentos son enteros.", ""]
    for sid, species in results["species"].items():
        lines += [f"## {NAMES[sid]}", "", "### Umbrales y soporte de desarrollo", "",
            "| Externo | Umbral B | Positivos / negativos | Grupos positivos / negativos | Motivo |",
            "|---|---:|---:|---:|---|"]
        for fold, choices in results["choices"].items():
            choice = choices[sid]; support = choice["support"]
            lines.append(f"| {fold} | {number(choice['threshold'])} | {support['positive_observations']} / {support['negative_observations']} | {support['positive_groups']} / {support['negative_groups']} | {choice['reason']} |")
        lines += ["", "### Externo: promedio de horizontes", "",
            "| Corte | Método | Obs / grupos | P→fav | P→desf | P→abs | N→fav | N→desf | N→abs | Precisión favorable | Favorables detectados | Cobertura |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for label in ("2024", "2025", "2026", "pooled"):
            value = species["strata"][label]["average"]
            for method in ("A", "B"):
                m, c = value[method]["metrics"], value[method]["matrix"]
                cells = " | ".join(number(x) for x in c.values())
                lines.append(f"| {label} | {method} | {value['observations']} / {value['groups']} | {cells} | {percent(m['precision'])} | {percent(m['recall'])} | {percent(m['coverage'])} |")
        lines += ["", "### Incertidumbre agregada", "",
            "Intervalos percentiles 95 %, 2.000 remuestreos de episodios por corte, modelos",
            "y reglas fijos. Entre paréntesis, réplicas con denominador válido. No incluyen",
            "incertidumbre de volver a entrenar/seleccionar; los grupos pueden seguir siendo dependientes.", "",
            "| Métrica | A: estimación | A: intervalo | B: estimación | B: intervalo | Diferencia B−A: intervalo |",
            "|---|---:|---|---:|---|---|"]
        pooled = species["strata"]["pooled"]["average"]
        for key, title in (("false_discovery_rate", "Falsos entre recomendaciones favorables"),
                           ("recall", "Favorables observados detectados"),
                           ("miss_rate", "Oportunidades favorables perdidas"),
                           ("coverage", "Consejos favorables o desfavorables / casos")):
            ci = pooled["bootstrap_95_percentile"]
            lines.append(f"| {title} | {percent(pooled['A']['metrics'][key])} | {interval(ci['A'][key])} | {percent(pooled['B']['metrics'][key])} | {interval(ci['B'][key])} | {interval(ci['B_minus_A'][key])} |")
        lines += ["", "Límite exploratorio unilateral 95 % de episodios recomendados con **algún**",
            "falso favorable. Es otra unidad, no un intervalo de precisión por predicción:", "",
            "| Método | Grupos recomendados | Grupos con algún falso favorable | Límite superior |",
            "|---|---:|---:|---:|"]
        for method, value in pooled["exploratory_group_bound"].items():
            lines.append(f"| {method} | {value['recommended_groups']} | {value['groups_with_any_false_favorable']} | {percent(value['one_sided_95_upper_event_rate'])} |")
        lines += ["", "### Matriz por corte y horizonte", "",
            "P: observado favorable; N: observado desfavorable. FP = N→fav.",
            "Oportunidades perdidas = P→desf + P→abs. Cobertura = todos los consejos",
            "favorables/desfavorables divididos por todas las observaciones.", "",
            "| Corte | h | Método | P→fav | P→desf | P→abs | N→fav | N→desf | N→abs | Precisión | Detección P | Cobertura |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for label in ("2024", "2025", "2026", "pooled"):
            for h, value in species["strata"][label]["horizons"].items():
                for method in ("A", "B"):
                    m, c = value[method]["metrics"], value[method]["matrix"]
                    cells = " | ".join(number(x) for x in c.values())
                    lines.append(f"| {label} | {h} | {method} | {cells} | {percent(m['precision'])} | {percent(m['recall'])} | {percent(m['coverage'])} |")
        lines += ["", "### Ganadores y abstenciones", "",
            f"Soporte espacial externo: {species['spatial_support']['areas']} áreas; no es una prueba de áreas completamente nuevas.", "",
            "Recuentos de emisiones con probabilidad del ganador disponible; pueden incluir",
            "veredicto incierto. Los motivos y ganadores no son observaciones independientes.", "",
            "| Corte | Familia | Emisiones |", "|---|---|---:|"]
        for fold, value in species["diagnostics"]["by_fold"].items():
            for name, count in sorted(value["winners_with_probability"].items(), key=lambda x: -x[1]):
                lines.append(f"| {fold} | `{name}` | {count} |")
        lines += ["", "| Motivo final | Emisiones |", "|---|---:|"]
        for reason, count in species["diagnostics"]["reason_counts"].items():
            lines.append(f"| `{reason}` | {count} |")
        lines += ["", "### Curva completa de desarrollo", "",
            "No se ha escogido el umbral con externos. VF y FF son verdaderos y falsos",
            "favorables, promediados sobre los siete horizontes. La admisibilidad exige",
            "todos los mínimos del protocolo y mejora estricta respecto a 0,60.", "",
            "| Externo | Umbral | VF | FF | Positivos perdidos | Grupos recomendados | Admisible |",
            "|---|---:|---:|---:|---:|---:|---|"]
        for fold, choices in results["choices"].items():
            for value in choices[sid]["curve"]:
                missed = value["positive_unfavorable"]+value["positive_abstain"]
                lines.append(f"| {fold} | {number(value['threshold'])} | {number(value['positive_favorable'])} | {number(value['negative_favorable'])} | {number(missed)} | {value['favored_groups']} | {'Sí' if value['admissible'] else 'No'} |")
        lines += [""]
    return "\n".join(lines)


def main():
    result = render(load(OUTPUT / "analysis/results.json"))
    with (OUTPUT / "analysis/tablas-2026-10-03.md").open("x") as stream:
        stream.write(result)
    print("Aggregate tables rendered; no per-case identifiers included")


if __name__ == "__main__":
    main()
