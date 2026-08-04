"""Server-rendered Predictor UI for the mushroom ML v0 model."""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from rainmapper_core import mushroom_paths
from rainmapper_core.mushroom_ml_predictor import MushroomMLPredictor

import mushroom_profiles_ui


# Module-level predictor cache — lazy-loaded, survives across requests
_predictor_cache: dict[str, MushroomMLPredictor] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lbl(key: str) -> str:
    return mushroom_profiles_ui.ui_label(key)


def _get_predictor(species_id: str) -> MushroomMLPredictor:
    if species_id not in _predictor_cache:
        _predictor_cache[species_id] = MushroomMLPredictor(species_id)
    return _predictor_cache[species_id]


def trained_species_ids() -> list[str]:
    """Return species IDs that have a trained .joblib model, sorted."""
    models_dir = mushroom_paths.mushroom_ml_models_dir()
    if not models_dir.exists():
        return []
    return sorted(
        p.stem.removeprefix("mushroom_ml_v0_")
        for p in models_dir.glob("mushroom_ml_v0_*.joblib")
    )


def _species_name(species_id: str, profiles_payload: dict[str, Any]) -> str:
    profiles = profiles_payload.get("species_profiles", []) if isinstance(profiles_payload, dict) else []
    for p in profiles:
        if not isinstance(p, dict) or p.get("species_id") != species_id:
            continue
        names = p.get("common_names")
        if isinstance(names, dict):
            name = names.get("es") or names.get("en") or names.get("ca")
            if name:
                return name
        if isinstance(names, list) and names:
            return names[0]
        return p.get("scientific_name") or species_id
    return species_id


def _area_name(area_id: str, known_sites_payload: dict[str, Any]) -> str:
    areas = known_sites_payload.get("areas", []) if isinstance(known_sites_payload, dict) else []
    for a in areas:
        if isinstance(a, dict) and a.get("area_id") == area_id:
            return a.get("name") or area_id
    return area_id


def _status_dot(label: str) -> str:
    if label == "favorable":
        return "🟢"
    if label == "uncertain":
        return "🟡"
    return "🔴"


def _pct(prob: float | None) -> str:
    if prob is None:
        return "—"
    return f"{round(prob * 100)}%"


def _status_cls(label: str) -> str:
    if label == "favorable":
        return "pred-green"
    if label == "uncertain":
        return "pred-yellow"
    return "pred-red"


def _url(view: str = "recommender", species: str = "", area: str = "", target_date: date | None = None, **extra: str) -> str:
    params: dict[str, str] = {"view": view}
    if species:
        params["species"] = species
    if area:
        params["area"] = area
    if target_date:
        params["date"] = target_date.isoformat()
    params.update({k: v for k, v in extra.items() if v})
    return "?" + urlencode(params)


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------

def _render_tabs(
    view: str,
    species: str,
    target_date: date,
) -> str:
    def tab(key: str, v: str, extra_params: str = "") -> str:
        href = _url(v, species, target_date=target_date)
        cls = "pred-tab pred-tab-active" if view == v else "pred-tab"
        return f'<a class="{cls}" href="{html.escape(href)}">{html.escape(_lbl(key))}</a>'

    return f"""
<nav class="pred-tabs">
  {tab("ui.predictor_tab_recommender", "recommender")}
  {tab("ui.predictor_tab_week", "week")}
  {tab("ui.predictor_tab_query", "query")}
  {tab("ui.predictor_tab_history", "history")}
</nav>
"""


# ---------------------------------------------------------------------------
# Day strip (shared between recommender and week)
# ---------------------------------------------------------------------------

def _render_day_strip(target_date: date, view: str, species: str) -> str:
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    cells = []
    for d in days:
        href = _url(view, species, target_date=d)
        is_active = d == target_date
        cls = "pred-day pred-day-active" if is_active else "pred-day"
        day_name = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
        label_text = f"{day_name}<br><strong>{d.day}/{d.month}</strong>"
        cells.append(
            f'<a class="{cls}" href="{html.escape(href)}">'
            f'{label_text}'
            f'</a>'
        )
    return '<div class="pred-day-strip">' + "".join(cells) + "</div>"


# ---------------------------------------------------------------------------
# Recommender view
# ---------------------------------------------------------------------------

def _render_recommender(
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    today = date.today()
    day_strip = _render_day_strip(target_date, "recommender", "")

    all_results = []
    errors = []
    for species_id in trained:
        try:
            predictor = _get_predictor(species_id)
            results = predictor.rank_areas(target_date, only_observed=True)
            for r in results:
                if r.ensemble_probability is not None:
                    all_results.append((r, species_id))
        except FileNotFoundError:
            pass
        except Exception as exc:
            errors.append(f"{species_id}: {html.escape(str(exc))}")

    all_results.sort(key=lambda t: t[0].ensemble_probability or 0, reverse=True)

    date_label = (
        "Hoy" if target_date == today
        else "Mañana" if target_date == today + timedelta(days=1)
        else target_date.strftime("%-d de %B")
    )

    if not all_results:
        no_data = f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>'
        error_block = _render_errors(errors)
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_recommender"))} — {html.escape(date_label)}</h2>
  {day_strip}
  {error_block}
  {no_data}
</section>
"""

    # Best bet card
    best_r, best_species = all_results[0]
    best_species_name = _species_name(best_species, profiles_payload)
    best_area_name = _area_name(best_r.area_id, known_sites_payload)
    best_card = f"""
<div class="pred-best-card {_status_cls(best_r.label)}">
  <div class="pred-best-badge">{html.escape(_lbl("ui.predictor_best_bet"))}</div>
  <div class="pred-best-name">{_status_dot(best_r.label)} {html.escape(best_species_name)}</div>
  <div class="pred-best-area">{html.escape(best_area_name)}</div>
  <div class="pred-best-prob">{_pct(best_r.ensemble_probability)}</div>
  <div class="pred-best-hint">{html.escape(_label_hint(best_r.label))}</div>
</div>
"""

    # Ranked list
    rows_html = ""
    for r, sp_id in all_results[:15]:
        sp_name = _species_name(sp_id, profiles_payload)
        area_n = _area_name(r.area_id, known_sites_payload)
        href = _url("query", sp_id, r.area_id, target_date)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(r.label)}" href="{html.escape(href)}">
  <span class="pred-rank-dot">{_status_dot(r.label)}</span>
  <span class="pred-rank-species">{html.escape(sp_name)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{_pct(r.ensemble_probability)}</span>
</a>
"""

    error_block = _render_errors(errors)
    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_recommender"))} — {html.escape(date_label)}</h2>
  {day_strip}
  {error_block}
  {best_card}
  <h3>{html.escape(_lbl("ui.predictor_all_areas"))}</h3>
  <div class="pred-rank-list">
    <div class="pred-rank-header">
      <span></span>
      <span>{html.escape(_lbl("ui.species"))}</span>
      <span>{html.escape(_lbl("ui.known_site_area"))}</span>
      <span>{html.escape(_lbl("ui.predictor_probability"))}</span>
    </div>
    {rows_html}
  </div>
</section>
"""


def _label_hint(label: str) -> str:
    if label == "favorable":
        return _lbl("ui.predictor_hint_favorable")
    if label == "uncertain":
        return _lbl("ui.predictor_hint_uncertain")
    return _lbl("ui.predictor_hint_unfavorable")


# ---------------------------------------------------------------------------
# Week view
# ---------------------------------------------------------------------------

def _render_week(
    species: str,
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    # Species chips
    chips = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        href = _url("week", sp_id, target_date=target_date)
        cls = "pred-chip pred-chip-active" if sp_id == species else "pred-chip"
        chips += f'<a class="{cls}" href="{html.escape(href)}">{html.escape(sp_name)}</a>'

    try:
        predictor = _get_predictor(species)
        area_ids = predictor.areas_with_species_observations()
    except FileNotFoundError:
        area_ids = []
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(str(exc))}</div>'

    if not area_ids:
        return f"""
<section class="pred-section">
  <div class="pred-chips">{chips}</div>
  <div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>
</section>
"""

    sp_name = _species_name(species, profiles_payload)

    # Day header
    day_headers = ""
    for d in days:
        day_name = ["L", "M", "X", "J", "V", "S", "D"][d.weekday()]
        is_today = d == today
        day_headers += f'<th class="{"pred-today-col" if is_today else ""}">{day_name}<br><small>{d.day}/{d.month}</small></th>'

    # Grid rows
    rows_html = ""
    for area_id in sorted(area_ids):
        area_n = _area_name(area_id, known_sites_payload)
        row_cells = f'<td class="pred-area-cell">{html.escape(area_n)}</td>'
        for d in days:
            try:
                predictor = _get_predictor(species)
                r = predictor.predict(area_id, d)
                cell_href = _url("query", species, area_id, d)
                row_cells += (
                    f'<td class="pred-cell {_status_cls(r.label)}">'
                    f'<a href="{html.escape(cell_href)}">'
                    f'{_status_dot(r.label)} {_pct(r.ensemble_probability)}'
                    f'</a></td>'
                )
            except Exception:
                row_cells += '<td class="pred-cell">—</td>'
        rows_html += f"<tr>{row_cells}</tr>"

    return f"""
<section class="pred-section">
  <div class="pred-chips">{chips}</div>
  <h2>{html.escape(sp_name)}</h2>
  <div class="pred-table-scroll">
    <table class="pred-week-table">
      <thead>
        <tr>
          <th>{html.escape(_lbl("ui.known_site_area"))}</th>
          {day_headers}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
  <p class="pred-hint-legend">
    🟢 {html.escape(_lbl("ui.predictor_favorable"))} &nbsp;
    🟡 {html.escape(_lbl("ui.predictor_uncertain"))} &nbsp;
    🔴 {html.escape(_lbl("ui.predictor_unfavorable"))}
  </p>
</section>
"""


# ---------------------------------------------------------------------------
# Query view
# ---------------------------------------------------------------------------

def _render_query(
    species: str,
    area: str,
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    # Area options for selected species
    area_options_html = f'<option value="">{html.escape(_lbl("ui.predictor_all_areas_option"))}</option>'
    try:
        predictor = _get_predictor(species)
        area_ids = predictor.areas_with_species_observations()
        areas = known_sites_payload.get("areas", []) if isinstance(known_sites_payload, dict) else []
        for a_id in sorted(area_ids):
            a_name = _area_name(a_id, known_sites_payload)
            sel = ' selected' if a_id == area else ''
            area_options_html += f'<option value="{html.escape(a_id)}"{sel}>{html.escape(a_name)}</option>'
    except Exception:
        pass

    # Species options
    species_options_html = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        sel = ' selected' if sp_id == species else ''
        species_options_html += f'<option value="{html.escape(sp_id)}"{sel}>{html.escape(sp_name)}</option>'

    form_html = f"""
<form class="pred-form" method="get" action="">
  <input type="hidden" name="view" value="query">
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.species"))}</label>
    <select name="species" onchange="this.form.submit()">{species_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.known_site_area"))}</label>
    <select name="area" onchange="this.form.submit()">{area_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.date_short"))}</label>
    <input type="date" name="date" value="{html.escape(target_date.isoformat())}">
  </div>
  <button type="submit" class="primary">{html.escape(_lbl("ui.predictor_query_submit"))}</button>
</form>
"""

    result_html = ""
    if area:
        result_html = _render_query_result(species, area, target_date, profiles_payload, known_sites_payload)
    elif species:
        # Show all areas for the species
        result_html = _render_query_all_areas(species, target_date, profiles_payload, known_sites_payload)

    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_query"))}</h2>
  {form_html}
  {result_html}
</section>
"""


def _render_query_result(
    species: str,
    area: str,
    target_date: date,
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    try:
        predictor = _get_predictor(species)
        r = predictor.predict(area, target_date)
    except FileNotFoundError as exc:
        return f'<div class="pred-error">{html.escape(str(exc))}</div>'
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(str(exc))}</div>'

    sp_name = _species_name(species, profiles_payload)
    area_n = _area_name(area, known_sites_payload)

    station_info = ""
    if r.weather_station_code:
        dist = f"{r.weather_station_distance_km:.1f} km" if r.weather_station_distance_km is not None else "?"
        cov = f"{r.weather_coverage_days}d" if r.weather_coverage_days is not None else "?"
        station_info = f"""
<div class="pred-station-info">
  <span>📡 {html.escape(r.weather_station_code)}</span>
  <span>{html.escape(dist)}</span>
  <span>{html.escape(_lbl("ui.predictor_coverage"))}: {html.escape(cov)}</span>
</div>
"""

    gaps_html = ""
    if r.feature_gaps:
        gaps = ", ".join(html.escape(g) for g in r.feature_gaps[:5])
        if len(r.feature_gaps) > 5:
            gaps += f", +{len(r.feature_gaps) - 5}"
        gaps_html = f'<div class="pred-gaps"><small>⚠️ {gaps}</small></div>'

    # 7-day strip for this area
    week_cells = ""
    try:
        predictor_w = _get_predictor(species)
        week_results = predictor_w.week_window(area, date.today())
        for wr in week_results:
            is_active = wr.target_date == target_date
            day_name = ["L", "M", "X", "J", "V", "S", "D"][wr.target_date.weekday()]
            href = _url("query", species, area, wr.target_date)
            cls = "pred-week-cell pred-week-active" if is_active else "pred-week-cell"
            week_cells += f"""
<a class="{cls} {_status_cls(wr.label)}" href="{html.escape(href)}">
  <small>{day_name} {wr.target_date.day}/{wr.target_date.month}</small>
  <span>{_status_dot(wr.label)}</span>
  <small>{_pct(wr.ensemble_probability)}</small>
</a>
"""
    except Exception:
        pass

    week_strip = f'<div class="pred-week-strip">{week_cells}</div>' if week_cells else ""

    # Feature bars for key indicators
    feature_bars = _render_feature_bars(r.features_used)

    return f"""
<div class="pred-result-card {_status_cls(r.label)}">
  <div class="pred-result-header">
    <span class="pred-result-dot">{_status_dot(r.label)}</span>
    <span class="pred-result-species">{html.escape(sp_name)}</span>
    <span class="pred-result-area">{html.escape(area_n)}</span>
    <span class="pred-result-date">{html.escape(target_date.strftime("%-d %b %Y"))}</span>
  </div>
  <div class="pred-result-prob">{_pct(r.ensemble_probability)}</div>
  <div class="pred-result-label">{html.escape(_label_text(r.label))}</div>
  <div class="pred-prob-detail">
    <span>LR: {_pct(r.lr_probability)}</span>
    <span>RF: {_pct(r.rf_probability)}</span>
  </div>
  {station_info}
  {gaps_html}
</div>
{week_strip}
{feature_bars}
"""


def _render_query_all_areas(
    species: str,
    target_date: date,
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    try:
        predictor = _get_predictor(species)
        results = predictor.rank_areas(target_date, only_observed=True)
    except FileNotFoundError as exc:
        return f'<div class="pred-error">{html.escape(str(exc))}</div>'
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(str(exc))}</div>'

    if not results:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>'

    sp_name = _species_name(species, profiles_payload)
    rows_html = ""
    for r in results:
        area_n = _area_name(r.area_id, known_sites_payload)
        href = _url("query", species, r.area_id, target_date)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(r.label)}" href="{html.escape(href)}">
  <span class="pred-rank-dot">{_status_dot(r.label)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{_pct(r.ensemble_probability)}</span>
</a>
"""

    return f"""
<div class="pred-rank-list pred-rank-compact">
  <h3>{html.escape(sp_name)} — {html.escape(target_date.strftime("%-d %b %Y"))}</h3>
  {rows_html}
</div>
"""


def _render_feature_bars(features: dict[str, Any]) -> str:
    if not features:
        return ""

    shown = [
        ("rain_1d_mm", "Lluvia 1d", 50),
        ("rain_7d_mm", "Lluvia 7d", 150),
        ("rain_15d_mm", "Lluvia 15d", 250),
        ("temp_max_c", "Tmax", 40),
        ("temp_min_c", "Tmin", 30),
        ("humidity_max_7d_pct", "Humedad max 7d", 100),
        ("humidity_min_7d_pct", "Humedad min 7d", 100),
    ]

    bars_html = ""
    for key, label_text, max_val in shown:
        val = features.get(key)
        if val is None:
            continue
        pct = min(100, round(float(val) / max_val * 100))
        unit = "%" if "pct" in key else ("°C" if "temp" in key else "mm")
        bars_html += f"""
<div class="pred-feat-row">
  <span class="pred-feat-label">{html.escape(label_text)}</span>
  <div class="pred-feat-bar-bg">
    <div class="pred-feat-bar" style="width:{pct}%"></div>
  </div>
  <span class="pred-feat-val">{val:.1f}{html.escape(unit)}</span>
</div>
"""

    if not bars_html:
        return ""

    return f"""
<div class="pred-features">
  <h4>{html.escape(_lbl("ui.predictor_weather_factors"))}</h4>
  {bars_html}
</div>
"""


def _label_text(label: str) -> str:
    if label == "favorable":
        return _lbl("ui.predictor_favorable")
    if label == "uncertain":
        return _lbl("ui.predictor_uncertain")
    return _lbl("ui.predictor_unfavorable")


def _actual_text(actual: str) -> str:
    if actual == "favorable":
        return _lbl("ui.predictor_favorable")
    if actual == "unfavorable":
        return _lbl("ui.predictor_actual_unfavorable")
    return "—"


# ---------------------------------------------------------------------------
# History view
# ---------------------------------------------------------------------------

def _render_history(
    species: str,
    area: str,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
    filter_mode: str = "",
) -> str:
    species_options_html = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        sel = ' selected' if sp_id == species else ''
        species_options_html += f'<option value="{html.escape(sp_id)}"{sel}>{html.escape(sp_name)}</option>'

    form_html = f"""
<form class="pred-form" method="get" action="">
  <input type="hidden" name="view" value="history">
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.species"))}</label>
    <select name="species" onchange="this.form.submit()">{species_options_html}</select>
  </div>
  <button type="submit" class="primary">{html.escape(_lbl("ui.search"))}</button>
</form>
"""

    try:
        predictor = _get_predictor(species)
        records = predictor.backtest()
    except FileNotFoundError as exc:
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))}</h2>
  {form_html}
  <div class="pred-error">{html.escape(str(exc))}</div>
</section>
"""
    except Exception as exc:
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))}</h2>
  {form_html}
  <div class="pred-error"><strong>Error:</strong> {html.escape(str(exc))}</div>
</section>
"""

    sp_name = _species_name(species, profiles_payload)
    stats_html = _render_backtest_stats(records, species, filter_mode)
    table_html = _render_backtest_table(records, known_sites_payload, filter_mode)

    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))} — {html.escape(sp_name)}</h2>
  {form_html}
  {stats_html}
  {table_html}
</section>
"""


def _render_backtest_stats(records: list[dict[str, Any]], species: str, filter_mode: str) -> str:
    if not records:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_history"))}</div>'

    total = len(records)
    correct = sum(1 for r in records if r.get("correct"))
    fn = sum(1 for r in records if r.get("actual") == "favorable" and r.get("predicted_label") != "favorable")
    fp = sum(1 for r in records if r.get("actual") == "unfavorable" and r.get("predicted_label") == "favorable")
    acc = round(correct / total * 100) if total else 0

    def stat_url(flt: str) -> str:
        # Toggle off if already active
        if filter_mode == flt:
            return html.escape(_url("history", species))
        return html.escape(_url("history", species, **{"filter": flt}))

    def stat_card(val: str, lbl_key: str, color_cls: str, flt: str) -> str:
        active_cls = " pred-stat-active" if filter_mode == flt else ""
        return (
            f'<a class="pred-stat-card {color_cls}{active_cls}" href="{stat_url(flt)}">'
            f'<div class="pred-stat-val">{html.escape(val)}</div>'
            f'<div class="pred-stat-label">{html.escape(_lbl(lbl_key))}</div>'
            f'</a>'
        )

    all_card = (
        f'<a class="pred-stat-card{"  pred-stat-active" if not filter_mode else ""}" href="{html.escape(_url("history", species))}">'
        f'<div class="pred-stat-val">{total}</div>'
        f'<div class="pred-stat-label">{html.escape(_lbl("ui.predictor_stat_episodes"))}</div>'
        f'</a>'
    )

    return f"""
<div class="pred-stats-row">
  {all_card}
  {stat_card(f"{acc}%", "ui.predictor_stat_accuracy", "pred-green", "correct")}
  {stat_card(str(fn), "ui.predictor_stat_fn", "pred-red", "fn")}
  {stat_card(str(fp), "ui.predictor_stat_fp", "pred-yellow", "fp")}
</div>
"""


def _render_backtest_table(records: list[dict[str, Any]], known_sites_payload: dict[str, Any], filter_mode: str = "") -> str:
    if not records:
        return ""

    def matches(r: dict[str, Any]) -> bool:
        if not filter_mode:
            return True
        actual = r.get("actual", "")
        predicted = r.get("predicted_label", "")
        if filter_mode == "correct":
            return bool(r.get("correct"))
        if filter_mode == "fn":
            return actual == "favorable" and predicted != "favorable"
        if filter_mode == "fp":
            return actual == "unfavorable" and predicted == "favorable"
        return True

    visible = [r for r in records if matches(r)]

    rows_html = ""
    for r in sorted(visible, key=lambda x: x.get("observed_at", ""), reverse=True):
        actual = r.get("actual", "")
        predicted = r.get("predicted_label", "")
        correct = r.get("correct", False)
        result_icon = "✅" if correct else ("⚠️" if predicted == "uncertain" else "❌")
        area_n = _area_name(r.get("area_id", ""), known_sites_payload)
        prob = r.get("ensemble_probability")
        rows_html += f"""
<tr>
  <td>{html.escape(str(r.get("observed_at", "")))}</td>
  <td>{html.escape(area_n)}</td>
  <td>{_status_dot(actual)} {html.escape(_actual_text(actual))}</td>
  <td>{_status_dot(predicted)} {html.escape(_label_text(predicted) if predicted else "—")} {_pct(prob)}</td>
  <td>{result_icon}</td>
</tr>
"""

    return f"""
<div class="pred-table-scroll">
  <table class="pred-history-table">
    <thead>
      <tr>
        <th>{html.escape(_lbl("ui.date_short"))}</th>
        <th>{html.escape(_lbl("ui.known_site_area"))}</th>
        <th>{html.escape(_lbl("ui.predictor_actual"))}</th>
        <th>{html.escape(_lbl("ui.predictor_predicted"))}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>
"""


# ---------------------------------------------------------------------------
# Error block
# ---------------------------------------------------------------------------

def _render_errors(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{e}</li>" for e in errors)
    return f'<div class="pred-error"><ul>{items}</ul></div>'


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_page(
    query: dict[str, list[str]],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    view = (query.get("view") or ["recommender"])[0]
    species = (query.get("species") or [""])[0]
    area = (query.get("area") or [""])[0]
    date_str = (query.get("date") or [""])[0]
    filter_mode = (query.get("filter") or [""])[0]

    trained = trained_species_ids()

    if not trained:
        return f"""
<div class="pred-no-models">
  <p style="font-size:3rem">🤖</p>
  <h2>{html.escape(_lbl("ui.predictor_no_models"))}</h2>
  <p>{html.escape(_lbl("ui.predictor_no_models_help"))}</p>
  <a class="button-link secondary-link" href="?" style="margin-top:1rem">{html.escape(_lbl("ui.back"))}</a>
</div>
"""

    if not species or species not in trained:
        species = trained[0]

    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        target_date = date.today()

    tabs = _render_tabs(view, species, target_date)

    try:
        if view == "week":
            content = _render_week(species, target_date, trained, profiles_payload, known_sites_payload)
        elif view == "query":
            content = _render_query(species, area, target_date, trained, profiles_payload, known_sites_payload)
        elif view == "history":
            content = _render_history(species, area, trained, profiles_payload, known_sites_payload, filter_mode)
        else:
            content = _render_recommender(target_date, trained, profiles_payload, known_sites_payload)
    except Exception as exc:
        content = f'<div class="pred-error"><strong>Error cargando predictor:</strong> {html.escape(str(exc))}</div>'

    return f"""
<style>
{_CSS}
</style>
<div class="pred-page">
  <div class="pred-back"><a href="../../">← {html.escape(_lbl("ui.back_to_panel"))}</a></div>
  <h1>🍄 {html.escape(_lbl("ui.predictor_title"))}</h1>
  {tabs}
  {content}
</div>
"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
.pred-page { max-width: 900px; margin: 0 auto; padding: 0 1rem 3rem; }
.pred-page h1 { margin-bottom: 0.5rem; }
.pred-back { margin-bottom: 0.75rem; }
.pred-back a { color: #9aa8b2; font-size: 0.85rem; text-decoration: none; }
.pred-back a:hover { color: #e8eef2; }

/* Tabs */
.pred-tabs { display: flex; gap: 0.25rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.pred-tab {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  background: #1b2229;
  color: #9aa8b2;
  text-decoration: none;
  font-size: 0.9rem;
  border: 1px solid #33404a;
  transition: background 0.15s;
}
.pred-tab:hover { background: #243040; color: #e8eef2; }
.pred-tab-active { background: #0d2436; color: #03a9f4; border-color: #03a9f4; }

/* Section */
.pred-section h2 { margin-top: 0; color: #e8eef2; }
.pred-section h3 { color: #9aa8b2; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1.5rem; }

/* Day strip */
.pred-day-strip {
  display: flex; gap: 0.25rem; margin-bottom: 1.5rem; flex-wrap: wrap;
}
.pred-day {
  flex: 1 1 80px; min-width: 60px;
  padding: 0.5rem 0.25rem;
  text-align: center;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 8px;
  text-decoration: none;
  color: #9aa8b2;
  font-size: 0.85rem;
  line-height: 1.4;
  transition: background 0.15s;
}
.pred-day:hover { background: #243040; color: #e8eef2; }
.pred-day-active { background: #0d2436; border-color: #03a9f4; color: #03a9f4; }

/* Best bet card */
.pred-best-card {
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #33404a;
  background: #1b2229;
  position: relative;
}
.pred-best-badge {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9aa8b2;
  margin-bottom: 0.5rem;
}
.pred-best-name { font-size: 1.4rem; font-weight: 700; color: #e8eef2; }
.pred-best-area { font-size: 1rem; color: #9aa8b2; margin-top: 0.15rem; }
.pred-best-prob { font-size: 2.5rem; font-weight: 900; margin: 0.5rem 0 0.25rem; }
.pred-best-hint { font-size: 0.85rem; color: #9aa8b2; }

/* Status colors */
.pred-green { border-color: #51cf66 !important; }
.pred-green .pred-best-prob, .pred-green .pred-result-prob { color: #51cf66; }
.pred-yellow { border-color: #ffd43b !important; }
.pred-yellow .pred-best-prob, .pred-yellow .pred-result-prob { color: #ffd43b; }
.pred-red { border-color: #ff6b6b !important; }
.pred-red .pred-best-prob, .pred-red .pred-result-prob { color: #ff6b6b; }

/* Ranked list */
.pred-rank-list { display: flex; flex-direction: column; gap: 0.25rem; }
.pred-rank-header {
  display: grid;
  grid-template-columns: 1.5rem 1fr 1fr 4rem;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #9aa8b2;
  letter-spacing: 0.05em;
}
.pred-rank-row {
  display: grid;
  grid-template-columns: 1.5rem 1fr 1fr 4rem;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  background: #1b2229;
  border-radius: 8px;
  border: 1px solid #33404a;
  text-decoration: none;
  color: #e8eef2;
  font-size: 0.9rem;
  align-items: center;
  transition: background 0.1s;
}
.pred-rank-row:hover { background: #243040; }
.pred-rank-area { color: #9aa8b2; }
.pred-rank-prob { text-align: right; font-weight: 600; }
.pred-rank-compact .pred-rank-row {
  grid-template-columns: 1.5rem 1fr 4rem;
}

/* Species chips */
.pred-chips { display: flex; gap: 0.4rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.pred-chip {
  padding: 0.4rem 0.9rem;
  border-radius: 20px;
  background: #1b2229;
  border: 1px solid #33404a;
  color: #9aa8b2;
  text-decoration: none;
  font-size: 0.85rem;
  transition: background 0.1s;
}
.pred-chip:hover { background: #243040; color: #e8eef2; }
.pred-chip-active { background: #0d2436; border-color: #03a9f4; color: #03a9f4; }

/* Week grid */
.pred-table-scroll { overflow-x: auto; }
.pred-week-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.pred-week-table th {
  background: #1b2229;
  padding: 0.5rem 0.4rem;
  text-align: center;
  color: #9aa8b2;
  border-bottom: 1px solid #33404a;
  white-space: nowrap;
}
.pred-week-table td { padding: 0.4rem; border-bottom: 1px solid #1b2229; }
.pred-area-cell { color: #9aa8b2; white-space: nowrap; padding-right: 0.75rem; }
.pred-cell { text-align: center; }
.pred-cell a { text-decoration: none; color: inherit; }
.pred-today-col { color: #03a9f4; }
.pred-hint-legend { font-size: 0.8rem; color: #9aa8b2; margin-top: 0.75rem; }

/* Form */
.pred-form { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; }
.pred-form-row { display: flex; flex-direction: column; gap: 0.3rem; }
.pred-form-row label { font-size: 0.8rem; color: #9aa8b2; text-transform: uppercase; letter-spacing: 0.05em; }
.pred-form select, .pred-form input[type="date"] {
  background: #1b2229;
  border: 1px solid #33404a;
  color: #e8eef2;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
}

/* Result card */
.pred-result-card {
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  border: 1px solid #33404a;
  background: #1b2229;
  margin-bottom: 1rem;
}
.pred-result-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
  color: #9aa8b2;
  font-size: 0.9rem;
}
.pred-result-species { font-weight: 600; color: #e8eef2; }
.pred-result-dot { font-size: 1.1rem; }
.pred-result-prob { font-size: 2.5rem; font-weight: 900; margin: 0.25rem 0; }
.pred-result-label { font-size: 0.9rem; color: #9aa8b2; margin-bottom: 0.5rem; }
.pred-prob-detail { font-size: 0.8rem; color: #9aa8b2; display: flex; gap: 1rem; }
.pred-station-info { font-size: 0.8rem; color: #9aa8b2; display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; }
.pred-gaps { margin-top: 0.5rem; color: #9aa8b2; }

/* Week strip (query view) */
.pred-week-strip {
  display: flex; gap: 0.25rem; margin-bottom: 1rem; flex-wrap: wrap;
}
.pred-week-cell {
  flex: 1 1 80px;
  padding: 0.4rem 0.25rem;
  text-align: center;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 8px;
  text-decoration: none;
  color: #9aa8b2;
  font-size: 0.8rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  transition: background 0.1s;
}
.pred-week-cell:hover { background: #243040; }
.pred-week-active { border-width: 2px; }

/* Feature bars */
.pred-features { margin-top: 1rem; background: #1b2229; border-radius: 10px; padding: 1rem 1.25rem; }
.pred-features h4 { margin: 0 0 0.75rem; color: #9aa8b2; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.pred-feat-row { display: grid; grid-template-columns: 9rem 1fr 4rem; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
.pred-feat-label { font-size: 0.82rem; color: #9aa8b2; white-space: nowrap; }
.pred-feat-bar-bg { background: #33404a; border-radius: 4px; height: 8px; }
.pred-feat-bar { background: #03a9f4; border-radius: 4px; height: 100%; min-width: 2px; }
.pred-feat-val { font-size: 0.82rem; color: #e8eef2; text-align: right; }

/* Stats row */
.pred-stats-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.pred-stat-card {
  flex: 1 1 100px;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: center;
}
.pred-stat-val { font-size: 1.8rem; font-weight: 900; color: #e8eef2; }
.pred-stat-label { font-size: 0.75rem; color: #9aa8b2; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem; }
.pred-stat-card.pred-green .pred-stat-val { color: #51cf66; }
.pred-stat-card.pred-red .pred-stat-val { color: #ff6b6b; }
.pred-stat-card.pred-yellow .pred-stat-val { color: #ffd43b; }
a.pred-stat-card { text-decoration: none; cursor: pointer; transition: background 0.15s, border-color 0.15s; }
a.pred-stat-card:hover { background: #243040; }
.pred-stat-active { outline: 2px solid #03a9f4; outline-offset: 2px; }

/* History table */
.pred-history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.pred-history-table th {
  background: #1b2229;
  padding: 0.5rem 0.75rem;
  text-align: left;
  color: #9aa8b2;
  border-bottom: 1px solid #33404a;
}
.pred-history-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #1b2229;
  color: #e8eef2;
}
.pred-history-table tr:hover td { background: #1e2a34; }

/* Utilities */
.pred-error {
  background: #2d1a1a;
  border: 1px solid #7a3030;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: #ff9b9b;
  margin-bottom: 1rem;
  font-size: 0.88rem;
}
.pred-empty { color: #9aa8b2; font-style: italic; padding: 1rem 0; }
.pred-no-models { text-align: center; padding: 3rem 1rem; color: #9aa8b2; }
.pred-no-models h2 { color: #e8eef2; }
"""
