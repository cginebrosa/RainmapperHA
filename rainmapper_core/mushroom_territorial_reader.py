"""One bounded session for territorial reads, including frozen rebuild datasets."""
from contextlib import AbstractContextManager
import atexit
import json
from pathlib import Path
import sys
import tempfile

from .mushroom_map_execution import ResidentReader
from .mushroom_map_ecology import compile_exact_mappings, resolve_land_context
from .mushroom_geography_store import IDENTITIES_FILE, relative_path

CONFIG_FILE = 'territorial-context.json'
FORMAT = 'territorial_dataset_v1'
PATH_FLAGS = {'forest_index': '--index', 'mvc50_index': '--mvc50-index',
              'land_cover': '--land-cover', 'geology': '--geology',
              'land_cover_parts': '--land-cover-parts', 'geology_parts': '--geology-parts'}


def install_dataset_identities(root, files):
    """Seal local reader identities after the existing dataset cache verified files.

    This writes only a small local index. No GIS copy, hash or network operation.
    """
    from .mushroom_geography_store import physical_stamp, write_metadata
    root = Path(root)
    config = root / CONFIG_FILE
    if not config.is_file():
        return
    dataset_config(root)  # Validate bounded config and containment first.
    data = json.loads(config.read_text())
    rows = {r['path']: r for r in files}
    records = {}
    stamps = data.get('source_stamps', {})
    if not isinstance(stamps, dict) or len(stamps) > 32:
        raise ValueError('territorial_source_limit')
    for name, logical in stamps.items():
        relative_path(name)
        row = rows.get(name)
        if (not row or not isinstance(logical, list) or len(logical) != 2
                or any(type(v) is not int or v < 0 for v in logical)
                or logical[0] != row['size_bytes']):
            raise ValueError('territorial_source_mismatch')
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('territorial_path_escape')
        physical = physical_stamp(path)
        if physical[0] != logical[0]:
            raise ValueError('territorial_source_mismatch')
        records[name] = {'logical': logical, 'physical': physical, 'sha256': row['sha256']}
    write_metadata(root / IDENTITIES_FILE,
                   {'format': 'geography_source_identities_v1', 'files': records})


def dataset_config(root):
    root = Path(root).resolve()
    path = root / CONFIG_FILE
    if not path.is_file():
        return None
    if path.stat().st_size > 8192:
        raise ValueError('territorial_config_limit')
    data = json.loads(path.read_text())
    if data.get('format') != FORMAT or not isinstance(data.get('geography'), dict):
        raise ValueError('invalid_territorial_config')
    config = {}
    for key, value in data['geography'].items():
        if key not in PATH_FLAGS:
            raise ValueError('invalid_territorial_role')
        path = root / relative_path(value)
        if not path.resolve().is_relative_to(root):
            raise ValueError('territorial_path_escape')
        config[key] = str(path)
    if not config.get('mvc50_index'):
        raise ValueError('territorial_mvc50_required')
    config['geography_sources'] = str(root / IDENTITIES_FILE)
    config['geography_python'] = '/usr/bin/python3' if Path('/app').is_dir() else sys.executable
    return config


class TerritorialSession(AbstractContextManager):
    """Reuse readers/catalog once per request or rebuild, close at its end."""
    def __init__(self, config, gis_payload, catalogs_payload):
        from .mushroom_gis_lab import catalog_ids_by_group
        self.tmp = tempfile.TemporaryDirectory(prefix='rainmapper-territorial-')
        self.reader = None
        try:
            # Frozen vocabulary from the same job/request, never the worker's
            # other coordinator or mutable global catalog.
            raw = json.dumps(catalogs_payload or {}, ensure_ascii=False).encode()
            if len(raw) > 1024 * 1024:
                raise ValueError('territorial_catalog_limit')
            catalog = Path(self.tmp.name)/'catalog.json'
            catalog.write_bytes(raw)
            ids = catalog_ids_by_group(catalogs_payload or {})
            self.hosts = ids.get('host_taxa', set())
            self.mappings = compile_exact_mappings(gis_payload or {}, ids)
            args = ['--catalogs', str(catalog)]
            for key, flag in PATH_FLAGS.items():
                if config.get(key): args += [flag, str(config[key])]
            if config.get('geography_sources'): args += ['--sources', str(config['geography_sources'])]
            self.reader = ResidentReader(config.get('geography_python', sys.executable),
                                         'recover-mushroom-forest.py', args, timeout=30,
                                         max_request_bytes=65536)
        except BaseException:
            self.close()
            raise

    def lookup(self, lat, lon):
        result = self.reader.call({'lat': lat, 'lon': lon})
        land = dict(result.get('land_context', {}), trees={k:v for k,v in result.items() if k != 'land_context'})
        resolution, _ = resolve_land_context(land, self.mappings, self.hosts)
        return {'land_context': land, 'resolution': resolution}

    def close(self):
        if self.reader is not None:
            self.reader.close()
            atexit.unregister(self.reader.close)
            self.reader = None
        self.tmp.cleanup()

    def __exit__(self, *args):
        self.close()
