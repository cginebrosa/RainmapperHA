import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_paths, mushroom_gis_lab, mushroom_soilgrids


class LocalGeographyPathsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.media = self.root / 'unmounted-media'
        self.geography = self.root / 'docker-media/rainmapper/geography'
        for patcher in (
            patch.dict(os.environ, {}, clear=True),
            patch.object(mushroom_paths, 'repo_root', return_value=self.root),
            patch.object(mushroom_paths, 'media_root', return_value=self.media),
            patch.object(mushroom_paths, 'share_root', return_value=self.root/'share'),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_host_gis_and_soil_use_complete_operational_tree(self):
        self.geography.mkdir(parents=True)
        (self.geography/'geography-dataset.json').write_text('{}')
        (self.geography/'territorial-context.json').write_text('{}')
        gis = self.geography/'mushroom-GIS'
        (gis/'soilgrids').mkdir(parents=True)
        (gis/'geography-dataset.json').write_text('{}')
        self.assertEqual(mushroom_gis_lab.gis_root(), self.geography)
        self.assertEqual(mushroom_gis_lab.legacy_gis_root(), gis)
        self.assertEqual(mushroom_soilgrids.default_cache_root(), gis/'soilgrids')

    def test_mounted_media_takes_precedence_over_host_copy(self):
        self.media.mkdir()
        self.geography.mkdir(parents=True)
        self.assertEqual(mushroom_paths.geography_root(), self.media/'geography')

    def test_explicit_overrides_are_preserved(self):
        os.environ['RAINMAPPER_MUSHROOM_GIS_ROOT'] = str(self.root/'configured-gis')
        os.environ['RAINMAPPER_SOILGRIDS_CACHE_ROOT'] = str(self.root/'configured-soil')
        self.assertEqual(mushroom_gis_lab.gis_root(), self.root/'configured-gis')
        self.assertEqual(mushroom_soilgrids.default_cache_root(), self.root/'configured-soil')
        os.environ['RAINMAPPER_MEDIA_ROOT'] = str(self.media)
        self.assertEqual(mushroom_paths.geography_root(), self.media/'geography')

    def test_archive_and_todelete_are_never_automatic_fallbacks(self):
        for relative in ('geography-sources/originals/mushroom-GIS', 'mushroom-GIS-todelete'):
            path = self.root/relative
            (path/'soilgrids').mkdir(parents=True)
            (path/'geography-dataset.json').write_text('{}')
        self.assertFalse(mushroom_gis_lab.gis_root().exists())
        self.assertFalse(mushroom_soilgrids.default_cache_root().exists())
