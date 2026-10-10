"""Worker-only temporal validation cache for competing model families.

This module never installs a model. A unit is one family/annual fold; its key
includes exactly the training and evaluation features it consumes. Changing K,
an observer's name or weather outside those features cannot invalidate a fit.
The coordinator should consume only the bounded sufficient-statistics result.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import time

PROTOCOL = 'competing_annual_temporal_v1'
MAX_SAMPLES = 50000
MAX_COLUMNS = 4096
MAX_UNITS = 10000
MAX_UNIT_BYTES = 2 * 1024 * 1024
MAX_CACHE_BYTES = 256 * 1024 * 1024
MAX_MATRIX_BYTES = 256 * 1024 * 1024
FAMILY_FIELDS = ('version_id', 'temporal_contract_id', 'profile_id', 'estimator_id', 'species_id')
SOURCE_FIELDS = ('observation_id', 'species_id', 'target_date', 'horizon_days',
                 'micro_area_id', 'area_id', 'validation_group_14d')
# Reviewed producers with the current binary row keys and source-window context.
# Only aggregation/cache lookup changed since these revisions; numerical fits
# and feature producers are identical. Do not add unreviewed code revisions.
COMPATIBLE_ROW_PROCEDURES = (
    'b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581',
    '93c1f890935a4d701d5a78b4e35d3151d32ad4dc10bd5dfef3a6f1f1ec339f1f',
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sample_identity(sample):
    m = sample['metadata']
    day = date.fromisoformat(m['target_date'])
    oid, sid = m['observation_id'], m['species_id']
    horizon = m['horizon_days']
    if (not isinstance(oid, str) or not oid or not isinstance(sid, str) or not sid
            or type(horizon) is not int or not 1 <= horizon <= 7):
        raise ValueError('invalid_history_sample_identity')
    return sid, oid, day, horizon


def partition(samples, year):
    """Strictly past training, cross-species site episodes and a 14-day gap.

    The boundary purge applies to whole episodes. No observation or horizon of
    an observation can occur on both sides. Missing site identity fails closed.
    """
    return PartitionPlan(samples).for_year(year)


class PartitionPlan:
    """Validate identities and site episodes once for all annual folds."""
    def __init__(self, samples):
        if len(samples) > MAX_SAMPLES:
            raise ValueError('history_sample_limit')
        identities, sites, groups = set(), defaultdict(list), defaultdict(list)
        ordered = []
        for sample in samples:
            identity = sample_identity(sample)
            sid, oid, day, horizon = identity
            if (sid,oid,horizon) in identities:
                raise ValueError('duplicate_history_sample')
            identities.add((sid,oid,horizon))
            m = sample['metadata']
            site, group = m.get('micro_area_id') or m.get('area_id'), m.get('validation_group_14d')
            if not site or not group:
                raise ValueError('missing_history_episode_identity')
            ordinal, row_id = day.toordinal(), id(sample)
            sites[str(site)].append((ordinal,row_id))
            groups[str(group)].append((ordinal,row_id))
            ordered.append((identity,sample))
        self.rows = [(identity[2].toordinal(),id(s),s) for identity,s in sorted(ordered,key=lambda r:r[0])]
        self.groups = [(min(d for d,_ in rows),max(d for d,_ in rows),tuple(i for _,i in rows))
                       for rows in groups.values()]
        self.episodes = []
        for rows in sites.values():
            episode, previous = [], None
            for day,row_id in sorted(rows,key=lambda r:r[0]):
                if previous is not None and day-previous > 14:
                    self.episodes.append(tuple(episode)); episode = []
                episode.append(row_id); previous = day
            if episode: self.episodes.append(tuple(episode))

    def for_year(self, year):
        start, end = date(year,1,1).toordinal(), date(year+1,1,1).toordinal()
        purged = set()
        for lo,hi,rows in self.groups:
            if any(lo <= boundary+14 and hi >= boundary-14 for boundary in (start,end)):
                purged.update(rows)
        for episode in self.episodes:
            if any(row in purged for row in episode):
                purged.update(episode)
        train, test, excluded = [], [], []
        for day,row_id,sample in self.rows:
            if row_id in purged:
                if start <= day < end: excluded.append(sample)
            elif day < start:
                train.append(sample)
            elif day < end:
                test.append(sample)
        return train, test, excluded


def _check_tensor(columns, train, test):
    required = set(columns)
    if not columns or len(columns) > MAX_COLUMNS or len(required) != len(columns):
        raise ValueError('history_column_limit')
    if (len(train) + len(test)) * len(columns) * 8 > MAX_MATRIX_BYTES:
        raise ValueError('history_matrix_limit')


def _tensor_row(columns, sample):
    from rainmapper_core.mushroom_ml_benchmark_io import ColumnarFeatures
    features = sample['predictive_features']
    if not (features.contains_all(columns) if isinstance(features, ColumnarFeatures)
            else set(columns).issubset(features)):
        raise ValueError('missing_history_feature')
    m = sample['metadata']
    if sample.get('prediction_target') not in ('favorable', 'unfavorable'):
        raise ValueError('invalid_history_target')
    values = (features.values_for(columns) if isinstance(features, ColumnarFeatures) else
              [features[c] for c in columns])
    return canonical([{k: m.get(k) for k in SOURCE_FIELDS}, sample['prediction_target'], values])


def _binary_tensor_row(columns, sample):
    """Exact consumed float64 values and null mask, without decimal JSON floats.

    JSON is retained for the small source identity. Null and missing remain
    distinct; non-finite supplied values fail as in the legacy JSON encoder.
    The versioned key never accepts a legacy digest as the same representation.
    """
    import numpy as np
    from rainmapper_core.mushroom_ml_benchmark_io import ColumnarFeatures
    features = sample['predictive_features']
    if isinstance(features, ColumnarFeatures):
        if not features.contains_all(columns):
            raise ValueError('missing_history_feature')
        indices, _ = features._projection(columns)
        values = features._values[features._row, indices].astype('<f8', copy=True)
        valid = features._valid[features._row, indices]
    else:
        if not set(columns).issubset(features):
            raise ValueError('missing_history_feature')
        raw = [features[c] for c in columns]
        valid = np.asarray([v is not None for v in raw], dtype=np.bool_)
        values = np.asarray([0. if v is None else v for v in raw], dtype='<f8')
    if not np.isfinite(values[valid]).all():
        raise ValueError('nonfinite_history_feature')
    values[~valid] = 0.
    target = sample.get('prediction_target')
    if target not in ('favorable', 'unfavorable'):
        raise ValueError('invalid_history_target')
    identity = canonical([{k:sample['metadata'].get(k) for k in SOURCE_FIELDS}, target])
    return identity + b'\0' + np.packbits(valid, bitorder='little').tobytes() + values.tobytes()


class RowFingerprints:
    """Hash each immutable feature row once, across annual training prefixes."""
    def __init__(self, columns):
        self.columns = tuple(columns)
        self.rows = {}

    def chunk(self, sample):
        key = id(sample)
        if key not in self.rows:
            if len(self.rows) >= MAX_SAMPLES:
                raise ValueError('history_sample_limit')
            self.rows[key] = sample, hashlib.sha256(_binary_tensor_row(self.columns,sample)).digest()
        # Retaining the row prevents object-id recycling within this benchmark.
        return self.rows[key][1]


def _tensor_chunks(columns, train, test, row_fingerprints=None):
    if row_fingerprints is not None and row_fingerprints.columns != tuple(columns):
        raise ValueError('history_fingerprint_columns')
    for role, rows in (('train', train), ('test', test)):
        yield canonical(role)
        for sample in rows:
            yield (row_fingerprints.chunk(sample) if row_fingerprints is not None
                   else _tensor_row(columns,sample))


def _key_seed(reference, benchmark, columns, implementation_id):
    h = hashlib.sha256()
    h.update(canonical([PROTOCOL, implementation_id,
                        {k: reference.as_dict()[k] for k in FAMILY_FIELDS},
                        columns, benchmark.get('water_state_contract_id')]))
    return h


def unit_keys(references, benchmark, train, test, *, implementation_ids,
              training_implementation_id=None, training_keys=None, row_fingerprints=None):
    """Seal one matrix for all its estimators/revisions in a single pass.

    Exact legacy SHA-256 keys, but no repeated JSON conversion and no retained
    serialized matrix. At most one row and a bounded set of hash states live.
    """
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    if not references or len(references) * len(implementation_ids) > MAX_UNITS:
        raise ValueError('history_key_batch_limit')
    columns = trainer._columns(references[0], benchmark)
    _check_tensor(columns, train, test)
    hashes = {}
    for ref in references:
        if trainer._columns(ref, benchmark) != columns or ref.species_id != references[0].species_id:
            raise ValueError('history_key_batch_scope')
        family = tuple(ref.as_dict()[k] for k in FAMILY_FIELDS)
        hashes[family] = {revision: _key_seed(ref, benchmark, columns, revision)
                          for revision in implementation_ids}
    states = [h for group in hashes.values() for h in group.values()]
    training = ({tuple(ref.as_dict()[k] for k in FAMILY_FIELDS):
                 _key_seed(ref,benchmark,columns,training_implementation_id)
                 for ref in references} if training_implementation_id is not None else {})
    if row_fingerprints is not None:
        for h in [*states,*training.values()]: h.update(b'row_float64_le_v2')
    in_test = False
    for chunk in _tensor_chunks(columns, train, test, row_fingerprints):
        for h in states:
            h.update(chunk)
        if not in_test:
            for h in training.values(): h.update(chunk)
            # Role markers are JSON strings; sample chunks are JSON arrays.
            # A training-only key ends immediately after the test marker.
            if chunk == b'"test"': in_test = True
    if training_keys is not None:
        training_keys.update({family:h.hexdigest() for family,h in training.items()})
    return {family: {revision: h.hexdigest() for revision, h in group.items()}
            for family, group in hashes.items()}


def unit_key(reference, benchmark, train, test, *, implementation_id, tensor_cache=None,
             row_fingerprints=None):
    """Hash actual consumed values, independently of whole snapshot timestamps."""
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    columns = trainer._columns(reference, benchmark)
    _check_tensor(columns, train, test)
    h = _key_seed(reference, benchmark, columns, implementation_id)
    if row_fingerprints is not None: h.update(b'row_float64_le_v2')
    identity = (row_fingerprints,tuple(columns), tuple(id(s) for s in train), tuple(id(s) for s in test))
    if tensor_cache is not None and identity in tensor_cache:
        for chunk in tensor_cache[identity]:
            h.update(chunk)
        return h.hexdigest()
    chunks, size = [], 0
    def update(chunk):
        nonlocal size
        h.update(chunk)
        size += len(chunk)
        if size <= 8 * 1024 * 1024:
            chunks.append(chunk)
        else:
            chunks.clear()
    for chunk in _tensor_chunks(columns, train, test, row_fingerprints):
        update(chunk)
    if tensor_cache is not None:
        tensor_cache.clear()
        if size <= 8 * 1024 * 1024:
            tensor_cache[identity] = chunks
    return h.hexdigest()


class UnitCache:
    """Private worker cache. Bounded, transactional; no automatic deletion."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > MAX_CACHE_BYTES:
            raise ValueError('history_cache_limit')
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA max_page_count=65536')
        self.db.execute('CREATE TABLE IF NOT EXISTS units '
                        '(key TEXT PRIMARY KEY, payload BLOB NOT NULL, sha256 TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS unit_aliases (key TEXT PRIMARY KEY, original TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS prepared_producers (producer TEXT PRIMARY KEY)')
        self.db.execute('CREATE TABLE IF NOT EXISTS history_producers (producer TEXT PRIMARY KEY)')
        self.db.execute('CREATE TABLE IF NOT EXISTS history_origin (untracked INTEGER NOT NULL)')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def read(self, key):
        key = self.resolve_key(key)
        row = self.db.execute('SELECT payload, sha256 FROM units WHERE key=?', (key,)).fetchone()
        if row is None:
            return None
        raw, sha = row
        if len(raw) > MAX_UNIT_BYTES or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('history_cache_integrity')
        return json.loads(raw)

    def resolve_key(self, key):
        row = self.db.execute('SELECT original FROM unit_aliases WHERE key=?',(key,)).fetchone()
        return row[0] if row is not None else key

    def alias(self, key, original):
        original = self.resolve_key(original)
        if key == original:
            return
        if (self.db.execute('SELECT count(*) FROM unit_aliases').fetchone()[0] >= MAX_UNITS or
                self.db.execute('SELECT 1 FROM units WHERE key=?',(original,)).fetchone() is None):
            raise ValueError('history_alias_limit')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO unit_aliases VALUES (?,?)',(key,original))

    def prepared(self, producer):
        return self.db.execute('SELECT 1 FROM prepared_producers WHERE producer=?',(producer,)).fetchone() is not None

    def mark_prepared(self, producer):
        if self.db.execute('SELECT count(*) FROM prepared_producers').fetchone()[0] >= 256:
            raise ValueError('history_producer_limit')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO prepared_producers VALUES (?)',(producer,))

    def compatible_producers(self, producer, candidates):
        """Do not search legacy fits that never existed in a new private cache.

        Old databases without provenance remain conservative. Register before
        the first unit, so an interrupted generation keeps the same knowledge
        when resumed; successful preparation is not required.
        """
        known = {row[0] for row in self.db.execute('SELECT producer FROM history_producers')}
        origin = self.db.execute('SELECT untracked FROM history_origin').fetchone()
        if producer not in known and len(known) >= 256:
            raise ValueError('history_producer_limit')
        with self.db:
            if origin is None:
                origin = (int(self.db.execute('SELECT 1 FROM units LIMIT 1').fetchone() is not None),)
                self.db.execute('INSERT INTO history_origin VALUES (?)', origin)
            self.db.execute('INSERT OR IGNORE INTO history_producers VALUES (?)', (producer,))
        return tuple(candidates) if origin[0] else tuple(c for c in candidates if c in known)

    def put(self, key, value):
        raw = canonical(value)
        count, used = self.db.execute('SELECT count(*), coalesce(sum(length(payload)),0) FROM units').fetchone()
        if (len(raw) > MAX_UNIT_BYTES or count >= MAX_UNITS or
                used + len(raw) > MAX_CACHE_BYTES - 1024 * 1024):
            raise ValueError('history_cache_limit')
        with self.db:
            self.db.execute('INSERT INTO units VALUES (?,?,?)',
                            (key, raw, hashlib.sha256(raw).hexdigest()))

    def has_test_scope(self, samples):
        """Avoid a legacy weekly migration for completely new evaluation sets.

        This only rules out impossible hits; accepting an old unit still needs
        its exact current training/test tensor AND legacy numerical week key.
        """
        if not hasattr(self, '_test_scopes'):
            self._test_scopes = set()
            for raw, sha in self.db.execute('SELECT payload,sha256 FROM units'):
                if len(raw) > MAX_UNIT_BYTES or hashlib.sha256(raw).hexdigest() != sha:
                    raise ValueError('history_cache_integrity')
                value = json.loads(raw)
                identities = {(r[0], r[1], r[3]) for r in value.get('rows', ())}
                identities.update((r[0], r[1], r[2]) for r in value.get('missing', ()))
                self._test_scopes.add(digest(sorted(identities)))
        return digest(sorted({(m['species_id'], m['observation_id'], m['horizon_days'])
                              for m in (s['metadata'] for s in samples)})) in self._test_scopes


def evaluate_benchmark(benchmark, references, *, cutoff, implementation_id, cache,
                       targets, progress=lambda event: None, evaluate=None, unit_context=None,
                       compatible_implementation_ids=(), compatible_unit_context=None, fit_cache=None,
                       fit_scheduler=None, fingerprint_rows=False, defer_results=False,
                       compatible_row_implementation_ids=()):
    """Stream cached annual units; fitting happens only on a cache miss.

    Callbacks are also cancellation checkpoints. Outputs include unsupported
    cases, so missing early observations never disappear without explanation.
    """
    from rainmapper_core import mushroom_ml_holdout as holdout
    from rainmapper_core import mushroom_ml_model_catalog as catalog
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    if evaluate is None:
        evaluate = fit_temporal_unit
    if compatible_unit_context is not None and unit_context is None:
        raise ValueError('history_legacy_context_requires_current_context')
    if compatible_row_implementation_ids and not fingerprint_rows:
        raise ValueError('history_row_compatibility_requires_row_fingerprints')
    known = getattr(cache, 'compatible_producers', lambda producer, candidates: tuple(candidates))(
        implementation_id, tuple(dict.fromkeys((*compatible_implementation_ids, *compatible_row_implementation_ids))))
    compatible_implementation_ids = tuple(c for c in compatible_implementation_ids if c in known)
    compatible_row_implementation_ids = tuple(c for c in compatible_row_implementation_ids if c in known)
    cutoff = date.fromisoformat(cutoff)
    samples = [s for s in holdout.eligible_samples(benchmark)
               if sample_identity(s)[2] < cutoff]
    eligible_ids = {sample_identity(s) for s in samples}
    ineligible = [s for s in benchmark.get('samples', [])
                  if sample_identity(s)[0] in targets and sample_identity(s)[2] < cutoff
                  and sample_identity(s) not in eligible_ids]
    years = sorted({sample_identity(s)[2].year for s in samples + ineligible
                    if sample_identity(s)[0] in targets})
    if len(years) * len(references) > MAX_UNITS:
        raise ValueError('history_unit_limit')
    total = len(years) * len(references)
    completed = 0
    pending = deque()
    def finish(task):
        nonlocal completed
        raw_ref, ref, train_rows, test_rows, key, value, reused, started, year, purged_cases, exclusions = task
        if value is None:
            try:
                value = evaluate(ref, benchmark, train_rows, test_rows, key)
            except (ValueError, FloatingPointError) as exc:
                reasons = ('No eligible rows', 'requires both classes', 'requires at least seven',
                           'calibration requires', 'sparse-group estimator did not converge',
                           'sparse-group logistic did not converge within 2000 iterations')
                if not any(reason in str(exc) for reason in reasons):
                    raise
                value = {'rows': [], 'fit_config': None, 'missing': [
                    [s['metadata']['species_id'], s['metadata']['observation_id'],
                     s['metadata']['horizon_days'], str(exc)[:300]] for s in test_rows]}
            # Only the calling thread publishes completed fits and validation.
            progress({'phase': 'Saving historical validation', 'completed': completed,
                      'total': total, 'year': year})
            cache.put(key, value)
        completed += 1
        return {'unit_key': key, 'year': year, 'family': {k: raw_ref[k] for k in FAMILY_FIELDS},
                'reused': reused, 'seconds': time.monotonic() - started,
                'purged_cases': purged_cases,
                **value, 'missing': [*value.get('missing', []), *exclusions]}
    grouped_references = defaultdict(list)
    planned_refs = []
    for raw_ref in references:
        ref = catalog.ModelArtifactRef.from_mapping(raw_ref)
        scope = ref.species_id, tuple(trainer._columns(ref, benchmark))
        grouped_references[scope].append(ref)
        planned_refs.append((raw_ref,ref,scope))
    partitions = PartitionPlan(samples)
    row_fingerprints = {scope[1]:RowFingerprints(scope[1]) for scope in grouped_references} if fingerprint_rows else {}
    for year in (reversed(years) if defer_results else years):
        train, test, purged = partitions.for_year(year)
        sealed, legacy_sealed, scoped_rows = {}, {}, {}
        purged_cases = len({s['metadata']['observation_id'] for s in purged
                            if s['metadata']['species_id'] in targets})
        for raw_ref, ref, scope in planned_refs:
            if scope not in scoped_rows:
                train_rows = [s for s in train if ref.species_id == 'all_species' or
                              s['metadata']['species_id'] == ref.species_id]
                test_rows = [s for s in test if s['metadata']['species_id'] in targets and
                             (ref.species_id == 'all_species' or s['metadata']['species_id'] == ref.species_id)]
                exclusions = [[s['metadata']['species_id'], s['metadata']['observation_id'],
                               s['metadata']['horizon_days'], reason]
                              for source, reason in ((purged, 'temporal_episode_boundary'),
                                                     (ineligible, 'not_eligible_for_profile'))
                              for s in source if sample_identity(s)[2].year == year and
                              s['metadata']['species_id'] in targets and
                              (ref.species_id == 'all_species' or s['metadata']['species_id'] == ref.species_id)]
                trained_species = {s['metadata']['species_id'] for s in train_rows}
                supported = [s for s in test_rows if s['metadata']['species_id'] in trained_species]
                supported_fit = bool(supported and len({s['prediction_target'] for s in train_rows}) == 2)
                # A new test population cannot match any legacy key. Check once
                # before hashing every matrix for unused producer revisions.
                legacy_possible = bool(compatible_implementation_ids)
                if legacy_possible and compatible_unit_context is not None:
                    legacy_possible = getattr(cache, 'has_test_scope', lambda rows: True)(test_rows)
                scoped_rows[scope] = train_rows, test_rows, exclusions, supported, supported_fit, legacy_possible
            train_rows, test_rows, exclusions, supported, supported_fit, legacy_possible = scoped_rows[scope]
            progress({'phase': 'Validating historical observations', 'completed': completed,
                      'total': total, 'year': year})
            if not test_rows:
                while pending:
                    yield finish(pending.popleft())
                completed += 1
                if exclusions:
                    yield {'unit_key': None, 'year': year, 'family': {k: raw_ref[k] for k in FAMILY_FIELDS},
                           'reused': False, 'evaluated': False, 'seconds': 0, 'rows': [], 'missing': exclusions}
                continue
            started = time.monotonic()
            if scope not in sealed:
                revisions = (implementation_id, *compatible_row_implementation_ids,
                             *(compatible_implementation_ids if legacy_possible and not fingerprint_rows else ()))
                seal = fit_cache.seal_unit_keys if fit_cache is not None else unit_keys
                sealed[scope] = seal(grouped_references[scope], benchmark, train_rows, test_rows,
                    implementation_ids=revisions, row_fingerprints=row_fingerprints.get(scope[1]))
            keys = sealed[scope][tuple(raw_ref[k] for k in FAMILY_FIELDS)]
            key = keys[implementation_id]
            if unit_context is not None:
                context = unit_context(ref, supported) if supported_fit else 'no_supported_fit'
                key = digest([key, context])
            value = cache.read(key)
            if value is not None:
                key = cache.resolve_key(key)
            else:
                # New-format producers share this exact row/source fingerprint.
                # Probe them before expanding any legacy full-week fingerprint.
                for previous_id in compatible_row_implementation_ids:
                    previous_key = keys[previous_id]
                    if unit_context is not None:
                        previous_key = digest([previous_key, context])
                    value = cache.read(previous_key)
                    if value is not None:
                        cache.alias(key, previous_key)
                        key = cache.resolve_key(previous_key)
                        break
            # Only explicitly reviewed producer revisions are compatible. The
            # current train/test tensors AND current full-week fingerprint must
            # match their old key exactly; never accept a snapshot-level alias.
            can_migrate = value is None and legacy_possible
            if can_migrate:
                if fingerprint_rows:
                    if scope not in legacy_sealed:
                        legacy_sealed[scope] = unit_keys(grouped_references[scope],benchmark,train_rows,test_rows,
                                                       implementation_ids=compatible_implementation_ids)
                    keys = legacy_sealed[scope][tuple(raw_ref[k] for k in FAMILY_FIELDS)]
                prior_context = context if unit_context is not None else None
                if compatible_unit_context is not None:
                    prior_context = compatible_unit_context(ref, supported) if supported_fit else 'no_supported_fit'
                for previous_id in compatible_implementation_ids:
                    previous_key = keys[previous_id]
                    if unit_context is not None:
                        previous_key = digest([previous_key, prior_context])
                    value = cache.read(previous_key)
                    if value is not None:
                        cache.alias(key, previous_key)
                        key = previous_key
                        break
            reused = value is not None
            if value is None and fit_scheduler is not None:
                fit_scheduler.prefetch(ref, benchmark, train_rows, test_rows, key)
            pending.append((raw_ref,ref,train_rows,test_rows,key,value,reused,started,year,purged_cases,exclusions))
            if defer_results:
                task = pending.pop()
                pending_result = lambda task=task: finish(task)
                pending_result.unit_key = task[4]
                yield pending_result
            elif len(pending) >= (fit_scheduler.queue_limit if fit_scheduler is not None else 1):
                yield finish(pending.popleft())
    while pending:
        yield finish(pending.popleft())


def fit_temporal_unit(reference, benchmark, train, test, key, *, panel_builder=None, prepared_cache=None,
                      fit_cache=None, defer_panels=False, capture=None, inner_executor=None, fit_key=None):
    """Isolated validation fit; installed weights and tuning are never loaded."""
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    from rainmapper_core import mushroom_ml_runtime_inference as inference
    from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
    from rainmapper_core import mushroom_ml_tuning_catalog as tuning
    counts = Counter(s['metadata']['species_id'] for s in train)
    positive = Counter(s['metadata']['species_id'] for s in train
                       if s['prediction_target'] == 'favorable')
    missing = [[s['metadata']['species_id'], s['metadata']['observation_id'],
                s['metadata']['horizon_days'], 'no_previous_species_prevalence']
               for s in test if not counts[s['metadata']['species_id']]]
    test = [s for s in test if counts[s['metadata']['species_id']]]
    if not test:
        return {'rows': [], 'missing': missing, 'fit_config': None}
    if len({s['prediction_target'] for s in train}) < 2:
        missing.extend([[s['metadata']['species_id'], s['metadata']['observation_id'],
                         s['metadata']['horizon_days'], 'training_single_class'] for s in test])
        return {'rows': [], 'missing': missing, 'fit_config': None}
    fit_key = fit_key if fit_key is not None else (fit_cache.key(reference, benchmark, train) if fit_cache is not None else None)
    fitted = fit_cache.read(fit_key) if fit_cache is not None else None
    decision = None
    tuning_diagnostics = {}
    if fitted is not None:
        bundle = {**fitted['bundle'], 'artifact_ref': reference.as_dict(), 'snapshot_id': 'sha256:' + key}
        tuning_diagnostics = fitted['diagnostics']
    else:
        filtered = {**benchmark, 'samples': train}
        scope = (reference.version_id, reference.temporal_contract_id, reference.profile_id,
                 reference.species_id, tuple(id(s) for s in train))
        saved = prepared_cache.get(scope) if prepared_cache is not None else None
        prepared = saved[1] if saved is not None else None
        if prepared is None:
            prepared = trainer._prepare_fit_inputs(reference, filtered)
            if prepared_cache is not None:
                # One immutable annual/profile matrix, shared by its estimators.
                # Keep rows alive so object identities cannot be recycled.
                prepared_cache.clear()
                prepared_cache[scope] = (train, prepared)
        if reference.version_id in ('biology_v6_smooth_hierarchical', smooth.WINDOWED_VERSION_ID):
            from rainmapper_core.mushroom_competing_tuning import historical_v6_config
            decision = {'key': tuning.decision_key(reference.as_dict()),
                        'fit_config': historical_v6_config(reference, prepared, diagnostics=tuning_diagnostics,
                                                           compact=True, executor=inner_executor)}
        elif inner_executor is not None and reference.version_id in (
                'biology_v5_raw_weather_discovery', 'biology_v5_windowed_raw_weather'):
            from rainmapper_core import mushroom_ml_holdout as holdout
            config, selected = holdout._select_v5(reference.estimator_id, prepared['samples'],
                prepared['X'], prepared['y'], prepared['columns'], 14, executor=inner_executor)
            decision = {'key': tuning.decision_key(reference.as_dict()),
                        'fit_config': {**config, 'inner_selection_available': selected}}
        bundle = trainer.fit_artifact(reference, filtered, snapshot_id='sha256:' + key,
                                      tuning_decision=decision, prepared_inputs=prepared)
    model = bundle['model']
    if hasattr(model, 'get_params'):
        params = {k: 1 for k in model.get_params(deep=True) if k.endswith('n_jobs')}
        if params:
            model.set_params(**params)
    if fitted is None and fit_cache is not None:
        fit_cache.write(fit_key, bundle, tuning_diagnostics)
    if capture is not None:
        capture(bundle, tuning_diagnostics)
    predictions = inference.predict_bundle_many(bundle, [s['predictive_features'] for s in test],
                                                species_ids=[s['metadata']['species_id'] for s in test],
                                                probability_only=True)
    rows = []
    for sample, predicted in zip(test, predictions, strict=True):
        m = sample['metadata']; sid = m['species_id']
        rows.append([sid, m['observation_id'], m['target_date'], m['horizon_days'],
                     int(sample['prediction_target'] == 'favorable'), predicted['probability'],
                     positive[sid] / counts[sid], m['validation_group_14d']])
    if panel_builder is not None:
        deferred = defer_panels and panel_builder.defer(reference, key, fit_cache, fit_key)
        if defer_panels and not deferred:
            raise ValueError('history_fit_cache_budget: cannot defer historical models within the cache limit')
        if not deferred:
            panel_builder(bundle, reference, test, key)
    return {'rows': rows, 'missing': missing, 'fit_config': bundle['fit_config'],
            **({'tuning_diagnostics': tuning_diagnostics} if reference.version_id in
               ('biology_v6_smooth_hierarchical', smooth.WINDOWED_VERSION_ID) else {})}


class OrderedUnits:
    """Bounded temporary headers; numerical rows stay in the durable unit cache."""
    MAX_HEADER_BYTES = 2*1024*1024
    MAX_HEADERS_BYTES = 16*1024*1024

    def __init__(self, cache, groups):
        self.cache, self.used = cache, 0
        self.order = {}
        for index, refs in enumerate(groups.values()):
            for position, ref in enumerate(refs):
                self.order[tuple(ref[name] for name in FAMILY_FIELDS)] = (
                    int(ref['temporal_contract_id'].startswith('lag_event_')),index,position)
        cache.db.execute('CREATE TEMP TABLE ordered_history_units '
            '(temporal INTEGER, family INTEGER, year INTEGER, position INTEGER, payload BLOB, '
            'PRIMARY KEY(temporal,family,year,position))')

    def add(self, unit):
        import zlib
        from rainmapper_core.mushroom_ml_benchmark_io import _encode
        header = {k:v for k,v in unit.items() if k != 'rows'}
        raw = _encode(header,self.MAX_HEADER_BYTES,'history_ordered_header_limit')
        packed = zlib.compress(raw,1)
        if self.used+len(packed)>self.MAX_HEADERS_BYTES:
            raise ValueError('history_ordered_headers_limit')
        temporal, family, position = self.order[tuple(unit['family'][name] for name in FAMILY_FIELDS)]
        self.cache.db.execute('INSERT INTO ordered_history_units VALUES (?,?,?,?,?)',
            (temporal,family,unit['year'],position,packed))
        self.used += len(packed)

    def __iter__(self):
        import zlib
        for (packed,) in self.cache.db.execute('SELECT payload FROM ordered_history_units '
                'ORDER BY temporal,family,year,position'):
            decoder = zlib.decompressobj()
            raw = decoder.decompress(packed,self.MAX_HEADER_BYTES+1)
            if len(raw)>self.MAX_HEADER_BYTES or not decoder.eof or decoder.unused_data:
                raise ValueError('history_ordered_header_limit')
            header = json.loads(raw)
            value = self.cache.read(header['unit_key']) if header['unit_key'] is not None else {'rows':[]}
            if value is None:
                raise ValueError('history_ordered_unit_missing')
            yield {**value,**header}
