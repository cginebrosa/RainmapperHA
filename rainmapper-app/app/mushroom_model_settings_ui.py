"""Small serving-policy editor; no model fitting or artifact scans on page load."""
from __future__ import annotations

from html import escape

from mushroom_profiles_ui import ui_label
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_prediction_policy as policy


def render(registry: dict, profiles: dict) -> str:
    from mushroom_predictor_ui import _COMPARISON_ESTIMATORS, _VERSION_SHORT_NAMES
    estimator_names = {key: name for key, name, _ in _COMPARISON_ESTIMATORS}
    def text(value):
        return escape(str(value), quote=True)

    def label(key):
        return text(ui_label("ui.model_settings_" + key))

    names = {
        row["species_id"]: row.get("scientific_name") or row["species_id"]
        for row in profiles.get("species_profiles", [])
        if isinstance(row, dict) and row.get("species_id")
    }
    model_names = {}
    for row in catalog.catalog_entries(registry):
        for estimator in row["estimator_ids"]:
            key = "/".join((row["version_id"], row["profile_id"], estimator))
            model_names[key] = " · ".join((_VERSION_SHORT_NAMES.get(row["version_id"], row["version_display_name"]),
                                          row["profile_display_name"], estimator_names.get(estimator, estimator)))
    revision = policy.revision(registry)
    options = "".join(f'<option value="{text(key)}">{text(name)}</option>'
                      for key, name in model_names.items())
    species_options = f'<option value="*">{label("all_species")}</option>' + "".join(
        f'<option value="{text(key)}">{text(name)}</option>'
        for key, name in sorted(names.items(), key=lambda item: item[1]))
    rules = []
    for row in registry.get(policy.FIELD, []):
        key = "/".join(row[field] for field in policy.IDENTITY[:3])
        species = label("all_species") if row["species_id"] == "*" else text(names.get(row["species_id"], row["species_id"]))
        rules.append(f'''<tr><td>{text(model_names.get(key, key))}</td><td>{species}</td>
          <td>{text(row['reason'])}<br><small>{text(row['updated_at'])}</small></td>
          <td><form method="post" action="">
            <input type="hidden" name="worker_action" value="set_prediction_model_policy">
            <input type="hidden" name="policy_revision" value="{revision}">
            <input type="hidden" name="model_key" value="{text(key)}">
            <input type="hidden" name="species_scope" value="{text(row['species_id'])}">
            <input type="hidden" name="model_enabled" value="true">
            <button type="submit">{label('reactivate')}</button></form></td></tr>''')
    table = (f'<div style="overflow-x:auto"><table><thead><tr><th>{label("model")}</th>'
             f'<th>{label("scope")}</th><th>{label("reason")}</th><th></th></tr></thead>'
             f'<tbody>{"".join(rules)}</tbody></table></div>') if rules else f'<p>{label("none")}</p>'
    return f'''<section class="workers-panel" id="prediction-model-settings">
      <details open><summary><strong>{label('title')}</strong> · {len(rules)} {label('suspended')}</summary>
      <p class="meta">{label('help')}</p>{table}
      <form method="post" action="" style="display:grid;gap:10px;max-width:850px">
        <input type="hidden" name="worker_action" value="set_prediction_model_policy">
        <input type="hidden" name="policy_revision" value="{revision}">
        <input type="hidden" name="model_enabled" value="false">
        <label>{label('model')}<select name="model_key" style="width:100%;max-width:100%">{options}</select></label>
        <label>{label('scope')}<select name="species_scope" style="width:100%">{species_options}</select></label>
        <label>{label('reason')}<input name="suspension_reason" required maxlength="500" style="width:100%;font-size:16px"></label>
        <button type="submit">{label('suspend')}</button>
      </form></details></section>'''
