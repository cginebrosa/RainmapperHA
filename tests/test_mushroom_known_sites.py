import json
import os
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_known_sites


class MushroomKnownSitesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        self.old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")
        self.addCleanup(self.restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(Path(__file__).resolve().parents[1] / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(self.root / "mushroom-data")

    def restore_env(self) -> None:
        for key, value in (
            ("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", self.old_defaults),
            ("RAINMAPPER_MUSHROOM_DATA_DIR", self.old_data),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_validate_hierarchy_and_build_options(self) -> None:
        payload = mushroom_known_sites.default_payload()
        area = mushroom_known_sites.empty_area("olvan")
        area["name"] = "Olvan"
        micro = mushroom_known_sites.empty_micro_area("olvan_la_pera", "olvan")
        micro["name"] = "La Pera"
        payload["areas"] = [area]
        payload["micro_areas"] = [micro]

        self.assertEqual([], mushroom_known_sites.validate_payload(payload))
        self.assertEqual([("olvan_la_pera", "Olvan · La Pera")], mushroom_known_sites.micro_area_options(payload))

        micro["area_id"] = "missing"
        self.assertIn("does not exist", " ".join(mushroom_known_sites.validate_payload(payload)))

    def test_save_creates_backup_and_counts_observation_references(self) -> None:
        payload = mushroom_known_sites.load_payload()
        area = mushroom_known_sites.empty_area("olvan")
        area["name"] = "Olvan"
        micro = mushroom_known_sites.empty_micro_area("olvan_serra_ramons", "olvan")
        micro["name"] = "Serra de Ramons"
        payload["areas"] = [area]
        payload["micro_areas"] = [micro]

        backup = mushroom_known_sites.save_payload(payload)
        self.assertIsNotNone(backup)
        saved = json.loads(mushroom_known_sites.persistent_path().read_text(encoding="utf-8"))
        self.assertEqual("olvan", saved["areas"][0]["area_id"])
        self.assertEqual(
            {"olvan_serra_ramons": 2},
            mushroom_known_sites.observation_reference_counts(
                {"observations": [{"micro_area_id": "olvan_serra_ramons"}, {"micro_area_id": "olvan_serra_ramons"}]}
            ),
        )

    def test_save_prunes_automatic_backups_but_preserves_keep_backups(self) -> None:
        payload = mushroom_known_sites.load_payload()
        target = mushroom_known_sites.persistent_path()
        backup_dir = target.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for index in range(25):
            (backup_dir / f"mushroom_known_sites.20260101T0000{index:02d}Z.json").write_text(
                "{}", encoding="utf-8"
            )
        keep_path = backup_dir / "mushroom_known_sites.20260101T999999Z.keep.json"
        keep_path.write_text("{}", encoding="utf-8")

        mushroom_known_sites.save_payload(payload)

        automatic_backups = [
            path
            for path in backup_dir.glob("mushroom_known_sites.*.json")
            if ".keep" not in path.stem
        ]
        self.assertEqual(20, len(automatic_backups))
        self.assertTrue(keep_path.exists())

    def test_polygon_geometry_is_accepted_for_areas_and_micro_areas(self) -> None:
        payload = mushroom_known_sites.default_payload()
        polygon = {
            "type": "Polygon",
            "coordinates": [[[1.90, 42.00], [1.91, 42.00], [1.91, 42.01], [1.90, 42.00]]],
        }
        area = mushroom_known_sites.empty_area("olvan")
        area.update({"name": "Olvan", "geometry": polygon})
        micro = mushroom_known_sites.empty_micro_area("olvan_la_pera", "olvan")
        micro.update({"name": "La Pera", "geometry": polygon})
        payload.update({"areas": [area], "micro_areas": [micro]})

        self.assertEqual([], mushroom_known_sites.validate_payload(payload))
        derived = mushroom_known_sites.derive_geometry_context(polygon)["geometry"]
        self.assertGreater(derived["area_ha"], 0)
        self.assertGreater(derived["perimeter_m"], 0)
        self.assertAlmostEqual(42.0033333, derived["centroid"]["lat"], places=5)


if __name__ == "__main__":
    unittest.main()
