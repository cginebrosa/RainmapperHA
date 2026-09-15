import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_map_geography_runtime as geo
from rainmapper_core import mushroom_map_volume as volume
from rainmapper_core import mushroom_worker_dataset_cache as datasets
from rainmapper_core.mushroom_geography_store import SourceIdentities, IDENTITIES_FILE


class GeographyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.media = self.root/'media'
        self.worker = self.root/'worker'
        self.calls = []

    def generation(self, name, contents=None):
        contents = contents or {'layers/index.sqlite': b'index', 'layers/source.tif': b'public raster'}
        root = self.media/'generations'/name
        rows = []
        for path, raw in contents.items():
            dst = root/path; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(raw)
            os.utime(dst, ns=(1_700_000_000_000_000_000,)*2)
            rows.append({'path': path, 'bytes': len(raw), 'mtime_ns': dst.stat().st_mtime_ns,
                         'sha256': hashlib.sha256(raw).hexdigest()})
        manifest = {'format': volume.FORMAT, 'geography': {'terrain_index': 'layers/index.sqlite'},
                    'files': rows, 'bytes': sum(r['bytes'] for r in rows), 'file_count': len(rows)}
        (root/'manifest.json').write_bytes(geo.encode(manifest))
        return root, manifest

    def setup_publication(self):
        self.generation('one')
        report = geo.publish(self.media, 'one')
        self.assertEqual(report['hashed_asset_bytes'], 0)
        self.publication = geo.GeographyPublication(self.media, start=False)
        self.addCleanup(self.publication.close)
        self.ref = self.publication.reference()
        return self.publication

    def post(self, action, reference, **extra):
        self.calls.append((action, extra))
        if action == 'geography_manifest':
            return io.BytesIO(geo.encode(self.publication.lookup(reference['fingerprint'])['manifest']))
        source, count = self.publication.object(reference['fingerprint'], extra['file'], extra['offset'])
        with source.open('rb') as stream:
            stream.seek(extra['offset'])
            return io.BytesIO(stream.read(count))

    def cache(self, **kwargs):
        cache = geo.GeographyCache(self.worker, 'coordinator_1234567890abcdef', self.post, **kwargs)
        self.addCleanup(cache.close)
        return cache

    def test_cold_warm_restart_and_one_changed_layer(self):
        self.setup_publication()
        cache = self.cache()
        cache.prepare(self.ref)
        self.assertEqual(cache.last_sync['fetched_files'], 2)
        self.assertEqual(cache.last_sync['transferred_bytes'], 18)
        root, manifest = cache.lookup(self.ref)
        self.assertEqual((root/'layers/source.tif').read_bytes(), b'public raster')
        self.assertEqual((root/'layers/source.tif').stat().st_mtime_ns, manifest['files'][1]['mtime_ns'])
        with patch.object(Path, 'stat', side_effect=AssertionError('warm asset stat')), patch.object(cache, 'post', side_effect=AssertionError('warm network')):
            cache.prepare(self.ref)
            cache.lookup(self.ref)
        self.calls.clear()
        restarted = self.cache(); restarted.prepare(self.ref)
        self.assertEqual(self.calls, [])
        self.assertEqual(restarted.last_sync['hashed_bytes'], 0)
        self.generation('two', {'layers/index.sqlite': b'index', 'layers/source.tif': b'new raster'})
        geo.publish(self.media, 'two'); self.publication.refresh()
        new_ref = self.publication.reference(); restarted.prepare(new_ref)
        self.assertEqual(restarted.last_sync['fetched_files'], 1)
        self.assertEqual(restarted.last_sync['transferred_bytes'], 10)
        self.assertEqual([extra['file'] for action, extra in self.calls if action == 'geography_object'], ['layers/source.tif'])
        # The old leased point keeps its original immutable view.
        self.assertEqual((cache.lookup(self.ref)[0]/'layers/source.tif').read_bytes(), b'public raster')

    def dataset_manifest(self):
        rows = [{'role': 'gis', 'path': 'previous-name/height.TIF', 'size_bytes': 13,
                 'sha256': hashlib.sha256(b'public raster').hexdigest()}]
        return {'datasets': [{'dataset_id': datasets.DEFAULT_DATASET_ID,
                               'fingerprint': datasets._canonical_fingerprint(rows), 'files': rows}]}

    def test_map_reuses_dataset_content_with_different_name_without_hash_or_transfer(self):
        self.setup_publication()
        source = self.root/'old-gis'
        file = source/'previous-name/height.TIF'
        file.parent.mkdir(parents=True); file.write_bytes(b'public raster')
        datasets.sync_local(self.dataset_manifest(), source, self.worker)
        cache = self.cache(); cache.prepare(self.ref)
        self.assertEqual(cache.last_sync['transferred_bytes'], len(b'index'))
        self.assertEqual(cache.last_sync['hashed_bytes'], len(b'index'))
        current = datasets.resolve_current(self.worker)
        old_view = Path(current['path'])/'previous-name/height.TIF'
        map_view = cache.lookup(self.ref)[0]/'layers/source.tif'
        self.assertTrue(os.path.samefile(old_view, map_view))
        self.assertEqual(SourceIdentities(map_view.parent.parent/IDENTITIES_FILE).stamp(map_view)[1],
                         1_700_000_000_000_000_000)

    def test_dataset_reuses_map_and_map_gc_keeps_dataset_reference(self):
        self.setup_publication()
        cache = self.cache(); cache.prepare(self.ref)
        with patch.object(hashlib, 'file_digest', side_effect=AssertionError('unexpected hash')):
            report = datasets.sync_from_fetcher(self.dataset_manifest(), self.worker,
                    fetch_file=lambda *args: self.fail('unexpected transfer'))
        self.assertEqual(report['transferred_size_bytes'], 0)
        old_view = Path(datasets.resolve_current(self.worker)['path'])/'previous-name/height.TIF'
        self.assertTrue(os.path.samefile(old_view, cache.lookup(self.ref)[0]/'layers/source.tif'))
        self.generation('two', {'layers/index.sqlite': b'new index', 'layers/source.tif': b'new raster'})
        geo.publish(self.media, 'two'); self.publication.refresh()
        cache.prepare(self.publication.reference())
        with patch.object(geo, 'RETENTION_SECONDS', 0):
            cache.prune()
        self.assertEqual(old_view.read_bytes(), b'public raster')
        report = datasets.sync_from_fetcher(self.dataset_manifest(), self.worker,
                    fetch_file=lambda *args: self.fail('unexpected transfer after map cleanup'))
        self.assertEqual(report['transferred_size_bytes'], 0)

    def test_same_content_new_source_mtime_keeps_one_inode_and_both_logical_identities(self):
        self.setup_publication(); cache = self.cache(); cache.prepare(self.ref)
        old_root = cache.lookup(self.ref)[0]
        root, manifest = self.generation('two')
        for row in manifest['files']:
            row['mtime_ns'] += 1_000_000_000
            os.utime(root/row['path'], ns=(row['mtime_ns'],)*2)
        (root/'manifest.json').write_bytes(geo.encode(manifest))
        geo.publish(self.media, 'two'); self.publication.refresh()
        ref = self.publication.reference(); cache.prepare(ref)
        new_root = cache.lookup(ref)[0]
        self.assertEqual(cache.last_sync['transferred_bytes'], 0)
        self.assertEqual(cache.last_sync['hashed_bytes'], 0)
        self.assertTrue(os.path.samefile(old_root/'layers/source.tif', new_root/'layers/source.tif'))
        a = SourceIdentities(old_root/IDENTITIES_FILE).stamp(old_root/'layers/source.tif')
        b = SourceIdentities(new_root/IDENTITIES_FILE).stamp(new_root/'layers/source.tif')
        self.assertEqual(b[1]-a[1], 1_000_000_000)

    def test_ha_warm_poll_only_stats_pointer_no_reads_or_hashes(self):
        self.setup_publication()
        original = Path.stat
        paths = []
        def stat(path, *args, **kwargs):
            paths.append(path.name)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', stat), patch.object(Path, 'open', side_effect=AssertionError('unexpected read')), patch.object(hashlib, 'sha256', side_effect=AssertionError('unexpected hash')):
            for _ in range(10):
                self.publication.refresh(); self.publication.reference()
        self.assertEqual(set(paths), {'CURRENT.json'})

    def test_pointer_change_blocks_until_sealed_manifest_loaded(self):
        self.setup_publication()
        self.generation('two', {'layers/index.sqlite': b'changed', 'layers/source.tif': b'raster'})
        geo.publish(self.media, 'two')
        with self.assertRaisesRegex(ValueError, 'geography_not_ready'):
            self.publication.reference()
        self.publication.refresh()
        self.assertNotEqual(self.ref, self.publication.reference())

    def test_publication_rejects_changed_source_without_hashing(self):
        root, _ = self.generation('one')
        (root/'layers/source.tif').write_bytes(b'changed')
        with patch.object(hashlib, 'sha256', side_effect=AssertionError('unexpected hash')):
            with self.assertRaisesRegex(ValueError, 'geography_source_changed'):
                geo.publish(self.media, 'one')
        self.assertFalse((self.media/'CURRENT.json').exists())

    def test_authorization_path_offsets_and_limits(self):
        self.setup_publication()
        fp = self.ref['fingerprint']
        for path in ('../secret', '/etc/passwd', 'not-in-manifest', None):
            with self.assertRaises(ValueError): self.publication.object(fp, path)
        with self.assertRaises(ValueError): self.publication.object('sha256:'+'f'*64, 'layers/source.tif')
        for offset in (-1, True, 999, '0'):
            with self.assertRaises(ValueError): self.publication.object(fp, 'layers/source.tif', offset)
        self.assertEqual(self.publication.object(fp, 'layers/source.tif', 13)[1], 0)
        _, manifest = self.generation('bad')
        manifest['geography']['geography_python'] = '/bin/false'
        with self.assertRaisesRegex(ValueError, 'configuration'): geo.checked_manifest(manifest)
        manifest['geography'] = {'terrain_index': 'unknown'}
        with self.assertRaisesRegex(ValueError, 'dependency'): geo.checked_manifest(manifest)

    def test_truncated_transfer_resumes_and_never_activates_partial(self):
        self.setup_publication(); cache = self.cache()
        post = cache.post
        failed = False
        def truncated(action, ref, **extra):
            nonlocal failed
            response = post(action, ref, **extra)
            if action == 'geography_object' and extra['file'].endswith('.tif') and not failed:
                failed = True
                return io.BytesIO(response.read(4))
            return response
        cache.post = truncated
        with self.assertRaisesRegex(ValueError, 'truncated'): cache.prepare(self.ref)
        self.assertIsNone(cache.reference())
        self.assertFalse((cache.root/'CURRENT.json').exists())
        self.calls.clear(); cache.prepare(self.ref)
        self.assertEqual(cache.last_sync['fetched_files'], 1)
        self.assertEqual(cache.last_sync['transferred_bytes'], 9)
        self.assertEqual(self.calls[-1][1]['offset'], 4)

    def test_corrupt_transfer_rejected_and_retry_recovers(self):
        self.setup_publication(); cache = self.cache()
        post = cache.post
        def corrupt(action, ref, **extra):
            response = post(action, ref, **extra)
            return io.BytesIO(b'x'*len(response.read())) if action == 'geography_object' else response
        cache.post = corrupt
        with self.assertRaisesRegex(ValueError, 'checksum'): cache.prepare(self.ref)
        self.assertIsNone(cache.reference())
        cache.post = post; cache.prepare(self.ref)
        self.assertEqual(cache.reference(), self.ref['fingerprint'])

    def test_background_busy_defers_download_but_does_not_take_online(self):
        self.setup_publication()
        background, online = threading.Lock(), threading.Lock()
        background.acquire()
        cache = self.cache(background_slot=background); cache.start(); cache.request(self.ref)
        time.sleep(.12)
        self.assertEqual(self.calls, [])
        self.assertTrue(online.acquire(blocking=False)); online.release()
        background.release()
        deadline = time.monotonic()+3
        while cache.reference() is None and time.monotonic() < deadline: time.sleep(.02)
        self.assertEqual(cache.reference(), self.ref['fingerprint'])
        self.assertTrue(background.acquire(blocking=False)); background.release()

    def test_new_association_reuses_objects_without_transferring_assets(self):
        self.setup_publication(); cache = self.cache(); cache.prepare(self.ref)
        other = geo.GeographyCache(self.worker, 'coordinator_fedcba0987654321', self.post)
        self.addCleanup(other.close); other.prepare(self.ref)
        self.assertEqual(other.last_sync['transferred_bytes'], 0)
        self.assertEqual(other.last_sync['hashed_bytes'], 0)
        self.assertEqual(other.last_sync['fetched_files'], 0)

    def test_corrupt_same_size_cached_object_is_repaired_on_worker(self):
        self.setup_publication(); cache = self.cache(); cache.prepare(self.ref)
        root, manifest = cache.lookup(self.ref)
        path = root/'layers/source.tif'
        stamp = path.stat().st_mtime_ns
        path.write_bytes(b'x'*13); os.utime(path, ns=(stamp, stamp))
        restarted = self.cache(); restarted.prepare(self.ref)
        self.assertEqual(restarted.last_sync['fetched_files'], 1)
        self.assertEqual((restarted.lookup(self.ref)[0]/'layers/source.tif').read_bytes(), b'public raster')

    def test_gc_preserves_source_backups_and_active_view(self):
        self.setup_publication(); cache = self.cache(); cache.prepare(self.ref)
        backup = self.worker/'backups'/'keep'; backup.parent.mkdir(); backup.write_text('keep')
        stale = cache.root/'versions'/('e'*64); stale.mkdir(); (stale/'unused').write_text('old')
        os.utime(stale, (1, 1))
        unused = cache.objects/'orphan'; unused.write_bytes(b'old')
        with patch.object(geo, 'RETENTION_SECONDS', 0): cache.prune()
        self.assertFalse(stale.exists()); self.assertFalse(unused.exists())
        self.assertTrue(cache.lookup(self.ref)[0].exists())
        self.assertEqual(backup.read_text(), 'keep')
        self.assertTrue((self.media/'generations/one/layers/source.tif').exists())

    def test_manifest_integrity_and_unpublished_startup(self):
        publication = geo.GeographyPublication(self.media, start=False)
        self.addCleanup(publication.close)
        with self.assertRaisesRegex(ValueError, 'not_ready'): publication.reference()
        self.generation('one'); geo.publish(self.media, 'one'); publication.refresh()
        self.assertIsNotNone(publication.reference())
        manifest = json.loads((self.media/'generations/one/manifest.json').read_text())
        with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
            geo.checked_manifest(manifest, 'sha256:'+'f'*64)
        manifest['files'][0]['bytes'] = geo.MAX_TOTAL_BYTES+1
        manifest['bytes'] = sum(r['bytes'] for r in manifest['files'])
        with self.assertRaisesRegex(ValueError, 'volume_limit'): geo.checked_manifest(manifest)

    def test_upload_archive_is_portable_sealed_and_activation_is_explicit(self):
        import importlib.util
        import tarfile
        spec = importlib.util.spec_from_file_location('map_upload', Path(__file__).resolve().parents[1]/'scripts/prepare-prediction-map-upload.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.setup_publication()
        archive = self.root/'upload.tar.gz'
        receipt = module.prepare(self.media, 'one', archive)
        self.assertEqual(receipt['sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
        with tarfile.open(archive) as package:
            self.assertNotIn('CURRENT.json', package.getnames())
            self.assertIn('SHA256SUMS', package.getnames())
            self.assertEqual(package.extractfile('generations/one/layers/source.tif').read(), b'public raster')
            self.assertEqual(package.getmember('generations/one/layers/source.tif').pax_headers['mtime'], '1700000000.000000000')
        with self.assertRaisesRegex(ValueError, 'already_exists'):
            module.prepare(self.media, 'one', archive)
        # Import tools with coarse timestamp support can restore sealed index stamps.
        path = self.media/'generations/one/layers/source.tif'
        os.utime(path, ns=(1, 1))
        geo.publish(self.media, 'one', restore_timestamps=True)
        self.assertEqual(path.stat().st_mtime_ns, 1_700_000_000_000_000_000)


if __name__ == '__main__': unittest.main()
