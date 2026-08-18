import json
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


class MushroomWorkerPackagingTests(unittest.TestCase):
    def test_worker_image_is_minimal_and_uses_python_311(self) -> None:
        dockerfile = (ROOT_DIR / "rainmapper-worker/Dockerfile").read_text(encoding="utf-8")
        dockerignore = (ROOT_DIR / ".dockerignore").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn("ARG RAINMAPPER_WORKER_VERSION=1.0.14", dockerfile)
        self.assertIn("gdal-bin", dockerfile)
        self.assertIn("gosu", dockerfile)
        self.assertIn("mushroom_rebuild_contracts.py", dockerfile)
        self.assertIn("mushroom_worker_dataset_cache.py", dockerfile)
        self.assertIn("mushroom_worker_config.py", dockerfile)
        self.assertIn("mushroom_worker_registry.py", dockerfile)
        self.assertIn("mushroom_worker_service.py", dockerfile)
        self.assertIn("mushroom_ml_experiments.py", dockerfile)
        self.assertIn("mushroom_ml_experiment_trainer.py", dockerfile)
        self.assertIn("mushroom_ml_input_identity.py", dockerfile)
        self.assertIn("mushroom_ml_version_registry.py", dockerfile)
        self.assertIn("mushroom_ml_version_registry.json", dockerfile)
        self.assertIn("mushroom_ml_comparison.py", dockerfile)
        self.assertIn("mushroom_ml_biology_v3.py", dockerfile)
        self.assertIn("mushroom_ml_biology_v3_evaluation.py", dockerfile)
        self.assertIn("mushroom_weather_idw.py", dockerfile)
        self.assertIn("mushroom_prediction_interpretation.py", dockerfile)
        self.assertIn("weather_history_contract.py", dockerfile)
        self.assertIn("weather_history_dataset.py", dockerfile)
        self.assertIn("run-mushroom-rebuild-job.py", dockerfile)
        self.assertIn("manage-mushroom-worker-datasets.py", dockerfile)
        self.assertIn("manage-mushroom-worker-config.py", dockerfile)
        self.assertIn("run-mushroom-worker-service.py", dockerfile)
        self.assertIn("build-biology-v3-benchmark.py", dockerfile)
        self.assertIn("prepare-mushroom-ml-multiversion-inputs.py", dockerfile)
        self.assertNotIn("evaluate-biology-v3-benchmark.py", dockerfile)
        self.assertNotIn("COPY mushroom-data/ /app/mushroom-data/", dockerfile)
        self.assertNotIn("web_server.py", dockerfile)
        self.assertNotIn("requirements.txt", dockerfile)
        self.assertNotIn("ffmpeg", dockerfile.lower())
        self.assertNotIn("exiftool", dockerfile.lower())
        self.assertIn("docker-data", dockerignore.splitlines())
        self.assertIn("mushroom-GIS", dockerignore.splitlines())

    def test_ha_image_packages_coordinator_without_enabling_it(self) -> None:
        dockerfile = (ROOT_DIR / "rainmapper-app/Dockerfile").read_text(encoding="utf-8")
        config = (ROOT_DIR / "rainmapper-app/config.yaml").read_text(encoding="utf-8")
        run_script = (ROOT_DIR / "rainmapper-app/run.sh").read_text(encoding="utf-8")
        translations = (ROOT_DIR / "rainmapper-app/translations/en.yaml").read_text(encoding="utf-8")

        self.assertIn("COPY rainmapper_core/ /app/rainmapper_core/", dockerfile)
        self.assertIn("mushroom_workers_ui.py", dockerfile)
        self.assertIn("run-mushroom-rebuild-job.py", dockerfile)
        self.assertIn("run-mushroom-ml-train-job.py", dockerfile)
        self.assertIn("run-mushroom-ml-multiversion-job.py", dockerfile)
        self.assertIn("prepare-mushroom-ml-multiversion-inputs.py", dockerfile)
        self.assertNotIn("COPY mushroom-data/ /app/mushroom-data/", dockerfile)
        self.assertIn(
            "rainmapper-app/defaults/mushroom_observations.json",
            dockerfile,
        )
        empty_observations = json.loads(
            (ROOT_DIR / "rainmapper-app/defaults/mushroom_observations.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([], empty_observations["observations"])
        self.assertNotIn("docker-data", dockerfile)
        self.assertNotIn("mushroom-GIS", dockerfile)
        self.assertIn("8100/tcp: null", config)
        self.assertIn("external_worker_connections_enabled: false", config)
        self.assertIn("external_worker_rebuilds_enabled: false", config)
        self.assertNotIn("predictor_executor_selection_enabled", config)
        self.assertNotIn("predictor_home_assistant_executor_enabled", config)
        self.assertIn('export RAINMAPPER_WORKER_API_ENABLED="$EXTERNAL_WORKER_CONNECTIONS_ENABLED_VALUE"', run_script)
        self.assertIn(
            'export RAINMAPPER_WORKER_AUTH_REQUIRED="${RAINMAPPER_WORKER_AUTH_REQUIRED:-true}"',
            run_script,
        )
        self.assertIn('export RAINMAPPER_WORKER_OPERATIONAL_ENABLED="$EXTERNAL_WORKER_REBUILDS_ENABLED_VALUE"', run_script)
        self.assertNotIn("RAINMAPPER_PREDICTOR_EXECUTOR_SELECTION_ENABLED", run_script)
        self.assertNotIn("RAINMAPPER_PREDICTOR_HOME_ASSISTANT_ENABLED", run_script)
        self.assertNotIn("RAINMAPPER_LOCAL_HA_COMPUTE_ENABLED", run_script)
        self.assertIn("--worker-port 8100", run_script)
        self.assertIn("name: Enable external worker connections", translations)
        self.assertIn("name: Allow external rebuilds and promotion", translations)
        self.assertNotIn("predictor_executor_selection_enabled", translations)
        self.assertNotIn("predictor_home_assistant_executor_enabled", translations)

    def test_worker_compose_is_offline_read_only_and_persistent(self) -> None:
        compose = (ROOT_DIR / "rainmapper-local/docker-compose.worker-test.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("image: rainmapper-worker:local", compose)
        self.assertIn("container_name: rainmapper-worker", compose)
        self.assertIn("pull_policy: never", compose)
        self.assertIn("network_mode: none", compose)
        self.assertIn("name: rainmapper-worker-data", compose)
        self.assertEqual(compose.count(":ro"), 2)
        self.assertNotIn("docker-data", compose)
        self.assertIn("/datasets/mushroom_gis_v0/current", compose)
        self.assertIn("--worker-data-dir", compose)

    def test_worker_entrypoint_drops_privileges(self) -> None:
        entrypoint = (ROOT_DIR / "rainmapper-worker/entrypoint.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("gosu rainmapper-worker:rainmapper-worker", entrypoint)
        self.assertIn("/var/lib/rainmapper-worker", entrypoint)
        self.assertIn('"$1" = "dataset"', entrypoint)
        self.assertIn('"$1" = "config"', entrypoint)
        self.assertIn('"$1" = "serve"', entrypoint)

    def test_local_worker_service_is_startable_and_stoppable_without_volume_deletion(self) -> None:
        compose = (ROOT_DIR / "rainmapper-local/docker-compose.worker-local.yml").read_text(
            encoding="utf-8"
        )
        start = (ROOT_DIR / "mushroom_worker_start.sh").read_text(encoding="utf-8")
        stop = (ROOT_DIR / "mushroom_worker_stop.sh").read_text(encoding="utf-8")

        self.assertIn(
            "image: rainmapper-worker:${RAINMAPPER_WORKER_VERSION:-1.0.14}",
            compose,
        )
        self.assertIn(
            "RAINMAPPER_WORKER_VERSION: ${RAINMAPPER_WORKER_VERSION:-1.0.14}",
            compose,
        )
        self.assertIn("name: rainmapper-worker-local", compose)
        self.assertIn("container_name: rainmapper-worker", compose)
        self.assertIn('127.0.0.1:8110:8098', compose)
        self.assertIn("name: rainmapper-worker-data", compose)
        self.assertIn("external: true", compose)
        self.assertIn("name: rainmapper-local-compute", compose)
        self.assertNotIn("RAINMAPPER_HA_URL", compose)
        self.assertIn("RAINMAPPER_WORKER_DISPLAY_NAME", compose)
        self.assertIn("RAINMAPPER_WORKER_HOST_NAME", compose)
        self.assertIn('RAINMAPPER_WORKER_HEARTBEAT_INTERVAL: "2"', compose)
        self.assertNotIn("docker-data", compose)
        self.assertIn("docker compose", start)
        self.assertIn('WORKER_VOLUME="rainmapper-worker-data"', start)
        self.assertIn('WORKER_IMAGE="rainmapper-worker:${RAINMAPPER_WORKER_VERSION}"', start)
        self.assertIn("export RAINMAPPER_WORKER_VERSION", start)
        self.assertIn('docker volume create "${WORKER_VOLUME}"', start)
        self.assertIn('WORKER_NETWORK="rainmapper-local-compute"', start)
        self.assertIn('docker network create "${WORKER_NETWORK}"', start)
        self.assertIn("--name", start)
        self.assertIn("--rainmapper-url", start)
        self.assertIn("--token-stdin", start)
        self.assertIn("--non-interactive", start)
        self.assertIn("rainmapper-worker-data", start)
        self.assertIn("scutil --get ComputerName", start)
        self.assertIn("up --force-recreate -d rainmapper-worker", start)
        self.assertIn("WORKER_HEALTH_URL", start)
        self.assertIn("needs_dataset", start)
        self.assertNotIn("WORKER_READY_URL", start)
        self.assertIn("stop rainmapper-worker", stop)
        self.assertNotIn("down", stop)
        self.assertNotIn("volume rm", stop)

    def test_worker_start_help_is_available_without_docker(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT_DIR / "mushroom_worker_start.sh"), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--rainmapper-url URL", result.stdout)
        self.assertIn("--token-stdin", result.stdout)
        self.assertIn("Future starts can omit them", result.stdout)
        self.assertIn("http://rainmapper-ha-ui:8100", result.stdout)
        self.assertIn("http://127.0.0.1:8101", result.stdout)

    def test_local_ui_discovers_worker_on_shared_docker_network(self) -> None:
        compose = (ROOT_DIR / "rainmapper-local/docker-compose.yml").read_text(encoding="utf-8")
        start = (ROOT_DIR / "mushroom_lab_start.sh").read_text(encoding="utf-8")
        dockerfile = (ROOT_DIR / "rainmapper-app/Dockerfile").read_text(encoding="utf-8")

        self.assertIn('RAINMAPPER_WORKER_API_ENABLED: "true"', compose)
        self.assertIn('RAINMAPPER_LOCAL_HA_COMPUTE_ENABLED: "true"', compose)
        self.assertIn('RAINMAPPER_MUSHROOM_REBUILD_PIPELINE: "shared"', compose)
        self.assertIn("name: rainmapper-local-compute", compose)
        self.assertIn("docker network create rainmapper-local-compute", start)
        self.assertIn("UI URL for your browser", start)
        self.assertIn("Rainmapper URL for the worker", start)
        self.assertIn("http://rainmapper-ha-ui:8100", start)
        self.assertIn("http://127.0.0.1:8101", start)
        self.assertIn("mushroom_workers_ui.py", dockerfile)


if __name__ == "__main__":
    unittest.main()
