import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_geography_portable as portable
from rainmapper_core import mushroom_map_geography_runtime as geo
from rainmapper_core import mushroom_worker_dataset_cache as datasets
from rainmapper_core.mushroom_geography_store import SourceIdentities, IDENTITIES_FILE, write_metadata


class PortableGeographyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()/'prepared'
        self.root.mkdir()
        self.raw = b'one shared raster'
        self.row = {'path': 'rasters/height.tif', 'bytes': len(self.raw),
                    'sha256': hashlib.sha256(self.raw).hexdigest(), 'mtime_ns': 1700000000123456789}
        self.aux = {'format': 'prediction_map_volume_v1', 'geography': {},
                    'files': [self.row], 'bytes': len(self.raw), 'file_count': 1}
        self.manifest = {**self.aux, 'geography': {'terrain_index': 'map/height.tif', 'regional_root': 'map'},
                         'files': [{**self.row, 'path': 'map/height.tif'}]}
        rows = [{'role': 'gis', 'path': self.row['path'], 'size_bytes': self.row['bytes'], 'sha256': self.row['sha256']}]
        self.dataset = {'dataset_id': datasets.DEFAULT_DATASET_ID, 'fingerprint': datasets._canonical_fingerprint(rows), 'files': rows}
        self.file = self.root/'mushroom-GIS'/self.row['path']
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(self.raw)
        os.utime(self.file, ns=(1800000000999999000,)*2)
        self.report = portable.prepare(self.root, self.manifest, self.aux, self.dataset, 'one', {})

    def publication(self, root=None):
        pub = geo.GeographyPublication(root or self.root, start=False)
        self.addCleanup(pub.close)
        return pub

    def test_copy_to_different_disk_identity_is_read_only_from_first_open(self):
        copied = self.root.parent/'other-mount'
        shutil.copytree(self.root, copied, copy_function=shutil.copy2)
        physical = copied/'mushroom-GIS'/self.row['path']
        self.assertNotEqual(physical.stat().st_ino, self.file.stat().st_ino)
        self.assertEqual(physical.stat().st_nlink, 1)
        before = {p.relative_to(copied): p.stat().st_mtime_ns for p in copied.rglob('*')}
        with patch.object(Path, 'mkdir', side_effect=AssertionError('startup mkdir')), patch.object(os, 'link', side_effect=AssertionError('startup link')):
            pub = self.publication(copied)
            ref = pub.reference()
            actual, size = pub.object(ref['fingerprint'], 'map/height.tif')
            self.assertEqual(actual, physical)
            self.assertEqual(actual.read_bytes(), self.raw)
            self.assertEqual(size, len(self.raw))
            snapshot = pub.lookup(ref['fingerprint'])
            config = geo.config_for_geography({}, snapshot['root'], snapshot['manifest'], snapshot['identities'])
            self.assertEqual(config['terrain_index'], str(physical))
            self.assertEqual(SourceIdentities(config['geography_sources']).stamp(copied/'map/height.tif'), [self.row['bytes'], self.row['mtime_ns']])
        self.assertEqual(before, {p.relative_to(copied): p.stat().st_mtime_ns for p in copied.rglob('*')})
        self.assertFalse((copied/'map').exists())
        self.assertFalse((copied/'receipts.sqlite').exists())

    def test_map_then_scientific_cache_share_content_and_warm_transport_is_empty(self):
        pub = self.publication()
        calls = []
        def post(action, reference, **kwargs):
            calls.append(action)
            if action == 'geography_manifest': return io.BytesIO(geo.encode(self.manifest))
            actual, count = pub.object(reference['fingerprint'], kwargs['file'], kwargs['offset'])
            return io.BytesIO(actual.read_bytes()[kwargs['offset']:kwargs['offset']+count])
        worker = self.root.parent/'worker'
        cache = geo.GeographyCache(worker, 'coordinator_1234567890abcdef', post)
        self.addCleanup(cache.close)
        cache.prepare(pub.reference())
        self.assertEqual(cache.last_sync['transferred_bytes'], len(self.raw))
        report = datasets.sync_from_fetcher({'datasets': [self.dataset]}, worker,
            fetch_file=lambda *args: self.fail('shared raster downloaded twice'))
        self.assertEqual(report['transferred_size_bytes'], 0)
        calls.clear()
        restarted = geo.GeographyCache(worker, 'coordinator_1234567890abcdef', post)
        self.addCleanup(restarted.close)
        restarted.prepare(pub.reference())
        self.assertEqual(calls, [])
        self.assertEqual(restarted.last_sync['hashed_bytes'], 0)

    def test_missing_mutated_or_escaping_file_fails_closed(self):
        pub = self.publication()
        ref = pub.reference()['fingerprint']
        os.utime(self.file, ns=(1900000000000000000,)*2)
        with self.assertRaisesRegex(ValueError, 'source_changed'): pub.object(ref, 'map/height.tif')
        self.file.unlink()
        with self.assertRaises(FileNotFoundError): pub.object(ref, 'map/height.tif')
        outside = self.root.parent/'outside'
        outside.write_bytes(self.raw)
        self.file.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'outside_view'): pub.object(ref, 'map/height.tif')

    def test_manifest_mismatch_is_not_published_and_gis_contract_unchanged(self):
        from rainmapper_core.mushroom_rebuild_snapshot import gis_file_records
        with patch.object(hashlib, 'file_digest', side_effect=AssertionError('HA raster hash')):
            self.assertEqual(gis_file_records(self.root/'mushroom-GIS'), self.dataset['files'])
        path = self.root/self.report['sources_file']
        data = json.loads(path.read_text())
        data['files']['map/height.tif']['sha256'] = '0'*64
        write_metadata(path, data)
        pub = self.publication()
        with self.assertRaisesRegex(ValueError, 'manifest_mismatch'): pub.refresh()

    def test_catalog_paths_cannot_escape_preparation_root(self):
        bad = {**self.aux, 'files': [{**self.row, 'path': '../outside'}]}
        with self.assertRaises(ValueError): portable.layout(self.manifest, bad)


if __name__ == '__main__': unittest.main()
