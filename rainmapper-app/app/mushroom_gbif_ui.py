"""GBIF import maintenance UI and HTTP adapter."""
import html
import json
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rainmapper_core import mushroom_gbif_import as gbif, mushroom_gbif_sites as sites, mushroom_known_sites as known

STAGE_LOCK = threading.Lock()


def precision_help(row, label):
    location = row.get("location") or {}
    origin = location.get("precision_origin")
    if origin == "assumed_unknown_500m":
        key = "uncertainty_assigned"
    elif origin == "declared":
        key = "uncertainty_declared"
    elif location.get("precision_m") is None or origin == "legacy_default_zero":
        key = "uncertainty_legacy"
    else:
        key = "uncertainty_manual"
    return html.escape(label("ui.gbif_" + key))


def provenance(row, label):
    ext = row.get("external_source") or {}
    if ext.get("provider") != "gbif":
        return ""
    original = ext.get("original") or {}
    entries = [("GBIF ID", ext.get("gbif_id")),
               (label("ui.gbif_original_author"), original.get("recordedBy")),
               (label("ui.gbif_original_dataset"), original.get("datasetName")),
               (label("ui.gbif_original_uncertainty"), ext.get("coordinate_uncertainty_m") if ext.get("coordinate_uncertainty_m") is not None else label("ui.gbif_unknown")),
               (label("ui.gbif_original_license"), original.get("license"))]
    for index, media in enumerate(row.get("media") or []):
        attribution = media.get("attribution")
        if attribution:
            entries.append((label("ui.gbif_photos") + f" {index+1}", " · ".join(str(attribution.get(k) or "—") for k in ("creator", "rightsHolder", "license"))))
    content = "".join(f"<dt>{html.escape(str(k))}</dt><dd>{html.escape(str(v or '—'))}</dd>" for k, v in entries)
    return f'<details><summary>{html.escape(label("ui.gbif_provenance"))}</summary><dl>{content}</dl></details>'


def render(label):
    labels = {key: label("ui.gbif_" + key) for key in (
        "auto_sites", "auto_sites_help", "sites_planning", "sites_prepare", "sites_review", "sites_confirm",
        "sites_back", "sites_area_created", "sites_area_expanded", "sites_micro_created", "sites_name",
        "sites_action", "sites_assignments", "error_sites_geometry", "sites_soil_pending",
        "title", "help", "choose", "preview", "accept", "cancel", "all", "none", "new", "duplicate",
        "conflict", "invalid", "photos", "assigned", "busy", "done", "rejected", "created", "skipped",
        "import_details", "no_selection", "unlicensed", "close", "pending", "resume", "quality",
        "keep", "replace", "replaced", "replacement_help", "archived", "error_changed",
        "error_invalid", "error_limit", "error_species", "error_date", "error_presence", "error_coordinates",
        "error_uncertainty", "error_photo", "error_staging", "error_space", "error_owner", "error_conflict",
        "error_validation", "error_network", "preparing", "saving", "gis_gaps", "auto_prepare", "error_preparation",
    )}
    data = json.dumps(labels, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<style>
      #gbif-import-dialog {{box-sizing:border-box;width:min(1020px,calc(100vw - 32px));height:min(800px,calc(100vh - 40px));height:min(800px,calc(100dvh - 40px));max-height:calc(100vh - 40px);padding:20px;overflow:hidden;border-radius:12px;background:var(--card,#fff);color:var(--fg,#18232c);}}
      #gbif-import-dialog[open] {{display:flex;flex-direction:column;gap:12px;}}
      #gbif-import-dialog [hidden] {{display:none!important;}}
      #gbif-import-dialog h2,#gbif-import-status {{margin:0;}}
      #gbif-import-dialog details {{max-height:24vh;overflow:auto;}}
      #gbif-import-dialog details p {{margin:8px 0;font-size:13px;}}
      #gbif-import-dialog .gbif-upload {{display:flex;gap:10px;align-items:end;flex-wrap:wrap;}}
      #gbif-import-dialog .gbif-upload label {{flex:1;min-width:200px;}}
      #gbif-import-dialog input[type=file] {{width:100%;box-sizing:border-box;}}
      #gbif-import-dialog>header,#gbif-import-dialog>.gbif-upload,#gbif-import-dialog>.gbif-status,#gbif-import-dialog>footer {{flex:none;}}
      #gbif-import-progress {{width:100%;height:12px;}}
      #gbif-import-pending {{max-height:100px;overflow:auto;}}
      #gbif-import-review {{display:flex;flex-direction:column;flex:1;min-height:0;gap:8px;}}
      #gbif-import-dialog .gbif-table-scroll {{overflow:auto;min-height:0;flex:1;}}
      #gbif-import-dialog table {{width:100%;border-collapse:collapse;}}
      #gbif-import-dialog th,#gbif-import-dialog td {{text-align:left;padding:10px 8px;vertical-align:middle;}}
      #gbif-import-dialog th:first-child,#gbif-import-dialog td:first-child,#gbif-import-dialog th:nth-child(6),#gbif-import-dialog td:nth-child(6) {{text-align:center;}}
      #gbif-import-dialog thead th {{position:sticky;top:0;background:var(--card,#fff);z-index:1;}}
      #gbif-import-dialog footer {{display:flex;flex-wrap:wrap;gap:8px;margin-top:auto;border-top:1px solid var(--line,#506070);padding-top:12px;}}
      #gbif-import-sites-plan {{flex:1;min-height:0;overflow:auto;}}
      #gbif-import-dialog .gbif-auto-sites {{display:block;flex:none;font-size:13px;}}
      #gbif-import-auto-sites {{display:inline-block;width:16px;height:16px;vertical-align:middle;margin:0 6px 0 0;}}
      #gbif-import-dialog .gbif-auto-sites small {{display:block;color:var(--muted);}}
      #gbif-import-sites-plan svg {{width:100%;height:180px;background:var(--bg);border:1px solid var(--line);}}
      #gbif-import-dialog .gbif-selection {{display:flex;flex-wrap:wrap;gap:8px;}}
    </style><button type="button" class="secondary" id="gbif-import-open">{html.escape(labels['title'])}</button>
      <dialog id="gbif-import-dialog">
        <header><h2>{html.escape(labels['title'])}</h2>
          <details><summary>{html.escape(labels['import_details'])}</summary>
            <p>{html.escape(labels['help'])}</p><p>{html.escape(labels['quality'])}</p>
            <p>{html.escape(labels['replacement_help'])}</p><p>{html.escape(labels['auto_prepare'])}</p>
          </details>
        </header>
        <div class="gbif-upload"><label>{html.escape(labels['choose'])} <input id="gbif-import-file" type="file" accept=".zip,application/zip"></label>
          <button type="button" id="gbif-import-preview">{html.escape(labels['preview'])}</button></div>
        <label class="gbif-auto-sites"><input type="checkbox" id="gbif-import-auto-sites"> {html.escape(labels["auto_sites"])}<small>{html.escape(labels["auto_sites_help"])}</small></label>
        <section id="gbif-import-sites-plan" hidden></section>
        <div class="gbif-status"><p id="gbif-import-status" role="status" aria-live="polite"></p><progress id="gbif-import-progress" hidden></progress></div>
        <div id="gbif-import-pending"></div>
        <div id="gbif-import-review" hidden>
          <div class="gbif-selection"><button type="button" id="gbif-import-all">{html.escape(labels['all'])}</button>
            <button type="button" id="gbif-import-none">{html.escape(labels['none'])}</button></div>
          <div class="gbif-table-scroll"><table><thead><tr><th>✓</th><th>GBIF</th><th>{html.escape(label('species_id'))}</th><th>{html.escape(label('observed_at'))}</th><th>{html.escape(label('location.precision_m'))}</th><th>{html.escape(labels['photos'])}</th><th>{html.escape(label('validation_status'))}</th></tr></thead><tbody id="gbif-import-rows"></tbody></table></div>
        </div>
        <footer><button type="button" id="gbif-import-accept" hidden>{html.escape(labels['accept'])}</button>
          <button type="button" id="gbif-import-cancel">{html.escape(labels['cancel'])}</button>
          <button type="button" id="gbif-import-close">{html.escape(labels['close'])}</button></footer>
      </dialog><script>window.gbifImportLabels={data};</script><script>{Path(__file__).with_name('observation-gbif-import.js').read_text()}</script>'''


def handle(handler, store, mutation_lock, archived_loader):
    # Same trusted maintenance context as HA controls; map read permission is insufficient.
    if handler.headers.get("X-Rainmapper-GBIF") != "1":
        handler.send_json(403, {"ok": False, "error": "owner"})
        return
    if handler.trusted_worker_control_request():
        owner = handler.headers.get("X-Remote-User-Id", "local-maintenance")
    else:
        user = handler.require_admin_api()
        if not user:
            return
        owner = str(user.get("user_id") or user.get("username") or user.get("id"))
    action = parse_qs(urlparse(handler.path).query).get("action", [""])[0]
    handler.close_connection = True
    if not STAGE_LOCK.acquire(blocking=False):
        handler.send_json(409, {"ok": False, "error": "busy"})
        return
    try:
        if action == "upload":
            token, package = gbif.receive(store, handler.iter_artifact_request_body(), owner)
            with mutation_lock:
                rows = gbif.preview(package, store.load("observations")["observations"], archived_loader(store)["observations"])
            handler.send_json(200, {"ok": True, "token": token, "rows": rows})
            return
        payload = json.loads(handler.read_request_body(max_bytes=32768) or b"{}")
        if action == "pending":
            pending = []
            root = gbif.stage_root(store)
            for path in root.iterdir() if root.exists() else []:
                if not path.is_dir():
                    continue
                try:
                    target, state = gbif.load_stage(store, path.name, owner)
                except (OSError, ValueError):
                    continue
                if state["status"] != "complete":
                    pending.append({"token": path.name, "status": state["status"]})
            handler.send_json(200, {"ok": True, "pending": pending})
        elif action == "resume":
            target, state = gbif.load_stage(store, payload.get("token"), owner)
            if state["status"] != "ready":
                raise gbif.ImportError("invalid")
            package = gbif.strict_json((target / "preview.json").read_bytes())
            with mutation_lock:
                rows = gbif.preview(package, store.load("observations")["observations"], archived_loader(store)["observations"])
            handler.send_json(200, {"ok": True, "token": payload["token"], "rows": rows})
        elif action == "cancel":
            with mutation_lock, known.MUTATION_LOCK:
                gbif.cancel(store, payload.get("token"), owner)
            handler.send_json(200, {"ok": True})
        elif action == "prepare":
            result = gbif.prepare_record(store, payload.get("token"), owner, payload.get("gbif_id"))
            handler.send_json(200, {"ok": True, **result})
        elif action == "plan_sites":
            with mutation_lock, known.MUTATION_LOCK:
                target, state = gbif.load_stage(store, payload.get("token"), owner)
                if state.get("status") != "ready":
                    raise gbif.ImportError("invalid")
                result = sites.plan(store, target, gbif.staged_package(target), payload.get("accepted"),
                                    payload.get("replacements", {}), archived_loader(store)["observations"])
            handler.send_json(200, {"ok": True, **result})
        elif action == "prepare_site":
            target, state = gbif.load_stage(store, payload.get("token"), owner)
            if state.get("status") != "ready":
                raise gbif.ImportError("invalid")
            result = sites.prepare_site(store, target, payload.get("plan_id"), payload.get("site_id"))
            handler.send_json(200, {"ok": True, **result})
        elif action == "commit":
            with mutation_lock:
                result = gbif.commit(store, payload.get("token"), owner, payload.get("accepted"), archived_loader(store)["observations"], payload.get("replacements"), require_prepared=True, sites_plan_id=payload.get("sites_plan_id"), site_names=payload.get("site_names"))
            handler.send_json(200, {"ok": True, **result})
        else:
            raise gbif.ImportError("invalid")
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc) in {"sites_geometry", "changed", "invalid", "limit", "preparation"} or isinstance(exc, gbif.ImportError) else "invalid"
        handler.send_json(422, {"ok": False, "error": code})
    finally:
        STAGE_LOCK.release()
