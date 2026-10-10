"""JSON compatibility and columnar storage for disposable feature matrices.

Metadata stays small and self describing in the Parquet footer. Numerical
features occupy typed columns, allowing readers to request only a profile's
inputs. Original source observations and installed model artifacts are untouched.
"""
from __future__ import annotations

import json
import base64
from collections.abc import Mapping
from itertools import islice
from pathlib import Path

MAX_ROWS = 50000
MAX_COLUMNS = 4096
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
METADATA_KEY = b'rainmapper_benchmark_v1'
CATALOG_KEY = b'rainmapper_soil_catalog_rows_v1'
MAX_CATALOG_ROWS = 50000
MAX_RECORD_BYTES = 8 * 1024 * 1024
WRITE_BATCH_CELLS = 262144
FIT_METADATA_FIELDS = frozenset((
    'observation_id', 'species_id', 'target_date', 'cutoff_date', 'horizon_days',
    'micro_area_id', 'area_id', 'validation_group_7d', 'validation_group_14d',
    'temporal_contract_id', 'training_eligible'))


def fit_sample(sample):
    """Project a final raw-weather row to its temporal-fit contract.

    Applied only after feature derivation. Intermediate V3/V4 and scientific
    exports must retain diagnostics consumed by their subsequent projections.
    """
    return {**sample,
            'metadata': {k:v for k,v in (sample.get('metadata') or {}).items() if k in FIT_METADATA_FIELDS},
            'quality': {k:v for k,v in (sample.get('quality') or {}).items()
                        if k in ('training_eligible', 'training_exclusion_reasons')}}


def historical_source_sample(sample):
    """Minimal V3/V4 source for historical fit-profile adapters only.

    Predictors are unchanged. V2 needs scalar rain quality; V3+ needs the
    original V3 gates and the soil reference; V4 needs block eligibility.
    Scientific exports and feature construction use the full source instead.
    """
    def metadata(value):
        result = {k:v for k,v in value.items() if k in FIT_METADATA_FIELDS or k == 'soil_state_key'}
        if isinstance(value.get('source_v3_metadata'), dict):
            result['source_v3_metadata'] = metadata(value['source_v3_metadata'])
        return result
    def quality(value):
        result = {k:v for k,v in value.items()
                  if v is None or type(v) in (str,int,float,bool) or k == 'training_exclusion_reasons'}
        if 'eligibility_by_block' in value:
            result['eligibility_by_block'] = value['eligibility_by_block']
        if isinstance(value.get('source_v3_quality'), dict):
            result['source_v3_quality'] = quality(value['source_v3_quality'])
        return result
    return {**sample, 'metadata':metadata(sample.get('metadata') or {}),
            'quality':quality(sample.get('quality') or {})}


class ColumnarFeatures(Mapping):
    """Immutable row view; batches share typed numbers and column identities.

    Opt-in for the private historical reader. Nulls and absent keys remain
    distinct, and values exposed to model consumers are ordinary Python floats.
    No per-cell Python float/dictionary survives materialization.
    """
    __slots__ = ('_positions', '_values', '_valid', '_row', '_absent', '_projections')

    def __init__(self, positions, values, valid, row, absent, projections):
        self._positions, self._values, self._valid = positions, values, valid
        self._row, self._absent = row, absent
        self._projections = projections

    def __len__(self):
        return len(self._positions) - len(self._absent)

    def __iter__(self):
        return (key for key, index in self._positions.items() if index not in self._absent)

    def __getitem__(self, key):
        column = self._positions[key]
        if column in self._absent:
            raise KeyError(key)
        return float(self._values[self._row, column]) if self._valid[self._row, column] else None

    def __deepcopy__(self, memo):
        return self

    def values_for(self, columns, *, numeric=False):
        """Read a model's ordered predictors in one bounded vector operation."""
        import numpy as np
        indices, _ = self._projection(columns)
        if not self._positions:
            return np.full(len(columns), np.nan) if numeric else [None] * len(columns)
        values = self._values[self._row, indices]
        valid = self._valid[self._row, indices] & (indices >= 0)
        if self._absent:
            valid &= np.asarray([i not in self._absent for i in indices])
        if numeric:
            values[~valid] = np.nan
            return values
        result = values.tolist()
        if not valid.all():
            for index in np.flatnonzero(~valid):
                result[index] = None
        return result

    def contains_all(self, columns):
        indices, complete = self._projection(columns)
        return complete and (not self._absent or not any(i in self._absent for i in indices))

    def _projection(self, columns):
        import numpy as np
        key = tuple(columns)
        projection = self._projections.get(key)
        if projection is None:
            indices = np.asarray([self._positions.get(c, -1) for c in key], dtype=np.intp)
            indices.flags.writeable = False
            projection = indices, bool((indices >= 0).all())
            if len(self._projections) >= 32:
                self._projections.clear()
            self._projections[key] = projection
        return projection


def training_sample(sample):
    """Keep fit inputs/gates/identity; omit already-consumed weather diagnostics.

    Only for private historical matrices after all predictive features have
    been constructed. Scientific exports retain their complete audit metadata.
    """
    def project(metadata):
        result = {k:v for k,v in metadata.items() if k not in {
            'weather_series', 'weather_idw', 'raw_daily_dates', 'diagnostic_weather_summary',
            'climatic_balance_metadata', 'soil_water_metadata'}}
        if isinstance(result.get('source_v3_metadata'), dict):
            result['source_v3_metadata'] = project(result['source_v3_metadata'])
        return result
    return {**sample, 'metadata': project(sample.get('metadata') or {})}


def historical_intermediate_sample(sample):
    """V3 inputs still needed by V4/V5; omit unused per-day audit metadata."""
    return {**sample, 'metadata': {key: value for key, value in sample['metadata'].items()
            if key in FIT_METADATA_FIELDS or key in ('weather_series', 'area_representative_location')}}


def _encode(value, limit, error):
    """Bound serialization without first allocating the complete JSON string."""
    if _json_bound(value, limit) >= 0:
        # The structural upper bound has already proved this fits. Use the C
        # encoder instead of yielding thousands of Python fragments per row.
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > limit:
            raise ValueError(error)
        return raw
    raw = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode()
        if len(raw) + len(encoded) > limit:
            raise ValueError(error)
        raw.extend(encoded)
    return bytes(raw)


def _json_bound(value, remaining):
    """Remaining budget after a conservative UTF-8 JSON bound; -1 is unknown.

    Walk existing containers without constructing a second tree. Strings use
    six bytes per codepoint (the largest escape); numbers use a safe bound.
    A pessimistic bound falls back to the incremental encoder above.
    """
    kind = type(value)
    if value is None or kind is bool:
        return remaining - 5
    if kind is float:
        return remaining - 25
    if kind is int:
        return remaining - (value.bit_length() * 30103 // 100000 + 3)
    if kind is str:
        return remaining - (len(value) * 6 + 2)
    if kind is dict:
        remaining -= len(value) * 2 + 2
        for key, item in value.items():
            if type(key) is not str:
                return -1
            remaining -= len(key) * 6 + 2
            if remaining < 0:
                return -1
            remaining = _json_bound(item, remaining)
            if remaining < 0:
                return -1
        return remaining
    if kind in (list, tuple):
        remaining -= len(value) + 2
        for item in value:
            if remaining < 0:
                return -1
            remaining = _json_bound(item, remaining)
        return remaining
    return -1


def _header_and_catalogs(benchmark):
    header = {k:v for k,v in benchmark.items() if k != 'samples'}
    catalogs = {}
    if isinstance(header.get('soil_variants'), dict):
        header['soil_variants'] = dict(header['soil_variants'])
        for name, variant in header['soil_variants'].items():
            if isinstance(variant, dict) and 'area_state_catalog' in variant:
                catalogs[name] = variant['area_state_catalog']
                header['soil_variants'][name] = {**variant, 'area_state_catalog': {}}
    if sum(len(c) for c in catalogs.values()) > MAX_CATALOG_ROWS:
        raise ValueError('benchmark_catalog_row_limit')
    return header, catalogs


def write(path, benchmark):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix != '.parquet':
        path.write_text(json.dumps(benchmark, ensure_ascii=False) + '\n', encoding='utf-8')
        return
    rows = benchmark['samples']
    if len(rows) > MAX_ROWS:
        raise ValueError('benchmark_row_limit')
    columns = sorted({key for row in rows for key in row['predictive_features']})
    write_rows(path, benchmark, iter(rows), columns=columns, count=len(rows))


WEATHER_COLUMN = 'weather_series'
WEATHER_LISTS = ('daily_dates', 'daily_area_rain_idw_mean_mm', 'daily_temp_max_corrected_c',
                 'daily_temp_min_corrected_c', 'daily_temp_mean_corrected_c', 'daily_humidity_max_pct',
                 'daily_humidity_min_pct', 'daily_humidity_mean_pct', 'daily_eto0_mean_mm')


def _weather_type():
    import pyarrow as pa
    return pa.struct([pa.field(name, pa.list_(pa.string() if name == 'daily_dates' else pa.float64()))
                      for name in WEATHER_LISTS] + [pa.field('water_state_contract_id', pa.string())])


def _weather_size(value):
    """Bound the typed intermediate row before allocating Arrow buffers."""
    if not isinstance(value, dict) or set(value) - set(WEATHER_LISTS) - {'water_state_contract_id'}:
        raise ValueError('benchmark_weather_fields')
    size = 128 + 16*len(value)
    for key, item in value.items():
        if key in WEATHER_LISTS:
            if not isinstance(item, (list, tuple)) or len(item) > 365:
                raise ValueError('benchmark_weather_size')
            size += len(item)*10
            if key == 'daily_dates':
                if any(type(v) is not str or len(v) > 128 for v in item):
                    raise ValueError('benchmark_weather_date')
                size += sum(map(len, item))*4
        elif type(item) is not str or len(item) > 160:
            raise ValueError('benchmark_weather_contract')
        else:
            size += len(item)*4
    return size


def _restore_weather(row, value):
    if value is not None:
        row['metadata'] = {**row.get('metadata', {}),
                           'weather_series': {k: v for k, v in value.items() if v is not None}}


def _weather_batch(batch):
    if WEATHER_COLUMN not in batch.schema.names:
        return {}
    array = batch.column(WEATHER_COLUMN)
    if array.type != _weather_type():
        raise ValueError('benchmark_weather_schema')
    for name in WEATHER_LISTS:
        values = array.field(name)
        count = values.offsets[-1].as_py() - values.offsets[0].as_py()
        if count > len(array)*365:
            raise ValueError('benchmark_weather_size')
    return {WEATHER_COLUMN: array.to_pylist()}


def write_rows(path, benchmark, rows, *, columns, count, refresh_header=False,
               weather_column=False):
    """Stream numerical rows directly to Parquet, with a predeclared schema."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = Path(path)
    split_weather = weather_column
    if split_weather and benchmark.get('kind') != 'mushroom_ml_biology_v3_benchmark':
        raise ValueError('benchmark_weather_kind')
    if path.suffix != '.parquet':
        raise ValueError('streaming_benchmark_requires_parquet')
    if type(count) is not int or not 0 <= count <= MAX_ROWS:
        raise ValueError('benchmark_row_limit')
    columns = sorted(columns)
    if len(columns) > MAX_COLUMNS:
        raise ValueError('benchmark_column_limit')
    if len(columns) != len(set(columns)):
        raise ValueError('benchmark_duplicate_column')
    if count * len(columns) * 10 > MAX_FILE_BYTES:
        raise ValueError('benchmark_uncompressed_limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    header, catalogs = _header_and_catalogs(benchmark)
    footer = {METADATA_KEY: _encode(header, MAX_METADATA_BYTES, 'benchmark_metadata_limit')}
    catalog_fields = []
    if catalogs:
        # Each area/cutoff/soil variant is stored once, as a data row. The footer
        # only describes it; neither samples nor the footer duplicate its data.
        footer[CATALOG_KEY] = _encode({'samples': count,
            'variants': {name:len(c) for name,c in catalogs.items()}},
            MAX_METADATA_BYTES, 'benchmark_metadata_limit')
        catalog_fields = [pa.field('catalog_variant', pa.string()), pa.field('catalog_key', pa.string())]
    schema = pa.schema([pa.field('record', pa.binary()), pa.field('absent', pa.list_(pa.int16()))] +
                       [pa.field('x:' + name, pa.float64()) for name in columns] + catalog_fields +
                       ([pa.field(WEATHER_COLUMN,_weather_type())] if split_weather else []),
                       metadata=footer)
    temporary = path.with_suffix('.parquet.tmp')
    uncompressed_bytes = sum(map(len, footer.values()))
    with pq.ParquetWriter(temporary, schema, compression='zstd') as writer:
        # No all-matrix Arrow copy and no all-matrix JSON string.
        iterator = iter(rows)
        completed = 0
        column_set = set(columns)
        # Tiny row groups repeat a column-chunk footer for every predictor.
        # Bound cells while letting narrow/projected matrices share fewer
        # groups. Reader batches stay independently bounded at 128 rows.
        batch_size = min(128 if split_weather else 1024, max(1, WRITE_BATCH_CELLS // max(1, len(columns))))
        while batch := list(islice(iterator, batch_size)):
            completed += len(batch)
            if completed > count:
                raise ValueError('benchmark_row_count_mismatch')
            if any(not set(row['predictive_features']).issubset(column_set) for row in batch):
                raise ValueError('benchmark_undeclared_column')
            uncompressed_bytes += len(batch) * len(columns) * 10
            if uncompressed_bytes > MAX_FILE_BYTES:
                raise ValueError('benchmark_uncompressed_limit')
            records = []
            weather_rows = []
            for row in batch:
                record = {k: v for k, v in row.items() if k != 'predictive_features'}
                if split_weather:
                    metadata = dict(record.get('metadata') or {})
                    weather = metadata.pop('weather_series', None)
                    weather_bytes = _weather_size(weather) if weather is not None else 0
                    uncompressed_bytes += weather_bytes
                    record['metadata'] = metadata
                    weather_rows.append(weather)
                raw = _encode(record,
                              MAX_RECORD_BYTES, 'benchmark_record_limit')
                if split_weather and len(raw) + weather_bytes > MAX_RECORD_BYTES:
                    raise ValueError('benchmark_record_limit')
                uncompressed_bytes += len(raw)
                if uncompressed_bytes > MAX_FILE_BYTES:
                    raise ValueError('benchmark_uncompressed_limit')
                records.append(raw)
            absent = [[i for i,c in enumerate(columns) if c not in row['predictive_features']] for row in batch]
            arrays = [pa.array(records, pa.binary()), pa.array(absent, pa.list_(pa.int16()))]
            arrays += [pa.array([row['predictive_features'].get(c) for row in batch], pa.float64()) for c in columns]
            arrays += [pa.nulls(len(batch), type=field.type) for field in catalog_fields]
            if split_weather:
                import pyarrow.compute as pc
                weather_array = pa.array(weather_rows, type=_weather_type())
                for name in WEATHER_LISTS[1:]:
                    if pc.any(pc.invert(pc.is_finite(weather_array.field(name).values))).as_py():
                        raise ValueError('benchmark_weather_nonfinite')
                arrays.append(weather_array)
            writer.write_batch(pa.RecordBatch.from_arrays(arrays, schema=schema))
            if temporary.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('benchmark_file_limit')
        if refresh_header:
            # Some producers compute eligibility counts while yielding rows.
            # Publish their final small header, never a partly consumed one.
            updated, updated_catalogs = _header_and_catalogs(benchmark)
            if updated_catalogs != catalogs:
                raise ValueError('benchmark_catalog_changed_during_write')
            raw_header = _encode(updated, MAX_METADATA_BYTES, 'benchmark_metadata_limit')
            uncompressed_bytes += max(0, len(raw_header) - len(footer[METADATA_KEY]))
            if uncompressed_bytes > MAX_FILE_BYTES:
                raise ValueError('benchmark_uncompressed_limit')
            footer[METADATA_KEY] = raw_header
            # Arrow restores schema metadata from its embedded schema, which
            # must agree with the Parquet footer's final eligibility counters.
            writer.add_key_value_metadata({**footer, b'ARROW:schema':
                base64.b64encode(schema.with_metadata(footer).serialize().to_pybytes())})
        if completed != count:
            raise ValueError('benchmark_row_count_mismatch')
        states = ((name, key, state) for name, catalog in catalogs.items() for key, state in catalog.items())
        while batch := list(islice(states, 16)):
            records = []
            for _, _, state in batch:
                raw = _encode(state, MAX_RECORD_BYTES, 'benchmark_record_limit')
                uncompressed_bytes += len(raw)
                if uncompressed_bytes > MAX_FILE_BYTES:
                    raise ValueError('benchmark_uncompressed_limit')
                records.append(raw)
            arrays = [pa.array(records, pa.binary()), pa.array([[]] * len(batch), pa.list_(pa.int16()))]
            arrays += [pa.nulls(len(batch), type=pa.float64()) for _ in columns]
            arrays += [pa.array([item[i] for item in batch], pa.string()) for i in (0, 1)]
            if split_weather:
                arrays.append(pa.nulls(len(batch), type=_weather_type()))
            writer.write_batch(pa.RecordBatch.from_arrays(arrays, schema=schema))
            if temporary.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('benchmark_file_limit')
    if temporary.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('benchmark_file_limit')
    temporary.replace(path)


def metadata(path):
    """Read the small header; soil catalogs are restored only by read()."""
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('benchmark_file_limit')
    if path.suffix != '.parquet':
        value = json.loads(path.read_text(encoding='utf-8'))
        return {k:v for k,v in value.items() if k != 'samples'}
    import pyarrow.parquet as pq
    source = pq.ParquetFile(path)
    counts = _catalog_counts(source)
    if source.metadata.num_rows > MAX_ROWS + sum(counts.get('variants', {}).values()) or len(source.schema_arrow) > MAX_COLUMNS + (4 if counts else 2) + int(WEATHER_COLUMN in source.schema_arrow.names):
        raise ValueError('benchmark_cardinality_limit')
    raw = (source.schema_arrow.metadata or {}).get(METADATA_KEY)
    if raw is None or len(raw) > MAX_METADATA_BYTES:
        raise ValueError('benchmark_metadata_limit')
    return json.loads(raw)


def _catalog_counts(source):
    raw = (source.schema_arrow.metadata or {}).get(CATALOG_KEY)
    if raw is None:
        return {}
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError('benchmark_metadata_limit')
    counts = json.loads(raw)
    values = [counts.get('samples'), *counts.get('variants', {}).values()]
    if (not values or any(type(n) is not int or n < 0 for n in values)
            or values[0] > MAX_ROWS or sum(values[1:]) > MAX_CATALOG_ROWS
            or sum(values) != source.metadata.num_rows
            or not {'catalog_variant', 'catalog_key'}.issubset(source.schema_arrow.names)):
        raise ValueError('benchmark_catalog_cardinality')
    return counts


class SampleRows:
    """Repeatable bounded reader for consumers that do not need soil catalogs."""
    def __init__(self, path, *, feature_columns=None, include_weather=True):
        import pyarrow.parquet as pq
        self.path, self.feature_columns = Path(path), feature_columns
        self.include_weather = include_weather
        metadata(self.path)  # Validate the header and cardinality before reading.
        source = pq.ParquetFile(self.path)
        counts = _catalog_counts(source)
        self.count = counts['samples'] if counts else source.metadata.num_rows

    def __len__(self):
        return self.count

    def __iter__(self):
        import pyarrow.parquet as pq
        source = pq.ParquetFile(self.path)
        counts = _catalog_counts(source)
        names = [n[2:] for n in source.schema_arrow.names if n.startswith('x:')]
        wanted = set(names) if self.feature_columns is None else set(self.feature_columns)
        if not wanted.issubset(names):
            raise ValueError('benchmark_required_column_missing')
        selected = [(i, c) for i,c in enumerate(names) if c in wanted]
        columns = ['record', 'absent'] + ['x:' + c for _,c in selected]
        if counts:
            columns.append('catalog_variant')
        if self.include_weather and WEATHER_COLUMN in source.schema_arrow.names:
            columns.append(WEATHER_COLUMN)
        decoded_bytes = 0
        for batch in source.iter_batches(batch_size=32, columns=columns, use_threads=False):
            weather_values = _weather_batch(batch)
            values = batch.select([n for n in batch.schema.names if n!=WEATHER_COLUMN]).to_pydict()
            for i, raw in enumerate(values['record']):
                decoded_bytes += len(raw)
                if len(raw) > MAX_RECORD_BYTES or decoded_bytes > MAX_FILE_BYTES:
                    raise ValueError('benchmark_record_limit')
                if counts and values['catalog_variant'][i] is not None:
                    continue
                row = json.loads(raw)
                if weather_values:
                    _restore_weather(row, weather_values[WEATHER_COLUMN][i])
                absent = set(values['absent'][i])
                row['predictive_features'] = {c:values['x:' + c][i] for j,c in selected if j not in absent}
                yield row


def read(path, *, feature_columns=None, compact_features=False, sample_projection=None):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('benchmark_file_limit')
    if path.suffix != '.parquet':
        result = json.loads(path.read_text(encoding='utf-8'))
        if sample_projection is not None:
            result['samples'] = [sample_projection(s) for s in result['samples']]
        return result
    import pyarrow.parquet as pq
    result = metadata(path)
    source = pq.ParquetFile(path)
    counts = _catalog_counts(source)
    names = [n[2:] for n in source.schema_arrow.names if n.startswith('x:')]
    selected = set(names) if feature_columns is None else set(feature_columns)
    if not selected.issubset(names):
        raise ValueError('benchmark_required_column_missing')
    indices = {c:i for i,c in enumerate(names)}
    ordered = [c for c in names if c in selected]
    positions = {c:i for i,c in enumerate(ordered)}
    projections = {}
    result['samples'] = []
    catalog_columns = ['catalog_variant', 'catalog_key'] if counts else []
    decoded_bytes = 0
    include_weather = sample_projection not in (fit_sample, historical_source_sample)
    weather_columns = [WEATHER_COLUMN] if include_weather and WEATHER_COLUMN in source.schema_arrow.names else []
    for batch in source.iter_batches(batch_size=128, columns=weather_columns+['record','absent'] + ['x:' + c for c in ordered] + catalog_columns,
                                     use_threads=False):
        weather_values = _weather_batch(batch)
        if compact_features:
            import numpy as np
            numeric = np.empty((batch.num_rows, len(ordered)), dtype=np.float64)
            valid = np.empty(numeric.shape, dtype=np.bool_)
            for column, name in enumerate(ordered):
                array = batch.column('x:' + name)
                numeric[:, column] = array.to_numpy(zero_copy_only=False)
                valid[:, column] = array.is_valid().to_numpy(zero_copy_only=False)
            numeric.flags.writeable = valid.flags.writeable = False
            values = batch.select(['record', 'absent'] + catalog_columns).to_pydict()
        else:
            values = batch.select([n for n in batch.schema.names if n!=WEATHER_COLUMN]).to_pydict()
        for index, raw in enumerate(values['record']):
            decoded_bytes += len(raw)
            if len(raw) > MAX_RECORD_BYTES or decoded_bytes > MAX_FILE_BYTES:
                raise ValueError('benchmark_record_limit')
            row = json.loads(raw)
            if weather_values:
                _restore_weather(row, weather_values[WEATHER_COLUMN][index])
            variant = values['catalog_variant'][index] if counts else None
            if variant is not None:
                if variant not in counts['variants'] or variant not in result.get('soil_variants', {}):
                    raise ValueError('benchmark_catalog_variant')
                catalog = result['soil_variants'][variant]['area_state_catalog']
                key = values['catalog_key'][index]
                if key is None or key in catalog:
                    raise ValueError('benchmark_catalog_key')
                catalog[key] = row
                continue
            absent = set(values['absent'][index])
            if compact_features:
                selected_absent = frozenset(positions[c] for c in ordered if indices[c] in absent)
                row['predictive_features'] = ColumnarFeatures(positions, numeric, valid, index, selected_absent, projections)
            else:
                row['predictive_features'] = {c:values['x:' + c][index] for c in ordered if indices[c] not in absent}
            result['samples'].append(sample_projection(row) if sample_projection is not None else row)
    if counts and (len(result['samples']) != counts['samples'] or any(
            len(result['soil_variants'][name]['area_state_catalog']) != size
            for name, size in counts['variants'].items())):
        raise ValueError('benchmark_catalog_cardinality')
    return result
