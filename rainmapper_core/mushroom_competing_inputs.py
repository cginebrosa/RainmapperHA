"""Bounded change detection and immutable planning for historical selection."""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

from rainmapper_core import mushroom_competing_control as control
from rainmapper_core.mushroom_competing_history import FAMILY_FIELDS, canonical, digest
from rainmapper_core.mushroom_map_competing import identity

TARGETS = ('boletus_aereus', 'amanita_caesarea')

# Exact source transition reviewed against f609f8ec: the changed functions
# serve Predictor preparation only. Historical Builder uses the unchanged
# _weather_requirements/_interpretation_features helpers. Real Builder parity
# covers V2--V6 fixed/lag inputs; an unknown future file hash is never aliased.
_REVIEWED_RUNTIME_FILE_HASHES = {
    ('mushroom_ml_multiversion_comparison.py',
     '2194d3aa92755919df9c728ba3e1dfcbc656a8b34c399f4678e7e8c93d353f31'):
    '1e97478f1838a0a426fac53f454c08820adc971fcbdbfea971abb6e52b522a32',
}


def _procedure_files():
    core = Path(__file__).parent
    code = sorted(core.glob('mushroom_competing_*.py')) + sorted(core.glob('mushroom_ml_*.py'))
    code += [core / name for name in ('mushroom_observations.py', 'mushroom_training_observations.py',
             'mushroom_observation_features.py', 'mushroom_observation_context.py', 'mushroom_known_sites.py',
             'mushroom_weather_idw.py', 'mushroom_weather_series.py', 'mushroom_water_physics.py', 'mushroom_soil_water_state.py',
             'mushroom_climatic_water_balance.py', 'mushroom_phenology.py', 'weather_history_dataset.py',
             'mushroom_map_competing.py', 'mushroom_map_prediction.py', 'mushroom_predictor_precompute.py',
             'mushroom_recommendation_policy.py', 'mushroom_prediction_interpretation.py')]
    code += [core.parent / 'scripts' / name for name in ('run-mushroom-competing-history.py',
             'build-biology-v3-benchmark.py','build-biology-v4-benchmark.py','build-biology-v5-raw-benchmark.py')]
    return code


def procedure_revision():
    """Same production code identity in coordinator and worker images."""
    return digest([(p.name,file_hash(p)) for p in _procedure_files()])


def runtime_feature_revision():
    """Feature producers have a narrower identity than selection/replay.

    A change to ranking or fit reuse must not rebuild unchanged weather/X.
    Keep all ML modules, numerical builders, physics and feature-cache adapters;
    new unreviewed modules are included by default, not implicitly trusted.
    """
    non_producers = {
        'mushroom_competing_comparison.py', 'mushroom_competing_control.py',
        'mushroom_competing_columns.py', 'mushroom_competing_audit.py',
        'mushroom_competing_statistics.py',
        'mushroom_competing_batch.py', 'mushroom_competing_parallel.py',
        'mushroom_competing_evidence.py', 'mushroom_competing_fits.py',
        'mushroom_competing_fit_scheduler.py',
        'mushroom_competing_history.py', 'mushroom_competing_inputs.py',
        'mushroom_competing_replay.py', 'mushroom_competing_tuning.py',
        'mushroom_map_competing.py', 'mushroom_map_prediction.py',
        'mushroom_predictor_precompute.py', 'run-mushroom-competing-history.py',
    }
    producers = []
    for path in _procedure_files():
        if path.name not in non_producers:
            source_hash = file_hash(path)
            producers.append((path.name, _REVIEWED_RUNTIME_FILE_HASHES.get(
                (path.name, source_hash), source_hash)))
    return digest(['historical_runtime_features_v1', producers])


def read_json(path, limit):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('history_input_limit')
    return json.loads(raw)


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def historical_weather_revision(data_dir, observations, cache_path):
    """Hash only historical date intervals, never rain after the last case.

    Immutable partition hashes cache prior scans. Boundary partitions are read
    in bounded batches so a new day appended to the current year does not by
    itself invalidate the history. Changed unused stations can conservatively
    request a check; the worker's feature keys still prevent redundant fits.
    """
    import pyarrow.parquet as pq
    from rainmapper_core import weather_history_dataset as dataset
    generation = dataset.resolve_weather_generation(Path(data_dir), verify_hashes=False)
    dates = []
    for row in observations:
        value = str(row.get('observed_at', ''))[:10]
        if value:
            dates.append(date.fromisoformat(value))
    if not dates:
        raise ValueError('history_has_no_observation_dates')
    intervals = []
    for d in sorted(set(dates)):
        start, end = d - timedelta(days=377), d - timedelta(days=1)
        if intervals and start <= intervals[-1][1] + timedelta(days=1):
            intervals[-1][1] = max(end, intervals[-1][1])
        else:
            intervals.append([start, end])
    windows = [(a.strftime('%Y%m%d'), b.strftime('%Y%m%d')) for a,b in intervals]
    cache_path = Path(cache_path)
    cache = read_json(cache_path, 256 * 1024) if cache_path.is_file() else {}
    next_cache = {}; parts = []
    for partition in generation.partitions:
        if not any(a <= partition.max_local_date and b >= partition.min_local_date for a,b in windows):
            continue
        key = digest([partition.sha256, windows])
        sha = cache.get(key)
        if any(a <= f'{partition.year:04d}0101' and b >= f'{partition.year:04d}1231' for a,b in windows):
            # Full immutable historical years need no scan at all.
            sha = partition.sha256
        if sha is None:
            h = hashlib.sha256()
            source = pq.ParquetFile(generation.object_path(partition.path))
            columns = [c for c in source.schema_arrow.names if c not in
                       {'reading_datetime','last_reading','station_name','county','municipality','province','local_time'}]
            for batch in source.iter_batches(batch_size=512, columns=columns, use_threads=False):
                for row in batch.to_pylist():
                    d = str(row['local_date']).replace('-', '')[:8]
                    if any(a <= d <= b for a,b in windows):
                        h.update(json.dumps(row, sort_keys=True, separators=(',', ':'), default=str,
                                            allow_nan=False).encode())
            sha = h.hexdigest()
        next_cache[key] = sha
        parts.append([partition.source, partition.year, sha])
    # Only cache current immutable partitions; this is a tiny memo, not source data.
    if cache != next_cache:
        raw = canonical(next_cache)
        if len(raw) > 256 * 1024:
            raise ValueError('history_revision_cache_limit')
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix('.tmp')
        temporary.write_bytes(raw); temporary.replace(cache_path)
    return digest(parts)


def plan(*, registry_path, models_root, observations_path, known_sites_path, stations_path,
         features_path, weather_data_dir, weather_cache_path, cutoff, profiles_path=None,
         comparison_k=None, comparison_ks=None):
    from rainmapper_core import mushroom_ml_version_registry as versions
    from rainmapper_core import mushroom_ml_model_catalog as catalog
    from rainmapper_core import mushroom_ml_policy_store as policy_store
    from rainmapper_core import mushroom_recommendation_policy as recommendations
    from rainmapper_core import mushroom_ml_prediction_policy as policy
    from rainmapper_core import mushroom_map_competing as competing
    from rainmapper_core.mushroom_map_model_runtime import projected_quality
    if comparison_k is not None and comparison_ks is not None:
        raise ValueError('ambiguous_comparison_ks')
    required_ks = control.normalize_ks(comparison_ks if comparison_ks is not None else
        [competing.defaults()['k_value'] if comparison_k is None else comparison_k])
    registry = policy_store.resolve(Path(registry_path), read_json(registry_path, 256 * 1024))
    profiles_path = Path(profiles_path) if profiles_path else Path(registry_path).parent / 'mushroom_profiles.json'
    profiles = {p['species_id']: {'phenology': p.get('phenology', {})}
                for p in read_json(profiles_path, 2 * 1024 * 1024)['species_profiles'] if p['species_id'] in TARGETS}
    root = Path(models_root)
    path = versions.operational_manifest_path(registry, models_root=root)
    if path is None:
        raise ValueError('No installed model batch for historical selection.')
    manifest = read_json(path, 2 * 1024 * 1024)
    quality_ref = manifest['quality_catalog']
    quality = projected_quality(root / quality_ref['path'], quality_ref['sha256'])
    wanted = {(row['species_id'], identity(entry['candidate']))
              for row in quality['species_selections'] if row['species_id'] in TARGETS
              for entry in row.get('candidate_chain', [])}
    if not wanted or len(wanted) > 4096:
        raise ValueError('No bounded candidate set for historical selection.')
    references = {}
    for sid, candidate in wanted:
        matching = [a['artifact_ref'] for a in manifest['artifacts']
                    if a['artifact_ref']['species_id'] in (sid, 'all_species') and
                    (a['artifact_ref']['version_id'], a['artifact_ref']['profile_id'],
                     a['artifact_ref']['temporal_contract_id'], a['artifact_ref']['estimator_id']) ==
                    (candidate[0], candidate[1], candidate[2], candidate[4])]
        if len(matching) != 1:
            raise ValueError('Historical candidate does not resolve to one installed family.')
        ref = matching[0]
        references[tuple(ref[k] for k in FAMILY_FIELDS)] = ref
    observations = read_json(observations_path, 16 * 1024 * 1024)['observations']
    if not isinstance(observations, list) or len(observations) > 10000:
        raise ValueError('history_observation_limit')
    observations = [r for r in observations if str(r.get('observed_at',''))[:10] < cutoff]
    # Keep semantic source fields and omit photo/observer display metadata.
    fields = ('observation_id','species_id','micro_area_id','observed_at','location','flush_abundance',
              'source','source_quality','validation_status','calibration_use','calibration_exclusion_reason',
              'site_context','altitude','derived')
    semantic = sorted([{k:r.get(k) for k in fields} for r in observations], key=lambda r:r['observation_id'])
    dependencies = {'observations':digest(semantic), 'models':file_hash(path),
                    'registry':digest(registry), 'known_sites':file_hash(known_sites_path),
                    'profiles': digest(profiles),
                    'stations':file_hash(stations_path), 'features':file_hash(features_path),
                    'weather':historical_weather_revision(weather_data_dir, observations, weather_cache_path)}
    dependencies['procedure'] = procedure_revision()
    history_revision = control.revision(dependencies)
    dependencies['comparison_ks'] = digest(required_ks)
    spec = {'kind':'competing_history_job_v2', 'revision':control.revision(dependencies),
            'history_revision':history_revision, 'required_ks':required_ks,
            'comparison_ks':required_ks, 'profiles':profiles,
            'recommendation_policy':recommendations.settings(registry),
            'prediction_model_suspensions':registry.get(policy.FIELD, []),
            'catalog_profiles':[{key:p[key] for key in ('version_id','profile_id','input_requirements')}
                                for p in catalog.catalog_entries(registry)],
            'cutoff':cutoff, 'species_ids':list(TARGETS), 'references':list(references.values()),
            'procedure_revision':dependencies['procedure'],
            'eligible_candidates':[[sid,list(c)] for sid,c in sorted(wanted)],
            'manifest':{k:manifest[k] for k in ('batch_id','snapshot_id','quality_catalog')},
            'known_sites_path':'snapshot/inputs/extra/known-sites.json',
            'stations_path':'snapshot/inputs/extra/stations.txt',
            'observation_features_path':'snapshot/inputs/extra/observation-features.json',
            'observations_path':'snapshot/inputs/mushroom-data/mushroom_observations.json',
            'weather_data_dir':'snapshot/inputs/weather'}
    return spec, dependencies
