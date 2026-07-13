"""Server-rendered maintenance UI for private mushroom areas and micro-areas."""

from __future__ import annotations

import html
import json
from urllib.parse import urlencode

from rainmapper_core import mushroom_known_sites
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
    options = []
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


def _known_sites_map_assets(geometry_json: str, parent_geometry_json: str, has_selection: bool) -> str:
    """Return the scoped layout and polygon editor used by known-site maintenance."""
    return f"""
    <style>
      .sites-page-head{{display:flex;justify-content:space-between;align-items:end;margin:0 0 14px}}.sites-page-head h1{{font-size:28px;margin:5px 0 2px}}.sites-page-head p{{margin:0;color:#9eacb9}}.sites-back{{color:#8fa2b2;text-decoration:none;font-size:13px}}
      .sites-metrics{{display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:10px;max-width:760px;margin-bottom:10px}}.sites-metrics article{{position:relative;padding:12px 14px;background:#111b24;border:1px solid #2a3a48;border-radius:6px}}.sites-metrics span{{display:block;color:#a9b5bf;font-size:12px}}.sites-metrics strong{{display:block;font-size:24px;line-height:1.15;margin-top:3px}}.sites-metrics small{{color:#31c985}}
      .sites-workspace{{display:grid;grid-template-columns:minmax(260px,310px) minmax(410px,1fr) minmax(440px,1.25fr);gap:10px;height:clamp(560px,calc(100vh - 285px),760px);min-height:0;font-size:12px}}.sites-workspace input,.sites-workspace select,.sites-workspace textarea,.sites-workspace button,.sites-workspace .button-link{{font-size:12px}}.sites-tree-panel,.sites-editor-panel,.sites-map-card,.sites-derived-card{{background:#0d1720;border:1px solid #293a47;border-radius:6px;overflow:hidden}}.sites-tree-panel{{display:flex;flex-direction:column;min-height:0}}.sites-create-actions{{display:grid;grid-template-columns:1fr 1.25fr;gap:6px;padding:10px}}.sites-create-actions .button-link{{text-align:center;padding:9px 5px;line-height:1.25}}.sites-search{{padding:0 10px 7px}}.sites-search input{{width:100%;height:34px}}.sites-tree-actions{{display:flex;gap:6px;padding:0 10px 7px}}.sites-tree-actions button{{flex:1;padding:5px 6px;font-size:10px}}.sites-tree{{padding:0 8px;overflow:auto;flex:1;min-height:0}}.site-area-group{{display:block}}.site-area-children[hidden]{{display:none}}.site-tree-row{{display:grid;grid-template-columns:minmax(0,1fr) auto 26px;align-items:center;gap:5px;min-height:35px;padding:0 7px;color:#d9e1e7;border-left:3px solid transparent;border-radius:3px}}.site-tree-row.area{{grid-template-columns:22px minmax(0,1fr) auto 26px}}.site-tree-row.micro{{padding-left:20px}}.site-tree-toggle{{display:grid;place-items:center;width:22px;height:24px;padding:0;border:0;background:transparent;color:#8ca0af;font-size:13px}}.site-tree-toggle:hover{{color:#fff;background:#173142}}.site-tree-toggle span{{transition:transform .15s ease}}.site-tree-toggle[aria-expanded="false"] span{{transform:rotate(-90deg)}}.site-tree-area-link{{min-width:0;color:inherit;text-decoration:none}}.site-tree-area-link strong{{display:block}}.site-tree-main{{display:grid;grid-template-columns:20px minmax(0,1fr);align-items:center;gap:5px;min-width:0;color:inherit;text-decoration:none;font-size:12px}}.site-tree-row:hover{{background:#132634}}.site-tree-row.selected-row{{background:#15384b;border-left-color:#12b8ff;color:#fff}}.site-tree-row strong{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}}.site-tree-icon{{color:#7f94a4}}.site-status{{font-size:10px;color:#42d494;background:#0d3024;border:1px solid #17643f;border-radius:3px;padding:2px 5px}}.site-status.archived{{color:#ffbd55;background:#35230b;border-color:#8a5a16}}.site-count{{display:grid;place-items:center;min-width:22px;height:24px;font-size:11px;color:#9edfff;text-align:center;text-decoration:none;border:1px solid transparent;border-radius:4px}}.site-count:hover{{color:#fff;border-color:#168dba;background:#123348}}.sites-tree-panel footer{{padding:8px 12px;border-top:1px solid #263642;color:#9cabb7;font-size:11px}}
      .sites-editor-panel{{display:flex;flex-direction:column}}.sites-editor-head{{display:flex;align-items:center;gap:10px;min-height:49px;padding:0 13px;border-bottom:1px solid #263642}}.sites-editor-head div{{flex:1;color:#16baff;font-size:13px}}.sites-editor-head div span{{color:#667887;margin:0 8px}}.site-kind{{font-size:11px;color:#67c9f5;border:1px solid #15648a;border-radius:3px;padding:4px 8px}}.sites-tabs{{display:flex;gap:25px;padding:0 14px;border-bottom:1px solid #263642;height:43px;align-items:end}}.sites-tabs button{{padding:0 3px 10px;color:#a8b4be;font-size:12px;background:none;border:0;border-radius:0}}.sites-tabs .active{{color:#1fc0ff;border-bottom:2px solid #1fc0ff}}.sites-editor-body{{padding:10px;overflow:auto;flex:1}}.sites-editor-body .catalog-entry-form{{display:flex;flex-direction:column;height:100%}}.sites-editor-body .parameter-card-heading{{display:none}}.sites-editor-body .profile-grid{{background:#101c25;border:1px solid #293b48;border-radius:6px;padding:11px}}.sites-editor-body .profile-grid label{{font-size:11px}}.sites-editor-body .profile-grid input,.sites-editor-body .profile-grid select,.sites-editor-body .profile-grid textarea{{font-size:12px}}.sites-editor-body .profile-action-bar{{gap:6px;margin-top:auto;position:sticky;bottom:0;background:#0d1720;padding:10px 0 0}}.sites-editor-body .profile-action-bar button{{border-radius:6px;font-size:10px;min-height:32px;padding:6px 10px;width:100%}}.known-site-geometry-raw{{display:none!important}}.sites-archive{{display:flex;gap:6px;padding:0 10px 10px}}.sites-archive form{{flex:1}}.sites-archive form button{{border-radius:6px;font-size:10px;min-height:32px;padding:6px 10px;width:100%}}.sites-archive .warning{{color:#ffbd55;border-color:#8a5a16;background:#35230b}}.sites-archive .danger{{color:#ff6a6a;border-color:#73383e}}
      .sites-map-column{{display:flex;flex-direction:column;gap:10px}}.sites-map-card header,.sites-derived-card header{{display:flex;justify-content:space-between;align-items:center;padding:10px 12px}}.sites-map-card header button{{font-size:11px}}.sites-map-wrap{{height:390px;margin:0 10px;position:relative;border:1px solid #344754;border-radius:5px;overflow:hidden;background:#071018}}#known-site-map{{position:absolute;inset:0}}.sites-map-empty{{position:absolute;inset:0;display:grid;place-items:center;background:#0a141dcc;color:#90a0ac;z-index:3}}.sites-map-empty[hidden]{{display:none}}.site-map-controls{{display:grid;gap:7px;position:absolute;right:10px;top:10px;z-index:5}}.site-map-control{{display:flex;align-items:center;justify-content:center;width:38px;height:38px;padding:0;background:rgba(20,27,35,.94);border:1px solid rgba(255,255,255,.2);border-radius:7px;color:#f6fbff;box-shadow:0 6px 18px #02080e55;font-weight:800}}.site-map-control[aria-pressed="true"]{{background:#078ec7;border-color:#6dd4ff}}.site-map-control svg{{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linejoin:round}}.site-layer-toggle polygon{{fill:currentColor;stroke:none}}.site-north-toggle{{position:relative}}.site-north-toggle::before{{content:'';position:absolute;width:25px;height:25px;border:2px solid rgba(246,251,255,.72);border-radius:50%}}.site-north-toggle span{{width:13px;height:25px;background:linear-gradient(180deg,#e33d37 0 48%,#fff 52% 100%);clip-path:polygon(50% 0,76% 50%,50% 100%,24% 50%)}}.site-layer-panel{{position:absolute;right:56px;top:0;display:grid;min-width:145px;padding:5px;background:rgba(15,23,31,.97);border:1px solid #405361;border-radius:6px;box-shadow:0 10px 25px #0008}}.site-layer-panel[hidden]{{display:none}}.site-layer-panel button{{text-align:left;background:none;border:0;padding:8px 10px}}.site-layer-panel button.active{{color:#26bdff;background:#163345}}.geometry-actions{{display:flex;gap:7px;flex-wrap:wrap;padding:11px 12px 5px}}.geometry-actions button{{font-size:12px}}.geometry-actions .danger{{color:#ff646b;border-color:#71343a}}.geometry-status{{margin:5px 12px 12px;color:#8fa0ad;font-size:11px}}.sites-derived-card{{padding-bottom:10px}}.sites-derived-card>div{{display:grid;grid-template-columns:1fr 1.2fr;gap:8px;padding:3px 12px;font-size:12px}}.sites-derived-card span{{color:#91a2af}}.sites-derived-card strong{{font-weight:500}}.maplibregl-ctrl-attrib{{font-size:9px}}
      .gis-review-modal{{max-width:940px;max-height:min(82vh,760px)}}.gis-review-modal form{{display:flex;flex-direction:column;min-height:0}}.gis-review-table{{width:100%;border-collapse:collapse;font-size:13px}}.gis-review-table th,.gis-review-table td{{padding:6px 9px;border-bottom:1px solid #2b3c48;text-align:left;vertical-align:middle}}.gis-review-table td small{{display:block;color:#8093a1;margin-top:2px}}.gis-review-table .gis-discrepancy{{background:#442b161f}}.gis-review-table .gis-discrepancy td:first-child strong::after{{content:' Discrepancia';color:#f0a23c;font-size:10px;margin-left:7px}}.gis-review-choice{{display:flex;align-items:center;gap:7px;white-space:nowrap;font-size:12px}}.gis-review-choice input{{appearance:none;width:17px;height:17px;min-width:17px;margin:0;border:1px solid #718391;border-radius:3px;background:#0b1319}}.gis-review-choice input:checked{{border-color:#18b9f4;background:#078ec7;box-shadow:inset 0 0 0 3px #0b1319}}.gis-review-actions{{display:flex;justify-content:flex-end;gap:7px;flex-wrap:wrap;padding-top:10px}}.gis-review-actions button{{padding:7px 10px;font-size:12px}}
      .unsaved-site-modal-layer:not([hidden]){{display:flex}}.unsaved-site-modal{{max-width:560px}}
      @media(max-width:1250px){{.sites-workspace{{grid-template-columns:270px 1fr;height:auto}}.sites-tree-panel,.sites-editor-panel{{height:650px}}.sites-map-column{{grid-column:1/-1}}.sites-map-wrap{{height:430px}}}}@media(max-width:760px){{.sites-metrics,.sites-workspace{{grid-template-columns:1fr}}.sites-tree-panel{{height:430px}}.sites-editor-panel{{height:650px}}.sites-map-column{{grid-column:auto}}.sites-map-wrap{{height:360px}}}}
    </style>
    <script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@watergis/maplibre-gl-terradraw@1.0.1/dist/maplibre-gl-terradraw.umd.js"></script>
    <script>
    (() => {{
      const treeGroups=Array.from(document.querySelectorAll('[data-site-area-group]'));
      const storageKey='rainmapper-known-sites-collapsed-areas';
      let collapsed=[];
      try{{collapsed=JSON.parse(sessionStorage.getItem(storageKey)||'[]');if(!Array.isArray(collapsed))collapsed=[];}}catch(error){{collapsed=[];}}
      const setAreaExpanded=(group,expanded,persist=true)=>{{
        const toggle=group.querySelector('[data-site-area-toggle]'),children=group.querySelector('.site-area-children');
        if(!toggle||!children)return;
        toggle.setAttribute('aria-expanded',String(expanded));children.hidden=!expanded;
        const areaId=group.dataset.areaId||'';collapsed=collapsed.filter(id=>id!==areaId);if(!expanded&&areaId)collapsed.push(areaId);
        if(persist)sessionStorage.setItem(storageKey,JSON.stringify(collapsed));
      }};
      treeGroups.forEach(group=>{{const forceOpen=group.dataset.selected==='true';setAreaExpanded(group,forceOpen||!collapsed.includes(group.dataset.areaId),false);const toggle=group.querySelector('[data-site-area-toggle]');if(toggle)toggle.addEventListener('click',()=>setAreaExpanded(group,toggle.getAttribute('aria-expanded')!=='true'));}});
      document.querySelector('[data-expand-all-areas]')?.addEventListener('click',()=>{{collapsed=[];treeGroups.forEach(group=>setAreaExpanded(group,true,false));sessionStorage.setItem(storageKey,'[]');}});
      document.querySelector('[data-collapse-all-areas]')?.addEventListener('click',()=>{{collapsed=treeGroups.map(group=>group.dataset.areaId).filter(Boolean);treeGroups.forEach(group=>setAreaExpanded(group,false,false));sessionStorage.setItem(storageKey,JSON.stringify(collapsed));}});
      const selected = {str(has_selection).lower()};
      const mapNode = document.getElementById('known-site-map');
      if (!selected || !mapNode || !window.maplibregl) return;
      const geometryField = document.getElementById('known-site-geometry');
      let initialGeometry = {geometry_json};
      const parentGeometry = {parent_geometry_json};
      const satelliteLayerIds=['satellite','satellite-boundary','satellite-road-outline','satellite-road','satellite-minor-road','satellite-road-label','satellite-place-label'];
      const hybridLayerIds=['hybrid-roads','hybrid-labels'];
      const style = {{version:8,glyphs:'https://tiles.openfreemap.org/fonts/{{fontstack}}/{{range}}.pbf',sources:{{
        satellite:{{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'],tileSize:256,maxzoom:19,attribution:'Tiles &copy; Esri'}},
        hybridRoads:{{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}'],tileSize:256,maxzoom:19,attribution:'Roads &copy; Esri'}},
        hybridLabels:{{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}'],tileSize:256,maxzoom:19,attribution:'Labels &copy; Esri'}},
        openmaptiles:{{type:'vector',url:'https://tiles.openfreemap.org/planet',attribution:'OpenStreetMap contributors'}},
        terrainDem:{{type:'raster-dem',tiles:['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{{z}}/{{x}}/{{y}}.png'],tileSize:256,maxzoom:15,encoding:'terrarium',attribution:'Elevation tiles &copy; Mapzen'}},
        topo:{{type:'raster',tiles:['https://a.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png','https://b.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png','https://c.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png'],tileSize:256,maxzoom:17,attribution:'OpenStreetMap · OpenTopoMap'}}
      }},layers:[
        {{id:'satellite',type:'raster',source:'satellite'}},
        {{id:'satellite-boundary',type:'line',source:'openmaptiles','source-layer':'boundary',filter:['all',['!=',['get','maritime'],1],['<=',['get','admin_level'],6]],paint:{{'line-color':'rgba(255,255,255,.78)','line-dasharray':[2,2],'line-width':['interpolate',['linear'],['zoom'],5,.7,10,1.4,14,2.2]}}}},
        {{id:'satellite-road-outline',type:'line',source:'openmaptiles','source-layer':'transportation',filter:['match',['get','class'],['motorway','trunk','primary','secondary','tertiary'],true,false],layout:{{'line-cap':'round','line-join':'round'}},paint:{{'line-color':'rgba(0,0,0,.75)','line-width':['interpolate',['exponential',1.2],['zoom'],6,1.4,10,2.8,15,8]}}}},
        {{id:'satellite-road',type:'line',source:'openmaptiles','source-layer':'transportation',filter:['match',['get','class'],['motorway','trunk','primary','secondary','tertiary'],true,false],layout:{{'line-cap':'round','line-join':'round'}},paint:{{'line-color':['match',['get','class'],['motorway','trunk'],'#f6c453',['primary'],'#ffd37a','#fff'],'line-width':['interpolate',['exponential',1.2],['zoom'],6,.8,10,1.6,15,5]}}}},
        {{id:'satellite-minor-road',type:'line',source:'openmaptiles','source-layer':'transportation',minzoom:12,filter:['match',['get','class'],['minor','service','track'],true,false],layout:{{'line-cap':'round','line-join':'round'}},paint:{{'line-color':'rgba(255,255,255,.86)','line-width':['interpolate',['exponential',1.2],['zoom'],12,.6,16,3.2]}}}},
        {{id:'satellite-road-label',type:'symbol',source:'openmaptiles','source-layer':'transportation_name',minzoom:12,layout:{{'symbol-placement':'line','text-field':['coalesce',['get','name_en'],['get','name']],'text-font':['Noto Sans Regular'],'text-size':['interpolate',['linear'],['zoom'],12,11,15,13]}},paint:{{'text-color':'#fff','text-halo-color':'rgba(0,0,0,.8)','text-halo-width':1.4}}}},
        {{id:'satellite-place-label',type:'symbol',source:'openmaptiles','source-layer':'place',filter:['match',['get','class'],['country','state','city','town','village'],true,false],layout:{{'text-field':['coalesce',['get','name_en'],['get','name']],'text-font':['Noto Sans Bold'],'text-size':['interpolate',['linear'],['zoom'],4,11,8,14,12,18],'text-max-width':9}},paint:{{'text-color':'#fff','text-halo-color':'rgba(0,0,0,.9)','text-halo-width':1.8}}}},
        {{id:'hybrid-roads',type:'raster',source:'hybridRoads',layout:{{visibility:'none'}}}},
        {{id:'hybrid-labels',type:'raster',source:'hybridLabels',layout:{{visibility:'none'}}}},
        {{id:'topo',type:'raster',source:'topo',layout:{{visibility:'none'}}}}
      ]}};
      const map = new maplibregl.Map({{container:mapNode,style,center:[1.9,42.05],zoom:11,maxPitch:85}});
      map.addControl(new maplibregl.NavigationControl({{showCompass:false}}),'bottom-right');
      map.addControl(new maplibregl.ScaleControl({{maxWidth:100,unit:'metric'}}));
      let draw = null;
      let terrainEnabled = false;
      let lastGeometryValue=initialGeometry?JSON.stringify(initialGeometry):'';
      const sync = () => {{
        if (!draw || !geometryField) return;
        const collection = draw.getFeatures();
        const polygons = (collection.features || []).filter(f => ['Polygon','MultiPolygon'].includes(f.geometry && f.geometry.type));
        const geometry = polygons.length ? polygons[polygons.length - 1].geometry : null;
        const nextValue=geometry?JSON.stringify(geometry):'';geometryField.value=nextValue;
        if(nextValue!==lastGeometryValue){{lastGeometryValue=nextValue;geometryField.dispatchEvent(new Event('input',{{bubbles:true}}));}}
        updateDerived(geometry);
      }};
      const updateDerived = geometry => {{
        const centroidNode=document.getElementById('site-centroid'), areaNode=document.getElementById('site-area');
        if (!geometry) {{ centroidNode.textContent='-'; areaNode.textContent='-'; return; }}
        const rings=geometry.type==='Polygon'?geometry.coordinates:geometry.coordinates.flat(); const pts=rings.flat();
        if(!pts.length)return; const lng=pts.reduce((s,p)=>s+p[0],0)/pts.length,lat=pts.reduce((s,p)=>s+p[1],0)/pts.length;
        centroidNode.textContent=`${{lat.toFixed(6)}}, ${{lng.toFixed(6)}}`;
        const ring=rings[0]||[], meanLat=lat*Math.PI/180, earth=6371008.8; let sum=0;
        for(let i=0;i<ring.length-1;i++){{const x1=ring[i][0]*Math.PI/180*earth*Math.cos(meanLat),y1=ring[i][1]*Math.PI/180*earth,x2=ring[i+1][0]*Math.PI/180*earth*Math.cos(meanLat),y2=ring[i+1][1]*Math.PI/180*earth;sum+=x1*y2-x2*y1;}}
        const hectares=Math.abs(sum)/2/10000; areaNode.textContent=hectares<0.01?'< 0,01 ha':`${{hectares.toLocaleString('es-ES',{{maximumFractionDigits:2}})}} ha`;
      }};
      map.on('load', () => {{
        if(parentGeometry){{map.addSource('parent-site',{{type:'geojson',data:{{type:'Feature',properties:{{}},geometry:parentGeometry}}}});map.addLayer({{id:'parent-site-fill',type:'fill',source:'parent-site',paint:{{'fill-color':'#ecb34c','fill-opacity':0.08}}}});map.addLayer({{id:'parent-site-line',type:'line',source:'parent-site',paint:{{'line-color':'#ecb34c','line-width':2,'line-dasharray':[3,2]}}}});}}
        draw = new MaplibreTerradrawControl.MaplibreTerradrawControl({{modes:['render','polygon','select','delete-selection','delete'],open:true}});
        map.addControl(draw,'top-left');
        if (initialGeometry) {{
          const feature={{type:'Feature',geometry:initialGeometry,properties:{{mode:initialGeometry.type==='MultiPolygon'?'polygon':'polygon'}}}};
          try {{ draw.getTerraDrawInstance().addFeatures([feature]); }} catch(error) {{ console.warn('Cannot load saved site geometry',error); }}
          const coords=(initialGeometry.type==='Polygon'?initialGeometry.coordinates:initialGeometry.coordinates.flat()).flat();
          if(coords.length){{const bounds=new maplibregl.LngLatBounds();coords.forEach(p=>bounds.extend(p));map.fitBounds(bounds,{{padding:55,maxZoom:16}});}}
          updateDerived(initialGeometry);
        }}
        window.setInterval(sync,700);
      }});
      const layerToggle=document.getElementById('site-layer-toggle'),layerPanel=document.getElementById('site-layer-panel');
      layerToggle.addEventListener('click',()=>{{const open=layerPanel.hidden;layerPanel.hidden=!open;layerToggle.setAttribute('aria-expanded',String(open));}});
      layerPanel.querySelectorAll('[data-basemap]').forEach(button=>button.addEventListener('click',()=>{{const value=button.dataset.basemap,topo=value==='topographic',hybrid=value==='hybrid';satelliteLayerIds.forEach((id,index)=>map.setLayoutProperty(id,'visibility',topo||(hybrid&&index>0)?'none':'visible'));hybridLayerIds.forEach(id=>map.setLayoutProperty(id,'visibility',hybrid?'visible':'none'));map.setLayoutProperty('topo','visibility',topo?'visible':'none');layerPanel.querySelectorAll('button').forEach(item=>item.classList.toggle('active',item===button));layerPanel.hidden=true;layerToggle.setAttribute('aria-expanded','false');}}));
      document.getElementById('site-north-toggle').addEventListener('click',()=>map.easeTo({{bearing:0,duration:500}}));
      document.getElementById('site-terrain-toggle').addEventListener('click',event=>{{terrainEnabled=!terrainEnabled;map.setTerrain(terrainEnabled?{{source:'terrainDem',exaggeration:1}}:null);map.easeTo({{pitch:terrainEnabled?48:0,bearing:terrainEnabled?-8:0,duration:650}});event.currentTarget.textContent=terrainEnabled?'2D':'3D';event.currentTarget.setAttribute('aria-pressed',String(terrainEnabled));}});
      document.getElementById('site-draw-polygon').addEventListener('click',()=>draw&&draw.getTerraDrawInstance().setMode('polygon'));
      document.getElementById('site-edit-polygon').addEventListener('click',()=>draw&&draw.getTerraDrawInstance().setMode('select'));
      document.getElementById('site-use-centroid').addEventListener('click',()=>{{sync();const text=document.getElementById('site-centroid').textContent;if(text==='-')return;const parts=text.split(',');const form=geometryField.closest('form'),lat=form.querySelector('[name=lat]'),lon=form.querySelector('[name=lon]');lat.value=parts[0].trim();lon.value=parts[1].trim();lat.dispatchEvent(new Event('input',{{bubbles:true}}));}});
      document.getElementById('site-recover-gis').addEventListener('click',()=>{{sync();if(!geometryField.value){{document.getElementById('site-geometry-status').textContent='Dibuja un polígono antes de recuperar GIS/DEM.';return;}}const form=geometryField.closest('form');form.querySelector('[name=known_site_action]').value='preview_gis_dem';form.requestSubmit();}});
      document.getElementById('site-map-fullscreen').addEventListener('click',()=>mapNode.parentElement.requestFullscreen&&mapNode.parentElement.requestFullscreen());
      geometryField.closest('form').addEventListener('submit',sync);
      document.querySelectorAll('.sites-tabs button').forEach(button=>button.addEventListener('click',()=>{{document.querySelectorAll('.sites-tabs button').forEach(item=>item.classList.remove('active'));button.classList.add('active');const form=geometryField.closest('form'),details=form.querySelector('details');if(button.dataset.siteTab==='geometry')document.querySelector('.sites-map-card').scrollIntoView({{behavior:'smooth',block:'center'}});else if(button.dataset.siteTab==='environment'){{if(details)details.open=true;details&&details.scrollIntoView({{behavior:'smooth',block:'start'}});}}else if(button.dataset.siteTab==='notes'){{if(details)details.open=true;const notes=form.querySelector('[name=notes]');notes&&notes.focus();}}else if(details)details.open=false;}}));
      document.querySelectorAll('[data-gis-select]').forEach(button=>button.addEventListener('click',()=>{{document.querySelectorAll('#gis-dem-review [name=gis_apply_field]').forEach(input=>{{input.checked=button.dataset.gisSelect==='all'||(button.dataset.gisSelect==='empty'&&input.dataset.currentEmpty==='true');}});}}));
      const editorForm=document.querySelector('.sites-editor-body .catalog-entry-form');const unsavedModal=document.getElementById('unsaved-site-changes');let pendingNavigation='',allowUnload=false;let dirty=Boolean(editorForm&&editorForm.dataset.initialDirty==='true');
      if(editorForm){{editorForm.addEventListener('input',()=>dirty=true);editorForm.addEventListener('change',()=>dirty=true);editorForm.addEventListener('submit',()=>allowUnload=true);}}
      document.querySelector('#gis-dem-review form')?.addEventListener('submit',()=>allowUnload=true);
      document.querySelector('[data-gis-cancel]')?.addEventListener('click',()=>allowUnload=true);
      document.addEventListener('click',event=>{{const link=event.target.closest('a[href]');if(!link||link.hasAttribute('data-gis-cancel')||!dirty||!editorForm)return;const href=link.getAttribute('href')||'';if(!href||href.startsWith('#'))return;event.preventDefault();pendingNavigation=href;unsavedModal.hidden=false;}},true);
      unsavedModal?.querySelector('[data-unsaved-discard]').addEventListener('click',()=>{{if(pendingNavigation){{allowUnload=true;const separator=pendingNavigation.includes('?')?'&':'?';window.location.href=pendingNavigation+separator+'discard_gis_draft=1';}}}});
      unsavedModal?.querySelector('[data-unsaved-save]').addEventListener('click',()=>{{if(!editorForm)return;let next=editorForm.querySelector('[name=next_url]');if(!next){{next=document.createElement('input');next.type='hidden';next.name='next_url';editorForm.appendChild(next);}}next.value=pendingNavigation;editorForm.requestSubmit(editorForm.querySelector('[data-save-site]'));}});
      unsavedModal?.querySelectorAll('[data-unsaved-cancel]').forEach(button=>button.addEventListener('click',()=>{{unsavedModal.hidden=true;pendingNavigation='';}}));
      window.addEventListener('beforeunload',event=>{{if(!dirty||allowUnload)return;event.preventDefault();event.returnValue='';}});
    }})();
    </script>
    """


def _gis_review_modal(preview: dict[str, object] | None, selected_row: dict[str, object] | None, return_to: str, close_href: str) -> str:
    if not isinstance(preview, dict) or preview.get("draft") or not isinstance(preview.get("report"), dict) or not selected_row:
        return ""
    report = preview["report"]
    base_row = preview.get("base") if isinstance(preview.get("base"), dict) else selected_row
    kind = str(preview.get("kind", ""))
    site_id = str(preview.get("id", ""))
    altitude = selected_row.get("altitude") if isinstance(selected_row.get("altitude"), dict) else {}
    topography = selected_row.get("topography") if isinstance(selected_row.get("topography"), dict) else {}
    ecology = selected_row.get("ecology") if isinstance(selected_row.get("ecology"), dict) else {}
    gis = report.get("gis") if isinstance(report.get("gis"), dict) else {}
    fields = [
        ("altitude_min_m", label("ui.altitude_min"), altitude.get("min_m"), report.get("altitude_min_m"), "DEM 5 m"),
        ("altitude_max_m", label("ui.altitude_max"), altitude.get("max_m"), report.get("altitude_max_m"), "DEM 5 m"),
        ("slope_notes", label("ui.slope_notes"), topography.get("slope_notes"), f"Media {report.get('slope_mean_deg', '-')}°, {report.get('slope_min_deg', '-')}°-{report.get('slope_max_deg', '-')}°", "DEM 5 m"),
        ("aspect_ids", label("ui.aspect_ids"), topography.get("aspect_ids"), report.get("dominant_aspect_ids"), "DEM 5 m"),
        ("host_ids", label("ui.host_ids"), ecology.get("host_ids"), gis.get("host_ids"), "MVC50"),
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
        current_text = ", ".join(map(str, current)) if isinstance(current, list) else str(current or "-")
        proposed_text = ", ".join(map(str, proposed)) if isinstance(proposed, list) else str(proposed)
        discrepancy = current not in (None, [], "") and current_text != proposed_text
        checked = " checked" if current in (None, [], "") else ""
        rows.append(
            f'<tr class="{"gis-discrepancy" if discrepancy else ""}"><td><strong>{html.escape(field_label)}</strong></td>'
            f'<td>{html.escape(current_text)}</td><td>{html.escape(proposed_text)}<small>{html.escape(source)}</small></td>'
            f'<td><label class="gis-review-choice"><input type="checkbox" name="gis_apply_field" value="{_text(field)}" data-current-empty="{str(current in (None, [], "")).lower()}"{checked}><span>Aceptar GIS/DEM</span></label></td></tr>'
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
          <div class="gis-review-actions"><button type="button" data-gis-select="empty">Aceptar campos vacíos</button><button type="button" data-gis-select="all">Aceptar todo GIS/DEM</button><button type="button" data-gis-select="none">Mantener actuales</button><button class="primary">Aplicar selección</button></div>
        </form>
      </div>
    </div>
    """


def _site_observations_modal(modal_id: str, title: str, rows: list[dict[str, object]], close_href: str, abundance_labels: dict[str, str]) -> str:
    normalized_rows = []
    for row in sorted(rows, key=lambda item: str(item.get("observed_at", "")), reverse=True):
        normalized = dict(row)
        normalized["location"] = mushroom_profiles_ui.observation_location(row)
        abundance_id = str(row.get("flush_abundance", "") or "")
        normalized["flush_abundance_label"] = abundance_labels.get(abundance_id, abundance_id)
        normalized_rows.append(normalized)
    return mushroom_profiles_ui.render_evidence_observation_modal(
        modal_id,
        "",
        "",
        "v0",
        "hosts_forests",
        title,
        normalized_rows,
        modal_title="Observaciones del setal",
        modal_help="Observaciones asociadas a esta área o microárea.",
        close_href_override=close_href,
        observation_return_to=close_href + f"#{modal_id}",
    )


def render_page(payload: dict[str, object], observations_payload: dict[str, object], query: dict[str, list[str]], flash: str = "", gis_preview: dict[str, object] | None = None, catalogs_payload: dict[str, object] | None = None) -> str:
    kind = (query.get("kind") or ["micro_area"])[0]
    selected_id = (query.get("id") or [""])[0]
    search = (query.get("q") or [""])[0].strip().casefold()
    return_to = (query.get("return_to") or ["./profiles?section=observations"])[0]
    areas = [row for row in payload.get("areas", []) if isinstance(row, dict)] if isinstance(payload.get("areas"), list) else []
    micro_areas = [row for row in payload.get("micro_areas", []) if isinstance(row, dict)] if isinstance(payload.get("micro_areas"), list) else []
    area_names = {str(row.get("area_id", "")): str(row.get("name", "")) for row in areas}
    counts = mushroom_known_sites.observation_reference_counts(observations_payload)
    observation_rows = mushroom_profiles_ui.observations_from_payload(observations_payload)
    catalog_groups = catalogs_payload.get("catalogs") if isinstance(catalogs_payload, dict) else {}
    abundance_labels = mushroom_profiles_ui.catalog_label_map(catalog_groups if isinstance(catalog_groups, dict) else {}, "observation_flush_abundance")
    current_url = query_url(kind, selected_id, (query.get("q") or [""])[0], return_to)
    observation_modals = []

    rows_html = []
    for area_index, area in enumerate(sorted(areas, key=lambda row: str(row.get("name", "")).casefold())):
        area_id = str(area.get("area_id", ""))
        if search and search not in f"{area_id} {area.get('name', '')}".casefold():
            area_matches = False
        else:
            area_matches = True
        children = [row for row in micro_areas if str(row.get("area_id", "")) == area_id]
        if area_matches or any(search in f"{row.get('micro_area_id', '')} {row.get('name', '')}".casefold() for row in children):
            selected_class = " selected-row" if kind == "area" and selected_id == area_id else ""
            status_text = label("ui.archived") if area.get("archived") else label("ui.active")
            area_micro_ids = {str(child.get("micro_area_id", "")) for child in children}
            area_observations = [row for row in observation_rows if str(row.get("micro_area_id", "")) in area_micro_ids]
            area_modal_id = f"site-observations-area-{area_id}"
            area_children_id = f"site-area-children-{area_index}"
            status_class = " archived" if area.get("archived") else ""
            group_selected = kind == "area" and selected_id == area_id or kind == "micro_area" and any(str(child.get("micro_area_id", "")) == selected_id for child in children)
            rows_html.append(f'<section class="site-area-group" data-site-area-group data-area-id="{_text(area_id)}" data-selected="{str(group_selected).lower()}"><div class="site-tree-row area{selected_class}"><button class="site-tree-toggle" type="button" data-site-area-toggle aria-expanded="true" aria-controls="{area_children_id}" title="Plegar o desplegar microáreas"><span aria-hidden="true">▾</span></button><a class="site-tree-area-link" href="{query_url("area", area_id, return_to=return_to)}"><strong>{html.escape(str(area.get("name", area_id)))}</strong></a><span class="site-status{status_class}">{html.escape(status_text)}</span><a class="site-count" href="#{_text(area_modal_id)}" title="Ver observaciones">{len(area_observations)}</a></div><div class="site-area-children" id="{area_children_id}">')
            if area_observations:
                observation_modals.append(_site_observations_modal(area_modal_id, str(area.get("name", area_id)), area_observations, current_url, abundance_labels))
            for micro in sorted(children, key=lambda row: str(row.get("name", "")).casefold()):
                micro_id = str(micro.get("micro_area_id", ""))
                if search and search not in f"{area_id} {area.get('name', '')} {micro_id} {micro.get('name', '')}".casefold():
                    continue
                selected_class = " selected-row" if kind == "micro_area" and selected_id == micro_id else ""
                status_text = label("ui.archived") if micro.get("archived") else label("ui.active")
                micro_observations = [row for row in observation_rows if str(row.get("micro_area_id", "")) == micro_id]
                micro_modal_id = f"site-observations-micro-{micro_id}"
                status_class = " archived" if micro.get("archived") else ""
                rows_html.append(f'<div class="site-tree-row micro{selected_class}"><a class="site-tree-main" href="{query_url("micro_area", micro_id, return_to=return_to)}"><span class="site-tree-icon">↳</span><strong>{html.escape(str(micro.get("name", micro_id)))}</strong></a><span class="site-status{status_class}">{html.escape(status_text)}</span><a class="site-count" href="#{_text(micro_modal_id)}" title="Ver observaciones">{len(micro_observations)}</a></div>')
                if micro_observations:
                    observation_modals.append(_site_observations_modal(micro_modal_id, f"{area_names.get(area_id, area_id)} · {micro.get('name', micro_id)}", micro_observations, current_url, abundance_labels))
            rows_html.append('</div></section>')

    selected_area = next((row for row in areas if str(row.get("area_id", "")) == selected_id), None) if kind == "area" else None
    selected_micro = next((row for row in micro_areas if str(row.get("micro_area_id", "")) == selected_id), None) if kind == "micro_area" else None
    if isinstance(gis_preview, dict) and gis_preview.get("kind") == kind and gis_preview.get("id") == selected_id and isinstance(gis_preview.get("draft") or gis_preview.get("base"), dict):
        preview_row = gis_preview.get("draft") or gis_preview.get("base")
        if kind == "area":
            selected_area = preview_row
        else:
            selected_micro = preview_row
    detail = _area_form(selected_area, return_to=return_to, geometry_id="known-site-geometry") if selected_area else _micro_form(selected_micro, payload, return_to=return_to, geometry_id="known-site-geometry") if selected_micro else f'<div class="catalog-empty-detail">{html.escape(label("ui.select_area_or_micro_area"))}</div>'
    selected_row = selected_area or selected_micro
    selected_name = str(selected_row.get("name", "")) if selected_row else ""
    parent_name = area_names.get(str(selected_micro.get("area_id", "")), "") if selected_micro else ""
    breadcrumb = f'{html.escape(parent_name)} <span>/</span> <strong>{html.escape(selected_name)}</strong>' if parent_name else f'<strong>{html.escape(selected_name)}</strong>'
    geometry = selected_row.get("geometry") if isinstance(selected_row, dict) and isinstance(selected_row.get("geometry"), dict) else None
    geometry_json = json.dumps(geometry, ensure_ascii=False).replace("<", "\\u003c") if geometry else "null"
    parent_area = next((row for row in areas if selected_micro and str(row.get("area_id", "")) == str(selected_micro.get("area_id", ""))), None)
    parent_geometry = parent_area.get("geometry") if isinstance(parent_area, dict) and isinstance(parent_area.get("geometry"), dict) else None
    parent_geometry_json = json.dumps(parent_geometry, ensure_ascii=False).replace("<", "\\u003c") if parent_geometry else "null"
    archive_action = ""
    if selected_area:
        action_class = "warning" if selected_area.get("archived") else "danger"
        archive_action = f'<form method="post"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="hidden" name="known_site_action" value="toggle_area_archive"><input type="hidden" name="area_id" value="{_text(selected_id)}"><button class="secondary {action_class}">{html.escape(label("ui.restore") if selected_area.get("archived") else label("ui.archive"))}</button></form>'
        if selected_area.get("archived"):
            archive_action += f'<form method="post" onsubmit="return confirm(\'Esta acción borrará definitivamente el área {html.escape(selected_id, quote=True)}. ¿Continuar?\')"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="hidden" name="known_site_action" value="delete_area"><input type="hidden" name="area_id" value="{_text(selected_id)}"><button class="danger">Borrar definitivamente</button></form>'
    elif selected_micro:
        action_class = "warning" if selected_micro.get("archived") else "danger"
        archive_action = f'<form method="post"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="hidden" name="known_site_action" value="toggle_micro_area_archive"><input type="hidden" name="micro_area_id" value="{_text(selected_id)}"><button class="secondary {action_class}">{html.escape(label("ui.restore") if selected_micro.get("archived") else label("ui.archive"))}</button></form>'
        if selected_micro.get("archived"):
            archive_action += f'<form method="post" onsubmit="return confirm(\'Esta acción borrará definitivamente la microárea {html.escape(selected_id, quote=True)}. ¿Continuar?\')"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="hidden" name="known_site_action" value="delete_micro_area"><input type="hidden" name="micro_area_id" value="{_text(selected_id)}"><button class="danger">Borrar definitivamente</button></form>'

    return f"""
    <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@watergis/maplibre-gl-terradraw@1.0.1/dist/maplibre-gl-terradraw.css">
    <div class="catalog-toolbar sites-top-toolbar">
      <a class="button-link" href="{_text(return_to)}">{html.escape(label('ui.back'))}</a>
      <a class="button-link" href="{query_url(kind, selected_id, (query.get('q') or [''])[0], return_to)}">Actualizar</a>
      <a class="button-link" href="./catalogs">Catálogos de referencia</a>
      <a class="button-link" href="./gis-mappings">Mapeos GIS</a>
      <a class="button-link" href="./profiles">Especies</a>
    </div>
    <div class="sites-page-head"><div><h1>{html.escape(label('ui.known_sites'))}</h1><p>{html.escape(label('ui.known_sites_help'))}</p></div></div>
    {f'<div class="catalog-alert">{html.escape(flash)}</div>' if flash else ''}
    <div class="sites-metrics">
      <article><span>{html.escape(label('ui.areas'))}</span><strong>{len(areas)}</strong><small>{html.escape(label('ui.active')).lower()}</small></article>
      <article><span>{html.escape(label('ui.micro_areas'))}</span><strong>{len(micro_areas)}</strong><small>{html.escape(label('ui.active')).lower()}</small></article>
      <article><span>{html.escape(label('ui.linked_observations'))}</span><strong>{sum(counts.values())}</strong><small>en total</small></article>
    </div>
    <div class="sites-workspace">
      <aside class="sites-tree-panel">
        <div class="sites-create-actions"><a class="button-link" href="#new-area">+ {html.escape(label('ui.new_area'))}</a><a class="button-link primary" href="#new-micro-area">+ {html.escape(label('ui.new_micro_area'))}</a></div>
        <form class="sites-search" method="get"><input type="hidden" name="return_to" value="{_text(return_to)}"><input type="search" name="q" value="{_text((query.get('q') or [''])[0])}" placeholder="Buscar setal..."></form>
        <div class="sites-tree-actions"><button type="button" data-collapse-all-areas>Plegar todas</button><button type="button" data-expand-all-areas>Desplegar todas</button></div>
        <nav class="sites-tree">{''.join(rows_html) or f'<p class="meta">{html.escape(label("ui.no_known_sites"))}</p>'}</nav>
        <footer>Mostrando {len(micro_areas)} microáreas en {len(areas)} áreas</footer>
      </aside>
      <main class="sites-editor-panel">
        <header class="sites-editor-head"><div>{breadcrumb or html.escape(label('ui.select_area_or_micro_area'))}</div>{f'<span class="site-kind">{"Área" if selected_area else "Microárea"}</span><span class="site-status{" archived" if selected_row.get("archived") else ""}">{html.escape(label("ui.archived") if selected_row.get("archived") else label("ui.active"))}</span>' if selected_row else ''}</header>
        <div class="sites-tabs"><button type="button" class="active" data-site-tab="general">General</button><button type="button" data-site-tab="geometry">Geometría</button><button type="button" data-site-tab="environment">Entorno</button><button type="button" data-site-tab="notes">Notas y acceso</button></div>
        <div class="sites-editor-body">{detail}</div>
        <div class="sites-archive">{archive_action}</div>
      </main>
      <aside class="sites-map-column">
        <section class="sites-map-card">
          <header><strong>Mapa / geometría</strong><button type="button" id="site-map-fullscreen" title="Amplía el mapa para dibujar o revisar el polígono con más espacio">Ver en mapa completo</button></header>
          <div class="sites-map-wrap"><div id="known-site-map"></div><div class="sites-map-empty" {'hidden' if selected_row else ''}>Selecciona un área o microárea</div><div class="site-map-controls"><button class="site-map-control site-layer-toggle" id="site-layer-toggle" type="button" aria-expanded="false" aria-controls="site-layer-panel" title="Mapa base"><svg aria-hidden="true" viewBox="0 0 24 24"><polygon points="12 2 22 7 12 12 2 7"></polygon><polyline points="22 12 12 17 2 12"></polyline><polyline points="22 17 12 22 2 17"></polyline></svg></button><button class="site-map-control" id="site-terrain-toggle" type="button" aria-pressed="false" title="Activar relieve 3D">3D</button><button class="site-map-control site-north-toggle" id="site-north-toggle" type="button" title="Orientar al norte"><span aria-hidden="true"></span></button><div class="site-layer-panel" id="site-layer-panel" hidden><button class="active" type="button" data-basemap="satellite">Satélite+</button><button type="button" data-basemap="hybrid">Híbrido</button><button type="button" data-basemap="topographic">Topográfico</button></div></div></div>
          <div class="geometry-actions"><button type="button" class="primary" id="site-draw-polygon" title="Dibuja el límite del área o microárea sobre el mapa">Dibujar polígono</button><button type="button" id="site-edit-polygon" title="Permite mover los vértices del polígono actual">Editar vértices</button><button type="button" id="site-use-centroid" title="Rellena latitud y longitud con el punto central calculado del polígono">Rellenar ubicación central</button><button type="button" id="site-recover-gis" title="Propone altitud, pendiente, orientación y entorno a partir del polígono"{' disabled' if not selected_row else ''}>Recuperar GIS/DEM</button></div>
          <p class="geometry-status" id="site-geometry-status">{'Geometría guardada. Puedes editar sus vértices.' if geometry else 'Sin geometría. Dibuja el límite del setal en el mapa.'}</p>
        </section>
        <section class="sites-derived-card"><header><strong>Datos derivados de la geometría</strong></header><div><span>Centroide</span><strong id="site-centroid">-</strong><span>Superficie aproximada</span><strong id="site-area">-</strong></div></section>
      </aside>
    </div>
    <div id="new-area" class="modal-layer"><a class="modal-backdrop" href="#"></a><div class="modal-card modal-card-wide">{_area_form({}, create=True, return_to=return_to, geometry_id="new-area-geometry")}</div></div>
    <div id="new-micro-area" class="modal-layer"><a class="modal-backdrop" href="#"></a><div class="modal-card modal-card-wide">{_micro_form({}, payload, create=True, return_to=return_to, geometry_id="new-micro-geometry")}</div></div>
    <div id="unsaved-site-changes" class="modal-layer unsaved-site-modal-layer" hidden><button class="modal-backdrop" type="button" data-unsaved-cancel aria-label="Cancelar"></button><div class="modal-card unsaved-site-modal"><h2>Cambios sin guardar</h2><p>Has modificado este setal. ¿Qué quieres hacer antes de abrir otro?</p><div class="profile-action-bar"><button type="button" class="danger" data-unsaved-discard>Descartar cambios</button><button type="button" data-unsaved-cancel>Cancelar</button><button type="button" class="primary" data-unsaved-save>Guardar y continuar</button></div></div></div>
    {_gis_review_modal(gis_preview, selected_row, return_to, current_url)}
    {mushroom_profiles_ui.observation_site_map_assets() if observation_modals else ''}
    {''.join(observation_modals)}
    {_known_sites_map_assets(geometry_json, parent_geometry_json, bool(selected_row))}
    """
