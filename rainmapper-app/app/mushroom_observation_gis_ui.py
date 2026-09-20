"""Draft-only controls for explicit observation GIS/DEM recovery."""
import html
import json
from pathlib import Path

from rainmapper_core.mushroom_gis_recovery import valid_recovery


def controls(row):
    location = row.get('location') or {}
    try:
        recovery = valid_recovery((row.get('site_context') or {}).get('gis_recovery'), location)
    except (ValueError, TypeError):
        recovery = {}
    encoded = html.escape(json.dumps(recovery, ensure_ascii=False), quote=True)
    return f'''
      <button type="button" class="secondary" data-observation-gis-recover>Recuperar GIS / DEM</button>
      <input type="hidden" name="gis_recovery_json" value="{encoded}">
      <span data-observation-gis-status role="status" aria-live="polite"></span>'''


def script():
    return '''<style>
      .observation-gis-dialog {background:var(--card,#fff);color:var(--fg,#18232c);border:1px solid var(--line,#ccd5dd);border-radius:12px;padding:20px;width:min(960px,calc(100vw - 40px));max-height:calc(100dvh - 40px);box-sizing:border-box;overflow:auto;}
      .observation-gis-dialog::backdrop {background:rgba(0,0,0,.6);}
      .observation-gis-dialog header {display:flex;align-items:center;justify-content:space-between;gap:16px;}
      .observation-gis-dialog h2 {margin:0;}
      .observation-gis-dialog .gis-review-scroll {overflow-x:auto;}
      .observation-gis-dialog table {width:100%;border-collapse:collapse;}
      .observation-gis-dialog th,.observation-gis-dialog td {padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line,#ccd5dd);}
      .observation-gis-dialog small {display:block;margin-top:4px;opacity:.75;}
      .observation-gis-dialog .gis-review-actions {display:flex;flex-wrap:wrap;gap:10px;margin-top:16px;}
      .observation-form [data-observation-gis-status] {grid-column:1/-1;white-space:normal;min-width:0;font-size:.85em;}
      .observation-form [data-observation-gis-status]:empty {display:none;}
      .observation-form .gis-selection-legend {font-size:12px;color:var(--muted,#55616a);margin:0 0 10px;}
      .observation-form .month-toggle.gis-selected input + .month-chip.host-chip,
      .observation-form .catalog-toggle.gis-selected input + .catalog-chip {background:#166b62;color:#fff;border-color:#54d6be;opacity:1;}
      .observation-form label.gis-selected > span::after {content:' ✓ GIS';font-size:.85em;font-weight:700;}
    </style><script>''' + Path(__file__).with_name('observation-gis.js').read_text(encoding='utf-8') + '</script>'


def summary(row, catalogs, names):
    try:
        recovery = valid_recovery((row.get('site_context') or {}).get('gis_recovery'), row.get('location') or {})
    except (ValueError, TypeError):
        return ''
    if not recovery:
        return ''
    from rainmapper_core.mushroom_gis_recovery import FIELDS
    labels = {'host_ids':'Hosts', 'forest_type_ids':'Bosque',
              'soil_tendency_ids':'Suelo', 'habitat_feature_ids':'Hábitat'}
    rows = []
    for key, ids in recovery['values'].items():
        text = names(catalogs, FIELDS[key], ids)
        rows.append('<p><strong>GIS · ' + labels[key] + '</strong>: ' + html.escape(text) + '</p>')
    return '<div class="observation-gis-summary">' + ''.join(rows) + '</div>'


def map_assets():
    return '''<style>
      .observation-map-control.observation-gis-toggle {display:flex;flex-direction:column;gap:0;line-height:1.05;font-size:11px;}
      .observation-gis-toggle[aria-pressed="true"] {background:var(--accent,#03a9f4);color:#fff;}
      .evidence-map-modal.gis-inspecting > .modal-header {grid-template-columns:minmax(240px,1fr) auto minmax(300px,1fr) auto;gap:16px;}
      .evidence-map-modal.gis-inspecting > .modal-header > div:first-child {min-width:0;max-width:100%;}
      .evidence-map-modal.gis-inspecting .observation-coordinate-toolbar {display:flex;flex-wrap:wrap;}
      .evidence-map-modal.gis-inspecting > .modal-header > .observation-map-gis-panel {grid-column:3;}
      .evidence-map-modal.gis-inspecting > .modal-header > [data-modal-history-close] {grid-column:4;}
      .observation-map-gis-panel {color:var(--fg,#18232c);background:var(--card,#fff);border:1px solid var(--line,#ccd5dd);border-radius:8px;padding:10px;max-height:280px;overflow:auto;min-width:0;font-size:13px;line-height:1.35;}
      .observation-map-gis-panel[hidden] {display:none;}
      .observation-map-gis-panel h3,.observation-map-gis-panel p {margin:0 0 6px;}
      .observation-map-gis-panel dl {display:grid;grid-template-columns:auto minmax(0,1fr);gap:5px 12px;margin:8px 0;}
      .observation-map-gis-panel dt {font-weight:600;}
      .observation-map-gis-panel dd {margin:0;overflow-wrap:anywhere;}
      .observation-map-gis-panel small {display:block;color:var(--muted,#55616a);}
      @media(max-width:1000px) {
        .evidence-map-modal.gis-inspecting > .modal-header {grid-template-columns:minmax(0,1fr) auto;}
        .evidence-map-modal.gis-inspecting > .modal-header > .observation-map-photo-strip {grid-column:1;grid-row:2;justify-self:start;}
        .evidence-map-modal.gis-inspecting > .modal-header > .observation-map-gis-panel {grid-column:2;grid-row:2;max-width:48vw;}
        .evidence-map-modal.gis-inspecting > .modal-header > [data-modal-history-close] {grid-column:2;grid-row:1;}
      }
      @media(max-width:600px) {
        .evidence-map-modal.gis-inspecting > .modal-header > .observation-map-gis-panel {grid-column:1 / -1;grid-row:3;max-width:none;}
      }
    </style><script>''' + Path(__file__).with_name('observation-map-gis.js').read_text(encoding='utf-8') + '</script>'
