import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_geography_import as importer
from rainmapper_core import mushroom_map_geography_runtime as geo
from rainmapper_core import mushroom_map_volume as volume
from rainmapper_core import mushroom_worker_dataset_cache as datasets
from rainmapper_core.mushroom_geography_store import IDENTITIES_FILE, SourceIdentities, write_metadata
from rainmapper_core.mushroom_rebuild_snapshot import gis_file_records


class GeographyImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root/'geography'
        self.source = self.root/'import'
        self.source.mkdir()
        self.raw = b'unchanged raster contents'
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.asset = self.source/'height.tif'
        self.asset.write_bytes(self.raw)
        self.records = [{'path': 'height.tif', 'bytes': len(self.raw),
                         'mtime_ns': self.asset.stat().st_mtime_ns, 'sha256': self.sha}]
        self.manifest = {'format': volume.FORMAT, 'geography': {'terrain_index': 'height.tif'},
                         'files': self.records, 'bytes': len(self.raw), 'file_count': 1}
        write_metadata(self.source/'manifest.json', self.manifest)

    def test_imports_share_bytes_preserve_logical_identity_and_do_not_activate(self):
        result = importer.adopt_map(self.source, self.store, 'one')
        self.assertEqual(result['hashed_asset_bytes'], len(self.raw))
        self.assertFalse((self.store/'CURRENT.json').exists())
        legacy = self.root/'legacy'
        legacy.mkdir()
        other = legacy/'other-name.tif'
        other.write_bytes(self.raw)
        os.utime(other, ns=(1_700_000_000_000_000_000,)*2)
        rows = [{'role': 'gis', 'path': other.name, 'sha256': self.sha, 'size_bytes': len(self.raw)}]
        dataset = {'dataset_id': datasets.DEFAULT_DATASET_ID, 'files': rows,
                   'fingerprint': datasets._canonical_fingerprint(rows)}
        report = importer.adopt_dataset(legacy, self.store, dataset)
        self.assertEqual(report['hashed_asset_bytes'], 0)
        self.assertEqual(report['reused_object_bytes'], len(self.raw))
        view = Path(report['destination'])
        self.assertTrue(os.path.samefile(view/other.name, Path(result['destination'])/'height.tif'))
        self.assertEqual(SourceIdentities(view/IDENTITIES_FILE).stamp(view/other.name)[1], other.stat().st_mtime_ns)
        # A sealed scientific snapshot hashes only small metadata, never the GIS asset.
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            if path.suffix == '.tif':
                raise AssertionError('GIS asset opened during sealed snapshot')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded_open):
            self.assertEqual(gis_file_records(view), rows)
            importer.publish_dataset(self.store, dataset['fingerprint'])
        self.assertTrue(self.asset.exists())
        self.assertEqual(other.read_bytes(), self.raw)
        self.assertFalse(os.path.samefile(other, view/other.name))
        geo.publish(self.store, 'one')
        publication = geo.GeographyPublication(self.store, start=False)
        self.addCleanup(publication.close)
        published, length = publication.object(publication.reference()['fingerprint'], 'height.tif', 0)
        self.assertEqual(published.read_bytes(), self.raw)
        self.assertEqual(length, len(self.raw))

    def test_corrupt_import_never_publishes_manifest_or_pointer(self):
        self.asset.write_bytes(b'x'*len(self.raw))
        with self.assertRaisesRegex(ValueError, 'checksum_mismatch'):
            importer.adopt_map(self.source, self.store, 'one')
        self.assertFalse((self.store/'CURRENT.json').exists())
        self.assertFalse((self.store/'generations/one/manifest.json').exists())
        self.assertTrue(self.asset.exists())

    def test_reimport_is_metadata_only_and_conflicting_generation_is_rejected(self):
        importer.adopt_map(self.source, self.store, 'one')
        second = importer.adopt_map(self.source, self.store, 'one')
        self.assertEqual(second['hashed_asset_bytes'], 0)
        self.assertEqual(second['reused_object_bytes'], len(self.raw))
        self.manifest['files'][0]['sha256'] = 'f'*64
        write_metadata(self.source/'manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'generation_already_exists'):
            importer.adopt_map(self.source, self.store, 'one')

    def test_changed_sealed_asset_fails_before_snapshot(self):
        rows = [{'role': 'gis', 'path': self.asset.name, 'size_bytes': len(self.raw), 'sha256': self.sha}]
        dataset = {'dataset_id': datasets.DEFAULT_DATASET_ID, 'files': rows,
                   'fingerprint': datasets._canonical_fingerprint(rows)}
        result = importer.adopt_dataset(self.source, self.store, dataset)
        view = Path(result['destination'])
        replacement = view/'replacement'
        replacement.write_bytes(b'x'*len(self.raw))
        os.replace(replacement, view/self.asset.name)
        with self.assertRaises(ValueError):
            gis_file_records(view)

    def test_auxiliary_soilgrids_survives_without_expanding_job_payload(self):
        soil = self.source/'soilgrids/normalized/tile.tif'
        soil.parent.mkdir(parents=True)
        soil.write_bytes(self.raw)
        rows = [{'role': 'gis', 'path': self.asset.name, 'size_bytes': len(self.raw), 'sha256': self.sha}]
        dataset = {'dataset_id': datasets.DEFAULT_DATASET_ID, 'files': rows,
                   'fingerprint': datasets._canonical_fingerprint(rows)}
        auxiliary = {'format': volume.FORMAT, 'geography': {}, 'file_count': 1,
                     'bytes': len(self.raw), 'files': [{'path': 'soilgrids/normalized/tile.tif',
                     'bytes': len(self.raw), 'sha256': self.sha, 'mtime_ns': soil.stat().st_mtime_ns}]}
        result = importer.adopt_dataset(self.source, self.store, dataset, auxiliary_manifest=auxiliary)
        view = Path(result['destination'])
        self.assertTrue(os.path.samefile(view/self.asset.name, view/'soilgrids/normalized/tile.tif'))
        self.assertEqual(gis_file_records(view), rows)

        # Acquisition updates by atomic replacement preserve the sealed source.
        temporary = view/'soilgrids/normalized/new-tile'
        temporary.write_bytes(b'new soil tile')
        os.replace(temporary, view/'soilgrids/normalized/tile.tif')
        self.assertEqual((view/self.asset.name).read_bytes(), self.raw)
        self.assertEqual(gis_file_records(view), rows)

    def test_delta_import_needs_no_second_copy_of_existing_objects(self):
        importer.adopt_map(self.source, self.store, 'one')
        delta = self.root/'delta'
        delta.mkdir()
        rows = [{'role': 'gis', 'path': self.asset.name, 'size_bytes': len(self.raw), 'sha256': self.sha}]
        dataset = {'dataset_id': datasets.DEFAULT_DATASET_ID, 'files': rows,
                   'fingerprint': datasets._canonical_fingerprint(rows)}
        result = importer.adopt_dataset(delta, self.store, dataset, auxiliary_manifest=self.manifest)
        self.assertEqual(result['hashed_asset_bytes'], 0)
        self.assertEqual(result['copied_asset_bytes'], 0)
        self.assertEqual(gis_file_records(Path(result['destination'])), rows)
