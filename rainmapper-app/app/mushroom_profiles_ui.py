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
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from rainmapper_core import mushroom_paths


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


def profile_query_url(
    species_id: str = "",
    search: str = "",
    mode: str = "",
    section: str = "",
    profile_view: str = "",
    evidence_view: str = "",
    parameter_view: str = "",
) -> str:
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
    if profile_view:
        params["view"] = profile_view
    if evidence_view and evidence_view != "hosts_forests":
        params["evidence_view"] = evidence_view
    if parameter_view and parameter_view != "habitat":
        params["parameter_view"] = parameter_view
    return ("?" + urlencode(params)) if params else "?"


def normalize_profile_view(value: object) -> str:
    """Return the active profile maintenance view."""
    text = str(value or "").strip().lower()
    return "v0" if text == "v0" else "enriched"


def is_v0_view(profile_view: str) -> bool:
    return normalize_profile_view(profile_view) == "v0"


PARAMETER_VIEWS = ("habitat", "soils", "topography", "phenology", "climate")


def available_parameter_views(profile_view: str) -> tuple[str, ...]:
    """Return parameter tabs available for the active profile view."""
    if is_v0_view(profile_view):
        return ("habitat", "soils", "topography", "phenology")
    return PARAMETER_VIEWS


def normalize_parameter_view(value: object, profile_view: str = "enriched") -> str:
    """Return the active parameter sub-section."""
    text = str(value or "").strip().lower()
    allowed = available_parameter_views(profile_view)
    return text if text in allowed else allowed[0]


def v0_active_affinity(item: dict[str, object]) -> bool:
    return item.get("v0_active") is not False


def inactive_v0_affinity_count(ecology: dict[str, object]) -> int:
    count = 0
    for field in PROFILE_AFFINITY_GROUPS:
        values = ecology.get(field)
        if isinstance(values, list):
            count += sum(1 for item in values if isinstance(item, dict) and item.get("v0_active") is False)
    return count


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


def host_observation_label(item: dict[str, object], language: str = UI_LANGUAGE) -> str:
    """Return a compact field-observation label for a host taxon."""
    common_names = item.get("common_names")
    if isinstance(common_names, dict):
        names = common_names.get(language) or common_names.get("en")
        if isinstance(names, list) and names:
            return str(names[0])
        if isinstance(names, str) and names:
            return names
    scientific = item.get("scientific_name")
    if scientific:
        return str(scientific)
    return str(item.get("id", ""))


def host_scientific_common_label(item: dict[str, object], language: str = UI_LANGUAGE) -> str:
    """Return a host label with scientific and localized common names."""
    scientific = str(item.get("scientific_name", "") or "").strip()
    common = host_observation_label(item, language).strip()
    item_id = str(item.get("id", "") or "").strip()
    if scientific and common and common != scientific:
        return f"{scientific} - {common}"
    if scientific:
        return scientific
    if common:
        return common
    return item_id


def host_observation_label_map(catalogs: dict[str, object]) -> dict[str, str]:
    """Return host labels meant for the field-observation selector."""
    items = catalogs.get("host_taxa")
    if not isinstance(items, list):
        return {}
    labels: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "") or "").strip()
        if item_id:
            labels[item_id] = host_observation_label(item)
    return labels


def host_affinity_options(catalogs: dict[str, object]) -> list[tuple[str, str]]:
    """Return host options for species affinities with scientific and UI-language names."""
    items = catalogs.get("host_taxa")
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
        item_id = str(item.get("id", "") or "").strip()
        if item_id:
            options.append((item_id, host_scientific_common_label(item)))
    return options


def observed_host_toggles(catalogs: dict[str, object], selected_values: object) -> str:
    """Render observed-host checkboxes with the same chip pattern used by month toggles."""
    selected = {str(value) for value in selected_values if str(value or "")} if isinstance(selected_values, list) else set()
    items = catalogs.get("host_taxa")
    items = items if isinstance(items, list) else []
    sorted_items = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: (
            item.get("sort_order") if isinstance(item.get("sort_order"), (int, float)) else 999999,
            host_observation_label(item).lower(),
            str(item.get("id", "")),
        ),
    )
    chips = []
    seen: set[str] = set()
    for item in sorted_items:
        item_id = str(item.get("id", "") or "").strip()
        if not item_id:
            continue
        seen.add(item_id)
        checked = " checked" if item_id in selected else ""
        chips.append(
            '<label class="month-toggle host-toggle">'
            f'<input type="checkbox" name="observed_host_ids" value="{html.escape(item_id, quote=True)}"{checked}>'
            f'<span class="month-chip host-chip active">{html.escape(host_observation_label(item))}</span>'
            '</label>'
        )
    for missing_id in sorted(selected - seen):
        chips.append(
            '<span class="month-chip host-chip warn">'
            f'{html.escape(missing_id)}'
            '</span>'
        )
    return "".join(chips)


def observation_catalog_toggles(
    catalogs: dict[str, object],
    group: str,
    field_name: str,
    selected_values: object,
) -> str:
    """Render optional observed site-context catalog values as compact chips."""
    selected = {str(value) for value in selected_values if str(value or "")} if isinstance(selected_values, list) else set()
    items = catalogs.get(group)
    items = items if isinstance(items, list) else []
    chips = []
    seen: set[str] = set()
    for item_id, label in catalog_options_for_group(catalogs, group):
        seen.add(item_id)
        checked = " checked" if item_id in selected else ""
        chips.append(
            '<label class="catalog-toggle observation-context-toggle">'
            f'<input type="checkbox" name="{html.escape(field_name, quote=True)}" value="{html.escape(item_id, quote=True)}"{checked}>'
            f'<span class="catalog-chip">{html.escape(label)}</span>'
            '</label>'
        )
    for missing_id in sorted(selected - seen):
        chips.append(f'<span class="catalog-chip missing">{html.escape(missing_id)}</span>')
    return "".join(chips)


def observation_catalog_names(catalogs: dict[str, object], group: str, values: object) -> str:
    """Return readable observed site-context catalog labels."""
    if not isinstance(values, list) or not values:
        return "-"
    labels = catalog_label_map(catalogs, group)
    return ", ".join(labels.get(str(value), str(value)) for value in values if str(value or ""))


def observed_host_names(catalogs: dict[str, object], site_context: dict[str, object]) -> str:
    """Return a readable list of manually observed hosts."""
    host_ids = site_context.get("observed_host_ids")
    if not isinstance(host_ids, list) or not host_ids:
        return "-"
    labels = host_observation_label_map(catalogs)
    return ", ".join(labels.get(str(host_id), str(host_id)) for host_id in host_ids if str(host_id or ""))


def affinity_badge(text: str, tone: str) -> str:
    """Render a separated visual badge inside a compact affinity chip."""
    return (
        f'<span class="parameter-affinity-badge {html.escape(tone, quote=True)}">'
        f'{html.escape(text)}</span>'
    )


def affinity_relationship_badge(item: dict[str, object], relationship: str) -> str:
    """Return a human relationship badge for parameter affinity chips."""
    labels = {
        "primary": ("Principal", "primary"),
        "preferred": ("Preferente", "preferred"),
        "secondary": ("Secundario", "secondary"),
        "possible": ("Posible", "possible"),
        "avoid": ("Evitar", "avoid"),
    }
    label, tone = labels.get(relationship, (relationship, "neutral"))
    return affinity_badge(label, tone)


def affinity_source_label(source_id: str) -> str:
    labels = {
        "literature_marc_estevez": ui_label("ui.source_marc_estevez"),
    }
    return labels.get(source_id, source_id)


def affinity_origin_badges(item: dict[str, object], profile_source_v0: bool = False) -> str:
    """Render the explicit provenance known for an ecology affinity row."""
    origins: list[tuple[str, str]] = []
    source_ids = item.get("source_ids")
    if isinstance(source_ids, list):
        for source_id in source_ids:
            source_text = str(source_id or "").strip()
            if source_text:
                origins.append((source_text, affinity_source_label(source_text)))
    active_v0_row = item.get("v0_active") is not False
    if not origins and active_v0_row and (profile_source_v0 or item.get("v0_placeholder")):
        origins.append(("v0", ui_label("ui.source_v0")))
    unique_origins = []
    seen = set()
    for tone, label in origins:
        key = (tone, label)
        if key not in seen:
            unique_origins.append((tone, label))
            seen.add(key)
    if not unique_origins:
        return '<span class="profile-origin-empty">-</span>'
    badges = "".join(
        f'<span class="profile-origin-badge {css_token(tone)}">{html.escape(label)}</span>'
        for tone, label in unique_origins
    )
    return f'<div class="profile-origin-badges">{badges}</div>'


def affinity_hidden_metadata_fields(field: str, index: int, item: dict[str, object]) -> str:
    """Preserve non-editable affinity metadata while allowing visible edits."""
    current_id = str(item.get("id", "") or "").strip()
    if not current_id:
        return ""
    hidden = [
        f'<input type="hidden" name="{html.escape(field, quote=True)}_{index}_original_id" value="{html.escape(current_id, quote=True)}">'
    ]
    source_ids = item.get("source_ids")
    if isinstance(source_ids, list):
        for source_id in source_ids:
            source_text = str(source_id or "").strip()
            if source_text:
                hidden.append(
                    f'<input type="hidden" name="{html.escape(field, quote=True)}_{index}_source_ids" value="{html.escape(source_text, quote=True)}">'
                )
    if item.get("v0_placeholder") is True:
        hidden.append(f'<input type="hidden" name="{html.escape(field, quote=True)}_{index}_v0_placeholder" value="true">')
    if item.get("v0_active") is False:
        hidden.append(f'<input type="hidden" name="{html.escape(field, quote=True)}_{index}_v0_active" value="false">')
    return "".join(hidden)


def affinity_chip_list(
    ecology: dict[str, object],
    key: str,
    labels: dict[str, str],
    relationship: str | None = None,
    exclude_relationships: set[str] | None = None,
    limit: int = 6,
    profile_view: str = "enriched",
) -> str:
    """Render affinity rows as compact chips, optionally filtered by relationship."""
    raw_items = ecology.get(key)
    items = raw_items if isinstance(raw_items, list) else []
    chips = []
    for item in items:
        if not isinstance(item, dict):
            continue
        inactive_v0 = item.get("v0_active") is False
        if is_v0_view(profile_view) and inactive_v0:
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
        badges = []
        if item_relationship and not relationship:
            badges.append(affinity_relationship_badge(item, item_relationship))
        source_ids = item.get("source_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                source_text = str(source_id or "").strip()
                if source_text:
                    badges.append(affinity_badge(affinity_source_label(source_text), "source"))
        if item.get("v0_placeholder"):
            badges.append(affinity_badge("v0", "v0"))
        if inactive_v0:
            badges.append(affinity_badge("Aparcado", "parked"))
        badge_html = f'<span class="parameter-affinity-badges">{"".join(badges)}</span>' if badges else ""
        css_class = "parameter-affinity-chip parked" if inactive_v0 else "parameter-affinity-chip"
        chips.append(
            f'<span class="{css_class}" title="{html.escape(item_id, quote=True)}">'
            f'<span class="parameter-affinity-label">{html.escape(visible_label)}</span>{badge_html}</span>'
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


def render_profile_list(profiles: list[dict[str, object]], selected_id: str, search: str, profile_view: str = "enriched") -> str:
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
            f'<a class="profile-list-item{active}" href="{profile_query_url(species_id, search, profile_view=profile_view)}">'
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


def render_section_tabs(active_section: str, selected_id: str, search: str, profile_view: str = "enriched") -> str:
    """Render top-level mushroom maintenance tabs as ingress-safe links."""
    sections = [
        ("summary", ui_label("ui.summary")),
        ("species", ui_label("ui.species")),
        ("observations", ui_label("ui.observations")),
        ("evidence", "Evidencia"),
        ("parameters", ui_label("ui.parameters")),
        ("calibration", ui_label("ui.calibration")),
    ]
    links = []
    for section, label in sections:
        active = ' class="active"' if section == active_section else ""
        href = profile_query_url(selected_id, search, section=section, profile_view=profile_view)
        links.append(f'<a{active} href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    return '<nav class="mushroom-section-tabs" aria-label="Mushroom maintenance sections">' + "".join(links) + "</nav>"


def render_profile_view_switch(selected_id: str, search: str, section: str, profile_view: str) -> str:
    """Render the V0/Enriched mode switch without changing the underlying data."""
    current = normalize_profile_view(profile_view)
    v0_href = profile_query_url(selected_id, search, section=section, profile_view="v0")
    enriched_href = profile_query_url(selected_id, search, section=section, profile_view="enriched")
    return (
        '<div class="profile-view-switch toolbar-switch">'
        f'<a class="button-link {"active" if current == "v0" else ""}" href="{html.escape(v0_href, quote=True)}">V0</a>'
        f'<a class="button-link {"active" if current == "enriched" else ""}" href="{html.escape(enriched_href, quote=True)}">Enriched</a>'
        "</div>"
    )


def render_parameter_tabs(
    active_view: str,
    selected_id: str,
    search: str,
    profile_view: str = "enriched",
) -> str:
    """Render internal tabs for the Parameters screen."""
    labels = {
        "habitat": ui_label("ui.ecology"),
        "soils": ui_label("ui.soils"),
        "topography": ui_label("ui.topography"),
        "phenology": ui_label("ui.phenology"),
        "climate": ui_label("ui.weather"),
    }
    links = []
    for view in available_parameter_views(profile_view):
        active = ' class="active" aria-selected="true"' if view == active_view else ' aria-selected="false"'
        href = profile_query_url(
            selected_id,
            search,
            section="parameters",
            profile_view=profile_view,
            parameter_view=view,
        )
        links.append(
            f'<a role="tab"{active} href="{html.escape(href, quote=True)}">'
            f'{html.escape(labels.get(view, view))}</a>'
        )
    return '<nav class="parameter-section-tabs" role="tablist" aria-label="Parameter sections">' + "".join(links) + "</nav>"


def species_header_selector(
    profiles: list[dict[str, object]] | None,
    selected_id: str,
    *,
    search: str = "",
    section_key: str = "",
    profile_view: str = "enriched",
    evidence_view: str = "",
    parameter_view: str = "",
    include_all: bool = False,
    all_selected: bool = False,
    select_name: str = "id",
) -> str:
    """Render a compact species selector for section headers."""
    if not profiles:
        return ""
    options = []
    if include_all:
        options.append(
            f'<option value="__all__"{" selected" if all_selected else ""}>{html.escape(ui_label("ui.all_species"))}</option>'
        )
    for item in profiles:
        species_id = str(item.get("species_id", "") or "")
        if not species_id:
            continue
        selected = " selected" if not all_selected and species_id == selected_id else ""
        label = str(item.get("scientific_name", species_id) or species_id)
        common = profile_common_name(item)
        visible_label = f"{label} - {common}" if common else label
        options.append(f'<option value="{html.escape(species_id, quote=True)}"{selected}>{html.escape(visible_label)}</option>')
    if not options:
        return ""
    hidden = []
    if section_key:
        hidden.append(f'<input type="hidden" name="section" value="{html.escape(section_key, quote=True)}">')
    if search:
        hidden.append(f'<input type="hidden" name="q" value="{html.escape(search, quote=True)}">')
    if profile_view and normalize_profile_view(profile_view) == "v0":
        hidden.append('<input type="hidden" name="view" value="v0">')
    if evidence_view:
        hidden.append(f'<input type="hidden" name="evidence_view" value="{html.escape(evidence_view, quote=True)}">')
    if parameter_view:
        hidden.append(f'<input type="hidden" name="parameter_view" value="{html.escape(parameter_view, quote=True)}">')
    return (
        '<form class="profile-header-selector" method="get" action="">'
        f'<label>{html.escape(ui_label("ui.change_species"))}</label>'
        f'{"".join(hidden)}'
        f'<select name="{html.escape(select_name, quote=True)}" onchange="this.form.submit()">{"".join(options)}</select>'
        "</form>"
    )


def render_selected_species_header(
    profile: dict[str, object] | None,
    section: str,
    profiles: list[dict[str, object]] | None = None,
    search: str = "",
    section_key: str = "",
    profile_view: str = "enriched",
    evidence_view: str = "",
    parameter_view: str = "",
    include_all: bool = False,
    all_selected: bool = False,
    select_name: str = "id",
    compact: bool = False,
) -> str:
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
    selector = species_header_selector(
        profiles,
        species_id,
        search=search,
        section_key=section_key,
        profile_view=profile_view,
        evidence_view=evidence_view,
        parameter_view=parameter_view,
        include_all=include_all,
        all_selected=all_selected,
        select_name=select_name,
    )
    section_label = "" if compact else f'<span class="meta">{html.escape(section)}</span>'
    banner_class = "profile-section-banner compact" if compact else "profile-section-banner"
    return f"""
    <header class="{banner_class}">
      <div class="profile-title-block">
        <span class="profile-hero-icon">{icon("mushroom")}</span>
        <div>
          {section_label}
          <h2>{html.escape(str(profile.get("scientific_name", species_id)))}</h2>
          <p class="meta">species_id: {html.escape(species_id)} · {html.escape(profile_common_name(profile) or "-")}</p>
        </div>
      </div>
      <div class="profile-hero-side">
        <div class="profile-hero-chips">{chips}</div>
        {selector}
      </div>
    </header>
    """


def render_observation_scope_header(
    profile: dict[str, object] | None,
    section: str,
    species_filter: str,
    profiles: list[dict[str, object]] | None = None,
    search: str = "",
) -> str:
    """Render the observation banner using the active observation species filter."""
    selected_id = str(profile.get("species_id", "") or "") if profile else ""
    selector = species_header_selector(
        profiles,
        selected_id,
        search=search,
        section_key="observations",
        include_all=True,
        all_selected=species_filter == "__all__",
        select_name="obs_species",
    )
    if species_filter == "__all__":
        return f"""
        <header class="profile-section-banner">
          <div class="profile-title-block">
            <span class="profile-hero-icon">{icon("mushroom")}</span>
            <div>
              <span class="meta">{html.escape(section)}</span>
              <h2>{html.escape(ui_label("ui.all_species"))}</h2>
              <p class="meta">{html.escape(ui_label("ui.observation_records"))}</p>
            </div>
          </div>
          <div class="profile-hero-side">{selector}</div>
        </header>
        """
    return render_selected_species_header(
        profile,
        section,
        profiles=profiles,
        search=search,
        section_key="observations",
        include_all=True,
        all_selected=False,
        select_name="obs_species",
    ) if profile else f'<h2>{html.escape(section)}</h2>'


LOCAL_EVIDENCE_GROUPS = [
    {
        "title_label": "ui.evidence_hosts",
        "catalog_group": "host_taxa",
        "profile_field": "host_affinities",
        "context_field": "host_ids",
        "evidence_view": "hosts_forests",
    },
    {
        "title_label": "ui.evidence_forests",
        "catalog_group": "forest_types",
        "profile_field": "forest_type_affinities",
        "context_field": "forest_type_ids",
        "evidence_view": "hosts_forests",
    },
    {
        "title_label": "ui.evidence_soils",
        "catalog_group": "soil_types",
        "profile_field": "soil_affinities",
        "context_field": "soil_tendency_ids",
        "evidence_view": "soils_habitat",
    },
    {
        "title_label": "ui.evidence_habitat",
        "catalog_group": "habitat_features",
        "profile_field": "habitat_feature_affinities",
        "context_field": "habitat_feature_ids",
        "evidence_view": "soils_habitat",
    },
]


def profile_v0_affinity_ids(ecology: dict[str, object], field: str) -> list[str]:
    """Return active v0 affinity IDs declared by the current profile."""
    values = ecology.get(field)
    if not isinstance(values, list):
        return []
    ids = []
    for item in values:
        if not isinstance(item, dict) or not v0_active_affinity(item):
            continue
        item_id = str(item.get("id", "") or "").strip()
        if item_id and item_id not in ids:
            ids.append(item_id)
    return ids


def local_evidence_counts(
    species_id: str,
    reconstruction_payload: dict[str, object] | None,
) -> tuple[int, dict[str, dict[str, dict[str, object]]]]:
    """Aggregate latest observation GIS v0 contexts for one species."""
    results = reconstruction_payload.get("results") if isinstance(reconstruction_payload, dict) else None
    rows = results if isinstance(results, list) else []
    counts: dict[str, dict[str, dict[str, object]]] = {
        str(group["context_field"]): {} for group in LOCAL_EVIDENCE_GROUPS
    }
    observation_count = 0
    seen_observations: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or str(row.get("species_id", "") or "") != species_id:
            continue
        context = row.get("gis_context_v0")
        if not isinstance(context, dict):
            continue
        observation_id = str(row.get("observation_id", "") or "")
        if observation_id and observation_id not in seen_observations:
            seen_observations.add(observation_id)
            observation_count += 1
        for group in LOCAL_EVIDENCE_GROUPS:
            context_field = str(group["context_field"])
            values = context.get(context_field)
            if not isinstance(values, list):
                continue
            for value in values:
                item_id = str(value or "").strip()
                if not item_id:
                    continue
                item = counts[context_field].setdefault(item_id, {"count": 0, "observations": []})
                item["count"] = int(item.get("count", 0) or 0) + 1
                examples = item.get("observations")
                if isinstance(examples, list) and observation_id and observation_id not in examples:
                    examples.append(observation_id)
    return observation_count, counts


def local_evidence_counts_from_features(
    species_id: str,
    features_payload: dict[str, object] | None,
) -> tuple[int, dict[str, dict[str, dict[str, object]]]]:
    """Aggregate joined v0 features for one species, preserving Campo/GIS origins."""
    rows = features_payload.get("rows") if isinstance(features_payload, dict) else None
    feature_rows = rows if isinstance(rows, list) else []
    counts: dict[str, dict[str, dict[str, object]]] = {
        str(group["context_field"]): {} for group in LOCAL_EVIDENCE_GROUPS
    }
    observation_count = 0
    seen_observations: set[str] = set()
    for row in feature_rows:
        if not isinstance(row, dict) or str(row.get("species_id", "") or "") != species_id:
            continue
        observation_id = str(row.get("observation_id", "") or "").strip()
        if observation_id and observation_id not in seen_observations:
            seen_observations.add(observation_id)
            observation_count += 1
        for group in LOCAL_EVIDENCE_GROUPS:
            context_field = str(group["context_field"])
            values = row.get(context_field)
            if not isinstance(values, list):
                continue
            source_values = row.get(context_field.replace("_ids", "_sources"))
            sources_by_id = source_values if isinstance(source_values, dict) else {}
            for value in values:
                item_id = str(value or "").strip()
                if not item_id:
                    continue
                item = counts[context_field].setdefault(
                    item_id,
                    {"count": 0, "observations": [], "sources": []},
                )
                item["count"] = int(item.get("count", 0) or 0) + 1
                examples = item.get("observations")
                if isinstance(examples, list) and observation_id and observation_id not in examples:
                    examples.append(observation_id)
                source_list = sources_by_id.get(item_id)
                for source in list_string_values(source_list):
                    sources = item.get("sources")
                    if isinstance(sources, list) and source not in sources:
                        sources.append(source)
    return observation_count, counts


def local_evidence_row_lookup(payload: dict[str, object] | None) -> dict[str, dict[str, object]]:
    """Return observation reconstruction rows by observation ID."""
    results = payload.get("results") if isinstance(payload, dict) else None
    rows = results if isinstance(results, list) else []
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        observation_id = str(row.get("observation_id", "") or "").strip()
        if observation_id:
            lookup[observation_id] = row
    return lookup


def observation_payload_lookup(payload: dict[str, object] | None) -> dict[str, dict[str, object]]:
    """Return persisted mushroom observations by observation ID."""
    observations = payload.get("observations") if isinstance(payload, dict) else None
    rows = observations if isinstance(observations, list) else []
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        observation_id = str(row.get("observation_id", "") or row.get("id", "") or "").strip()
        if observation_id:
            lookup[observation_id] = row
    return lookup


def evidence_anchor_id(*parts: object) -> str:
    """Return a stable HTML anchor ID for an evidence modal."""
    raw = "-".join(str(part or "") for part in parts)
    safe = "".join(char if char.isalnum() else "-" for char in raw.lower()).strip("-")
    return safe or "evidence-observations"


def observation_location(row: dict[str, object] | None) -> tuple[float, float] | None:
    """Extract a WGS84 latitude/longitude pair from one observation-like row."""
    if not isinstance(row, dict):
        return None
    location = row.get("location")
    if isinstance(location, dict):
        lat = location.get("lat", location.get("latitude"))
        lon = location.get("lon", location.get("longitude"))
        if isinstance(lat, int | float) and isinstance(lon, int | float):
            return float(lat), float(lon)
    lat = row.get("lat", row.get("latitude"))
    lon = row.get("lon", row.get("longitude"))
    if isinstance(lat, int | float) and isinstance(lon, int | float):
        return float(lat), float(lon)
    return None


def evidence_observation_rows(
    observation_ids: list[str],
    reconstruction_lookup: dict[str, dict[str, object]],
    observation_lookup: dict[str, dict[str, object]],
    catalogs: dict[str, object],
) -> list[dict[str, object]]:
    """Build modal rows that combine reconstruction and persisted observation fields."""
    rows = []
    for observation_id in observation_ids:
        reconstruction_row = reconstruction_lookup.get(observation_id, {})
        observation_row = observation_lookup.get(observation_id, {})
        location = observation_location(reconstruction_row) or observation_location(observation_row)
        flush_abundance = observation_row.get("flush_abundance") or reconstruction_row.get("flush_abundance") or ""
        rows.append(
            {
                "observation_id": observation_id,
                "observed_at": observation_row.get("observed_at") or reconstruction_row.get("observed_at") or "",
                "flush_abundance": flush_abundance,
                "flush_abundance_label": observation_catalog_label(catalogs, "observation_flush_abundance", flush_abundance),
                "analysis_result": observation_row.get("analysis_result") or reconstruction_row.get("analysis_result") or "",
                "location": location,
            }
        )
    return rows


def google_maps_embed_src(lat: float, lon: float, zoom: int = 16) -> str:
    """Return a Google Maps hybrid embed URL for one point."""
    params = urlencode({"q": f"{lat:.7f},{lon:.7f}", "t": "h", "z": str(zoom), "output": "embed"})
    return f"https://maps.google.com/maps?{params}"


def google_maps_external_url(lat: float, lon: float) -> str:
    """Return an external Google Maps URL for one point."""
    params = urlencode({"api": "1", "query": f"{lat:.7f},{lon:.7f}"})
    return f"https://www.google.com/maps/search/?{params}"


def observation_map_modal_id(observation_id: str) -> str:
    """Return a stable map modal ID for one observation."""
    return "observation-map-" + evidence_anchor_id(observation_id)


def observation_photo_modal_id(observation_id: str, media: dict[str, object], index: int) -> str:
    """Return a stable photo modal ID for one observation media entry."""
    token = str(media.get("path") or media.get("stored_filename") or media.get("url") or index)
    return "observation-photo-" + evidence_anchor_id(observation_id, token)


def observation_photo_raw_exif_modal_id(observation_id: str, media: dict[str, object], index: int) -> str:
    """Return a stable raw EXIF modal ID for one observation media entry."""
    token = str(media.get("path") or media.get("stored_filename") or media.get("url") or index)
    return "observation-photo-raw-exif-" + evidence_anchor_id(observation_id, token)


def observation_coordinates_html(row: dict[str, object], *, precision: int = 5) -> str:
    """Render coordinates as a link to the local map modal when available."""
    observation_id = str(row.get("observation_id", "") or "")
    location = observation_location(row)
    if not location:
        return "-"
    lat, lon = location
    coords = f"{lat:.{precision}f}, {lon:.{precision}f}"
    if not observation_id:
        return html.escape(coords)
    return (
        f'<a class="observation-map-link" href="#{html.escape(observation_map_modal_id(observation_id), quote=True)}" '
        'onclick="event.stopPropagation()">'
        f'{html.escape(coords)}</a>'
    )


def observation_photo_media(row: dict[str, object]) -> list[tuple[int, dict[str, object]]]:
    """Return photo media rows with their original media index."""
    media_rows = row.get("media") if isinstance(row.get("media"), list) else []
    photos: list[tuple[int, dict[str, object]]] = []
    for index, media in enumerate(media_rows):
        if not isinstance(media, dict) or str(media.get("kind", "")) != "photo":
            continue
        if not str(media.get("url", "") or ""):
            continue
        photos.append((index, media))
    return photos


def render_observation_photo_strip(
    row: dict[str, object],
    *,
    extra_class: str = "",
    limit: int | None = None,
) -> str:
    """Render linked observation photo thumbnails when media is available."""
    observation_id = str(row.get("observation_id", "") or "")
    photo_links = []
    for index, media in observation_photo_media(row):
        if limit is not None and len(photo_links) >= limit:
            break
        url = str(media.get("url", "") or "")
        label = str(media.get("original_filename", "") or media.get("stored_filename", "") or "photo")
        modal_href = "#" + observation_photo_modal_id(observation_id, media, index)
        photo_links.append(
            '<a class="observation-photo-link" '
            f'href="{html.escape(modal_href, quote=True)}" '
            f'title="{html.escape(label, quote=True)}">'
            f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(label, quote=True)}">'
            "</a>"
        )
    if not photo_links:
        return ""
    classes = "observation-photo-strip"
    if extra_class:
        classes += " " + extra_class
    return f'<div class="{html.escape(classes, quote=True)}">' + "".join(photo_links) + "</div>"


def observation_media_file_path(relative_path: str) -> Path | None:
    """Return a safe local file path for one media path under mushroom-data."""
    path_text = str(relative_path or "").strip().lstrip("/")
    if not path_text or "\x00" in path_text:
        return None
    root = mushroom_paths.mushroom_data_dir().resolve()
    candidate = (root / path_text).resolve()
    if root != candidate and root not in candidate.parents:
        return None
    return candidate


def exif_value_text(value: object) -> str:
    """Return a compact readable representation for EXIF values."""
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8").strip("\x00").strip()
        except UnicodeDecodeError:
            text = ""
        return text if text and all(char.isprintable() for char in text) else f"<{len(value)} bytes>"
    if isinstance(value, (list, tuple)):
        return ", ".join(exif_value_text(item) for item in value)
    text = str(value)
    return text if len(text) <= 240 else text[:237] + "..."


def observation_photo_exif_rows(media: dict[str, object]) -> list[tuple[str, str]]:
    """Read displayable EXIF metadata for one stored observation image."""
    rows: list[tuple[str, str]] = []
    filename = str(media.get("original_filename", "") or media.get("stored_filename", "") or "")
    if filename:
        rows.append(("Archivo original", filename))
    if media.get("size_bytes") not in (None, ""):
        rows.append(("Tamano guardado", f"{media.get('size_bytes')} bytes"))
    if media.get("content_type"):
        rows.append(("Tipo", str(media.get("content_type"))))
    path = observation_media_file_path(str(media.get("path", "") or ""))
    if path is None or not path.exists():
        rows.append(("EXIF", "Imagen no encontrada en disco"))
        return rows
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        with Image.open(path) as image:
            rows.append(("Dimensiones", f"{image.width} x {image.height} px"))
            exif = image.getexif()
            if not exif:
                rows.append(("EXIF", "Sin metadatos EXIF"))
                return rows
            for tag, value in sorted(exif.items(), key=lambda item: str(TAGS.get(item[0], item[0]))):
                label = str(TAGS.get(tag, tag))
                if label == "GPSInfo":
                    continue
                rows.append((label, exif_value_text(value)))
            try:
                gps_ifd = exif.get_ifd(34853)
            except Exception:
                gps_ifd = {}
            if isinstance(gps_ifd, dict):
                for tag, value in sorted(gps_ifd.items(), key=lambda item: str(GPSTAGS.get(item[0], item[0]))):
                    label = "GPS " + str(GPSTAGS.get(tag, tag))
                    rows.append((label, exif_value_text(value)))
    except Exception as exc:
        rows.append(("EXIF", f"No se pudo leer EXIF: {exc}"))
    return rows


def observation_photo_raw_exif_text(media: dict[str, object]) -> str:
    """Read raw EXIF metadata as formatted JSON for a stored observation image."""
    path = observation_media_file_path(str(media.get("path", "") or ""))
    if path is None or not path.exists():
        return json.dumps({"error": "image_not_found", "path": str(media.get("path", "") or "")}, indent=2, ensure_ascii=False)
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        with Image.open(path) as image:
            exif = image.getexif()
            payload: dict[str, object] = {
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "exif": {},
                "gps": {},
            }
            for tag, value in sorted(exif.items(), key=lambda item: str(TAGS.get(item[0], item[0]))):
                label = str(TAGS.get(tag, tag))
                if label == "GPSInfo":
                    continue
                payload["exif"][label] = exif_value_text(value)
            try:
                gps_ifd = exif.get_ifd(34853)
            except Exception:
                gps_ifd = {}
            if isinstance(gps_ifd, dict):
                for tag, value in sorted(gps_ifd.items(), key=lambda item: str(GPSTAGS.get(item[0], item[0]))):
                    payload["gps"][str(GPSTAGS.get(tag, tag))] = exif_value_text(value)
            return json.dumps(payload, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": "exif_read_failed", "message": str(exc)}, indent=2, ensure_ascii=False)


def render_observation_photo_modal(
    row: dict[str, object],
    media: dict[str, object],
    index: int,
) -> str:
    """Render a full-screen photo modal with EXIF data."""
    observation_id = str(row.get("observation_id", "") or "")
    url = str(media.get("url", "") or "")
    if not observation_id or not url:
        return ""
    label = str(media.get("original_filename", "") or media.get("stored_filename", "") or "photo")
    modal_id = observation_photo_modal_id(observation_id, media, index)
    raw_modal_id = observation_photo_raw_exif_modal_id(observation_id, media, index)
    rows = observation_photo_exif_rows(media)
    exif_rows = "".join(
        f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>"
        for key, value in rows
    )
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <div class="modal-card observation-photo-modal">
        <div class="modal-header">
          <div>
            <h2>{html.escape(label)}</h2>
            <p class="meta">{html.escape(observation_id)}</p>
          </div>
          <div class="modal-header-actions">
            <a class="button-link compact-button" href="#{html.escape(raw_modal_id, quote=True)}">Raw EXIF metadata</a>
            <a class="button-link compact-button" href="#" data-modal-history-close>{html.escape(ui_label("ui.close"))}</a>
          </div>
        </div>
        <div class="observation-photo-exif">
          <table><tbody>{exif_rows}</tbody></table>
        </div>
        <div class="observation-photo-stage">
          <img src="{html.escape(url, quote=True)}" alt="{html.escape(label, quote=True)}">
        </div>
      </div>
    </div>
    """


def render_observation_raw_exif_modal(
    row: dict[str, object],
    media: dict[str, object],
    index: int,
) -> str:
    """Render a modal with raw EXIF metadata for one observation photo."""
    observation_id = str(row.get("observation_id", "") or "")
    if not observation_id:
        return ""
    label = str(media.get("original_filename", "") or media.get("stored_filename", "") or "photo")
    modal_id = observation_photo_raw_exif_modal_id(observation_id, media, index)
    raw_text = observation_photo_raw_exif_text(media)
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <div class="modal-card observation-raw-exif-modal">
        <div class="modal-header">
          <div>
            <h2>Raw EXIF metadata</h2>
            <p class="meta">{html.escape(label)} · {html.escape(observation_id)}</p>
          </div>
          <a class="button-link compact-button" href="#" data-modal-history-close>{html.escape(ui_label("ui.close"))}</a>
        </div>
        <pre>{html.escape(raw_text)}</pre>
      </div>
    </div>
    """


def render_observation_map_modal(
    row: dict[str, object],
    selected_species_id: str = "",
    search: str = "",
    filters: dict[str, str] | None = None,
) -> str:
    """Render the shared observation map modal used by observation list/detail/edit views."""
    observation_id = str(row.get("observation_id", "") or "")
    location = observation_location(row)
    if not observation_id or not location:
        return ""
    lat, lon = location
    modal_id = observation_map_modal_id(observation_id)
    close_href = observation_select_url(selected_species_id, search, filters, observation_id)
    map_rows = [{"observation_id": observation_id, "location": (lat, lon)}]
    photo_html = render_observation_photo_strip(row, extra_class="observation-map-photo-strip", limit=1)
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <div class="modal-card evidence-map-modal">
        <div class="modal-header">
          <div>
            <h2>{html.escape(ui_label("ui.evidence_map"))}</h2>
            <p class="meta">{html.escape(observation_id)} · {html.escape(f"{lat:.6f}, {lon:.6f}")}</p>
          </div>
          {photo_html}
          <a class="button-link compact-button" href="{html.escape(close_href, quote=True)}" data-modal-history-close>{html.escape(ui_label("ui.close"))}</a>
        </div>
        {render_evidence_observation_map(map_rows, modal_id)}
      </div>
    </div>
    """


def render_evidence_observation_map(rows: list[dict[str, object]], map_id: str) -> str:
    """Render a Google Maps hybrid iframe for the observations listed in one evidence modal."""
    located = [
        (index, row, row.get("location"))
        for index, row in enumerate(rows, start=1)
        if isinstance(row.get("location"), tuple)
    ]
    if not located:
        return f'<div class="evidence-map-empty">{html.escape(ui_label("ui.evidence_no_coordinates"))}</div>'
    _, first_row, first_location = located[0]
    lat, lon = float(first_location[0]), float(first_location[1])
    external_href = google_maps_external_url(lat, lon)
    return f"""
    <div class="evidence-map-viewport">
      <iframe
        class="evidence-google-map"
        data-evidence-map-frame="{html.escape(map_id, quote=True)}"
        src="{html.escape(google_maps_embed_src(lat, lon), quote=True)}"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
        title="{html.escape(ui_label("ui.evidence_map"), quote=True)}"></iframe>
      <div class="evidence-map-toolbar">
        <span>{html.escape(str(first_row.get("observation_id", "") or ""))}</span>
        <a class="button-link compact-button" data-evidence-map-external="{html.escape(map_id, quote=True)}" href="{html.escape(external_href, quote=True)}" target="_blank" rel="noopener">{html.escape(ui_label("ui.evidence_open_google_maps"))}</a>
      </div>
    </div>
    """


def render_evidence_observation_modal(
    modal_id: str,
    species_id: str,
    search: str,
    profile_view: str,
    evidence_view: str,
    item_label: str,
    rows: list[dict[str, object]],
) -> str:
    """Render a modal with observation rows and a zoomable local map."""
    close_href = profile_query_url(
        species_id,
        search,
        section="evidence",
        profile_view=profile_view,
        evidence_view=evidence_view,
    )
    list_rows = []
    for index, row in enumerate(rows, start=1):
        observation_id = str(row.get("observation_id", "") or "")
        location = row.get("location")
        if isinstance(location, tuple):
            coords = f"{location[0]:.6f}, {location[1]:.6f}"
            map_button = (
                f'<button class="evidence-map-select-button" type="button" '
                f'data-evidence-map-target="{html.escape(modal_id, quote=True)}" '
                f'data-map-label="{html.escape(observation_id, quote=True)}" '
                f'data-map-src="{html.escape(google_maps_embed_src(float(location[0]), float(location[1])), quote=True)}" '
                f'data-map-external="{html.escape(google_maps_external_url(float(location[0]), float(location[1])), quote=True)}">'
                f'{html.escape(ui_label("ui.evidence_show_on_map"))}</button>'
            )
        else:
            coords = ui_label("ui.evidence_no_coordinates")
            map_button = ""
        open_href = observation_select_url(species_id, search, None, observation_id)
        list_rows.append(
            '<li class="evidence-observation-item">'
            f'<span class="evidence-observation-index">{index}</span>'
            f'<strong class="evidence-observation-date">{html.escape(str(row.get("observed_at", "") or "-"))}</strong>'
            '<span class="evidence-observation-main">'
            f'<strong>{html.escape(observation_id)}</strong>'
            f'<span class="meta">{html.escape(str(row.get("flush_abundance_label", "") or row.get("flush_abundance", "") or "-"))} · {html.escape(str(row.get("analysis_result", "") or "-"))}</span>'
            "</span>"
            f'<span class="evidence-observation-coords">{html.escape(coords)}</span>'
            f'{map_button}'
            f'<a class="evidence-map-select-button" href="{html.escape(open_href, quote=True)}">{html.escape(ui_label("ui.open"))}</a>'
            "</li>"
        )
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <div class="modal-card evidence-map-modal">
        <div class="modal-header">
          <div>
            <h2>{html.escape(ui_label("ui.evidence_observations_modal_title"))}</h2>
            <p class="meta">{html.escape(item_label)} · {len(rows)} {html.escape(ui_label("ui.evidence_observations_short"))}</p>
          </div>
          <a class="button-link compact-button" href="{html.escape(close_href, quote=True)}">{html.escape(ui_label("ui.close"))}</a>
        </div>
        <p class="meta">{html.escape(ui_label("ui.evidence_observations_modal_help"))}</p>
        <div class="evidence-observation-layout">
          <section>
            <h3>{html.escape(ui_label("ui.evidence_observation_list"))}</h3>
            <ol class="evidence-observation-list">{"".join(list_rows)}</ol>
          </section>
          <section>
            <h3>{html.escape(ui_label("ui.evidence_map"))}</h3>
            {render_evidence_observation_map(rows, modal_id)}
          </section>
        </div>
      </div>
    </div>
    """


def local_evidence_status(declared: bool, observed_count: int, observation_count: int) -> tuple[str, str]:
    """Return display status for one profile-vs-observation evidence row."""
    if declared and observed_count:
        return ui_label("ui.evidence_declared_observed"), "ok"
    if not declared and observed_count:
        return ui_label("ui.evidence_observed_not_declared"), "warn"
    if declared and observation_count:
        return ui_label("ui.evidence_declared_not_observed"), "muted"
    return ui_label("ui.evidence_no_local_evidence"), "muted"


def local_evidence_status_help(declared: bool, observed_count: int, observation_count: int) -> str:
    """Return contextual help for one profile-vs-observation evidence value."""
    if declared and observed_count:
        return ui_label("ui.evidence_status_declared_observed_help")
    if not declared and observed_count:
        return ui_label("ui.evidence_status_observed_not_declared_help")
    if declared and observation_count:
        return ui_label("ui.evidence_status_declared_not_observed_help")
    return ui_label("ui.evidence_status_no_local_evidence_help")


def local_evidence_decision_lookup(decisions_payload: dict[str, object] | None) -> dict[tuple[str, str, str], str]:
    """Return local evidence decisions indexed by species, group and item ID."""
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload, dict) else None
    rows = decisions if isinstance(decisions, list) else []
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        species_id = str(row.get("species_id", "") or "")
        group = str(row.get("group", "") or "")
        item_id = str(row.get("item_id", "") or "")
        decision = str(row.get("decision", "") or "")
        if species_id and group and item_id and decision and decision != "unreviewed":
            lookup[(species_id, group, item_id)] = decision
    return lookup


def local_evidence_decision_label(decision: str) -> str:
    labels = {
        "promote": ui_label("ui.evidence_decision_promote"),
        "ignore": ui_label("ui.evidence_decision_ignore"),
        "keep": ui_label("ui.evidence_decision_keep"),
        "doubtful": ui_label("ui.evidence_decision_doubtful"),
    }
    return labels.get(decision, ui_label("ui.evidence_decision_none"))


def local_evidence_decision_help(decision: str) -> str:
    """Return contextual help for one manual evidence decision."""
    labels = {
        "promote": ui_label("ui.evidence_decision_promote_help"),
        "ignore": ui_label("ui.evidence_decision_ignore_help"),
        "keep": ui_label("ui.evidence_decision_keep_help"),
        "doubtful": ui_label("ui.evidence_decision_doubtful_help"),
    }
    return labels.get(decision, ui_label("ui.evidence_decision_none_help"))


def evidence_decision_button(
    species_id: str,
    group_key: str,
    item_id: str,
    decision: str,
    label: str,
    current_decision: str,
) -> str:
    """Render one reversible evidence decision button."""
    active = " active" if decision == current_decision else ""
    confirm = f"Guardar decision de evidencia: {label} para {item_id}?"
    return (
        '<button class="evidence-action-button'
        f'{active}" name="evidence_decision" value="{html.escape(decision, quote=True)}" '
        f'title="{html.escape(local_evidence_decision_help(decision), quote=True)}" '
        f'type="submit" onclick="return confirm(\'{html.escape(confirm, quote=True)}\')">'
        f'{html.escape(label)}</button>'
    )


def render_local_evidence_group(
    title: str,
    group_key: str,
    catalog_group: str,
    species_id: str,
    declared_ids: list[str],
    observed_items: dict[str, dict[str, object]],
    observation_count: int,
    catalogs: dict[str, object],
    decisions: dict[tuple[str, str, str], str],
    reconstruction_lookup: dict[str, dict[str, object]] | None = None,
    observation_lookup: dict[str, dict[str, object]] | None = None,
    search: str = "",
    profile_view: str = "enriched",
    evidence_view: str = "hosts_forests",
) -> str:
    """Render one group of observed/declared local v0 evidence."""
    if catalog_group == "host_taxa":
        catalog_items = catalogs.get(catalog_group)
        catalog_items = catalog_items if isinstance(catalog_items, list) else []
        labels = {
            str(item.get("id", "") or ""): host_scientific_common_label(item)
            for item in catalog_items
            if isinstance(item, dict) and str(item.get("id", "") or "")
        }
    else:
        labels = catalog_label_map(catalogs, catalog_group)
    all_ids = sorted(set(declared_ids) | set(observed_items), key=lambda item: labels.get(item, item))
    if not all_ids:
        return f"""
        <article class="profile-section-card evidence-group">
          <h3>{html.escape(title)}</h3>
          <p class="meta">No hay valores declarados ni observados para este grupo.</p>
        </article>
        """
    rows = []
    modals = []
    reconstruction_lookup = reconstruction_lookup or {}
    observation_lookup = observation_lookup or {}
    for item_id in all_ids:
        observed = observed_items.get(item_id, {})
        count = int(observed.get("count", 0) or 0)
        observation_ids = [
            str(value)
            for value in observed.get("observations", [])
            if str(value or "").strip()
        ] if isinstance(observed.get("observations"), list) else []
        declared = item_id in declared_ids
        status, tone = local_evidence_status(declared, count, observation_count)
        current_decision = decisions.get((species_id, group_key, item_id), "")
        primary_actions = (
            [
                ("promote", ui_label("ui.evidence_decision_promote")),
                ("ignore", ui_label("ui.evidence_decision_ignore")),
            ]
            if count and not declared else
            [
                ("keep", ui_label("ui.evidence_decision_keep")),
                ("doubtful", ui_label("ui.evidence_decision_doubtful")),
            ]
            if declared and observation_count and not count else
            [
                ("keep", ui_label("ui.evidence_decision_confirm")),
            ]
            if declared and count else
            []
        )
        action_buttons = "".join(
            evidence_decision_button(species_id, group_key, item_id, decision, label, current_decision)
            for decision, label in primary_actions
        )
        reset_button = (
            evidence_decision_button(species_id, group_key, item_id, "unreviewed", ui_label("ui.evidence_decision_reset"), current_decision)
            if current_decision else ""
        )
        profile_help = (
            ui_label("ui.evidence_profile_value_declared_help")
            if declared else
            ui_label("ui.evidence_profile_value_not_declared_help")
        )
        observations_help = f"{count}. {ui_label('ui.evidence_observations_value_help')}"
        observations_cell = html.escape(str(count))
        sources = [
            learned_source_label(source)
            for source in list_string_values(observed.get("sources"))
        ]
        sources_text = ", ".join(sources)
        if count and observation_ids:
            modal_id = evidence_anchor_id("evidence-observations", group_key, item_id)
            item_label = labels.get(item_id, item_id)
            modal_rows = evidence_observation_rows(observation_ids, reconstruction_lookup, observation_lookup, catalogs)
            observations_cell = (
                f'<a class="evidence-observation-link" href="#{html.escape(modal_id, quote=True)}" '
                f'title="{html.escape(ui_label("ui.evidence_view_observations"), quote=True)}">'
                f'{count}</a>'
            )
            modals.append(
                render_evidence_observation_modal(
                    modal_id,
                    species_id,
                    search,
                    profile_view,
                    evidence_view,
                    item_label,
                    modal_rows,
                )
            )
        if count and sources_text:
            observations_cell += f'<span class="meta">{html.escape(sources_text)}</span>'
        status_help = local_evidence_status_help(declared, count, observation_count)
        decision_help = local_evidence_decision_help(current_decision)
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(labels.get(item_id, item_id))}</strong><span class=\"meta\">{html.escape(item_id)}</span></td>"
            f'<td title="{html.escape(profile_help, quote=True)}">{html.escape(ui_label("ui.yes") if declared else ui_label("ui.no"))}</td>'
            f'<td title="{html.escape(observations_help, quote=True)}">{observations_cell}</td>'
            f'<td><span class="evidence-status {html.escape(tone)}" title="{html.escape(status_help, quote=True)}">{html.escape(status)}</span></td>'
            f'<td><span class="evidence-decision" title="{html.escape(decision_help, quote=True)}">{html.escape(local_evidence_decision_label(current_decision))}</span></td>'
            f'<td title="{html.escape(ui_label("ui.evidence_actions_help"), quote=True)}"><form method="post" class="evidence-action-form">'
            '<input type="hidden" name="profile_action" value="update_evidence_decision">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">'
            f'<input type="hidden" name="evidence_view" value="{html.escape(evidence_view, quote=True)}">'
            f'<input type="hidden" name="evidence_group" value="{html.escape(group_key, quote=True)}">'
            f'<input type="hidden" name="evidence_item_id" value="{html.escape(item_id, quote=True)}">'
            f'{action_buttons}{reset_button}</form></td>'
            "</tr>"
        )
    header = (
        "<thead><tr>"
        "<th>ID</th>"
        f'<th title="{html.escape(ui_label("ui.evidence_profile_v0_help"), quote=True)}">{html.escape(ui_label("ui.evidence_profile_v0"))}</th>'
        f'<th title="{html.escape(ui_label("ui.evidence_observations_help"), quote=True)}">Obs.</th>'
        f'<th title="{html.escape(ui_label("ui.evidence_status_help"), quote=True)}">{html.escape(ui_label("ui.evidence_status"))}</th>'
        f'<th title="{html.escape(ui_label("ui.evidence_decision_help"), quote=True)}">{html.escape(ui_label("ui.evidence_decision"))}</th>'
        f'<th title="{html.escape(ui_label("ui.evidence_actions_help"), quote=True)}">{html.escape(ui_label("ui.evidence_actions"))}</th>'
        "</tr></thead>"
    )
    return f"""
    <article class="profile-section-card evidence-group">
      <h3>{html.escape(title)}</h3>
      <div class="evidence-table-shell local-evidence-table">
        <table>
          {header}
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      {''.join(modals)}
    </article>
    """


def numeric_values(rows: list[dict[str, object]], key: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def numeric_range_label(rows: list[dict[str, object]], key: str, unit: str = "") -> str:
    values = numeric_values(rows, key)
    if not values:
        return "-"
    low = min(values)
    high = max(values)
    suffix = f" {unit}" if unit else ""
    if low == high:
        return f"{low:g}{suffix}"
    return f"{low:g}-{high:g}{suffix}"


def numeric_range_label_first(rows: list[dict[str, object]], keys: tuple[str, ...], unit: str = "") -> str:
    """Return a range using the first available numeric key per row."""
    values = []
    for row in rows:
        for key in keys:
            value = row.get(key)
            if isinstance(value, int | float):
                values.append(float(value))
                break
    if not values:
        return "-"
    suffix = f" {unit}" if unit else ""
    low = min(values)
    high = max(values)
    if low == high:
        return f"{low:g}{suffix}"
    return f"{low:g}-{high:g}{suffix}"


def weather_number_label(value: object, decimals: int, unit: str = "") -> str:
    if value is None:
        return "-"
    suffix = f" {unit}" if unit else ""
    if isinstance(value, int | float):
        return f"{value:.{decimals}f}{suffix}"
    return f"{value}{suffix}"


def weather_cell(row: dict[str, object], key: str, fallback_key: str = "", unit: str = "", decimals: int = 0) -> str:
    value = row.get(key)
    if value is None and fallback_key:
        value = row.get(fallback_key)
    return html.escape(weather_number_label(value, decimals, unit))


def weather_metric_header(unit: str, period: str) -> str:
    return (
        '<th class="weather-metric-heading">'
        f'<span>{html.escape(unit)}</span>'
        f'<em>{html.escape(period)}</em>'
        '</th>'
    )


def temperature_window_label(row: dict[str, object], days: int) -> str:
    min_key = f"temp_min_{days}d_c"
    max_key = f"temp_max_{days}d_c"
    min_value = row.get(min_key)
    max_value = row.get(max_key)
    if days == 7:
        min_value = min_value if min_value is not None else row.get("temp_min_c")
        max_value = max_value if max_value is not None else row.get("temp_max_c")
    if min_value is None and max_value is None:
        return "-"
    return f"{weather_number_label(min_value, 1)} / {weather_number_label(max_value, 1)}"


def humidity_window_label(row: dict[str, object], days: int) -> str:
    min_key = f"humidity_min_{days}d_pct"
    max_key = f"humidity_max_{days}d_pct"
    min_value = row.get(min_key)
    max_value = row.get(max_key)
    if days == 7:
        min_value = min_value if min_value is not None else row.get("humidity_min_pct")
        max_value = max_value if max_value is not None else row.get("humidity_max_pct")
    if min_value is None and max_value is None:
        return "-"
    return f"{weather_number_label(min_value, 1)} / {weather_number_label(max_value, 1)}"


def compact_gap_label(gaps: object, limit: int = 2) -> str:
    values = weather_gap_values(gaps)
    if not values:
        return "-"
    suffix = f" +{len(values) - limit}" if len(values) > limit else ""
    return ", ".join(values[:limit]) + suffix


def weather_gap_values(gaps: object) -> list[str]:
    return [str(value) for value in gaps if str(value or "").strip()] if isinstance(gaps, list) else []


def weather_gap_description(gap: str) -> str:
    rain_coverage = re.fullmatch(r"rain_(\d+)d_coverage_(\d+)/(\d+)", gap)
    if rain_coverage:
        window_days, available_days, expected_days = rain_coverage.groups()
        return (
            f"Acumulado de lluvia de {window_days} dias calculado con "
            f"{available_days} dias validos de {expected_days} ({gap})."
        )
    rain_suspect = re.fullmatch(r"rain_suspect_daily_(\d{8})_(.+)", gap)
    if rain_suspect:
        raw_day, value = rain_suspect.groups()
        day_label = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:8]}"
        return f"Lluvia diaria sospechosa excluida del acumulado ({day_label}: {value}; {gap})."
    temperature_missing = re.fullmatch(r"temperature_no_data_(\d+)d", gap)
    if temperature_missing:
        return f"Sin datos de temperatura en la ventana de {temperature_missing.group(1)} dias ({gap})."
    humidity_missing = re.fullmatch(r"humidity_no_data_(\d+)d", gap)
    if humidity_missing:
        return f"Sin datos de humedad en la ventana de {humidity_missing.group(1)} dias ({gap})."
    if gap == "wind_no_data_7d":
        return "La estacion elegida no tiene datos de viento en la ventana de 7 dias (wind_no_data_7d)."
    if gap == "no_weather_station_with_90d_coverage":
        return "No se encontro estacion meteorologica con datos en los 90 dias previos (no_weather_station_with_90d_coverage)."
    if gap == "invalid_observed_at":
        return "Fecha de observacion no valida (invalid_observed_at)."
    if gap == "missing_coordinates":
        return "Faltan coordenadas para buscar estacion meteorologica (missing_coordinates)."
    return f"Incidencia meteorologica sin descripcion especifica ({gap})."


def weather_gap_tooltip(gaps: object) -> str:
    values = weather_gap_values(gaps)
    if not values:
        return ""
    return "\n".join(weather_gap_description(value) for value in values)


def render_weather_gap_cell(gaps: object) -> str:
    label = compact_gap_label(gaps)
    tooltip = weather_gap_tooltip(gaps)
    if not tooltip:
        return '<td><span class="meta">-</span></td>'
    return (
        '<td><span class="meta weather-gap-help" '
        f'title="{html.escape(tooltip, quote=True)}">{html.escape(label)}</span></td>'
    )


def ratio_label(value: object) -> str:
    if isinstance(value, int | float):
        return f"{value * 100:.0f}%"
    return "-"


def model_number_label(value: object, unit: str = "") -> str:
    if isinstance(value, int | float):
        suffix = f" {unit}" if unit else ""
        return f"{value:g}{suffix}"
    return "-"


def learned_model_for_species(payload: dict[str, object] | None, species_id: str) -> dict[str, object] | None:
    models = payload.get("species_models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return None
    for model in models:
        if isinstance(model, dict) and str(model.get("species_id", "") or "") == species_id:
            return model
    return None


FIELD_OBSERVATION_FEATURES = (
    ("observed_host_ids", "hosts"),
    ("observed_forest_type_ids", "forests"),
    ("observed_soil_tendency_ids", "soils"),
    ("observed_habitat_feature_ids", "habitat"),
    ("observed_aspect_ids", "aspects"),
)


def observation_is_training_row(row: dict[str, object]) -> bool:
    return (
        str(row.get("validation_status", "") or "").strip() == "valid"
        and str(row.get("calibration_use", "") or "").strip() == "include"
    )


def observation_is_positive(row: dict[str, object]) -> bool:
    result = str(row.get("analysis_result", "") or "").strip()
    abundance = str(row.get("flush_abundance", "") or "").strip()
    return result != "absent" and abundance != "absent"


def list_string_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def field_evidence_model_from_observations(
    observations_payload: dict[str, object] | None,
    species_id: str,
) -> dict[str, object] | None:
    """Build live field-source evidence directly from persisted observations."""
    rows = [
        row for row in observations_from_payload(observations_payload)
        if str(row.get("species_id", "") or "").strip() == species_id and observation_is_training_row(row)
    ]
    if not rows:
        return None
    positive_rows = [row for row in rows if observation_is_positive(row)]
    negative_rows = [row for row in rows if not observation_is_positive(row)]
    categorical: dict[str, list[dict[str, object]]] = {}
    for observed_key, output_key in FIELD_OBSERVATION_FEATURES:
        positive_by_id: dict[str, set[str]] = {}
        negative_by_id: dict[str, set[str]] = {}
        for row in rows:
            site_context = row.get("site_context") if isinstance(row.get("site_context"), dict) else {}
            observation_id = str(row.get("observation_id", "") or "").strip()
            if not observation_id:
                continue
            target = positive_by_id if observation_is_positive(row) else negative_by_id
            for item_id in list_string_values(site_context.get(observed_key)):
                target.setdefault(item_id, set()).add(observation_id)
        item_ids = sorted(set(positive_by_id) | set(negative_by_id))
        items = []
        for item_id in item_ids:
            positive_ids = sorted(positive_by_id.get(item_id, set()))
            negative_ids = sorted(negative_by_id.get(item_id, set()))
            items.append(
                {
                    "id": item_id,
                    "positive_support": len(positive_ids),
                    "negative_support": len(negative_ids),
                    "positive_ratio": round(len(positive_ids) / len(positive_rows), 4) if positive_rows else None,
                    "negative_ratio": round(len(negative_ids) / len(negative_rows), 4) if negative_rows else None,
                    "positive_sources": ["field"] if positive_ids else [],
                    "negative_sources": ["field"] if negative_ids else [],
                    "positive_source_support": {"field": len(positive_ids)} if positive_ids else {},
                    "negative_source_support": {"field": len(negative_ids)} if negative_ids else {},
                    "positive_observations": positive_ids,
                    "negative_observations": negative_ids,
                }
            )
        categorical[output_key] = items
    return {
        "schema_version": "0.1",
        "kind": "mushroom_live_field_evidence_v0",
        "species_id": species_id,
        "observation_count": len(rows),
        "positive_count": len(positive_rows),
        "negative_count": len(negative_rows),
        "categorical_features": categorical,
        "numeric_features": {},
    }


def strip_field_source(item: dict[str, object]) -> dict[str, object]:
    cleaned = dict(item)
    for key in ("positive_sources", "negative_sources"):
        values = cleaned.get(key)
        cleaned[key] = [source for source in values if source != "field"] if isinstance(values, list) else []
    for key in ("positive_source_support", "negative_source_support"):
        support = dict(cleaned.get(key)) if isinstance(cleaned.get(key), dict) else {}
        support.pop("field", None)
        cleaned[key] = support
    if not cleaned.get("positive_sources") and not cleaned.get("positive_source_support"):
        cleaned["positive_support"] = 0
        cleaned["positive_ratio"] = None
    if not cleaned.get("negative_sources") and not cleaned.get("negative_source_support"):
        cleaned["negative_support"] = 0
        cleaned["negative_ratio"] = None
    return cleaned


def merge_source_lists(left: object, right: object) -> list[str]:
    values = []
    for source in list_string_values(left) + list_string_values(right):
        if source not in values:
            values.append(source)
    return values


def merge_field_item(base: dict[str, object] | None, field: dict[str, object]) -> dict[str, object]:
    merged = strip_field_source(base or {})
    merged["id"] = str(field.get("id", "") or merged.get("id", ""))
    for polarity in ("positive", "negative"):
        observations_key = f"{polarity}_observations"
        support_key = f"{polarity}_support"
        ratio_key = f"{polarity}_ratio"
        sources_key = f"{polarity}_sources"
        source_support_key = f"{polarity}_source_support"
        observations = sorted(set(list_string_values(merged.get(observations_key))) | set(list_string_values(field.get(observations_key))))
        merged[observations_key] = observations
        source_support = dict(merged.get(source_support_key)) if isinstance(merged.get(source_support_key), dict) else {}
        field_support = field.get(source_support_key)
        if isinstance(field_support, dict):
            source_support.update(field_support)
        merged[source_support_key] = source_support
        merged[sources_key] = merge_source_lists(merged.get(sources_key), field.get(sources_key))
        merged[support_key] = max(int(merged.get(support_key, 0) or 0), int(field.get(support_key, 0) or 0), len(observations))
        merged[ratio_key] = field.get(ratio_key) if field.get(ratio_key) is not None else merged.get(ratio_key)
    return merged


def merge_live_field_model(
    learned_model: dict[str, object] | None,
    field_model: dict[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(learned_model, dict) and not isinstance(field_model, dict):
        return None
    if not isinstance(field_model, dict):
        return learned_model
    merged = dict(learned_model) if isinstance(learned_model, dict) else {}
    merged["observation_count"] = max(int(merged.get("observation_count", 0) or 0), int(field_model.get("observation_count", 0) or 0))
    merged["positive_count"] = max(int(merged.get("positive_count", 0) or 0), int(field_model.get("positive_count", 0) or 0))
    merged["negative_count"] = max(int(merged.get("negative_count", 0) or 0), int(field_model.get("negative_count", 0) or 0))
    base_categorical = merged.get("categorical_features") if isinstance(merged.get("categorical_features"), dict) else {}
    field_categorical = field_model.get("categorical_features") if isinstance(field_model.get("categorical_features"), dict) else {}
    categorical: dict[str, list[dict[str, object]]] = {}
    for key in sorted(set(base_categorical) | set(field_categorical)):
        base_items = base_categorical.get(key) if isinstance(base_categorical, dict) else []
        field_items = field_categorical.get(key) if isinstance(field_categorical, dict) else []
        by_id = {
            str(item.get("id", "") or ""): strip_field_source(item)
            for item in base_items
            if isinstance(item, dict) and str(item.get("id", "") or "")
        } if isinstance(base_items, list) else {}
        if isinstance(field_items, list):
            for item in field_items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id", "") or "")
                if not item_id:
                    continue
                by_id[item_id] = merge_field_item(by_id.get(item_id), item)
        categorical[key] = [
            item for item in by_id.values()
            if int(item.get("positive_support", 0) or 0) > 0 or int(item.get("negative_support", 0) or 0) > 0
        ]
    merged["categorical_features"] = categorical
    return merged


def active_affinity_ids(ecology: dict[str, object], key: str, profile_view: str = "enriched") -> set[str]:
    """Return affinity IDs visible in the active profile view."""
    raw_items = ecology.get(key)
    items = raw_items if isinstance(raw_items, list) else []
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if is_v0_view(profile_view) and item.get("v0_active") is False:
            continue
        item_id = str(item.get("id", "") or "").strip()
        if item_id:
            ids.add(item_id)
    return ids


def learned_positive_items(model: dict[str, object] | None, key: str) -> list[dict[str, object]]:
    """Return learned categorical rows with positive support."""
    categorical = model.get("categorical_features") if isinstance(model, dict) else None
    items = categorical.get(key) if isinstance(categorical, dict) else None
    if not isinstance(items, list):
        return []
    return [
        item for item in items
        if isinstance(item, dict) and isinstance(item.get("positive_support"), int) and item.get("positive_support", 0) > 0
    ]


def learned_source_label(source: object) -> str:
    key = str(source or "").strip()
    labels = {
        "field": ui_label("ui.source_field"),
        "gis": ui_label("ui.source_gis_dem"),
        "dem": ui_label("ui.source_gis_dem"),
        "v0": ui_label("ui.source_v0"),
    }
    return labels.get(key, key or ui_label("ui.source_v0"))


def learned_source_badges(item: dict[str, object], source_key: str = "positive_sources") -> str:
    values = item.get(source_key)
    sources = [str(value) for value in values if str(value or "").strip()] if isinstance(values, list) else []
    if not sources:
        sources = ["v0"]
    return "".join(
        f'<em class="parameter-source-badge source-{html.escape(css_token(source), quote=True)}">{html.escape(learned_source_label(source))}</em>'
        for source in sources
    )


def learned_item_chip(item: dict[str, object], labels: dict[str, str]) -> str:
    """Render a compact learned-model support chip."""
    item_id = str(item.get("id", "") or "")
    label = labels.get(item_id, item_id)
    support = item.get("positive_support", 0)
    ratio = ratio_label(item.get("positive_ratio"))
    return (
        '<span class="parameter-learned-chip">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(str(support))}</strong>'
        f'<em>{html.escape(ratio)}</em>'
        f'{learned_source_badges(item)}'
        '</span>'
    )


def learned_parameter_comparison_row(
    title: str,
    configured_ids: set[str],
    learned_items: list[dict[str, object]],
    labels: dict[str, str],
    section_class: str = "",
    value_mode: str = "matches",
) -> str:
    """Render one compact comparison row between profile values and learned evidence."""
    observed_ids = {str(item.get("id", "") or "") for item in learned_items}
    configured_observed = configured_ids & observed_ids
    matching_items = [item for item in learned_items if str(item.get("id", "") or "") in configured_observed]
    emerging_items = [item for item in learned_items if str(item.get("id", "") or "") not in configured_ids]
    observed_label = f"{len(configured_observed)}/{len(configured_ids)}" if configured_ids else "0/0"
    if value_mode == "emerging":
        visible_items = emerging_items
        meta_label = ui_label("ui.emerging_outside_profile")
        meta_value = str(len(emerging_items))
    else:
        visible_items = matching_items
        meta_label = ui_label("ui.profile_overlap")
        meta_value = observed_label
    values_html = (
        "".join(learned_item_chip(item, labels) for item in visible_items[:4])
        if visible_items else
        f'<span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span>'
    )
    css_class = f"parameter-comparison-section parameter-learned-row {section_class}".strip()
    return f"""
      <div class="{html.escape(css_class, quote=True)}">
        <div>
          <h4>{html.escape(title)}</h4>
          <span class="meta">{html.escape(meta_label)}: {html.escape(meta_value)}</span>
        </div>
        <div class="parameter-learned-values">{values_html}</div>
      </div>
    """


def render_habitat_learned_comparison(
    model: dict[str, object] | None,
    ecology: dict[str, object],
    catalogs: dict[str, object],
    profile_view: str = "enriched",
    value_mode: str = "matches",
) -> str:
    """Render learned-model context beside habitat parameters."""
    title_label = "ui.learned_emerging_values" if value_mode == "emerging" else "ui.learned_observational_evidence"
    if not isinstance(model, dict):
        return f"""
        <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-ecology-learned">
          <h3>{html.escape(ui_label(title_label))}</h3>
          <p class="meta">{html.escape(ui_label("ui.learned_model_missing"))}</p>
        </aside>
        """
    host_labels = {
        str(item.get("id", "") or ""): host_scientific_common_label(item)
        for item in catalogs.get("host_taxa", [])
        if isinstance(item, dict) and str(item.get("id", "") or "")
    }
    rows = [
        learned_parameter_comparison_row(
            ui_label("ui.primary_hosts"),
            active_affinity_ids(ecology, "host_affinities", profile_view),
            learned_positive_items(model, "hosts"),
            host_labels,
            "parameter-section-hosts",
            value_mode,
        ),
        learned_parameter_comparison_row(
            ui_label("ui.forest_types"),
            active_affinity_ids(ecology, "forest_type_affinities", profile_view),
            learned_positive_items(model, "forests"),
            catalog_label_map(catalogs, "forest_types"),
            "parameter-section-forests",
            value_mode,
        ),
        learned_parameter_comparison_row(
            ui_label("ui.habitat_features"),
            active_affinity_ids(ecology, "habitat_feature_affinities", profile_view),
            learned_positive_items(model, "habitat"),
            catalog_label_map(catalogs, "habitat_features"),
            "parameter-section-habitat",
            value_mode,
        ),
    ]
    return f"""
      <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-ecology-learned">
        <h3>{html.escape(ui_label(title_label))}</h3>
        <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
          <h4>{html.escape(ui_label("ui.observations"))}</h4>
          <div class="parameter-learned-metrics">
            <span>{html.escape(ui_label("ui.total_observations_used"))}: <strong>{html.escape(str(model.get("observation_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.positive_observations"))}: <strong>{html.escape(str(model.get("positive_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.negative_observations"))}: <strong>{html.escape(str(model.get("negative_count", 0) or 0))}</strong></span>
          </div>
        </div>
        <div class="parameter-learned-rows">{"".join(rows)}</div>
      </aside>
    """


def render_soils_learned_comparison(
    model: dict[str, object] | None,
    ecology: dict[str, object],
    catalogs: dict[str, object],
    profile_view: str = "enriched",
    value_mode: str = "matches",
) -> str:
    """Render learned-model context beside soil parameters."""
    title_label = "ui.learned_emerging_values" if value_mode == "emerging" else "ui.learned_observational_evidence"
    if not isinstance(model, dict):
        return f"""
        <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-soils-column">
          <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
            <h3>{html.escape(ui_label(title_label))}</h3>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.soils"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
          <p class="meta parameter-pending-note">{html.escape(ui_label("ui.learned_model_missing"))}</p>
        </aside>
        """
    row = learned_parameter_comparison_row(
        ui_label("ui.soils"),
        active_affinity_ids(ecology, "soil_affinities", profile_view),
        learned_positive_items(model, "soils"),
        catalog_label_map(catalogs, "soil_types"),
        value_mode=value_mode,
    )
    return f"""
      <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-soils-column">
        <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
          <h3>{html.escape(ui_label(title_label))}</h3>
          <div class="parameter-learned-metrics">
            <span>{html.escape(ui_label("ui.total_observations_used"))}: <strong>{html.escape(str(model.get("observation_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.positive_observations"))}: <strong>{html.escape(str(model.get("positive_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.negative_observations"))}: <strong>{html.escape(str(model.get("negative_count", 0) or 0))}</strong></span>
          </div>
        </div>
        <div class="parameter-learned-rows">{row}</div>
      </aside>
    """


def learned_numeric_positive(model: dict[str, object] | None, key: str) -> dict[str, object]:
    """Return the positive numeric summary for a learned feature."""
    numeric = model.get("numeric_features") if isinstance(model, dict) else None
    feature = numeric.get(key) if isinstance(numeric, dict) else None
    positive = feature.get("positive") if isinstance(feature, dict) else None
    return positive if isinstance(positive, dict) else {}


def phenology_evidence_from_observations(
    observations_payload: dict[str, object] | None,
    species_id: str,
) -> dict[str, object] | None:
    """Build month/season evidence directly from eligible observations."""
    rows = [
        row for row in observations_from_payload(observations_payload)
        if str(row.get("species_id", "") or "").strip() == species_id and observation_is_training_row(row)
    ]
    if not rows:
        return None
    positive_rows = [row for row in rows if observation_is_positive(row)]
    negative_rows = [row for row in rows if not observation_is_positive(row)]
    month_counts: dict[int, int] = {}
    season_counts: dict[str, int] = {}
    for row in positive_rows:
        derived = row.get("derived") if isinstance(row.get("derived"), dict) else {}
        month = derived.get("month")
        if isinstance(month, int) and 1 <= month <= 12:
            month_counts[month] = month_counts.get(month, 0) + 1
        season = str(derived.get("season", "") or "").strip()
        if season:
            season_counts[season] = season_counts.get(season, 0) + 1
    return {
        "observation_count": len(rows),
        "positive_count": len(positive_rows),
        "negative_count": len(negative_rows),
        "month_counts": month_counts,
        "season_counts": season_counts,
    }


def phenology_support_chip(label: str, support: int, total: int, source: str = "field") -> str:
    ratio = ratio_label((support / total) if total else None)
    return (
        '<span class="parameter-learned-chip">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(str(support))}</strong>'
        f'<em>{html.escape(ratio)}</em>'
        f'<em class="parameter-source-badge source-{html.escape(css_token(source), quote=True)}">{html.escape(learned_source_label(source))}</em>'
        '</span>'
    )


def render_phenology_month_row(
    title: str,
    month_counts: dict[int, int],
    visible_months: set[int],
    total_positive: int,
    meta_label: str,
    meta_value: str,
) -> str:
    chips = [
        phenology_support_chip(ui_label(f"month.{month}"), month_counts[month], total_positive)
        for month in sorted(visible_months)
        if month in month_counts
    ]
    values_html = (
        "".join(chips)
        if chips else
        f'<span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span>'
    )
    return f"""
      <div class="parameter-comparison-section parameter-learned-row">
        <h4>{html.escape(title)}</h4>
        <span class="meta">{html.escape(meta_label)}: {html.escape(meta_value)}</span>
        <div class="parameter-learned-values">{values_html}</div>
      </div>
    """


def render_phenology_season_row(
    season_counts: dict[str, int],
    total_positive: int,
    catalogs: dict[str, object],
) -> str:
    season_labels = catalog_label_map(catalogs, "season_patterns")
    chips = [
        phenology_support_chip(season_labels.get(f"season_{season}", season), count, total_positive)
        for season, count in sorted(season_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    values_html = (
        "".join(chips)
        if chips else
        f'<span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span>'
    )
    return f"""
      <div class="parameter-comparison-section parameter-learned-row">
        <h4>{html.escape(ui_label("ui.season_patterns"))}</h4>
        <div class="parameter-learned-values">{values_html}</div>
      </div>
    """


def render_phenology_learned_comparison(
    phenology: dict[str, object],
    observations_payload: dict[str, object] | None,
    species_id: str,
    catalogs: dict[str, object],
    value_mode: str = "matches",
) -> str:
    """Render observed phenology evidence beside phenology parameters."""
    title_label = "ui.learned_emerging_values" if value_mode == "emerging" else "ui.learned_observational_evidence"
    evidence = phenology_evidence_from_observations(observations_payload, species_id)
    if not isinstance(evidence, dict):
        return f"""
        <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-phenology-column">
          <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
            <h3>{html.escape(ui_label(title_label))}</h3>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.main_months"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.secondary_months"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.season_patterns"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
        </aside>
        """
    month_counts = evidence.get("month_counts") if isinstance(evidence.get("month_counts"), dict) else {}
    season_counts = evidence.get("season_counts") if isinstance(evidence.get("season_counts"), dict) else {}
    total_positive = int(evidence.get("positive_count", 0) or 0)
    main_months = {month for month in phenology.get("main_months", []) if isinstance(month, int)}
    secondary_months = {month for month in phenology.get("secondary_months", []) if isinstance(month, int)}
    observed_months = {month for month in month_counts if isinstance(month, int)}
    configured_months = main_months | secondary_months
    if value_mode == "emerging":
        emerging_months = observed_months - configured_months
        rows = [
            render_phenology_month_row(
                ui_label("ui.main_months"),
                month_counts,
                emerging_months,
                total_positive,
                ui_label("ui.emerging_outside_profile"),
                str(len(emerging_months)),
            ),
            render_phenology_month_row(
                ui_label("ui.secondary_months"),
                month_counts,
                set(),
                total_positive,
                ui_label("ui.emerging_outside_profile"),
                "0",
            ),
            render_phenology_season_row({}, total_positive, catalogs),
        ]
    else:
        rows = [
            render_phenology_month_row(
                ui_label("ui.main_months"),
                month_counts,
                observed_months & main_months,
                total_positive,
                ui_label("ui.profile_overlap"),
                f"{len(observed_months & main_months)}/{len(main_months)}" if main_months else "0/0",
            ),
            render_phenology_month_row(
                ui_label("ui.secondary_months"),
                month_counts,
                observed_months & secondary_months,
                total_positive,
                ui_label("ui.profile_overlap"),
                f"{len(observed_months & secondary_months)}/{len(secondary_months)}" if secondary_months else "0/0",
            ),
            render_phenology_season_row(season_counts, total_positive, catalogs),
        ]
    return f"""
      <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-phenology-column">
        <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
          <h3>{html.escape(ui_label(title_label))}</h3>
          <div class="parameter-learned-metrics">
            <span>{html.escape(ui_label("ui.total_observations_used"))}: <strong>{html.escape(str(evidence.get("observation_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.positive_observations"))}: <strong>{html.escape(str(evidence.get("positive_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.negative_observations"))}: <strong>{html.escape(str(evidence.get("negative_count", 0) or 0))}</strong></span>
          </div>
        </div>
        <div class="parameter-learned-rows">{"".join(rows)}</div>
      </aside>
    """


def render_topography_learned_comparison(
    model: dict[str, object] | None,
    topography: dict[str, object],
    value_mode: str = "matches",
) -> str:
    """Render learned altitude evidence beside topography parameters."""
    title_label = "ui.learned_emerging_values" if value_mode == "emerging" else "ui.learned_observational_evidence"
    if not isinstance(model, dict):
        return f"""
        <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-topography-column">
          <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
            <h3>{html.escape(ui_label(title_label))}</h3>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("altitude.meters"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.preferred_aspects"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
          <p class="meta parameter-pending-note">{html.escape(ui_label("ui.learned_model_missing"))}</p>
        </aside>
        """
    altitude = learned_numeric_positive(model, "altitude_m")
    profile_range = (
        f"{model_number_label(topography.get('altitude_min_m'), 'm')} - "
        f"{model_number_label(topography.get('altitude_max_m'), 'm')}"
    )
    observed_range = (
        f"{model_number_label(altitude.get('min'), 'm')} - "
        f"{model_number_label(altitude.get('max'), 'm')}"
    )
    mean_label = model_number_label(altitude.get("mean"), "m")
    emerging_altitude = False
    try:
        profile_min = float(topography.get("altitude_min_m"))
        profile_max = float(topography.get("altitude_max_m"))
        observed_min = float(altitude.get("min"))
        observed_max = float(altitude.get("max"))
        emerging_altitude = observed_min < profile_min or observed_max > profile_max
    except (TypeError, ValueError):
        emerging_altitude = False
    if value_mode == "emerging":
        altitude_meta_label = ui_label("ui.emerging_outside_profile")
        altitude_meta_value = "1" if emerging_altitude else "0"
        altitude_values_html = (
            f'<span class="parameter-learned-chip"><span>{html.escape(ui_label("ui.observed_range"))}</span><strong>{html.escape(observed_range)}</strong></span>'
            if emerging_altitude else
            f'<span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span>'
        )
    else:
        altitude_meta_label = ui_label("ui.profile_range")
        altitude_meta_value = profile_range
        altitude_values_html = (
            f'<span class="parameter-learned-chip"><span>{html.escape(ui_label("ui.observed_range"))}</span><strong>{html.escape(observed_range)}</strong></span>'
            f'<span class="parameter-learned-chip"><span>{html.escape(ui_label("ui.learned_mean"))}</span><strong>{html.escape(mean_label)}</strong></span>'
        )
    return f"""
      <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-topography-column">
        <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
          <h3>{html.escape(ui_label(title_label))}</h3>
          <div class="parameter-learned-metrics">
            <span>{html.escape(ui_label("ui.total_observations_used"))}: <strong>{html.escape(str(model.get("observation_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.positive_observations"))}: <strong>{html.escape(str(model.get("positive_count", 0) or 0))}</strong></span>
            <span>{html.escape(ui_label("ui.gis_gaps"))}: <strong>{html.escape(str(model.get("gis_gap_count", 0) or 0))}</strong></span>
          </div>
        </div>
        <div class="parameter-learned-rows">
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("altitude.meters"))}</h4>
            <span class="meta">{html.escape(altitude_meta_label)}: {html.escape(altitude_meta_value)}</span>
            <div class="parameter-learned-values">
              {altitude_values_html}
            </div>
          </div>
          <div class="parameter-comparison-section parameter-learned-row">
            <h4>{html.escape(ui_label("ui.preferred_aspects"))}</h4>
            <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
          </div>
        </div>
      </aside>
    """


def render_phenology_pending_comparison(value_mode: str = "matches") -> str:
    """Render a consistent learned-model column for phenology parameters."""
    title_label = "ui.learned_emerging_values" if value_mode == "emerging" else "ui.learned_observational_evidence"
    return f"""
      <aside class="profile-subsection parameter-focus-subsection parameter-learned-comparison parameter-aligned-column parameter-phenology-column">
        <div class="parameter-comparison-section parameter-section-summary parameter-learned-summary">
          <h3>{html.escape(ui_label(title_label))}</h3>
        </div>
        <div class="parameter-comparison-section parameter-learned-row">
          <h4>{html.escape(ui_label("ui.main_months"))}</h4>
          <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
        </div>
        <div class="parameter-comparison-section parameter-learned-row">
          <h4>{html.escape(ui_label("ui.secondary_months"))}</h4>
          <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
        </div>
        <div class="parameter-comparison-section parameter-learned-row">
          <h4>{html.escape(ui_label("ui.season_patterns"))}</h4>
          <div class="parameter-learned-values"><span class="parameter-empty">{html.escape(ui_label("ui.none"))}</span></div>
        </div>
        <p class="meta parameter-pending-note">{html.escape(ui_label("ui.learned_model_missing"))}</p>
      </aside>
    """


def learned_categorical_feature_rows(model: dict[str, object], catalogs: dict[str, object]) -> str:
    groups = [
        ("hosts", ui_label("ui.evidence_hosts"), "host_taxa"),
        ("forests", ui_label("ui.evidence_forests"), "forest_types"),
        ("soils", ui_label("ui.evidence_soils"), "soil_types"),
        ("habitat", ui_label("ui.evidence_habitat"), "habitat_features"),
    ]
    categorical = model.get("categorical_features") if isinstance(model.get("categorical_features"), dict) else {}
    rows = []
    for key, title, catalog_group in groups:
        labels = {
            str(item.get("id", "") or ""): host_scientific_common_label(item)
            for item in catalogs.get(catalog_group, [])
            if catalog_group == "host_taxa" and isinstance(item, dict) and str(item.get("id", "") or "")
        } if catalog_group == "host_taxa" else catalog_label_map(catalogs, catalog_group)
        items = categorical.get(key)
        if not isinstance(items, list):
            continue
        for item in items[:8]:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "") or "")
            rows.append(
                "<tr>"
                f"<td><strong>{html.escape(labels.get(item_id, item_id))}</strong><span class=\"meta\">{html.escape(item_id)}</span></td>"
                f"<td>{html.escape(title)}</td>"
                f"<td><strong>{html.escape(str(item.get('positive_support', 0) or 0))}</strong><span class=\"meta\">{html.escape(ratio_label(item.get('positive_ratio')))}</span></td>"
                f"<td><strong>{html.escape(str(item.get('negative_support', 0) or 0))}</strong><span class=\"meta\">{html.escape(ratio_label(item.get('negative_ratio')))}</span></td>"
                f"<td>{html.escape(ratio_label(item.get('ratio_delta')))}</td>"
                "</tr>"
            )
    if not rows:
        return f'<p class="meta">{html.escape(ui_label("ui.learned_no_categorical_features"))}</p>'
    return (
        '<div class="evidence-table-shell learned-model-table learned-model-table-categorical"><table>'
        "<thead><tr>"
        "<th>ID</th>"
        f"<th>{html.escape(ui_label('ui.group'))}</th>"
        f"<th>{html.escape(ui_label('ui.learned_positive_short'))}</th>"
        f"<th>{html.escape(ui_label('ui.learned_negative_short'))}</th>"
        f"<th>{html.escape(ui_label('ui.learned_ratio_delta'))}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def learned_numeric_summary_cell(stats: dict[str, object], unit: str) -> str:
    """Render compact support, range and mean for learned numeric evidence."""
    count = str(stats.get("count", 0) or 0)
    minimum = model_number_label(stats.get("min"), unit)
    maximum = model_number_label(stats.get("max"), unit)
    mean = model_number_label(stats.get("mean"), unit)
    if minimum == "-" and maximum == "-":
        range_label = "-"
    else:
        range_label = f"{minimum} - {maximum}"
    return (
        f'<span class="learned-numeric-count">{html.escape(count)}</span>'
        f'<span class="learned-numeric-range">{html.escape(range_label)}</span>'
        f'<span class="meta">{html.escape(ui_label("ui.learned_mean"))}: {html.escape(mean)}</span>'
    )


def learned_numeric_feature_rows(model: dict[str, object]) -> str:
    labels = {
        "altitude_m": ui_label("altitude"),
        "rain_7d_mm": f"{ui_label('rainfall')} 7d",
        "rain_14d_mm": f"{ui_label('rainfall')} 14d",
        "rain_21d_mm": f"{ui_label('rainfall')} 21d",
        "rain_30d_mm": f"{ui_label('rainfall')} 30d",
        "rain_60d_mm": f"{ui_label('rainfall')} 60d",
        "rain_90d_mm": f"{ui_label('rainfall')} 90d",
        "temp_min_7d_c": "Temp min 7d",
        "temp_max_7d_c": "Temp max 7d",
        "temp_min_14d_c": "Temp min 14d",
        "temp_max_14d_c": "Temp max 14d",
        "temp_min_21d_c": "Temp min 21d",
        "temp_max_21d_c": "Temp max 21d",
        "temp_min_30d_c": "Temp min 30d",
        "temp_max_30d_c": "Temp max 30d",
        "humidity_min_7d_pct": "Hum min 7d",
        "humidity_max_7d_pct": "Hum max 7d",
        "humidity_min_14d_pct": "Hum min 14d",
        "humidity_max_14d_pct": "Hum max 14d",
        "humidity_min_21d_pct": "Hum min 21d",
        "humidity_max_21d_pct": "Hum max 21d",
        "humidity_min_30d_pct": "Hum min 30d",
        "humidity_max_30d_pct": "Hum max 30d",
    }
    units = {
        "altitude_m": "m",
        **{key: "mm" for key in labels if key.startswith("rain_")},
        **{key: "C" for key in labels if key.startswith("temp_")},
        **{key: "%" for key in labels if key.startswith("humidity_")},
    }
    numeric = model.get("numeric_features") if isinstance(model.get("numeric_features"), dict) else {}
    rows = []
    for key, label in labels.items():
        item = numeric.get(key)
        if not isinstance(item, dict):
            continue
        positive = item.get("positive") if isinstance(item.get("positive"), dict) else {}
        negative = item.get("negative") if isinstance(item.get("negative"), dict) else {}
        unit = units.get(key, "")
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(label)}</strong><span class=\"meta\">{html.escape(key)}</span></td>"
            f"<td>{learned_numeric_summary_cell(positive, unit)}</td>"
            f"<td>{learned_numeric_summary_cell(negative, unit)}</td>"
            "</tr>"
        )
    if not rows:
        return f'<p class="meta">{html.escape(ui_label("ui.learned_no_numeric_features"))}</p>'
    return (
        '<div class="evidence-table-shell learned-model-table numeric"><table>'
        "<thead><tr>"
        f"<th>{html.escape(ui_label('ui.variable'))}</th>"
        f"<th>{html.escape(ui_label('ui.learned_positive_short'))}</th>"
        f"<th>{html.escape(ui_label('ui.learned_negative_short'))}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_learned_model_section(
    profile: dict[str, object],
    catalogs: dict[str, object],
    learned_model_payload: dict[str, object] | None,
    search: str = "",
    profile_view: str = "enriched",
) -> str:
    """Render the experimental observation-learned v0 model for one species."""
    species_id = str(profile.get("species_id", "") or "")
    model = learned_model_for_species(learned_model_payload, species_id)
    generated_at = str(learned_model_payload.get("generated_at", "") or "") if isinstance(learned_model_payload, dict) else ""
    if model is None:
        return f"""
        <article class="profile-section-card learned-model-panel">
          <h3>{html.escape(ui_label("ui.learned_model"))}</h3>
          <p class="meta">{html.escape(ui_label("ui.learned_model_missing"))}</p>
        </article>
        """
    return f"""
    <article class="profile-section-card learned-model-panel">
      <div class="learned-model-toolbar">
        <div>
          <h3>{html.escape(ui_label("ui.learned_model"))}</h3>
          <p class="meta">{html.escape(ui_label("ui.learned_model_note"))} · {html.escape(generated_at or '-')}</p>
        </div>
        <div class="learned-model-actions">
          <form method="post" action="{html.escape(profile_query_url(species_id, search, section='evidence', profile_view=profile_view, evidence_view='learned_model'), quote=True)}" onsubmit="return confirm('{html.escape(ui_label("ui.rebuild_selected_learned_model_help"), quote=True)}')">
            <input type="hidden" name="profile_action" value="rebuild_learned_model_v0_species">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
            <input type="hidden" name="evidence_view" value="learned_model">
            <button class="secondary" type="submit" title="{html.escape(ui_label("ui.rebuild_selected_learned_model_help"), quote=True)}">{html.escape(ui_label("ui.rebuild_selected_learned_model"))}</button>
          </form>
          <form method="post" action="{html.escape(profile_query_url(species_id, search, section='evidence', profile_view=profile_view, evidence_view='learned_model'), quote=True)}" onsubmit="return confirm('{html.escape(ui_label("ui.rebuild_all_learned_model_help"), quote=True)}')">
            <input type="hidden" name="profile_action" value="rebuild_learned_model_v0_all">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
            <input type="hidden" name="evidence_view" value="learned_model">
            <button class="secondary" type="submit" title="{html.escape(ui_label("ui.rebuild_all_learned_model_help"), quote=True)}">{html.escape(ui_label("ui.rebuild_all_learned_model"))}</button>
          </form>
        </div>
      </div>
      <div class="profile-calibration-cards evidence-summary-cards learned-model-summary">
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.total_observations_used"))}</span><span class="value">{html.escape(str(model.get("observation_count", 0) or 0))}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.positive_observations"))}</span><span class="value ok">{html.escape(str(model.get("positive_count", 0) or 0))}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.negative_observations"))}</span><span class="value">{html.escape(str(model.get("negative_count", 0) or 0))}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.weather_gaps"))}</span><span class="value warn">{html.escape(str(model.get("weather_gap_count", 0) or 0))}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.gis_gaps"))}</span><span class="value">{html.escape(str(model.get("gis_gap_count", 0) or 0))}</span></div>
      </div>
      <div class="learned-model-grid">
        <section>
          <h4>{html.escape(ui_label("ui.learned_categorical_features"))}</h4>
          {learned_categorical_feature_rows(model, catalogs)}
        </section>
        <section>
          <h4>{html.escape(ui_label("ui.learned_numeric_features"))}</h4>
          {learned_numeric_feature_rows(model)}
        </section>
      </div>
    </article>
    """


def render_weather_evidence_section(profile: dict[str, object], features_payload: dict[str, object] | None) -> str:
    """Render read-only weather evidence from joined v0 observation features."""
    species_id = str(profile.get("species_id", "") or "")
    rows = features_payload.get("rows") if isinstance(features_payload, dict) else None
    all_rows = rows if isinstance(rows, list) else []
    species_rows = [
        row for row in all_rows
        if isinstance(row, dict) and str(row.get("species_id", "") or "") == species_id
    ]
    generated_at = str(features_payload.get("generated_at", "") or "") if isinstance(features_payload, dict) else ""
    if not isinstance(features_payload, dict):
        note = ui_label("ui.weather_features_missing")
    elif not species_rows:
        note = ui_label("ui.weather_features_species_missing")
    else:
        note = ui_label("ui.weather_readonly_note")
    present_rows = [row for row in species_rows if row.get("analysis_result") != "absent"]
    absent_rows = [row for row in species_rows if row.get("analysis_result") == "absent"]
    weather_gap_count = sum(1 for row in species_rows if row.get("weather_gaps"))
    gis_gap_count = sum(1 for row in species_rows if row.get("gis_gaps") or row.get("feature_gaps"))
    table_rows = []
    for row in sorted(species_rows, key=lambda item: (str(item.get("observed_at", "")), str(item.get("observation_id", ""))))[:80]:
        result_tone = "muted" if row.get("analysis_result") == "absent" else "ok"
        table_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(row.get('observed_at', '-') or '-'))}</strong><span class=\"meta\">{html.escape(str(row.get('observation_id', '-') or '-'))}</span></td>"
            f"<td><span class=\"evidence-status {result_tone}\">{html.escape(str(row.get('analysis_result', '-') or '-'))}</span><span class=\"meta\">{html.escape(str(row.get('flush_abundance', '-') or '-'))}</span></td>"
            f"<td>{weather_cell(row, 'gis_altitude_m', 'altitude_m')}</td>"
            f"<td>{weather_cell(row, 'rain_7d_mm')}</td>"
            f"<td>{weather_cell(row, 'rain_14d_mm')}</td>"
            f"<td>{weather_cell(row, 'rain_21d_mm')}</td>"
            f"<td>{weather_cell(row, 'rain_30d_mm')}</td>"
            f"<td>{weather_cell(row, 'rain_60d_mm')}</td>"
            f"<td>{weather_cell(row, 'rain_90d_mm')}</td>"
            f"<td>{html.escape(temperature_window_label(row, 7))}</td>"
            f"<td>{html.escape(temperature_window_label(row, 14))}</td>"
            f"<td>{html.escape(temperature_window_label(row, 21))}</td>"
            f"<td>{html.escape(temperature_window_label(row, 30))}</td>"
            f"<td>{html.escape(humidity_window_label(row, 7))}</td>"
            f"<td>{html.escape(humidity_window_label(row, 14))}</td>"
            f"<td>{html.escape(humidity_window_label(row, 21))}</td>"
            f"<td>{html.escape(humidity_window_label(row, 30))}</td>"
            f"<td><strong>{html.escape(str(row.get('weather_source', '-') or '-'))}</strong><span class=\"meta weather-station-detail\">{html.escape(str(row.get('weather_station_code', '-') or '-'))} · {html.escape(str(row.get('weather_station_distance_km', '-') if row.get('weather_station_distance_km') is not None else '-'))} km</span></td>"
            f"{render_weather_gap_cell(row.get('weather_gaps'))}"
            "</tr>"
        )
    table_html = (
        '<div class="evidence-table-shell weather-evidence-table"><table>'
        "<thead><tr>"
        f"<th>{html.escape(ui_label('ui.date_short'))}</th>"
        f"<th>{html.escape(ui_label('ui.result'))}</th>"
        f"{weather_metric_header('m', ui_label('ui.altitude_short'))}"
        f"{''.join(weather_metric_header('mm', f'{days}d') for days in (7, 14, 21, 30, 60, 90))}"
        f"{''.join(weather_metric_header('°C', f'{days}d') for days in (7, 14, 21, 30))}"
        f"{''.join(weather_metric_header('%', f'{days}d') for days in (7, 14, 21, 30))}"
        f"<th>{html.escape(ui_label('ui.station'))}</th>"
        f"<th>{html.escape(ui_label('ui.weather_gaps'))}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(table_rows)}</tbody></table></div>"
        if table_rows else
        f'<p class="meta">{html.escape(ui_label("ui.weather_no_rows"))}</p>'
    )
    return f"""
    <article class="profile-section-card weather-evidence">
      <h3>{icon("weather")} {html.escape(ui_label("ui.weather_evidence"))}</h3>
      <p class="meta">{html.escape(ui_label("ui.latest_features_join"))}: {html.escape(generated_at or '-')} · {html.escape(note)}</p>
      <div class="profile-calibration-cards evidence-summary-cards">
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.observations"))}</span><span class="value">{len(species_rows)}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.present_observations"))}</span><span class="value ok">{len(present_rows)}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.absent_observations"))}</span><span class="value">{len(absent_rows)}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.weather_gaps"))}</span><span class="value warn">{weather_gap_count}</span></div>
        <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.gis_gaps"))}</span><span class="value">{gis_gap_count}</span></div>
      </div>
      {table_html}
    </article>
    """


def render_evidence_view_tabs(species_id: str, search: str, profile_view: str, evidence_view: str) -> str:
    """Render the local evidence subnavigation."""
    active = str(evidence_view or "").strip().lower()
    if active not in {"hosts_forests", "soils_habitat", "weather", "learned_model"}:
        active = "hosts_forests"
    tabs = [
        ("hosts_forests", ui_label("ui.evidence_hosts_forests")),
        ("soils_habitat", ui_label("ui.evidence_soils_habitat")),
        ("weather", ui_label("ui.evidence_weather")),
        ("learned_model", ui_label("ui.evidence_learned_model")),
    ]
    links = []
    for key, label in tabs:
        css = "mushroom-title-tab active" if key == active else "mushroom-title-tab"
        href = profile_query_url(
            species_id,
            search,
            section="evidence",
            profile_view=profile_view,
            evidence_view=key,
        )
        links.append(f'<a class="{css}" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    return f'<nav class="evidence-view-tabs">{"".join(links)}</nav>'


def render_local_evidence_section(
    profile: dict[str, object] | None,
    catalogs: dict[str, object],
    reconstruction_payload: dict[str, object] | None,
    observation_features_payload: dict[str, object] | None = None,
    decisions_payload: dict[str, object] | None = None,
    learned_model_payload: dict[str, object] | None = None,
    search: str = "",
    profile_view: str = "enriched",
    evidence_view: str = "hosts_forests",
    observations_payload: dict[str, object] | None = None,
    profiles: list[dict[str, object]] | None = None,
) -> str:
    """Render profile-vs-observed local v0 evidence without changing profiles."""
    if not profile:
        return '<section class="card profile-section-screen"><h2>Evidencia</h2><p class="meta">Selecciona una especie para revisar evidencia local v0.</p></section>'
    species_id = str(profile.get("species_id", "") or "")
    ecology = nested_dict(profile, "ecology")
    observation_count, counts = local_evidence_counts_from_features(species_id, observation_features_payload)
    if not observation_count:
        observation_count, counts = local_evidence_counts(species_id, reconstruction_payload)
    reconstruction_lookup = local_evidence_row_lookup(reconstruction_payload)
    observation_lookup = observation_payload_lookup(observations_payload)
    decisions = local_evidence_decision_lookup(decisions_payload)
    generated_at = str(reconstruction_payload.get("generated_at", "") or "") if isinstance(reconstruction_payload, dict) else ""
    evidence_view = str(evidence_view or "").strip().lower()
    if evidence_view not in {"hosts_forests", "soils_habitat", "weather", "learned_model"}:
        evidence_view = "hosts_forests"
    visible_groups = [
        group for group in LOCAL_EVIDENCE_GROUPS
        if str(group.get("evidence_view", "")) == evidence_view
    ]
    groups = []
    summary_values = {"observed_not_declared": 0, "declared_not_observed": 0, "declared_observed": 0}
    for group in visible_groups:
        declared_ids = profile_v0_affinity_ids(ecology, str(group["profile_field"]))
        observed_items = counts.get(str(group["context_field"]), {})
        for item_id in set(declared_ids) | set(observed_items):
            observed_count = int(observed_items.get(item_id, {}).get("count", 0) or 0)
            declared = item_id in declared_ids
            if declared and observed_count:
                summary_values["declared_observed"] += 1
            elif declared and observation_count:
                summary_values["declared_not_observed"] += 1
            elif observed_count:
                summary_values["observed_not_declared"] += 1
        groups.append(
            render_local_evidence_group(
                ui_label(str(group["title_label"])),
                str(group["profile_field"]),
                str(group["catalog_group"]),
                species_id,
                declared_ids,
                observed_items,
                observation_count,
                catalogs,
                decisions,
                reconstruction_lookup,
                observation_lookup,
                search,
                profile_view,
                evidence_view,
            )
        )
    if not isinstance(reconstruction_payload, dict):
        note = "No hay reconstruccion GIS local cargada. Ejecuta la reconstruccion desde Observaciones."
    elif not observation_count:
        note = "La ultima reconstruccion no contiene observaciones para esta especie."
    else:
        note = "Vista de solo lectura. No modifica perfiles; sirve para decidir promociones o dudas de forma manual."
    tabs_html = render_evidence_view_tabs(species_id, search, profile_view, evidence_view)
    if evidence_view == "weather":
        return f"""
        <section class="card profile-section-screen evidence-screen">
          <div class="evidence-sticky-header">
            {render_selected_species_header(profile, "Evidencia local v0", profiles=profiles, search=search, section_key="evidence", profile_view=profile_view, evidence_view=evidence_view)}
            {tabs_html}
          </div>
          {render_weather_evidence_section(profile, observation_features_payload)}
        </section>
        """
    if evidence_view == "learned_model":
        return f"""
        <section class="card profile-section-screen evidence-screen">
          <div class="evidence-sticky-header">
            {render_selected_species_header(profile, "Evidencia local v0", profiles=profiles, search=search, section_key="evidence", profile_view=profile_view, evidence_view=evidence_view)}
            {tabs_html}
          </div>
          {render_learned_model_section(profile, catalogs, learned_model_payload, search=search, profile_view=profile_view)}
        </section>
        """
    return f"""
    <section class="card profile-section-screen evidence-screen">
      <div class="evidence-sticky-header">
        {render_selected_species_header(profile, "Evidencia local v0", profiles=profiles, search=search, section_key="evidence", profile_view=profile_view, evidence_view=evidence_view)}
        {tabs_html}
        <div class="profile-calibration-cards evidence-summary-cards">
          <div class="profile-metric"><span class="label">Obs. reconstruidas</span><span class="value">{observation_count}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.evidence_observed_not_declared"))}</span><span class="value warn">{summary_values["observed_not_declared"]}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.evidence_declared_observed"))}</span><span class="value ok">{summary_values["declared_observed"]}</span></div>
          <div class="profile-metric"><span class="label">{html.escape(ui_label("ui.evidence_declared_not_observed"))}</span><span class="value">{summary_values["declared_not_observed"]}</span></div>
        </div>
        <p class="meta">Ultima reconstruccion: {html.escape(generated_at or '-')} · {html.escape(note)}</p>
      </div>
      <div class="evidence-grid">
        {''.join(groups)}
      </div>
    </section>
    """


def render_profile_affinity_rows(
    field: str,
    values: object,
    catalogs: dict[str, object],
    profile_view: str = "enriched",
    profile_source_v0: bool = False,
) -> str:
    """Render editable affinity rows while hiding already-used IDs from new rows."""
    catalog_group = PROFILE_AFFINITY_GROUPS[field]
    options = host_affinity_options(catalogs) if field == "host_affinities" else catalog_options_for_group(catalogs, catalog_group)
    affinities = values if isinstance(values, list) else []
    used_ids = {
        str(item.get("id", "") or "").strip()
        for item in affinities
        if isinstance(item, dict) and str(item.get("id", "") or "").strip()
    }
    rows = []
    visible_affinities = [
        item for item in affinities
        if isinstance(item, dict) and (not is_v0_view(profile_view) or v0_active_affinity(item))
    ]
    editable_rows = visible_affinities + ([] if is_v0_view(profile_view) else [{} for _ in range(3)])
    for index, item in enumerate(editable_rows):
        current_id = str(item.get("id", "") or "").strip()
        row_options = [option for option in options if option[0] == current_id or option[0] not in used_ids]
        inactive_v0 = item.get("v0_active") is False
        status = []
        if inactive_v0:
            status.append("Aparcado v0")
        status_html = (
            '<div class="profile-v0-row-flags">' + "".join(f"<span>{html.escape(flag)}</span>" for flag in status) + "</div>"
            if status else ""
        )
        rows.append(
            '<div class="profile-affinity-row">'
            + affinity_hidden_metadata_fields(field, index, item)
            + form_catalog_select(f"{field}_{index}_id", "ID", current_id, row_options)
            + form_select(f"{field}_{index}_relationship", ui_label("ui.relationship"), item.get("relationship", ""), PROFILE_SELECT_VALUES["relationship"])
            + (
                '<div class="admin-field profile-affinity-origins">'
                f'<label>{html.escape(ui_label("ui.origins"))}</label>'
                f'<div>{affinity_origin_badges(item, profile_source_v0)}</div>'
                "</div>"
            )
            + form_field(f"{field}_{index}_affinity", ui_label("ui.affinity"), item.get("affinity", ""), field_type="number", step="0.01")
            + status_html
            + "</div>"
        )
    return (
        f'<div class="profile-affinity-block {html.escape(field)}">'
        f'<h2>{html.escape(field.replace("_", " ").title())}</h2>'
        '<div class="profile-affinity-rows">'
        + "".join(rows)
        + "</div></div>"
    )


def render_ecology_affinity_tabs(
    ecology: dict[str, object],
    catalogs: dict[str, object],
    profile_view: str = "enriched",
    profile_source_v0: bool = False,
) -> str:
    """Render ecology affinity groups as internal subtabs without changing POST fields."""
    fields = [field for field in PROFILE_AFFINITY_GROUPS if not (is_v0_view(profile_view) and field == "lithology_affinities")]
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
        panels.append(
            f'<section class="ecology-subtab-panel panel-{index}">'
            f'{render_profile_affinity_rows(field, ecology.get(field, []), catalogs, profile_view, profile_source_v0)}'
            "</section>"
        )
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
    profile_view: str = "enriched",
) -> str:
    """Render the visual first-tab dashboard inspired by the species mockup."""
    delay = phenology.get("fruiting_delay_after_rain_days") if isinstance(phenology.get("fruiting_delay_after_rain_days"), dict) else {}
    host_labels = catalog_label_map(catalogs, "host_taxa")
    host_names = []
    for item in ecology.get("host_affinities", []) if isinstance(ecology.get("host_affinities"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            if is_v0_view(profile_view) and not v0_active_affinity(item):
                continue
            host_id = str(item.get("id"))
            host_names.append(host_labels.get(host_id, f"{host_id} (missing)"))
    season_names = phenology.get("season_pattern_ids") if isinstance(phenology.get("season_pattern_ids"), list) else []
    aspect_names = topography.get("preferred_aspect_ids") if isinstance(topography.get("preferred_aspect_ids"), list) else []
    weather_card = "" if is_v0_view(profile_view) else f"""
      <article class="profile-overview-card wide">
        {card_title(4, ui_label("ui.weather_model_summary"), "weather")}
        {render_weather_summary(weather_model)}
      </article>
    """
    scoring_card = "" if is_v0_view(profile_view) else f"""
      <article class="profile-overview-card">
        {card_title(5, ui_label("ui.scoring_weights"), "scoring")}
        {''.join(score_bar(key, value) for key, value in scoring.items())}
      </article>
    """
    delay_row = "" if is_v0_view(profile_view) else value_row(ui_label("ui.fruiting_delay"), f'{delay.get("min", "-")} / {delay.get("optimal_min", "-")}-{delay.get("optimal_max", "-")} / {delay.get("max", "-")} days')
    optimal_altitude_row = "" if is_v0_view(profile_view) else value_row(ui_label("ui.optimal_altitude"), f'{topography.get("altitude_optimal_min_m", "-")} - {topography.get("altitude_optimal_max_m", "-")} m')
    parked_count = inactive_v0_affinity_count(ecology)
    parked_row = value_row("Aparcado para v0", f"{parked_count} afinidades") if is_v0_view(profile_view) and parked_count else ""
    metadata_card = f"""
      <article class="profile-overview-card">
        {card_title(7, ui_label("ui.metadata"), "metadata")}
        {value_row(ui_label("metadata.created_at"), metadata.get("created_at"))}
        {value_row(ui_label("metadata.updated_at"), metadata.get("updated_at"))}
        {value_row(ui_label("metadata.created_by"), metadata.get("created_by"))}
        {value_row(ui_label("ui.review_status"), value_label(metadata.get("review_status")))}
        {value_row(ui_label("ui.source_quality"), value_label(metadata.get("source_quality")))}
        {value_row(ui_label("ui.requires_human_validation"), ui_label("ui.yes") if metadata.get("requires_human_validation") is True else ui_label("ui.no"))}
      </article>
    """
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
        {optimal_altitude_row}
        {value_row(ui_label("ui.preferred_aspects"), catalog_compact_list(catalogs, "aspects", aspect_names, 6))}
        {parked_row}
      </article>
      <article class="profile-overview-card">
        {card_title(3, ui_label("ui.phenology"), "phenology")}
        <span class="label">{html.escape(ui_label("ui.main_months"))}</span>
        {month_chips(phenology.get("main_months", []))}
        <span class="label">{html.escape(ui_label("ui.secondary_months"))}</span>
        {month_chips(phenology.get("secondary_months", []), "secondary-month")}
        {value_row(ui_label("ui.season_patterns"), catalog_compact_list(catalogs, "season_patterns", season_names, 3))}
        {delay_row}
      </article>
      {weather_card}
      {scoring_card}
      <article class="profile-overview-card">
        {card_title(6, ui_label("ui.confidence_calibration"), "calibration")}
        {value_row(ui_label("ui.overall_confidence"), value_label(confidence.get("overall_confidence")))}
        {value_row(ui_label("ui.habitat_confidence"), value_label(confidence.get("habitat_confidence")))}
        {value_row(ui_label("ui.phenology_confidence"), value_label(confidence.get("phenology_confidence")))}
        {value_row(ui_label("ui.weather_threshold_confidence"), value_label(confidence.get("weather_threshold_confidence")))}
        {value_row(ui_label("ui.local_calibration_status"), value_label(confidence.get("local_calibration_status")))}
        {value_row(ui_label("ui.priority"), value_label(confidence.get("calibration_priority")))}
      </article>
      {metadata_card}
    </section>
    """


def render_profile_editor(profile: dict[str, object] | None, catalogs: dict[str, object], profile_view: str = "enriched", search: str = "") -> str:
    """Render the selected profile editor using the existing POST contract."""
    if not profile:
        return f'<section class="card profile-editor"><h2>{html.escape(ui_label("ui.species_detail"))}</h2><p>{html.escape(ui_label("ui.no_species_selected"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    profile_view = normalize_profile_view(profile_view)
    v0_mode = is_v0_view(profile_view)
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
    profile_source_v0 = bool(str(metadata.get("v0_candidate_source", "") or "").strip())
    affinity_blocks = render_ecology_affinity_tabs(ecology, catalogs, profile_view, profile_source_v0)
    status_chips = "".join(
        [
            value_chip(profile.get("taxonomy_status", "-"), ui_label("ui.taxonomy")),
            value_chip(profile.get("edibility", "-"), ui_label("ui.edibility")),
            value_chip(confidence.get("overall_confidence", "-"), ui_label("ui.confidence")),
            value_chip(confidence.get("local_calibration_status", "-"), ui_label("ui.calibration")),
            value_chip(metadata.get("review_status", "-"), ui_label("ui.review_status")),
        ]
    )
    general_dashboard = render_general_dashboard(profile, catalogs, ecology, phenology, topography, weather_model, scoring, confidence, metadata, profile_view)
    duplicate_species_id = f"{species_id}_copy"
    duplicate_scientific_name = f"{profile.get('scientific_name', species_id)} copy"
    weather_tab_input = '' if v0_mode else '<input type="radio" name="profile_tab" id="profile-tab-weather">'
    scoring_tab_input = '' if v0_mode else '<input type="radio" name="profile_tab" id="profile-tab-scoring">'
    json_tab_input = '' if v0_mode else '<input type="radio" name="profile_tab" id="profile-tab-json">'
    weather_tab_label = '' if v0_mode else f'<label for="profile-tab-weather">{icon("weather")}{html.escape(ui_label("ui.weather"))}</label>'
    scoring_tab_label = '' if v0_mode else f'<label for="profile-tab-scoring">{icon("scoring")}{html.escape(ui_label("ui.scoring"))}</label>'
    json_tab_label = '' if v0_mode else f'<label for="profile-tab-json">{icon("metadata")}{html.escape(ui_label("ui.json"))}</label>'
    weather_panel = '' if v0_mode else f"""
            <section class="profile-section profile-tab-panel weather">
              <h2>{html.escape(ui_label("ui.weather_model"))}</h2>
              <div class="profile-grid four">
                {''.join(form_field(f"rainfall_{key}", parameter_label(key), value, field_type="number") for key, value in rainfall.items())}
                {''.join(form_field(f"temperature_{key}", parameter_label(key), value, field_type="number") for key, value in temperature.items())}
                {''.join(form_field(f"humidity_{key}", parameter_label(key), value, field_type="number") for key, value in humidity.items())}
                {''.join(form_field(f"wind_{key}", parameter_label(key), value, field_type="checkbox" if isinstance(value, bool) else "number") for key, value in wind.items())}
              </div>
            </section>
    """
    scoring_panel = '' if v0_mode else f"""
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
    """
    json_panel = '' if v0_mode else f"""
            <section class="profile-section profile-tab-panel json">
              <h2>{html.escape(ui_label("ui.advanced_json"))}</h2>
              <p class="meta">{html.escape(ui_label("ui.raw_json_help"))}</p>
            </section>
    """
    delay_grid = '' if v0_mode else f"""
                  <div class="profile-delay-grid">
                    {form_field("delay_min", ui_label("ui.delay_min"), delay.get("min", ""), field_type="number")}
                    {form_field("delay_optimal_min", ui_label("ui.delay_optimal_min"), delay.get("optimal_min", ""), field_type="number")}
                    {form_field("delay_max", ui_label("ui.delay_max"), delay.get("max", ""), field_type="number")}
                    {form_field("delay_optimal_max", ui_label("ui.delay_optimal_max"), delay.get("optimal_max", ""), field_type="number")}
                  </div>
    """
    altitude_fields = (
        f'{form_field("altitude_min_m", parameter_label("altitude_min_m"), topography.get("altitude_min_m", ""), field_type="number")}'
        f'{form_field("altitude_max_m", parameter_label("altitude_max_m"), topography.get("altitude_max_m", ""), field_type="number")}'
        if v0_mode else
        f'{form_field("altitude_min_m", parameter_label("altitude_min_m"), topography.get("altitude_min_m", ""), field_type="number")}'
        f'{form_field("altitude_optimal_min_m", parameter_label("altitude_optimal_min_m"), topography.get("altitude_optimal_min_m", ""), field_type="number")}'
        f'{form_field("altitude_max_m", parameter_label("altitude_max_m"), topography.get("altitude_max_m", ""), field_type="number")}'
        f'{form_field("altitude_optimal_max_m", parameter_label("altitude_optimal_max_m"), topography.get("altitude_optimal_max_m", ""), field_type="number")}'
    )
    save_button = f'<button class="primary profile-primary-action">{html.escape(ui_label("ui.save_species_profile"))}</button>'
    raw_json_details = "" if v0_mode else f"""
      <details class="profile-raw-json">
        <summary><strong>{html.escape(ui_label("ui.advanced_raw_json"))}</strong></summary>
        <form class="profile-json-editor" method="post" action="{html.escape(profile_query_url(species_id, search, section='species', profile_view=profile_view), quote=True)}" onsubmit="return confirm('Save raw JSON for this species profile and validate the full dataset?')">
          <input type="hidden" name="profile_action" value="save_profile_json">
          <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
          <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
          <input type="hidden" name="profile_return_tab" value="profile-tab-json">
          <label class="label" for="profile-json">{html.escape(ui_label("ui.species_profile_json"))}</label>
          <textarea id="profile-json" name="profile_json" spellcheck="false">{html.escape(json_value)}</textarea>
          <button class="primary">{html.escape(ui_label("ui.save_raw_json"))}</button>
        </form>
      </details>
    """
    modal_return_href = profile_query_url(species_id, search, section="species", profile_view=profile_view)
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
        <div class="profile-hero-side">
          <div class="profile-hero-chips">{status_chips}</div>
        </div>
      </div>
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='species', profile_view=profile_view), quote=True)}" onsubmit="return confirm('Save this species profile and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_form">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
        <input type="hidden" name="profile_return_tab" value="profile-tab-general">
        <div class="profile-tabs">
          <input type="radio" name="profile_tab" id="profile-tab-general" checked>
          <input type="radio" name="profile_tab" id="profile-tab-ecology">
          <input type="radio" name="profile_tab" id="profile-tab-phenology">
          {weather_tab_input}
          {scoring_tab_input}
          <input type="radio" name="profile_tab" id="profile-tab-calibration">
          <input type="radio" name="profile_tab" id="profile-tab-metadata">
          {json_tab_input}
          <div class="profile-tab-labels">
            <label for="profile-tab-general">{icon("identity")}{html.escape(ui_label("ui.general"))}</label>
            <label for="profile-tab-ecology">{icon("ecology")}{html.escape(ui_label("ui.ecology"))}</label>
            <label for="profile-tab-phenology">{icon("phenology")}{html.escape(ui_label("ui.phenology_topography"))}</label>
            {weather_tab_label}
            {scoring_tab_label}
            <label for="profile-tab-calibration">{icon("calibration")}{html.escape(ui_label("ui.confidence"))}</label>
            <label for="profile-tab-metadata">{icon("metadata")}{html.escape(ui_label("ui.metadata"))}</label>
            {json_tab_label}
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
                  {delay_grid}
                </div>
                <div class="profile-season-pattern-field">
                  {form_catalog_toggles("season_pattern_ids", ui_label("ui.season_patterns"), phenology.get("season_pattern_ids", []), catalogs, "season_patterns")}
                </div>
              </div>
              <h3>{html.escape(ui_label("ui.topography"))}</h3>
              <div class="profile-topography-layout">
                <div class="profile-altitude-grid">
                  {altitude_fields}
                </div>
                <div class="profile-aspect-field">
                  {form_catalog_toggles("preferred_aspect_ids", ui_label("ui.preferred_aspects"), topography.get("preferred_aspect_ids", []), catalogs, "aspects")}
                </div>
              </div>
              {form_textarea("aspect_notes", ui_label("site_context.aspect_notes"), topography.get("aspect_notes", ""), rows=2)}
            </section>
            {weather_panel}
            {scoring_panel}
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
            {json_panel}
          </div>
        </div>
        <div class="profile-action-bar">
          <a class="button-link primary-link" href="#new-species-modal">{html.escape(ui_label("ui.new_species"))}</a>
          <button class="secondary" name="profile_action" value="backup_profiles_keep" type="submit" formnovalidate onclick="return confirm('Create a manual keep backup of the full species profiles file now?')">{html.escape(ui_label("ui.backup"))}</button>
          {save_button}
          <a class="button-link secondary-link" href="#duplicate-species-modal">{html.escape(ui_label("ui.duplicate_species"))}</a>
          <a class="button-link danger-link" href="#archive-species-modal">{html.escape(ui_label("ui.archive_species"))}</a>
          <button class="secondary planned-action" type="button" disabled title="{html.escape(ui_label('ui.planned_profile_validation_title'), quote=True)}">{html.escape(ui_label("ui.validate_profile_planned"))}</button>
        </div>
      </form>
      <div id="duplicate-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="{html.escape(modal_return_href, quote=True)}" aria-label="Cancel duplicate species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>{html.escape(ui_label("ui.duplicate_species"))}</h2>
              <p>{html.escape(ui_label("ui.duplicate_species_help"))}</p>
            </div>
            <a class="button-link" href="{html.escape(modal_return_href, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
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
              <a class="button-link" href="{html.escape(modal_return_href, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
              <button class="secondary">{html.escape(ui_label("ui.duplicate_species"))}</button>
            </div>
          </form>
        </section>
      </div>
      <div id="archive-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="{html.escape(modal_return_href, quote=True)}" aria-label="Cancel archive species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>{html.escape(ui_label("ui.archive_species"))}</h2>
              <p>{html.escape(ui_label("ui.archive_species_help"))}</p>
            </div>
            <a class="button-link" href="{html.escape(modal_return_href, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
          </header>
          <form method="post" action="" onsubmit="return confirm('Archive this species profile? It will be removed from active profiles but can be restored.')">
            <input type="hidden" name="profile_action" value="archive_profile">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <div class="admin-field">
              <label for="profile-archive-species-id">{html.escape(ui_label("ui.species_id_to_archive"))}</label>
              <input id="profile-archive-species-id" value="{html.escape(species_id, quote=True)}" readonly>
            </div>
            <div class="modal-actions">
              <a class="button-link" href="{html.escape(modal_return_href, quote=True)}">{html.escape(ui_label("ui.cancel"))}</a>
              <button class="danger-button">{html.escape(ui_label("ui.archive_species"))}</button>
            </div>
          </form>
        </section>
      </div>
      {raw_json_details}
    </section>
    """


def render_parameters_section(
    profile: dict[str, object] | None,
    catalogs: dict[str, object],
    profiles: list[dict[str, object]] | None = None,
    search: str = "",
    profile_view: str = "enriched",
    parameter_view: str = "habitat",
    learned_model_payload: dict[str, object] | None = None,
    observations_payload: dict[str, object] | None = None,
) -> str:
    """Render the top-level Parameters screen using real profile model fields."""
    if not profile:
        return f'<section class="card profile-section-screen"><h2>{html.escape(ui_label("ui.parameters"))}</h2><p>{html.escape(ui_label("ui.no_species_selected"))}</p></section>'
    species_id = str(profile.get("species_id", ""))
    profile_view = normalize_profile_view(profile_view)
    v0_mode = is_v0_view(profile_view)
    parameter_view = normalize_parameter_view(parameter_view, profile_view)
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
    learned_model = merge_live_field_model(
        learned_model_for_species(learned_model_payload, species_id),
        field_evidence_model_from_observations(observations_payload, species_id),
    )
    delay = phenology.get("fruiting_delay_after_rain_days") if isinstance(phenology.get("fruiting_delay_after_rain_days"), dict) else {}
    host_labels = catalog_label_map(catalogs, "host_taxa")
    forest_labels = catalog_label_map(catalogs, "forest_types")
    soil_labels = catalog_label_map(catalogs, "soil_types")
    lithology_labels = catalog_label_map(catalogs, "lithology_types")
    habitat_labels = catalog_label_map(catalogs, "habitat_features")
    scoring_total = sum(float(value) for value in scoring.values() if isinstance(value, int | float))
    species_href = profile_query_url(species_id, search, section="species", profile_view=profile_view)
    species_ecology_href = f"{species_href}#profile-tab-ecology"
    affinity_row_class = "stacked"
    climate_card = "" if v0_mode else f"""
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
    """
    scoring_card = "" if v0_mode else f"""
            <article class="profile-section-card">
              <h2>{icon("scoring")} {html.escape(ui_label("ui.scoring_weights"))}</h2>
              <div class="profile-scoring-total"><span>{html.escape(ui_label("ui.current_total"))}</span><strong>{scoring_total:.2f}</strong><em>{html.escape(ui_label("ui.target"))}: 1.00</em></div>
              <div class="parameter-score-grid">
                {''.join(parameter_field(f"score_{key}", parameter_label(key), value, step="0.01", minimum="0", maximum="1") for key, value in scoring.items())}
              </div>
            </article>
    """
    lithology_row = "" if v0_mode else value_html_row(
        ui_label("ui.lithology"),
        affinity_chip_list(ecology, "lithology_affinities", lithology_labels, profile_view=profile_view),
        affinity_row_class,
    )
    optimal_altitude_fields = "" if v0_mode else (
        f'{parameter_field("altitude_optimal_min_m", parameter_label("altitude_optimal_min_m"), topography.get("altitude_optimal_min_m", ""), unit="m")}'
        f'{parameter_field("altitude_optimal_max_m", parameter_label("altitude_optimal_max_m"), topography.get("altitude_optimal_max_m", ""), unit="m")}'
    )
    delay_fields = "" if v0_mode else f"""
                <div class="parameter-duo-grid">
                  {parameter_field("delay_min", ui_label("ui.delay_min"), delay.get("min", ""), unit="d")}
                  {parameter_field("delay_optimal_min", ui_label("ui.delay_optimal_min"), delay.get("optimal_min", ""), unit="d")}
                  {parameter_field("delay_optimal_max", ui_label("ui.delay_optimal_max"), delay.get("optimal_max", ""), unit="d")}
                  {parameter_field("delay_max", ui_label("ui.delay_max"), delay.get("max", ""), unit="d")}
                </div>
    """
    main_months_control = (
        form_month_toggles("main_months", ui_label("ui.main_months"), phenology.get("main_months", []))
        if v0_mode else
        parameter_textarea("main_months", ui_label("ui.main_months"), phenology.get("main_months", []), rows=1)
    )
    secondary_months_control = (
        form_month_toggles("secondary_months", ui_label("ui.secondary_months"), phenology.get("secondary_months", []), "secondary-month")
        if v0_mode else
        parameter_textarea("secondary_months", ui_label("ui.secondary_months"), phenology.get("secondary_months", []), rows=1)
    )
    aspect_notes_control = (
        parameter_textarea("aspect_notes", ui_label("site_context.aspect_notes"), topography.get("aspect_notes", ""), rows=3)
        if v0_mode else
        parameter_textarea("aspect_notes", ui_label("site_context.aspect_notes"), topography.get("aspect_notes", ""), rows=1)
    )

    def parameter_panel(view: str, content: str) -> str:
        active_class = "active" if view == parameter_view else "inactive"
        return f'<div class="parameter-tab-panel {active_class}" data-parameter-view="{html.escape(view, quote=True)}">{content}</div>'

    habitat_panel = f"""
      <article class="profile-section-card">
        <div class="parameter-card-heading">
          <h2>{icon("ecology")} {html.escape(ui_label("ui.habitat_model"))}</h2>
          <p class="parameter-card-note">{html.escape(ui_label("ui.habitat_model_note"))}</p>
        </div>
        <div class="parameter-comparison-layout">
          <div class="profile-subsection parameter-focus-subsection parameter-ecology-profile">
            <h3>{icon("host")} {html.escape(ui_label("ui.ecology_and_habitat"))}</h3>
            <div class="parameter-profile-sections">
              <div class="parameter-comparison-section parameter-section-summary parameter-profile-section">
                {form_catalog_select("trophic_mode_id", ui_label("ui.trophic_mode"), ecology.get("trophic_mode_id", ""), catalog_options_for_group(catalogs, "trophic_modes"))}
              </div>
              <div class="parameter-comparison-section parameter-section-hosts parameter-profile-section">
                <h4>{html.escape(ui_label("ui.primary_hosts"))}</h4>
                {value_html_row(ui_label("ui.primary_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, "primary", profile_view=profile_view), affinity_row_class)}
                {value_html_row(ui_label("ui.secondary_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, "secondary", profile_view=profile_view), affinity_row_class)}
                {value_html_row(ui_label("ui.other_hosts"), affinity_chip_list(ecology, "host_affinities", host_labels, exclude_relationships={"primary", "secondary"}, profile_view=profile_view), affinity_row_class)}
              </div>
              <div class="parameter-comparison-section parameter-section-forests parameter-profile-section">
                <h4>{html.escape(ui_label("ui.forest_types"))}</h4>
                <div class="parameter-section-values">{affinity_chip_list(ecology, "forest_type_affinities", forest_labels, profile_view=profile_view)}</div>
              </div>
              <div class="parameter-comparison-section parameter-section-habitat parameter-profile-section">
                <h4>{html.escape(ui_label("ui.habitat_features"))}</h4>
                <div class="parameter-section-values">{affinity_chip_list(ecology, "habitat_feature_affinities", habitat_labels, profile_view=profile_view)}</div>
              </div>
            </div>
          </div>
          {render_habitat_learned_comparison(learned_model, ecology, catalogs, profile_view)}
          {render_habitat_learned_comparison(learned_model, ecology, catalogs, profile_view, value_mode="emerging")}
        </div>
        <div class="parameter-edit-note"><a href="{html.escape(species_ecology_href, quote=True)}">{html.escape(ui_label("ui.edit_affinities_note"))}</a></div>
      </article>
    """
    soils_panel = f"""
      <article class="profile-section-card">
        <div class="parameter-card-heading">
          <h2>{icon("soil")} {html.escape(ui_label("ui.soils_and_lithology"))}</h2>
        </div>
        <div class="parameter-comparison-layout">
          <div class="profile-subsection parameter-focus-subsection parameter-aligned-column parameter-soils-column">
            <div class="parameter-comparison-section parameter-section-summary parameter-profile-section"></div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("ui.soils"))}</h4>
              <div class="parameter-section-values">{affinity_chip_list(ecology, "soil_affinities", soil_labels, profile_view=profile_view)}</div>
            </div>
            {f'<div class="parameter-comparison-section parameter-profile-section"><h4>{html.escape(ui_label("ui.lithology"))}</h4><div class="parameter-section-values">{affinity_chip_list(ecology, "lithology_affinities", lithology_labels, profile_view=profile_view)}</div></div>' if not v0_mode else ""}
            <p class="meta">{html.escape(ui_label("ui.affinity_ids_note"))}</p>
          </div>
          {render_soils_learned_comparison(learned_model, ecology, catalogs, profile_view)}
          {render_soils_learned_comparison(learned_model, ecology, catalogs, profile_view, value_mode="emerging")}
        </div>
      </article>
    """
    topography_panel = f"""
      <article class="profile-section-card">
        <div class="parameter-card-heading">
          <h2>{icon("topography")} {html.escape(ui_label("ui.topography"))}</h2>
        </div>
        <div class="parameter-comparison-layout">
          <div class="profile-subsection parameter-focus-subsection parameter-aligned-column parameter-topography-column">
            <div class="parameter-comparison-section parameter-section-summary parameter-profile-section parameter-topography-notes">
              {aspect_notes_control}
            </div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("altitude.meters"))}</h4>
              <div class="parameter-duo-grid">
                {parameter_field("altitude_min_m", parameter_label("altitude_min_m"), topography.get("altitude_min_m", ""), unit="m")}
                {parameter_field("altitude_max_m", parameter_label("altitude_max_m"), topography.get("altitude_max_m", ""), unit="m")}
                {optimal_altitude_fields}
              </div>
            </div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("ui.preferred_aspects"))}</h4>
              {form_catalog_toggles("preferred_aspect_ids", ui_label("ui.preferred_aspects"), topography.get("preferred_aspect_ids", []), catalogs, "aspects")}
            </div>
          </div>
          {render_topography_learned_comparison(learned_model, topography)}
          {render_topography_learned_comparison(learned_model, topography, value_mode="emerging")}
        </div>
      </article>
    """
    phenology_panel = f"""
      <article class="profile-section-card">
        <div class="parameter-card-heading">
          <h2>{icon("phenology")} {html.escape(ui_label("ui.phenology"))}</h2>
        </div>
        <div class="parameter-comparison-layout">
          <div class="profile-subsection parameter-focus-subsection parameter-aligned-column parameter-phenology-column">
            <div class="parameter-comparison-section parameter-section-summary parameter-profile-section"></div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("ui.main_months"))}</h4>
              {main_months_control}
            </div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("ui.secondary_months"))}</h4>
              {secondary_months_control}
            </div>
            <div class="parameter-comparison-section parameter-profile-section">
              <h4>{html.escape(ui_label("ui.season_patterns"))}</h4>
              {form_catalog_toggles("season_pattern_ids", ui_label("ui.season_patterns"), phenology.get("season_pattern_ids", []), catalogs, "season_patterns")}
            </div>
            {f'<div class="parameter-comparison-section parameter-profile-section">{delay_fields}</div>' if delay_fields else ""}
          </div>
          {render_phenology_learned_comparison(phenology, observations_payload, species_id, catalogs)}
          {render_phenology_learned_comparison(phenology, observations_payload, species_id, catalogs, value_mode="emerging")}
        </div>
      </article>
    """
    climate_panel = "" if v0_mode else f"""
      <div class="parameter-climate-stack">
        {climate_card}
        {scoring_card}
      </div>
    """
    return f"""
    <section class="card profile-section-screen parameters-screen">
      {render_selected_species_header(profile, ui_label("ui.parameters"), profiles=profiles, search=search, section_key="parameters", profile_view=profile_view, parameter_view=parameter_view, compact=True)}
      {render_parameter_tabs(parameter_view, species_id, search, profile_view)}
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='parameters', profile_view=profile_view, parameter_view=parameter_view), quote=True)}" onsubmit="return confirm('Save parameter changes for this species and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_parameters">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
        <input type="hidden" name="parameter_view" value="{html.escape(parameter_view, quote=True)}">
        <div class="profile-parameters-grid parameter-tabbed-grid{' v0' if v0_mode else ''}">
          {parameter_panel("habitat", habitat_panel)}
          {parameter_panel("soils", soils_panel)}
          {parameter_panel("topography", topography_panel)}
          {parameter_panel("phenology", phenology_panel)}
          {parameter_panel("climate", climate_panel) if not v0_mode else ""}
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


def render_calibration_section(
    profile: dict[str, object] | None,
    profiles: list[dict[str, object]] | None = None,
    search: str = "",
) -> str:
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
      {render_selected_species_header(profile, ui_label("ui.calibration"), profiles=profiles, search=search, section_key="calibration")}
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


def observation_context_inputs(
    filters: dict[str, str] | None,
    *,
    selected_species_id: str = "",
    archive_open: bool = False,
    override_obs_id: str = "",
) -> str:
    """Render hidden inputs that preserve observation filters across POST actions."""
    fields = []
    if selected_species_id:
        fields.append(f'<input type="hidden" name="return_selected_species_id" value="{html.escape(selected_species_id, quote=True)}">')
    for key in ("date_from", "date_to", "result", "validation", "obs_q", "obs_species", "sort", "dir"):
        value = observation_filter_value(filters, key)
        if value:
            fields.append(
                f'<input type="hidden" name="return_{html.escape(key, quote=True)}" value="{html.escape(value, quote=True)}">'
            )
    obs_id = override_obs_id or observation_filter_value(filters, "obs_id")
    if obs_id:
        fields.append(f'<input type="hidden" name="return_obs_id" value="{html.escape(obs_id, quote=True)}">')
    if archive_open:
        fields.append('<input type="hidden" name="return_archive_open" value="1">')
    return "".join(fields)


def observation_sort_url(
    selected_species_id: str,
    search: str,
    filters: dict[str, str] | None,
    key: str,
) -> str:
    """Return a query URL that preserves observation filters and toggles a sort column."""
    current_sort = observation_filter_value(filters, "sort") or "observed_at"
    current_dir = observation_filter_value(filters, "dir") or "desc"
    next_dir = "asc" if current_sort == key and current_dir == "desc" else "desc"
    params = {"section": "observations", "sort": key, "dir": next_dir}
    if selected_species_id:
        params["id"] = selected_species_id
    if search:
        params["q"] = search
    for filter_key in ("date_from", "date_to", "result", "validation", "obs_q", "obs_species", "obs_id"):
        value = observation_filter_value(filters, filter_key)
        if value:
            params[filter_key] = value
    return "?" + urlencode(params)


def observation_select_url(
    selected_species_id: str,
    search: str,
    filters: dict[str, str] | None,
    observation_id: str,
) -> str:
    """Return a query URL that selects one observation row without losing filters."""
    params = {"section": "observations", "obs_id": observation_id}
    if selected_species_id:
        params["id"] = selected_species_id
    if search:
        params["q"] = search
    for filter_key in ("date_from", "date_to", "result", "validation", "obs_q", "obs_species", "sort", "dir"):
        value = observation_filter_value(filters, filter_key)
        if value:
            params[filter_key] = value
    return "?" + urlencode(params) + "#observation-detail"


def observation_duplicate_url(
    selected_species_id: str,
    search: str,
    filters: dict[str, str] | None,
    observation_id: str,
) -> str:
    """Return a query URL that opens an unsaved duplicate observation template."""
    params = {"section": "observations", "duplicate_from": observation_id}
    if selected_species_id:
        params["id"] = selected_species_id
    if search:
        params["q"] = search
    for filter_key in ("date_from", "date_to", "result", "validation", "obs_q", "obs_species", "sort", "dir", "obs_id"):
        value = observation_filter_value(filters, filter_key)
        if value:
            params[filter_key] = value
    return "?" + urlencode(params) + "#duplicate-observation"


def observation_sort_header(
    label: str,
    key: str,
    selected_species_id: str,
    search: str,
    filters: dict[str, str] | None,
) -> str:
    """Render a sortable observation table header."""
    current_sort = observation_filter_value(filters, "sort") or "observed_at"
    current_dir = observation_filter_value(filters, "dir") or "desc"
    marker = " ↓" if current_sort == key and current_dir == "desc" else " ↑" if current_sort == key else ""
    href = observation_sort_url(selected_species_id, search, filters, key)
    return f'<a class="table-sort-link" href="{html.escape(href, quote=True)}">{html.escape(label + marker)}</a>'


def filtered_observation_rows(
    rows: list[dict[str, object]],
    selected_species_id: str,
    filters: dict[str, str] | None,
) -> list[dict[str, object]]:
    """Apply the visible observation filters used by the maintenance screen."""
    species_filter = observation_filter_value(filters, "obs_species")
    date_from = observation_filter_value(filters, "date_from")
    date_to = observation_filter_value(filters, "date_to")
    result = observation_filter_value(filters, "result")
    validation = observation_filter_value(filters, "validation")
    text = observation_filter_value(filters, "obs_q").lower()
    visible_rows = rows
    if species_filter == "__all__":
        pass
    elif species_filter:
        visible_rows = [row for row in visible_rows if str(row.get("species_id", "")) == species_filter]
    elif selected_species_id:
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
    *,
    selected_species_id: str = "",
    search: str = "",
    filters: dict[str, str] | None = None,
    sort_key: str = "observed_at",
    sort_dir: str = "desc",
) -> str:
    """Render the observation list with enough columns for field calibration review."""
    def sort_value(row: dict[str, object]) -> object:
        location = row.get("location") if isinstance(row.get("location"), dict) else {}
        altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        observer = row.get("observer") if isinstance(row.get("observer"), dict) else {}
        if sort_key == "species":
            return species_labels.get(str(row.get("species_id", "")), str(row.get("species_id", ""))).lower()
        if sort_key == "coordinates":
            return f"{location.get('lat', '')},{location.get('lon', '')}" if isinstance(location, dict) else ""
        if sort_key == "altitude":
            value = altitude.get("meters") if isinstance(altitude, dict) else None
            return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else -99999.0
        if sort_key == "abundance":
            return observation_catalog_label(catalogs, "observation_flush_abundance", row.get("flush_abundance")).lower()
        if sort_key == "observer":
            return str(observer.get("name", "") if isinstance(observer, dict) else "").lower()
        if sort_key == "source":
            return str(source.get("label", source.get("type", "")) if isinstance(source, dict) else "").lower()
        if sort_key == "validation":
            return observation_catalog_label(catalogs, "observation_validation_statuses", row.get("validation_status")).lower()
        if sort_key == "use":
            return observation_catalog_label(catalogs, "observation_calibration_uses", row.get("calibration_use")).lower()
        return str(row.get("observed_at", ""))

    visible_rows = sorted(rows, key=sort_value, reverse=sort_dir != "asc")
    if not visible_rows:
        return f'<tr><td colspan="10">{html.escape(ui_label("ui.no_observations_filter"))}</td></tr>'

    body = []
    selected_observation_id = observation_filter_value(filters, "obs_id")
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
        coordinates = observation_coordinates_html(row, precision=5)
        altitude_text = "-"
        if isinstance(altitude, dict) and altitude.get("meters") is not None:
            altitude_text = f'{round(float(altitude.get("meters")))} m'
        observation_id = str(row.get("observation_id", ""))
        selected_class = " selected" if observation_id and observation_id == selected_observation_id else ""
        select_href = observation_select_url(selected_species_id, search, filters, observation_id) if observation_id else "#observation-detail"
        duplicate_href = observation_duplicate_url(selected_species_id, search, filters, observation_id) if observation_id else "#duplicate-observation"
        archive_context_inputs = observation_context_inputs(filters, selected_species_id=selected_species_id, archive_open=True, override_obs_id="")
        body.append(
            f'<tr class="observation-row{selected_class}" data-observation-select data-observation-href="{html.escape(select_href, quote=True)}" onclick="selectObservationRow(this)">'
            f"<td>{html.escape(str(row.get('observed_at', '-')))}</td>"
            f"<td><strong>{html.escape(species_labels.get(species_id, species_id))}</strong></td>"
            f"<td>{coordinates}</td>"
            f"<td>{html.escape(altitude_text)}</td>"
            f"<td>{html.escape(abundance)}</td>"
            f"<td>{html.escape(str(observer.get('name', '-') or '-') if isinstance(observer, dict) else '-')}</td>"
            f"<td>{html.escape(str(source.get('label', source.get('type', '-')) or '-') if isinstance(source, dict) else '-')}</td>"
            f"<td>{observation_badge(validation, validation_tone)}</td>"
            f"<td>{observation_badge(calibration_use, use_tone)}</td>"
            "<td class=\"observation-row-actions\">"
            f"<a class=\"button-link compact\" href=\"#edit-observation-{html.escape(observation_id, quote=True)}\" onclick=\"event.stopPropagation()\">{html.escape(ui_label('ui.edit'))}</a>"
            f"<a class=\"button-link compact\" href=\"{html.escape(duplicate_href, quote=True)}\" onclick=\"event.stopPropagation()\">{html.escape(ui_label('ui.duplicate'))}</a>"
            "<form method=\"post\" action=\"\" onclick=\"event.stopPropagation()\" onsubmit=\"return confirm('Archive this observation?')\">"
            "<input type=\"hidden\" name=\"profile_action\" value=\"archive_observation\">"
            f"{archive_context_inputs}"
            f"<input type=\"hidden\" name=\"species_id\" value=\"{html.escape(species_id, quote=True)}\">"
            f"<input type=\"hidden\" name=\"observation_id\" value=\"{html.escape(observation_id, quote=True)}\">"
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
    *,
    selected_observation_id: str = "",
) -> str:
    """Render the most recent observation detail panel."""
    visible_rows = sorted(rows, key=lambda row: str(row.get("observed_at", "")), reverse=True)
    if not visible_rows:
        return """
        <h2 id="observation-detail">""" + html.escape(ui_label("ui.observation_detail")) + """</h2>
        <p class="meta">""" + html.escape(ui_label("ui.select_or_create_observation")) + """</p>
        """
    row = next(
        (
            item
            for item in visible_rows
            if selected_observation_id and str(item.get("observation_id", "")) == selected_observation_id
        ),
        visible_rows[0],
    )
    location = row.get("location") if isinstance(row.get("location"), dict) else {}
    altitude = row.get("altitude") if isinstance(row.get("altitude"), dict) else {}
    site_context = row.get("site_context") if isinstance(row.get("site_context"), dict) else {}
    species_id = str(row.get("species_id", ""))
    coords = observation_coordinates_html(row, precision=14)
    altitude_text = "-"
    if isinstance(altitude, dict) and altitude.get("meters") is not None:
        altitude_text = f'{round(float(altitude.get("meters")))} m'
    photos_html = render_observation_photo_strip(row, extra_class="observation-detail-photo-strip", limit=1)
    species_text = species_labels.get(species_id, species_id)
    flush_text = observation_catalog_label(catalogs, "observation_flush_abundance", row.get("flush_abundance"))
    summary_html = f"""
    <div class="observation-detail-summary">
      {photos_html or '<div class="observation-detail-photo-placeholder"></div>'}
      <div class="observation-detail-summary-fields">
        <div><strong>{html.escape(species_text)}</strong></div>
        <div><span>ID:</span> <strong>{html.escape(str(row.get("observation_id", "-")))}</strong></div>
        <div class="observation-detail-coordinate">{coords}</div>
        <div><span>Altitud:</span> <strong>{html.escape(altitude_text)}</strong></div>
        <div><span>Florada:</span> <strong>{html.escape(flush_text)}</strong></div>
      </div>
    </div>
    """
    return f"""
    <h2 id="observation-detail">{html.escape(ui_label("ui.observation_detail"))}</h2>
    {summary_html}
    {value_row(ui_label("source_quality"), row.get("source_quality", "-"))}
    {value_row(ui_label("ui.calibration_weight"), f"{observation_weight(catalogs, row):.2f}")}
    {value_row(ui_label("site_context.observed_host_ids"), observed_host_names(catalogs, site_context))}
    {value_row(ui_label("site_context.observed_forest_type_ids"), observation_catalog_names(catalogs, "forest_types", site_context.get("observed_forest_type_ids") if isinstance(site_context, dict) else []))}
    {value_row(ui_label("site_context.observed_soil_tendency_ids"), observation_catalog_names(catalogs, "soil_types", site_context.get("observed_soil_tendency_ids") if isinstance(site_context, dict) else []))}
    {value_row(ui_label("site_context.observed_habitat_feature_ids"), observation_catalog_names(catalogs, "habitat_features", site_context.get("observed_habitat_feature_ids") if isinstance(site_context, dict) else []))}
    {value_row(ui_label("site_context.observed_aspect_ids"), observation_catalog_names(catalogs, "aspects", site_context.get("observed_aspect_ids") if isinstance(site_context, dict) else []))}
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
    filters: dict[str, str] | None = None,
    allow_exif_images: bool = False,
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
    location_source = str(location.get("source", "") if isinstance(location, dict) else "")
    altitude_value = "" if not isinstance(altitude, dict) or altitude.get("meters") is None else str(altitude.get("meters"))
    map_action = ""
    if observation_id and observation_location(row):
        map_action = (
            f'<a class="button-link" href="#{html.escape(observation_map_modal_id(observation_id), quote=True)}">'
            f'{html.escape(ui_label("ui.evidence_map"))}</a>'
        )
    form_enctype = ' enctype="multipart/form-data"' if action == "update_observation" or allow_exif_images else ""
    context_inputs = observation_context_inputs(
        filters,
        selected_species_id=selected_species_id,
        override_obs_id=observation_id,
    )
    exif_edit_fields = ""
    if action == "update_observation" or allow_exif_images:
        exif_edit_fields = f"""
        <div class="catalog-alert">
          <strong>{html.escape(ui_label("ui.update_from_exif_images"))}</strong><br>
          {html.escape(ui_label("ui.update_from_exif_images_help"))}
          <div class="admin-field wide exif-edit-upload">
            <label>{html.escape(ui_label("ui.exif_images"))}</label>
            <input name="observation_exif_images" type="file" accept="image/jpeg,image/heic,image/heif" multiple webkitdirectory directory>
          </div>
        </div>
        """
    return f"""
    <div id="{html.escape(modal_id, quote=True)}" class="modal-layer">
      <a class="modal-backdrop" href="#" aria-label="{html.escape(ui_label("ui.cancel"), quote=True)}"></a>
      <form class="modal-card modal-card-wide observation-form" method="post" action=""{form_enctype}>
        <input type="hidden" name="profile_action" value="{html.escape(action, quote=True)}">
        {context_inputs}
        {f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">' if observation_id else ""}
        <header class="modal-head">
          <div>
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(ui_label("ui.observation_form_help"))}</p>
          </div>
          <a class="button-link" href="#">{html.escape(ui_label("ui.cancel"))}</a>
        </header>
        {f'<div class="catalog-alert error"><strong>{html.escape(ui_label("ui.observation_not_saved"))}</strong><br>{html.escape(form_message.replace("Observation was not saved: ", ""))}</div>' if form_message else ""}
        <div class="observation-field-groups">
          <section class="observation-field-group observation-record-group">
            <h3>{html.escape(ui_label("ui.observation_group_record"))}</h3>
            <div class="observation-group-grid record">
              <div class="admin-field wide"><label>{html.escape(ui_label("species_id"))}</label><select name="observation_species_id" required>{species_select_options(profiles, current_species_id)}</select></div>
              <div class="admin-field compact"><label>{html.escape(ui_label("observed_at"))}</label><input name="observed_at" type="date" value="{html.escape(str(row.get("observed_at", "")), quote=True)}" onchange="this.blur()" required></div>
              <div class="admin-field"><label>{html.escape(ui_label("flush_abundance"))}</label><select name="flush_abundance" required>{catalog_select_options(catalogs, "observation_flush_abundance", str(row.get("flush_abundance", "") or "normal"))}</select></div>
              <div class="admin-field compact"><label>{html.escape(ui_label("source_quality"))}</label><input name="source_quality" type="number" min="0" max="1" step="0.05" value="{html.escape(str(row.get("source_quality", 0.75)), quote=True)}" required></div>
            </div>
          </section>
          <section class="observation-field-group observation-location-group">
            <h3>{html.escape(ui_label("ui.observation_group_location"))}</h3>
            <div class="observation-group-grid location">
              <div class="admin-field location-input"><label>{html.escape(ui_label("location.input"))}</label><input name="location_input" value="{html.escape(location_input, quote=True)}" placeholder="41.38740, 2.16860 or Google Maps URL"></div>
              <div class="admin-field"><label>{html.escape(ui_label("location.lat"))}</label><input name="location_lat" type="number" step="any" value="{html.escape(lat_value, quote=True)}"></div>
              <div class="admin-field"><label>{html.escape(ui_label("location.lon"))}</label><input name="location_lon" type="number" step="any" value="{html.escape(lon_value, quote=True)}"></div>
              <div class="admin-field compact"><label>{html.escape(ui_label("altitude.meters"))}</label><input name="altitude_m" type="number" step="1" value="{html.escape(altitude_value, quote=True)}"></div>
              <div class="admin-field"><label>{html.escape(ui_label("catalog_group.observation_location_sources"))}</label><select name="location_source">{catalog_select_options(catalogs, "observation_location_sources", location_source, ui_label("ui.not_informed"))}</select></div>
              <div class="admin-field"><label>{html.escape(ui_label("altitude.source"))}</label><select name="altitude_source">{catalog_select_options(catalogs, "observation_altitude_sources", str(altitude.get("source", "") if isinstance(altitude, dict) else ""), ui_label("ui.not_informed"))}</select></div>
            </div>
          </section>
          <section class="observation-field-group observation-validation-group">
            <h3>{html.escape(ui_label("ui.observation_group_validation"))}</h3>
            <div class="observation-group-grid validation">
              <div class="admin-field"><label>{html.escape(ui_label("validation_status"))}</label><select name="validation_status" required>{catalog_select_options(catalogs, "observation_validation_statuses", str(row.get("validation_status", "") or "draft"))}</select></div>
              <div class="admin-field"><label>{html.escape(ui_label("calibration_use"))}</label><select name="calibration_use" required>{catalog_select_options(catalogs, "observation_calibration_uses", str(row.get("calibration_use", "") or "review"))}</select></div>
              <div class="admin-field"><label>{html.escape(ui_label("calibration_exclusion_reason"))}</label><select name="calibration_exclusion_reason">{catalog_select_options(catalogs, "observation_exclusion_reasons", str(row.get("calibration_exclusion_reason", "") or ""), ui_label("ui.none"))}</select></div>
            </div>
          </section>
          <section class="observation-field-group observation-source-group">
            <h3>{html.escape(ui_label("ui.observation_group_source"))}</h3>
            <div class="observation-group-grid source">
              <div class="admin-field"><label>{html.escape(ui_label("observer.name"))}</label><input name="observer_name" value="{html.escape(str(observer.get("name", "") if isinstance(observer, dict) else ""), quote=True)}"></div>
              <div class="admin-field"><label>{html.escape(ui_label("observer.expertise"))}</label><select name="observer_expertise">{catalog_select_options(catalogs, "observer_expertise_levels", str(observer.get("expertise", "") if isinstance(observer, dict) else "") or "unknown")}</select></div>
              <div class="admin-field"><label>{html.escape(ui_label("source.type"))}</label><select name="source_type">{catalog_select_options(catalogs, "observation_source_types", str(source.get("type", "") if isinstance(source, dict) else "") or "personal_observation")}</select></div>
              <div class="admin-field"><label>{html.escape(ui_label("source.label"))}</label><input name="source_label" value="{html.escape(str(source.get("label", "") if isinstance(source, dict) else ""), quote=True)}"></div>
              <div class="admin-field source-url"><label>{html.escape(ui_label("source.url"))}</label><input name="source_url" type="url" value="{html.escape(str(source.get("url", "") if isinstance(source, dict) else ""), quote=True)}"></div>
            </div>
          </section>
        </div>
        <div class="profile-grid full">
          <div class="admin-field wide">
            <label>{html.escape(ui_label("site_context.observed_host_ids"))}</label>
            <div class="month-toggle-grid host-toggle-grid">{observed_host_toggles(catalogs, site_context.get("observed_host_ids") if isinstance(site_context, dict) else [])}</div>
            <span class="meta">{html.escape(ui_label("ui.observed_hosts_help"))}</span>
          </div>
        </div>
        <div class="profile-grid two observation-context-grid">
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_forest_type_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "forest_types", "observed_forest_type_ids", site_context.get("observed_forest_type_ids") if isinstance(site_context, dict) else [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_soil_tendency_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "soil_types", "observed_soil_tendency_ids", site_context.get("observed_soil_tendency_ids") if isinstance(site_context, dict) else [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_habitat_feature_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "habitat_features", "observed_habitat_feature_ids", site_context.get("observed_habitat_feature_ids") if isinstance(site_context, dict) else [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_aspect_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "aspects", "observed_aspect_ids", site_context.get("observed_aspect_ids") if isinstance(site_context, dict) else [])}</div>
          </div>
        </div>
        <div class="profile-grid two">
          {form_textarea("habitat_notes", ui_label("site_context.habitat_notes"), site_context.get("habitat_notes", "") if isinstance(site_context, dict) else "", rows=3)}
          {form_textarea("host_notes", ui_label("site_context.host_notes"), site_context.get("host_notes", "") if isinstance(site_context, dict) else "", rows=3)}
        </div>
        {exif_edit_fields}
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.save_observation"))}</button>
          {map_action}
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
    filters: dict[str, str] | None = None,
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
        filters=filters,
        allow_exif_images=True,
    )


def observation_duplicate_template_row(row: dict[str, object] | None) -> dict[str, object]:
    """Return an unsaved observation template copied from an existing row."""
    template = json.loads(json.dumps(row if isinstance(row, dict) else {}))
    if isinstance(template, dict):
        template.pop("observation_id", None)
        template.pop("metadata", None)
    return template if isinstance(template, dict) else {}


def render_observation_duplicate_form(
    rows: list[dict[str, object]],
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    selected_species_id: str,
    filters: dict[str, str] | None = None,
) -> str:
    """Render an unsaved duplicate observation modal when requested by query string."""
    duplicate_from = observation_filter_value(filters, "duplicate_from")
    if not duplicate_from:
        return ""
    source = next((row for row in rows if str(row.get("observation_id", "")) == duplicate_from), None)
    if not source:
        return ""
    return render_observation_form_modal(
        profiles,
        catalogs,
        observation_duplicate_template_row(source),
        modal_id="duplicate-observation",
        action="create_observation",
        title=f"{ui_label('ui.duplicate')} {duplicate_from}",
        selected_species_id=selected_species_id,
        filters=filters,
        allow_exif_images=True,
    )


def render_observation_exif_import_form(
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    selected_species_id: str,
    filters: dict[str, str] | None = None,
) -> str:
    """Render the common-field template used by EXIF image batch imports."""
    return f"""
    <div id="import-observation-exif" class="modal-layer">
      <a class="modal-backdrop" href="#" aria-label="{html.escape(ui_label("ui.cancel"), quote=True)}"></a>
      <form class="modal-card modal-card-wide observation-form" method="post" action="" enctype="multipart/form-data">
        <input type="hidden" name="profile_action" value="import_observation_exif_images">
        {observation_context_inputs(filters, selected_species_id=selected_species_id)}
        <header class="modal-head">
          <div>
            <h2>{html.escape(ui_label("ui.import_exif_images"))}</h2>
            <p>{html.escape(ui_label("ui.import_exif_images_help"))}</p>
          </div>
          <a class="button-link" href="#">{html.escape(ui_label("ui.cancel"))}</a>
        </header>
        <div class="profile-grid four">
          <div class="admin-field"><label>{html.escape(ui_label("observer.name"))}</label><input name="observer_name"></div>
          <div class="admin-field"><label>{html.escape(ui_label("observer.expertise"))}</label><select name="observer_expertise">{catalog_select_options(catalogs, "observer_expertise_levels", "unknown")}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("source_quality"))}</label><input name="source_quality" type="number" min="0" max="1" step="0.05" value="0.9" required></div>
          <div class="admin-field"><label>{html.escape(ui_label("flush_abundance"))}</label><select name="flush_abundance" required>{catalog_select_options(catalogs, "observation_flush_abundance", "normal")}</select></div>
        </div>
        <div class="profile-grid three">
          <div class="admin-field"><label>{html.escape(ui_label("validation_status"))}</label><select name="validation_status" required>{catalog_select_options(catalogs, "observation_validation_statuses", "draft")}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("species_id"))}</label><select name="observation_species_id" required>{species_select_options(profiles, selected_species_id)}</select></div>
          <div class="admin-field"><label>{html.escape(ui_label("calibration_use"))}</label><select name="calibration_use" required>{catalog_select_options(catalogs, "observation_calibration_uses", "review")}</select></div>
        </div>
        <div class="profile-grid two">
          <div class="admin-field wide"><label>{html.escape(ui_label("ui.exif_images"))}</label><input name="exif_images" type="file" accept="image/jpeg,image/heic,image/heif" multiple webkitdirectory directory required></div>
          <div class="admin-field wide"><label>{html.escape(ui_label("source.notes"))}</label><input name="source_notes"></div>
        </div>
        <div class="profile-grid full">
          <div class="admin-field wide">
            <label>{html.escape(ui_label("site_context.observed_host_ids"))}</label>
            <div class="month-toggle-grid host-toggle-grid">{observed_host_toggles(catalogs, [])}</div>
            <span class="meta">{html.escape(ui_label("ui.observed_hosts_help"))}</span>
          </div>
        </div>
        <div class="profile-grid two observation-context-grid">
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_forest_type_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "forest_types", "observed_forest_type_ids", [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_soil_tendency_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "soil_types", "observed_soil_tendency_ids", [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_habitat_feature_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "habitat_features", "observed_habitat_feature_ids", [])}</div>
          </div>
          <div class="admin-field wide catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("site_context.observed_aspect_ids"))}</span>
            <div class="catalog-toggle-grid">{observation_catalog_toggles(catalogs, "aspects", "observed_aspect_ids", [])}</div>
          </div>
        </div>
        <div class="catalog-alert">
          <strong>{html.escape(ui_label("ui.exif_filled_fields"))}</strong><br>
          {html.escape(ui_label("ui.exif_filled_fields_help"))}
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">{html.escape(ui_label("ui.import_exif_images"))}</button>
        </div>
      </form>
    </div>
    """


def render_observation_edit_modals(
    rows: list[dict[str, object]],
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    selected_species_id: str,
    filters: dict[str, str] | None = None,
) -> str:
    """Render edit modals for active observations in the current filter."""
    visible_rows = rows
    return "".join(
        render_observation_form_modal(
            profiles,
            catalogs,
            row,
            modal_id=f"edit-observation-{str(row.get('observation_id', ''))}",
            action="update_observation",
            title=f"{ui_label('ui.edit_observation')} {str(row.get('observation_id', ''))}",
            selected_species_id=selected_species_id,
            filters=filters,
        )
        for row in visible_rows
        if row.get("observation_id")
    )


def render_observation_map_modals(
    rows: list[dict[str, object]],
    selected_species_id: str = "",
    search: str = "",
    filters: dict[str, str] | None = None,
) -> str:
    """Render map modals for visible observations with coordinates."""
    seen: set[str] = set()
    modals = []
    for row in rows:
        observation_id = str(row.get("observation_id", "") or "")
        if not observation_id or observation_id in seen or not observation_location(row):
            continue
        seen.add(observation_id)
        modals.append(render_observation_map_modal(row, selected_species_id, search, filters))
    return "".join(modals)


def render_observation_photo_modals(rows: list[dict[str, object]]) -> str:
    """Render photo viewer modals for visible observation media."""
    seen: set[str] = set()
    modals = []
    for row in rows:
        observation_id = str(row.get("observation_id", "") or "")
        if not observation_id:
            continue
        for index, media in observation_photo_media(row):
            modal_id = observation_photo_modal_id(observation_id, media, index)
            if modal_id in seen:
                continue
            seen.add(modal_id)
            modals.append(render_observation_photo_modal(row, media, index))
            modals.append(render_observation_raw_exif_modal(row, media, index))
    return "".join(modals)


def render_archived_observations_panel(
    archived_payload: dict[str, object] | None,
    species_labels: dict[str, str],
    selected_species_id: str,
    filters: dict[str, str] | None = None,
) -> str:
    """Render archived observation restore/delete controls."""
    archived = observations_from_payload(archived_payload)
    species_filter = observation_filter_value(filters, "obs_species")
    if species_filter == "__all__":
        pass
    elif species_filter:
        archived = [row for row in archived if str(row.get("species_id", "")) == species_filter]
    elif selected_species_id:
        archived = [row for row in archived if str(row.get("species_id", "")) == selected_species_id]
    open_attr = " open" if observation_filter_value(filters, "archive_open") == "1" else ""
    if not archived:
        return f'<details id="archived-observations" class="profile-section-card"{open_attr}><summary><strong>{html.escape(ui_label("ui.archived_observations"))}</strong></summary><p class="meta">{html.escape(ui_label("ui.no_archived_observations"))}</p></details>'
    rows = []
    for row in sorted(archived, key=lambda item: str(item.get("observed_at", "")), reverse=True):
        observation_id = str(row.get("observation_id", ""))
        species_id = str(row.get("species_id", ""))
        context_inputs = observation_context_inputs(filters, selected_species_id=selected_species_id, archive_open=True)
        rows.append(
            '<div class="archived-species-row">'
            f'<div><strong>{html.escape(observation_id)}</strong><br><span class="meta">{html.escape(str(row.get("observed_at", "-")))} · {html.escape(species_labels.get(species_id, species_id))}</span></div>'
            '<div class="archived-species-actions">'
            '<form method="post" action="">'
            '<input type="hidden" name="profile_action" value="restore_observation">'
            f'{context_inputs}'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">'
            f'<button class="secondary" type="submit">{html.escape(ui_label("ui.restore"))}</button>'
            '</form>'
            '<form method="post" action="" onsubmit="return confirm(\'Delete this archived observation permanently?\') && confirm(\'This action cannot be undone. The archived copy will be removed permanently.\')">'
            '<input type="hidden" name="profile_action" value="delete_archived_observation">'
            f'{context_inputs}'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">'
            f'<input type="hidden" name="delete_confirm_id" value="{html.escape(observation_id, quote=True)}">'
            f'<button class="danger" type="submit">{html.escape(ui_label("ui.delete_permanently"))}</button>'
            '</form>'
            '</div></div>'
        )
    return f'<details id="archived-observations" class="profile-section-card"{open_attr}><summary><strong>{html.escape(ui_label("ui.archived_observations"))}</strong></summary><div class="archived-observations-list">' + "".join(rows) + '</div></details>'


def observation_has_coordinates(row: dict[str, object]) -> bool:
    location = row.get("location")
    if not isinstance(location, dict):
        return False
    return location.get("lat") not in (None, "") and location.get("lon") not in (None, "")


def gis_layer_property(layer_result: dict[str, object], *keys: str) -> str:
    properties = layer_result.get("properties")
    if not isinstance(properties, dict):
        return "-"
    for key in keys:
        value = properties.get(key)
        if value not in (None, ""):
            return str(value)
    return "-"


def gis_layer_properties_join(layer_result: dict[str, object], *keys: str) -> str:
    properties = layer_result.get("properties")
    if not isinstance(properties, dict):
        return "-"
    values = []
    for key in keys:
        value = properties.get(key)
        if value not in (None, ""):
            text = str(value)
            if text not in values:
                values.append(text)
    return " · ".join(values) if values else "-"


def gis_layer_mapped_ids(layer_result: dict[str, object], *keys: str) -> str:
    mapped = layer_result.get("mapped")
    if not isinstance(mapped, dict):
        return "-"
    values = []
    for key in keys:
        raw_values = mapped.get(key)
        if not isinstance(raw_values, list):
            continue
        for value in raw_values:
            text = str(value)
            if text and text not in values:
                values.append(text)
    return " · ".join(values) if values else "-"


def gis_context_v0_value(context: dict[str, object], key: str, limit: int = 4) -> str:
    """Return compact v0 GIS context IDs for table display."""
    raw_values = context.get(key)
    if not isinstance(raw_values, list) or not raw_values:
        return "-"
    values = [str(value) for value in raw_values if str(value or "").strip()]
    if not values:
        return "-"
    suffix = f" +{len(values) - limit}" if len(values) > limit else ""
    return ", ".join(values[:limit]) + suffix


def render_gis_context_v0_summary(context: object) -> str:
    """Render the predictor-v0 GIS projection for one observation."""
    if not isinstance(context, dict):
        return '<span class="meta">sin contexto v0</span>'
    parts = [
        ("Hosts", gis_context_v0_value(context, "host_ids")),
        ("Bosque", gis_context_v0_value(context, "forest_type_ids")),
        ("Suelo", gis_context_v0_value(context, "soil_tendency_ids")),
        ("Habitat", gis_context_v0_value(context, "habitat_feature_ids")),
    ]
    altitude = context.get("altitude_m")
    if altitude not in (None, ""):
        parts.append(("Alt.", f"{altitude} m"))
    return (
        '<span class="gis-v0-summary">'
        + "".join(
            f'<span><strong>{html.escape(label)}:</strong> {html.escape(value)}</span>'
            for label, value in parts
            if value != "-"
        )
        + ('<span class="meta">sin senales v0</span>' if all(value == "-" for _, value in parts) else "")
        + "</span>"
    )


def render_gis_unmapped_candidates(rows: list[dict[str, object]]) -> str:
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        layers = row.get("layers")
        if not isinstance(layers, dict):
            continue
        for layer_result in layers.values():
            if not isinstance(layer_result, dict):
                continue
            mapped = layer_result.get("mapped")
            if not isinstance(mapped, dict):
                continue
            unmapped_values = mapped.get("unmapped_values")
            if not isinstance(unmapped_values, list):
                continue
            for candidate in unmapped_values:
                if not isinstance(candidate, dict):
                    continue
                source_id = str(candidate.get("source_id", "") or "")
                field = str(candidate.get("field", "") or "")
                raw_value = str(candidate.get("raw_value", "") or "")
                key = (source_id, field, raw_value)
                if not source_id or not field or not raw_value or key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
    if not candidates:
        return ""
    items = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        source_id = str(candidate.get("source_id", "") or "")
        field = str(candidate.get("field", "") or "")
        raw_value = str(candidate.get("raw_value", "") or "")
        if not source_id or not field or not raw_value:
            continue
        items.append(
            "<li>"
            f"<strong>{html.escape(source_id)}.{html.escape(field)}</strong>: "
            f"<span>{html.escape(raw_value)}</span>"
            "</li>"
        )
    if not items:
        return ""
    return (
        '<details class="gis-result-details gis-unmapped-candidates" open>'
        '<summary>Valores GIS pendientes de mapping</summary>'
        f'<ul>{"".join(items)}</ul>'
        '</details>'
    )


def gis_layer_status_badge(layer_result: object) -> str:
    if not isinstance(layer_result, dict):
        return observation_badge("-", "warn")
    status = str(layer_result.get("status", "") or "-")
    status_labels = {
        "ok": "ok",
        "missing_layer": "capa no montada",
        "query_error": "error consulta",
        "invalid_json": "error lectura",
        "no_coverage_at_point": "sin cobertura",
        "no_value": "sin valor",
        "no_data": "sin dato",
    }
    tone = "ok" if status == "ok" else "warn"
    return observation_badge(status_labels.get(status, status), tone)


def gis_observation_status_badge(status: object, has_gaps: bool) -> str:
    status_text = str(status or "-")
    labels = {
        "complete": "completa",
        "complete_with_gaps": "con gaps",
        "skipped": "omitida",
        "error": "error",
        "pending": "pendiente",
    }
    return observation_badge(labels.get(status_text, status_text), "ok" if not has_gaps else "warn")


def render_gis_result_summary(
    result: dict[str, object] | None,
    species_labels: dict[str, str],
    selected_species_id: str = "",
) -> str:
    """Render the latest local GIS reconstruction in a compact review table."""
    if not isinstance(result, dict):
        return '<p class="meta">Todavia no hay reconstruccion GIS local. Selecciona observaciones y ejecuta la reconstruccion.</p>'
    rows = result.get("results")
    rows = rows if isinstance(rows, list) else []
    if selected_species_id and selected_species_id != "__all__":
        rows = [
            row for row in rows
            if isinstance(row, dict) and str(row.get("species_id", "") or "") == selected_species_id
        ]
    if not rows:
        return '<p class="meta">La ultima reconstruccion GIS no contiene resultados revisables.</p>'
    table_rows = []
    detail_cards = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        observation_id = str(item.get("observation_id", "") or "")
        species_id = str(item.get("species_id", "") or "")
        layers = item.get("layers")
        layers = layers if isinstance(layers, dict) else {}
        mvc50 = layers.get("mvc50") if isinstance(layers.get("mvc50"), dict) else {}
        geology = layers.get("geology_50000") if isinstance(layers.get("geology_50000"), dict) else {}
        dem = layers.get("dem_5m") if isinstance(layers.get("dem_5m"), dict) else {}
        gis_context_v0 = item.get("gis_context_v0")
        gaps = item.get("gaps")
        gaps = gaps if isinstance(gaps, list) else []
        display_gaps = [str(gap) for gap in gaps if str(gap) != "soil_25000"]
        substrate = gis_layer_property(mvc50, "LLVA_Subst")
        dem_altitude = "-"
        dem_delta = "-"
        if isinstance(dem, dict):
            if dem.get("elevation_m") not in (None, ""):
                dem_altitude = f"{dem.get('elevation_m')} m"
            if dem.get("delta_observed_vs_dem_m") not in (None, ""):
                dem_delta = f"{dem.get('delta_observed_vs_dem_m')} m"
        table_rows.append(
            "<tr>"
            f"<td><span class=\"gis-inline\"><strong>{html.escape(observation_id)}</strong><span class=\"meta\">{html.escape(species_labels.get(species_id, species_id))}</span></span></td>"
            f"<td><span class=\"gis-inline\">{gis_layer_status_badge(mvc50)}<span class=\"gis-inline-text\">{html.escape(gis_layer_properties_join(mvc50, 'LLVA_niv2t', 'LLFISCAT_t'))}</span></span></td>"
            f"<td><span class=\"gis-inline\">{gis_layer_status_badge(mvc50)}<span class=\"gis-inline-text\">{html.escape(substrate)}</span></span></td>"
            f"<td><span class=\"gis-inline\">{gis_layer_status_badge(geology)}<span class=\"gis-inline-text\">{html.escape(gis_layer_property(geology, 'Codi'))} · {html.escape(gis_layer_property(geology, 'Descripcio'))}</span></span></td>"
            f"<td><span class=\"gis-inline\">{gis_layer_status_badge(dem)}<span class=\"gis-inline-text\">{html.escape(dem_altitude)} · delta obs.: {html.escape(dem_delta)}</span></span></td>"
            f"<td>{render_gis_context_v0_summary(gis_context_v0)}</td>"
            f"<td><span class=\"gis-inline\">{gis_observation_status_badge(item.get('status', '-'), bool(display_gaps))}<span class=\"gis-inline-text meta\">{html.escape(', '.join(display_gaps) if display_gaps else 'sin gaps')}</span></span></td>"
            "</tr>"
        )
        detail_lines = []
        for source_id, layer_result in layers.items():
            if source_id == "soil_25000":
                continue
            if not isinstance(layer_result, dict):
                continue
            properties = layer_result.get("properties")
            if isinstance(properties, dict) and properties:
                rendered_properties = "; ".join(
                    f"{key}: {value}" for key, value in properties.items() if value not in (None, "")
                )
                mapped = layer_result.get("mapped")
                if isinstance(mapped, dict):
                    mapped_bits = []
                    for key in (
                        "mapped_host_ids",
                        "mapped_forest_type_ids",
                        "mapped_soil_tendency_ids",
                        "mapped_lithology_ids",
                    ):
                        values = mapped.get(key)
                        if isinstance(values, list) and values:
                            mapped_bits.append(f"{key}: {', '.join(str(value) for value in values)}")
                    unmapped_values = mapped.get("unmapped_values")
                    if isinstance(unmapped_values, list) and unmapped_values:
                        pending = [
                            f"{item.get('field')}: {item.get('raw_value')}"
                            for item in unmapped_values
                            if isinstance(item, dict)
                        ]
                        mapped_bits.append(f"unmapped: {', '.join(pending)}")
                    if mapped_bits:
                        rendered_properties = f"{rendered_properties}; mapped: {'; '.join(mapped_bits)}"
            else:
                scalar_values = {
                    key: value
                    for key, value in layer_result.items()
                    if key not in {"status", "source", "properties"} and value not in (None, "")
                }
                rendered_properties = (
                    "; ".join(f"{key}: {value}" for key, value in scalar_values.items())
                    or str(layer_result.get("message") or layer_result.get("error") or layer_result.get("raw") or "-")
                )
            detail_lines.append(
                f"<li><strong>{html.escape(str(source_id))}</strong>: {gis_layer_status_badge(layer_result)} "
                f"<span>{html.escape(rendered_properties)}</span></li>"
            )
        detail_cards.append(
            f'<details class="gis-result-details"><summary>{html.escape(observation_id)} · valores crudos de capas</summary>'
            f'<div class="gis-result-v0-detail"><strong>Contexto v0:</strong> {render_gis_context_v0_summary(gis_context_v0)}</div>'
            f'<ul>{"".join(detail_lines)}</ul></details>'
        )
    generated_at = str(result.get("generated_at", "") or "")
    qgis_points_path = str(result.get("qgis_points_host_path") or result.get("qgis_points_path") or "")
    qgis_note = (
        f'<br>Revision visual QGIS: <code>{html.escape(qgis_points_path)}</code>'
        if qgis_points_path
        else ""
    )
    return (
        f'<p class="meta">Ultima reconstruccion: {html.escape(generated_at)} · {len(table_rows)} observacion(es). '
        f'Las coordenadas se leen localmente pero no se muestran en esta revision.{qgis_note}</p>'
        '<div class="observations-table-shell gis-results-table"><table>'
        '<thead><tr><th>Observacion</th><th>MVC50</th><th>Sustrato</th><th>Geologia</th><th>DEM</th><th>Contexto v0</th><th>Estado</th></tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody></table></div>'
        f'{render_gis_unmapped_candidates([row for row in rows if isinstance(row, dict)])}'
        '<details class="gis-result-details gis-result-detail-section">'
        f'<summary>{html.escape(ui_label("ui.gis_last_reconstruction_observations"))}</summary>'
        f'<div class="gis-result-detail-list">{"".join(detail_cards)}</div>'
        '</details>'
    )


def render_observation_gis_lab(
    filtered_rows: list[dict[str, object]],
    species_labels: dict[str, str],
    selected_species_id: str,
    search: str,
    filters: dict[str, str] | None,
    result: dict[str, object] | None = None,
) -> str:
    """Render the local GIS reconstruction lab for explicitly selected observations."""
    candidate_rows = sorted(
        [row for row in filtered_rows if observation_has_coordinates(row)],
        key=lambda row: str(row.get("observation_id", "") or ""),
    )
    selected_ids = set()
    if isinstance(result, dict):
        raw_ids = result.get("selected_observation_ids")
        if isinstance(raw_ids, list):
            selected_ids = {str(item) for item in raw_ids}
    chips = []
    visible_hidden_inputs = []
    for row in candidate_rows:
        observation_id = str(row.get("observation_id", "") or "")
        if not observation_id:
            continue
        visible_hidden_inputs.append(
            f'<input type="hidden" name="gis_visible_observation_ids" value="{html.escape(observation_id, quote=True)}">'
        )
        species_id = str(row.get("species_id", "") or "")
        checked = " checked" if observation_id in selected_ids else ""
        label = f"{row.get('observed_at', '-')} · {species_labels.get(species_id, species_id)} · {row.get('flush_abundance', '-')}"
        chips.append(
            '<label class="catalog-toggle gis-observation-toggle">'
            f'<input type="checkbox" name="gis_observation_ids" value="{html.escape(observation_id, quote=True)}"{checked}>'
            f'<span class="catalog-chip" title="{html.escape(observation_id, quote=True)}">{html.escape(label)}</span>'
            '</label>'
        )
    picker = (
        '<div class="catalog-toggle-grid gis-observation-grid">' + "".join(chips) + "</div>"
        if chips
        else f'<p class="meta">{html.escape(ui_label("ui.rebuild_observation_model_v0_none"))}</p>'
    )
    return f"""
    <details id="gis-reconstruction-lab" class="profile-section-card gis-reconstruction-lab">
      <summary><strong>{icon("topography")} {html.escape(ui_label("ui.rebuild_observation_model_v0_lab"))}</strong></summary>
      <div class="collapsible-section-body">
        <p class="meta">{html.escape(ui_label("ui.rebuild_observation_model_v0_lab_help"))}</p>
        <form method="post" action="#gis-reconstruction-lab" class="gis-lab-form">
          <input type="hidden" name="profile_action" value="rebuild_observation_model_v0">
          {observation_context_inputs(filters, selected_species_id=selected_species_id)}
          {"".join(visible_hidden_inputs)}
          <div class="admin-field catalog-toggle-field">
            <span class="field-label">{html.escape(ui_label("ui.rebuild_observation_model_v0_observations"))}</span>
            {picker}
          </div>
          <div class="profile-action-bar inline">
            <button class="primary profile-primary-action" name="gis_reconstruction_scope" value="selected" {"disabled" if not chips else ""}>{html.escape(ui_label("ui.rebuild_observation_model_v0_selected"))}</button>
            <button class="button-link" name="gis_reconstruction_scope" value="visible" {"disabled" if not chips else ""}>{html.escape(ui_label("ui.rebuild_observation_model_v0_visible"))} ({len(chips)})</button>
          </div>
        </form>
        <div class="gis-lab-results">
          {render_gis_result_summary(result, species_labels, selected_species_id)}
        </div>
      </div>
    </details>
    """


def render_observations_section(
    profile: dict[str, object] | None,
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    observations_payload: dict[str, object] | None,
    archived_observations_payload: dict[str, object] | None,
    search: str = "",
    form_message: str = "",
    filters: dict[str, str] | None = None,
    gis_reconstruction_payload: dict[str, object] | None = None,
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
    sort_key = observation_filter_value(filters, "sort") or "observed_at"
    sort_dir = observation_filter_value(filters, "dir") or "desc"
    selected_observation_id = observation_filter_value(filters, "obs_id")
    species_filter = observation_filter_value(filters, "obs_species") or selected_species_id
    visible_profile = profile
    if species_filter and species_filter != "__all__":
        visible_profile = next((item for item in profiles if str(item.get("species_id", "")) == species_filter), profile)
    species_filter_options = f'<option value="__all__"{" selected" if species_filter == "__all__" else ""}>{html.escape(ui_label("ui.all_species"))}</option>' + "".join(
        f'<option value="{html.escape(str(item.get("species_id", "")), quote=True)}"{" selected" if str(item.get("species_id", "")) == species_filter else ""}>{html.escape(str(item.get("scientific_name", item.get("species_id", ""))))}</option>'
        for item in profiles
        if item.get("species_id")
    )
    return f"""
    <section id="observations-workspace" class="card profile-section-screen observations-screen">
      {render_observation_scope_header(visible_profile, ui_label("ui.observations"), species_filter, profiles=profiles, search=search)}
      <div class="profile-calibration-cards observations-metrics">
        <div class="profile-metric"><span class="label">{icon("metadata")} {html.escape(ui_label("ui.total_observations"))}</span><span class="value">{total}</span></div>
        <div class="profile-metric"><span class="label">{icon("mushroom")} {html.escape(ui_label("ui.positive_present"))}</span><span class="value ok">{positive}</span></div>
        <div class="profile-metric"><span class="label">{icon("scoring")} {html.escape(ui_label("ui.negative_absent"))}</span><span class="value danger">{negative}</span></div>
        <div class="profile-metric"><span class="label">{icon("calibration")} {html.escape(ui_label("ui.pending_validation"))}</span><span class="value warn">{pending}</span></div>
      </div>
      <form class="observations-filters" method="get" action="">
        <input type="hidden" name="section" value="observations">
        <input type="hidden" name="q" value="{html.escape(search, quote=True)}">
        <input type="hidden" name="sort" value="{html.escape(sort_key, quote=True)}">
        <input type="hidden" name="dir" value="{html.escape(sort_dir, quote=True)}">
        <input type="hidden" name="obs_id" value="{html.escape(selected_observation_id, quote=True)}">
        <div class="admin-field"><label>{html.escape(ui_label("ui.date_from"))}</label><input name="date_from" type="date" value="{html.escape(date_from, quote=True)}" max="9999-12-31" placeholder="{html.escape(today_value, quote=True)}" onchange="this.blur(); this.form.submit()"></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.date_to"))}</label><input name="date_to" type="date" value="{html.escape(date_to, quote=True)}" max="9999-12-31" placeholder="{html.escape(today_value, quote=True)}" onchange="this.blur(); this.form.submit()"></div>
        <div class="admin-field"><label>{html.escape(ui_label("species_id"))}</label><select name="obs_species" onchange="this.form.submit()">{species_filter_options}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.result"))}</label><select name="result" onchange="this.form.submit()">{catalog_select_options(catalogs, "observation_flush_abundance", result_filter, ui_label("ui.all"))}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("validation_status"))}</label><select name="validation" onchange="this.form.submit()">{catalog_select_options(catalogs, "observation_validation_statuses", validation_filter, ui_label("ui.all"))}</select></div>
        <div class="admin-field"><label>{html.escape(ui_label("ui.search"))}</label><input name="obs_q" type="search" value="{html.escape(observation_search, quote=True)}"></div>
      </form>
      <div class="observations-layout">
        <article class="profile-section-card observations-table-card">
          <h2>{icon("metadata")} {html.escape(ui_label("ui.observation_records"))}</h2>
          <div class="observations-table-shell">
            <table>
              <thead><tr><th>{observation_sort_header(ui_label("ui.date_short"), "observed_at", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("species_id"), "species", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("ui.coordinates"), "coordinates", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("ui.altitude_short"), "altitude", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("flush_abundance"), "abundance", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("observer.name"), "observer", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("source.label"), "source", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("ui.status_short"), "validation", selected_species_id, search, filters)}</th><th>{observation_sort_header(ui_label("ui.use"), "use", selected_species_id, search, filters)}</th><th></th></tr></thead>
              <tbody>{render_observation_table(filtered_rows, catalogs, species_labels, selected_species_id=selected_species_id, search=search, filters=filters, sort_key=sort_key, sort_dir=sort_dir)}</tbody>
            </table>
          </div>
        </article>
        <aside class="profile-section-card observation-detail-shell">
          {render_observation_detail(filtered_rows, catalogs, species_labels, selected_observation_id=selected_observation_id)}
        </aside>
      </div>
      <div class="profile-action-bar observations-main-actions">
        <a class="button-link primary-link" href="#new-observation">{html.escape(ui_label("ui.new_observation"))}</a>
        <a class="button-link" href="#import-observation-exif">{html.escape(ui_label("ui.import_exif_images"))}</a>
        <a class="button-link" href="{html.escape(calibration_href, quote=True)}">{html.escape(ui_label("ui.open_calibration"))}</a>
      </div>
      {render_archived_observations_panel(archived_observations_payload, species_labels, selected_species_id, filters)}
      {render_observation_gis_lab(filtered_rows, species_labels, selected_species_id, search, filters, gis_reconstruction_payload)}
      {render_observation_create_form(profiles, catalogs, selected_species_id, form_message, filters)}
      {render_observation_exif_import_form(profiles, catalogs, selected_species_id, filters)}
      {render_observation_duplicate_form(rows, profiles, catalogs, selected_species_id, filters)}
      {render_observation_edit_modals(filtered_rows, profiles, catalogs, selected_species_id, filters)}
      {render_observation_map_modals(filtered_rows, selected_species_id, search, filters)}
      {render_observation_photo_modals(filtered_rows)}
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
