"""Offline exploratory comparison; never imports or changes Rainmapper runtime.

Run with the repository .venv Python. Reads the bounded evidence bundle only.
No credentials or network access are required. No parameters are fitted.
"""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import csv
import gzip
import json

import numpy as np
from scipy.stats import pearsonr, spearmanr
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Div, HoverTool, Range1d, TabPanel, Tabs
from bokeh.plotting import figure
from bokeh.resources import INLINE


ROOT = Path(__file__).resolve().parent
EVIDENCE = json.loads(gzip.decompress((ROOT / "evidence.json.gz").read_bytes()))
LOCAL = {p["name"]: p for p in EVIDENCE["local"]["points"]}
LEVELS = [2, 5, 10, 15, 20, 40, 60, 100]
MODELS = {"smi_legacy_pct": "Depósito simple", "smi_pct": "Extracción regulada"}
COLOURS = {"smi_legacy_pct": "#d97706", "smi_pct": "#007ca8"}
METRICS, ROWS, TABS = [], [], []
SUMMARY = {"coverage": {}, "satellite": {}, "stations": {}}


def correlations(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    a, b = x[mask], y[mask]
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return {"n": len(a), "pearson": None, "spearman": None}
    return {"n": len(a), "pearson": float(pearsonr(a, b).statistic),
            "spearman": float(spearmanr(a, b).statistic)}


def record(name, reference, x, y, model):
    result = {"point": name, "reference": reference, "model": model,
              **correlations(x, y)}
    # Difference on original daily arrays: missing days never become adjacent.
    result["daily_change_r"] = correlations(np.diff(x), np.diff(y))["pearson"]
    for lag in (-2, -1, 1, 2):
        # local date d paired with external date d + lag; diagnostic, not tuning.
        a, b = (x[:-lag], y[lag:]) if lag > 0 else (x[-lag:], y[:lag])
        result[f"r_external_day_{lag:+d}"] = correlations(a, b)["pearson"]
    result["r_first30"] = correlations(x[:30], y[:30])["pearson"]
    result["r_last30"] = correlations(x[30:], y[30:])["pearson"]
    METRICS.append(result)
    return result


def chart(title, ylabel, height=230, x_range=None):
    kwargs = {} if x_range is None else {"x_range": x_range}
    p = figure(title=title, x_axis_type="datetime", height=height,
               sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save", **kwargs)
    p.yaxis.axis_label = ylabel
    p.grid.grid_line_alpha = .2
    return p


def curve(p, dates, values, label, colour, dash="solid"):
    source = ColumnDataSource(dict(date=dates, value=values))
    line = p.line("date", "value", source=source, legend_label=label,
                  line_color=colour, line_width=2, line_dash=dash)
    p.add_tools(HoverTool(renderers=[line], tooltips=[("Serie", label),
                ("Fecha", "@date{%F}"), ("Valor", "@value{0.000}")],
                formatters={"@date": "datetime"}, mode="vline"))
    p.legend.click_policy = "hide"
    p.legend.location = "top_left"
    p.legend.label_text_font_size = "10px"


def model_panel(name):
    point = LOCAL[name]
    weather = point["weather"]
    dates = [datetime.fromisoformat(d) for d in weather["dates"]]
    assert len(dates) == 60 and len(set(dates)) == 60
    assert weather["water_balance"]["history_days"] == 365
    p = chart(name.replace("_", " ") + " · cálculo local", "SMI disponible (%)")
    p.y_range = Range1d(0, 100)
    for key, label in MODELS.items():
        values = weather["water_balance"][key]
        assert all(v is None or 0 <= v <= 100 for v in values)
        curve(p, dates, values, label, COLOURS[key])
    rain = chart("Lluvia · entrada del cálculo", "mm / día", 180, p.x_range)
    rain.vbar(dates, width=65_000_000, top=weather["series"]["rain_mm"],
              color="#3182bd", alpha=.6, legend_label="IDW Rainmapper")
    return point, weather, dates, p, rain


for external in EVIDENCE["copernicus"]["points"]:
    name = external["name"]
    point, weather, dates, p, rain = model_panel(name)
    bands = EVIDENCE["copernicus"]["bands"]
    daily = {}
    for interval in external["response"]["data"]:
        date = interval["interval"]["from"][:10]
        assert date not in daily
        raw = interval["outputs"]["raw"]["bands"]
        for b in raw.values():
            assert b["stats"]["sampleCount"] == 1
        daily[date] = {label: raw[f"B{i}"]["stats"]["mean"] for i, label in enumerate(bands)}
    assert set(daily) == set(weather["dates"])
    outputs = {}
    for t in LEVELS:
        values = []
        for date in weather["dates"]:
            r = daily[date]
            dn, q = r[f"SWI{t:03}"], r[f"QFLAG{t:03}"]
            # Conservative audit threshold, not an official universal QFLAG rule.
            valid = r["dataMask"] == 1 and 0 <= dn <= 200 and 140 <= q <= 200
            values.append(dn * .5 if valid else np.nan)
        outputs[t] = values
    ssf = Counter(str(daily[d]["SSF"]) for d in weather["dates"])
    SUMMARY["coverage"][name] = {"days": len(daily), "valid_t10": int(np.isfinite(outputs[10]).sum()),
                                  "ssf_raw_counts": dict(ssf), "pixel_bbox": external["pixel_bbox"]}
    for i, date in enumerate(weather["dates"]):
        row = {"point": name, "date": date, "rain_idw_mm": weather["series"]["rain_mm"][i],
               "simple_pct": weather["water_balance"]["smi_legacy_pct"][i],
               "regulated_pct": weather["water_balance"]["smi_pct"][i],
               "ssf_raw": daily[date]["SSF"], "data_mask": daily[date]["dataMask"]}
        for t in LEVELS:
            row[f"swi_t{t}"] = outputs[t][i] if np.isfinite(outputs[t][i]) else None
            row[f"qflag_t{t}_raw"] = daily[date][f"QFLAG{t:03}"]
        ROWS.append(row)
    if not any(np.isfinite(outputs[10])):
        continue
    results = []
    for t in LEVELS:
        for key in MODELS:
            results.append(record(name, f"SWI T={t}", weather["water_balance"][key], outputs[t], key))
    SUMMARY["satellite"][name] = results
    satellite = chart("Referencia externa · escala propia, no equivale al SMI disponible", "SWI (%)", 230, p.x_range)
    satellite.y_range = Range1d(0, 100)
    for t, colour in ((2, "#689f38"), (5, "#00897b"), (10, "#7b1fa2")):
        curve(satellite, dates, outputs[t], f"Copernicus T={t}", colour)
    warning = Div(text="<p>Comparación exploratoria. SWI no mide nuestros litros disponibles. "
                       "El indicador SSF=2 necesita aclaración para esta colección; se conservan "
                       "DN, dataMask y QFLAG. Las cifras de correlación no son porcentajes de acierto.</p>")
    TABS.append(TabPanel(title=name, child=column(warning, p, satellite, rain, sizing_mode="stretch_width")))


for external in EVIDENCE["icgc"]["points"]:
    name = external["name"]
    point, weather, dates, p, rain = model_panel(name)
    by_day = defaultdict(list)
    timestamps = set()
    for row in external["rows"]:
        assert row["TmStamp"] not in timestamps
        timestamps.add(row["TmStamp"])
        by_day[row["TmStamp"][:10]].append(row)
    observations = {}
    for channel in ("VWC_005", "VWC_020", "VWC_050"):
        values = []
        for date in weather["dates"]:
            rows = by_day[date]
            vals = [float(r[channel]) for r in rows]
            assert all(0 <= v <= 1 for v in vals)
            # 90% daily coverage. This does not replace instrument quality control.
            values.append(float(np.mean(vals)) if len(vals) >= 44 else np.nan)
        observations[channel] = values
    observed_rain = [sum(float(r["Pluja_Tot"]) for r in by_day[d]) for d in weather["dates"]]
    results = []
    for channel, values in observations.items():
        for key in MODELS:
            results.append(record(name, channel, weather["water_balance"][key], values, key))
    SUMMARY["stations"][name] = {
        "results": results, "half_hour_counts": dict(Counter(len(by_day[d]) for d in weather["dates"])),
        "rain_measured_mm": sum(observed_rain), "rain_idw_mm": sum(weather["series"]["rain_mm"]),
        "coordinates": [point["lat"], point["lon"]], "soil_capacity_mm": point["capacity_mm"],
        "volume_ranges": {k: [min(v), max(v)] for k, v in observations.items()}}
    sensor = chart("Sondas ICGC · contenido volumétrico observado", "m³ / m³", 230, p.x_range)
    for channel, colour in (("VWC_005", "#689f38"), ("VWC_020", "#7b1fa2"), ("VWC_050", "#546e7a")):
        curve(sensor, dates, observations[channel], f"Sonda {int(channel[-3:])} cm", colour)
    curve(rain, dates, observed_rain, "Pluviómetro ICGC", "#c62828")
    for i, date in enumerate(weather["dates"]):
        ROWS.append({"point": name, "date": date, "rain_idw_mm": weather["series"]["rain_mm"][i],
                     "rain_measured_mm": observed_rain[i],
                     "simple_pct": weather["water_balance"]["smi_legacy_pct"][i],
                     "regulated_pct": weather["water_balance"]["smi_pct"][i],
                     **{k: values[i] for k, values in observations.items()},
                     "observations_count": len(by_day[date])})
    warning = Div(text="<p>Cálculo en la ubicación de la estación, no en el setal. "
                       "Media diaria de las sondas, fecha publicada sin conversión de zona horaria "
                       "(zona no confirmada). No se convierte m³/m³ a SMI: faltan capacidad de campo "
                       "y punto de marchitez medidos. No consta control de calidad instrumental en esta descarga.</p>")
    TABS.append(TabPanel(title=name.replace("XMS_", "").replace("_", " "),
                         child=column(warning, p, sensor, rain, sizing_mode="stretch_width")))


for filename, rows in (("series.csv", ROWS), ("metrics.csv", METRICS)):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (ROOT / filename).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
(ROOT / "summary.json").write_text(json.dumps(SUMMARY, ensure_ascii=False, indent=2, allow_nan=False))
header = Div(text="""<h1>Contraste del SMI calculado por Rainmapper</h1>
<p>21 julio – 18 septiembre 2026 · Cálculo propio frente a referencias externas.
Los datos externos se usan únicamente para esta auditoría. Sin ajuste de parámetros ni integración en el mapa.</p>
<p>Azul: extracción regulada. Naranja: depósito simple. Los paneles externos mantienen su propia escala.
Usa las pestañas, el zoom y las leyendas para explorar. Correlación de evolución no implica exactitud de litros.</p>""")
layout = column(header, Tabs(tabs=TABS, sizing_mode="stretch_width"), sizing_mode="stretch_width")
(ROOT / "comparison.html").write_text(file_html(layout, INLINE, "Rainmapper · contraste SMI"))
print("Written offline comparison, 420 daily rows and", len(METRICS), "metric rows.")
for name in ("Vallcebre", "Olvan", "XMS_Batlliu_de_Sort", "XMS_Cami_dels_Nerets"):
    ref = "SWI T=10" if not name.startswith("XMS") else "VWC_020"
    print(name, [(m["model"], round(m["pearson"], 3)) for m in METRICS
                 if m["point"] == name and m["reference"] == ref])
