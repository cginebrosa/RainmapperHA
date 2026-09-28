"""One field-wise source policy for recovered observations and map predictions.

Inputs contain only accepted mappings. Empty values allow fallback; conflicting
explicit substrate classes are retained as a conflict, not silently resolved.
No geographic reads, label heuristics, or changes to user field evidence.
"""
POLICY = 'territorial_sources_v1'
PRIORITIES = {
    'host_ids': ('mfe25', 'mvc50'),
    'forest_type_ids': ('mvc50', 'icgc_cobertes_2024'),
    'soil_tendency_ids': ('mvc50', 'geology_50000'),
    'habitat_feature_ids': ('mvc50', 'icgc_cobertes_2024'),
    'lithology_ids': ('geology_50000',),
}
# Only unambiguous artificial/water classes: a grassland/shrub polygon is not
# proof that all trees are absent. Codes belong to ICGC Cobertes 2024 nivell_2.
NON_FOREST_COVER = frozenset(('341', '342', '347', '349', '351', '353', '354', '355',
                              '461', '462', '464', '465', '466'))


def resolve_context(candidates, *, cover=None):
    values, sources, conflicts = {}, {}, []
    for field, order in PRIORITIES.items():
        choices = [(source, sorted(set(candidates.get(source, {}).get(field, []))))
                   for source in order]
        populated = [(source, ids) for source, ids in choices if ids]
        source, ids = populated[0] if populated else (None, [])
        values[field], sources[field] = ids, [source] if source else []
        if field == 'soil_tendency_ids' and len(populated) > 1:
            classes = {'soil_siliceous', 'soil_calcareous'}
            a, b = set(populated[0][1]) & classes, set(populated[1][1]) & classes
            if a and b and a.isdisjoint(b):
                conflicts.append({'field': field, 'reason': 'contradictory_substrate',
                                  'sources': [s for s, _ in populated]})
                # Both explicit classes must reach ecological conflict handling.
                values[field] = sorted(set(ids).union(*(v for _, v in populated)))
                sources[field] = [s for s, _ in populated]
    if (cover and cover.get('status') == 'available'
            and cover.get('source_id') == 'icgc_cobertes_2024'
            and cover.get('edition') == '2024' and cover.get('field') == 'nivell_2'
            and str(cover.get('code')) in NON_FOREST_COVER
            and (values['host_ids'] or values['forest_type_ids'])):
        conflicts.append({'field': 'forest_type_ids', 'reason': 'non_forest_cover_conflict',
                          'sources': list(dict.fromkeys(sources['host_ids'] + sources['forest_type_ids']
                                                       + ['icgc_cobertes_2024']))})
    return {'policy': POLICY, 'values': values, 'sources': sources, 'conflicts': conflicts}


def layer_candidates(layers):
    """Adapt the GIS reconstruction vocabulary without accepting pending values."""
    return {source: {field: mapped.get('mapped_' + field, []) for field in PRIORITIES}
            for source, layer in layers.items() if isinstance(layer, dict)
            and isinstance(mapped := layer.get('mapped'), dict)
            and not mapped.get('invalid_references')}
