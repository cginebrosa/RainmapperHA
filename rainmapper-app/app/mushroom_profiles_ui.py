"""Server-rendered UI helpers for mushroom species maintenance.

This module intentionally contains presentation-only helpers used by the Home
Assistant web server. Keeping them outside `web_server.py` prevents the main
server from growing with every mushroom maintenance screen iteration while
preserving the existing server-side POST flow required by HA ingress.
"""

from __future__ import annotations

import html
import json
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


def profile_query_url(species_id: str = "", search: str = "", mode: str = "") -> str:
    """Return an ingress-safe query URL for the species maintenance page."""
    params = {}
    if species_id:
        params["id"] = species_id
    if search:
        params["q"] = search
    if mode:
        params["mode"] = mode
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
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "") or "").strip()
        if item_id:
            options.append((item_id, catalog_label(item)))
    return sorted(options, key=lambda option: option[0])


def value_chip(value: object, label: str = "") -> str:
    """Render a compact status chip."""
    text = str(value or "-")
    label_html = f'<span class="profile-chip-label">{html.escape(label)}</span>' if label else ""
    return f'<span class="profile-status-chip">{label_html}{html.escape(text)}</span>'


def value_row(label: str, value: object, css_class: str = "") -> str:
    """Render a compact read-only field used by summary cards."""
    return (
        f'<div class="profile-kv {html.escape(css_class)}">'
        f'<span>{html.escape(label)}</span><strong>{html.escape(str(value if value not in (None, "") else "-"))}</strong></div>'
    )


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


def render_new_species_form() -> str:
    """Render the guided species creation panel."""
    return """
    <details id="new-species" class="card profile-new-species">
      <summary><strong>New species</strong></summary>
      <p>Create a draft species profile with a complete validated starter structure. Review ecology, phenology, weather, scoring and calibration before using it for prediction.</p>
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
        <button class="primary">Create species</button>
      </form>
    </details>
    """


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
    for profile in profiles:
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
            '<span class="profile-list-icon" aria-hidden="true">◎</span>'
            '<span class="profile-list-main">'
            f"<strong>{html.escape(scientific_name or species_id)}</strong>"
            f'<span class="meta">{html.escape(common_name or species_id)}</span></span>'
            f'<span class="profile-chip-line">{chips}</span></a>'
        )
    if not rows:
        rows.append('<div class="profile-list-item"><strong>No species match</strong><span class="meta">Adjust the search.</span></div>')
    return '<aside class="profile-list"><div class="profile-list-search-title">Species</div>' + "".join(rows) + "</aside>"


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
        '<div class="profile-affinity-block">'
        f'<h2>{html.escape(field.replace("_", " ").title())}</h2>'
        + "".join(rows)
        + "</div>"
    )


def render_weather_summary(weather_model: dict[str, object]) -> str:
    """Render a compact weather summary from the current model blocks."""
    rainfall = weather_model.get("rainfall") if isinstance(weather_model.get("rainfall"), dict) else {}
    temperature = weather_model.get("temperature") if isinstance(weather_model.get("temperature"), dict) else {}
    humidity = weather_model.get("humidity") if isinstance(weather_model.get("humidity"), dict) else {}
    wind = weather_model.get("wind") if isinstance(weather_model.get("wind"), dict) else {}
    return f"""
    <div class="profile-weather-grid">
      <div>{value_row("Rain 7d min", rainfall.get("min_7d_mm"))}{value_row("Rain 15d optimal", f'{rainfall.get("optimal_15d_min_mm", "-")} - {rainfall.get("optimal_15d_max_mm", "-")} mm')}{value_row("Rain saturation", rainfall.get("saturation_30d_mm"))}</div>
      <div>{value_row("Temp optimal", f'{temperature.get("optimal_min_c", "-")} - {temperature.get("optimal_max_c", "-")} °C')}{value_row("Heat penalty", temperature.get("heat_penalty_above_c"))}{value_row("Frost penalty", temperature.get("frost_penalty_below_c"))}</div>
      <div>{value_row("Humidity min", humidity.get("min_preferred_percent"))}{value_row("Humidity optimal", humidity.get("optimal_percent"))}{value_row("Dry wind sensitive", "yes" if wind.get("dry_wind_sensitive") is True else "no")}</div>
      <div>{value_row("Wind penalty", wind.get("penalty_above_kmh"))}{value_row("Gust penalty", wind.get("gust_penalty_above_kmh"))}</div>
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
      <article class="profile-overview-card">
        <h3>1. Identity</h3>
        <div class="profile-grid">
          {form_field("species_id_display", "Species ID", profile.get("species_id", ""), readonly=True)}
          {form_field("scientific_name", "Scientific name", profile.get("scientific_name", ""))}
          {form_textarea("common_names", "Common names", profile.get("common_names", []), rows=2)}
          {form_select("taxonomy_status", "Taxonomy status", profile.get("taxonomy_status", ""), PROFILE_SELECT_VALUES["taxonomy_status"])}
          {form_select("edibility", "Edibility", profile.get("edibility", ""), PROFILE_SELECT_VALUES["edibility"])}
        </div>
      </article>
      <article class="profile-overview-card">
        <h3>2. Ecology and topography</h3>
        {value_row("Trophic mode", ecology.get("trophic_mode_id", "-"))}
        {value_row("Primary hosts", ", ".join(host_names[:4]) if host_names else "-")}
        {value_row("Altitude", f'{topography.get("altitude_min_m", "-")} - {topography.get("altitude_max_m", "-")} m')}
        {value_row("Optimal altitude", f'{topography.get("altitude_optimal_min_m", "-")} - {topography.get("altitude_optimal_max_m", "-")} m')}
        {value_row("Aspects", ", ".join(str(item) for item in aspect_names[:6]) if aspect_names else "-")}
      </article>
      <article class="profile-overview-card">
        <h3>3. Phenology</h3>
        <span class="label">Main months</span>
        {month_chips(phenology.get("main_months", []))}
        <span class="label">Secondary months</span>
        {month_chips(phenology.get("secondary_months", []), "secondary")}
        {value_row("Season patterns", ", ".join(str(item) for item in season_names[:3]) if season_names else "-")}
        {value_row("Fruiting delay", f'{delay.get("min", "-")} / {delay.get("optimal_min", "-")}-{delay.get("optimal_max", "-")} / {delay.get("max", "-")} days')}
      </article>
      <article class="profile-overview-card wide">
        <h3>4. Weather model summary</h3>
        {render_weather_summary(weather_model)}
      </article>
      <article class="profile-overview-card">
        <h3>5. Scoring weights</h3>
        {''.join(score_bar(key, value) for key, value in scoring.items())}
      </article>
      <article class="profile-overview-card">
        <h3>6. Confidence and calibration</h3>
        {value_row("Overall", confidence.get("overall_confidence"))}
        {value_row("Habitat", confidence.get("habitat_confidence"))}
        {value_row("Phenology", confidence.get("phenology_confidence"))}
        {value_row("Weather", confidence.get("weather_threshold_confidence"))}
        {value_row("Calibration", confidence.get("local_calibration_status"))}
        {value_row("Priority", confidence.get("calibration_priority"))}
      </article>
      <article class="profile-overview-card full">
        <h3>7. Metadata</h3>
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
    affinity_blocks = "".join(render_profile_affinity_rows(field, ecology.get(field, []), catalogs) for field in PROFILE_AFFINITY_GROUPS)
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
    return f"""
    <section class="card profile-editor profile-editor-polished">
      <div class="profile-editor-head profile-hero">
        <div class="profile-title-block">
          <span class="profile-hero-icon" aria-hidden="true">◎</span>
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
            <label for="profile-tab-general">General</label>
            <label for="profile-tab-ecology">Ecology</label>
            <label for="profile-tab-phenology">Phenology</label>
            <label for="profile-tab-weather">Weather</label>
            <label for="profile-tab-scoring">Scoring</label>
            <label for="profile-tab-calibration">Confidence</label>
            <label for="profile-tab-metadata">Metadata</label>
            <label for="profile-tab-json">JSON</label>
          </div>
          <div class="profile-tab-content">
            <section class="profile-section profile-tab-panel general">{general_dashboard}</section>
            <section class="profile-section profile-tab-panel ecology">
              <h2>Ecology</h2>
              <div class="profile-grid">
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
              <h2>Metadata</h2>
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
            </section>
            <section class="profile-section profile-tab-panel json">
              <h2>Advanced JSON</h2>
              <p class="meta">Use the raw JSON panel below only when a field is not exposed by the guided form.</p>
            </section>
          </div>
        </div>
        <div class="profile-action-bar">
          <button class="primary">Save species profile</button>
          <button class="secondary" type="button" disabled>Duplicate species</button>
          <button class="secondary" type="button" disabled>Validate profile</button>
          <button class="danger-button" type="button" disabled>Archive species</button>
        </div>
      </form>
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
