"""Focused behavior tests for MapLibre's client-side IDW support gate."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


APP_JS = (
    Path(__file__).resolve().parents[1]
    / "rainmapper_core"
    / "viewers"
    / "maplibre-viewer"
    / "app.js"
)


def javascript_function(name: str) -> str:
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index(f"function {name}(")
    end = source.index("\n}\n", start) + len("\n}\n")
    return source[start:end]


class MapLibreIdwSupportTests(unittest.TestCase):
    def run_javascript(self, source: str) -> object:
        result = subprocess.run(
            ["node", "-e", source],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_zero_rain_is_finite_spatial_support(self) -> None:
        function = javascript_function("estimatedFieldPaintSupport")
        result = self.run_javascript(
            function
            + "\nconsole.log(JSON.stringify({"
            + 'zero: estimatedFieldPaintSupport(0, {id: "rain"}),'
            + 'positive: estimatedFieldPaintSupport(2.5, {id: "rain"}),'
            + 'missing: estimatedFieldPaintSupport(Number.NaN, {id: "rain"})'
            + "}));"
        )

        self.assertEqual(result, {"zero": 1, "positive": 1, "missing": 0})

    def test_na_is_filtered_but_zero_remains_usable(self) -> None:
        functions = "\n".join(
            [
                javascript_function("parseOptionalNumber"),
                javascript_function("featureMetricValue"),
                javascript_function("estimatedFieldUsableFeatures"),
            ]
        )
        result = self.run_javascript(
            "const enabledStationSources = new Set(['Wunderground']);\n"
            "function selectedLayerMetric() { return {id: 'rain', property: 'Total'}; }\n"
            "function featureStationSource(feature) { return feature.properties.Source; }\n"
            "function featureAltitude() { return null; }\n"
            + functions
            + "\nconst features = ["
            + "{properties:{Source:'Wunderground',Total:0},geometry:{coordinates:[1.96,42.34]}},"
            + "{properties:{Source:'Wunderground',Total:null},geometry:{coordinates:[1.97,42.35]}},"
            + "{properties:{Source:'Meteocat',Total:3},geometry:{coordinates:[1.98,42.36]}}"
            + "];"
            + "console.log(JSON.stringify(estimatedFieldUsableFeatures(features).map(x => x.value)));"
        )

        self.assertEqual(result, [0])

    def test_zero_station_inside_core_radius_produces_zero_not_null(self) -> None:
        functions = "\n".join(
            [
                javascript_function("haversineKm"),
                javascript_function("estimatedFieldPaintSupport"),
                javascript_function("estimateFieldCellValue"),
            ]
        )
        result = self.run_javascript(
            "function isTemperatureMetric() { return false; }\n"
            "function estimatedFieldTemperatureLapseRate() { return 0.65; }\n"
            + functions
            + "\nconst value = estimateFieldCellValue("
            + "{lng: 2, lat: 42}, [{lng: 2.05, lat: 42, value: 0, altitude: null}], "
            + "15, 2, {id: 'rain'}, null);"
            + "console.log(JSON.stringify(value));"
        )

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
