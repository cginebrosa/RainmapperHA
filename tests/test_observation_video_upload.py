"""Video conversion failures must not masquerade as successful saves."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.test_web_server_auth import load_web_server_module


class VideoUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = load_web_server_module()

    def test_invalid_colour_header_retries_h264_copy_then_original_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'source.mp4'; source.write_bytes(b'original-video')
            command = ['ffmpeg','-i',str(source),'-t','30','-c:v','libx264',str(Path(tmp)/'out.mp4')]
            failed = subprocess.CalledProcessError(234,command,stderr='Invalid color space')
            with patch.object(self.web.subprocess,'run',side_effect=[failed,
                Mock(stdout=json.dumps({'streams':[{'codec_name':'h264'}]})),Mock(),Mock()]) as run:
                self.web.run_observation_video_conversion(command,source)
            self.assertEqual(run.call_count,4)
            repair = run.call_args_list[2].args[0]
            self.assertIn('h264_metadata=matrix_coefficients=2',repair)
            self.assertEqual(repair[repair.index('-c')+1],'copy')
            self.assertEqual(repair[repair.index('-t')+1],'30')
            retry = run.call_args_list[3].args[0]
            expected = list(command);expected[2]=str(source.with_name('normalized-colour.mkv'))
            self.assertEqual(retry,expected)
            self.assertEqual(source.read_bytes(),b'original-video')

    def test_valid_input_or_unrelated_error_never_rewrites_colour(self):
        command=['ffmpeg','-i','source.mp4','out.mp4']
        with patch.object(self.web.subprocess,'run') as run:
            self.web.run_observation_video_conversion(command,Path('source.mp4'))
        self.assertEqual(run.call_count,1)
        for error in ('decoder unavailable','Invalid color space'):
            failure=subprocess.CalledProcessError(1,command,stderr=error)
            steps=[failure] if error=='decoder unavailable' else [failure,Mock(stdout='{"streams":[{"codec_name":"vp9"}]}')]
            with patch.object(self.web.subprocess,'run',side_effect=steps) as run:
                with self.assertRaises(subprocess.CalledProcessError) as raised:
                    self.web.run_observation_video_conversion(command,Path('source.mp4'))
            self.assertIs(raised.exception,failure)
            self.assertEqual(run.call_count,len(steps))

    def test_missing_capture_metadata_does_not_block_video_or_consult_dem(self):
        with tempfile.TemporaryDirectory() as tmp:
            def convert(command,source):
                Path(command[-1]).write_bytes(b'converted-video')
            with (patch.object(self.web,'extract_video_metadata_observation_fields',side_effect=ValueError("invalid media capture date '0000:00:00 00:00:00'")),
                  patch.object(self.web,'run_observation_video_conversion',side_effect=convert),
                  patch.object(self.web.mushroom_paths,'mushroom_observation_videos_dir',return_value=Path(tmp)),
                  patch.object(self.web.mushroom_gis_lab,'sample_dem',side_effect=AssertionError('media does not require DEM'))):
                result=self.web.save_observation_video_media({'filename':'field.mp4','content':b'video'},'2026-09-25')
            self.assertEqual(result['kind'],'video')
            self.assertEqual(result['capture_metadata'],{})
            self.assertEqual((Path(tmp)/'2026'/result['stored_filename']).read_bytes(),b'converted-video')

    def async_request(self,callback):
        handler=self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        body=b'profile_action=update_observation&rainmapper_async=1'
        handler.path='/mushrooms/profiles?section=observations'
        handler.headers={'Content-Type':'application/x-www-form-urlencoded','Content-Length':str(len(body))}
        handler.rfile=io.BytesIO(body)
        handler._handle_mushroom_profiles_post_unlocked=callback
        response={};handler.send_json=lambda status,payload:response.update(status=status,payload=payload)
        handler.do_POST()
        return response

    def test_async_save_reports_conversion_validation_and_storage_errors(self):
        for message in ('video conversion failed: decoder unavailable','invalid media capture date',
                        'observation validation failed','cannot write media file'):
            def rejected(form,files):
                self.web.set_mushroom_profiles_flash(message,error=True)
                # A page consuming the shared flash must not erase this result.
                self.web.mushroom_profiles_flash()
                return '?section=observations'
            response=self.async_request(rejected)
            self.assertEqual(response['status'],422)
            self.assertEqual(response['payload']['ok'],False)
            self.assertEqual(response['payload']['error'],message)
            self.assertIsNone(self.web.MUSHROOM_PROFILE_ACTION_RESULT.get())
        success=self.async_request(lambda form,files:'?section=observations#saved')
        self.assertEqual(success,{'status':200,'payload':{'ok':True,'redirect':'?section=observations#saved'}})


if __name__ == '__main__':
    unittest.main()
