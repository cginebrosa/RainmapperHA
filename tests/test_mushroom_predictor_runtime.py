from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest import mock

from rainmapper_core.mushroom_predictor_runtime import build_manifest, service_paths, synchronize_runtime


class PredictorRuntimeTests(TestCase):
    def _source_tree(self, root: Path) -> tuple[Path, Path, Path, Path, Path]:
        weather = root / "weather-source"
        models = root / "models-source"
        weather.mkdir()
        models.mkdir()
        (weather / "weather_daily.parquet").write_bytes(b"daily")
        (weather / "weather_stations_catalog.parquet").write_bytes(b"catalog")
        (models / "mushroom_ml_v0_boletus.joblib").write_bytes(b"model")
        (models / "mushroom_ml_experiment_fixed_gap_7d_v1_boletus.joblib").write_bytes(
            b"shadow"
        )
        features = root / "features.json"
        sites = root / "sites.json"
        profiles = root / "profiles.json"
        features.write_text("{}", encoding="utf-8")
        sites.write_text("{}", encoding="utf-8")
        profiles.write_text('{"species_profiles": []}', encoding="utf-8")
        return weather, models, features, sites, profiles

    def test_runtime_is_content_addressed_and_reused(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            manifest, sources = build_manifest(
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            fetched: list[str] = []

            def fetch(logical_path: str, target: Path) -> None:
                fetched.append(logical_path)
                target.write_bytes(sources[logical_path].read_bytes())

            runtime, first = synchronize_runtime(root / "cache", manifest, fetch)
            reused, second = synchronize_runtime(root / "cache", manifest, fetch)

            self.assertEqual(runtime, reused)
            self.assertEqual(first["status"], "synchronized")
            self.assertEqual(second, {"status": "reused", "transferred_size_bytes": 0})
            self.assertEqual(len(fetched), len(manifest["files"]))
            self.assertTrue(service_paths(runtime)["known_sites_path"].is_file())
            self.assertTrue(service_paths(runtime)["profiles_path"].is_file())
            self.assertIn(
                "models/mushroom_ml_experiment_fixed_gap_7d_v1_boletus.joblib",
                sources,
            )

    def test_partitioned_weather_generation_is_packaged_as_predictor_runtime(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            history = weather / "weather-history"
            current = history / "CURRENT.json"
            manifest_path = history / "manifests/generation.json"
            catalog_path = history / "catalogs/stations.parquet"
            partition_path = history / "parts/source=meteocat/year=2024/data.parquet"
            for path, content in (
                (current, b"current"),
                (manifest_path, b"manifest"),
                (catalog_path, b"catalog"),
                (partition_path, b"partition"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

            generation = SimpleNamespace(
                root=history,
                manifest_path=manifest_path,
                catalog=SimpleNamespace(path="catalogs/stations.parquet"),
                partitions=(
                    SimpleNamespace(
                        path="parts/source=meteocat/year=2024/data.parquet"
                    ),
                ),
                object_path=lambda relative: history / relative,
            )

            with mock.patch(
                "rainmapper_core.weather_history_dataset.resolve_weather_generation",
                return_value=generation,
            ):
                manifest, sources = build_manifest(
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                )

            self.assertEqual(
                manifest["contracts"]["weather"], "partitioned_weather_history_v1"
            )
            self.assertIn("weather/weather-history/CURRENT.json", sources)
            self.assertIn(
                "weather/weather-history/parts/source=meteocat/year=2024/data.parquet",
                sources,
            )
            self.assertNotIn("weather/weather_daily.parquet", sources)

    def test_runtime_cache_keeps_only_current_and_immediate_predecessor(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            cache = root / "cache"
            for version in range(3):
                (models / "mushroom_ml_v0_boletus.joblib").write_bytes(
                    f"model-{version}".encode()
                )
                manifest, sources = build_manifest(
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                )
                synchronize_runtime(
                    cache,
                    manifest,
                    lambda logical_path, target: target.write_bytes(
                        sources[logical_path].read_bytes()
                    ),
                )

            self.assertEqual(len(list((cache / "versions").iterdir())), 2)
