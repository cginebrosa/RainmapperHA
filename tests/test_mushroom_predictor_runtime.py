from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest import mock

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_predictor_runtime
from rainmapper_core.mushroom_predictor_runtime import (
    build_manifest,
    build_runtime_archive,
    cache_runtime_objects,
    invalidate_published_manifest,
    load_or_publish_manifest,
    load_published_manifest,
    load_published_manifest_metadata,
    publish_manifest,
    service_paths,
    synchronize_runtime,
    synchronize_runtime_archive,
)


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
            self.assertEqual(second["status"], "reused")
            self.assertEqual(second["transferred_size_bytes"], 0)
            self.assertEqual(second["verification_status"], "receipt")
            self.assertEqual(second["hashed_file_count"], 0)
            self.assertEqual(second["reused_file_count"], len(manifest["files"]))
            self.assertEqual(second["fetched_file_count"], 0)
            self.assertGreaterEqual(second["elapsed_seconds"], 0.0)
            self.assertEqual(len(fetched), len(manifest["files"]))
            self.assertTrue(service_paths(runtime)["known_sites_path"].is_file())
            self.assertTrue((runtime / "verified-runtime.json").is_file())
            self.assertTrue(service_paths(runtime)["profiles_path"].is_file())
            self.assertIn(
                "models/mushroom_ml_experiment_fixed_gap_7d_v1_boletus.joblib",
                sources,
            )

    def test_preferred_version_is_not_part_of_runtime_identity(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            (models / "batches/example").mkdir(parents=True)
            (models / "batches/example/manifest.json").write_text(
                "{}", encoding="utf-8"
            )
            registry_path = root / "mushroom_ml_version_registry.json"
            registry_path.write_text("{}", encoding="utf-8")
            common = {
                "schema_version": "1.0",
                "kind": "rainmapper_mushroom_ml_version_registry",
                "versions": [],
            }

            with mock.patch(
                "rainmapper_core.mushroom_ml_version_registry.load_registry",
                side_effect=[
                    {**common, "preferred_version_id": "biology_v4"},
                    {**common, "preferred_version_id": "biology_v6_windowed"},
                    {**common, "preferred_version_id": "biology_v4"},
                ],
            ):
                first, first_sources = build_manifest(
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                    version_registry_path=registry_path,
                )
                second, _second_sources = build_manifest(
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                    version_registry_path=registry_path,
                )
                (models / "mushroom_ml_v0_boletus.joblib").write_bytes(
                    b"changed-scientific-model"
                )
                third, _third_sources = build_manifest(
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                    version_registry_path=registry_path,
                )

            runtime_registry = first_sources[
                "data/mushroom_ml_version_registry.json"
            ]
            self.assertNotIn(
                "preferred_version_id",
                json.loads(runtime_registry.read_text(encoding="utf-8")),
            )
            self.assertEqual(first["fingerprint"], second["fingerprint"])
            self.assertNotEqual(second["fingerprint"], third["fingerprint"])

    def test_preference_file_change_reuses_canonical_publication(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            (models / "batches/example").mkdir(parents=True)
            (models / "batches/example/manifest.json").write_text(
                "{}", encoding="utf-8"
            )
            registry_path = root / "mushroom_ml_version_registry.json"
            registry_path.write_text('{"preferred_version_id":"biology_v4"}')
            publication = root / "cache/published-runtime.json"
            registry = {
                "schema_version": "1.0",
                "kind": "rainmapper_mushroom_ml_version_registry",
                "preferred_version_id": "biology_v4",
                "versions": [],
            }
            with mock.patch(
                "rainmapper_core.mushroom_ml_version_registry.load_registry",
                return_value=registry,
            ):
                published, _sources = publish_manifest(
                    publication,
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                    version_registry_path=registry_path,
                )

            registry_path.write_text(
                '{"preferred_version_id":"biology_v6_windowed"}'
            )
            reused, _sources, status = load_or_publish_manifest(publication)

            self.assertEqual("reused", status)
            self.assertEqual(published["fingerprint"], reused["fingerprint"])

    def test_runtime_registry_snapshot_tracks_the_complete_registry(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = root / "mushroom_ml_version_registry.json"
            versions = [
                {"version_id": "biology_v4", "installed_generation_id": "g4"},
                {"version_id": "biology_v6", "installed_generation_id": "g6"},
            ]
            first = mushroom_predictor_runtime._runtime_registry_snapshot(
                {"preferred_version_id": "biology_v4", "versions": versions},
                source_path=registry_path,
                explicit_source=True,
            )
            second = mushroom_predictor_runtime._runtime_registry_snapshot(
                {"preferred_version_id": "biology_v6", "versions": versions},
                source_path=registry_path,
                explicit_source=True,
            )

            self.assertEqual(first, second)
            self.assertEqual(
                {"versions": versions},
                json.loads(second.read_text(encoding="utf-8")),
            )

    def test_published_metadata_load_does_not_inspect_runtime_sources(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            publication = root / "cache/published-runtime.json"
            manifest, _sources = publish_manifest(
                publication,
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            for source in (weather, models, features, sites, profiles):
                if source.is_dir():
                    for child in source.iterdir():
                        child.unlink()
                    source.rmdir()
                else:
                    source.unlink()

            self.assertEqual(manifest, load_published_manifest_metadata(publication))

    def test_reused_runtime_receipt_does_not_rehash_installed_files(self) -> None:
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
            cache = root / "cache"
            synchronize_runtime(
                cache,
                manifest,
                lambda logical_path, target: target.write_bytes(
                    sources[logical_path].read_bytes()
                ),
            )

            with mock.patch.object(
                mushroom_predictor_runtime,
                "_sha256",
                side_effect=AssertionError("a sealed runtime must not be rehashed"),
            ):
                reused, result = synchronize_runtime(
                    cache,
                    manifest,
                    lambda _logical_path, _target: self.fail("nothing should be fetched"),
                )

            self.assertEqual(
                reused.resolve(),
                mushroom_predictor_runtime.current_runtime(cache),
            )
            self.assertEqual(result["verification_status"], "receipt")

    def test_missing_runtime_receipt_forces_full_verification_once(self) -> None:
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
            cache = root / "cache"
            runtime, _result = synchronize_runtime(
                cache,
                manifest,
                lambda logical_path, target: target.write_bytes(
                    sources[logical_path].read_bytes()
                ),
            )
            (runtime / "verified-runtime.json").unlink()

            with mock.patch.object(
                mushroom_predictor_runtime,
                "_sha256",
                wraps=mushroom_predictor_runtime._sha256,
            ) as digest:
                _runtime, result = synchronize_runtime(
                    cache,
                    manifest,
                    lambda _logical_path, _target: self.fail("nothing should be fetched"),
                )

            self.assertEqual(digest.call_count, len(manifest["files"]))
            self.assertEqual(result["verification_status"], "receipt")
            self.assertTrue((runtime / "verified-runtime.json").is_file())

    def test_published_manifest_is_reused_without_hashing_sources(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            publication = root / "cache/published-runtime.json"
            expected, _sources = publish_manifest(
                publication,
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )

            with mock.patch.object(
                mushroom_predictor_runtime,
                "_sha256",
                side_effect=AssertionError("a published manifest must not rehash sources"),
            ):
                manifest, sources, status = load_or_publish_manifest(publication)

            self.assertEqual(status, "reused")
            self.assertEqual(manifest, expected)
            self.assertEqual(set(sources), {row["path"] for row in expected["files"]})

    def test_dirty_publication_is_rebuilt_after_source_change(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            publication = root / "cache/published-runtime.json"
            original, _sources = publish_manifest(
                publication,
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            (models / "mushroom_ml_v0_boletus.joblib").write_bytes(b"changed-model")
            invalidate_published_manifest(publication)

            updated, _sources, status = load_or_publish_manifest(
                publication,
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )

            self.assertEqual(status, "published")
            self.assertNotEqual(updated["fingerprint"], original["fingerprint"])
            self.assertEqual(load_published_manifest(publication)[0], updated)

    def test_publication_detects_unannounced_change_and_hashes_only_that_file(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            publication = root / "cache/published-runtime.json"
            original, _sources = publish_manifest(
                publication,
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            changed = models / "mushroom_ml_v0_boletus.joblib"
            changed.write_bytes(b"a-different-sized-model")
            mushroom_predictor_runtime._DIGEST_CACHE.clear()
            original_sha256 = mushroom_predictor_runtime._sha256
            content_hashes: list[Path] = []

            def tracked_sha256(path: Path) -> str:
                stat = path.stat()
                cache_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
                if cache_key not in mushroom_predictor_runtime._DIGEST_CACHE:
                    content_hashes.append(path)
                return original_sha256(path)

            with mock.patch.object(
                mushroom_predictor_runtime,
                "_sha256",
                side_effect=tracked_sha256,
            ):
                updated, _sources, status = load_or_publish_manifest(
                    publication,
                    weather_data_dir=weather,
                    models_dir=models,
                    features_artifact_path=features,
                    known_sites_path=sites,
                    profiles_path=profiles,
                )

            self.assertEqual(status, "published")
            self.assertNotEqual(updated["fingerprint"], original["fingerprint"])
            self.assertEqual(content_hashes, [changed])

    def test_changed_runtime_reuses_unchanged_sealed_files_by_manifest(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            original, original_sources = build_manifest(
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            cache = root / "cache"
            synchronize_runtime(
                cache,
                original,
                lambda logical_path, target: target.write_bytes(
                    original_sources[logical_path].read_bytes()
                ),
            )
            changed_path = models / "mushroom_ml_v0_boletus.joblib"
            changed_path.write_bytes(b"changed-model")
            updated, updated_sources = build_manifest(
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
            )
            fetched: list[str] = []

            with mock.patch.object(
                mushroom_predictor_runtime,
                "_sha256",
                wraps=mushroom_predictor_runtime._sha256,
            ) as digest:
                _runtime, result = synchronize_runtime(
                    cache,
                    updated,
                    lambda logical_path, target: (
                        fetched.append(logical_path),
                        target.write_bytes(updated_sources[logical_path].read_bytes()),
                    ),
                )

            self.assertEqual(fetched, ["models/mushroom_ml_v0_boletus.joblib"])
            self.assertEqual(digest.call_count, 1)
            self.assertEqual(
                result["transferred_size_bytes"],
                changed_path.stat().st_size,
            )

    def test_runtime_archive_transfers_all_files_in_one_verified_container(self) -> None:
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

            archive = build_runtime_archive(root / "archives", manifest, sources)
            runtime, result = synchronize_runtime_archive(
                root / "cache",
                manifest,
                archive,
            )

            self.assertEqual(result["status"], "synchronized")
            self.assertEqual(result["transferred_size_bytes"], manifest["size_bytes"])
            self.assertTrue(service_paths(runtime)["features_artifact_path"].is_file())
            self.assertEqual(build_runtime_archive(root / "archives", manifest, sources), archive)
            self.assertEqual((root / "archives").stat().st_mode & 0o777, 0o700)
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)

            archive.write_bytes(b"truncated")
            rebuilt = build_runtime_archive(root / "archives", manifest, sources)
            rebuilt_runtime, rebuilt_result = synchronize_runtime_archive(
                root / "rebuilt-cache",
                manifest,
                rebuilt,
            )
            self.assertEqual(rebuilt, archive)
            self.assertGreater(rebuilt.stat().st_size, len(b"truncated"))
            self.assertEqual(rebuilt_result["status"], "synchronized")
            self.assertTrue(service_paths(rebuilt_runtime)["profiles_path"].is_file())

            stale = root / "archives" / "stale.tar"
            stale.write_bytes(b"stale")
            self.assertEqual(build_runtime_archive(root / "archives", manifest, sources), archive)
            self.assertFalse(stale.exists())

    def test_runtime_reuses_worker_produced_objects_by_digest(self) -> None:
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
            model_row = next(row for row in manifest["files"] if row["path"].endswith("boletus.joblib"))
            cache = root / "cache"
            cache_runtime_objects(
                cache,
                [(sources[model_row["path"]], model_row["sha256"], model_row["size_bytes"])],
            )
            fetched: list[str] = []

            synchronize_runtime(
                cache,
                manifest,
                lambda logical_path, target: (
                    fetched.append(logical_path),
                    target.write_bytes(sources[logical_path].read_bytes()),
                ),
            )

            self.assertNotIn(model_row["path"], fetched)
            self.assertFalse((cache / "objects").exists())

    def test_runtime_packages_enabled_station_source_contract(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            stations = root / "stations.txt"
            stations.write_text("Wunderground;TEST;false\n", encoding="utf-8")
            manifest, sources = build_manifest(
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
                stations_file_path=stations,
            )

            self.assertIn("data/stations.txt", sources)
            self.assertTrue(
                any(row["path"] == "data/stations.txt" for row in manifest["files"])
            )
            self.assertEqual(
                service_paths(root)["stations_file_path"], root / "data/stations.txt"
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

    def test_runtime_packages_exact_multiversion_batch(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather, models, features, sites, profiles = self._source_tree(root)
            registry = (
                Path(__file__).resolve().parents[1]
                / "mushroom-data/mushroom_ml_version_registry.json"
            )
            model_ref = mushroom_ml_model_catalog.ModelRef.from_mapping(
                {
                    "batch_id": "batch-a",
                    "generation_id": "generation-a",
                    "version_id": "altitude_v2",
                    "temporal_contract_id": "lag_event_altitude_v2",
                    "profile_id": "common_idw",
                    "estimator_id": "logistic_regression_reduced_v1",
                    "species_id": "lactarius_deliciosus",
                    "horizon_days": 3,
                }
            )
            relative = mushroom_ml_model_catalog.model_relative_path(model_ref)
            artifact = models / relative
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"multiversion-model")
            import hashlib
            import json

            batch_path = models / "batches/batch-a/manifest.json"
            batch_path.parent.mkdir(parents=True, exist_ok=True)
            quality_path = batch_path.parent / "quality-catalog.json"
            quality_audit_path = batch_path.parent / "quality-audit-catalog.json"
            quality_path.write_text("{}", encoding="utf-8")
            quality_audit_path.write_text("{}", encoding="utf-8")
            batch_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "kind": "mushroom_ml_runtime_batch",
                        "batch_id": "batch-a",
                        "snapshot_id": "sha256:" + "a" * 64,
                        "artifacts": [
                            {
                                "artifact_ref": model_ref.artifact_ref.as_dict(),
                                "supported_horizons": list(range(1, 8)),
                                "path": relative.as_posix(),
                                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                            }
                        ],
                        "quality_catalog": {
                            "path": "batches/batch-a/quality-catalog.json",
                            "sha256": hashlib.sha256(
                                quality_path.read_bytes()
                            ).hexdigest(),
                        },
                        "quality_audit_catalog": {
                            "path": (
                                "batches/batch-a/quality-audit-catalog.json"
                            ),
                            "sha256": hashlib.sha256(
                                quality_audit_path.read_bytes()
                            ).hexdigest(),
                            "selection_id": "sha256:" + "c" * 64,
                        },
                    }
                ),
                encoding="utf-8",
            )

            from rainmapper_core import mushroom_ml_version_registry

            registry_payload = mushroom_ml_version_registry.load_registry(registry)
            registry_payload = mushroom_ml_version_registry.append_generation(
                registry_payload,
                version_id="altitude_v2",
                generation={
                    "generation_id": "generation-a",
                    "kind": "trained_model",
                    "promotion_gate_status": "passed",
                    "profile_ids": ["common_idw"],
                    "batch_id": "batch-a",
                },
            )
            registry_payload = mushroom_ml_version_registry.transition_active_generation(
                registry_payload,
                "altitude_v2",
                generation_id="generation-a",
            )
            runtime_registry = root / "runtime-registry.json"
            mushroom_ml_version_registry.save_registry(
                runtime_registry, registry_payload
            )

            manifest, sources = build_manifest(
                weather_data_dir=weather,
                models_dir=models,
                features_artifact_path=features,
                known_sites_path=sites,
                profiles_path=profiles,
                version_registry_path=runtime_registry,
            )

            self.assertEqual(
                manifest["contracts"]["models"],
                "mushroom_ml_v0_plus_multiversion_v1_joblib",
            )
            self.assertIn("data/mushroom_ml_version_registry.json", sources)
            self.assertIn(f"models/{relative.as_posix()}", sources)
            self.assertIn("models/batches/batch-a/manifest.json", sources)
            self.assertIn("models/batches/batch-a/quality-catalog.json", sources)
            self.assertIn(
                "models/batches/batch-a/quality-audit-catalog.json", sources
            )
            self.assertNotIn("models/runtime-batch.json", sources)
