import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import threading
from rainmapper_core import mushroom_map_volume as volume


class MapVolumeTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir()
        self.asset=self.source/'maps'/'geology.gpkg';self.asset.parent.mkdir()
        self.asset.write_bytes(b'public map bytes')
        os.utime(self.asset,ns=(1789000000123456789,1789000000123456789))
        self.config={'geology':'maps/geology.gpkg','profiles':'private.json',
                     'model_registry':'registry.json','token':'must not export'}
        self.data=volume.plan(self.config,self.source)
        self.dest=self.root/'destination'

    def test_plan_is_public_and_has_no_machine_paths(self):
        self.assertEqual(self.data['file_count'],1)
        self.assertNotIn('profiles',self.data['geography'])
        self.assertNotIn('token',json.dumps(self.data))
        self.assertNotIn(str(self.root),json.dumps(self.data))

    def test_copy_preserves_nanoseconds_and_second_install_has_no_io(self):
        first=volume.install(self.data,self.source,self.dest)
        self.assertEqual(first['transferred_bytes'],self.asset.stat().st_size)
        installed=self.dest/'maps/geology.gpkg'
        self.assertEqual(installed.stat().st_mtime_ns,self.asset.stat().st_mtime_ns)
        with patch.object(volume,'digest',side_effect=AssertionError('rehash')):
            self.assertEqual(volume.install(self.data,self.source,self.dest)['hashed_bytes'],0)
        # Sealed package supports a separate destination without original machine paths.
        sealed=json.loads((self.dest/'manifest.json').read_text())
        volume.install(sealed,self.dest,self.root/'other')
        self.assertEqual((self.root/'other/maps/geology.gpkg').read_bytes(),self.asset.read_bytes())

    def test_hardlinks_and_resume_staging(self):
        stage=self.dest/'maps/geology.gpkg.installing';stage.parent.mkdir(parents=True)
        os.link(self.asset,stage)
        result=volume.install(self.data,self.source,self.dest,link=True)
        self.assertEqual(result['transferred_bytes'],0)
        self.assertTrue(os.path.samefile(self.asset,self.dest/'maps/geology.gpkg'))

    def test_checksum_failure_does_not_publish_receipt(self):
        self.data['files'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'checksum'):
            volume.install(self.data,self.source,self.dest)

        self.assertFalse((self.dest/'manifest.json').exists())

    def test_source_mutation_and_existing_generation_not_overwritten(self):
        volume.install(self.data,self.source,self.dest)
        changed=copy.deepcopy(self.data);changed['geography']['geology']='other.gpkg'
        with self.assertRaisesRegex(ValueError,'generation_conflict'):
            volume.install(changed,self.source,self.dest)
        self.asset.write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError,'source_changed'):
            volume.install(self.data,self.source,self.root/'new')

    def test_paths_duplicates_and_escape_rejected_before_copy(self):
        for path in ('../private.json','/etc/passwd','maps/../../outside'):
            data=copy.deepcopy(self.data);data['files'][0]['path']=path
            with self.assertRaises(ValueError):volume.install(data,self.source,self.dest)
        data=copy.deepcopy(self.data);data['files']*=2
        with self.assertRaises(ValueError):volume.install(data,self.source,self.dest)
        self.dest.mkdir();(self.dest/'maps').symlink_to(self.source/'maps',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'escape'):
            volume.install(self.data,self.source,self.dest)


class PointReadinessTest(unittest.TestCase):
    def test_all_configured_readers_and_model_must_be_ready(self):
        from rainmapper_core.mushroom_map_execution import PointExecutor
        executor=object.__new__(PointExecutor)
        executor.lock=threading.Lock()
        executor.geography=Mock();executor.weather=Mock();executor.model=Mock()
        executor.geography.call.return_value={'terrain_ready':True,'geography_ready':False}
        executor.weather.call.return_value={'weather_ready':True}
        executor.model.call.return_value={'model_ready':True}
        self.assertFalse(executor.ready())
        executor.geography.call.return_value['geography_ready']=True
        executor.model.call.return_value={'model_ready':False}
        self.assertFalse(executor.ready())
        executor.model.call.return_value={'model_ready':True}
        self.assertTrue(executor.ready())
