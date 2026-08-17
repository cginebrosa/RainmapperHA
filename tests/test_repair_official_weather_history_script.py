import importlib.util
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pyarrow as pa


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/repair-official-weather-history.py"


def load_script():
    spec = importlib.util.spec_from_file_location("repair_official_weather_history", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepairOfficialWeatherHistoryScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script()

    def test_meteocat_batches_preserve_zero_and_condition_only_day(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "estacions_xema.csv"
            pd.DataFrame(
                [
                    {
                        "Codi Estació": "CR",
                        "Estació": "Olvan",
                        "Comarca": "Berguedà",
                        "Municipi": "Olvan",
                        "Provincia": "Barcelona",
                        "Altitud": "600",
                        "Latitud": "42.0",
                        "Longitud": "1.9",
                    }
                ]
            ).to_csv(catalog, index=False)
            self.module.atomic_json_gzip(
                root / "rain_20200801_20200815.json.gz",
                [
                    {
                        "codi_estacio": "CR",
                        "ultima_lectura": "2020-08-01T00:00:00.000",
                        "codi_variable": "35",
                        "valor_variable": "0",
                    }
                ],
            )
            self.module.atomic_json_gzip(
                root / "conditions_20200801_20200815.json.gz",
                [
                    {
                        "codi_estacio": "CR",
                        "ultima_lectura": "2020-08-01T00:00:00.000",
                        "codi_variable": "40",
                        "max_valor_variable": "28.0",
                        "min_valor_variable": "12.0",
                    },
                    {
                        "codi_estacio": "CR",
                        "ultima_lectura": "2020-08-02T00:00:00.000",
                        "codi_variable": "3",
                        "max_valor_variable": "91",
                        "min_valor_variable": "40",
                    },
                ],
            )

            tables = list(self.module.meteocat_batches(root, catalog))
            frame = pa.concat_tables(tables).to_pandas().sort_values("Data Local")

            self.assertEqual(frame["Data Local"].tolist(), ["20200801", "20200802"])
            self.assertEqual(frame.iloc[0]["Total"], "0")
            self.assertTrue(pd.isna(frame.iloc[1]["Total"]))
            self.assertEqual(frame.iloc[1]["max_humidity_percent"], "91")


if __name__ == "__main__":
    unittest.main()
