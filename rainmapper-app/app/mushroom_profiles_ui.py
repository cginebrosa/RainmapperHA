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

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


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


def catalog_label(item: dict[str, object]) -> str:
    """Prefer Spanish, then Catalan, then English catalog labels."""
    label = item.get("label")
    if isinstance(label, dict):
        for language in ("es", "ca", "en"):
            value = label.get(language)
            if value:
                return str(value)
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
    text = str(value or "-")
    label_html = f'<span class="profile-chip-label">{html.escape(label)}</span>' if label else ""
    css_class = css_token(text)
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
        css_class = active_class if month in months else ""
        rendered.append(f'<span class="month-chip {css_class}">{html.escape(MONTH_LABELS[month])}</span>')
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
        f'<span>{html.escape(label.replace("_", " ").title())}</span>'
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
        option_html.append(f'<option value="{html.escape(option, quote=True)}"{selected}>{html.escape(option)}</option>')
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


def parameter_label(name: str, language: str = "en") -> str:
    """Return a short human label for a model parameter key."""
    labels = PARAMETER_LABELS.get(name)
    if labels:
        return labels.get(language) or labels.get("en") or next(iter(labels.values()))
    return name.replace("_", " ").strip().title()


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
            '<em>Yes</em></label>'
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
    return """
    <div id="new-species-modal" class="modal-layer">
      <a class="modal-backdrop" href="?" aria-label="Cancel new species"></a>
      <section class="modal-card">
        <header class="modal-head">
          <div>
            <h2>New species</h2>
            <p>Create a draft profile, then complete ecology, phenology, weather, scoring and calibration.</p>
          </div>
          <a class="button-link" href="?">Cancel</a>
        </header>
        <form class="catalog-create-form" method="post" action="" onsubmit="return confirm('Create this draft species profile and validate the full dataset?')">
          <input type="hidden" name="profile_action" value="create_profile">
          <div class="admin-form-grid">
            <div class="admin-field">
              <label>Species ID</label>
              <input name="new_species_id" placeholder="boletus_example" required>
            </div>
            <div class="admin-field">
              <label>Scientific name</label>
              <input name="new_scientific_name" placeholder="Boletus example" required>
            </div>
            <div class="admin-field">
              <label>Common name</label>
              <input name="new_common_name" placeholder="optional">
            </div>
          </div>
          <div class="modal-actions">
            <a class="button-link" href="?">Cancel</a>
            <button class="primary">Create species</button>
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
            '<button class="secondary">Restore species</button>'
            "</form>"
            '<form method="post" action="" onsubmit="return confirm(\'Delete this archived species permanently?\') && confirm(\'This action cannot be undone. The archived copy will be removed permanently.\')">'
            '<input type="hidden" name="profile_action" value="delete_archived_profile">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="delete_confirm_id" value="{html.escape(species_id, quote=True)}">'
            '<button class="danger-button">Delete permanently</button>'
            "</form>"
            "</div></div>"
        )
    content = "".join(rows) if rows else '<p class="meta">No archived species profiles.</p>'
    return (
        '<div id="restore-species-modal" class="modal-layer">'
        '<a class="modal-backdrop" href="?" aria-label="Cancel restore species"></a>'
        '<section class="modal-card modal-card-wide">'
        '<header class="modal-head"><div>'
        f'<h2>Restore species</h2><p>{len(rows)} archived species profiles.</p>'
        '</div><a class="button-link" href="?">Cancel</a></header>'
        f'<div class="archived-species-panel">{content}</div>'
        '<div class="modal-actions"><a class="button-link" href="?">Cancel</a></div>'
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
        ("Species", str(len(profiles)), ""),
        ("Accepted", str(accepted), "ok"),
        ("Operational", str(operational), "warn" if operational else ""),
        ("Uncalibrated", str(uncalibrated), "warn" if uncalibrated else "ok"),
        ("Draft", str(draft), "warn" if draft else "ok"),
        ("High priority", str(priority), "warn" if priority else "ok"),
        ("Human validation", str(human), "warn" if human else "ok"),
        ("Validation", f"{len(errors)} errors · {len(warnings)} warnings", "danger" if errors else "warn" if warnings else "ok"),
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
        chips = "".join(
            f'<span class="profile-chip {html.escape(str(value))}">{html.escape(str(value))}</span>'
            for value in (
                confidence.get("overall_confidence", ""),
                confidence.get("calibration_priority", ""),
                metadata.get("review_status", ""),
            )
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
        rows.append('<div class="profile-list-item"><strong>No species match</strong><span class="meta">Adjust the search.</span></div>')
    return '<aside class="profile-list"><div class="profile-list-search-title">Species</div>' + "".join(rows) + "</aside>"


def render_section_tabs(active_section: str, selected_id: str, search: str) -> str:
    """Render top-level mushroom maintenance tabs as ingress-safe links."""
    sections = [
        ("summary", "Summary"),
        ("species", "Species"),
        ("observations", "Observations"),
        ("parameters", "Parameters"),
        ("calibration", "Calibration"),
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
        return '<section class="card profile-section-screen"><h2>No species selected</h2><p class="meta">Create or select a species first.</p></section>'
    species_id = str(profile.get("species_id", ""))
    confidence = nested_dict(profile, "prediction_confidence")
    metadata = nested_dict(profile, "metadata")
    chips = "".join(
        [
            value_chip(profile.get("taxonomy_status", "-"), "Taxonomy"),
            value_chip(confidence.get("overall_confidence", "-"), "Confidence"),
            value_chip(confidence.get("local_calibration_status", "-"), "Calibration"),
            value_chip(confidence.get("calibration_priority", "-"), "Priority"),
            value_chip(metadata.get("review_status", "-"), "Review"),
        ]
    )
    return f"""
    <header class="profile-section-banner">
      <div class="profile-title-block">
        <span class="profile-hero-icon">{icon("mushroom")}</span>
        <div>
          <span class="meta">{html.escape(section)}</span>
          <h2>{html.escape(str(profile.get("scientific_name", species_id)))}</h2>
          <p class="meta">species_id: {html.escape(species_id)} · {html.escape(profile_common_name(profile) or "no common name")}</p>
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
            + form_select(f"{field}_{index}_relationship", "Relationship", item.get("relationship", ""), PROFILE_SELECT_VALUES["relationship"])
            + form_field(f"{field}_{index}_affinity", "Affinity", item.get("affinity", ""), field_type="number")
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
        "host_affinities": "Host affinities",
        "forest_type_affinities": "Forest types",
        "soil_affinities": "Soils",
        "lithology_affinities": "Lithology",
        "habitat_feature_affinities": "Habitat features",
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
      <div>{value_row("Rain 7d min", rainfall.get("rain_7d_min_mm"))}{value_row("Rain 15d optimal", f'{rainfall.get("rain_15d_optimal_min_mm", "-")} - {rainfall.get("rain_15d_optimal_max_mm", "-")} mm')}{value_row("Rain saturation", rainfall.get("rain_30d_saturation_penalty_mm"))}</div>
      <div>{value_row("Temp min optimal", f'{temperature.get("temp_min_7d_optimal_min_c", "-")} - {temperature.get("temp_min_7d_optimal_max_c", "-")} °C')}{value_row("Temp max optimal", f'{temperature.get("temp_max_7d_optimal_min_c", "-")} - {temperature.get("temp_max_7d_optimal_max_c", "-")} °C')}{value_row("Heat penalty", temperature.get("heat_penalty_temp_max_c"))}{value_row("Frost penalty", temperature.get("frost_penalty_temp_min_c"))}</div>
      <div>{value_row("Humidity min", humidity.get("humidity_min_7d_preferred_min_pct"))}{value_row("Humidity optimal", humidity.get("humidity_max_7d_preferred_min_pct"))}{value_row("Dry wind sensitive", "yes" if wind.get("dry_wind_sensitive") is True else "no")}</div>
      <div>{value_row("Wind penalty", wind.get("wind_avg_3d_penalty_kmh"))}{value_row("Gust penalty", wind.get("wind_gust_3d_penalty_kmh"))}</div>
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
    host_names = []
    for item in ecology.get("host_affinities", []) if isinstance(ecology.get("host_affinities"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            host_names.append(str(item.get("id")))
    season_names = phenology.get("season_pattern_ids") if isinstance(phenology.get("season_pattern_ids"), list) else []
    aspect_names = topography.get("preferred_aspect_ids") if isinstance(topography.get("preferred_aspect_ids"), list) else []
    return f"""
    <section class="profile-overview-grid">
      <article class="profile-overview-card identity">
        {card_title(1, "Identity", "identity")}
        {value_row("Species ID", profile.get("species_id", ""))}
        {value_row("Scientific name", profile.get("scientific_name", ""))}
        {value_row("Common names", compact_list(profile.get("common_names", []), 4))}
        {value_row("Taxonomy", profile.get("taxonomy_status", ""))}
        {value_row("Edibility", profile.get("edibility", ""))}
      </article>
      <article class="profile-overview-card">
        {card_title(2, "Ecology and topography", "ecology")}
        {value_row("Trophic mode", ecology.get("trophic_mode_id", "-"))}
        {value_row("Primary hosts", ", ".join(host_names[:4]) if host_names else "-")}
        {value_row("Altitude", f'{topography.get("altitude_min_m", "-")} - {topography.get("altitude_max_m", "-")} m')}
        {value_row("Optimal altitude", f'{topography.get("altitude_optimal_min_m", "-")} - {topography.get("altitude_optimal_max_m", "-")} m')}
        {value_row("Aspects", ", ".join(str(item) for item in aspect_names[:6]) if aspect_names else "-")}
      </article>
      <article class="profile-overview-card">
        {card_title(3, "Phenology", "phenology")}
        <span class="label">Main months</span>
        {month_chips(phenology.get("main_months", []))}
        <span class="label">Secondary months</span>
        {month_chips(phenology.get("secondary_months", []), "secondary")}
        {value_row("Season patterns", ", ".join(str(item) for item in season_names[:3]) if season_names else "-")}
        {value_row("Fruiting delay", f'{delay.get("min", "-")} / {delay.get("optimal_min", "-")}-{delay.get("optimal_max", "-")} / {delay.get("max", "-")} days')}
      </article>
      <article class="profile-overview-card wide">
        {card_title(4, "Weather model summary", "weather")}
        {render_weather_summary(weather_model)}
      </article>
      <article class="profile-overview-card">
        {card_title(5, "Scoring weights", "scoring")}
        {''.join(score_bar(key, value) for key, value in scoring.items())}
      </article>
      <article class="profile-overview-card">
        {card_title(6, "Confidence and calibration", "calibration")}
        {value_row("Overall", confidence.get("overall_confidence"))}
        {value_row("Habitat", confidence.get("habitat_confidence"))}
        {value_row("Phenology", confidence.get("phenology_confidence"))}
        {value_row("Weather", confidence.get("weather_threshold_confidence"))}
        {value_row("Calibration", confidence.get("local_calibration_status"))}
        {value_row("Priority", confidence.get("calibration_priority"))}
      </article>
      <article class="profile-overview-card full">
        {card_title(7, "Metadata", "metadata")}
        <div class="profile-metadata-strip">
          {value_row("Created", metadata.get("created_at"))}
          {value_row("Updated", metadata.get("updated_at"))}
          {value_row("Created by", metadata.get("created_by"))}
          {value_row("Review", metadata.get("review_status"))}
          {value_row("Source", metadata.get("source_quality"))}
          {value_row("Human validation", "yes" if metadata.get("requires_human_validation") is True else "no")}
        </div>
      </article>
    </section>
    """


def render_profile_editor(profile: dict[str, object] | None, catalogs: dict[str, object]) -> str:
    """Render the selected profile editor using the existing POST contract."""
    if not profile:
        return '<section class="card profile-editor"><h2>Species detail</h2><p>No species selected.</p></section>'
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
            value_chip(profile.get("taxonomy_status", "-"), "Taxonomy"),
            value_chip(profile.get("edibility", "-"), "Edibility"),
            value_chip(confidence.get("overall_confidence", "-"), "Confidence"),
            value_chip(confidence.get("local_calibration_status", "-"), "Calibration"),
            value_chip(metadata.get("review_status", "-"), "Review"),
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
            <label for="profile-tab-general">{icon("identity")}General</label>
            <label for="profile-tab-ecology">{icon("ecology")}Ecology</label>
            <label for="profile-tab-phenology">{icon("phenology")}Phenology</label>
            <label for="profile-tab-weather">{icon("weather")}Weather</label>
            <label for="profile-tab-scoring">{icon("scoring")}Scoring</label>
            <label for="profile-tab-calibration">{icon("calibration")}Confidence</label>
            <label for="profile-tab-metadata">{icon("metadata")}Metadata</label>
            <label for="profile-tab-json">{icon("metadata")}JSON</label>
          </div>
          <div class="profile-tab-content">
            <section class="profile-section profile-tab-panel general">{general_dashboard}</section>
            <section class="profile-section profile-tab-panel ecology">
              <div class="profile-section-head">
                <h2>Ecology</h2>
                {form_catalog_select("trophic_mode_id", "Trophic mode", ecology.get("trophic_mode_id", ""), catalog_options_for_group(catalogs, "trophic_modes"))}
              </div>
              {affinity_blocks}
            </section>
            <section class="profile-section profile-tab-panel phenology">
              <h2>Phenology and topography</h2>
              <div class="profile-grid four">
                {form_textarea("main_months", "Main months", phenology.get("main_months", []), rows=2)}
                {form_textarea("secondary_months", "Secondary months", phenology.get("secondary_months", []), rows=2)}
                {form_textarea("season_pattern_ids", "Season patterns", phenology.get("season_pattern_ids", []), rows=2)}
                {form_textarea("preferred_aspect_ids", "Preferred aspects", topography.get("preferred_aspect_ids", []), rows=2)}
                {form_field("delay_min", "Delay min", delay.get("min", ""), field_type="number")}
                {form_field("delay_optimal_min", "Delay optimal min", delay.get("optimal_min", ""), field_type="number")}
                {form_field("delay_optimal_max", "Delay optimal max", delay.get("optimal_max", ""), field_type="number")}
                {form_field("delay_max", "Delay max", delay.get("max", ""), field_type="number")}
                {form_field("altitude_min_m", "Altitude min m", topography.get("altitude_min_m", ""), field_type="number")}
                {form_field("altitude_optimal_min_m", "Altitude optimal min m", topography.get("altitude_optimal_min_m", ""), field_type="number")}
                {form_field("altitude_optimal_max_m", "Altitude optimal max m", topography.get("altitude_optimal_max_m", ""), field_type="number")}
                {form_field("altitude_max_m", "Altitude max m", topography.get("altitude_max_m", ""), field_type="number")}
              </div>
              {form_textarea("aspect_notes", "Aspect notes", topography.get("aspect_notes", ""), rows=2)}
            </section>
            <section class="profile-section profile-tab-panel weather">
              <h2>Weather model</h2>
              <div class="profile-grid four">
                {''.join(form_field(f"rainfall_{key}", key, value, field_type="number") for key, value in rainfall.items())}
                {''.join(form_field(f"temperature_{key}", key, value, field_type="number") for key, value in temperature.items())}
                {''.join(form_field(f"humidity_{key}", key, value, field_type="number") for key, value in humidity.items())}
                {''.join(form_field(f"wind_{key}", key, value, field_type="checkbox" if isinstance(value, bool) else "number") for key, value in wind.items())}
              </div>
            </section>
            <section class="profile-section profile-tab-panel scoring">
              <h2>Scoring weights</h2>
              <div class="profile-scoring-total">
                <span>Current total</span><strong>{scoring_total:.2f}</strong><em>Target: 1.00</em>
              </div>
              <div class="profile-score-editor">
                {''.join(score_bar(key, value) for key, value in scoring.items())}
              </div>
              <div class="profile-grid four">
                {''.join(form_field(f"score_{key}", key, value, field_type="number", step="0.01", minimum="0", maximum="1") for key, value in scoring.items())}
              </div>
            </section>
            <section class="profile-section profile-tab-panel calibration">
              <h2>Confidence and calibration</h2>
              <div class="profile-calibration-summary">
                <div><span class="label">Current status</span><span class="value">{html.escape(str(confidence.get("local_calibration_status", "-")))}</span></div>
                <div><span class="label">Priority</span><span class="value">{html.escape(str(confidence.get("calibration_priority", "-")))}</span></div>
                <div><span class="label">Overall confidence</span><span class="value">{html.escape(str(confidence.get("overall_confidence", "-")))}</span></div>
                <div><span class="label">Human validation</span><span class="value">{html.escape(str(metadata.get("requires_human_validation", "-")))}</span></div>
              </div>
              <div class="profile-grid four">
                {form_select("local_calibration_status", "Local calibration status", confidence.get("local_calibration_status", ""), PROFILE_SELECT_VALUES["calibration_status"])}
                {form_select("calibration_priority", "Calibration priority", confidence.get("calibration_priority", ""), PROFILE_SELECT_VALUES["calibration_priority"])}
                {form_select("overall_confidence", "Overall confidence", confidence.get("overall_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("habitat_confidence", "Habitat confidence", confidence.get("habitat_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("topography_confidence", "Topography confidence", confidence.get("topography_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("phenology_confidence", "Phenology confidence", confidence.get("phenology_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("weather_threshold_confidence", "Weather threshold confidence", confidence.get("weather_threshold_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_select("taxonomy_confidence", "Taxonomy confidence", confidence.get("taxonomy_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
                {form_field("minimum_observations_for_calibration", "Min observations calibration", confidence.get("minimum_observations_for_calibration", ""), field_type="number")}
                {form_field("minimum_positive_observations", "Min positive observations", confidence.get("minimum_positive_observations", ""), field_type="number")}
                {form_field("minimum_negative_observations", "Min negative observations", confidence.get("minimum_negative_observations", ""), field_type="number")}
              </div>
              {form_textarea("confidence_notes", "Calibration notes", confidence.get("notes", ""), rows=3)}
            </section>
            <section class="profile-section profile-tab-panel metadata">
              <h2>Identity and metadata</h2>
              <div class="profile-subsection">
                <h3>Identity fields</h3>
                <div class="profile-grid two">
                  {form_field("scientific_name", "Scientific name", profile.get("scientific_name", ""))}
                  {form_select("taxonomy_status", "Taxonomy status", profile.get("taxonomy_status", ""), PROFILE_SELECT_VALUES["taxonomy_status"])}
                  {form_textarea("common_names", "Common names", profile.get("common_names", []), rows=3)}
                  {form_select("edibility", "Edibility", profile.get("edibility", ""), PROFILE_SELECT_VALUES["edibility"])}
                </div>
              </div>
              <div class="profile-subsection">
                <h3>Maintenance metadata</h3>
              <div class="profile-grid three">
                {form_field("profile_version", "Profile version", metadata.get("profile_version", ""))}
                {form_field("created_at", "Created at", metadata.get("created_at", ""))}
                {form_field("updated_at", "Updated at", metadata.get("updated_at", ""))}
                {form_field("created_by", "Created by", metadata.get("created_by", ""))}
                {form_select("review_status", "Review status", metadata.get("review_status", ""), PROFILE_SELECT_VALUES["review_status"])}
                {form_field("reviewed_by", "Reviewed by", metadata.get("reviewed_by", ""))}
                {form_select("source_quality", "Source quality", metadata.get("source_quality", ""), PROFILE_SELECT_VALUES["source_quality"])}
                {form_field("requires_human_validation", "Requires human validation", metadata.get("requires_human_validation"), field_type="checkbox")}
              </div>
              </div>
            </section>
            <section class="profile-section profile-tab-panel json">
              <h2>Advanced JSON</h2>
              <p class="meta">Use the raw JSON panel below only when a field is not exposed by the guided form.</p>
            </section>
          </div>
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">Save species profile</button>
          <a class="button-link secondary-link" href="#duplicate-species-modal">Duplicate species</a>
          <a class="button-link danger-link" href="#archive-species-modal">Archive species</a>
          <button class="secondary planned-action" type="button" disabled title="Planned action: explicit single-profile validation is not implemented yet">Validate profile · planned</button>
        </div>
      </form>
      <div id="duplicate-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="?id={html.escape(species_id, quote=True)}" aria-label="Cancel duplicate species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>Duplicate species</h2>
              <p>Clone this profile into a new draft species ID, then review all predictor fields.</p>
            </div>
            <a class="button-link" href="?id={html.escape(species_id, quote=True)}">Cancel</a>
          </header>
          <form method="post" action="" onsubmit="return confirm('Duplicate this species profile as a new draft profile?')">
            <input type="hidden" name="profile_action" value="duplicate_profile">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <div class="profile-grid">
              {form_field("duplicate_species_id", "New species ID", duplicate_species_id)}
              {form_field("duplicate_scientific_name", "Scientific name", duplicate_scientific_name)}
              {form_field("duplicate_common_name", "Common name", "")}
            </div>
            <div class="modal-actions">
              <a class="button-link" href="?id={html.escape(species_id, quote=True)}">Cancel</a>
              <button class="secondary">Duplicate species</button>
            </div>
          </form>
        </section>
      </div>
      <div id="archive-species-modal" class="modal-layer">
        <a class="modal-backdrop" href="?id={html.escape(species_id, quote=True)}" aria-label="Cancel archive species"></a>
        <section class="modal-card">
          <header class="modal-head">
            <div>
              <h2>Archive species</h2>
              <p>Move this profile out of active maintenance. It can be restored later if the ID is still free.</p>
            </div>
            <a class="button-link" href="?id={html.escape(species_id, quote=True)}">Cancel</a>
          </header>
          <form method="post" action="" onsubmit="return confirm('Archive this species profile? It will be removed from active profiles but can be restored.')">
            <input type="hidden" name="profile_action" value="archive_profile">
            <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
            <div class="admin-field">
              <label for="profile-archive-species-id">Species ID to archive</label>
              <input id="profile-archive-species-id" value="{html.escape(species_id, quote=True)}" readonly>
            </div>
            <div class="modal-actions">
              <a class="button-link" href="?id={html.escape(species_id, quote=True)}">Cancel</a>
              <button class="danger-button">Archive species</button>
            </div>
          </form>
        </section>
      </div>
      <details class="profile-raw-json">
        <summary><strong>Advanced raw JSON</strong></summary>
        <form class="profile-json-editor" method="post" action="?id={html.escape(species_id, quote=True)}" onsubmit="return confirm('Save raw JSON for this species profile and validate the full dataset?')">
          <input type="hidden" name="profile_action" value="save_profile_json">
          <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
          <label class="label" for="profile-json">Species profile JSON</label>
          <textarea id="profile-json" name="profile_json" spellcheck="false">{html.escape(json_value)}</textarea>
          <button class="primary">Save raw JSON</button>
        </form>
      </details>
    </section>
    """


def render_parameters_section(profile: dict[str, object] | None, catalogs: dict[str, object], search: str = "") -> str:
    """Render the top-level Parameters screen using real profile model fields."""
    if not profile:
        return '<section class="card profile-section-screen"><h2>Parameters</h2><p>No species selected.</p></section>'
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
      {render_selected_species_header(profile, "Parameters")}
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='parameters'), quote=True)}" onsubmit="return confirm('Save parameter changes for this species and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_parameters">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <div class="profile-parameters-grid">
          <article class="profile-section-card">
            <h2>{icon("weather")} Climate model</h2>
            <p class="parameter-card-note">Weather thresholds used by the suitability model.</p>
            <div class="parameter-climate-grid">
              <div class="profile-subsection">
                <h3>{icon("rain")} Rainfall</h3>
                {''.join(parameter_field(f"rainfall_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in rainfall.items())}
              </div>
              <div class="profile-subsection">
                <h3>{icon("temperature")} Temperature</h3>
                {''.join(parameter_field(f"temperature_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in temperature.items())}
              </div>
              <div class="profile-subsection">
                <h3>{icon("humidity")} Humidity</h3>
                {''.join(parameter_field(f"humidity_{key}", parameter_label(key), value, unit=parameter_unit(key)) for key, value in humidity.items())}
              </div>
              <div class="profile-subsection">
                <h3>{icon("wind")} Wind</h3>
                {''.join(parameter_field(f"wind_{key}", parameter_label(key), value, unit=parameter_unit(key), field_type="checkbox" if isinstance(value, bool) else "number") for key, value in wind.items())}
              </div>
            </div>
          </article>
          <article class="profile-section-card">
            <h2>{icon("ecology")} Habitat model</h2>
            <p class="parameter-card-note">Habitat, terrain and season inputs used by the species model.</p>
            <div class="profile-section-card-grid two parameter-habitat-grid">
              <div class="profile-subsection">
                <h3>{icon("host")} Ecology and habitat</h3>
                {form_catalog_select("trophic_mode_id", "Trophic mode", ecology.get("trophic_mode_id", ""), catalog_options_for_group(catalogs, "trophic_modes"))}
                {value_html_row("Primary hosts", affinity_chip_list(ecology, "host_affinities", host_labels, "primary"))}
                {value_html_row("Secondary hosts", affinity_chip_list(ecology, "host_affinities", host_labels, "secondary"))}
                {value_html_row("Other hosts", affinity_chip_list(ecology, "host_affinities", host_labels, exclude_relationships={"primary", "secondary"}))}
                {value_html_row("Forest types", affinity_chip_list(ecology, "forest_type_affinities", forest_labels))}
                {value_html_row("Habitat features", affinity_chip_list(ecology, "habitat_feature_affinities", habitat_labels))}
                <p class="meta">Use Species > Ecology to edit catalog-backed affinity rows and relationships.</p>
              </div>
              <div class="profile-subsection">
                <h3>{icon("soil")} Soils and lithology</h3>
                {value_html_row("Soils", affinity_chip_list(ecology, "soil_affinities", soil_labels))}
                {value_html_row("Lithology", affinity_chip_list(ecology, "lithology_affinities", lithology_labels))}
                <p class="meta">Affinity IDs are preserved here and edited in the full Species form.</p>
              </div>
              <div class="profile-subsection">
                <h3>{icon("topography")} Topography</h3>
                <div class="parameter-duo-grid">
                  {parameter_field("altitude_min_m", "Altitude min", topography.get("altitude_min_m", ""), unit="m")}
                  {parameter_field("altitude_optimal_min_m", "Optimal min", topography.get("altitude_optimal_min_m", ""), unit="m")}
                  {parameter_field("altitude_optimal_max_m", "Optimal max", topography.get("altitude_optimal_max_m", ""), unit="m")}
                  {parameter_field("altitude_max_m", "Altitude max", topography.get("altitude_max_m", ""), unit="m")}
                </div>
                {parameter_textarea("preferred_aspect_ids", "Preferred aspects", topography.get("preferred_aspect_ids", []), rows=1)}
                {parameter_textarea("aspect_notes", "Aspect notes", topography.get("aspect_notes", ""), rows=1)}
              </div>
              <div class="profile-subsection">
                <h3>{icon("phenology")} Phenology</h3>
                {parameter_textarea("main_months", "Main months", phenology.get("main_months", []), rows=1)}
                {parameter_textarea("secondary_months", "Secondary months", phenology.get("secondary_months", []), rows=1)}
                {parameter_textarea("season_pattern_ids", "Season patterns", phenology.get("season_pattern_ids", []), rows=1)}
                <div class="parameter-duo-grid">
                  {parameter_field("delay_min", "Delay min", delay.get("min", ""), unit="d")}
                  {parameter_field("delay_optimal_min", "Delay optimal min", delay.get("optimal_min", ""), unit="d")}
                  {parameter_field("delay_optimal_max", "Delay optimal max", delay.get("optimal_max", ""), unit="d")}
                  {parameter_field("delay_max", "Delay max", delay.get("max", ""), unit="d")}
                </div>
              </div>
              <div class="profile-subsection full">
                <h3>{icon("scoring")} Scoring weights</h3>
                <div class="profile-scoring-total"><span>Current total</span><strong>{scoring_total:.2f}</strong><em>Target: 1.00</em></div>
                <div class="parameter-score-grid">
                  {''.join(parameter_field(f"score_{key}", parameter_label(key), value, step="0.01", minimum="0", maximum="1") for key, value in scoring.items())}
                </div>
              </div>
            </div>
          </article>
        </div>
        <div class="profile-action-bar">
          <a class="button-link secondary-link" href="{html.escape(species_href, quote=True)}">Back to Species editor</a>
          <button class="secondary" type="reset">Reset visible changes</button>
          <button class="primary profile-primary-action">Save parameter changes</button>
        </div>
      </form>
      <p class="meta">Review status: {html.escape(str(metadata.get("review_status", "-")))}. Catalog-backed affinity relationships are intentionally edited from the Species tab to avoid lossy partial updates.</p>
    </section>
    """


def render_calibration_section(profile: dict[str, object] | None, search: str = "") -> str:
    """Render the top-level Calibration screen using real confidence fields."""
    if not profile:
        return '<section class="card profile-section-screen"><h2>Calibration</h2><p>No species selected.</p></section>'
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
      {render_selected_species_header(profile, "Calibration")}
      <form method="post" action="{html.escape(profile_query_url(species_id, search, section='calibration'), quote=True)}" onsubmit="return confirm('Save calibration settings for this species and validate the full mushroom dataset?')">
        <input type="hidden" name="profile_action" value="save_profile_calibration">
        <input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">
        <div class="profile-calibration-cards">
          <div class="profile-metric"><span class="label">Calibration status</span><span class="value warn">{html.escape(str(confidence.get("local_calibration_status", "-")))}</span></div>
          <div class="profile-metric"><span class="label">Priority</span><span class="value ok">{html.escape(str(confidence.get("calibration_priority", "-")))}</span></div>
          <div class="profile-metric"><span class="label">Overall confidence</span><span class="value">{html.escape(str(confidence.get("overall_confidence", "-")))}</span></div>
          <div class="profile-metric"><span class="label">Min observations</span><span class="value">{html.escape(str(minimum_total))}</span></div>
          <div class="profile-metric"><span class="label">Min positive</span><span class="value">{html.escape(str(minimum_positive))}</span></div>
          <div class="profile-metric"><span class="label">Min negative</span><span class="value">{html.escape(str(minimum_negative))}</span></div>
        </div>
        <div class="profile-calibration-grid">
          <article class="profile-section-card">
            <h2>1. Confidence profile</h2>
            <div class="profile-grid two">
              {form_select("overall_confidence", "Overall confidence", confidence.get("overall_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("habitat_confidence", "Habitat confidence", confidence.get("habitat_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("topography_confidence", "Topography confidence", confidence.get("topography_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("phenology_confidence", "Phenology confidence", confidence.get("phenology_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("weather_threshold_confidence", "Weather threshold confidence", confidence.get("weather_threshold_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
              {form_select("taxonomy_confidence", "Taxonomy confidence", confidence.get("taxonomy_confidence", ""), PROFILE_SELECT_VALUES["confidence"])}
            </div>
          </article>
          <article class="profile-section-card">
            <h2>2. Calibration requirements</h2>
            <div class="profile-grid two">
              {form_select("local_calibration_status", "Local calibration status", confidence.get("local_calibration_status", ""), PROFILE_SELECT_VALUES["calibration_status"])}
              {form_select("calibration_priority", "Calibration priority", confidence.get("calibration_priority", ""), PROFILE_SELECT_VALUES["calibration_priority"])}
              {form_field("minimum_observations_for_calibration", "Minimum observations", confidence.get("minimum_observations_for_calibration", ""), field_type="number", minimum="0")}
              {form_field("minimum_positive_observations", "Minimum positive", confidence.get("minimum_positive_observations", ""), field_type="number", minimum="0")}
              {form_field("minimum_negative_observations", "Minimum negative", confidence.get("minimum_negative_observations", ""), field_type="number", minimum="0")}
              {form_field("requires_human_validation", "Requires human validation", metadata.get("requires_human_validation"), field_type="checkbox")}
              {form_select("review_status", "Review status", metadata.get("review_status", ""), PROFILE_SELECT_VALUES["review_status"])}
            </div>
          </article>
          <article class="profile-section-card">
            <h2>3. Observation coverage</h2>
            <div class="profile-coverage-grid">
              {value_row("Total observations used", f'0 / {minimum_total}')}
              {value_row("Positive observations", f'0 / {minimum_positive}')}
              {value_row("Negative observations", f'0 / {minimum_negative}')}
              {value_row("Key data gaps", "pending observation model")}
            </div>
            <p class="meta">Coverage will be calculated from the future observations dataset. No observation data is stored inside mushroom_profiles.json.</p>
          </article>
          <article class="profile-section-card">
            <h2>4. Calibration notes</h2>
            {form_textarea("confidence_notes", "Notes stored in prediction_confidence.notes", confidence.get("notes", ""), rows=8)}
          </article>
          <article class="profile-section-card full">
            <h2>5. Actions and recommendations</h2>
            <div class="profile-recommendation-list">
              <a class="button-link" href="{html.escape(observations_href, quote=True)}">Add local observations</a>
              <a class="button-link" href="{html.escape(parameters_href, quote=True)}">Review weather thresholds</a>
              <button class="secondary planned-action" type="button" disabled>Start human validation · planned</button>
              <button class="secondary planned-action" type="button" disabled>Recalculate scoring · planned</button>
            </div>
          </article>
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">Save calibration</button>
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
    selected_species_id: str,
) -> str:
    """Render the observation list with enough columns for field calibration review."""
    visible_rows = rows
    if selected_species_id:
        visible_rows = [row for row in rows if str(row.get("species_id", "")) == selected_species_id]
    visible_rows = sorted(visible_rows, key=lambda row: str(row.get("observed_at", "")), reverse=True)
    if not visible_rows:
        return '<tr><td colspan="10">No observations yet for the current filter. Create one from the panel below.</td></tr>'

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
            f"<a class=\"button-link compact\" href=\"#edit-observation-{html.escape(str(row.get('observation_id', '')), quote=True)}\">Edit</a>"
            "<form method=\"post\" action=\"\" onsubmit=\"return confirm('Archive this observation?')\">"
            "<input type=\"hidden\" name=\"profile_action\" value=\"archive_observation\">"
            f"<input type=\"hidden\" name=\"species_id\" value=\"{html.escape(species_id, quote=True)}\">"
            f"<input type=\"hidden\" name=\"observation_id\" value=\"{html.escape(str(row.get('observation_id', '')), quote=True)}\">"
            "<button class=\"secondary compact\" type=\"submit\">Archive</button>"
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
    selected_species_id: str,
) -> str:
    """Render the most recent observation detail panel."""
    visible_rows = rows
    if selected_species_id:
        visible_rows = [row for row in rows if str(row.get("species_id", "")) == selected_species_id]
    visible_rows = sorted(visible_rows, key=lambda row: str(row.get("observed_at", "")), reverse=True)
    if not visible_rows:
        return """
        <h2 id="observation-detail">Observation detail</h2>
        <p class="meta">Select or create an observation to review its calibration context.</p>
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
    <h2 id="observation-detail">Observation detail</h2>
    {value_row("Observation ID", row.get("observation_id", "-"))}
    {value_row("Species", species_labels.get(species_id, species_id))}
    {value_row("Coordinates", coords)}
    {value_row("Altitude", f'{altitude.get("meters")} m' if isinstance(altitude, dict) and altitude.get("meters") is not None else "-")}
    {value_row("Abundance", observation_catalog_label(catalogs, "observation_flush_abundance", row.get("flush_abundance")))}
    {value_row("Source quality", row.get("source_quality", "-"))}
    {value_row("Calibration weight", f"{observation_weight(catalogs, row):.2f}")}
    <div class="observation-notes">
      <strong>Habitat notes</strong>
      <p>{html.escape(str(site_context.get("habitat_notes", "") or "No habitat notes recorded.") if isinstance(site_context, dict) else "No habitat notes recorded.")}</p>
      <strong>Host notes</strong>
      <p>{html.escape(str(site_context.get("host_notes", "") or "No host notes recorded.") if isinstance(site_context, dict) else "No host notes recorded.")}</p>
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
      <a class="modal-backdrop" href="#" aria-label="Cancel new observation"></a>
      <form class="modal-card modal-card-wide observation-form" method="post" action="">
        <input type="hidden" name="profile_action" value="{html.escape(action, quote=True)}">
        {f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">' if observation_id else ""}
        <header class="modal-head">
          <div>
            <h2>{html.escape(title)}</h2>
            <p>Register a field outcome for species calibration. Use either a map link/decimal pair or explicit latitude and longitude.</p>
          </div>
          <a class="button-link" href="#">Cancel</a>
        </header>
        {f'<div class="catalog-alert error"><strong>Observation was not saved</strong><br>{html.escape(form_message.replace("Observation was not saved: ", ""))}</div>' if form_message else ""}
        <div class="profile-grid four">
          <div class="admin-field"><label>Species</label><select name="observation_species_id" required>{species_select_options(profiles, current_species_id)}</select></div>
          <div class="admin-field"><label>Date</label><input name="observed_at" type="date" value="{html.escape(str(row.get("observed_at", "")), quote=True)}" onchange="this.blur()" required></div>
          <div class="admin-field"><label>Abundance</label><select name="flush_abundance" required>{catalog_select_options(catalogs, "observation_flush_abundance", str(row.get("flush_abundance", "") or "normal"))}</select></div>
          <div class="admin-field"><label>Source quality</label><input name="source_quality" type="number" min="0" max="1" step="0.05" value="{html.escape(str(row.get("source_quality", 0.75)), quote=True)}" required></div>
        </div>
        <div class="profile-grid three">
          <div class="admin-field wide"><label>Coordinates or Google Maps link</label><input name="location_input" value="{html.escape(location_input, quote=True)}" placeholder="41.38740, 2.16860 or Google Maps URL"></div>
          <div class="admin-field"><label>Latitude</label><input name="location_lat" type="number" step="any" value="{html.escape(lat_value, quote=True)}"></div>
          <div class="admin-field"><label>Longitude</label><input name="location_lon" type="number" step="any" value="{html.escape(lon_value, quote=True)}"></div>
        </div>
        <div class="profile-grid four">
          <div class="admin-field"><label>Altitude m</label><input name="altitude_m" type="number" step="1" value="{html.escape(altitude_value, quote=True)}"></div>
          <div class="admin-field"><label>Altitude source</label><select name="altitude_source">{catalog_select_options(catalogs, "observation_altitude_sources", str(altitude.get("source", "") if isinstance(altitude, dict) else ""), "Not informed")}</select></div>
          <div class="admin-field"><label>Validation</label><select name="validation_status" required>{catalog_select_options(catalogs, "observation_validation_statuses", str(row.get("validation_status", "") or "draft"))}</select></div>
          <div class="admin-field"><label>Calibration use</label><select name="calibration_use" required>{catalog_select_options(catalogs, "observation_calibration_uses", str(row.get("calibration_use", "") or "review"))}</select></div>
        </div>
        <div class="profile-grid four">
          <div class="admin-field"><label>Exclusion reason</label><select name="calibration_exclusion_reason">{catalog_select_options(catalogs, "observation_exclusion_reasons", str(row.get("calibration_exclusion_reason", "") or ""), "None")}</select></div>
          <div class="admin-field"><label>Observer</label><input name="observer_name" value="{html.escape(str(observer.get("name", "") if isinstance(observer, dict) else ""), quote=True)}"></div>
          <div class="admin-field"><label>Expertise</label><select name="observer_expertise">{catalog_select_options(catalogs, "observer_expertise_levels", str(observer.get("expertise", "") if isinstance(observer, dict) else "") or "unknown")}</select></div>
          <div class="admin-field"><label>Source type</label><select name="source_type">{catalog_select_options(catalogs, "observation_source_types", str(source.get("type", "") if isinstance(source, dict) else "") or "personal_observation")}</select></div>
        </div>
        <div class="profile-grid two">
          <div class="admin-field"><label>Source label</label><input name="source_label" value="{html.escape(str(source.get("label", "") if isinstance(source, dict) else ""), quote=True)}"></div>
          <div class="admin-field wide"><label>Source URL</label><input name="source_url" type="url" value="{html.escape(str(source.get("url", "") if isinstance(source, dict) else ""), quote=True)}"></div>
        </div>
        <div class="profile-grid two">
          {form_textarea("habitat_notes", "Habitat notes", site_context.get("habitat_notes", "") if isinstance(site_context, dict) else "", rows=3)}
          {form_textarea("host_notes", "Host notes", site_context.get("host_notes", "") if isinstance(site_context, dict) else "", rows=3)}
        </div>
        <div class="profile-action-bar">
          <button class="primary profile-primary-action">Save observation</button>
          <button class="secondary planned-action" type="button" disabled>Recover altitude</button>
          <button class="secondary planned-action" type="button" disabled>Import CSV</button>
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
        title="New observation",
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
            title=f"Edit observation {str(row.get('observation_id', ''))}",
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
        return '<details class="profile-section-card"><summary><strong>Archived observations</strong></summary><p class="meta">No archived observations for the current filter.</p></details>'
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
            '<button class="secondary" type="submit">Restore</button>'
            '</form>'
            '<form method="post" action="" onsubmit="return confirm(\'Delete this archived observation permanently?\') && confirm(\'This action cannot be undone. The archived copy will be removed permanently.\')">'
            '<input type="hidden" name="profile_action" value="delete_archived_observation">'
            f'<input type="hidden" name="species_id" value="{html.escape(species_id, quote=True)}">'
            f'<input type="hidden" name="observation_id" value="{html.escape(observation_id, quote=True)}">'
            f'<input type="hidden" name="delete_confirm_id" value="{html.escape(observation_id, quote=True)}">'
            '<button class="danger" type="submit">Delete permanently</button>'
            '</form>'
            '</div></div>'
        )
    return '<details class="profile-section-card"><summary><strong>Archived observations</strong></summary><div class="archived-observations-list">' + "".join(rows) + '</div></details>'


def render_observations_section(
    profile: dict[str, object] | None,
    profiles: list[dict[str, object]],
    catalogs: dict[str, object],
    observations_payload: dict[str, object] | None,
    archived_observations_payload: dict[str, object] | None,
    search: str = "",
    form_message: str = "",
) -> str:
    """Render the observation workspace backed by mushroom_observations.json."""
    selected_species_id = str(profile.get("species_id", "")) if profile else ""
    rows = observations_from_payload(observations_payload)
    species_labels = profile_name_map(profiles)
    total, positive, negative, pending = observation_metrics(
        [row for row in rows if not selected_species_id or str(row.get("species_id", "")) == selected_species_id]
    )
    calibration_href = profile_query_url(selected_species_id, search, section="calibration") if selected_species_id else profile_query_url(section="calibration")
    species_filter_options = '<option value="">All species</option>' + "".join(
        f'<option value="{html.escape(str(item.get("species_id", "")), quote=True)}"{" selected" if str(item.get("species_id", "")) == selected_species_id else ""}>{html.escape(str(item.get("scientific_name", item.get("species_id", ""))))}</option>'
        for item in profiles
        if item.get("species_id")
    )
    return f"""
    <section class="card profile-section-screen observations-screen">
      {render_selected_species_header(profile, "Observations") if profile else '<h2>Observations</h2>'}
      <div class="profile-calibration-cards observations-metrics">
        <div class="profile-metric"><span class="label">{icon("metadata")} Total observations</span><span class="value">{total}</span></div>
        <div class="profile-metric"><span class="label">{icon("mushroom")} Positive / present</span><span class="value ok">{positive}</span></div>
        <div class="profile-metric"><span class="label">{icon("scoring")} Negative / absent</span><span class="value danger">{negative}</span></div>
        <div class="profile-metric"><span class="label">{icon("calibration")} Pending validation</span><span class="value warn">{pending}</span></div>
      </div>
      <div class="observations-filters">
        <div class="admin-field"><label>Date from</label><input type="date" readonly></div>
        <div class="admin-field"><label>Date to</label><input type="date" readonly></div>
        <div class="admin-field"><label>Species</label><select disabled>{species_filter_options}</select></div>
        <div class="admin-field"><label>Result</label><select disabled>{catalog_select_options(catalogs, "observation_flush_abundance", "", "All")}</select></div>
        <div class="admin-field"><label>Validation</label><select disabled>{catalog_select_options(catalogs, "observation_validation_statuses", "", "All")}</select></div>
        <div class="admin-field"><label>Search</label><input value="{html.escape(search, quote=True)}" readonly></div>
      </div>
      <div class="observations-layout">
        <article class="profile-section-card observations-table-card">
          <h2>{icon("metadata")} Observation records</h2>
          <div class="observations-table-shell">
            <table>
              <thead><tr><th>Date</th><th>Species</th><th>Coordinates</th><th>Alt.</th><th>Abundance</th><th>Observer</th><th>Source</th><th>Validation</th><th>Use</th><th></th></tr></thead>
              <tbody>{render_observation_table(rows, catalogs, species_labels, selected_species_id)}</tbody>
            </table>
          </div>
        </article>
        <aside class="profile-section-card observation-detail-shell">
          {render_observation_detail(rows, catalogs, species_labels, selected_species_id)}
        </aside>
      </div>
      {render_archived_observations_panel(archived_observations_payload, species_labels, selected_species_id)}
      {render_observation_create_form(profiles, catalogs, selected_species_id, form_message)}
      {render_observation_edit_modals(rows, profiles, catalogs, selected_species_id)}
      <div class="profile-action-bar">
        <a class="button-link primary-link" href="#new-observation">New observation</a>
        <a class="button-link" href="{html.escape(calibration_href, quote=True)}">Open calibration</a>
      </div>
    </section>
    """


def render_profile_full_json_panel(payload: dict[str, object], mode: str) -> str:
    """Render advanced full-file JSON maintenance for profiles."""
    json_value = json.dumps(payload, indent=2, ensure_ascii=False)
    mode_label = "empty template" if mode == "template" else "current profiles"
    return f"""
    <details class="card" {"open" if mode == "template" else ""}>
      <summary><strong>Full profiles JSON import/export</strong> · {html.escape(mode_label)}</summary>
      <p>Use this panel for controlled full-file import/export. Saving validates profiles, catalogs and GIS mappings together before replacing the persistent profiles file.</p>
      <div class="quick-actions">
        <a class="button-link" href="?mode=current">Current profiles</a>
        <a class="button-link" href="?mode=default">Packaged default</a>
        <a class="button-link" href="?mode=template">Empty template</a>
      </div>
      <form class="profile-json-editor" method="post" action="" onsubmit="return confirm('Replace the full profiles JSON after validation?')">
        <input type="hidden" name="profile_action" value="save_profiles">
        <label class="label" for="profiles-full-json">Profiles JSON</label>
        <textarea id="profiles-full-json" name="profiles_json" spellcheck="false">{html.escape(json_value)}</textarea>
        <button class="primary">Validate and save full profiles</button>
      </form>
    </details>
    """
