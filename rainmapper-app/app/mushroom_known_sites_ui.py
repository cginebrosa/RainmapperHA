"""Server-rendered maintenance UI for private mushroom areas and micro-areas."""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlencode

from rainmapper_core import mushroom_known_sites, mushroom_soilgrids_reconciler
import mushroom_profiles_ui


def label(key: str) -> str:
    return mushroom_profiles_ui.ui_label(key)


def query_url(kind: str = "", item_id: str = "", search: str = "", return_to: str = "") -> str:
    params = {}
    if kind:
        params["kind"] = kind
    if item_id:
        params["id"] = item_id
    if search:
        params["q"] = search
    if return_to:
        params["return_to"] = return_to
    return "?" + urlencode(params) if params else "?"


def _text(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _number(value: object) -> str:
    return "" if value is None else _text(value)


def _aliases(value: object) -> str:
    return ", ".join(str(item) for item in value) if isinstance(value, list) else ""


def _location(row: dict[str, object]) -> tuple[str, str]:
    location = row.get("representative_location")
    if not isinstance(location, dict):
        return "", ""
    return _number(location.get("lat")), _number(location.get("lon"))


def _geometry(row: dict[str, object]) -> str:
    value = row.get("geometry")
    return "" if value in (None, {}) else json.dumps(value, ensure_ascii=False, indent=2)


def _area_options(payload: dict[str, object], selected: str = "") -> str:
    rows = payload.get("areas") if isinstance(payload.get("areas"), list) else []
    options = ['<option value="">Selecciona un área…</option>']
    for row in rows:
        if not isinstance(row, dict) or row.get("archived"):
            continue
        area_id = str(row.get("area_id", ""))
        chosen = " selected" if area_id == selected else ""
        options.append(f'<option value="{_text(area_id)}"{chosen}>{html.escape(str(row.get("name", area_id)))}</option>')
    return "".join(options)


def _area_form(row: dict[str, object], *, create: bool = False, return_to: str = "", geometry_id: str = "") -> str:
    row = row or mushroom_known_sites.empty_area()
    area_id = str(row.get("area_id", ""))
    administrative = row.get("administrative_location") if isinstance(row.get("administrative_location"), dict) else {}
    lat, lon = _location(row)
    action = "create_area" if create else "save_area"
    geometry_attr = f' id="{_text(geometry_id)}"' if geometry_id else ""
    pending_report = row.get("_pending_gis_report") if isinstance(row.get("_pending_gis_report"), dict) else None
    initial_dirty = bool(pending_report or row.get("_has_unsaved_changes"))
    return f"""
    <form class="catalog-entry-form" method="post"{' data-initial-dirty="true"' if initial_dirty else ''}>
      <input type="hidden" name="known_site_action" value="{action}">
      <input type="hidden" name="known_site_kind" value="area">
      <input type="hidden" name="return_to" value="{_text(return_to)}">
      {f'<input type="hidden" name="gis_report_json" value="{_text(json.dumps(pending_report, ensure_ascii=False))}">' if pending_report else ''}
      <div class="parameter-card-heading"><h2>{html.escape(label('ui.known_site_area'))}</h2></div>
      {f'<input type="hidden" name="area_id" value="{_text(area_id)}">' if create else ''}
      <div class="profile-grid two">
        {'' if create else f'<div class="admin-field"><label>{html.escape(label("ui.area_id"))}</label><input name="area_id" value="{_text(area_id)}" readonly></div>'}
        <div class="admin-field{' wide' if create else ''}"><label>{html.escape(label('ui.name'))}</label><input name="name" value="{_text(row.get('name'))}" required autofocus></div>
        <div class="admin-field wide"><label>{html.escape(label('ui.description'))}</label><input name="description" value="{_text(row.get('description'))}"></div>
        <div class="admin-field wide"><label>{html.escape(label('ui.aliases'))}</label><input name="aliases" value="{_text(_aliases(row.get('aliases')))}"></div>
      </div>
      <details class="catalog-json-panel">
        <summary>{html.escape(label('ui.advanced_fields'))}</summary>
        <div class="profile-grid two">
          <div class="admin-field"><label>{html.escape(label('ui.municipality'))}</label><input name="municipality" value="{_text(administrative.get('municipality'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.county'))}</label><input name="county" value="{_text(administrative.get('county'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.province'))}</label><input name="province" value="{_text(administrative.get('province'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.country'))}</label><input name="country" value="{_text(administrative.get('country'))}"></div>
          <div class="admin-field"><label>{html.escape(label('location.lat'))}</label><input name="lat" type="number" step="any" value="{lat}"></div>
          <div class="admin-field"><label>{html.escape(label('location.lon'))}</label><input name="lon" type="number" step="any" value="{lon}"></div>
          <div class="admin-field wide known-site-geometry-raw"><label>{html.escape(label('ui.geometry_geojson'))}</label><textarea{geometry_attr} name="geometry_json" rows="5">{html.escape(_geometry(row))}</textarea></div>
          <div class="admin-field wide"><label>{html.escape(label('ui.private_notes'))}</label><textarea name="notes" rows="4">{html.escape(str(row.get('notes', '') or ''))}</textarea></div>
        </div>
      </details>
      <div class="profile-action-bar maintenance-action-bar"><button class="primary" name="save_confirmation" value="1" data-save-site>{html.escape(label('ui.create') if create else label('ui.save'))}</button></div>
    </form>
    """


def _micro_form(row: dict[str, object], payload: dict[str, object], *, create: bool = False, return_to: str = "", geometry_id: str = "") -> str:
    row = row or mushroom_known_sites.empty_micro_area()
    micro_id = str(row.get("micro_area_id", ""))
    altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
    topography = row.get("topography") if isinstance(row.get("topography"), dict) else {}
    ecology = row.get("ecology") if isinstance(row.get("ecology"), dict) else {}
    access = row.get("access") if isinstance(row.get("access"), dict) else {}
    provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    lat, lon = _location(row)
    action = "create_micro_area" if create else "save_micro_area"
    geometry_attr = f' id="{_text(geometry_id)}"' if geometry_id else ""
    pending_report = row.get("_pending_gis_report") if isinstance(row.get("_pending_gis_report"), dict) else None
    initial_dirty = bool(pending_report or row.get("_has_unsaved_changes"))
    return f"""
    <form class="catalog-entry-form" method="post"{' data-initial-dirty="true"' if initial_dirty else ''}>
      <input type="hidden" name="known_site_action" value="{action}">
      <input type="hidden" name="known_site_kind" value="micro_area">
      <input type="hidden" name="return_to" value="{_text(return_to)}">
      {f'<input type="hidden" name="gis_report_json" value="{_text(json.dumps(pending_report, ensure_ascii=False))}">' if pending_report else ''}
      <div class="parameter-card-heading"><h2>{html.escape(label('ui.known_site_micro_area'))}</h2></div>
      {f'<input type="hidden" name="micro_area_id" value="{_text(micro_id)}">' if create else ''}
      <div class="profile-grid two">
        {'' if create else f'<div class="admin-field"><label>{html.escape(label("ui.micro_area_id"))}</label><input name="micro_area_id" value="{_text(micro_id)}" readonly></div>'}
        <div class="admin-field"><label>{html.escape(label('ui.parent_area'))}</label><select name="area_id" required>{_area_options(payload, str(row.get('area_id', '')))}</select></div>
        <div class="admin-field"><label>{html.escape(label('ui.name'))}</label><input name="name" value="{_text(row.get('name'))}" required autofocus></div>
        <div class="admin-field"><label>{html.escape(label('ui.aliases'))}</label><input name="aliases" value="{_text(_aliases(row.get('aliases')))}"></div>
        <div class="admin-field wide"><label>{html.escape(label('ui.description'))}</label><input name="description" value="{_text(row.get('description'))}"></div>
        <div class="admin-field"><label>{html.escape(label('location.lat'))}</label><input name="lat" type="number" step="any" value="{lat}"></div>
        <div class="admin-field"><label>{html.escape(label('location.lon'))}</label><input name="lon" type="number" step="any" value="{lon}"></div>
        <div class="admin-field"><label>{html.escape(label('ui.location_precision_m'))}</label><input name="location_precision_m" type="number" min="0" step="1" value="{_number(row.get('location_precision_m'))}"></div>
      </div>
      <details class="catalog-json-panel">
        <summary>{html.escape(label('ui.environment_and_future_fields'))}</summary>
        <div class="profile-grid two">
          <div class="admin-field"><label>{html.escape(label('ui.altitude_min'))}</label><input name="altitude_min_m" type="number" step="1" value="{_number(altitude.get('min_m'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.altitude_max'))}</label><input name="altitude_max_m" type="number" step="1" value="{_number(altitude.get('max_m'))}"></div>
          <div class="admin-field"><label>{html.escape(label('altitude.source'))}</label><input name="altitude_source" value="{_text(altitude.get('source'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.aspect_ids'))}</label><input name="aspect_ids" value="{_text(_aliases(topography.get('aspect_ids')))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.slope_notes'))}</label><input name="slope_notes" value="{_text(topography.get('slope_notes'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.exposure_notes'))}</label><input name="exposure_notes" value="{_text(topography.get('exposure_notes'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.host_ids'))}</label><input name="host_ids" value="{_text(_aliases(ecology.get('host_ids')))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.forest_type_ids'))}</label><input name="forest_type_ids" value="{_text(_aliases(ecology.get('forest_type_ids')))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.soil_tendency_ids'))}</label><input name="soil_tendency_ids" value="{_text(_aliases(ecology.get('soil_tendency_ids')))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.habitat_feature_ids'))}</label><input name="habitat_feature_ids" value="{_text(_aliases(ecology.get('habitat_feature_ids')))}"></div>
          <div class="admin-field wide"><label>{html.escape(label('ui.ecology_notes'))}</label><textarea name="ecology_notes" rows="3">{html.escape(str(ecology.get('notes', '') or ''))}</textarea></div>
          <div class="admin-field"><label>{html.escape(label('ui.access_difficulty'))}</label><input name="access_difficulty" value="{_text(access.get('difficulty'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.provenance_source'))}</label><input name="provenance_source" value="{_text(provenance.get('source'))}"></div>
          <div class="admin-field"><label>{html.escape(label('ui.provenance_confidence'))}</label><input name="provenance_confidence" value="{_text(provenance.get('confidence'))}"></div>
          <div class="admin-field wide"><label>{html.escape(label('ui.access_notes'))}</label><textarea name="access_notes" rows="3">{html.escape(str(access.get('notes', '') or ''))}</textarea></div>
          <div class="admin-field wide"><label>{html.escape(label('ui.provenance_notes'))}</label><textarea name="provenance_notes" rows="3">{html.escape(str(provenance.get('notes', '') or ''))}</textarea></div>
          <div class="admin-field wide known-site-geometry-raw"><label>{html.escape(label('ui.geometry_geojson'))}</label><textarea{geometry_attr} name="geometry_json" rows="5">{html.escape(_geometry(row))}</textarea></div>
          <div class="admin-field wide"><label>{html.escape(label('ui.private_notes'))}</label><textarea name="notes" rows="4">{html.escape(str(row.get('notes', '') or ''))}</textarea></div>
        </div>
      </details>
      <div class="profile-action-bar maintenance-action-bar"><button class="primary" name="save_confirmation" value="1" data-save-site>{html.escape(label('ui.create') if create else label('ui.save'))}</button></div>
    </form>
    """


def _known_sites_map_assets() -> str:
    # Small static assets only; no hidden observation reports or GIS payloads.
    root = Path(__file__).parent
    return ('<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css">'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@watergis/maplibre-gl-terradraw@1.0.1/dist/maplibre-gl-terradraw.css">'
            '<style>' + (root / "known-sites.css").read_text(encoding="utf-8") + '</style>'
            '<script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>'
            '<script src="https://cdn.jsdelivr.net/npm/@watergis/maplibre-gl-terradraw@1.0.1/dist/maplibre-gl-terradraw.umd.js"></script>'
            '<script>' + (root / "known-sites.js").read_text(encoding="utf-8") + '</script>')


def _gis_review_modal(preview: dict[str, object] | None, selected_row: dict[str, object] | None, return_to: str, close_href: str) -> str:
    if not isinstance(preview, dict) or preview.get("draft") or not isinstance(preview.get("report"), dict) or not selected_row:
        return ""
    report = preview["report"]
    base_row = preview.get("base") if isinstance(preview.get("base"), dict) else selected_row
    kind = str(preview.get("kind", ""))
    site_id = str(preview.get("id", ""))
    altitude = base_row.get("altitude") if isinstance(base_row.get("altitude"), dict) else {}
    topography = base_row.get("topography") if isinstance(base_row.get("topography"), dict) else {}
    ecology = base_row.get("ecology") if isinstance(base_row.get("ecology"), dict) else {}
    gis = report.get("gis") if isinstance(report.get("gis"), dict) else {}
    fields = [
        ("altitude_min_m", label("ui.altitude_min"), altitude.get("min_m"), report.get("altitude_min_m"), "DEM 5 m"),
        ("altitude_max_m", label("ui.altitude_max"), altitude.get("max_m"), report.get("altitude_max_m"), "DEM 5 m"),
        ("slope_notes", label("ui.slope_notes"), topography.get("slope_notes"), f"DEM: media {report.get('slope_mean_deg', '-')}°, rango {report.get('slope_min_deg', '-')}°-{report.get('slope_max_deg', '-')}°", "DEM 5 m"),
        ("aspect_ids", label("ui.aspect_ids"), topography.get("aspect_ids"), report.get("dominant_aspect_ids"), "DEM 5 m"),
        ("host_ids", label("ui.host_ids"), ecology.get("host_ids"), gis.get("host_ids"), "MVC50 + MFE25: " + str(gis.get("mfe25", {}).get("status", "not_connected"))),
        ("forest_type_ids", label("ui.forest_type_ids"), ecology.get("forest_type_ids"), gis.get("forest_type_ids"), "MVC50"),
        ("soil_tendency_ids", label("ui.soil_tendency_ids"), ecology.get("soil_tendency_ids"), gis.get("soil_tendency_ids"), "Geología/GIS"),
        ("habitat_feature_ids", label("ui.habitat_feature_ids"), ecology.get("habitat_feature_ids"), gis.get("habitat_feature_ids"), "MVC50/GIS"),
    ]
    rows = []
    if kind == "area":
        fields = []
    for field, field_label, current, proposed, source in fields:
        if proposed in (None, [], ""):
            continue
        current_text = ", ".join(map(str, current)) if isinstance(current, list) else str(current if current not in (None, "") else "-")
        proposed_text = ", ".join(map(str, proposed)) if isinstance(proposed, list) else str(proposed)
        empty = current in (None, [], "")
        same = set(map(str, current or [])) == set(map(str, proposed)) if isinstance(proposed, list) else current == proposed
        if field in {"altitude_min_m", "altitude_max_m"} and not empty:
            same = float(current) == float(proposed)
        discrepancy = not empty and not same
        options = (f'<option value="keep"{" selected" if same else ""}>Mantener</option>'
                   + ('<option value="merge">Fusionar</option>' if isinstance(proposed, list) else '')
                   + f'<option value="replace"{" selected" if not same else ""}>Reemplazar</option>')
        rows.append(
            f'<tr class="{"gis-discrepancy" if discrepancy else ""}"><td><strong>{html.escape(field_label)}</strong></td>'
            f'<td data-gis-label="Valor actual">{html.escape(current_text)}</td><td data-gis-label="Propuesta">{html.escape(proposed_text)}<small>{html.escape(source)}</small></td>'
            f'<td data-gis-label="Decisión"><select name="gis_mode_{_text(field)}" data-gis-mode data-current-empty="{str(empty).lower()}" aria-label="{_text(field_label)}">{options}</select></td></tr>'
        )
    metrics = (
        f"Centroide y métricas geométricas · {report.get('sample_count', 0)} muestras · "
        f"altitud {report.get('altitude_min_m', '-')}–{report.get('altitude_max_m', '-')} m · "
        f"orientaciones {', '.join(f'{key}: {value}%' for key, value in (report.get('aspect_distribution') or {}).items()) or '-'}"
    )
    close_separator = "&" if "?" in close_href else "?"
    cancel_href = f"{close_href}{close_separator}discard_gis_draft=1"
    return f"""
    <div id="gis-dem-review" class="modal-layer">
      <div class="modal-card modal-card-wide gis-review-modal">
        <header class="modal-head"><div><h2>Revisar datos GIS/DEM</h2><p>{html.escape(site_id)} · {html.escape(metrics)}</p></div><a class="button-link" data-gis-cancel href="{_text(cancel_href)}">{html.escape(label('ui.cancel'))}</a></header>
        <form method="post">
          <input type="hidden" name="known_site_action" value="apply_gis_dem"><input type="hidden" name="known_site_kind" value="{_text(kind)}"><input type="hidden" name="known_site_id" value="{_text(site_id)}"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="hidden" name="gis_report_json" value="{_text(json.dumps(report, ensure_ascii=False))}"><input type="hidden" name="gis_base_row_json" value="{_text(json.dumps(base_row, ensure_ascii=False))}">
          {f'<table class="gis-review-table"><thead><tr><th>Campo</th><th>Valor actual</th><th>Propuesta</th><th>Decisión</th></tr></thead><tbody>{"".join(rows)}</tbody></table>' if rows else '<div class="catalog-alert">Los datos derivados se guardarán como contexto propio del área. No hay campos manuales equivalentes que sustituir.</div>'}
          <p>La cobertura MFE25 corresponde al polígono forestal, no a la abundancia de cada árbol. Aplicar deja la ficha abierta para revisar antes de Guardar.</p>
          <div class="gis-review-actions"><button type="button" data-gis-select="empty">Completar campos vacíos</button><button type="button" data-gis-select="merge">Fusionar listas</button><button type="button" data-gis-select="all">Reemplazar todo GIS/DEM</button><button type="button" data-gis-select="none">Mantener actuales</button><button class="primary">Aplicar al borrador</button></div>
        </form>
      </div>
    </div>
    """


def workspace_data(payload: dict[str, object], observations: dict[str, object]) -> dict[str, object]:
    """Map contract: geometry once, minimal metadata, no derived rasters/reports."""
    counts = mushroom_known_sites.observation_reference_counts(observations)
    pending = {r["micro_area_id"] for r in mushroom_soilgrids_reconciler.inspect_payload(payload)["unresolved"]}
    children_counts: dict[str, int] = {}
    micros = payload.get("micro_areas", [])
    for row in micros:
        parent = str(row.get("area_id", ""))
        children_counts[parent] = children_counts.get(parent, 0) + counts.get(str(row.get("micro_area_id", "")), 0)
    features = []
    rows = []
    for kind, key, id_key in (("area", "areas", "area_id"), ("micro_area", "micro_areas", "micro_area_id")):
        for row in payload.get(key, []):
            item_id = str(row.get(id_key, ""))
            uid = f"{kind}:{item_id}"
            location = row.get("representative_location") or {}
            geometry = row.get("geometry")
            if not geometry and isinstance(location.get("lon"), (int, float)) and isinstance(location.get("lat"), (int, float)):
                geometry = {"type": "Point", "coordinates": [location["lon"], location["lat"]]}
            properties = {"key": uid, "kind": kind, "id": item_id, "name": str(row.get("name", item_id)),
                          "parent": str(row.get("area_id", "")) if kind == "micro_area" else "",
                          "archived": bool(row.get("archived")),
                          "count": children_counts.get(item_id, 0) if kind == "area" else counts.get(item_id, 0),
                          "has_geometry": bool(row.get("geometry")),
                          "soilgrids_pending": kind == "micro_area" and item_id in pending}
            rows.append(properties)
            if geometry:
                features.append({"type": "Feature", "id": uid, "properties": {"key": uid, "kind": kind}, "geometry": geometry})
    return {"rows": rows, "geojson": {"type": "FeatureCollection", "features": features}}


def render_selection_fragment(payload: dict[str, object], query: dict[str, list[str]], gis_preview: dict[str, object] | None = None) -> dict[str, object]:
    kind = (query.get("kind") or ["micro_area"])[0]
    item_id = (query.get("id") or [""])[0]
    create = (query.get("new") or [""])[0] == "1"
    return_to = (query.get("return_to") or ["./profiles?section=observations"])[0]
    key, id_key = ("areas", "area_id") if kind == "area" else ("micro_areas", "micro_area_id")
    row = next((x for x in payload.get(key, []) if str(x.get(id_key)) == item_id), None)
    if create:
        row = mushroom_known_sites.empty_area() if kind == "area" else mushroom_known_sites.empty_micro_area(area_id=(query.get("parent") or [""])[0])
    if row is None:
        return {"selected": False, "editor_html": "", "map_html": ""}
    if gis_preview and gis_preview.get("kind") == kind and gis_preview.get("id") == item_id:
        row = gis_preview.get("draft") or gis_preview.get("base") or row
    parent = next((x for x in payload.get("areas", []) if x.get("area_id") == row.get("area_id")), {}) if kind == "micro_area" else {}
    form = (_area_form(row, create=create, return_to=return_to, geometry_id="known-site-geometry") if kind == "area" else
            _micro_form(row, payload, create=create, return_to=return_to, geometry_id="known-site-geometry"))
    # Section placement is client-side; all controls remain in this one form.
    form = form.replace(' autofocus', '')
    title = ("Nueva área" if kind == "area" else "Nueva microárea") if create else str(row.get("name", item_id))
    editor = f'''<header class="site-detail-head"><div><small>{_text(parent.get("name", "Área" if kind == "area" else "Microárea"))}</small><h2>{_text(title)}</h2></div><button type="button" data-close-detail aria-label="Cerrar ficha">×</button></header>
      <nav class="sites-tabs" aria-label="Secciones de la ficha"><button type="button" data-tab="general" class="active">General</button><button type="button" data-tab="environment">Entorno</button><button type="button" data-tab="notes">Notas</button><button type="button" data-tab="observations" {'disabled' if create else ''}>Observaciones</button></nav>
      <div class="sites-editor-body">{form}<div id="site-observations" hidden></div></div>
      <footer class="site-detail-actions"><span id="site-save-state" role="status"></span><button type="button" id="site-cancel">Cancelar</button><button type="button" id="site-save" class="primary">{'Crear setal' if create else 'Guardar'}</button></footer>'''
    selection = {"kind": kind, "id": item_id, "selected": True, "create": create, "archived": bool(row.get("archived")),
                 "name": title, "parent": str(row.get("area_id", "")) if kind == "micro_area" else "",
                 "parent_geometry": parent.get("geometry"), "location": row.get("representative_location"),
                 "dirty": bool(row.get("_pending_gis_report") or row.get("_has_unsaved_changes"))}
    current_url = query_url(kind, item_id, return_to=return_to)
    return {"selected": True, "kind": kind, "selected_id": item_id, "editor_html": editor,
            "selection": selection, "map_html": "",
            "gis_html": _gis_review_modal(gis_preview, row, return_to, current_url)}


def observation_page(payload: dict[str, object], observations: dict[str, object], query: dict[str, list[str]]) -> dict[str, object]:
    """Bounded list, fetched only when the observations tab is opened."""
    kind, item_id = (query.get("kind") or [""])[0], (query.get("id") or [""])[0]
    ids = {item_id} if kind == "micro_area" else {str(x.get("micro_area_id")) for x in payload.get("micro_areas", []) if x.get("area_id") == item_id}
    rows = sorted((x for x in observations.get("observations", []) if x.get("micro_area_id") in ids), key=lambda x: str(x.get("observed_at", "")), reverse=True)
    try:
        offset = max(0, int((query.get("offset") or ["0"])[0]))
    except ValueError:
        offset = 0
    items = []
    for row in rows[offset:offset + 50]:
        href = "./profiles?" + urlencode({"section": "observations", "id": row.get("species_id", ""), "obs_id": row.get("observation_id", ""),
                                          "return_to": "./known-sites" + query_url(kind, item_id)}) + "#observation-detail"
        items.append({"date": str(row.get("observed_at", "")), "species": str(row.get("species_id", "")), "abundance": str(row.get("flush_abundance", "")), "href": href})
    return {"ok": True, "total": len(rows), "offset": offset, "items": items, "next": offset + 50 if offset + 50 < len(rows) else None}


def render_page(payload: dict[str, object], observations_payload: dict[str, object], query: dict[str, list[str]], flash: str = "", gis_preview: dict[str, object] | None = None, catalogs_payload: dict[str, object] | None = None, soilgrids_health: dict[str, object] | None = None) -> str:
    data = workspace_data(payload, observations_payload)
    data["soilgrids_warning"] = label("ui.soilgrids_pending") if any(r["soilgrids_pending"] for r in data["rows"]) else ""
    data["return_to"] = (query.get("return_to") or ["./profiles?section=observations"])[0]
    # Escape '<' even inside JSON to keep user-entered names out of script markup.
    bootstrap = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    initial = render_selection_fragment(payload, query, gis_preview) if (query.get("id") or query.get("new")) else None
    initial_json = json.dumps(initial, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'''
    <section id="sites-app" aria-label="Mantenimiento de setales">
      <header class="sites-header"><div class="sites-heading"><a class="button-link" href="{_text(data['return_to'])}">← Volver</a><h1>{html.escape(label('ui.known_sites'))}</h1><span id="sites-counts"></span></div>
      <div class="sites-actions"><button type="button" id="sites-list-toggle" aria-expanded="true">☰ Lista</button><button type="button" data-new="area">+ Área</button><button type="button" data-new="micro_area">+ Microárea</button><button type="button" id="site-archive" disabled>Archivar</button><button type="button" id="site-delete" class="danger" hidden>Borrar…</button><button type="button" id="site-detail-toggle" disabled>Ficha</button></div></header>
      <div class="sites-stage"><div id="known-site-map"></div>
        <aside id="sites-list" class="sites-floating"><div class="sites-list-tools"><input id="sites-filter" type="search" placeholder="Buscar setal…" aria-label="Buscar setal"><select id="sites-status" aria-label="Estado"><option value="active">Activos</option><option value="all">Todos</option><option value="archived">Archivados</option></select></div><nav id="sites-tree" aria-label="Áreas y microáreas"></nav></aside>
        <aside id="sites-detail" class="sites-floating" hidden></aside>
        <div class="sites-map-controls"><button type="button" id="site-search-toggle" title="Buscar municipio o topónimo" aria-label="Buscar municipio o topónimo" aria-expanded="false"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/></svg></button><button type="button" id="site-layer-toggle" title="Fondo del mapa" aria-label="Fondo del mapa" aria-expanded="false"><svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 8 9-5 9 5-9 5Zm0 5 9 5 9-5M3 18l9 5 9-5"/></svg></button><button type="button" id="site-terrain-toggle" title="Relieve 3D" aria-pressed="false">3D</button><button type="button" id="site-north-toggle" title="Orientar al norte">↑N</button><button type="button" id="site-fit-all" title="Encuadrar todos los setales">⊞</button><button type="button" id="site-fit-selected" title="Encuadrar selección" disabled>◎</button></div>
        <section id="site-layer-panel" class="sites-map-panel" hidden><strong>Fondo del mapa</strong><button data-basemap="satellite" class="active">Satélite+</button><button data-basemap="hybrid">Híbrido</button><button data-basemap="topographic">Topográfico</button></section>
        <section id="site-search-panel" class="sites-map-panel" hidden><form id="site-search-form"><label for="site-search-input">Municipio o topónimo</label><div><input id="site-search-input" type="search" minlength="2" maxlength="160" required autocomplete="off" placeholder="Nombre, provincia o país"><button>Buscar</button></div></form><p id="site-search-status" role="status"></p><div id="site-search-results"></div><small>Búsqueda online: <a href="https://photon.komoot.io/" target="_blank" rel="noopener">Photon</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap</a></small></section>
        <div id="site-overlaps" class="sites-map-panel" hidden></div>
        <div id="site-geometry-tools" hidden><span id="site-geometry-status">Sin geometría</span><button type="button" id="site-edit-geometry">Editar geometría</button><button type="button" id="site-draw-polygon" hidden>Dibujar polígono</button><button type="button" id="site-edit-polygon" hidden>Editar vértices</button><button type="button" id="site-finish-geometry" hidden>Terminar dibujo</button><button type="button" id="site-clear-geometry" hidden>Quitar geometría…</button><button type="button" id="site-recover-gis">Recuperar GIS / DEM</button></div>
        <div id="sites-status-message" role="status" aria-live="polite">{_text(flash) or 'Selecciona un setal en el mapa o en la lista.'}</div>
      </div>
      <dialog id="site-unsaved"><h2>Cambios sin guardar</h2><p>¿Qué quieres hacer antes de continuar?</p><div><button data-choice="cancel">Seguir editando</button><button data-choice="discard">Descartar</button><button class="primary" data-choice="save">Guardar y continuar</button></div></dialog>
      <dialog id="site-confirm"><h2 id="site-confirm-title"></h2><p id="site-confirm-text"></p><div><button data-choice="cancel">Cancelar</button><button class="danger" data-choice="confirm">Confirmar</button></div></dialog>
      <dialog id="site-busy" aria-labelledby="site-busy-title"><span class="sites-spinner" aria-hidden="true"></span><h2 id="site-busy-title">Operación en curso</h2><p id="site-busy-text"></p><small>Espera a que termine. Los datos del formulario se conservan si hay un error.</small></dialog>
      <div id="site-gis-review"></div>
      <script id="sites-bootstrap" type="application/json">{bootstrap}</script><script id="sites-initial" type="application/json">{initial_json}</script>
    </section>{_known_sites_map_assets()}'''
