"""Server-rendered UI helpers for mushroom species maintenance.

This module intentionally contains presentation-only helpers used by the Home
Assistant web server. Keeping them outside `web_server.py` prevents the main
server from growing with every mushroom maintenance screen iteration while
preserving the existing server-side POST flow required by HA ingress.
"""

from __future__ import annotations

import html
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import urlencode


PROFILE_SELECT_VALUES = {
    "taxonomy_status": ["accepted", "species_complex_operational", "uncertain_operational_taxon"],
    "edibility": ["excellent", "good", "edible_when_thoroughly_cooked"],
    "confidence": ["very_low", "low", "medium", "high", "very_high"],
    "calibration_status": ["not_calibrated", "partially_calibrated", "locally_calibrated", "needs_review"],
    "calibration_priority": ["very_high", "high", "medium", "low"],
    "review_status": ["draft", "reviewed", "published"],
    "source_quality": ["inferred_from_literature", "expert_reviewed", "local_observations"],
    "relationship": ["primary", "preferred", "secondary", "possible", "avoid"],
}

PROFILE_AFFINITY_GROUPS = {
    "host_affinities": "host_taxa",
    "forest_type_affinities": "forest_types",
    "soil_affinities": "soil_types",
    "lithology_affinities": "lithology_types",
    "habitat_feature_affinities": "habitat_features",
}

UI_LANGUAGE = os.environ.get("RAINMAPPER_MUSHROOM_UI_LANGUAGE", "en").strip().lower() or "en"


ICONS = {
    "mushroom": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 10.5C4.6 6.2 8.1 3.5 12 3.5s7.4 2.7 8 7c.1.7-.5 1.3-1.2 1.3H5.2c-.7 0-1.3-.6-1.2-1.3Z"/><path d="M9.2 11.8c.1 2.6-.6 5-1.8 7.2h9.2c-1.2-2.2-1.9-4.6-1.8-7.2"/><path d="M9.3 7.2h.1M14.8 7.1h.1M12 9.1h.1"/></svg>',
    "identity": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/></svg>',
    "ecology": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21V8"/><path d="M7 10c0-3.5 2.6-6 5-7 2.4 1 5 3.5 5 7a5 5 0 0 1-10 0Z"/><path d="M12 14c-3.2 0-5.5 1.7-7 4 2.2 1.1 4.6 1.4 7 1.4s4.8-.3 7-1.4c-1.5-2.3-3.8-4-7-4Z"/></svg>',
    "phenology": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3v4M17 3v4M4 9h16"/><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 13h2M12 13h2M16 13h2M8 17h2M12 17h2"/></svg>',
    "weather": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18a4 4 0 0 1 0-8 6 6 0 0 1 11.4 1.9A3.3 3.3 0 0 1 18 18H7Z"/><path d="M9 21v-1M13 21v-1M17 21v-1"/></svg>',
    "scoring": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-4M12 16V8M16 16v-7"/></svg>',
    "calibration": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="4"/><path d="m15 9 3-3M9 15l-3 3M9 9 6 6M15 15l3 3"/></svg>',
    "metadata": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>',
    "rain": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 16a4 4 0 0 1 0-8 5.5 5.5 0 0 1 10.4 1.8A3.1 3.1 0 0 1 17 16H7Z"/><path d="M8 20l1-2M12 21l1-3M16 20l1-2"/></svg>',
    "temperature": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14.5V5a2 2 0 1 1 4 0v9.5a4 4 0 1 1-4 0Z"/><path d="M12 8v8"/></svg>',
    "humidity": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3s6 6.2 6 11a6 6 0 0 1-12 0c0-4.8 6-11 6-11Z"/><path d="M9.5 14.5c.6 1.4 1.6 2.1 3 2.1"/></svg>',
    "wind": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h10a2 2 0 1 0-2-2"/><path d="M4 12h15a2 2 0 1 1-2 2"/><path d="M4 16h8"/></svg>',
    "host": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21V9"/><path d="M7 10c0-3.4 2.5-5.8 5-7 2.5 1.2 5 3.6 5 7a5 5 0 0 1-10 0Z"/><path d="M12 15c-2.8 0-5 1.3-7 3.4"/></svg>',
    "soil": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17c3-2 5-2 8 0s5 2 8 0"/><path d="M4 13c3-2 5-2 8 0s5 2 8 0"/><path d="M7 9h.1M12 8h.1M17 9h.1"/></svg>',
    "topography": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 18 9 7l4 7 2-3 6 7H3Z"/><path d="M9 7l2.2 3.8"/></svg>',
}


def icon(name: str) -> str:
    """Return a small inline SVG icon with inherited stroke color."""
    return ICONS.get(name, "")


def parameter_label_candidates() -> list[Path]:
    """Return candidate parameter-label dictionaries for HA and local runs."""
    configured_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", "").strip()
    candidates = []
    if configured_defaults:
        candidates.append(Path(configured_defaults) / "mushroom_labels.json")
    candidates.extend(
        [
            Path("/app/mushroom-data/mushroom_labels.json"),
        ]
    )
    module_path = Path(__file__).resolve()
    if len(module_path.parents) > 2:
        candidates.append(module_path.parents[2] / "mushroom-data" / "mushroom_labels.json")
    return candidates


def load_parameter_labels() -> dict[str, dict[str, str]]:
    """Load human labels from mushroom-data with a safe empty fallback."""
    for candidate in parameter_label_candidates():
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


PARAMETER_LABELS = load_parameter_labels()


def profile_query_url(species_id: str = "", search: str = "", mode: str = "", section: str = "") -> str:
    """Return an ingress-safe query URL for the species maintenance page."""
    params = {}
    if species_id:
        params["id"] = species_id
    if search:
        params["q"] = search
    if mode:
        params["mode"] = mode
    if section:
        params["section"] = section
    return ("?" + urlencode(params)) if params else "?"


def nested_dict(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return a nested object only when it is a dictionary."""
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def profile_common_name(profile: dict[str, object]) -> str:
    """Return the first common name as compact display text."""
    names = profile.get("common_names")
    if isinstance(names, list) and names:
        return str(names[0])
    return ""


def textarea_value(values: object) -> str:
    """Format scalar/list textarea values using one item per line."""
    if isinstance(values, list):
        return "\n".join(str(value) for value in values)
    if values is None:
        return ""
    return str(values)


def localized_label(labels: dict[str, str], language: str = UI_LANGUAGE) -> str:
    """Return a translated label or an explicit missing-language marker."""
    return labels.get(language) or labels.get("en") or f"missing label: {language}"


def ui_label(key: str, language: str = UI_LANGUAGE) -> str:
    """Return a translated mushroom UI label or an explicit missing-label marker."""
    labels = PARAMETER_LABELS.get(key)
    if not labels:
        return f"missing label: {key}"
    return localized_label(labels, language)


def value_label(value: object, language: str = UI_LANGUAGE) -> str:
    """Return a translated controlled value label without hiding missing entries."""
    if value is None or value == "":
        return "-"
    text = str(value)
    labels = PARAMETER_LABELS.get(f"value.{text}")
    if not labels:
        return f"missing label: value.{text}"
    return localized_label(labels, language)


def catalog_label(item: dict[str, object], language: str = UI_LANGUAGE) -> str:
    """Return a catalog label using the configured mushroom UI language."""
    label = item.get("label")
    if isinstance(label, dict):
        translations = {str(key): str(value) for key, value in label.items() if value}
        if translations:
            return localized_label(translations, language)
    scientific = item.get("scientific_name")
    if scientific:
        return str(scientific)
    return str(item.get("id", ""))


def catalog_options_for_group(catalogs: dict[str, object], group: str) -> list[tuple[str, str]]:
    """Return stable catalog options for select controls."""
    items = catalogs.get(group)
    if not isinstance(items, list):
        return []
    options = []
    sorted_items = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: (
            item.get("sort_order") if isinstance(item.get("sort_order"), (int, float)) else 999999,
            str(item.get("id", "")),
        ),
    )
    for item in sorted_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "") or "").strip()
        if item_id:
            options.append((item_id, catalog_label(item)))
    return options


def css_token(value: object) -> str:
    """Return a conservative CSS token for known controlled values."""
    text = str(value or "").strip().lower().replace(" ", "_")
    return "".join(character if character.isalnum() or character in ("_", "-") else "_" for character in text)


def value_chip(value: object, label: str = "") -> str:
    """Render a compact status chip."""
    raw = str(value or "-")
    text = value_label(value) if value not in (None, "", "-") else "-"
    label_html = f'<span class="profile-chip-label">{html.escape(label)}</span>' if label else ""
    css_class = css_token(raw)
    return f'<span class="profile-status-chip {html.escape(css_class, quote=True)}">{label_html}{html.escape(text)}</span>'


def card_title(number: int, title: str, icon_name: str) -> str:
    """Render a numbered dashboard card title with a lightweight inline icon."""
    return (
        '<h3 class="profile-card-title">'
        f'<span class="profile-card-icon">{icon(icon_name)}</span>'
        f'<span>{number}. {html.escape(title)}</span>'
        "</h3>"
    )


def value_row(label: str, value: object, css_class: str = "") -> str:
    """Render a compact read-only field used by summary cards."""
    return (
        f'<div class="profile-kv {html.escape(css_class)}">'
        f'<span>{html.escape(label)}</span><strong>{html.escape(str(value if value not in (None, "") else "-"))}</strong></div>'
    )


def value_html_row(label: str, value_html: str, css_class: str = "") -> str:
    """Render a compact row whose value was already produced by trusted helpers."""
    return (
        f'<div class="profile-kv {html.escape(css_class)}">'
        f'<span>{html.escape(label)}</span><strong>{value_html}</strong></div>'
    )


def compact_list(values: object, limit: int = 5) -> str:
    """Render short comma-separated summaries without losing overflow context."""
    items = [str(value) for value in values] if isinstance(values, list) else []
    if not items:
        return "-"
    visible = items[:limit]
    suffix = f" +{len(items) - limit}" if len(items) > limit else ""
    return ", ".join(visible) + suffix


def month_chips(values: object, active_class: str = "active") -> str:
    """Render month arrays as compact chips, preserving invalid raw values."""
    months = values if isinstance(values, list) else []
    rendered = []
    for month in range(1, 13):
        css_class = f" {active_class}" if month in months else ""
        rendered.append(f'<span class="month-chip{css_class}">{html.escape(ui_label(f"month.{month}"))}</span>')
    extras = [value for value in months if not isinstance(value, int) or value < 1 or value > 12]
    rendered.extend(f'<span class="month-chip warn">{html.escape(str(value))}</span>' for value in extras)
    return '<div class="month-chip-grid">' + "".join(rendered) + "</div>"


def score_bar(label: str, value: object) -> str:
    """Render a scoring weight as a horizontal bar."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    width = max(0, min(100, int(number * 100)))
    return (
        '<div class="score-row">'
        f'<span>{html.escape(parameter_label(label))}</span>'
        f'<div class="score-track"><span style="width:{width}%"></span></div>'
        f'<strong>{number:.2f}</strong></div>'
    )


def form_field(
    name: str,
    label: str,
    value: object = "",
    field_type: str = "text",
    readonly: bool = False,
    step: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
) -> str:
    """Render a standard form input preserving current POST field names."""
    readonly_attr = " readonly" if readonly else ""
    step_value = step if step is not None else "any"
    step_attr = f' step="{html.escape(step_value, quote=True)}"' if field_type == "number" else ""
    min_attr = f' min="{html.escape(minimum, quote=True)}"' if field_type == "number" and minimum is not None else ""
    max_attr = f' max="{html.escape(maximum, quote=True)}"' if field_type == "number" and maximum is not None else ""
    checked_attr = ' checked' if field_type == "checkbox" and value is True else ""
    escaped_name = html.escape(name, quote=True)
    if field_type == "checkbox":
        control = f'<input id="profile-{escaped_name}" name="{escaped_name}" type="checkbox" value="true"{checked_attr}>'
    else:
        escaped_value = html.escape("" if value is None else str(value), quote=True)
        inputmode_attr = ' inputmode="decimal"' if field_type == "number" else ""
        control = (
            f'<input id="profile-{escaped_name}" name="{escaped_name}" type="{html.escape(field_type, quote=True)}" '
            f'value="{escaped_value}"{step_attr}{min_attr}{max_attr}{inputmode_attr}{readonly_attr}>'
        )
    return '<div class="admin-field">' f'<label for="profile-{escaped_name}">{html.escape(label)}</label>{control}</div>'


def form_select(name: str, label: str, value: object, options: list[str]) -> str:
    """Render a select control preserving unknown current values."""
    current = "" if value is None else str(value)
    merged = list(options)
    if current and current not in merged:
        merged.append(current)
    option_html = [f'<option value=""{" selected" if not current else ""}>-</option>']
    for option in merged:
        selected = " selected" if option == current else ""
        option_html.append(f'<option value="{html.escape(option, quote=True)}"{selected}>{html.escape(value_label(option))}</option>')
    escaped_name = html.escape(name, quote=True)
    return (
        '<div class="admin-field">'
        f'<label for="profile-{escaped_name}">{html.escape(label)}</label>'
        f'<select id="profile-{escaped_name}" name="{escaped_name}">{"".join(option_html)}</select></div>'
    )


def form_catalog_select(name: str, label: str, value: object, options: list[tuple[str, str]]) -> str:
    """Render a catalog-backed select with human labels and stable IDs."""
    current = "" if value is None else str(value)
    option_ids = [option_id for option_id, _label in options]
    option_html = [f'<option value=""{" selected" if not current else ""}>-</option>']
    for option_id, option_label in options:
        selected = " selected" if option_id == current else ""
        visible_label = option_id if option_label == option_id else f"{option_id} · {option_label}"
        option_html.append(
            f'<option value="{html.escape(option_id, quote=True)}"{selected}>{html.escape(visible_label)}</option>'
        )
    if current and current not in option_ids:
        option_html.append(f'<option value="{html.escape(current, quote=True)}" selected>{html.escape(current)} (missing)</option>')
    escaped_name = html.escape(name, quote=True)
    return (
        '<div class="admin-field">'
        f'<label for="profile-{escaped_name}">{html.escape(label)}</label>'
        f'<select id="profile-{escaped_name}" name="{escaped_name}">{"".join(option_html)}</select></div>'
    )


def form_textarea(name: str, label: str, value: object, rows: int = 3) -> str:
    """Render a textarea using one logical value per line."""
    escaped_name = html.escape(name, quote=True)
    return (
        '<div class="admin-field">'
        f'<label for="profile-{escaped_name}">{html.escape(label)}</label>'
        f'<textarea id="profile-{escaped_name}" name="{escaped_name}" rows="{rows}">{html.escape(textarea_value(value))}</textarea></div>'
    )


def form_month_toggles(name: str, label: str, values: object, active_class: str = "active") -> str:
    """Render editable month checkboxes as compact visual chips."""
    selected = {value for value in values if isinstance(value, int)} if isinstance(values, list) else set()
    escaped_name = html.escape(name, quote=True)
    chips = []
    for month in range(1, 13):
        checked = " checked" if month in selected else ""
        chips.append(
            '<label class="month-toggle">'
            f'<input type="checkbox" name="{escaped_name}" value="{month}"{checked}>'
            f'<span class="month-chip {html.escape(active_class)}">{html.escape(ui_label(f"month.{month}"))}</span>'
            "</label>"
        )
    return (
        '<div class="admin-field month-toggle-field">'
        f'<span class="field-label">{html.escape(label)}</span>'
        f'<div class="month-toggle-grid">{"".join(chips)}</div>'
        "</div>"
    )


def form_catalog_toggles(
    name: str,
    label: str,
    values: object,
    catalogs: dict[str, object],
    group: str,
) -> str:
    """Render editable catalog-backed checkboxes as compact visual chips."""
    selected = {str(value) for value in values if str(value or "")} if isinstance(values, list) else set()
    labels = catalog_label_map(catalogs, group)
    items = catalogs.get(group)
    items = items if isinstance(items, list) else []
    escaped_name = html.escape(name, quote=True)
    chips = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "") or "")
        if not item_id:
            continue
        checked = " checked" if item_id in selected else ""
        chips.append(
            '<label class="catalog-toggle">'
            f'<input type="checkbox" name="{escaped_name}" value="{html.escape(item_id, quote=True)}"{checked}>'
            f'<span class="catalog-chip">{html.escape(labels.get(item_id, item_id))}</span>'
            "</label>"
        )
    extras = sorted(selected - {str(item.get("id", "") or "") for item in items if isinstance(item, dict)})
    chips.extend(
        '<span class="catalog-chip missing">'
        f'{html.escape(value)}'
        '</span>'
        for value in extras
    )
    return (
        '<div class="admin-field catalog-toggle-field">'
        f'<span class="field-label">{html.escape(label)}</span>'
        f'<div class="catalog-toggle-grid">{"".join(chips)}</div>'
        "</div>"
    )


def parameter_unit(name: str) -> str:
    """Infer a compact unit label from a parameter key."""
    if name.endswith("_mm"):
        return "mm"
    if name.endswith("_c"):
        return "C"
    if name.endswith("_pct"):
        return "%"
    if name.endswith("_kmh"):
        return "km/h"
    if name.endswith("_m"):
        return "m"
    if name.endswith("_days"):
        return "d"
    return ""


def parameter_label(name: str, language: str = UI_LANGUAGE) -> str:
    """Return a short human label for a model parameter key."""
    labels = PARAMETER_LABELS.get(name)
    if labels:
        return localized_label(labels, language)
    return f"missing label: {name}"


def parameter_field(name: str, label: str, value: object, unit: str = "", field_type: str = "number", **attrs: str) -> str:
    """Render a dense label/input row for the Parameters screen."""
    escaped_name = html.escape(name, quote=True)
    escaped_label = html.escape(label)
    if field_type == "checkbox":
        checked_attr = ' checked' if value is True else ""
        return (
            '<label class="parameter-switch-row">'
            f'<span>{escaped_label}</span>'
            f'<input id="profile-{escaped_name}" name="{escaped_name}" type="checkbox" value="true"{checked_attr}>'
            f'<em>{html.escape(ui_label("ui.yes"))}</em></label>'
        )
    step_value = attrs.get("step", "any")
    step_attr = f' step="{html.escape(step_value, quote=True)}"'
    min_attr = f' min="{html.escape(attrs["minimum"], quote=True)}"' if "minimum" in attrs else ""
    max_attr = f' max="{html.escape(attrs["maximum"], quote=True)}"' if "maximum" in attrs else ""
    unit_html = f'<span class="parameter-unit">{html.escape(unit)}</span>' if unit else ""
    escaped_value = html.escape("" if value is None else str(value), quote=True)
    return (
        '<label class="parameter-field-row">'
        f'<span>{escaped_label}</span>'
        '<span class="parameter-input-shell">'
        f'<input id="profile-{escaped_name}" name="{escaped_name}" type="{html.escape(field_type, quote=True)}" '
        f'value="{escaped_value}"{step_attr}{min_attr}{max_attr} inputmode="decimal">'
        f'{unit_html}</span></label>'
    )


def parameter_textarea(name: str, label: str, value: object, rows: int = 1) -> str:
    """Render a compact textarea row for list-like Parameters fields."""
    escaped_name = html.escape(name, quote=True)
    return (
        '<label class="parameter-text-row">'
        f'<span>{html.escape(label)}</span>'
        f'<textarea id="profile-{escaped_name}" name="{escaped_name}" rows="{rows}">{html.escape(textarea_value(value))}</textarea></label>'
    )


def catalog_label_map(catalogs: dict[str, object], group: str) -> dict[str, str]:
    """Return catalog labels indexed by ID for compact read-only summaries."""
    return {item_id: label for item_id, label in catalog_options_for_group(catalogs, group)}


def catalog_display(catalogs: dict[str, object], group: str, item_id: object) -> str:
    """Return a translated catalog label for an ID, exposing missing catalog rows."""
    text = str(item_id or "").strip()
    if not text:
        return "-"
    return catalog_label_map(catalogs, group).get(text, f"{text} (missing)")


def catalog_compact_list(catalogs: dict[str, object], group: str, values: object, limit: int = 5) -> str:
    """Render translated catalog labels from a list of IDs."""
    items = values if isinstance(values, list) else []
    labels = [catalog_display(catalogs, group, item) for item in items[:limit]]
    if not labels:
        return "-"
    suffix = f" +{len(items) - limit}" if len(items) > limit else ""
    return ", ".join(labels) + suffix


def catalog_select_options(
    catalogs: dict[str, object],
    group: str,
    current: str = "",
    empty_label: str = "",
) -> str:
    """Render select options from a reference catalog group."""
    options = []
    if empty_label:
        selected = " selected" if not current else ""
        options.append(f'<option value=""{selected}>{html.escape(empty_label)}</option>')
    seen: set[str] = set()
    for item_id, label in catalog_options_for_group(catalogs, group):
        seen.add(item_id)
        selected = " selected" if item_id == current else ""
        options.append(
            f'<option value="{html.escape(item_id, quote=True)}"{selected}>{html.escape(label)}</option>'
        )
    if current and current not in seen:
        options.append(
            f'<option value="{html.escape(current, quote=True)}" selected>{html.escape(current)} (missing)</option>'
        )
    return "".join(options)


def affinity_chip_list(
    ecology: dict[str, object],
    key: str,
    labels: dict[str, str],
    relationship: str | None = None,
    exclude_relationships: set[str] | None = None,
    limit: int = 6,
) -> str:
    """Render affinity rows as compact chips, optionally filtered by relationship."""
    raw_items = ecology.get(key)
    items = raw_items if isinstance(raw_items, list) else []
    chips = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "") or "")
        if not item_id:
            continue
        item_relationship = str(item.get("relationship", "") or "")
        if relationship and item_relationship != relationship:
            continue
        if exclude_relationships and item_relationship in exclude_relationships:
            continue
        label = labels.get(item_id, item_id)
        visible_label = label if label != item_id else item_id
        relationship_html = f'<em>{html.escape(item_relationship)}</em>' if item_relationship and not relationship else ""
        chips.append(
            f'<span class="parameter-affinity-chip" title="{html.escape(item_id, quote=True)}">'
            f'{html.escape(visible_label)}{relationship_html}</span>'
        )
    if not chips:
        return '<span class="parameter-empty">-</span>'
    visible = chips[:limit]
    if len(chips) > limit:
        visible.append(f'<span class="parameter-affinity-chip muted">+{len(chips) - limit}</span>')
    return '<span class="parameter-chip-row">' + "".join(visible) + "</span>"


def render_new_species_form() -> str:
    """Render the guided species creation modal."""
    return f"""
    <div id="new-species-modal" class="modal-layer">
      <a class="modal-backdrop" href="?" aria-label="{html.escape(ui_label("ui.cancel"), quote=True)}"></a>
      <section class="modal-card">
        <header class="modal-head">
          <div>
            <h2>{html.escape(ui_label("ui.new_species"))}</h2>
            <p>{html.escape(ui_label("ui.create_species_help"))}</p>
          </div>
          <a class="button-link" href="?">{html.escape(ui_label("ui.cancel"))}</a>
        </header>
        <form class="catalog-create-form" method="post" action="" onsubmit="return confirm('Create this draft species profile and validate the full dataset?')">
          <input type="hidden" name="profile_action" value="create_profile">
          <div class="admin-form-grid">
            <div class="admin-field">
              <label>{html.escape(ui_label("ui.species_id"))}</label>
              <input name="new_species_id" placeholder="boletus_example" required>
            </div>
            <div class="admin-field">
              <label>{html.escape(ui_label("ui.scientific_name"))}</label>
              <input name="new_scientific_name" placeholder="Boletus example" required>
            </div>
            <div class="admin-field">
              <label>{html.escape(ui_label("ui.common_name"))}</label>
              <input name="new_common_name" placeholder="optional">
            </div>
          </div>
          <div class="modal-actions">
            <a class="button-link" href="?">{html.escape(ui_label("ui.cancel"))}</a>
            <button class="primary">{html.escape(ui_label("ui.create_species"))}</button>
          </div>
        </form>
      </section>
    </div>
    """


def render_archived_species_panel(archived_profiles: list[dict[str, object]]) -> str:
    """Render restore/permanent-delete controls for archived species."""
    rows = []
    for profile in sorted(archived_profiles, key=lambda item: str(item.get("species_id", ""))):
        species_id = str(profile.get("species_id", "") or "")
        if not species_id:
            continue
        name = str(profile.get("scientific_name", species_id) or species_id)
        common_name = profile_common_name(profile)
        rows.append(
            '<div class="archived-species-row">'
            f'<div><strong>{html.escape(name)}</strong><span class="meta">{html.escape(common_name)} · {html.escape(species_id)}</span></div>'
            '<div class="archived-species-actions">'
            '<form method="post" action="" onsubmit="return confirm(\'Restore this archived species profile?\')">'
            '<input type="hidden" name="profile_action" value="restore_profile">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<button class="secondary">{html.escape(ui_label("ui.restore_species"))}</button>'
            "</form>"
            '<form method="post" action="" onsubmit="return confirm(\'Delete this archived species permanently?\') && confirm(\'This action cannot be undone. The archived copy will be removed permanently.\')">'
            '<input type="hidden" name="profile_action" value="delete_archived_profile">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="delete_confirm_id" value="{html.escape(species_id, quote=True)}">'
            f'<button class="danger-button">{html.escape(ui_label("ui.delete_permanently"))}</button>'
            "</form>"
            "</div></div>"
        )
    content = "".join(rows) if rows else f'<p class="meta">{html.escape(ui_label("ui.no_archived_species"))}</p>'
    return (
        '<div id="restore-species-modal" class="modal-layer">'
        '<a class="modal-backdrop" href="?" aria-label="Cancel restore species"></a>'
        '<section class="modal-card modal-card-wide">'
        '<header class="modal-head"><div>'
        f'<h2>{html.escape(ui_label("ui.restore_species"))}</h2><p>{len(rows)} {html.escape(ui_label("ui.archived_species_count"))}.</p>'
        f'</div><a class="button-link" href="?">{html.escape(ui_label("ui.cancel"))}</a></header>'
        f'<div class="archived-species-panel">{content}</div>'
        f'<div class="modal-actions"><a class="button-link" href="?">{html.escape(ui_label("ui.cancel"))}</a></div>'
        '</section></div>'
    )


def selected_profile(profiles: list[dict[str, object]], species_id: str) -> dict[str, object] | None:
    """Return the requested profile or the first available profile."""
    if species_id:
        for profile in profiles:
            if str(profile.get("species_id", "")) == species_id:
                return profile
    return profiles[0] if profiles else None


def profile_metric_cards(profiles: list[dict[str, object]], errors: list[object], warnings: list[object]) -> str:
    """Render top-level profile health metrics in a single compact strip."""
    accepted = 0
    operational = 0
    uncalibrated = 0
    draft = 0
    priority = 0
    human = 0
    for profile in profiles:
        taxonomy = str(profile.get("taxonomy_status", ""))
        if taxonomy == "accepted":
            accepted += 1
        elif taxonomy:
            operational += 1
        confidence = nested_dict(profile, "prediction_confidence")
        metadata = nested_dict(profile, "metadata")
        if confidence.get("local_calibration_status") == "not_calibrated":
            uncalibrated += 1
        if metadata.get("review_status") == "draft":
            draft += 1
        if confidence.get("calibration_priority") in {"high", "very_high"}:
            priority += 1
        if metadata.get("requires_human_validation") is True:
            human += 1
    cards = [
        (ui_label("ui.species"), str(len(profiles)), ""),
        (ui_label("ui.accepted"), str(accepted), "ok"),
        (ui_label("ui.operational"), str(operational), "warn" if operational else ""),
        (ui_label("ui.uncalibrated"), str(uncalibrated), "warn" if uncalibrated else "ok"),
        (ui_label("ui.draft"), str(draft), "warn" if draft else "ok"),
        (ui_label("ui.high_priority"), str(priority), "warn" if priority else "ok"),
        (ui_label("ui.human_validation"), str(human), "warn" if human else "ok"),
        (ui_label("ui.validation"), f"{len(errors)} {ui_label('ui.errors')} · {len(warnings)} {ui_label('ui.warnings')}", "danger" if errors else "warn" if warnings else "ok"),
    ]
    return '<div class="profile-metrics profile-metrics-compact">' + "".join(
        f'<div class="profile-metric"><span class="label">{html.escape(label)}</span>'
        f'<span class="value {css_class}">{html.escape(value)}</span></div>'
        for label, value, css_class in cards
    ) + "</div>"


def render_profile_list(profiles: list[dict[str, object]], selected_id: str, search: str) -> str:
    """Render the left species navigator."""
    tokens = [token.lower() for token in search.split() if token.strip()]
    rows = []
    sorted_profiles = sorted(
        profiles,
        key=lambda item: (
            str(item.get("scientific_name", "") or item.get("species_id", "")).casefold(),
            str(item.get("species_id", "")).casefold(),
        ),
    )
    for profile in sorted_profiles:
        species_id = str(profile.get("species_id", ""))
        scientific_name = str(profile.get("scientific_name", ""))
        common_name = profile_common_name(profile)
        confidence = nested_dict(profile, "prediction_confidence")
        metadata = nested_dict(profile, "metadata")
        searchable = " ".join(
            [
                species_id,
                scientific_name,
                common_name,
                str(profile.get("taxonomy_status", "")),
                str(profile.get("edibility", "")),
                str(confidence.get("overall_confidence", "")),
                str(confidence.get("calibration_priority", "")),
                str(metadata.get("review_status", "")),
            ]
        ).lower()
        if tokens and not all(token in searchable for token in tokens):
            continue
        active = " active" if species_id == selected_id else ""
        chip_items = (
            (confidence.get("overall_confidence", ""), ui_label("ui.overall_confidence")),
            (confidence.get("calibration_priority", ""), ui_label("ui.calibration_priority")),
            (metadata.get("review_status", ""), ui_label("ui.review_status")),
        )
        chips = "".join(
            f'<span class="profile-chip {html.escape(str(value))}" title="{html.escape(label, quote=True)}: {html.escape(value_label(value), quote=True)}">{html.escape(value_label(value))}</span>'
            for value, label in chip_items
            if value
        )
        rows.append(
            f'<a class="profile-list-item{active}" href="{profile_query_url(species_id, search)}">'
            f'<span class="profile-list-icon">{icon("mushroom")}</span>'
            '<span class="profile-list-main">'
            f"<strong>{html.escape(scientific_name or species_id)}</strong>"
            f'<span class="meta">{html.escape(common_name or species_id)}</span></span>'
            f'<span class="profile-chip-line">{chips}</span></a>'
        )
    if not rows:
        rows.append(f'<div class="profile-list-item"><strong>{html.escape(ui_label("ui.no_species_match"))}</strong><span class="meta">{html.escape(ui_label("ui.adjust_search"))}</span></div>')
    legend = (
        f'<span class="profile-list-title">{html.escape(ui_label("ui.species"))}</span>'
        '<span class="profile-list-chip-legend">'
        f'<span title="{html.escape(ui_label("ui.overall_confidence"), quote=True)}">{html.escape(ui_label("ui.profile_list_confidence_short"))}</span>'
        f'<span title="{html.escape(ui_label("ui.calibration_priority"), quote=True)}">{html.escape(ui_label("ui.profile_list_priority_short"))}</span>'
        f'<span title="{html.escape(ui_label("ui.review_status"), quote=True)}">{html.escape(ui_label("ui.profile_list_review_short"))}</span>'
        "</span>"
    )
    return f'<aside class="profile-list"><div class="profile-list-search-title">{legend}</div><div class="profile-list-rows">' + "".join(rows) + "</div></aside>"


def render_section_tabs(active_section: str, selected_id: str, search: str) -> str:
    """Render top-level mushroom maintenance tabs as ingress-safe links."""
    sections = [
        ("summary", ui_label("ui.summary")),
        ("species", ui_label("ui.species")),
        ("observations", ui_label("ui.observations")),
        ("parameters", ui_label("ui.parameters")),
        ("calibration", ui_label("ui.calibration")),
    ]
    links = []
    for section, label in sections:
        active = ' class="active"' if section == active_section else ""
        href = profile_query_url(selected_id, search, section=section)
        links.append(f'<a{active} href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    return '<nav class="mushroom-section-tabs" aria-label="Mushroom maintenance sections">' + "".join(links) + "</nav>"


def render_selected_species_header(profile: dict[str, object] | None, section: str) -> str:
    """Render the selected species banner shared by section-level screens."""
    if not profile:
        return f'<section class="card profile-section-screen"><h2>{html.escape(ui_label("ui.no_species_selected"))}</h2><p class="meta">{html.escape(ui_label("ui.create_or_select_species"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    confidence = nested_dict(profile, "prediction_confidence")
    metadata = nested_dict(profile, "metadata")
    chips = "".join(
        [
            value_chip(profile.get("taxonomy_status", "-"), ui_label("ui.taxonomy")),
            value_chip(confidence.get("overall_confidence", "-"), ui_label("ui.confidence")),
            value_chip(confidence.get("local_calibration_status", "-"), ui_label("ui.calibration")),
            value_chip(confidence.get("calibration_priority", "-"), ui_label("ui.priority")),
            value_chip(metadata.get("review_status", "-"), ui_label("ui.review_status")),
        ]
    )
    return f"""
    <header class="profile-section-banner">
      <div class="profile-title-block">
        <span class="profile-hero-icon">{icon("mushroom")}</span>
        <div>
          <span class="meta">{html.escape(section)}</span>
          <h2>{html.escape(str(profile.get("scientific_name", species_id)))}</h2>
          <p class="meta">species_id: {html.escape(species_id)} · {html.escape(profile_common_name(profile) or "-")}</p>
        </div>
      </div>
      <div class="profile-hero-chips">{chips}</div>
    </header>
    """


def render_profile_affinity_rows(field: str, values: object, catalogs: dict[str, object]) -> str:
    """Render editable affinity rows while hiding already-used IDs from new rows."""
    catalog_group = PROFILE_AFFINITY_GROUPS[field]
    options = catalog_options_for_group(catalogs, catalog_group)
    affinities = values if isinstance(values, list) else []
    used_ids = {
        str(item.get("id", "") or "").strip()
        for item in affinities
        if isinstance(item, dict) and str(item.get("id", "") or "").strip()
    }
    rows = []
    editable_rows = [item if isinstance(item, dict) else {} for item in affinities] + [{} for _ in range(3)]
    for index, item in enumerate(editable_rows):
        current_id = str(item.get("id", "") or "").strip()
        row_options = [option for option in options if option[0] == current_id or option[0] not in used_ids]
        rows.append(
            '<div class="profile-affinity-row">'
            + form_catalog_select(f"{field}_{index}_id", "ID", current_id, row_options)
            + form_select(f"{field}_{index}_relationship", ui_label("ui.relationship"), item.get("relationship", ""), PROFILE_SELECT_VALUES["relationship"])
            + form_field(f"{field}_{index}_affinity", ui_label("ui.affinity"), item.get("affinity", ""), field_type="number")
            + "</div>"
        )
    return (
        f'<div class="profile-affinity-block {html.escape(field)}">'
        f'<h2>{html.escape(field.replace("_", " ").title())}</h2>'
        + "".join(rows)
        + "</div>"
    )


def render_ecology_affinity_tabs(ecology: dict[str, object], catalogs: dict[str, object]) -> str:
    """Render ecology affinity groups as internal subtabs without changing POST fields."""
    fields = list(PROFILE_AFFINITY_GROUPS)
    labels = {
        "host_affinities": ui_label("ui.primary_hosts"),
        "forest_type_affinities": ui_label("ui.forest_types"),
        "soil_affinities": ui_label("ui.soils"),
        "lithology_affinities": ui_label("ui.lithology"),
        "habitat_feature_affinities": ui_label("ui.habitat_features"),
    }
    radios = []
    tab_labels = []
    panels = []
    for index, field in enumerate(fields):
        tab_id = f"eco-tab-{index}"
        radios.append(f'<input type="radio" name="ecology_tab" id="{tab_id}"{" checked" if index == 0 else ""}>')
        tab_labels.append(f'<label for="{tab_id}">{html.escape(labels[field])}</label>')
        panels.append(f'<section class="ecology-subtab-panel panel-{index}">{render_profile_affinity_rows(field, ecology.get(field, []), catalogs)}</section>')
    return (
        '<div class="ecology-subtabs">'
        + "".join(radios)
        + '<div class="ecology-subtab-labels">'
        + "".join(tab_labels)
        + "</div>"
        + '<div class="ecology-subtab-content">'
        + "".join(panels)
        + "</div></div>"
    )


def render_weather_summary(weather_model: dict[str, object]) -> str:
    """Render a compact weather summary from the current model blocks."""
    rainfall = weather_model.get("rainfall") if isinstance(weather_model.get("rainfall"), dict) else {}
    temperature = weather_model.get("temperature") if isinstance(weather_model.get("temperature"), dict) else {}
    humidity = weather_model.get("humidity") if isinstance(weather_model.get("humidity"), dict) else {}
    wind = weather_model.get("wind") if isinstance(weather_model.get("wind"), dict) else {}
    return f"""
    <div class="profile-weather-grid">
      <div>{value_row(parameter_label("rain_7d_min_mm"), rainfall.get("rain_7d_min_mm"))}{value_row(ui_label("ui.rain_15d_optimal"), f'{rainfall.get("rain_15d_optimal_min_mm", "-")} - {rainfall.get("rain_15d_optimal_max_mm", "-")} mm')}{value_row(ui_label("ui.rain_saturation"), rainfall.get("rain_30d_saturation_penalty_mm"))}</div>
      <div>{value_row(ui_label("ui.temp_min_optimal"), f'{temperature.get("temp_min_7d_optimal_min_c", "-")} - {temperature.get("temp_min_7d_optimal_max_c", "-")} °C')}{value_row(ui_label("ui.temp_max_optimal"), f'{temperature.get("temp_max_7d_optimal_min_c", "-")} - {temperature.get("temp_max_7d_optimal_max_c", "-")} °C')}{value_row(parameter_label("heat_penalty_temp_max_c"), temperature.get("heat_penalty_temp_max_c"))}{value_row(parameter_label("frost_penalty_temp_min_c"), temperature.get("frost_penalty_temp_min_c"))}</div>
      <div>{value_row(parameter_label("humidity_min_7d_preferred_min_pct"), humidity.get("humidity_min_7d_preferred_min_pct"))}{value_row(ui_label("ui.humidity_optimal"), humidity.get("humidity_max_7d_preferred_min_pct"))}{value_row(parameter_label("dry_wind_sensitive"), ui_label("ui.yes") if wind.get("dry_wind_sensitive") is True else ui_label("ui.no"))}</div>
      <div>{value_row(parameter_label("wind_avg_3d_penalty_kmh"), wind.get("wind_avg_3d_penalty_kmh"))}{value_row(ui_label("ui.gust_penalty"), wind.get("wind_gust_3d_penalty_kmh"))}</div>
    </div>
    """


def render_general_dashboard(
    profile: dict[str, object],
    catalogs: dict[str, object],
    ecology: dict[str, object],
    phenology: dict[str, object],
    topography: dict[str, object],
    weather_model: dict[str, object],
    scoring: dict[str, object],
    confidence: dict[str, object],
    metadata: dict[str, object],
) -> str:
    """Render the visual first-tab dashboard inspired by the species mockup."""
    delay = phenology.get("fruiting_delay_after_rain_days") if isinstance(phenology.get("fruiting_delay_after_rain_days"), dict) else {}
    host_labels = catalog_label_map(catalogs, "host_taxa")
    host_names = []
    for item in ecology.get("host_affinities", []) if isinstance(ecology.get("host_affinities"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            host_id = str(item.get("id"))
            host_names.append(host_labels.get(host_id, f"{host_id} (missing)"))
    season_names = phenology.get("season_pattern_ids") if isinstance(phenology.get("season_pattern_ids"), list) else []
    aspect_names = topography.get("preferred_aspect_ids") if isinstance(topography.get("preferred_aspect_ids"), list) else []
    return f"""
    <section class="profile-overview-grid">
      <article class="profile-overview-card identity">
        {card_title(1, ui_label("ui.identity"), "identity")}
        {value_row(ui_label("species_id"), profile.get("species_id", ""))}
        {value_row(ui_label("ui.scientific_name"), profile.get("scientific_name", ""))}
        {value_row(ui_label("ui.common_names"), compact_list(profile.get("common_names", []), 4))}
        {value_row(ui_label("ui.taxonomy"), value_label(profile.get("taxonomy_status", "")))}
        {value_row(ui_label("ui.edibility"), value_label(profile.get("edibility", "")))}
      </article>
      <article class="profile-overview-card">
        {card_title(2, ui_label("ui.ecology_topography"), "ecology")}
        {value_row(ui_label("ui.trophic_mode"), catalog_display(catalogs, "trophic_modes", ecology.get("trophic_mode_id", "-")))}
        {value_row(ui_label("ui.primary_hosts"), ", ".join(host_names[:4]) if host_names else "-")}
        {value_row(ui_label("altitude.meters"), f'{topography.get("altitude_min_m", "-")} - {topography.get("altitude_max_m", "-")} m')}
        {value_row(ui_label("ui.optimal_altitude"), f'{topography.get("altitude_optimal_min_m", "-")} - {topography.get("altitude_optimal_max_m", "-")} m')}
        {value_row(ui_label("ui.preferred_aspects"), catalog_compact_list(catalogs, "aspects", aspect_names, 6))}
      </article>
      <article class="profile-overview-card">
        {card_title(3, ui_label("ui.phenology"), "phenology")}
        <span class="label">{html.escape(ui_label("ui.main_months"))}</span>
        {month_chips(phenology.get("main_months", []))}
        <span class="label">{html.escape(ui_label("ui.secondary_months"))}</span>
        {month_chips(phenology.get("secondary_months", []), "secondary-month")}
        {value_row(ui_label("ui.season_patterns"), catalog_compact_list(catalogs, "season_patterns", season_names, 3))}
        {value_row(ui_label("ui.fruiting_delay"), f'{delay.get("min", "-")} / {delay.get("optimal_min", "-")}-{delay.get("optimal_max", "-")} / {delay.get("max", "-")} days')}
      </article>
      <article class="profile-overview-card wide">
        {card_title(4, ui_label("ui.weather_model_summary"), "weather")}
        {render_weather_summary(weather_model)}
      </article>
      <article class="profile-overview-card">
        {card_title(5, ui_label("ui.scoring_weights"), "scoring")}
        {''.join(score_bar(key, value) for key, value in scoring.items())}
      </article>
      <article class="profile-overview-card">
        {card_title(6, ui_label("ui.confidence_calibration"), "calibration")}
        {value_row(ui_label("ui.overall_confidence"), value_label(confidence.get("overall_confidence")))}
        {value_row(ui_label("ui.habitat_confidence"), value_label(confidence.get("habitat_confidence")))}
        {value_row(ui_label("ui.phenology_confidence"), value_label(confidence.get("phenology_confidence")))}
        {value_row(ui_label("ui.weather_threshold_confidence"), value_label(confidence.get("weather_threshold_confidence")))}
        {value_row(ui_label("ui.local_calibration_status"), value_label(confidence.get("local_calibration_status")))}
        {value_row(ui_label("ui.priority"), value_label(confidence.get("calibration_priority")))}
      </article>
      <article class="profile-overview-card full">
        {card_title(7, ui_label("ui.metadata"), "metadata")}
        <div class="profile-metadata-strip">
          {value_row(ui_label("metadata.created_at"), metadata.get("created_at"))}
          {value_row(ui_label("metadata.updated_at"), metadata.get("updated_at"))}
          {value_row(ui_label("metadata.created_by"), metadata.get("created_by"))}
          {value_row(ui_label("ui.review_status"), value_label(metadata.get("review_status")))}
          {value_row(ui_label("ui.source_quality"), value_label(metadata.get("source_quality")))}
          {value_row(ui_label("ui.requires_human_validation"), ui_label("ui.yes") if metadata.get("requires_human_validation") is True else ui_label("ui.no"))}
        </div>
      </article>
    </section>
    """


def render_profile_editor(profile: dict[str, object] | None, catalogs: dict[str, object]) -> str:
    """Render the selected profile editor using the existing POST contract."""
    if not profile:
        return f'<section class="card profile-editor"><h2>{html.escape(ui_label("ui.species_detail"))}</h2><p>{html.escape(ui_label("ui.no_species_selected"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    ecology = nested_dict(profile, "ecology")
    phenology = nested_dict(profile, "phenology")
    topography = nested_dict(profile, "topography")
    weather_model = nested_dict(profile, "weather_model")
    rainfall = weather_model.get("rainfall") if isinstance(weather_model.get("rainfall"), dict) else {}
    temperature = weather_model.get("temperature") if isinstance(weather_model.get("temperature"), dict) else {}
    humidity = weather_model.get("humidity") if isinstance(weather_model.get("humidity"), dict) else {}
    wind = weather_model.get("wind") if isinstance(weather_model.get("wind"), dict) else {}
    scoring = nested_dict(profile, "scoring_weights")
    scoring_total = sum(float(value) for value in scoring.values() if isinstance(value, int | float))
    confidence = nested_dict(profile, "prediction_confidence")
    metadata = nested_dict(profile, "metadata")
    delay = phenology.get("fruiting_delay_after_rain_days") if isinstance(phenology.get("fruiting_delay_after_rain_days"), dict) else {}
    json_value = json.dumps(profile, indent=2, ensure_ascii=False)
    affinity_blocks = render_ecology_affinity_tabs(ecology, catalogs)
    status_chips = "".join(
        [
            value_chip(profile.get("taxonomy_status", "-"), ui_label("ui.taxonomy")),
            value_chip(profile.get("edibility", "-"), ui_label("ui.edibility")),
            value_chip(confidence.get("overall_confidence", "-"), ui_label("ui.confidence")),
            value_chip(confidence.get("local_calibration_status", "-"), ui_label("ui.calibration")),
            value_chip(metadata.get("review_status", "-"), ui_label("ui.review_status")),
        ]
    )
    general_dashboard = render_general_dashboard(profile, catalogs, ecology, phenology, topography, weather_model, scoring, confidence, metadata)
    duplicate_species_id = f"{species_id}_copy"
    duplicate_scientific_name = f"{profile.get('scientific_name', species_id)} copy"
    return f"""
    <section class="card profile-editor profile-editor-polished">
      <div class="profile-editor-head profile-hero">
        <div class="profile-title-block">
          <span class="profile-hero-icon">{icon("mushroom")}</span>
          <div>
            <h2>{html.escape(str(profile.get("scientific_name", species_id)))}</h2>
            <p class="meta">{html.escape(profile_common_name(profile))} · {html.escape(species_id)}</p>
          </div>
        </div>
        <div class="profile-hero-chips">{status_chips}</div>
      </div>
      <form method="post" action="?id={html.escape(species_id, quote=True)}" onsubmit="return confirm('Save this species profile and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_form">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <input type="hidden" name="profile_return_tab" value="profile-tab-general">
        <div class="profile-tabs">
          <input type="radio" name="profile_tab" id="profile-tab-general" checked>
          <input type="radio" name="profile_tab" id="profile-tab-ecology">
          <input type="radio" name="profile_tab" id="profile-tab-phenology">
          <input type="radio" name="profile_tab" id="profile-tab-weather">
          <input type="radio" name="profile_tab" id="profile-tab-scoring">
          <input type="radio" name="profile_tab" id="profile-tab-calibration">
          <input type="radio" name="profile_tab" id="profile-tab-metadata">
          <input type="radio" name="profile_tab" id="profile-tab-json">
          <div class="profile-tab-labels">
            <label for="profile-tab-general">{icon("identity")}{html.escape(ui_label("ui.general"))}</label>
            <label for="profile-tab-ecology">{icon("ecology")}{html.escape(ui_label("ui.ecology"))}</label>
            <label for="profile-tab-phenology">{icon("phenology")}{html.escape(ui_label("ui.phenology_topography"))}</label>
            <label for="profile-tab-weather">{icon("weather")}{html.escape(ui_label("ui.weather"))}</label>
            <label for="profile-tab-scoring">{icon("scoring")}{html.escape(ui_label("ui.scoring"))}</label>
            <label for="profile-tab-calibration">{icon("calibration")}{html.escape(ui_label("ui.confidence"))}</label>
            <label for="profile-tab-metadata">{icon("metadata")}{html.escape(ui_label("ui.metadata"))}</label>
            <label for="profile-tab-json">{icon("metadata")}{html.escape(ui_label("ui.json"))}</label>
          </div>
          <div class="profile-tab-content">
            <section class="profile-section profile-tab-panel general">{general_dashboard}</section>
            <section class="profile-section profile-tab-panel ecology">
              <div class="profile-section-head">
                <h2>{html.escape(ui_label("ui.ecology"))}</h2>
                {form_catalog_select("trophic_mode_id", ui_label("ui.trophic_mode"), ecology.get("trophic_mode_id", ""), catalog_options_for_group(catalogs, "trophic_modes"))}
              </div>
              {affinity_blocks}
            </section>
            <section class="profile-section profile-tab-panel phenology">
              <h3>{html.escape(ui_label("ui.phenology"))}</h3>
              <div class="profile-phenology-layout">
                <div class="profile-phenology-left">
                  <div class="profile-month-grid">
                    {form_month_toggles("main_months", ui_label("ui.main_months"), phenology.get("main_months", []))}
                    {form_month_toggles("secondary_months", ui_label("ui.secondary_months"), phenology.get("secondary_months", []), "secondary-month")}
                  </div>
                  <div class="profile-delay-grid">
                    {form_field("delay_min", ui_label("ui.delay_min"), delay.get("min", ""), field_type="number")}
                    {form_field("delay_optimal_min", ui_label("ui.delay_optimal_min"), delay.get("optimal_min", ""), field_type="number")}
                    {form_field("delay_max", ui_label("ui.delay_max"), delay.get("max", ""), field_type="number")}
                    {form_field("delay_optimal_max", ui_label("ui.delay_optimal_max"), delay.get("optimal_max", ""), field_type="number")}
                  </div>
                </div>
                <div class="profile-season-pattern-field">
                  {form_catalog_toggles("season_pattern_ids", ui_label("ui.season_patterns"), phenology.get("season_pattern_ids", []), catalogs, "season_patterns")}
                </div>
              </div>
              <h3>{html.escape(ui_label("ui.topography"))}</h3>
              <div class="profile-topography-layout">
                <div class="profile-altitude-grid">
                  {form_field("altitude_min_m", parameter_label("altitude_min_m"), topography.get("altitude_min_m", ""), field_type="number")}
                  {form_field("altitude_optimal_min_m", parameter_label("altitude_optimal_min_m"), topography.get("altitude_optimal_min_m", ""), field_type="number")}
                  {form_field("altitude_max_m", parameter_label("altitude_max_m"), topography.get("altitude_max_m", ""), field_type="number")}
                  {form_field("altitude_optimal_max_m", parameter_label("altitude_optimal_max_m"), topography.get("altitude_optimal_max_m", ""), field_type="number")}
                </div>
                <div class="profile-aspect-field">
                  {form_catalog_toggles("preferred_aspect_ids", ui_label("ui.preferred_aspects"), topography.get("preferred_aspect_ids", []), catalogs, "aspects")}
                </div>
              </div>
              {form_textarea("aspect_notes", ui_label("site_context.aspect_notes"), topography.get("aspect_notes", ""), rows=2)}
            </section>
            <section class="profile-section profile-tab-panel weather">
              <h2>{html.escape(ui_label("ui.weather_model"))}</h2>
              <div class="profile-grid four">
                {''.join(form_field(f"rainfall_{key}", parameter_label(key), value, field_type="number") for key, value in rainfall.items())}
                {''.join(form_field(f"temperature_{key}", parameter_label(key), value, field_type="number") for key, value in temperature.items())}
                {''.join(form_field(f"humidity_{key}", parameter_label(key), value, field_type="number") for key, value in humidity.items())}
                {''.join(form_field(f"wind_{key}", parameter_label(key), value, field_type="checkbox" if isinstance(value, bool) else "number") for key, value in wind.items())}
              </div>
            </section>
            <section class="profile-section profile-tab-panel scoring">
              <h2>{html.escape(ui_label("ui.scoring_weights"))}</h2>
              <div class="profile-scoring-total">
                <span>{html.escape(ui_label("ui.current_total"))}</span><strong>{scoring_total:.2f}</strong><em>{html.escape(ui_label("ui.target"))}: 1.00</em>
              </div>
              <div class="profile-score-editor">
                {''.join(score_bar(key, value) for key, value in scoring.items())}
              </div>
              <div class="profile-grid four">
                {''.join(form_field(f"score_{key}", parameter_label(key), value, field_type="number", step="0.01", minimum="0", maximum="1") for key, value in scoring.items())}
              </div>
            </section>
            <section class="profile-section profile-tab-panel calibration">
              <h2>{html.escape(ui_label("ui.confidence_calibration"))}</h2>
              <div class="profile-calibration-summary">
                <div><span class="label">{html.escape(ui_label("ui.current_status"))}</span><span class="value">{html.escape(value_label(confidence.get("local_calibration_status")))}</span></div>
                <div><span class="label">{html.escape(ui_label("ui.priority"))}</span><span class="value">{html.escape(value_label(confidence.get("calibration_priority")))}</span></div>
                <div><span class="label">{html.escape(ui_label("ui.overall_confidence"))}</span><span class="value">{html.escape(value_label(confidence.get("overall_confidence")))}</span></div>
                <div><span class="label">{html.escape(ui_label("ui.human_validation"))}</span><span class="value">{html.escape(ui_label("ui.yes") if metadata.get("requires_human_validation") is True else ui_label("ui.no"))}</span></div>
              </div>
              <div class="profile-grid four">
                {form_select("local_calibration_status", ui_label("ui.local_calibration_status"), confidence.get("local_calibration_status", ""), PROFILE_SELECT_VALUES["calibration_status"])}
                {form_select("calibration_priority", ui_label("ui.calibration_priority"), confidence.get("calibration_priority", ""), PROFILE_SELECT_VALUES["calibration_priority"])}
                {form_select("overall_confidence", ui_label("ui.overall_confidence"), confidence.get("overall_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("habitat_confidence", ui_label("ui.habitat_confidence"), confidence.get("habitat_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("topography_confidence", ui_label("ui.topography_confidence"), confidence.get("topography_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("phenology_confidence", ui_label("ui.phenology_confidence"), confidence.get("phenology_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("weather_threshold_confidence", ui_label("ui.weather_threshold_confidence"), confidence.get("weather_threshold_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("taxonomy_confidence", ui_label("ui.taxonomy_confidence"), confidence.get("taxonomy_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_field("minimum_observations_for_calibration", ui_label("ui.minimum_observations_for_calibration"), confidence.get("minimum_observations_for_calibration", ""), field_type="number")}
                {form_field("minimum_positive_observations", ui_label("ui.minimum_positive_observations"), confidence.get("minimum_positive_observations", ""), field_type="number")}
                {form_field("minimum_negative_observations", ui_label("ui.minimum_negative_observations"), confidence.get("minimum_negative_observations", ""), field_type="number")}
              </div>
              {form_textarea("confidence_notes", ui_label("ui.calibration_notes"), confidence.get("notes", ""), rows=3)}
            </section>
            <section class="profile-section profile-tab-panel metadata">
              <h2>{html.escape(ui_label("ui.identity_metadata"))}</h2>
              <div class="profile-subsection">
                <h3>{html.escape(ui_label("ui.identity_fields"))}</h3>
                <div class="profile-grid two">
                  {form_field("scientific_name", ui_label("ui.scientific_name"), profile.get("scientific_name", ""))}
                  {form_select("taxonomy_status", ui_label("ui.taxonomy_status"), profile.get("taxonomy_status", ""), PROFILE_SELECT_VALUES["taxonomy_status"])}
                  {form_textarea("common_names", ui_label("ui.common_names"), profile.get("common_names", []), rows=3)}
                  {form_select("edibility", ui_label("ui.edibility"), profile.get("edibility", ""), PROFILE_SELECT_VALUES["edibility"])}
                </div>
              </div>
              <div class="profile-subsection">
                <h3>{html.escape(ui_label("ui.maintenance_metadata"))}</h3>
              <div class="profile-grid three">
                {form_field("profile_version", ui_label("ui.profile_version"), metadata.get("profile_version", ""))}
                {form_field("created_at", ui_label("metadata.created_at"), metadata.get("created_at", ""))}
                {form_field("updated_at", ui_label("metadata.updated_at"), metadata.get("updated_at", ""))}
                {form_field("created_by", ui_label("metadata.created_by"), metadata.get("created_by", ""))}
                {form_select("review_status", ui_label("ui.review_status"), metadata.get("review_status", ""), PROFILE_SELECT_VALUES["review_status"])}
                {form_field("reviewed_by", ui_label("metadata.reviewed_by"), metadata.get("reviewed_by", ""))}
                {form_select("source_quality", ui_label("ui.source_quality"), metadata.get("source_quality", ""), PROFILE_SELECT_VALUES["source_quality"])}
                {form_field("requires_human_validation", ui_label("ui.requires_human_validation"), metadata.get("requires_human_validation"), field_type="checkbox")}
              </div>
              </div>
            </section>
            <section class="profile-section profile-tab-panel json">
              <h2>{html.escape(ui_label("ui.advanced_json"))}</h2>
              <p class="meta">{html.escape(ui_label("ui.raw_json_help"))}</p>
            </section>
          </div>
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.save_species_profile"))}</button>
          <a class="button-link secondary-link" href="#duplicate-species-modal">{html.escape(ui_label("ui.duplicate_species"))}</a>
          <a class="button-link danger-link" href="#archive-species-modal">{html.escape(ui_label("ui.archive_species"))}</a>
          <button class="secondary planned-action" type="button" disabled title="{html.escape(ui_label('ui.planned_profile_validation_title'), quote=True)}">{html.escape(ui_label("ui.validate_profile_planned"))}</button>
        </div>
      </form>
      <div id="duplicate-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="?id={html.escape(species_id, quote=True)}" aria-label="Cancel duplicate species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>{html.escape(ui_label("ui.duplicate_species"))}</h2>
              <p>{html.escape(ui_label("ui.duplicate_species_help"))}</p>
            </div>
            <a class="button-link" href="?id={html.escape(species_id, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
          </header>
          <form method="post" action="" onsubmit="return confirm('Duplicate this species profile as a new draft profile?')">
            <input type="hidden" name="profile_action" value="duplicate_profile">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <div class="profile-grid">
              {form_field("duplicate_species_id", ui_label("ui.new_species_id"), duplicate_species_id)}
              {form_field("duplicate_scientific_name", ui_label("ui.scientific_name"), duplicate_scientific_name)}
              {form_field("duplicate_common_name", ui_label("ui.common_name"), "")}
            </div>
            <div class="modal-actions">
              <a class="button-link" href="?id={html.escape(species_id, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
              <button class="secondary">{html.escape(ui_label("ui.duplicate_species"))}</button>
            </div>
          </form>
        </section>
      </div>
      <div id="archive-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="?id={html.escape(species_id, quote=True)}" aria-label="Cancel archive species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>{html.escape(ui_label("ui.archive_species"))}</h2>
              <p>{html.escape(ui_label("ui.archive_species_help"))}</p>
            </div>
            <a class="button-link" href="?id={html.escape(species_id, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
          </header>
          <form method="post" action="" onsubmit="return confirm('Archive this species profile? It will be removed from active profiles but can be restored.')">
            <input type="hidden" name="profile_action" value="archive_profile">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <div class="admin-field">
              <label for="profile-archive-species-id">{html.escape(ui_label("ui.species_id_to_archive"))}</label>
              <input id="profile-archive-species-id" value="{html.escape(species_id, quote=True)}" readonly>
            </div>
            <div class="modal-actions">
              <a class="button-link" href="?id={html.escape(species_id, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
              <button class="danger-button">{html.escape(ui_label("ui.archive_species"))}</button>
            </div>
          </form>
        </section>
      </div>
      <details class="profile-raw-json">
        <summary><strong>{html.escape(ui_label("ui.advanced_raw_json"))}</strong></summary>
        <form class="profile-json-editor" method="post" action="?id={html.escape(species_id, quote=True)}" onsubmit="return confirm('Save raw JSON for this species profile and validate the full dataset?')">
          <input type="hidden" name="profile_action" value="save_profile_json">
          <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
          <input type="hidden" name="profile_return_tab" value="profile-tab-json">
          <label class="label" for="profile-json">{html.escape(ui_label("ui.species_profile_json"))}</label>
          <textarea id="profile-json" name="profile_json" spellcheck="false">{html.escape(json_value)}</textarea>
          <button class="primary">{html.escape(ui_label("ui.save_raw_json"))}</button>
        </form>
      </details>
    </section>
    """


def render_parameters_section(profile: dict[str, object] | None, catalogs: dict[str, object], search: str = "") -> str:
    """Render the top-level Parameters screen using real profile model fields."""
    if not profile:
        return f'<section class="card profile-section-screen"><h2>{html.escape(ui_label("ui.parameters"))}</h2><p>{html.escape(ui_label("ui.no_species_selected"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    ecology = nested_dict(profile, "ecology")
    phenology = nested_dict(profile, "phenology")
    topography = nested_dict(profile, "topography")
    weather_model = nested_dict(profile, "weather_model")
    rainfall = weather_model.get("rainfall") if isinstance(weather_model.get("rainfall"), dict) else {}
    temperature = weather_model.get("temperature") if isinstance(weather_model.get("temperature"), dict) else {}
    humidity = weather_model.get("humidity") if isinstance(weather_model.get("humidity"), dict) else {}
    wind = weather_model.get("wind") if isinstance(weather_model.get("wind"), dict) else {}
    scoring = nested_dict(profile, "scoring_weights")
    metadata = nested_dict(profile, "metadata")
    delay = phenology.get("fruiting_delay_after_rain_days") if isinstance(phenology.get("fruiting_delay_after_rain_days"), dict) else {}
    host_labels = catalog_label_map(catalogs, "host_taxa")
    forest_labels = catalog_label_map(catalogs, "forest_types")
    soil_labels = catalog_label_map(catalogs, "soil_types")
    lithology_labels = catalog_label_map(catalogs, "lithology_types")
    habitat_labels = catalog_label_map(catalogs, "habitat_features")
    scoring_total = sum(float(value) for value in scoring.values() if isinstance(value, int | float))
    species_href = profile_query_url(species_id, search, section="species")
    return f"""
    <section class="card profile-section-screen parameters-screen">
      {render_selected_species_header(profile, ui_label("ui.parameters"))}
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='parameters'), quote=True)}" onsubmit="return confirm('Save parameter changes for this species and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_parameters">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <div class="profile-parameters-grid">
          <div class="parameter-left-stack">
            <article class="profile-section-card">
              <h2>{icon("weather")} {html.escape(ui_label("ui.climate_model"))}</h2>
              <p class="parameter-card-note">{html.escape(ui_label("ui.weather_thresholds_note"))}</p>
              <div class="parameter-climate-grid">
                <div class="profile-subsection">
                  <h3>{icon("rain")} {html.escape(ui_label("rainfall"))}</h3>
                  {''.join(parameter_field(f"rainfall_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in rainfall.items())}
                </div>
                <div class="profile-subsection">
                  <h3>{icon("temperature")} {html.escape(ui_label("temperature"))}</h3>
                  {''.join(parameter_field(f"temperature_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in temperature.items())}
                </div>
                <div class="profile-subsection">
                  <h3>{icon("humidity")} {html.escape(ui_label("humidity"))}</h3>
                  {''.join(parameter_field(f"humidity_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in humidity.items())}
                </div>
                <div class="profile-subsection">
                  <h3>{icon("wind")} {html.escape(ui_label("ui.wind"))}</h3>
                  {''.join(parameter_field(f"wind_{key}", parameter_label(key), value, unit=parameter_unit(key), field_type="checkbox" if isinstance(value, bool) else "number") for key, value in wind.items())}
                </div>
              </div>
            </article>
            <article class="profile-section-card">
              <h2>{icon("scoring")} {html.escape(ui_label("ui.scoring_weights"))}</h2>
              <div class="profile-scoring-total"><span>{html.escape(ui_label("ui.current_total"))}</span><strong>{scoring_total:.2f}</strong><em>{html.escape(ui_label("ui.target"))}: 1.00</em></div>
              <div class="parameter-score-grid">
                {''.join(parameter_field(f"score_{key}", parameter_label(key), value, step="0.01", minimum="0", maximum="1") for key, value in scoring.items())}
              </div>
            </article>
          </div>
          <article class="profile-section-card">
            <h2>{icon("ecology")} {html.escape(ui_label("ui.habitat_model"))}</h2>
            <p class="parameter-card-note">{html.escape(ui_label("ui.habitat_model_note"))}</p>
            <div class="profile-section-card-grid two parameter-habitat-grid">
              <div class="profile-subsection">
                <h3>{icon("host")} {html.escape(ui_label("ui.ecology_and_habitat"))}</h3>
                {form_catalog_select("trophic_mode_id", ui_label("ui.trophic_mode"), ecology.get("trophic_mode_id", ""), catalog_options_for_group(catalogs, "trophic_modes"))}
                {value_html_row(ui_label("ui.primary_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, "primary"))}
                {value_html_row(ui_label("ui.secondary_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, "secondary"))}
                {value_html_row(ui_label("ui.other_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, exclude_relationships={"primary", "secondary"}))}
                {value_html_row(ui_label("ui.forest_types"), affinity_chip_list(ecology, "forest_type_affinities", forest_labels))}
                {value_html_row(ui_label("ui.habitat_features"), affinity_chip_list(ecology, "habitat_feature_affinities", habitat_labels))}
                <p class="meta">{html.escape(ui_label("ui.edit_affinities_note"))}</p>
              </div>
              <div class="profile-subsection">
                <h3>{icon("soil")} {html.escape(ui_label("ui.soils_and_lithology"))}</h3>
                {value_html_row(ui_label("ui.soils"), affinity_chip_list(ecology, "soil_affinities", soil_labels))}
                {value_html_row(ui_label("ui.lithology"), affinity_chip_list(ecology, "lithology_affinities", lithology_labels))}
                <p class="meta">{html.escape(ui_label("ui.affinity_ids_note"))}</p>
              </div>
              <div class="profile-subsection">
                <h3>{icon("topography")} {html.escape(ui_label("ui.topography"))}</h3>
                <div class="parameter-duo-grid">
                  {parameter_field("altitude_min_m", parameter_label("altitude_min_m"), topography.get("altitude_min_m", ""), unit="m")}
                  {parameter_field("altitude_optimal_min_m", parameter_label("altitude_optimal_min_m"), topography.get("altitude_optimal_min_m", ""), unit="m")}
                  {parameter_field("altitude_optimal_max_m", parameter_label("altitude_optimal_max_m"), topography.get("altitude_optimal_max_m", ""), unit="m")}
                  {parameter_field("altitude_max_m", parameter_label("altitude_max_m"), topography.get("altitude_max_m", ""), unit="m")}
                </div>
                {form_catalog_toggles("preferred_aspect_ids", ui_label("ui.preferred_aspects"), topography.get("preferred_aspect_ids", []), catalogs, "aspects")}
                {parameter_textarea("aspect_notes", ui_label("site_context.aspect_notes"), topography.get("aspect_notes", ""), rows=1)}
              </div>
              <div class="profile-subsection">
                <h3>{icon("phenology")} {html.escape(ui_label("ui.phenology"))}</h3>
                {parameter_textarea("main_months", ui_label("ui.main_months"), phenology.get("main_months", []), rows=1)}
                {parameter_textarea("secondary_months", ui_label("ui.secondary_months"), phenology.get("secondary_months", []), rows=1)}
                {form_catalog_toggles("season_pattern_ids", ui_label("ui.season_patterns"), phenology.get("season_pattern_ids", []), catalogs, "season_patterns")}
                <div class="parameter-duo-grid">
                  {parameter_field("delay_min", ui_label("ui.delay_min"), delay.get("min", ""), unit="d")}
                  {parameter_field("delay_optimal_min", ui_label("ui.delay_optimal_min"), delay.get("optimal_min", ""), unit="d")}
                  {parameter_field("delay_optimal_max", ui_label("ui.delay_optimal_max"), delay.get("optimal_max", ""), unit="d")}
                  {parameter_field("delay_max", ui_label("ui.delay_max"), delay.get("max", ""), unit="d")}
                </div>
              </div>
            </div>
          </article>
        </div>
        <div class="profile-action-bar">
          <a class="button-link secondary-link" href="{html.escape(species_href, quote=True)}">{html.escape(ui_label("ui.back_to_species_editor"))}</a>
          <button class="secondary" type="reset">{html.escape(ui_label("ui.reset_visible_changes"))}</button>
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.save_parameter_changes"))}</button>
        </div>
      </form>
      <p class="meta">Review status: {html.escape(str(metadata.get("review_status", "-")))}. Catalog-backed affinity relationships are intentionally edited from the Species tab to avoid lossy partial updates.</p>
    </section>
    """


def render_calibration_section(profile: dict[str, object] | None, search: str = "") -> str:
    """Render the top-level Calibration screen using real confidence fields."""
    if not profile:
        return f'<section class="card profile-section-screen"><h2>{html.escape(ui_label("ui.calibration"))}</h2><p>{html.escape(ui_label("ui.no_species_selected"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    confidence = nested_dict(profile, "prediction_confidence")
    metadata = nested_dict(profile, "metadata")
    minimum_total = confidence.get("minimum_observations_for_calibration", "-")
    minimum_positive = confidence.get("minimum_positive_observations", "-")
    minimum_negative = confidence.get("minimum_negative_observations", "-")
    observations_href = profile_query_url(species_id, search, section="observations")
    parameters_href = profile_query_url(species_id, search, section="parameters")
    return f"""
    <section class="card profile-section-screen calibration-screen">
      {render_selected_species_header(profile, ui_label("ui.calibration"))}
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='calibration'), quote=True)}" onsubmit="return confirm('Save calibration settings for this species and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_calibration">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <div class="profile-calibration-cards">
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.local_calibration_status"))}</span><span class="value warn">{html.escape(value_label(confidence.get("local_calibration_status")))}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.priority"))}</span><span class="value ok">{html.escape(value_label(confidence.get("calibration_priority")))}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.overall_confidence"))}</span><span class="value">{html.escape(value_label(confidence.get("overall_confidence")))}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.minimum_observations"))}</span><span class="value">{html.escape(str(minimum_total))}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.minimum_positive_observations"))}</span><span class="value">{html.escape(str(minimum_positive))}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.minimum_negative_observations"))}</span><span class="value">{html.escape(str(minimum_negative))}</span></div>
        </div>
        <div class="profile-calibration-grid">
          <article class="profile-section-card">
            <h2>1. {html.escape(ui_label("ui.confidence_profile"))}</h2>
            <div class="profile-grid two">
              {form_select("overall_confidence", ui_label("ui.overall_confidence"), confidence.get("overall_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("habitat_confidence", ui_label("ui.habitat_confidence"), confidence.get("habitat_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("topography_confidence", ui_label("ui.topography_confidence"), confidence.get("topography_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("phenology_confidence", ui_label("ui.phenology_confidence"), confidence.get("phenology_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("weather_threshold_confidence", ui_label("ui.weather_threshold_confidence"), confidence.get("weather_threshold_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("taxonomy_confidence", ui_label("ui.taxonomy_confidence"), confidence.get("taxonomy_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
            </div>
          </article>
          <article class="profile-section-card">
            <h2>2. {html.escape(ui_label("ui.calibration_requirements"))}</h2>
            <div class="profile-grid two">
              {form_select("local_calibration_status", ui_label("ui.local_calibration_status"), confidence.get("local_calibration_status", ""), PROFILE_SELECT_VALUES["calibration_status"])}
              {form_select("calibration_priority", ui_label("ui.calibration_priority"), confidence.get("calibration_priority", ""), PROFILE_SELECT_VALUES["calibration_priority"])}
              {form_field("minimum_observations_for_calibration", ui_label("ui.minimum_observations"), confidence.get("minimum_observations_for_calibration", ""), field_type="number", minimum="0")}
              {form_field("minimum_positive_observations", ui_label("ui.minimum_positive_observations"), confidence.get("minimum_positive_observations", ""), field_type="number", minimum="0")}
              {form_field("minimum_negative_observations", ui_label("ui.minimum_negative_observations"), confidence.get("minimum_negative_observations", ""), field_type="number", minimum="0")}
              {form_field("requires_human_validation", ui_label("ui.requires_human_validation"), metadata.get("requires_human_validation"), field_type="checkbox")}
              {form_select("review_status", ui_label("ui.review_status"), metadata.get("review_status", ""), PROFILE_SELECT_VALUES["review_status"])}
            </div>
          </article>
          <article class="profile-section-card">
            <h2>3. {html.escape(ui_label("ui.observation_coverage"))}</h2>
            <div class="profile-coverage-grid">
              {value_row(ui_label("ui.total_observations_used"), f'0 / {minimum_total}')}
              {value_row(ui_label("ui.positive_observations"), f'0 / {minimum_positive}')}
              {value_row(ui_label("ui.negative_observations"), f'0 / {minimum_negative}')}
              {value_row(ui_label("ui.key_data_gaps"), ui_label("ui.pending_observation_model"))}
            </div>
            <p class="meta">{html.escape(ui_label("ui.observation_coverage_help"))}</p>
          </article>
          <article class="profile-section-card">
            <h2>4. {html.escape(ui_label("ui.calibration_notes"))}</h2>
            {form_textarea("confidence_notes", ui_label("ui.calibration_notes"), confidence.get("notes", ""), rows=8)}
          </article>
          <article class="profile-section-card full">
            <h2>5. {html.escape(ui_label("ui.actions_recommendations"))}</h2>
            <div class="profile-recommendation-list">
              <a class="button-link" href="{html.escape(observations_href, quote=True)}">{html.escape(ui_label("ui.add_local_observations"))}</a>
              <a class="button-link" href="{html.escape(parameters_href, quote=True)}">{html.escape(ui_label("ui.review_weather_thresholds"))}</a>
              <button class="secondary planned-action" type="button" disabled>{html.escape(ui_label("ui.start_human_validation_planned"))}</button>
              <button class="secondary planned-action" type="button" disabled>{html.escape(ui_label("ui.recalculate_scoring_planned"))}</button>
            </div>
          </article>
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.save_calibration"))}</button>
        </div>
      </form>
    </section>
    """


def observations_from_payload(payload: dict[str, object] | None) -> list[dict[str, object]]:
    """Return observation rows from the persisted observation store."""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def profile_name_map(profiles: list[dict[str, object]]) -> dict[str, str]:
    """Return compact species labels indexed by species ID."""
    labels = {}
    for profile in profiles:
        species_id = str(profile.get("species_id", "") or "")
        if not species_id:
            continue
        labels[species_id] = str(profile.get("scientific_name", species_id) or species_id)
    return labels


def observation_metrics(rows: list[dict[str, object]]) -> tuple[int, int, int, int]:
    """Calculate high-level observation counters for the dashboard strip."""
    total = len(rows)
    positive = sum(1 for row in rows if str(row.get("flush_abundance", "")) not in {"", "absent"})
    negative = sum(1 for row in rows if str(row.get("flush_abundance", "")) == "absent")
    pending = sum(1 for row in rows if str(row.get("validation_status", "")) in {"", "draft", "doubtful"})
    return total, positive, negative, pending


def observation_filter_value(filters: dict[str, str] | None, key: str) -> str:
    """Return a normalized observation filter value."""
    if not isinstance(filters, dict):
        return ""
    return str(filters.get(key, "") or "").strip()


def filtered_observation_rows(
    rows: list[dict[str, object]],
    selected_species_id: str,
    filters: dict[str, str] | None,
) -> list[dict[str, object]]:
    """Apply the visible observation filters used by the maintenance screen."""
    date_from = observation_filter_value(filters, "date_from")
    date_to = observation_filter_value(filters, "date_to")
    result = observation_filter_value(filters, "result")
    validation = observation_filter_value(filters, "validation")
    text = observation_filter_value(filters, "obs_q").lower()
    visible_rows = rows
    if selected_species_id:
        visible_rows = [row for row in visible_rows if str(row.get("species_id", "")) == selected_species_id]
    if date_from:
        visible_rows = [row for row in visible_rows if str(row.get("observed_at", "")) >= date_from]
    if date_to:
        visible_rows = [row for row in visible_rows if str(row.get("observed_at", "")) <= date_to]
    if result:
        visible_rows = [row for row in visible_rows if str(row.get("flush_abundance", "")) == result]
    if validation:
        visible_rows = [row for row in visible_rows if str(row.get("validation_status", "")) == validation]
    if text:
        def row_text(row: dict[str, object]) -> str:
            location = row.get("location") if isinstance(row.get("location"), dict) else {}
            source = row.get("source") if isinstance(row.get("source"), dict) else {}
            observer = row.get("observer") if isinstance(row.get("observer"), dict) else {}
            parts = [
                row.get("observation_id", ""),
                row.get("species_id", ""),
                row.get("flush_abundance", ""),
                row.get("validation_status", ""),
                observer.get("name", "") if isinstance(observer, dict) else "",
                source.get("label", "") if isinstance(source, dict) else "",
                source.get("type", "") if isinstance(source, dict) else "",
                location.get("input", "") if isinstance(location, dict) else "",
            ]
            return " ".join(str(part) for part in parts).lower()

        visible_rows = [row for row in visible_rows if text in row_text(row)]
    return visible_rows


def observation_catalog_label(catalogs: dict[str, object], group: str, item_id: object) -> str:
    """Return a catalog-backed label for an observation value."""
    value = str(item_id or "")
    if not value:
        return "-"
    return catalog_label_map(catalogs, group).get(value, value)


def observation_weight(catalogs: dict[str, object], row: dict[str, object]) -> float:
    """Estimate the current calibration weight from quality and catalog multipliers."""
    quality = row.get("source_quality")
    quality_value = float(quality) if isinstance(quality, (int, float)) and not isinstance(quality, bool) else 0.0
    multiplier = 1.0
    statuses = catalogs.get("observation_validation_statuses")
    if isinstance(statuses, list):
        for item in statuses:
            if isinstance(item, dict) and str(item.get("id", "")) == str(row.get("validation_status", "")):
                raw_multiplier = item.get("calibration_multiplier")
                if isinstance(raw_multiplier, (int, float)) and not isinstance(raw_multiplier, bool):
                    multiplier = float(raw_multiplier)
                break
    if str(row.get("calibration_use", "")) == "exclude":
        multiplier = 0.0
    return round(quality_value * multiplier, 3)


def observation_badge(text: str, tone: str = "") -> str:
    """Render a compact status badge used by observation rows."""
    return f'<span class="observation-badge {html.escape(tone, quote=True)}">{html.escape(text)}</span>'


def render_observation_table(
    rows: list[dict[str, object]],
    catalogs: dict[str, object],
    species_labels: dict[str, str],
) -> str:
    """Render the observation list with enough columns for field calibration review."""
    visible_rows = sorted(rows, key=lambda row: str(row.get("observed_at", "")), reverse=True)
    if not visible_rows:
        return f'<tr><td colspan="10">{html.escape(ui_label("ui.no_observations_filter"))}</td></tr>'

    body = []
    for row in visible_rows:
        location = row.get("location") if isinstance(row.get("location"), dict) else {}
        altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        observer = row.get("observer") if isinstance(row.get("observer"), dict) else {}
        species_id = str(row.get("species_id", ""))
        abundance = observation_catalog_label(catalogs, "observation_flush_abundance", row.get("flush_abundance"))
        validation = observation_catalog_label(catalogs, "observation_validation_statuses", row.get("validation_status"))
        calibration_use = observation_catalog_label(catalogs, "observation_calibration_uses", row.get("calibration_use"))
        validation_tone = "ok" if row.get("validation_status") == "valid" else "warn" if row.get("validation_status") in {"draft", "doubtful"} else "danger"
        use_tone = "ok" if row.get("calibration_use") == "include" else "danger" if row.get("calibration_use") == "exclude" else "warn"
        coordinates = "-"
        if isinstance(location, dict) and location.get("lat") is not None and location.get("lon") is not None:
            coordinates = f'{float(location.get("lat")):.5f}, {float(location.get("lon")):.5f}'
        altitude_text = "-"
        if isinstance(altitude, dict) and altitude.get("meters") is not None:
            altitude_text = f'{altitude.get("meters")} m'
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('observed_at', '-')))}</td>"
            f"<td><strong>{html.escape(species_labels.get(species_id, species_id))}</strong><br><span class=\"meta\">{html.escape(species_id)}</span></td>"
            f"<td>{html.escape(coordinates)}<br><span class=\"meta\">{html.escape(str(location.get('source', '-')) if isinstance(location, dict) else '-')}</span></td>"
            f"<td>{html.escape(altitude_text)}</td>"
            f"<td>{html.escape(abundance)}</td>"
            f"<td>{html.escape(str(observer.get('name', '-') or '-') if isinstance(observer, dict) else '-')}</td>"
            f"<td>{html.escape(str(source.get('label', source.get('type', '-')) or '-') if isinstance(source, dict) else '-')}</td>"
            f"<td>{observation_badge(validation, validation_tone)}</td>"
            f"<td>{observation_badge(calibration_use, use_tone)}</td>"
            "<td class=\"observation-row-actions\">"
            f"<a class=\"button-link compact\" href=\"#edit-observation-{html.escape(str(row.get('observation_id', '')), quote=True)}\">{html.escape(ui_label('ui.edit'))}</a>"
            "<form method=\"post\" action=\"\" onsubmit=\"return confirm('Archive this observation?')\">"
            "<input type=\"hidden\" name=\"profile_action\" value=\"archive_observation\">"
            f"<input type=\"hidden\" name=\"species_id\" value=\"{html.escape(species_id, quote=True)}\">"
            f"<input type=\"hidden\" name=\"observation_id\" value=\"{html.escape(str(row.get('observation_id', '')), quote=True)}\">"
            f"<button class=\"secondary compact\" type=\"submit\">{html.escape(ui_label('ui.archive'))}</button>"
            "</form>"
            "</td>"
            "</tr>"
        )
    return "".join(body)


def species_select_options(
    profiles: list[dict[str, object]],
    selected_species_id: str,
) -> str:
    """Render species options with the requested species selected."""
    return "".join(
        f'<option value="{html.escape(str(item.get("species_id", "")), quote=True)}"{" selected" if str(item.get("species_id", "")) == selected_species_id else ""}>{html.escape(str(item.get("scientific_name", item.get("species_id", ""))))}</option>'
        for item in profiles
        if item.get("species_id")
    )


def render_observation_detail(
    rows: list[dict[str, object]],
    catalogs: dict[str, object],
    species_labels: dict[str, str],
) -> str:
    """Render the most recent observation detail panel."""
    visible_rows = sorted(rows, key=lambda row: str(row.get("observed_at", "")), reverse=True)
    if not visible_rows:
        return """
        <h2 id="observation-detail">""" + html.escape(ui_label("ui.observation_detail")) + """</h2>
        <p class="meta">""" + html.escape(ui_label("ui.select_or_create_observation")) + """</p>
        """
    row = visible_rows[0]
    location = row.get("location") if isinstance(row.get("location"), dict) else {}
    altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
    site_context = row.get("site_context") if isinstance(row.get("site_context"), dict) else {}
    species_id = str(row.get("species_id", ""))
    coords = "-"
    if isinstance(location, dict) and location.get("lat") is not None and location.get("lon") is not None:
        coords = f'{location.get("lat")}, {location.get("lon")}'
    return f"""
    <h2 id="observation-detail">{html.escape(ui_label("ui.observation_detail"))}</h2>
    {value_row(ui_label("observation_id"), row.get("observation_id", "-"))}
    {value_row(ui_label("species_id"), species_labels.get(species_id, species_id))}
    {value_row(ui_label("ui.coordinates"), coords)}
    {value_row(ui_label("altitude.meters"), f'{altitude.get("meters")} m' if isinstance(altitude, dict) and altitude.get("meters") is not None else "-")}
    {value_row(ui_label("flush_abundance"), observation_catalog_label(catalogs, "observation_flush_abundance", row.get("flush_abundance")))}
    {value_row(ui_label("source_quality"), row.get("source_quality", "-"))}
    {value_row(ui_label("ui.calibration_weight"), f"{observation_weight(catalogs, row):.2f}")}
    <div class="observation-notes">
      <strong>{html.escape(ui_label("site_context.habitat_notes"))}</strong>
      <p>{html.escape(str(site_context.get("habitat_notes", "") or ui_label("ui.no_habitat_notes")) if isinstance(site_context, dict) else ui_label("ui.no_habitat_notes"))}</p>
      <strong>{html.escape(ui_label("site_context.host_notes"))}</strong>
      <p>{html.escape(str(site_context.get("host_notes", "") or ui_label("ui.no_host_notes")) if isinstance(site_context, dict) else ui_label("ui.no_host_notes"))}</p>
    </div>
    """


def render_observation_form_modal(
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    row: dict[str, object] | None,
    *,
    modal_id: str,
    action: str,
    title: str,
    selected_species_id: str = "",
    form_message: str = "",
) -> str:
    """Render create/edit observation modal using one shared field layout."""
    row = row if isinstance(row, dict) else {}
    location = row.get("location") if isinstance(row.get("location"), dict) else {}
    altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
    observer = row.get("observer") if isinstance(row.get("observer"), dict) else {}
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    site_context = row.get("site_context") if isinstance(row.get("site_context"), dict) else {}
    observation_id = str(row.get("observation_id", ""))
    current_species_id = str(row.get("species_id", "") or selected_species_id)
    location_input = str(location.get("input", "") if isinstance(location, dict) else "")
    lat_value = "" if not isinstance(location, dict) or location.get("lat") is None else str(location.get("lat"))
    lon_value = "" if not isinstance(location, dict) or location.get("lon") is None else str(location.get("lon"))
    altitude_value = "" if not isinstance(altitude, dict) or altitude.get("meters") is None else str(altitude.get("meters"))
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <a class="modal-backdrop" href="#" aria-label="{html.escape(ui_label("ui.cancel"), quote=True)}"></a>
      <form class="modal-card modal-card-wide observation-form" method="post" action="">
        <input type="hidden" name="profile_action" value="{html.escape(action, quote=True)}">
        {f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">' if observation_id else ""}
        <header class="modal-head">
          <div>
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(ui_label("ui.observation_form_help"))}</p>
          </div>
          <a class="button-link" href="#">{html.escape(ui_label("ui.cancel"))}</a>
        </header>
        {f'<div class="catalog-alert error"><strong>{html.escape(ui_label("ui.observation_not_saved"))}</strong><br>{html.escape(form_message.replace("Observation was not saved: ", ""))}</div>' if form_message else ""}
        <div class="profile-grid four">
          <div class="admin-field"><label>{html.escape(ui_label("species_id"))}</label><select name="observation_species_id" required>{species_select_options(profiles, current_species_id)}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("observed_at"))}</label><input name="observed_at" type="date" value="{html.escape(str(row.get("observed_at", "")), quote=True)}" onchange="this.blur()" required></div>
          <div class="admin-field"><label>{html.escape(ui_label("flush_abundance"))}</label><select name="flush_abundance" required>{catalog_select_options(catalogs, "observation_flush_abundance", str(row.get("flush_abundance", "") or "normal"))}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("source_quality"))}</label><input name="source_quality" type="number" min="0" max="1" step="0.05" value="{html.escape(str(row.get("source_quality", 0.75)), quote=True)}" required></div>
        </div>
        <div class="profile-grid three">
          <div class="admin-field wide"><label>{html.escape(ui_label("location.input"))}</label><input name="location_input" value="{html.escape(location_input, quote=True)}" placeholder="41.38740, 2.16860 or Google Maps URL"></div>
          <div class="admin-field"><label>{html.escape(ui_label("location.lat"))}</label><input name="location_lat" type="number" step="any" value="{html.escape(lat_value, quote=True)}"></div>
          <div class="admin-field"><label>{html.escape(ui_label("location.lon"))}</label><input name="location_lon" type="number" step="any" value="{html.escape(lon_value, quote=True)}"></div>
        </div>
        <div class="profile-grid four">
          <div class="admin-field"><label>{html.escape(ui_label("altitude.meters"))}</label><input name="altitude_m" type="number" step="1" value="{html.escape(altitude_value, quote=True)}"></div>
          <div class="admin-field"><label>{html.escape(ui_label("altitude.source"))}</label><select name="altitude_source">{catalog_select_options(catalogs, "observation_altitude_sources", str(altitude.get("source", "") if isinstance(altitude, dict) else ""), ui_label("ui.not_informed"))}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("validation_status"))}</label><select name="validation_status" required>{catalog_select_options(catalogs, "observation_validation_statuses", str(row.get("validation_status", "") or "draft"))}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("calibration_use"))}</label><select name="calibration_use" required>{catalog_select_options(catalogs, "observation_calibration_uses", str(row.get("calibration_use", "") or "review"))}</select></div>
        </div>
        <div class="profile-grid four">
          <div class="admin-field"><label>{html.escape(ui_label("calibration_exclusion_reason"))}</label><select name="calibration_exclusion_reason">{catalog_select_options(catalogs, "observation_exclusion_reasons", str(row.get("calibration_exclusion_reason", "") or ""), ui_label("ui.none"))}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("observer.name"))}</label><input name="observer_name" value="{html.escape(str(observer.get("name", "") if isinstance(observer, dict) else ""), quote=True)}"></div>
          <div class="admin-field"><label>{html.escape(ui_label("observer.expertise"))}</label><select name="observer_expertise">{catalog_select_options(catalogs, "observer_expertise_levels", str(observer.get("expertise", "") if isinstance(observer, dict) else "") or "unknown")}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("source.type"))}</label><select name="source_type">{catalog_select_options(catalogs, "observation_source_types", str(source.get("type", "") if isinstance(source, dict) else "") or "personal_observation")}</select></div>
        </div>
        <div class="profile-grid two">
          <div class="admin-field"><label>{html.escape(ui_label("source.label"))}</label><input name="source_label" value="{html.escape(str(source.get("label", "") if isinstance(source, dict) else ""), quote=True)}"></div>
          <div class="admin-field wide"><label>{html.escape(ui_label("source.url"))}</label><input name="source_url" type="url" value="{html.escape(str(source.get("url", "") if isinstance(source, dict) else ""), quote=True)}"></div>
        </div>
        <div class="profile-grid two">
          {form_textarea("habitat_notes", ui_label("site_context.habitat_notes"), site_context.get("habitat_notes", "") if isinstance(site_context, dict) else "", rows=3)}
          {form_textarea("host_notes", ui_label("site_context.host_notes"), site_context.get("host_notes", "") if isinstance(site_context, dict) else "", rows=3)}
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.save_observation"))}</button>
          <button class="secondary planned-action" type="button" disabled>{html.escape(ui_label("ui.recover_altitude"))}</button>
          <button class="secondary planned-action" type="button" disabled>{html.escape(ui_label("ui.import_csv"))}</button>
        </div>
      </form>
    </div>
    """


def render_observation_create_form(
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    selected_species_id: str,
    form_message: str = "",
) -> str:
    """Render the observation creation modal."""
    return render_observation_form_modal(
        profiles,
        catalogs,
        None,
        modal_id="new-observation",
        action="create_observation",
        title=ui_label("ui.new_observation"),
        selected_species_id=selected_species_id,
        form_message=form_message,
    )


def render_observation_edit_modals(
    rows: list[dict[str, object]],
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    selected_species_id: str,
) -> str:
    """Render edit modals for active observations in the current filter."""
    visible_rows = rows
    if selected_species_id:
        visible_rows = [row for row in rows if str(row.get("species_id", "")) == selected_species_id]
    return "".join(
        render_observation_form_modal(
            profiles,
            catalogs,
            row,
            modal_id=f"edit-observation-{str(row.get('observation_id', ''))}",
            action="update_observation",
            title=f"{ui_label('ui.edit_observation')} {str(row.get('observation_id', ''))}",
            selected_species_id=selected_species_id,
        )
        for row in visible_rows
        if row.get("observation_id")
    )


def render_archived_observations_panel(
    archived_payload: dict[str, object] | None,
    species_labels: dict[str, str],
    selected_species_id: str,
) -> str:
    """Render archived observation restore/delete controls."""
    archived = observations_from_payload(archived_payload)
    if selected_species_id:
        archived = [row for row in archived if str(row.get("species_id", "")) == selected_species_id]
    if not archived:
        return f'<details class="profile-section-card"><summary><strong>{html.escape(ui_label("ui.archived_observations"))}</strong></summary><p class="meta">{html.escape(ui_label("ui.no_archived_observations"))}</p></details>'
    rows = []
    for row in sorted(archived, key=lambda item: str(item.get("observed_at", "")), reverse=True):
        observation_id = str(row.get("observation_id", ""))
        species_id = str(row.get("species_id", ""))
        rows.append(
            '<div class="archived-species-row">'
            f'<div><strong>{html.escape(observation_id)}</strong><br><span class="meta">{html.escape(str(row.get("observed_at", "-")))} · {html.escape(species_labels.get(species_id, species_id))}</span></div>'
            '<div class="archived-species-actions">'
            '<form method="post" action="">'
            '<input type="hidden" name="profile_action" value="restore_observation">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">'
            f'<button class="secondary" type="submit">{html.escape(ui_label("ui.restore"))}</button>'
            '</form>'
            '<form method="post" action="" onsubmit="return confirm(\'Delete this archived observation permanently?\') && confirm(\'This action cannot be undone. The archived copy will be removed permanently.\')">'
            '<input type="hidden" name="profile_action" value="delete_archived_observation">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">'
            f'<input type="hidden" name="delete_confirm_id" value="{html.escape(observation_id, quote=True)}">'
            f'<button class="danger" type="submit">{html.escape(ui_label("ui.delete_permanently"))}</button>'
            '</form>'
            '</div></div>'
        )
    return f'<details class="profile-section-card"><summary><strong>{html.escape(ui_label("ui.archived_observations"))}</strong></summary><div class="archived-observations-list">' + "".join(rows) + '</div></details>'


def render_observations_section(
    profile: dict[str, object] | None,
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    observations_payload: dict[str, object] | None,
    archived_observations_payload: dict[str, object] | None,
    search: str = "",
    form_message: str = "",
    filters: dict[str, str] | None = None,
) -> str:
    """Render the observation workspace backed by mushroom_observations.json."""
    selected_species_id = str(profile.get("species_id", "")) if profile else ""
    rows = observations_from_payload(observations_payload)
    filtered_rows = filtered_observation_rows(rows, selected_species_id, filters)
    species_labels = profile_name_map(profiles)
    total, positive, negative, pending = observation_metrics(filtered_rows)
    calibration_href = profile_query_url(selected_species_id, search, section="calibration") if selected_species_id else profile_query_url(section="calibration")
    today_value = date.today().isoformat()
    date_from = observation_filter_value(filters, "date_from")
    date_to = observation_filter_value(filters, "date_to")
    result_filter = observation_filter_value(filters, "result")
    validation_filter = observation_filter_value(filters, "validation")
    observation_search = observation_filter_value(filters, "obs_q")
    species_filter_options = f'<option value="">{html.escape(ui_label("ui.all_species"))}</option>' + "".join(
        f'<option value="{html.escape(str(item.get("species_id", "")), quote=True)}"{" selected" if str(item.get("species_id", "")) == selected_species_id else ""}>{html.escape(str(item.get("scientific_name", item.get("species_id", ""))))}</option>'
        for item in profiles
        if item.get("species_id")
    )
    return f"""
    <section class="card profile-section-screen observations-screen">
      {render_selected_species_header(profile, ui_label("ui.observations")) if profile else f'<h2>{html.escape(ui_label("ui.observations"))}</h2>'}
      <div class="profile-calibration-cards observations-metrics">
        <div class="profile-metric"><span class="label">{icon("metadata")} {html.escape(ui_label("ui.total_observations"))}</span><span class="value">{total}</span></div>
        <div class="profile-metric"><span class="label">{icon("mushroom")} {html.escape(ui_label("ui.positive_present"))}</span><span class="value ok">{positive}</span></div>
        <div class="profile-metric"><span class="label">{icon("scoring")} {html.escape(ui_label("ui.negative_absent"))}</span><span class="value danger">{negative}</span></div>
        <div class="profile-metric"><span class="label">{icon("calibration")} {html.escape(ui_label("ui.pending_validation"))}</span><span class="value warn">{pending}</span></div>
      </div>
      <form class="observations-filters" method="get" action="">
        <input type="hidden" name="section" value="observations">
        <input type="hidden" name="q" value="{html.escape(search, quote=True)}">
        <div class="admin-field"><label>{html.escape(ui_label("ui.date_from"))}</label><input name="date_from" type="date" value="{html.escape(date_from, quote=True)}" max="9999-12-31" placeholder="{html.escape(today_value, quote=True)}" onchange="this.blur(); this.form.submit()"></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.date_to"))}</label><input name="date_to" type="date" value="{html.escape(date_to, quote=True)}" max="9999-12-31" placeholder="{html.escape(today_value, quote=True)}" onchange="this.blur(); this.form.submit()"></div>
        <div class="admin-field"><label>{html.escape(ui_label("species_id"))}</label><select name="id" onchange="this.form.submit()">{species_filter_options}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.result"))}</label><select name="result" onchange="this.form.submit()">{catalog_select_options(catalogs, "observation_flush_abundance", result_filter, ui_label("ui.all"))}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("validation_status"))}</label><select name="validation" onchange="this.form.submit()">{catalog_select_options(catalogs, "observation_validation_statuses", validation_filter, ui_label("ui.all"))}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.search"))}</label><input name="obs_q" type="search" value="{html.escape(observation_search, quote=True)}"></div>
      </form>
      <div class="observations-layout">
        <article class="profile-section-card observations-table-card">
          <h2>{icon("metadata")} {html.escape(ui_label("ui.observation_records"))}</h2>
          <div class="observations-table-shell">
            <table>
              <thead><tr><th>{html.escape(ui_label("observed_at"))}</th><th>{html.escape(ui_label("species_id"))}</th><th>{html.escape(ui_label("ui.coordinates"))}</th><th>{html.escape(ui_label("ui.altitude_short"))}</th><th>{html.escape(ui_label("flush_abundance"))}</th><th>{html.escape(ui_label("observer.name"))}</th><th>{html.escape(ui_label("source.label"))}</th><th>{html.escape(ui_label("validation_status"))}</th><th>{html.escape(ui_label("ui.use"))}</th><th></th></tr></thead>
              <tbody>{render_observation_table(filtered_rows, catalogs, species_labels)}</tbody>
            </table>
          </div>
        </article>
        <aside class="profile-section-card observation-detail-shell">
          {render_observation_detail(filtered_rows, catalogs, species_labels)}
        </aside>
      </div>
      {render_archived_observations_panel(archived_observations_payload, species_labels, selected_species_id)}
      {render_observation_create_form(profiles, catalogs, selected_species_id, form_message)}
      {render_observation_edit_modals(filtered_rows, profiles, catalogs, selected_species_id)}
      <div class="profile-action-bar">
        <a class="button-link primary-link" href="#new-observation">{html.escape(ui_label("ui.new_observation"))}</a>
        <a class="button-link" href="{html.escape(calibration_href, quote=True)}">{html.escape(ui_label("ui.open_calibration"))}</a>
      </div>
    </section>
    """


def render_profile_full_json_panel(payload: dict[str, object], mode: str) -> str:
    """Render advanced full-file JSON maintenance for profiles."""
    json_value = json.dumps(payload, indent=2, ensure_ascii=False)
    mode_label = ui_label("ui.empty_template") if mode == "template" else ui_label("ui.current_profiles")
    return f"""
    <details class="card" {"open" if mode == "template" else ""}>
      <summary><strong>{html.escape(ui_label("ui.full_profiles_json_import_export"))}</strong> · {html.escape(mode_label)}</summary>
      <p>{html.escape(ui_label("ui.import_export_help_profiles"))}</p>
      <div class="quick-actions">
        <a class="button-link" href="?mode=current">{html.escape(ui_label("ui.current_profiles"))}</a>
        <a class="button-link" href="?mode=default">{html.escape(ui_label("ui.packaged_default"))}</a>
        <a class="button-link" href="?mode=template">{html.escape(ui_label("ui.empty_template"))}</a>
      </div>
      <form class="profile-json-editor" method="post" action="" onsubmit="return confirm('Replace the full profiles JSON after validation?')">
        <input type="hidden" name="profile_action" value="save_profiles">
        <label class="label" for="profiles-full-json">{html.escape(ui_label("ui.profiles_json"))}</label>
        <textarea id="profiles-full-json" name="profiles_json" spellcheck="false">{html.escape(json_value)}</textarea>
        <button class="primary">{html.escape(ui_label("ui.validate_save_full_profiles"))}</button>
      </form>
    </details>
    """
