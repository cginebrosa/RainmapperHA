import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "resize-mushroom-observation-photos.py"
SPEC = importlib.util.spec_from_file_location("resize_mushroom_observation_photos", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ObservationPhotoResizeTests(unittest.TestCase):
    def test_normalize_one_bounds_image_and_preserves_exif(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.jpg"
            target = root / "output" / "source.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (2400, 1200), "green").save(
                source, format="JPEG", quality=95, exif=exif
            )

            result = MODULE.normalize_one(source, target)

            self.assertEqual(result["output_width"], 800)
            self.assertEqual(result["output_height"], 1600)
            self.assertTrue(result["exif_preserved"])
            self.assertLess(result["output_size_bytes"], result["original_size_bytes"])
            with Image.open(target) as output:
                self.assertEqual(output.format, "JPEG")
                self.assertEqual(max(output.size), 1600)

    def test_safe_relative_photo_path_rejects_escape(self):
        with self.assertRaises(ValueError):
            MODULE.safe_relative_photo_path("media/observation-photos/../../secret.jpg")

    def test_update_media_metadata_updates_repeated_references(self):
        payload = {
            "observations": [
                {"media": [{"kind": "photo", "path": "media/observation-photos/2025/a.jpg"}]},
                {"media": [{"kind": "photo", "path": "media/observation-photos/2025/a.jpg"}]},
            ]
        }
        items = {
            "media/observation-photos/2025/a.jpg": {
                "output_size_bytes": 1234,
                "exif_preserved": True,
            }
        }

        self.assertEqual(MODULE.update_media_metadata(payload, items), 2)
        for row in payload["observations"]:
            self.assertEqual(
                row["media"][0],
                {
                    "kind": "photo",
                    "path": "media/observation-photos/2025/a.jpg",
                    "size_bytes": 1234,
                    "content_type": "image/jpeg",
                    "resized": True,
                    "exif_preserved": True,
                },
            )

    def test_verify_checks_active_and_archived_references(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "mushroom-data"
            photo = data_dir / "media" / "observation-photos" / "2025" / "a.jpg"
            photo.parent.mkdir(parents=True)
            exif = Image.Exif()
            exif[305] = "Rainmapper test"
            Image.new("RGB", (1600, 1200), "brown").save(photo, format="JPEG", exif=exif)
            media_path = "media/observation-photos/2025/a.jpg"
            item = {
                "path": media_path,
                "output_sha256": MODULE.sha256_file(photo),
                "output_size_bytes": photo.stat().st_size,
                "exif_preserved": True,
            }
            active = {
                "observations": [
                    {
                        "media": [
                            {
                                "kind": "photo",
                                "path": media_path,
                                "size_bytes": photo.stat().st_size,
                                "content_type": "image/jpeg",
                                "resized": True,
                                "exif_preserved": True,
                            }
                        ]
                    }
                ]
            }
            (data_dir / "archived").mkdir()
            (data_dir / "mushroom_observations.json").write_text(
                json.dumps(active), encoding="utf-8"
            )
            (data_dir / "archived" / "mushroom_observations_archived.json").write_text(
                json.dumps({"observations": []}), encoding="utf-8"
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"item_count": 1, "items": [item]}), encoding="utf-8"
            )
            report = root / "report.json"

            MODULE.verify(
                argparse.Namespace(data_dir=data_dir, manifest=manifest, report=report)
            )

            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(result["disk_file_count"], 1)
            self.assertEqual(result["referenced_file_count"], 1)
            self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
