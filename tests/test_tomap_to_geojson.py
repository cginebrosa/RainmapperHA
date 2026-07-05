import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

from rainmapper_core import geojson as tomap_to_geojson


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures"


class TomapToGeojsonTests(unittest.TestCase):
    def test_infer_station_source_from_station_code_pattern(self):
        self.assertEqual(tomap_to_geojson.infer_station_source("AEMET:9632X"), "AEMET")
        self.assertEqual(tomap_to_geojson.infer_station_source("ESCAT2500000025515A"), "Meteoclimatic")
        self.assertEqual(tomap_to_geojson.infer_station_source("ES1234567890123"), "Meteoclimatic")
        self.assertEqual(tomap_to_geojson.infer_station_source("ES00000000000000000"), "Meteoclimatic")
        self.assertEqual(tomap_to_geojson.infer_station_source("ES123"), "Unknown")
        self.assertEqual(tomap_to_geojson.infer_station_source("IGUILS3"), "Wunderground")
        self.assertEqual(tomap_to_geojson.infer_station_source("Z1"), "Meteocat")
        self.assertEqual(tomap_to_geojson.infer_station_source("Z12"), "Unknown")
        self.assertEqual(tomap_to_geojson.infer_station_source(""), "Unknown")

    def test_load_ignore_station_codes_supports_comments_case_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ignore_file = Path(tmp_dir) / "ignore_stations_tomap.txt"
            ignore_file.write_text(
                "\n# ignored stations\n test_drop  # bad rain spike\nTEST_OTHER\n",
                encoding="utf-8",
            )

            station_codes = tomap_to_geojson.load_ignore_station_codes(ignore_file)

        self.assertEqual(station_codes, {"TEST_DROP", "TEST_OTHER"})

    def test_filter_ignored_stations_does_not_modify_original_dataframe(self):
        df = pd.DataFrame(
            [
                {"Codi Estació": "TEST_KEEP", "Latitud": 41.1, "Longitud": 2.1},
                {"Codi Estació": "test_drop", "Latitud": 41.2, "Longitud": 2.2},
            ]
        )

        filtered, ignored_count = tomap_to_geojson.filter_ignored_stations(df, {"TEST_DROP"})

        self.assertEqual(ignored_count, 1)
        self.assertEqual(filtered["Codi Estació"].tolist(), ["TEST_KEEP"])
        self.assertEqual(df["Codi Estació"].tolist(), ["TEST_KEEP", "test_drop"])

    def test_convert_file_filters_ignored_and_invalid_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_file = tmp_path / "01_Tomap_Last_day.csv"
            output_file = tmp_path / "01d.geojson"
            shutil.copyfile(FIXTURE_DIR / "tomap_sample.csv", input_file)

            with redirect_stdout(StringIO()):
                feature_count, ignored_count, _duration_seconds = tomap_to_geojson.convert_file(
                    input_file,
                    output_file,
                    {"TEST_DROP"},
                )
            data = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(feature_count, 1)
        self.assertEqual(ignored_count, 1)
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIn("generated_at", data["metadata"])

        [feature] = data["features"]
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(feature["geometry"]["coordinates"], [2.1, 41.1])
        self.assertEqual(feature["properties"]["Codi Estació"], "TEST_KEEP")
        self.assertEqual(feature["properties"]["Pluja"], 3.5)
        self.assertEqual(feature["properties"]["Source"], "Unknown")
        self.assertNotIn("Latitud", feature["properties"])
        self.assertNotIn("Longitud", feature["properties"])

    def test_convert_file_warns_when_station_source_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_file = tmp_path / "unknown.csv"
            output_file = tmp_path / "unknown.geojson"
            input_file.write_text(
                "Codi Estació,Latitud,Longitud\nUNKNOWN_CODE,41.1,2.1\n",
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                tomap_to_geojson.convert_file(input_file, output_file, set())
            data = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertIn("WARNING", output.getvalue())
        self.assertIn("UNKNOWN_CODE", output.getvalue())
        self.assertEqual(data["features"][0]["properties"]["Source"], "Unknown")

    def test_convert_all_uses_expected_period_output_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_dir = tmp_path / "Tomap"
            output_dir = tmp_path / "PublicData"
            ignore_file = tmp_path / "ignore_stations_tomap.txt"
            input_dir.mkdir()
            shutil.copyfile(FIXTURE_DIR / "tomap_sample.csv", input_dir / "01_Tomap_Last_day.csv")
            ignore_file.write_text("TEST_DROP\n", encoding="utf-8")

            with redirect_stdout(StringIO()):
                converted = tomap_to_geojson.convert_all(input_dir, output_dir, ignore_file)
            output_exists = (output_dir / "01d.geojson").exists()

        self.assertEqual([path.name for path in converted], ["01d.geojson"])
        self.assertTrue(output_exists)

    def test_convert_file_requires_latitude_and_longitude_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_file = tmp_path / "broken.csv"
            output_file = tmp_path / "broken.geojson"
            input_file.write_text("Codi Estació,Latitud\nTEST,41.1\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Longitud"):
                tomap_to_geojson.convert_file(input_file, output_file, set())


if __name__ == "__main__":
    unittest.main()
