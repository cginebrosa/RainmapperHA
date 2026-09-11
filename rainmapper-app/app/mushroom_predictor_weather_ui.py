"""Small, read-only weather charts derived from the selected prediction inputs.

No weather lookup, inference or extra persisted payload is needed to render them.
"""

from __future__ import annotations

import html
import math
import re
from datetime import date, timedelta
from typing import Any, Callable


CHANNELS = ("rain_mm", "temp_min_c", "temp_max_c", "humidity_min_pct", "humidity_max_pct")
RAIN_BANDS = (
    ("rain_cutoff_0_3d_mm", 0, 2),
    ("rain_cutoff_4_7d_mm", 3, 6),
    ("rain_cutoff_8_14d_mm", 7, 13),
    ("rain_cutoff_15_21d_mm", 14, 20),
    ("rain_cutoff_22_30d_mm", 21, 29),
    ("rain_cutoff_31_60d_mm", 30, 59),
    ("rain_cutoff_61_90d_mm", 60, 89),
)


def _number(value: object, *, rain: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) and (not rain or value >= 0) else None


def weather_inputs(result: dict[str, Any], ref: dict[str, Any], target: date) -> dict[str, Any] | None:
    """Use only the selected result; never a competing model or current weather."""
    features = result.get("features_used") or {}
    metadata = result.get("metadata") or {}
    if not isinstance(features, dict) or not isinstance(metadata, dict):
        return None
    horizon = ref.get("horizon_days", result.get("horizon_days"))
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 7:
        return None
    cutoff = target - timedelta(days=horizon)
    # Old persisted results lack cutoff metadata; their explicit horizon is sufficient.
    if metadata.get("cutoff_date") and metadata["cutoff_date"] != cutoff.isoformat():
        return None
    lags = [int(match[1]) for key in features
            if (match := re.fullmatch(r"rain_mm__lag_(\d{3})", key))]
    if lags:
        count = max(lags) + 1
        profile = re.fullmatch(r"(?:smooth|raw)_window_(\d+)d_plus_physical_state", str(ref.get("profile_id", "")))
        if profile:
            count = max(count, int(profile[1]))
        if not 1 <= count <= 365:
            return None
        rows = []
        for lag in reversed(range(count)):
            row = {channel: _number(features.get(f"{channel}__lag_{lag:03d}"), rain=channel == "rain_mm")
                   for channel in CHANNELS}
            row["date"] = cutoff - timedelta(days=lag)
            rows.append(row)
        return {"kind": "daily", "start": rows[0]["date"], "end": cutoff, "rows": rows,
                "channels": {channel for channel in CHANNELS
                             if any(key.startswith(channel + "__lag_") for key in features)}}
    # Older versions expose period aggregates. Do not reconstruct fictitious days.
    bands = [{"start": cutoff - timedelta(days=oldest), "end": cutoff - timedelta(days=youngest),
              "rain_mm": _number(features[key], rain=True)}
             for key, youngest, oldest in reversed(RAIN_BANDS) if key in features]
    if bands:
        return {"kind": "bands", "start": bands[0]["start"], "end": cutoff, "rows": bands,
                "features": features}
    return None


def _date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def render_weather(comparison: dict[str, Any], target: date, label: Callable[[str], str]) -> str:
    """Render only actual winners, keeping different temporal scenarios separate."""
    def text(key: str, **values: object) -> str:
        return html.escape(label("ui.predictor_weather_" + key).format(**values))

    sections = []
    for winner in comparison.get("selected_winners") or []:
        if not isinstance(winner, dict):
            continue
        result = comparison.get(winner.get("result_key"))
        ref = winner.get("model_ref") or {}
        if not isinstance(result, dict) or not isinstance(ref, dict):
            continue
        data = weather_inputs(result, ref, target)
        if data is None:
            continue
        rows = data["rows"]
        daily = data["kind"] == "daily"
        values = [row["rain_mm"] for row in rows if row["rain_mm"] is not None]
        missing = len(rows) - len(values)
        total = f"{sum(values):.1f} mm" if values else "—"
        period = f'{_date(data["start"])} – {_date(data["end"])}'
        summary = text("total" if daily and not missing else "available_total", amount=total)
        # Ignore sub-hundredth traces in the last-rain summary only; preserve model inputs.
        latest = next((row for row in reversed(rows) if (row["rain_mm"] or 0) >= 0.01), None)
        last_html = ""
        if daily:
            last_html = (text("latest", date=_date(latest["date"]), amount=f'{latest["rain_mm"]:.2f}')
                         if latest else text("no_rain" if not missing else "no_rain_data"))
        chart = _rain_chart(rows, daily, text)
        if daily:
            for name, low, high, unit in (("temperature", "temp_min_c", "temp_max_c", "°C"),
                                           ("humidity", "humidity_min_pct", "humidity_max_pct", "%")):
                if {low, high} & data["channels"]:
                    chart += _line_chart(rows, name, low, high, unit, text)
        else:
            chart += _aggregate_weather(data["features"], data["end"], text)
        notes = text("daily_note" if daily else "bands_note")
        if missing:
            notes += " " + text("missing", count=missing)
        heading = text("title") if daily else text("bands_title")
        sections.append(
            '<section class="pred-weather">'
            f'<div class="pred-weather-heading">{heading}: '
            f'<span class="pred-weather-period">{period}</span></div>'
            f'<div class="pred-weather-summary"><strong>{summary}</strong><span>{last_html}</span></div>'
            '<details class="pred-weather-details">'
            f'<summary title="{notes}" aria-label="{text("expand")}. {notes}">'
            f'<span class="pred-tooltip">{text("expand")} '
            '<span class="pred-tooltip-icon" aria-hidden="true">ⓘ</span></span></summary>'
            f'{chart}'
            '</details></section>'
        )
    return "".join(sections)


def _aggregate_weather(features: dict[str, Any], cutoff: date, text: Callable[..., str]) -> str:
    """Present legacy means/extremes as aggregates, never as daily measurements."""
    windows = {"0_3d": (0, 2), "4_7d": (3, 6), "7d": (0, 6),
               "8_14d": (7, 13), "15_21d": (14, 20), "22_30d": (21, 29)}
    tables = []
    for prefix, name, unit in (("temp", "temperature", "°C"), ("humidity", "humidity", "%")):
        rows = []
        for key, value in features.items():
            match = re.fullmatch(prefix + r"_(max_mean|min_mean|max|min|mean)_cutoff_(.+)_(?:c|pct)", key)
            if match and match[2] in windows:
                young, old = windows[match[2]]
                period = f'{_date(cutoff - timedelta(days=old))} – {_date(cutoff - timedelta(days=young))}'
                measure = text({"max": "maximum", "min": "minimum", "mean": "mean",
                                "max_mean": "mean_max", "min_mean": "mean_min"}[match[1]])
            elif key == f"{prefix}_mean_after_significant_rain_{'c' if prefix == 'temp' else 'pct'}":
                period, measure = text("after_event"), text("mean")
            else:
                continue
            number = _number(value)
            amount = f'{number:.1f} {unit}' if number is not None else text("missing_value")
            rows.append(f'<tr><td>{period}</td><td>{measure}</td><td>{amount}</td></tr>')
        if rows:
            tables.append('<div class="pred-weather-chart pred-weather-table">'
                          f'<strong>{text(name)}</strong><div><table><thead><tr>'
                          f'<th>{text("date")}</th><th>{text("measure")}</th><th>{unit}</th></tr></thead>'
                          f'<tbody>{"".join(rows)}</tbody></table></div></div>')
    return "".join(tables)


def _rain_chart(rows: list[dict[str, Any]], daily: bool, text: Callable[..., str]) -> str:
    maximum = max((row["rain_mm"] or 0 for row in rows), default=0)
    top = max(1, math.ceil(maximum))
    bars = []
    table = []
    for row in rows:
        day = _date(row["date"]) if daily else f'{_date(row["start"])} – {_date(row["end"])}'
        value = row["rain_mm"]
        amount = f"{value:.2f} mm" if value is not None else text("missing_value")
        detail = html.escape(day) + " · " + amount
        height = 100 * (value or 0) / top
        state = "missing" if value is None else "wet" if value > 0 else "dry"
        bars.append(f'<button type="button" class="pred-weather-bar {state}" data-weather-label="{detail}" '
                    f'aria-label="{detail}"><span style="height:{height:.4f}%"></span></button>')
        table.append(f'<tr><td>{day}</td><td>{amount}</td></tr>')
    start = rows[0]["date"] if daily else rows[0]["start"]
    end = rows[-1]["date"] if daily else rows[-1]["end"]
    width = len(rows) * 8
    return (
        '<div class="pred-weather-chart">'
        f'<div class="pred-weather-chart-heading"><strong>{text("rain")}</strong><span>0 – {top} mm</span></div>'
        f'<div class="pred-weather-scroll"><div style="min-width:{width}px">'
        f'<div class="pred-weather-bars">{"".join(bars)}</div>'
        f'<div class="pred-weather-axis"><span>{_date(start)}</span><span>{_date(end)}</span></div>'
        '</div></div>'
        '<div class="pred-weather-readout" aria-live="polite" hidden></div>'
        f'<details class="pred-weather-table"><summary>{text("values")}</summary>'
        f'<div><table><thead><tr><th>{text("date")}</th><th>mm</th></tr></thead>'
        f'<tbody>{"".join(table)}</tbody></table></div></details></div>'
    )


def _line_chart(rows: list[dict[str, Any]], name: str, low: str, high: str, unit: str,
                text: Callable[..., str]) -> str:
    values = [row[key] for row in rows for key in (low, high) if row[key] is not None]
    if not values:
        return f'<p>{text(name)}: {text("missing_value")}</p>'
    bottom, top = math.floor(min(values)), math.ceil(max(values))
    if bottom == top:
        top += 1
    paths = []
    # Break the line at missing readings; no interpolation across unknown days.
    for key, css in ((low, "minimum"), (high, "maximum")):
        points = []
        for index, row in enumerate(rows):
            value = row[key]
            if value is None:
                if points:
                    paths.append(f'<polyline class="{css}" points="{" ".join(points)}"/>')
                    points = []
                continue
            x = 8 + index * 744 / max(1, len(rows) - 1)
            y = 130 - (value - bottom) * 118 / (top - bottom)
            points.append(f"{x:.2f},{y:.2f}")
            paths.append(f'<circle class="{css}" cx="{x:.2f}" cy="{y:.2f}" r="2"/>')
        if points:
            paths.append(f'<polyline class="{css}" points="{" ".join(points)}"/>')
    hits = []
    table = []
    for index, row in enumerate(rows):
        lo = f'{row[low]:.1f}' if row[low] is not None else '—'
        hi = f'{row[high]:.1f}' if row[high] is not None else '—'
        detail = text("range", date=_date(row["date"]), low=lo, high=hi, unit=unit)
        hits.append(f'<button type="button" data-weather-label="{detail}" aria-label="{detail}"></button>')
        table.append(f'<tr><td>{_date(row["date"])}</td><td>{lo}</td><td>{hi}</td></tr>')
    return (
        '<div class="pred-weather-chart">'
        f'<div class="pred-weather-chart-heading"><strong>{text(name)}</strong><span>{bottom} – {top} {unit}</span></div>'
        '<div class="pred-weather-scroll">'
        f'<div style="min-width:{len(rows)*8}px"><div class="pred-weather-lines">'
        f'<svg viewBox="0 0 760 145" preserveAspectRatio="none" aria-hidden="true">{"".join(paths)}</svg>'
        f'<div class="pred-weather-hitareas">{"".join(hits)}</div></div>'
        f'<div class="pred-weather-axis pred-weather-axis-with-legend"><span>{_date(rows[0]["date"])}</span>'
        f'<span class="pred-weather-legend"><span class="minimum">{text("minimum")}</span><span class="maximum">{text("maximum")}</span></span>'
        f'<span>{_date(rows[-1]["date"])}</span></div>'
        '</div></div>'
        '<div class="pred-weather-readout" aria-live="polite" hidden></div>'
        f'<details class="pred-weather-table"><summary>{text("values")}</summary><div><table>'
        f'<thead><tr><th>{text("date")}</th><th>{text("minimum")} {unit}</th><th>{text("maximum")} {unit}</th></tr></thead>'
        f'<tbody>{"".join(table)}</tbody></table></div></details></div>'
    )


CSS = """
.pred-weather { margin-top:1.1rem; padding:1rem 1.15rem; border:1px solid #344952; border-radius:10px; background:#142127; }
.pred-weather-heading { color:#dfe8ed; font-weight:700; }
.pred-weather-period { color:#b3c3cb; font-weight:400; font-variant-numeric:tabular-nums; }
.pred-weather-summary { display:flex; flex-wrap:wrap; gap:.5rem 1.5rem; margin:.65rem 0; color:#afc3cb; }
.pred-weather-summary strong { color:#66d6b5; }
.pred-weather summary { cursor:pointer; color:#c5ddd9; padding:.4rem 0; }
.pred-weather-chart { position:relative; margin-top:1.2rem; }
.pred-weather-chart-heading,.pred-weather-axis { display:flex; justify-content:space-between; gap:1rem; color:#a9bac3; }
.pred-weather-chart-heading strong { color:#71ddbc; }
.pred-weather-scroll { overflow-x:auto; padding-top:.5rem; }
.pred-weather-bars { height:140px; display:flex; gap:3px; align-items:stretch; border-bottom:1px solid #62737a; background:repeating-linear-gradient(to top,transparent 0,transparent 34px,#ffffff09 34px,#ffffff09 35px); }
.pred-weather-bar { flex:1; min-width:0; position:relative; display:flex; align-items:flex-end; padding:0; border:0; border-radius:0; background:transparent; cursor:crosshair; }
.pred-weather-bar span { width:100%; background:#3bc9a0; border-radius:2px 2px 0 0; }
.pred-weather-bar.wet span { min-height:1px; }
.pred-weather-bar.dry span { height:2px!important; background:#52666d; }
.pred-weather-bar.missing { background:repeating-linear-gradient(135deg,transparent,transparent 5px,#8d9ba32b 5px,#8d9ba32b 7px); }
.pred-weather-bar:hover,.pred-weather-bar:focus-visible { background:#ffffff14; outline:1px solid #89e8cc; outline-offset:0; }
.pred-weather-axis { font-size:.8rem; padding-top:.4rem; }
.pred-weather-readout { position:absolute; top:2rem; z-index:4; max-width:calc(100% - 16px); box-sizing:border-box; padding:.45rem .65rem; border:1px solid #628b83; border-radius:6px; background:#091a20f2; color:#b6ecd9; font-size:.85rem; line-height:1.4; box-shadow:0 3px 10px #0005; pointer-events:none; }
.pred-weather-axis-with-legend { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:.5rem; }
.pred-weather-axis-with-legend>span:last-child { justify-self:end; }
.pred-weather-legend { display:flex; gap:.6rem; color:#a9bac3; font-size:.8rem; }
.pred-weather-lines { height:145px; position:relative; }
.pred-weather-lines svg { width:100%; height:145px; }
.pred-weather-lines polyline { fill:none; stroke-width:2; vector-effect:non-scaling-stroke; }
.pred-weather-lines .minimum { stroke:#55c9ef; fill:#55c9ef; }
.pred-weather-lines .maximum { stroke:#ee8ea6; fill:#ee8ea6; }
.pred-weather-lines polyline.minimum,.pred-weather-lines polyline.maximum { fill:none; }
.pred-weather-legend .minimum { color:#55c9ef; }
.pred-weather-legend .maximum { color:#ee8ea6; }
.pred-weather-hitareas { position:absolute; inset:0; display:flex; }
.pred-weather-hitareas button { flex:1; min-width:0; padding:0; border:0; border-radius:0; background:transparent; cursor:crosshair; }
.pred-weather-hitareas button:hover,.pred-weather-hitareas button:focus-visible { background:#ffffff10; outline:1px solid #89e8cc; outline-offset:-1px; }
.pred-weather-table { margin-top:.45rem; font-size:.85rem; }
.pred-weather-table>div { max-height:230px; overflow:auto; }
.pred-weather-table table { width:100%; border-collapse:collapse; text-align:left; }
.pred-weather-table th,.pred-weather-table td { padding:.3rem .5rem; border-bottom:1px solid #ffffff12; color:#c4d2d8; }
"""

SCRIPT = """<script>
(() => {
  const stateKey = 'rainmapper.predictor.observedWeatherOpen';
  try {
    const saved = sessionStorage.getItem(stateKey);
    if (saved !== null) {
      document.querySelectorAll('.pred-weather-details').forEach(details => {
        details.open = saved === 'true';
      });
    }
  } catch (_) { /* Charts also work when browser storage is unavailable. */ }
  // Weekly cards use document.open/write: the window survives, its document
  // listeners do not. Bind once per rendered root, not once per window.
  const root = document.documentElement;
  if (root.dataset.predictionWeatherBound === 'true') return;
  root.dataset.predictionWeatherBound = 'true';
  document.addEventListener('toggle', event => {
    if (!event.target.matches('.pred-weather-details')) return;
    try { sessionStorage.setItem(stateKey, String(event.target.open)); } catch (_) {}
  }, true);
  const hide = () => document.querySelectorAll('.pred-weather-readout:not([hidden])').forEach(output => {
    output.hidden = true;
  });
  const show = (event) => {
    const button = event.target.closest('[data-weather-label]');
    if (!button) {
      if (event.type === 'click' || event.type === 'focusin') hide();
      return;
    }
    const chart = button.closest('.pred-weather-chart');
    const output = chart && chart.querySelector('.pred-weather-readout');
    if (output) {
      hide();
      output.textContent = button.dataset.weatherLabel;
      output.style.left = '8px';
      output.hidden = false;
      const bounds = chart.getBoundingClientRect();
      const target = button.getBoundingClientRect();
      const width = output.getBoundingClientRect().width;
      const left = target.left + target.width / 2 - bounds.left - width / 2;
      output.style.left = Math.max(8, Math.min(left, bounds.width - width - 8)) + 'px';
    }
  };
  ['pointerover', 'focusin', 'click'].forEach(type => document.addEventListener(type, show));
  ['pointerout', 'focusout'].forEach(type => document.addEventListener(type, event => {
    const button = event.target.closest('[data-weather-label]');
    if (button && !button.contains(event.relatedTarget)) hide();
  }));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
  document.addEventListener('scroll', hide, true);
})();
</script>"""
