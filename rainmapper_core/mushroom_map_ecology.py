"""Small, resident ecological window evaluator shared by HA and workers.

No probabilities, web requests, GIS scans, model training or data writes.
Profiles and accepted exact mappings remain the editable sources of truth.
"""
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import threading
from rainmapper_core.mushroom_phenology import season_phase_for_months

POLICY = 'territorial_and_seasonal_windows_v6'
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PROFILES = 32
MAX_MAPPING_RULES = 512
MAX_MAPPING_CODES = 2048
POSITIVE = {'primary', 'preferred', 'secondary', 'possible', 'present'}
MAPPING_CATALOGS = {'mapped_host_ids':'host_taxa', 'mapped_forest_type_ids':'forest_types',
                    'mapped_soil_tendency_ids':'soil_types', 'mapped_lithology_ids':'lithology_types',
                    'mapped_habitat_feature_ids':'habitat_features'}


def territorial_candidates(ecology, species_ids=()):
    """One date-independent gate shared by input preparation and inference."""
    if ecology.get('status') != 'available' or ecology.get('abstention_reason'):
        return []
    rows = ecology.get('species', [])
    if not isinstance(rows, list) or len(rows) > MAX_PROFILES:
        raise ValueError('point_species_limit')
    return [row for row in rows if row.get('status') == 'compatible'
            and (not species_ids or row['species_id'] in species_ids)]


def prediction_candidates(ecology, species_ids=()):
    """Keep territorial candidates with at least one in-season requested day."""
    return [row for row in territorial_candidates(ecology, species_ids)
            if any(phase in ('main', 'secondary') for phase in row.get('daily_season_phases', []))]


def mapping_key(row, value):
    identity = tuple(row.get(k) for k in ('source_id', 'edition', 'field'))
    if (any(not isinstance(v, str) or not v or len(v) > 128 for v in identity)
            or type(value) not in (str, int) or not str(value) or len(str(value)) > 128):
        return None
    # Older map publications used a map-only alias for this same product.
    # Adapt it here, keeping the editable source and reconstruction unchanged.
    if identity[0] == 'icgc_geologia_50000' and identity[2] == 'Codi':
        identity = ('geology_50000', *identity[1:])
    return (*identity, str(value))


def compile_exact_mappings(payload, ids):
    """Codes reference shared rules; never copy target lists per code or day."""
    exact = payload.get('exact_value_mappings', [])
    groups = payload.get('exact_value_mapping_groups', [])
    if not isinstance(exact, list) or not isinstance(groups, list) or len(exact)+len(groups) > MAX_MAPPING_RULES:
        raise ValueError('ecology_mapping_rule_limit')
    count = 0
    # Check cardinality before constructing the lookup index.
    for row in exact + groups:
        values = row.get('raw_values', [row.get('raw_value')])
        if not isinstance(values, list) or not values:
            raise ValueError('invalid_ecology_mapping_values')
        count += len(values)
    if count > MAX_MAPPING_CODES:
        raise ValueError('ecology_mapping_code_limit')
    index = {}
    for row in exact + groups:
        if row.get('review_status') != 'accepted':
            continue
        grouped = 'raw_values' in row
        if grouped and ('raw_value' in row or not row.get('review_ref')):
            raise ValueError('invalid_ecology_mapping_group')
        for field, group in MAPPING_CATALOGS.items():
            targets = row.get(field, [])
            if (not isinstance(targets, list) or len(targets) > 32 or
                    any(not isinstance(v, str) or v not in ids[group] for v in targets)):
                raise ValueError('unknown_ecology_mapping_id')
        for value in row.get('raw_values', [row.get('raw_value')]):
            key = mapping_key(row, value)
            if key is None:
                # Keep legacy, unversioned mappings in storage, but never apply
                # them to a point with missing product identity.
                if not grouped and not row.get('edition'):
                    continue
                raise ValueError('invalid_ecology_mapping_identity')
            if key in index:
                raise ValueError('duplicate_ecology_mapping')
            index[key] = row
    return index


def number(value):
    return value if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) else None


def stamp(path):
    stat = path.stat()
    return stat.st_ino, stat.st_size, stat.st_mtime_ns


def positive_ids(profile, field):
    return {row['id'] for row in profile.get('ecology', {}).get(field, [])
            if row.get('v0_active') is not False and row.get('relationship') in POSITIVE}


def validate_soil_filter(rule, soil_ids):
    """Optional reviewed policy, independent of qualitative affinity weights."""
    if not isinstance(rule, dict) or set(rule) - {
            'accepted_soil_ids', 'excluded_soil_ids', 'ph_override_blocked_soil_ids',
            'conditional_soil_ids', 'require_soil_context', 'ph_conflict', 'review_ref'}:
        raise ValueError('invalid_soil_filter')
    for field in ('accepted_soil_ids', 'excluded_soil_ids', 'ph_override_blocked_soil_ids',
                  'conditional_soil_ids'):
        values = rule.get(field, [])
        if (not isinstance(values, list) or len(values) > 32 or
                any(not isinstance(v, str) or v not in soil_ids for v in values)):
            raise ValueError('invalid_soil_filter_ids')
    if set(rule.get('accepted_soil_ids', [])) & set(rule.get('excluded_soil_ids', [])):
        raise ValueError('conflicting_soil_filter_ids')
    if set(rule.get('conditional_soil_ids', [])) & set(rule.get('excluded_soil_ids', [])):
        raise ValueError('conflicting_soil_filter_ids')
    if type(rule.get('require_soil_context', False)) is not bool:
        raise ValueError('invalid_soil_context_requirement')
    if rule.get('ph_conflict', 'strict') not in ('strict', 'estimated_interval_overlap'):
        raise ValueError('invalid_soil_ph_conflict')
    if (not isinstance(rule.get('review_ref'), str) or not rule['review_ref'].strip()
            or len(rule['review_ref']) > 512):
        raise ValueError('soil_filter_review_required')


def soil_ph_override(rule, soil, ph, low, high):
    """A GIS preference can qualify an estimate, never replace a missing pH."""
    if (rule.get('ph_conflict') != 'estimated_interval_overlap'
            or not soil.intersection(rule.get('accepted_soil_ids', []))
            or soil.intersection(rule.get('excluded_soil_ids', []))
            or soil.intersection(rule.get('ph_override_blocked_soil_ids', []))
            or ph.get('source') != 'openlandmap'):
        return False
    a, b = number(ph.get('uncertainty_lower')), number(ph.get('uncertainty_upper'))
    value = number(ph.get('lower'))
    return (a is not None and b is not None and value is not None
            and 0 < a <= value <= b <= 14
            and (low is None or b >= low) and (high is None or a <= high))


class EcologyReader:
    def __init__(self, profiles, catalogs, mappings, *, ph_source='soilgrids'):
        if ph_source not in ('soilgrids','openlandmap'):
            raise ValueError('invalid_ecology_ph_source')
        self.ph_source = ph_source
        self.paths = tuple(Path(p).resolve() for p in (profiles, catalogs, mappings))
        self.lock = threading.Lock()
        self.identity = None
        self._refresh()

    def _refresh(self):
        identity = tuple(stamp(p) for p in self.paths)
        if identity == self.identity:
            return
        payloads, digest = [], sha256(self.ph_source.encode())
        for file_index, path in enumerate(self.paths):
            with path.open('rb') as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError('ecology_file_limit')
            digest.update(raw)
            payloads.append(json.loads(raw))
            if file_index == 1:
                catalog_revision = sha256(raw).hexdigest()[:20]
        profiles = payloads[0]['species_profiles']
        catalogs = payloads[1]['catalogs']
        if not isinstance(profiles, list) or len(profiles) > MAX_PROFILES:
            raise ValueError('ecology_cardinality_limit')
        ids = {group: {row['id'] for row in rows} for group, rows in catalogs.items()}
        hosts = {row['id']: row for row in catalogs['host_taxa']}
        if sum(len(v) for v in ids.values()) > 4096 or len(hosts) > 1024:
            raise ValueError('ecology_catalog_limit')
        ancestors = {}
        for host in hosts:
            seen, parent = set(), hosts[host].get('parent_id')
            while parent:
                if parent == host or parent in seen or parent not in hosts:
                    raise ValueError('invalid_host_hierarchy')
                seen.add(parent)
                parent = hosts[parent].get('parent_id')
            ancestors[host] = seen
        profile_ids = set()
        fields = {'host_affinities':'host_taxa', 'forest_type_affinities':'forest_types',
                  'soil_affinities':'soil_types', 'lithology_affinities':'lithology_types',
                  'habitat_feature_affinities':'habitat_features'}
        for profile in profiles:
            sid = profile['species_id']
            if sid in profile_ids:
                raise ValueError('duplicate_ecology_species')
            profile_ids.add(sid)
            if 'soil_filter' in profile['ecology']:
                validate_soil_filter(profile['ecology']['soil_filter'], ids['soil_types'])
            for field, group in fields.items():
                if any(row['id'] not in ids[group] for row in profile['ecology'].get(field, [])):
                    raise ValueError('unknown_ecology_id')
            months = profile['phenology']['main_months'] + profile['phenology']['secondary_months']
            if any(type(m) is not int or not 1 <= m <= 12 for m in months):
                raise ValueError('invalid_ecology_month')
            for block, low, high in (('ecology','ph_min','ph_max'), ('topography','altitude_min_m','altitude_max_m')):
                a,b = profile[block].get(low),profile[block].get(high)
                if any(v is not None and number(v) is None for v in (a,b)) or (a is not None and b is not None and a>b):
                    raise ValueError('invalid_ecology_bounds')
                if block=='ecology' and any(v is not None and not 0<=v<=14 for v in (a,b)):
                    raise ValueError('invalid_ecology_ph')
        mapping_index = compile_exact_mappings(payloads[2], ids)
        if tuple(stamp(p) for p in self.paths) != identity:
            raise ValueError('ecology_changed_during_read')
        self.profiles, self.hosts, self.ancestors = profiles, hosts, ancestors
        self.mappings, self.revision, self.identity = mapping_index, digest.hexdigest()[:20], identity
        # Hash the exact catalog bytes already read, not a normalized second copy.
        self.catalog_revision = catalog_revision
        self.context_labels = {group:{row['id']:row.get('label', {}) for row in catalogs[group]}
                               for group in ('forest_types', 'soil_types', 'lithology_types')}

    def host_matches(self, observed, required):
        if observed not in self.hosts or required not in self.hosts:
            return False
        return (observed == required or required in self.ancestors[observed] or
                (self.hosts[observed].get('rank') == 'genus' and observed in self.ancestors[required]))

    def evaluate(self, geography, start_date, horizon_days=7):
        if type(horizon_days) is not int or not 1 <= horizon_days <= 7:
            raise ValueError('invalid_ecology_horizon')
        start = date.fromisoformat(start_date)
        days = [start+timedelta(days=i) for i in range(horizon_days)]
        with self.lock:
            try:
                self._refresh()
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                # Never continue with stale rules after a partial/invalid edit.
                return {'status':'unavailable','policy':POLICY,'species':[]}
            land = geography.get('land_context', {})
            trees = land.get('trees', {})
            if (trees.get('source_id') == 'mfe25' and trees.get('status') == 'available'
                    and trees.get('catalog_status') != 'unavailable'
                    and trees.get('catalog_revision') != self.catalog_revision):
                return {'status':'unavailable','policy':POLICY,'species':[],
                        'reason':'host_catalog_mismatch'}
            observed = {row.get('host_id') for row in trees.get('items', []) if row.get('host_id') in self.hosts} if trees.get('status')=='available' and trees.get('catalog_status')!='unavailable' else set()
            forest, soil, lithology, mapping_states = set(), set(), set(), {}
            for kind in ('vegetation','geology'):
                row = land.get(kind,{})
                key = mapping_key(row, row.get('code'))
                mapped = self.mappings.get(key) if row.get('status')=='available' else None
                mapping_states[kind] = 'accepted' if mapped else 'unresolved'
                if mapped:
                    observed.update(mapped.get('mapped_host_ids',[]))
                    forest.update(mapped.get('mapped_forest_type_ids',[]))
                    soil.update(mapped.get('mapped_soil_tendency_ids',[]))
                    lithology.update(mapped.get('mapped_lithology_ids',[]))
            context_available = bool(observed or forest)
            terrain = geography.get('terrain', {})
            elevation = terrain.get('elevation', {})
            altitude = number(elevation.get('value_m')) if elevation.get('status')=='available' else None
            if self.ph_source == 'openlandmap':
                context = terrain.get('ph_openlandmap',{})
                value = number(context.get('estimate')) if context.get('status') in ('available','partial') else None
                # Compare a point estimate with species bounds. The original
                # uncertainty remains untouched in terrain.ph_openlandmap.
                ph = {'status':context.get('status'),'lower':value,'upper':value,
                      'source':'openlandmap', 'uncertainty_lower':context.get('lower'),
                      'uncertainty_upper':context.get('upper')}
            else:
                ph = next((d for d in terrain.get('ph',{}).get('depths',[]) if d.get('depth_cm')==[0,5]), {})
            rows = [self._species(p, observed, forest, soil, lithology, altitude, ph, days) for p in self.profiles]
            if not context_available:
                # Hosts remain mandatory for ectomycorrhizal species; a reviewed
                # habitat can independently support non-ectomycorrhizal profiles.
                for row in rows:
                    row.update(status='unknown', daily_statuses=['unknown']*len(days),
                               admission=None, reasons=['terrain_context_missing'], matched_host_ids=[])
            return {'status':'available','policy':POLICY,'revision':self.revision,
                    'ph_selection':{'source':self.ph_source,
                                    'statistic':'mean' if self.ph_source=='openlandmap' else 'interval'},
                    'dates':[d.isoformat() for d in days],'mapping_states':mapping_states,'species':rows,
                    'mapped_context':{
                        name:[{'id':key,'label':dict(self.context_labels[group][key])} for key in sorted(values)]
                        for name,group,values in (('habitats','forest_types',forest),
                                                 ('soil_tendencies','soil_types',soil),
                                                 ('lithologies','lithology_types',lithology))},
                    'abstention_reason':None if context_available else 'terrain_context_missing'}

    def _species(self, profile, observed, forest, soil, lithology, altitude, ph, days):
        ecology, topo = profile['ecology'], profile['topography']
        reasons, states = [], []
        soil_rule = ecology.get('soil_filter', {})
        soil_accepted = soil.intersection(soil_rule.get('accepted_soil_ids', []))
        soil_excluded = soil.intersection(soil_rule.get('excluded_soil_ids', []))
        if soil_excluded:
            # Mixed units do not locate either constituent at the exact setal.
            states.append('unknown' if soil_accepted else 'incompatible')
            reasons.append('soil_mixed_conflict' if soil_accepted else 'soil_excluded')
        elif soil_accepted:
            reasons.append('soil_accepted')
        elif soil_rule:
            reasons.append('soil_unresolved' if not soil else 'soil_not_listed')
        if soil_rule.get('require_soil_context') and not soil:
            # An information gap is abstention, never proof of biological absence.
            states.append('unknown')
        # A confirmed accepted component already supports admission in a mixed
        # unit. The extra conditional component must not add a warning by itself.
        # Explicit exclusions above and the independent pH checks still apply.
        soil_conditional = not soil_accepted and bool(
            soil.intersection(soil_rule.get('conditional_soil_ids', [])))
        hosts = positive_ids(profile,'host_affinities')
        matching = sorted(h for h in observed if any(self.host_matches(h,r) for r in hosts))
        grassland = ecology.get('trophic_mode_id') != 'trophic_ectomycorrhizal'
        if grassland:
            habitat_ok = bool(forest & positive_ids(profile,'forest_type_affinities'))
            reasons.append('habitat_match' if habitat_ok else 'habitat_unknown')
            states.append('compatible' if habitat_ok else 'unknown')
        else:
            reasons.append('hosts_match' if matching else 'hosts_unknown')
            states.append('compatible' if matching else 'unknown')
        minimum, maximum = topo.get('altitude_min_m'),topo.get('altitude_max_m')
        if minimum is not None or maximum is not None:
            if altitude is None:
                states.append('unknown'); reasons.append('altitude_unknown')
            elif (minimum is not None and altitude<minimum) or (maximum is not None and altitude>maximum):
                states.append('incompatible'); reasons.append('altitude_outside')
            else:
                reasons.append('altitude_match')
        else:
            reasons.append('altitude_unbounded')
        low, high = ecology.get('ph_min'),ecology.get('ph_max')
        if low is None and high is None:
            reasons.append('ph_unbounded')
        else:
            a,b = number(ph.get('lower')),number(ph.get('upper'))
            if ph.get('status') not in ('available','partial') or a is None or b is None or not 0<a<=b<=14:
                states.append('unknown'); reasons.append('ph_unknown')
            elif (low is not None and b<low) or (high is not None and a>high):
                if soil_ph_override(soil_rule, soil, ph, low, high):
                    reasons.append('ph_conflict_soil_supported')
                else:
                    states.append('incompatible'); reasons.append('ph_outside')
            elif (low is not None and a<low) or (high is not None and b>high):
                states.append('unknown'); reasons.append('ph_overlap')
            else:
                reasons.append('ph_match')
                if soil_conditional:
                    reasons.append('soil_ph_conditional')
        if soil & positive_ids(profile,'soil_affinities'): reasons.append('soil_preference_match')
        if lithology & positive_ids(profile,'lithology_affinities'): reasons.append('lithology_preference_match')
        base = 'incompatible' if 'incompatible' in states else 'unknown' if 'unknown' in states else 'compatible'
        conditional = any(r in reasons for r in ('ph_conflict_soil_supported',
                                                 'soil_ph_conditional', 'soil_not_listed'))
        # Daily projection retained for transport; phenology belongs to the predictor.
        daily = [base] * len(days)
        phenology = profile['phenology']
        phases = [season_phase_for_months(day, phenology['main_months'], phenology['secondary_months'])
                  for day in days]
        names = profile.get('common_names',[])
        return {'species_id':profile['species_id'],'name':profile.get('metadata',{}).get('map_display_name') or (names[0] if isinstance(names,list) and names else profile['scientific_name']),
                'scientific_name':profile['scientific_name'],'status':base,'daily_statuses':daily,
                'daily_season_phases':phases,
                'admission':('conditional' if conditional else 'standard') if base == 'compatible' else None,
                'soil_filter_review_ref':soil_rule.get('review_ref'),
                'reasons':reasons,'matched_host_ids':matching}
