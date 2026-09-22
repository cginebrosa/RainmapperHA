"""Small serving-policy editor; no model fitting or artifact scans on page load."""
from __future__ import annotations

from html import escape

from mushroom_profiles_ui import ui_label
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_prediction_policy as policy
from rainmapper_core import mushroom_recommendation_policy as recommendations


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
    mode = recommendations.settings(registry)["mode"]
    recommendation_options = "".join(
        f'<option value="{m}" {"selected" if m == mode else ""}>{label("recommendation_" + m)}</option>'
        for m in recommendations.MODES)
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
      <details><summary><strong>{label('title')}</strong> · {len(rules)} {label('suspended')}</summary>
      <form method="post" action="" style="display:grid;gap:10px;max-width:850px">
        <input type="hidden" name="worker_action" value="set_recommendation_policy">
        <input type="hidden" name="policy_revision" value="{revision}">
        <label>{label('recommendation_title')}<select name="recommendation_mode">{recommendation_options}</select></label>
        <p class="meta">{label('recommendation_help')}</p>
        <button type="submit">{label('recommendation_save')}</button>
      </form>
      <p class="meta">{label('help')}</p>{table}
      <p><a href="./workers/model-policy.json">{label('export')}</a></p>
      <details><summary>{label('import')}</summary>
        <p class="meta">{label('transfer_help')}</p>
        <form method="post" action="./workers/model-policy" style="display:grid;gap:10px;max-width:850px">
          <input type="hidden" name="policy_revision" value="{revision}">
          <label>{label('import_file')}<input type="file" accept=".json,application/json" id="model-policy-file"></label>
          <label>{label('json')}<textarea id="model-policy-json" name="policy_json" required rows="8"
            style="width:100%;font-size:16px" maxlength="262144"></textarea></label>
          <p id="model-policy-preview" role="status"></p>
          <label><input type="checkbox" name="confirm_replace" value="true" required> {label('confirm_replace')}</label>
          <button type="submit">{label('import_apply')}</button>
        </form>
      </details>
      <form method="post" action="" style="display:grid;gap:10px;max-width:850px">
        <input type="hidden" name="worker_action" value="set_prediction_model_policy">
        <input type="hidden" name="policy_revision" value="{revision}">
        <input type="hidden" name="model_enabled" value="false">
        <label>{label('model')}<select name="model_key" style="width:100%;max-width:100%">{options}</select></label>
        <label>{label('scope')}<select name="species_scope" style="width:100%">{species_options}</select></label>
        <label>{label('reason')}<input name="suspension_reason" required maxlength="500" style="width:100%;font-size:16px"></label>
        <button type="submit">{label('suspend')}</button>
      </form></details></section>
      <script>
      (() => {{
        const file = document.getElementById('model-policy-file');
        const input = document.getElementById('model-policy-json');
        const preview = document.getElementById('model-policy-preview');
        function check() {{
          file.form.querySelector('[name=confirm_replace]').checked = false;
          try {{
            const value = JSON.parse(input.value);
            if (value.kind !== 'mushroom_ml_prediction_policy' || !Array.isArray(value.suspensions)) throw new Error();
            preview.textContent = value.suspensions.length + ' {label('suspended')}';
            input.setCustomValidity('');
          }} catch (_) {{
            preview.textContent = '{label('invalid_file')}';
            input.setCustomValidity('{label('invalid_file')}');
          }}
        }}
        input.addEventListener('input', check);
        file.addEventListener('change', async () => {{
          const selected = file.files[0];
          input.value = '';
          if (selected && selected.size <= 262144) input.value = await selected.text();
          check();
        }});
      }})();
      </script>'''
