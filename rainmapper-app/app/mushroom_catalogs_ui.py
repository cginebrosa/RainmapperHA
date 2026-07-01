"""Server-rendered UI helpers for mushroom reference catalog maintenance.

This module is intentionally presentation-focused. The Home Assistant web
server owns routing, POST handling, persistence and validation orchestration;
this file owns the HTML helpers needed to render the reference catalog hub.
Keeping catalog rendering here prevents `web_server.py` from absorbing every
maintenance-screen iteration.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.parse import urlencode


CATALOG_ID_PREFIXES = {
    "trophic_modes": "trophic_",
    "host_taxa": "host_",
    "forest_types": "forest_",
    "soil_types": "soil_",
    "lithology_types": "lith_",
    "aspects": "aspect_",
    "season_patterns": "season_",
    "habitat_features": "feature_",
    "observation_flush_abundance": "",
    "observation_validation_statuses": "",
    "observation_calibration_uses": "",
    "observation_exclusion_reasons": "",
    "observation_source_types": "",
    "observer_expertise_levels": "",
    "observation_location_sources": "",
    "observation_altitude_sources": "",
}

UI_LANGUAGE = os.environ.get("RAINMAPPER_MUSHROOM_UI_LANGUAGE", "en").strip().lower() or "en"


def catalog_label_candidates() -> list[Path]:
    """Return candidate label dictionaries for HA and local runs."""
    configured_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", "").strip()
    candidates = []
    if configured_defaults:
        candidates.append(Path(configured_defaults) / "mushroom_labels.json")
    candidates.append(Path("/app/mushroom-data/mushroom_labels.json"))
    module_path = Path(__file__).resolve()
    if len(module_path.parents) > 2:
        candidates.append(module_path.parents[2] / "mushroom-data" / "mushroom_labels.json")
    return candidates


def load_mushroom_labels() -> dict[str, dict[str, str]]:
    """Load mushroom-data label translations."""
    for candidate in catalog_label_candidates():
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        labels: dict[str, dict[str, str]] = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                translations = {str(language): str(label) for language, label in value.items() if label}
                if translations:
                    labels[str(key)] = translations
        return labels
    return {}


MUSHROOM_LABELS = load_mushroom_labels()


def mushroom_label(key: str, language: str = "en") -> str:
    """Return a translated label or an explicit missing-label marker."""
    labels = MUSHROOM_LABELS.get(key)
    if not labels:
        return f"missing label: {key}"
    return labels.get(language) or labels.get("en") or f"missing label: {key}.{language}"


def ui_label(key: str, language: str = UI_LANGUAGE) -> str:
    """Return a translated UI label using the configured mushroom UI language."""
    return mushroom_label(key, language=language)


def catalog_group_label(group: str, language: str = UI_LANGUAGE) -> str:
    """Return the configured display label for a catalog group."""
    return mushroom_label(f"catalog_group.{group}", language=language)


def catalog_label(item: dict[str, object], language: str = UI_LANGUAGE) -> str:
    """Return the best compact display label for a catalog entry."""
    scientific_name = str(item.get("scientific_name", "") or "").strip()
    if scientific_name:
        return scientific_name
    label = item.get("label")
    if isinstance(label, dict):
        value = str(label.get(language, "") or label.get("en", "") or "").strip()
        if value:
            return value
    common_names = item.get("common_names")
    if isinstance(common_names, dict):
        for language in ("es", "ca", "en"):
            names = common_names.get(language)
            if isinstance(names, list) and names:
                return str(names[0])
    return str(item.get("id", ""))


def collect_catalog_usage_references(payload: object, catalog_ids: set[str]) -> dict[str, int]:
    """Count how often catalog IDs appear inside a nested payload."""
    references = {item_id: 0 for item_id in catalog_ids}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)
        elif isinstance(value, str) and value in references:
            references[value] += 1

    visit(payload)
    return references


def catalog_rows(
    catalogs: dict[str, object],
    profiles: object,
    gis: object,
    observations: object | None = None,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Build table rows and summary metrics for the catalog hub."""
    catalog_ids = {
        str(item.get("id"))
        for items in catalogs.values()
        if isinstance(items, list)
        for item in items
        if isinstance(item, dict) and item.get("id")
    }
    profile_usage = collect_catalog_usage_references(profiles, catalog_ids)
    gis_usage = collect_catalog_usage_references(gis, catalog_ids)
    observation_usage = collect_catalog_usage_references(observations or {}, catalog_ids)
    rows: list[dict[str, object]] = []
    hierarchy_count = 0
    for group, items in catalogs.items():
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", ""))
            if not item_id:
                continue
            parent_id = str(item.get("parent_id", "") or "")
            if parent_id:
                hierarchy_count += 1
            profile_count = profile_usage.get(item_id, 0)
            gis_count = gis_usage.get(item_id, 0)
            observation_count = observation_usage.get(item_id, 0)
            rows.append(
                {
                    "group": group,
                    "index": index,
                    "id": item_id,
                    "label": catalog_label(item),
                    "parent_id": parent_id,
                    "profile_count": profile_count,
                    "gis_count": gis_count,
                    "observation_count": observation_count,
                    "domain": catalog_group_label(group),
                    "status": "active" if profile_count or gis_count or observation_count else "unused",
                    "item": item,
                }
            )
    metrics = {
        "groups": len([items for items in catalogs.values() if isinstance(items, list)]),
        "ids": len(rows),
        "profile_used": len([row for row in rows if int(row["profile_count"]) > 0]),
        "gis_used": len([row for row in rows if int(row["gis_count"]) > 0]),
        "observation_used": len([row for row in rows if int(row["observation_count"]) > 0]),
        "unused": len([row for row in rows if row["status"] == "unused"]),
        "hierarchy": hierarchy_count,
    }
    return rows, metrics


def selected_catalog_row(rows: list[dict[str, object]], group: str, item_id: str) -> dict[str, object] | None:
    """Select an explicit row, then first row in group, then first row overall."""
    if group and item_id:
        for row in rows:
            if row["group"] == group and row["id"] == item_id:
                return row
    if group:
        for row in rows:
            if row["group"] == group:
                return row
    return rows[0] if rows else None


def catalog_query_url(group: str = "", item_id: str = "", search: str = "") -> str:
    """Return an ingress-safe query URL for catalog navigation."""
    params = {}
    if group:
        params["group"] = group
    if item_id:
        params["id"] = item_id
    if search:
        params["q"] = search
    return ("?" + urlencode(params)) if params else "?"


def catalog_reference_error_count(errors: list[object]) -> int:
    """Count validation errors that look like broken catalog references."""
    count = 0
    for message in errors:
        text = str(getattr(message, "message", "")).lower()
        if "unknown" in text and "id" in text:
            count += 1
    return count


def render_catalog_metric_cards(metrics: dict[str, int], errors: list[object], warnings: list[object]) -> str:
    """Render compact catalog summary cards."""
    errors_count = len(errors)
    warnings_count = len(warnings)
    reference_errors = catalog_reference_error_count(errors)
    cards = [
        (ui_label("ui.total_groups"), str(metrics["groups"]), ""),
        (ui_label("ui.total_ids"), str(metrics["ids"]), ""),
        (ui_label("ui.used_in_profiles"), str(metrics["profile_used"]), "ok"),
        (ui_label("ui.used_in_gis"), str(metrics["gis_used"]), "ok"),
        (ui_label("ui.used_in_observations"), str(metrics["observation_used"]), "ok"),
        (ui_label("ui.reference_errors"), str(reference_errors), "danger" if reference_errors else "ok"),
        (ui_label("ui.unused"), str(metrics["unused"]), "warn" if metrics["unused"] else "ok"),
        (ui_label("ui.with_hierarchy"), str(metrics["hierarchy"]), ""),
        (ui_label("ui.validation"), f"{errors_count} {ui_label('ui.errors')} · {warnings_count} {ui_label('ui.warnings')}", "danger" if errors_count else "warn" if warnings_count else "ok"),
    ]
    return '<div class="profile-metrics catalog-metrics">' + "".join(
        f'<div class="profile-metric"><span class="label">{html.escape(label)}</span><span class="value {css_class}">{html.escape(value)}</span></div>'
        for label, value, css_class in cards
    ) + "</div>"


def render_catalog_group_chips(catalogs: dict[str, object], rows: list[dict[str, object]], selected_group: str, search: str) -> str:
    """Render catalog group filters."""
    total = sum(len(items) for items in catalogs.values() if isinstance(items, list))
    total_used = len([row for row in rows if int(row["profile_count"]) > 0 or int(row["gis_count"]) > 0 or int(row["observation_count"]) > 0])
    chips = [
        (
            f'<a class="catalog-chip{" active" if not selected_group else ""}" href="{catalog_query_url(search=search)}">'
            f'<strong>{html.escape(ui_label("ui.catalog_all"))}</strong><span>{total} IDs · {total_used} {html.escape(ui_label("ui.used"))}</span></a>'
        )
    ]
    for group, items in catalogs.items():
        if not isinstance(items, list):
            continue
        group_rows = [row for row in rows if row["group"] == group]
        used = len([row for row in group_rows if int(row["profile_count"]) > 0 or int(row["gis_count"]) > 0 or int(row["observation_count"]) > 0])
        domain = catalog_group_label(group)
        chips.append(
            f'<a class="catalog-chip{" active" if group == selected_group else ""}" href="{catalog_query_url(group=group, search=search)}" title="{html.escape(group, quote=True)}">'
            f'<strong>{html.escape(domain)}</strong><span>{len(items)} IDs · {used} {html.escape(ui_label("ui.used"))}</span></a>'
        )
    return '<div class="catalog-chip-row">' + "".join(chips) + "</div>"


def render_catalog_domain_impact(rows: list[dict[str, object]], selected_group: str) -> str:
    """Render read-only usage impact for the selected catalog group."""
    scoped_rows = [row for row in rows if not selected_group or row["group"] == selected_group]
    if not scoped_rows:
        return ""
    title = catalog_group_label(selected_group) if selected_group else ui_label("ui.whole_catalog")
    ids = len(scoped_rows)
    profile_refs = sum(int(row["profile_count"]) for row in scoped_rows)
    gis_refs = sum(int(row["gis_count"]) for row in scoped_rows)
    observation_refs = sum(int(row["observation_count"]) for row in scoped_rows)
    unused = len([row for row in scoped_rows if row["status"] == "unused"])
    examples = [
        str(row["id"])
        for row in scoped_rows
        if int(row["profile_count"]) > 0 or int(row["gis_count"]) > 0 or int(row["observation_count"]) > 0
    ][:6]
    if not examples:
        examples = [str(row["id"]) for row in scoped_rows[:6]]
    example_html = "".join(f"<span>{html.escape(example)}</span>" for example in examples)
    scope_text = selected_group or ui_label("ui.all_groups")
    return f"""
    <section class="card catalog-domain-impact">
      <div>
        <h2>{html.escape(ui_label("ui.domain_impact"))}</h2>
        <p class="meta">{html.escape(title)} · {html.escape(scope_text)}</p>
      </div>
      <div class="catalog-domain-impact-grid">
        <div><span class="label">{html.escape(ui_label("ui.ids_in_scope"))}</span><span class="value">{ids}</span></div>
        <div><span class="label">{html.escape(ui_label("ui.profile_references"))}</span><span class="value ok">{profile_refs}</span></div>
        <div><span class="label">{html.escape(ui_label("ui.gis_references"))}</span><span class="value ok">{gis_refs}</span></div>
        <div><span class="label">{html.escape(ui_label("ui.observation_references"))}</span><span class="value ok">{observation_refs}</span></div>
        <div><span class="label">{html.escape(ui_label("ui.unused_ids"))}</span><span class="value {'warn' if unused else 'ok'}">{unused}</span></div>
      </div>
      <div>
        <span class="label">{html.escape(ui_label("ui.representative_ids"))}</span>
        <div class="catalog-domain-examples">{example_html}</div>
      </div>
    </section>
    """


def render_catalog_table(rows: list[dict[str, object]], selected: dict[str, object] | None, group: str, search: str) -> str:
    """Render the reference catalog table."""
    tokens = [token.lower() for token in search.split() if token.strip()]
    filtered_rows = []
    for row in rows:
        if group and row["group"] != group:
            continue
        searchable = " ".join(str(row.get(key, "")) for key in ("group", "id", "label", "parent_id", "domain", "status")).lower()
        if tokens and not all(token in searchable for token in tokens):
            continue
        filtered_rows.append(row)

    body_rows = []
    for row in filtered_rows:
        item_id = str(row["id"])
        row_group = str(row["group"])
        detail_url = catalog_query_url(row_group, item_id, search)
        is_selected = selected and selected.get("group") == row_group and selected.get("id") == item_id
        body_rows.append(
            f'<tr class="catalog-click-row{" selected-row" if is_selected else ""}" data-href="{html.escape(detail_url, quote=True)}" onclick="if (!event.target.closest(\'a, button, input, select, textarea\')) window.location.href = this.dataset.href">'
            f'<td>{html.escape(row_group)}</td>'
            f'<td><a class="catalog-row-link" href="{html.escape(detail_url, quote=True)}">{html.escape(item_id)}</a></td>'
            f'<td>{html.escape(str(row["label"]))}</td>'
            f'<td>{html.escape(str(row["parent_id"] or "-"))}</td>'
            f'<td>{int(row["profile_count"])}</td>'
            f'<td>{int(row["gis_count"])}</td>'
            f'<td>{int(row["observation_count"])}</td>'
            f'<td>{html.escape(str(row["domain"]))}</td>'
            f'<td><span class="status-pill {"" if row["status"] == "active" else "warn"}">{html.escape(ui_label("ui.active") if row["status"] == "active" else ui_label("ui.unused"))}</span></td>'
            "</tr>"
        )
    if not body_rows:
        body_rows.append(f'<tr><td colspan="9"><span class="meta">{html.escape(ui_label("ui.no_catalog_entries_match"))}</span></td></tr>')
    return (
        '<div class="control-table-wrap catalog-table-wrap">'
        '<table class="control-table catalog-table">'
        f'<thead><tr><th>{html.escape(ui_label("ui.group"))}</th><th>ID</th><th>{html.escape(ui_label("ui.label_scientific_name"))}</th><th>{html.escape(ui_label("ui.parent_id"))}</th><th>{html.escape(ui_label("ui.profiles"))}</th><th>GIS</th><th>{html.escape(ui_label("ui.obs_short"))}</th><th>{html.escape(ui_label("ui.domain"))}</th><th>{html.escape(ui_label("ui.status"))}</th></tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        "</table></div>"
    )


def render_catalog_alerts(errors: list[object], warnings: list[object], limit: int = 10) -> str:
    """Render validator messages with clear severity styling."""
    messages = []
    for severity, items in (("error", errors), ("warn", warnings)):
        for message in items[:limit]:
            location = html.escape(str(getattr(message, "location", "")))
            text = html.escape(str(getattr(message, "message", "")))
            messages.append(f'<div class="catalog-alert {severity}"><strong>{location}</strong><br>{text}</div>')
    if not messages:
        messages.append(f'<div class="catalog-alert"><strong>{html.escape(ui_label("ui.validation_clean"))}</strong><br>{html.escape(ui_label("ui.no_blocking_validation_errors"))}</div>')
    return '<div class="catalog-alert-list">' + "".join(messages) + "</div>"


def catalog_textarea_value(values: object) -> str:
    """Format scalar/list values for textarea controls."""
    if isinstance(values, list):
        return "\n".join(str(value) for value in values if str(value).strip())
    return str(values or "")


def catalog_form_field(name: str, label: str, value: object = "", field_type: str = "text", readonly: bool = False) -> str:
    """Render a catalog form input."""
    readonly_attr = " readonly" if readonly else ""
    step_attr = ' step="any"' if field_type == "number" else ""
    escaped_name = html.escape(name, quote=True)
    escaped_label = html.escape(label)
    escaped_value = html.escape("" if value is None else str(value), quote=True)
    return (
        '<div class="admin-field compact">'
        f'<label for="catalog-{escaped_name}">{escaped_label}</label>'
        f'<input id="catalog-{escaped_name}" name="{escaped_name}" type="{html.escape(field_type, quote=True)}" value="{escaped_value}"{step_attr}{readonly_attr}>'
        "</div>"
    )


def catalog_ids_for_group(catalogs: dict[str, object], group: str) -> list[str]:
    """Return sorted IDs for a catalog group."""
    items = catalogs.get(group)
    if not isinstance(items, list):
        return []
    return sorted(
        str(item.get("id", ""))
        for item in items
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    )


def catalog_form_select(name: str, label: str, value: object, options: list[str], exclude: str = "") -> str:
    """Render a select control preserving missing current values."""
    current = "" if value is None else str(value)
    escaped_name = html.escape(name, quote=True)
    option_html = [f'<option value=""{" selected" if not current else ""}>-</option>']
    for option in options:
        if option == exclude:
            continue
        selected = " selected" if option == current else ""
        option_html.append(f'<option value="{html.escape(option, quote=True)}"{selected}>{html.escape(option)}</option>')
    if current and current not in options:
        option_html.append(f'<option value="{html.escape(current, quote=True)}" selected>{html.escape(current)} (missing)</option>')
    return (
        '<div class="admin-field compact">'
        f'<label for="catalog-{escaped_name}">{html.escape(label)}</label>'
        f'<select id="catalog-{escaped_name}" name="{escaped_name}">{"".join(option_html)}</select>'
        "</div>"
    )


def catalog_form_textarea(name: str, label: str, value: object) -> str:
    """Render a catalog textarea."""
    escaped_name = html.escape(name, quote=True)
    return (
        '<div class="admin-field">'
        f'<label for="catalog-{escaped_name}">{html.escape(label)}</label>'
        f'<textarea id="catalog-{escaped_name}" name="{escaped_name}">{html.escape(catalog_textarea_value(value))}</textarea>'
        "</div>"
    )


def catalog_missing_ids(values: object, allowed_ids: set[str]) -> list[str]:
    """Return values that do not exist in the allowed ID set."""
    if not isinstance(values, list):
        values = [values] if values else []
    return sorted(
        str(value)
        for value in values
        if str(value).strip() and str(value) not in allowed_ids
    )


def catalog_cross_reference_checks(group: str, item: dict[str, object], catalogs: dict[str, object]) -> list[tuple[str, str, str]]:
    """Validate catalog-to-catalog references used by the edit form."""
    host_ids = set(catalog_ids_for_group(catalogs, "host_taxa"))
    forest_ids = set(catalog_ids_for_group(catalogs, "forest_types"))
    soil_ids = set(catalog_ids_for_group(catalogs, "soil_types"))
    checks: list[tuple[str, str, str]] = []
    if group == "host_taxa":
        parent_id = str(item.get("parent_id", "") or "")
        if parent_id and parent_id not in host_ids:
            checks.append(("error", "parent_id", f"{parent_id}: {ui_label('ui.id_not_in_catalog')} host_taxa."))
        else:
            checks.append(("ok", "parent_id", ui_label("ui.parent_id_empty_or_exists")))
    elif group == "forest_types":
        parent_id = str(item.get("parent_id", "") or "")
        if parent_id and parent_id not in forest_ids:
            checks.append(("error", "parent_id", f"{parent_id}: {ui_label('ui.id_not_in_catalog')} forest_types."))
        missing_hosts = catalog_missing_ids(item.get("dominant_host_ids", []), host_ids)
        missing_soils = catalog_missing_ids(item.get("soil_bias_ids", []), soil_ids)
        if missing_hosts:
            checks.append(("error", "dominant_host_ids", f"{ui_label('ui.missing_ids')} host_taxa: " + ", ".join(missing_hosts)))
        else:
            checks.append(("ok", "dominant_host_ids", ui_label("ui.dominant_host_ids_exist")))
        if missing_soils:
            checks.append(("error", "soil_bias_ids", f"{ui_label('ui.missing_ids')} soil_types: " + ", ".join(missing_soils)))
        elif item.get("soil_bias_ids"):
            checks.append(("ok", "soil_bias_ids", ui_label("ui.soil_bias_ids_exist")))
    elif group == "lithology_types":
        missing_soils = catalog_missing_ids(item.get("parent_soil_tendency_ids", []), soil_ids)
        if missing_soils:
            checks.append(("error", "parent_soil_tendency_ids", f"{ui_label('ui.missing_ids')} soil_types: " + ", ".join(missing_soils)))
        else:
            checks.append(("ok", "parent_soil_tendency_ids", ui_label("ui.parent_soil_tendency_ids_exist")))
    return checks


def render_catalog_cross_reference_checks(group: str, item: dict[str, object], catalogs: dict[str, object]) -> str:
    """Render catalog cross-reference validation hints."""
    checks = catalog_cross_reference_checks(group, item, catalogs)
    if not checks:
        return ""
    rows = []
    for severity, field, message in checks:
        rows.append(
            f'<div class="catalog-reference-check {html.escape(severity)}">'
            f"<strong>{html.escape(field)}</strong>{html.escape(message)}</div>"
        )
    return f'<section class="catalog-reference-checks"><h2>{html.escape(ui_label("ui.cross_references"))}</h2>' + "".join(rows) + "</section>"


def catalog_label_fields(item: dict[str, object]) -> str:
    """Render multilingual label inputs."""
    label = item.get("label")
    if not isinstance(label, dict):
        label = {}
    return "".join(
        catalog_form_field(f"label_{language}", ui_label(f"ui.label_{language}"), label.get(language, ""))
        for language in ("es", "ca", "en")
    )


def render_catalog_entry_form(row: dict[str, object], catalogs: dict[str, object]) -> str:
    """Render the friendly per-entry edit form."""
    item = row.get("item", {})
    item = item if isinstance(item, dict) else {}
    group = str(row["group"])
    item_id = str(row["id"])
    fields = [catalog_form_field("id", "ID", item_id, readonly=True)]
    if group == "host_taxa":
        common_names = item.get("common_names") if isinstance(item.get("common_names"), dict) else {}
        fields.extend(
            [
                catalog_form_field("rank", ui_label("ui.rank"), item.get("rank", "")),
                catalog_form_field("scientific_name", ui_label("ui.scientific_name"), item.get("scientific_name", "")),
                catalog_form_field("genus", ui_label("ui.genus"), item.get("genus", "")),
                catalog_form_field("family", ui_label("ui.family"), item.get("family", "")),
                catalog_form_select("parent_id", ui_label("ui.parent_id"), item.get("parent_id", ""), catalog_ids_for_group(catalogs, "host_taxa"), exclude=item_id),
                catalog_form_textarea("common_names_es", ui_label("ui.common_names_es"), common_names.get("es", [])),
                catalog_form_textarea("common_names_ca", ui_label("ui.common_names_ca"), common_names.get("ca", [])),
                catalog_form_textarea("common_names_en", ui_label("ui.common_names_en"), common_names.get("en", [])),
                catalog_form_textarea("gis_aliases", ui_label("ui.gis_aliases"), item.get("gis_aliases", [])),
            ]
        )
    else:
        fields.append(catalog_label_fields(item))
        if group == "forest_types":
            fields.extend(
                [
                    catalog_form_select("parent_id", ui_label("ui.parent_id"), item.get("parent_id", ""), catalog_ids_for_group(catalogs, "forest_types"), exclude=item_id),
                    catalog_form_textarea("dominant_host_ids", ui_label("ui.dominant_host_ids"), item.get("dominant_host_ids", [])),
                    catalog_form_textarea("soil_bias_ids", ui_label("ui.soil_bias_ids"), item.get("soil_bias_ids", [])),
                    catalog_form_textarea("gis_aliases", ui_label("ui.gis_aliases"), item.get("gis_aliases", [])),
                ]
            )
        elif group == "soil_types":
            fields.extend(
                [
                    catalog_form_field("ph_min", ui_label("ui.ph_min"), item.get("ph_min", ""), field_type="number"),
                    catalog_form_field("ph_max", ui_label("ui.ph_max"), item.get("ph_max", ""), field_type="number"),
                    catalog_form_field("texture", ui_label("ui.texture"), item.get("texture", "")),
                    catalog_form_field("organic_matter", ui_label("ui.organic_matter"), item.get("organic_matter", "")),
                    catalog_form_field("drainage", ui_label("ui.drainage"), item.get("drainage", "")),
                    catalog_form_textarea("gis_aliases", ui_label("ui.gis_aliases"), item.get("gis_aliases", [])),
                ]
            )
        elif group == "lithology_types":
            fields.extend(
                [
                    catalog_form_field("general_reaction", ui_label("ui.general_reaction"), item.get("general_reaction", "")),
                    catalog_form_textarea("parent_soil_tendency_ids", ui_label("ui.parent_soil_tendency_ids"), item.get("parent_soil_tendency_ids", [])),
                    catalog_form_textarea("gis_aliases", ui_label("ui.gis_aliases"), item.get("gis_aliases", [])),
                ]
            )
        elif group == "aspects":
            fields.extend(
                [
                    catalog_form_field("azimuth_min", ui_label("ui.azimuth_min"), item.get("azimuth_min", ""), field_type="number"),
                    catalog_form_field("azimuth_max", ui_label("ui.azimuth_max"), item.get("azimuth_max", ""), field_type="number"),
                ]
            )
        if "description" in item or group == "trophic_modes":
            fields.append(catalog_form_textarea("description", ui_label("ui.description"), item.get("description", "")))
        if "notes" in item:
            fields.append(catalog_form_textarea("notes", ui_label("ui.notes"), item.get("notes", "")))

    return f"""
      <form class="catalog-entry-form" method="post" action="?group={html.escape(group, quote=True)}&id={html.escape(item_id, quote=True)}" onsubmit="return confirm('Save this catalog entry and validate the full dataset?')">
        <input type="hidden" name="catalog_action" value="save_entry_form">
        <input type="hidden" name="group" value="{html.escape(group, quote=True)}">
        <input type="hidden" name="id" value="{html.escape(item_id, quote=True)}">
        <div class="admin-form-grid">{''.join(fields)}</div>
        <div class="catalog-entry-actions">
          <button class="secondary" name="catalog_action" value="backup_catalog_keep" type="submit" formnovalidate onclick="return confirm('Create a manual keep backup of the full reference catalog now?')">{html.escape(ui_label("ui.backup"))}</button>
          <button class="primary">{html.escape(ui_label("ui.save_entry"))}</button>
        </div>
      </form>
    """


def render_catalog_detail(row: dict[str, object] | None, errors: list[object], warnings: list[object], catalogs: dict[str, object]) -> str:
    """Render the selected catalog entry detail panel."""
    if not row:
        return f'<aside class="card catalog-detail"><h2>{html.escape(ui_label("ui.catalog_detail"))}</h2><p>{html.escape(ui_label("ui.no_catalog_entry_selected"))}</p></aside>'
    item = row.get("item", {})
    json_value = json.dumps(item, indent=2, ensure_ascii=False)
    group = str(row["group"])
    item_id = str(row["id"])
    return f"""
    <aside class="card catalog-detail">
      <h2>{html.escape(ui_label("ui.catalog_detail"))}</h2>
      <p><strong>{html.escape(item_id)}</strong><br>{html.escape(group)} · {html.escape(str(row["domain"]))}</p>
      {render_catalog_entry_form(row, catalogs)}
      {render_catalog_cross_reference_checks(group, item if isinstance(item, dict) else {}, catalogs)}
      <details>
        <summary><strong>{html.escape(ui_label("ui.advanced_raw_json"))}</strong></summary>
        <form class="catalog-json-editor" method="post" action="?group={html.escape(group, quote=True)}&id={html.escape(item_id, quote=True)}" onsubmit="return confirm('Save raw JSON for this catalog entry and validate the full dataset?')">
          <input type="hidden" name="catalog_action" value="save_entry">
          <input type="hidden" name="group" value="{html.escape(group, quote=True)}">
          <input type="hidden" name="id" value="{html.escape(item_id, quote=True)}">
          <label class="label" for="catalog-entry-json">{html.escape(ui_label("ui.entry_json"))}</label>
          <textarea id="catalog-entry-json" name="entry_json" spellcheck="false">{html.escape(json_value)}</textarea>
          <button class="primary">{html.escape(ui_label("ui.save_raw_json"))}</button>
        </form>
      </details>
      <h2>{html.escape(ui_label("ui.validation"))}</h2>
      {render_catalog_alerts(errors, warnings, limit=4)}
    </aside>
    """


def render_catalog_full_json_panel(payload: dict[str, object], mode: str) -> str:
    """Render controlled full-file import/export controls."""
    json_value = json.dumps(payload, indent=2, ensure_ascii=False)
    mode_label = ui_label("ui.empty_template") if mode == "template" else ui_label("ui.current_catalog")
    return f"""
    <details class="card" {"open" if mode == "template" else ""}>
      <summary><strong>{html.escape(ui_label("ui.full_catalog_json_import_export"))}</strong> · {html.escape(mode_label)}</summary>
      <p>{html.escape(ui_label("ui.import_export_help_catalog"))}</p>
      <div class="quick-actions">
        <a class="button-link" href="?mode=current">{html.escape(ui_label("ui.current_catalog"))}</a>
        <a class="button-link" href="?mode=default">{html.escape(ui_label("ui.packaged_default"))}</a>
        <a class="button-link" href="?mode=template">{html.escape(ui_label("ui.empty_template"))}</a>
      </div>
      <form class="catalog-json-editor" method="post" action="" onsubmit="return confirm('Replace the full catalog JSON after validation?')">
        <input type="hidden" name="catalog_action" value="save_catalog">
        <label class="label" for="catalog-full-json">{html.escape(ui_label("ui.catalog_json"))}</label>
        <textarea id="catalog-full-json" name="catalog_json" spellcheck="false">{html.escape(json_value)}</textarea>
        <button class="primary">{html.escape(ui_label("ui.validate_save_full_catalog"))}</button>
      </form>
    </details>
    """


def render_new_catalog_entry_form(catalogs: dict[str, object], selected_group: str) -> str:
    """Render the starter form for creating a catalog entry."""
    options = []
    for group, items in catalogs.items():
        if not isinstance(items, list):
            continue
        selected = " selected" if group == selected_group else ""
        prefix = CATALOG_ID_PREFIXES.get(group, "")
        label = catalog_group_label(group)
        options.append(
            f'<option value="{html.escape(group, quote=True)}"{selected}>{html.escape(label)} · {html.escape(group)}{(" · " + html.escape(prefix)) if prefix else ""}</option>'
        )
    return f"""
    <section class="card">
      <h2>{html.escape(ui_label("ui.new_catalog_entry"))}</h2>
      <p>{html.escape(ui_label("ui.new_catalog_entry_help"))}</p>
      <form class="catalog-create-form" method="post" action="" onsubmit="return confirm('Create this catalog entry and validate the full dataset?')">
        <input type="hidden" name="catalog_action" value="create_entry">
        <div class="admin-form-grid">
          <div class="admin-field">
            <label>{html.escape(ui_label("ui.group"))}</label>
            <select name="group">{''.join(options)}</select>
          </div>
          <div class="admin-field">
            <label>ID</label>
            <input name="id" placeholder="host_cistus_spp" required>
          </div>
        </div>
        <button class="primary">{html.escape(ui_label("ui.create_entry"))}</button>
      </form>
    </section>
    """
