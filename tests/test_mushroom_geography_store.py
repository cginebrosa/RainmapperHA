import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from rainmapper_core.mushroom_geography_store import (
    IDENTITIES_FILE, ObjectStore, SourceIdentities, receipt_stamp,
)


class SharedGeographyStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = ObjectStore(self.root / 'geography')
        self.addCleanup(self.store.close)

    def source(self, name, payload, mtime):
        path = self.root / name
        path.write_bytes(payload)
        os.utime(path, ns=(mtime, mtime))
        return path, hashlib.sha256(payload).hexdigest()

    def test_same_content_different_names_and_times_has_one_object_and_original_identities(self):
        first, digest = self.source('first.tif', b'public raster', 1000000000)
        other, _ = self.source('renamed.TIF', b'public raster', 2000000000)
        for index, source in enumerate((first, other)):
            view = self.root / f'view{index}'
            with self.store.locked():
                obj = self.store.adopt_checked(source, digest, 13, receipt_stamp(source))
                self.store.link(obj, view / source.name)
                self.store.seal_view(view, [{'path': source.name, 'sha256': digest,
                    'bytes': 13, 'mtime_ns': (index+1)*1000000000}])
        self.assertEqual(len(list(self.store.objects.iterdir())), 1)
        a, b = self.root/'view0/first.tif', self.root/'view1/renamed.TIF'
        self.assertTrue(os.path.samefile(a, b))
        # A new consumer's hardlink must not invalidate the running first reader.
        self.assertEqual(SourceIdentities(a.parent/IDENTITIES_FILE).stamp(a), [13,1000000000])
        self.assertEqual(SourceIdentities(b.parent/IDENTITIES_FILE).stamp(b), [13,2000000000])
        self.assertTrue(first.exists())
        self.assertTrue(other.exists())

    def test_same_size_different_contents_are_not_deduplicated(self):
        for name, data in [('a', b'ab'), ('b', b'cd')]:
            source, digest = self.source(name, data, 1000000000)
            with self.store.locked():
                self.store.adopt_checked(source, digest, 2, receipt_stamp(source))
        self.assertEqual(len(list(self.store.objects.iterdir())), 2)

    def test_mutation_fails_closed_and_original_check_cannot_be_replayed(self):
        source, digest = self.source('source', b'ab', 1000000000)
        checked = receipt_stamp(source)
        source.write_bytes(b'cd')
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'source_changed'):
            self.store.adopt_checked(source, digest, 2, checked)

    def test_reopen_reuses_receipt_without_hashing_or_rewriting_receipts(self):
        source, digest = self.source('source', b'ab', 1000000000)
        with self.store.locked():
            self.store.adopt_checked(source, digest, 2, receipt_stamp(source))
        self.store.close()
        with self.store.locked():
            before = self.store.db.total_changes
            self.assertIsNotNone(self.store.find(digest, 2))
            self.assertEqual(self.store.db.total_changes, before)


if __name__ == '__main__':
    unittest.main()
