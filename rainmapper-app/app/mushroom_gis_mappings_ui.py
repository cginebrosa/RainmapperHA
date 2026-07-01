"""Server-rendered UI helpers for mushroom GIS mappings maintenance.

This module renders the review screen that connects raw GIS layer values to
internal mushroom reference catalog IDs. Routing, persistence and validation
remain in `web_server.py`; this file keeps the HTML and row-building logic
close to the domain UI.
"""

from __future__ import annotations

import html
import json
from urllib.parse import urlencode

import mushroom_catalogs_ui


TARGET_CATALOG_FIELDS = (
    ("mapped_host_ids", "host_taxa"),
    ("mapped_forest_type_ids", "forest_types"),
    ("mapped_soil_tendency_ids", "soil_types"),
    ("mapped_lithology_ids", "lithology_types"),
    ("mapped_habitat_feature_ids", "habitat_features"),
)

TARGETS_BY_SOURCE_FIELD = {
    ("mvc50", "LLFISCAT_t"): ("mapped_host_ids", "mapped_forest_type_ids"),
    ("mvc50", "LLVA_niv2t"): ("mapped_forest_type_ids", "mapped_habitat_feature_ids"),
    ("mvc50", "LLVA_Subst"): ("mapped_soil_tendency_ids",),
    ("geology_50000", "Codi"): ("mapped_lithology_ids", "mapped_soil_tendency_ids"),
}

CONFIDENCE_VALUES = ("high", "medium", "low")
REVIEW_STATUS_VALUES = ("accepted", "pending_review", "ignored")


def has_review_suggestion(context: object) -> bool:
    """Return true when a reconstruction candidate carries preselected target IDs."""
    if not isinstance(context, dict):
        return False
    return any(isinstance(context.get(f"suggested_{target_field}"), list) for target_field, _group in TARGET_CATALOG_FIELDS)


def suggested_status_from_context(context: object) -> str:
    """Return the review status declared by reconstruction suggestions."""
    if not has_review_suggestion(context):
        return "unmapped"
    if isinstance(context, dict):
        status = str(context.get("suggested_review_status", "") or "")
        if status in REVIEW_STATUS_VALUES:
            return status
    return "pending_review"


def mapping_key(source_id: object, field: object, raw_value: object) -> str:
    """Return a stable row key for exact mappings and candidates."""
    return f"{source_id}\u241f{field}\u241f{raw_value}"


def split_mapping_key(key: str) -> tuple[str, str, str]:
    """Parse a key created by `mapping_key`."""
    parts = key.split("\u241f", 2)
    if len(parts) != 3:
        return "", "", ""
    return parts[0], parts[1], parts[2]


def exact_mappings(gis_payload: dict[str, object]) -> list[dict[str, object]]:
    """Return exact-value mappings from the GIS mappings payload."""
    values = gis_payload.get("exact_value_mappings")
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def candidate_rows(reconstruction_payload: dict[str, object] | None) -> list[dict[str, object]]:
    """Return unmapped candidates detected by the latest GIS reconstruction."""
    if not isinstance(reconstruction_payload, dict):
        return []
    candidates = reconstruction_payload.get("unmapped_candidates")
    rows: list[dict[str, object]] = []
    if not isinstance(candidates, list):
        return rows
    geology_descriptions = [
        str(candidate.get("raw_value", "") or "")
        for candidate in candidates
        if isinstance(candidate, dict)
        and str(candidate.get("source_id", "") or "") == "geology_50000"
        and str(candidate.get("field", "") or "") == "Descripcio"
        and candidate.get("raw_value")
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        source_id = str(candidate.get("source_id", "") or "")
        field = str(candidate.get("field", "") or "")
        raw_value = str(candidate.get("raw_value", "") or "")
        if not source_id or not field or not raw_value:
            continue
        if source_id == "geology_50000" and field == "Descripcio":
            continue
        context = {
            key: value
            for key, value in candidate.items()
            if key not in {"source_id", "field", "raw_value"} and value not in (None, "")
        }
        if source_id == "geology_50000" and field == "Codi" and "description" not in context and geology_descriptions:
            context["description"] = geology_descriptions[0]
        rows.append(
            {
                "source_id": source_id,
                "field": field,
                "raw_value": raw_value,
                "context": context,
                "status": suggested_status_from_context(context),
                "key": mapping_key(source_id, field, raw_value),
                "mapping": None,
            }
        )
    return rows


def mapping_rows(
    gis_payload: dict[str, object],
    reconstruction_payload: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Build merged rows from stored exact mappings and latest candidates."""
    rows: list[dict[str, object]] = []
    mapped_keys: set[str] = set()
    for index, mapping in enumerate(exact_mappings(gis_payload)):
        source_id = str(mapping.get("source_id", "") or "")
        field = str(mapping.get("field", "") or "")
        raw_value = str(mapping.get("raw_value", "") or "")
        key = mapping_key(source_id, field, raw_value)
        mapped_keys.add(key)
        rows.append(
            {
                "index": index,
                "source_id": source_id,
                "field": field,
                "raw_value": raw_value,
                "status": str(mapping.get("review_status", "") or "accepted"),
                "confidence": str(mapping.get("confidence", "") or ""),
                "key": key,
                "mapping": mapping,
            }
        )
    for candidate in candidate_rows(reconstruction_payload):
        if str(candidate["key"]) not in mapped_keys:
            rows.append(candidate)
    rows.sort(key=lambda row: (str(row.get("source_id", "")), str(row.get("field", "")), str(row.get("raw_value", ""))))
    return rows


def selected_mapping_row(rows: list[dict[str, object]], selected_key: str) -> dict[str, object] | None:
    """Return the selected mapping row or the first available row."""
    if selected_key:
        for row in rows:
            if str(row.get("key", "")) == selected_key:
                return row
    return rows[0] if rows else None


def mappings_query_url(
    selected_key: str = "",
    source_id: str = "",
    field: str = "",
    search: str = "",
    status_filter: str = "",
    sort_by: str = "",
    sort_dir: str = "",
) -> str:
    """Return an ingress-safe query URL for GIS mapping navigation."""
    params = {}
    if selected_key:
        params["key"] = selected_key
    if source_id:
        params["source"] = source_id
    if field:
        params["field"] = field
    if search:
        params["q"] = search
    if status_filter:
        params["status"] = status_filter
    if sort_by:
        params["sort"] = sort_by
    if sort_dir:
        params["dir"] = sort_dir
    return ("?" + urlencode(params)) if params else "?"


def mapping_target_summary(mapping: dict[str, object] | None) -> str:
    """Render compact target IDs for a mapping row."""
    if not isinstance(mapping, dict):
        return "-"
    values: list[str] = []
    for field, _catalog_group in TARGET_CATALOG_FIELDS:
        raw_ids = mapping.get(field)
        if isinstance(raw_ids, list):
            values.extend(str(item) for item in raw_ids if item)
    return ", ".join(values) if values else "-"


def suggested_mapping_from_context(context: object) -> dict[str, object]:
    """Return a mapping-shaped payload from review suggestions in row context."""
    if not isinstance(context, dict):
        return {}
    suggestion: dict[str, object] = {}
    for target_field, _catalog_group in TARGET_CATALOG_FIELDS:
        suggested = context.get(f"suggested_{target_field}")
        if isinstance(suggested, list):
            suggestion[target_field] = [str(item) for item in suggested if item]
    confidence = str(context.get("suggested_confidence", "") or "")
    if confidence:
        suggestion["confidence"] = confidence
    notes = str(context.get("suggestion_notes", "") or "")
    if notes:
        suggestion["notes"] = notes
    return suggestion


def status_tone(status: str) -> str:
    """Return the UI tone for a mapping status."""
    if status == "accepted":
        return "ok"
    if status in {"pending_review", "unmapped"}:
        return "warn"
    if status == "ignored":
        return ""
    return "warn"


def raw_value_label(row: dict[str, object]) -> str:
    """Return the raw value label with source-specific context where useful."""
    raw_value = str(row.get("raw_value", "") or "")
    context = row.get("context")
    description = ""
    if isinstance(context, dict):
        description = str(context.get("description", "") or "")
    if row.get("source_id") == "geology_50000" and row.get("field") == "Codi" and description:
        return f"{raw_value} · {description}"
    return raw_value


def render_mapping_context(row: dict[str, object], mapping: dict[str, object]) -> str:
    """Render non-persistent context that explains what a raw GIS value means."""
    context = row.get("context")
    if not isinstance(context, dict):
        return ""
    suggestion = suggested_mapping_from_context(context)
    suggestion_html = ""
    if suggestion:
        suggested_ids = mapping_target_summary(suggestion)
        suggested_confidence = str(context.get("suggested_confidence", "") or "")
        suggestion_source = str(context.get("suggestion_source", "") or "")
        suggestion_notes = str(context.get("suggestion_notes", "") or "")
        suggestion_html = (
            '<div class="gis-mapping-context">'
            '<strong>Review suggestion</strong>'
            f'<span>Suggested IDs: {html.escape(suggested_ids)}</span>'
            f'<span>Confidence: {html.escape(suggested_confidence or "-")}</span>'
            f'<span>Source: {html.escape(suggestion_source or "-")}</span>'
            f'<span>{html.escape(suggestion_notes)}</span>'
            '</div>'
        )
    elif not isinstance(row.get("mapping"), dict):
        suggestion_html = (
            '<div class="gis-mapping-context">'
            '<strong>No automatic suggestion</strong>'
            '<span>No declarative batch rule produced catalog IDs for this raw GIS value.</span>'
            '<span>Keep it as pending review, mark it ignored, or select targets manually before saving.</span>'
            '</div>'
        )
    if row.get("source_id") == "geology_50000" and row.get("field") == "Codi":
        description = str(context.get("description", "") or "")
        if description:
            return (
                '<div class="gis-mapping-context">'
                '<strong>Codigo oficial de geologia</strong>'
                f'<span>El mapping se guarda por <code>Codi</code>: <code>{html.escape(str(row.get("raw_value", "")))}</code></span>'
                f'<span>Descripcion asociada: {html.escape(description)}</span>'
                '</div>'
                + suggestion_html
            )
    return suggestion_html


def mapping_metrics(rows: list[dict[str, object]], errors: list[object], warnings: list[object]) -> dict[str, int]:
    """Return metrics for the GIS mappings screen."""
    mapped = [row for row in rows if str(row.get("status", "") or "") == "accepted"]
    pending = [row for row in rows if str(row.get("status", "") or "") in {"pending_review", "unmapped"}]
    return {
        "rows": len(rows),
        "mapped": len(mapped),
        "pending": len(pending),
        "sources": len({str(row.get("source_id", "")) for row in rows if row.get("source_id")}),
        "fields": len({str(row.get("field", "")) for row in rows if row.get("field")}),
        "errors": len(errors),
        "warnings": len(warnings),
    }


def render_mapping_metric_cards(
    metrics: dict[str, int],
    selected_status: str = "",
    selected_source: str = "",
    selected_field: str = "",
    search: str = "",
    sort_by: str = "",
    sort_dir: str = "",
) -> str:
    """Render compact summary cards for GIS mappings."""
    mapped_pct = round((metrics["mapped"] / metrics["rows"]) * 100) if metrics["rows"] else 0
    pending_pct = round((metrics["pending"] / metrics["rows"]) * 100) if metrics["rows"] else 0
    cards = [
        ("Total values", str(metrics["rows"]), "in the system", "list", "", ""),
        ("Mapped", str(metrics["mapped"]), f"{mapped_pct}%", "ok", "ok", "mapped"),
        ("Pending review", str(metrics["pending"]), f"{pending_pct}%", "pending", "warn" if metrics["pending"] else "ok", "pending"),
        ("Sources", str(metrics["sources"]), "active inputs", "source", "", ""),
        ("Fields", str(metrics["fields"]), "raw fields", "field", "", ""),
        ("Validation", f"{metrics['errors']} / {metrics['warnings']}", "errors / warnings", "check", "danger" if metrics["errors"] else "warn" if metrics["warnings"] else "ok", ""),
    ]
    rendered = []
    for label, value, subtitle, icon_class, value_class, metric_status in cards:
        active = metric_status and selected_status == metric_status
        clear_active = active
        href = mappings_query_url(
            source_id=selected_source,
            field=selected_field,
            search=search,
            status_filter="" if clear_active else metric_status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        tag = "a" if metric_status else "div"
        attrs = f' href="{html.escape(href, quote=True)}"' if metric_status else ""
        rendered.append(
            f'<{tag} class="profile-metric gis-mapping-metric{" active" if active else ""}"{attrs}>'
            f'<span class="gis-mapping-metric-icon {html.escape(icon_class)}"></span>'
            '<span class="gis-mapping-metric-body">'
            f'<span class="label">{html.escape(label)}</span>'
            f'<span class="value {html.escape(value_class)}">{html.escape(value)}</span>'
            f'<span class="meta">{html.escape(subtitle)}</span>'
            "</span>"
            f'</{tag}>'
        )
    return '<div class="gis-mapping-metrics">' + "".join(rendered) + "</div>"


def render_source_field_chips(
    rows: list[dict[str, object]],
    selected_source: str,
    selected_field: str,
    search: str,
    selected_status: str = "",
    sort_by: str = "",
    sort_dir: str = "",
) -> str:
    """Render source and field filters using compact chips."""
    sources = sorted({str(row.get("source_id", "")) for row in rows if row.get("source_id")})
    field_rows = [row for row in rows if not selected_source or row.get("source_id") == selected_source]
    fields = sorted({str(row.get("field", "")) for row in field_rows if row.get("field")})
    source_count_rows = [row for row in rows if not selected_field or row.get("field") == selected_field]
    field_count_rows = [row for row in rows if not selected_source or row.get("source_id") == selected_source]
    source_chips = [
        f'<a class="catalog-chip{" active" if not selected_source else ""}" href="{mappings_query_url(field=selected_field, search=search, status_filter=selected_status, sort_by=sort_by, sort_dir=sort_dir)}"><strong>All sources</strong><span>{len(source_count_rows)} values</span></a>'
    ]
    source_chips.extend(
        f'<a class="catalog-chip{" active" if selected_source == source else ""}" href="{mappings_query_url(source_id=source, field=selected_field, search=search, status_filter=selected_status, sort_by=sort_by, sort_dir=sort_dir)}"><strong>{html.escape(source)}</strong><span>{sum(1 for row in source_count_rows if row.get("source_id") == source)} values</span></a>'
        for source in sources
        if any(row.get("source_id") == source for row in source_count_rows)
    )
    field_chips = [
        f'<a class="catalog-chip{" active" if not selected_field else ""}" href="{mappings_query_url(source_id=selected_source, search=search, status_filter=selected_status, sort_by=sort_by, sort_dir=sort_dir)}"><strong>All fields</strong><span>{len(field_count_rows)} values</span></a>'
    ]
    field_chips.extend(
        f'<a class="catalog-chip{" active" if selected_field == field else ""}" href="{mappings_query_url(source_id=selected_source, field=field, search=search, status_filter=selected_status, sort_by=sort_by, sort_dir=sort_dir)}"><strong>{html.escape(field)}</strong><span>{sum(1 for row in field_count_rows if row.get("field") == field)} values</span></a>'
        for field in fields
    )
    return (
        '<div class="gis-mapping-filter-panel">'
        '<div class="gis-mapping-filter-row"><span class="gis-mapping-filter-label">Sources</span>'
        '<div class="catalog-group-grid gis-mapping-filter-grid">'
        + "".join(source_chips)
        + "</div></div>"
        '<div class="gis-mapping-filter-row"><span class="gis-mapping-filter-label">Fields</span>'
        '<div class="catalog-group-grid gis-mapping-filter-grid compact">'
        + "".join(field_chips)
        + "</div></div></div>"
    )


def filtered_mapping_rows(
    rows: list[dict[str, object]],
    source_id: str,
    field: str,
    search: str,
    status_filter: str = "",
) -> list[dict[str, object]]:
    """Filter rows by source, field and free-text search."""
    normalized_search = search.strip().lower()
    filtered = []
    for row in rows:
        if source_id and row.get("source_id") != source_id:
            continue
        if field and row.get("field") != field:
            continue
        status = str(row.get("status", "") or "")
        if status_filter == "mapped" and status != "accepted":
            continue
        if status_filter == "pending" and status not in {"pending_review", "unmapped"}:
            continue
        haystack = " ".join(str(row.get(key, "")) for key in ("source_id", "field", "raw_value", "status"))
        context = row.get("context")
        if isinstance(context, dict):
            haystack = f"{haystack} {' '.join(str(value) for value in context.values())}"
        haystack = f"{haystack} {mapping_target_summary(row.get('mapping') if isinstance(row.get('mapping'), dict) else None)}"
        if normalized_search and normalized_search not in haystack.lower():
            continue
        filtered.append(row)
    return filtered


def sorted_mapping_rows(rows: list[dict[str, object]], sort_by: str, sort_dir: str) -> list[dict[str, object]]:
    """Return rows sorted by a visible table column."""
    valid_sorts = {"source", "field", "raw_value", "mapped_ids", "status"}
    if sort_by not in valid_sorts:
        return rows
    reverse = sort_dir == "desc"

    def sort_value(row: dict[str, object]) -> tuple[str, str]:
        mapping = row.get("mapping") if isinstance(row.get("mapping"), dict) else None
        if sort_by == "source":
            primary = str(row.get("source_id", ""))
        elif sort_by == "field":
            primary = str(row.get("field", ""))
        elif sort_by == "raw_value":
            primary = raw_value_label(row)
        elif sort_by == "mapped_ids":
            primary = mapping_target_summary(mapping)
        else:
            primary = str(row.get("status", ""))
        return (primary.casefold(), str(row.get("key", "")).casefold())

    return sorted(rows, key=sort_value, reverse=reverse)


def render_mapping_table(
    rows: list[dict[str, object]],
    selected: dict[str, object] | None,
    selected_source: str = "",
    selected_field: str = "",
    search: str = "",
    selected_status: str = "",
    sort_by: str = "",
    sort_dir: str = "",
) -> str:
    """Render the GIS mapping rows table."""
    selected_key = str(selected.get("key", "")) if isinstance(selected, dict) else ""
    if not rows:
        return '<div class="catalog-alert"><strong>No GIS mapping values</strong><br>Run the local GIS reconstructor or add exact mappings.</div>'
    body = []
    scroll_key = "gis_mappings_scroll:" + "|".join(
        str(value)
        for value in (selected_source, selected_field, search, selected_status, sort_by, sort_dir)
    )
    for row in rows:
        key = str(row.get("key", ""))
        active = " selected" if key == selected_key else ""
        status = str(row.get("status", "") or "-")
        tone = status_tone(status)
        mapping = row.get("mapping") if isinstance(row.get("mapping"), dict) else None
        target_summary = mapping_target_summary(mapping or suggested_mapping_from_context(row.get("context")))
        raw_label = raw_value_label(row)
        row_url = mappings_query_url(
            selected_key=key,
            source_id=selected_source,
            field=selected_field,
            search=search,
            status_filter=selected_status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        body.append(
            f'<tr class="catalog-row{active}" data-href="{html.escape(row_url, quote=True)}" onclick="window.saveGisMappingListScroll(this.dataset.href)">'
            f'<td><span class="gis-table-source">{html.escape(str(row.get("source_id", "")))}</span></td>'
            f'<td><strong>{html.escape(str(row.get("field", "")))}</strong></td>'
            f'<td><span class="gis-table-raw" title="{html.escape(raw_label, quote=True)}">{html.escape(raw_label)}</span></td>'
            f'<td><span class="gis-table-targets" title="{html.escape(target_summary, quote=True)}">{html.escape(target_summary)}</span></td>'
            f'<td><span class="observation-badge {tone}">{html.escape(status)}</span></td>'
            "</tr>"
        )
    header_defs = [
        ("source", "Source"),
        ("field", "Field"),
        ("raw_value", "Raw value"),
        ("mapped_ids", "Mapped / suggested IDs"),
        ("status", "Status"),
    ]
    headers = []
    for header_key, label in header_defs:
        next_dir = "desc" if sort_by == header_key and sort_dir != "desc" else "asc"
        arrow = " ↓" if sort_by == header_key and sort_dir == "desc" else " ↑" if sort_by == header_key else ""
        href = mappings_query_url(
            source_id=selected_source,
            field=selected_field,
            search=search,
            status_filter=selected_status,
            sort_by=header_key,
            sort_dir=next_dir,
        )
        headers.append(
            f'<th><a class="table-sort-link" href="{html.escape(href, quote=True)}">{html.escape(label)}{html.escape(arrow)}</a></th>'
        )
    return (
        '<div class="gis-mapping-list-card"><div id="gis-mapping-table-shell" class="observations-table-shell catalog-table-shell gis-mapping-table-shell"><table>'
        f'<thead><tr>{"".join(headers)}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div></div>'
        '<script>'
        '(function(){'
        'const shell=document.getElementById("gis-mapping-table-shell");'
        f'const key={json.dumps(scroll_key)};'
        'if(!shell){return;}'
        'const saved=sessionStorage.getItem(key);'
        'if(saved!==null){shell.scrollTop=parseInt(saved,10)||0;}'
        'window.saveGisMappingListScroll=function(url){'
        'sessionStorage.setItem(key,String(shell.scrollTop));'
        'window.location.href=url;'
        '};'
        '})();'
        '</script>'
    )


def catalog_entry_label(item: dict[str, object]) -> str:
    """Return a human label with the stable ID visible."""
    return f"{mushroom_catalogs_ui.catalog_label(item)} · {item.get('id', '')}"


def render_catalog_checkbox_grid(
    catalogs: dict[str, object],
    catalog_group: str,
    field_name: str,
    selected_ids: list[str],
) -> str:
    """Render catalog-backed checkbox pills for mapping targets."""
    entries = catalogs.get(catalog_group)
    if not isinstance(entries, list):
        return '<p class="meta">Catalog group is not available.</p>'
    selected = set(selected_ids)
    chips = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        item_id = str(entry.get("id"))
        checked = " checked" if item_id in selected else ""
        chips.append(
            '<label class="catalog-toggle">'
            f'<input type="checkbox" name="{html.escape(field_name, quote=True)}" value="{html.escape(item_id, quote=True)}"{checked}>'
            f'<span class="catalog-chip" title="{html.escape(item_id, quote=True)}">{html.escape(catalog_entry_label(entry))}</span>'
            '</label>'
        )
    return '<div class="catalog-toggle-grid gis-mapping-target-grid">' + "".join(chips) + "</div>"


def target_fields_for_mapping(source_id: str, field: str, mapping: dict[str, object] | None) -> tuple[tuple[str, str], ...]:
    """Return relevant target catalog groups for a source field.

    Existing mappings keep any previously used target group visible even when it
    is not part of the default relevance map, so the UI never hides stored data.
    """
    relevant = list(TARGETS_BY_SOURCE_FIELD.get((source_id, field), ()))
    if isinstance(mapping, dict):
        for target_field, _catalog_group in TARGET_CATALOG_FIELDS:
            if target_field in mapping and target_field not in relevant:
                relevant.append(target_field)
    if not relevant:
        return TARGET_CATALOG_FIELDS
    return tuple(
        (target_field, catalog_group)
        for target_field, catalog_group in TARGET_CATALOG_FIELDS
        if target_field in relevant
    )


def render_mapping_detail(row: dict[str, object] | None, catalogs: dict[str, object]) -> str:
    """Render the editable mapping detail panel."""
    if not isinstance(row, dict):
        return '<aside class="catalog-detail gis-mapping-detail"><h2>GIS mapping detail</h2><p class="meta">No mapping value selected.</p></aside>'
    stored_mapping = row.get("mapping") if isinstance(row.get("mapping"), dict) else {}
    suggested_mapping = suggested_mapping_from_context(row.get("context")) if not stored_mapping else {}
    mapping = stored_mapping or suggested_mapping
    source_id = str(row.get("source_id", "") or "")
    field = str(row.get("field", "") or "")
    raw_value = str(row.get("raw_value", "") or "")
    key = str(row.get("key", "") or "")
    confidence = str(mapping.get("confidence", "") if isinstance(mapping, dict) else "") or "medium"
    if isinstance(stored_mapping, dict) and stored_mapping:
        review_status = str(mapping.get("review_status", "") or "accepted")
    elif suggested_mapping:
        review_status = suggested_status_from_context(row.get("context"))
    else:
        review_status = "pending_review"
    notes = str(mapping.get("notes", "") if isinstance(mapping, dict) else "")
    existing_index = str(row.get("index", "")) if "index" in row else ""
    status_tone_class = status_tone(review_status)
    target_sections = []
    relevant_targets = target_fields_for_mapping(source_id, field, mapping if isinstance(mapping, dict) else None)
    selected_target_count = 0
    for target_field, catalog_group in relevant_targets:
        selected_ids = mapping.get(target_field, []) if isinstance(mapping, dict) else []
        selected_ids = [str(item) for item in selected_ids] if isinstance(selected_ids, list) else []
        selected_target_count += len(selected_ids)
        target_sections.append(
            '<details class="gis-mapping-target-section" open>'
            f'<summary>{html.escape(mushroom_catalogs_ui.catalog_group_label(catalog_group))}</summary>'
            f'{render_catalog_checkbox_grid(catalogs, catalog_group, target_field, selected_ids)}'
            '</details>'
        )
    confidence_options = "".join(
        f'<option value="{value}"{" selected" if value == confidence else ""}>{value}</option>'
        for value in CONFIDENCE_VALUES
    )
    status_options = "".join(
        f'<option value="{value}"{" selected" if value == review_status else ""}>{value}</option>'
        for value in REVIEW_STATUS_VALUES
    )
    quality_status = "Stored mapping" if isinstance(stored_mapping, dict) and stored_mapping else "Candidate from reconstruction"
    if suggested_mapping:
        quality_status = "Candidate with review suggestion"
    quality_status_tone = "ok" if isinstance(stored_mapping, dict) and stored_mapping else "warn"
    active_groups = ", ".join(mushroom_catalogs_ui.catalog_group_label(group) for _field, group in relevant_targets)
    return f"""
    <aside class="catalog-detail gis-mapping-detail">
      <form method="post" action="">
        <input type="hidden" name="gis_mapping_action" value="save_exact_mapping">
        <input type="hidden" name="mapping_key" value="{html.escape(key, quote=True)}">
        <input type="hidden" name="mapping_index" value="{html.escape(existing_index, quote=True)}">
        <div class="gis-mapping-detail-fixed">
          <div class="gis-mapping-detail-head">
            <div>
              <h2>{html.escape(source_id)} · {html.escape(field)}</h2>
              <p class="meta">{html.escape(raw_value)}</p>
            </div>
            <div class="gis-mapping-detail-actions">
              <span class="observation-badge {html.escape(status_tone_class)}">{html.escape(review_status)}</span>
              <button class="primary gis-mapping-save-button">Guardar</button>
            </div>
          </div>
          <div class="catalog-entry-form compact-labels">
            <label><span>Source:</span><input name="source_id" value="{html.escape(source_id, quote=True)}" readonly></label>
            <label><span>Field:</span><input name="field" value="{html.escape(field, quote=True)}" readonly></label>
            <label><span>Raw value:</span><input name="raw_value" value="{html.escape(raw_value, quote=True)}" readonly></label>
            <label><span>Confidence:</span><select name="confidence">{confidence_options}</select></label>
            <label><span>Review status:</span><select name="review_status">{status_options}</select></label>
            <label class="span-full"><span>Notes:</span><textarea name="notes">{html.escape(notes)}</textarea></label>
          </div>
          {render_mapping_context(row, mapping if isinstance(mapping, dict) else {})}
        </div>
        <div class="gis-mapping-detail-scroll">
          <div class="gis-mapping-targets">
            {"".join(target_sections)}
          </div>
          <div class="gis-mapping-quality-grid">
            <div class="gis-mapping-quality-card">
              <strong>Use and impact</strong>
              <span><span class="observation-badge {quality_status_tone}">{html.escape(quality_status)}</span></span>
              <span>{selected_target_count} selected catalog ID(s)</span>
            </div>
            <div class="gis-mapping-quality-card">
              <strong>Validation and quality</strong>
              <span>Targets: {html.escape(active_groups)}</span>
              <span>Catalog IDs are validated before saving.</span>
            </div>
          </div>
        </div>
      </form>
    </aside>
    """


def render_full_json_panel(gis_payload: dict[str, object]) -> str:
    """Render a read-only JSON panel for traceability."""
    import json

    return (
        '<details id="gis-mappings-json" class="catalog-json-panel">'
        '<summary>JSON actual de GIS mappings</summary>'
        f'<textarea readonly>{html.escape(json.dumps(gis_payload, indent=2, ensure_ascii=False))}</textarea>'
        '</details>'
    )
