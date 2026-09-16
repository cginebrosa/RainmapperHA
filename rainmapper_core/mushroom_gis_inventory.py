"""Small source inventory and lossless editing of grouped GIS mappings.

The inventory is display metadata, never an alternative classification source.
Only mushroom_gis_mappings.json carries operational decisions.
"""
from functools import lru_cache
import json
from pathlib import Path

TARGET_FIELDS = ('mapped_host_ids', 'mapped_forest_type_ids', 'mapped_soil_tendency_ids',
                 'mapped_lithology_ids', 'mapped_habitat_feature_ids')
GEOLOGY_PRODUCT = ('geology_50000', '2024-12', 'Codi')


@lru_cache(maxsize=1)
def source_inventory():
    path = Path(__file__).with_name('data') / 'gis-value-inventory.json'
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('GIS inventory size limit')
    data = json.loads(path.read_text())
    if sum(len(s['values']) for s in data['sources']) > 4096:
        raise ValueError('GIS inventory value limit')
    return data['sources']


def identity(row):
    return tuple(str(row.get(k, '') or '') for k in ('source_id', 'edition', 'field', 'raw_value'))


def logical_mappings(payload):
    """Expand codes for maintenance, sharing target lists and other metadata."""
    for row in payload.get('exact_value_mappings', []):
        if isinstance(row, dict):
            yield row
    for group in payload.get('exact_value_mapping_groups', []):
        if not isinstance(group, dict):
            continue
        base = {k: v for k, v in group.items() if k != 'raw_values'}
        for code in group.get('raw_values', []):
            yield dict(base, raw_value=code)


def upsert_mapping(payload, replacement):
    """Split only the edited code; preserve siblings, editions and provenance."""
    exact = payload.get('exact_value_mappings', [])
    groups = payload.get('exact_value_mapping_groups', [])
    if not isinstance(exact, list) or not isinstance(groups, list):
        raise ValueError('GIS mappings and groups must be lists')
    key = identity(replacement)
    matches = [row for row in logical_mappings(payload) if identity(row) == key]
    if len(matches) > 1:
        raise ValueError('Duplicate GIS mapping identity; resolve before editing')
    merged = dict(matches[0]) if matches else {}
    # Checkbox omissions mean deselection, not preservation of old targets.
    for field in (*TARGET_FIELDS, 'notes', 'review_ref'):
        merged.pop(field, None)
    merged.update(replacement)
    new_groups = []
    for group in groups:
        if isinstance(group, dict) and identity(dict(group, raw_value=key[3])) == key:
            remaining = [v for v in group.get('raw_values', []) if str(v) != key[3]]
            if remaining:
                new_groups.append(dict(group, raw_values=remaining))
        else:
            new_groups.append(group)
    new_exact = [row for row in exact if not isinstance(row, dict) or identity(row) != key]
    new_exact.append(merged)
    # Validate the map contract before changing the caller's payload.
    if len(new_exact) + len(new_groups) > 512:
        raise ValueError('GIS rule budget exceeded; regroup reviewed equivalences before saving')
    payload['exact_value_mappings'] = new_exact
    if 'exact_value_mapping_groups' in payload:
        payload['exact_value_mapping_groups'] = new_groups
