import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_worker_config


class MushroomWorkerConfigTests(unittest.TestCase):
    def test_config_cli_add_and_check_all_keep_primary_and_tolerate_one_failure(
        self,
    ) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/offline/"):
                    self.send_error(503)
                    return
                if not self.path.endswith("/api/mushrooms/workers/ping"):
                    self.send_error(404)
                    return
                if (
                    self.headers.get("Authorization") != f"Bearer {'s' * 40}"
                    or not self.headers.get("X-Rainmapper-Worker", "").startswith(
                        "worker_"
                    )
                ):
                    self.send_error(403)
                    return
                self._write(
                    {
                        "ok": True,
                        "kind": "rainmapper_worker_coordinator",
                        "auth_required": True,
                        "authenticated": True,
                    }
                )

            def do_POST(self) -> None:  # noqa: N802
                if not self.path.endswith("/api/mushrooms/workers/pair"):
                    self.send_error(404)
                    return
                size = int(self.headers.get("Content-Length", "0"))
                json.loads(self.rfile.read(size))
                self._write({"ok": True, "token": "s" * 40})

            def _write(self, payload: dict[str, object]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                worker_data_dir = Path(temporary)
                base_url = f"http://127.0.0.1:{server.server_port}"
                mushroom_worker_config.save_coordinator_config(
                    worker_data_dir,
                    rainmapper_url=f"{base_url}/offline",
                    token="p" * 40,
                )
                primary_config = (
                    worker_data_dir / "config/coordinator.json"
                ).read_bytes()
                primary_token = (
                    worker_data_dir / "secrets/coordinator-token"
                ).read_bytes()
                script = (
                    Path(__file__).resolve().parents[1]
                    / "scripts/manage-mushroom-worker-config.py"
                )

                added = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--worker-data-dir",
                        str(worker_data_dir),
                        "add",
                        "--rainmapper-url",
                        f"{base_url}/online",
                        "--pairing-code-stdin",
                        "--label",
                        "Local test",
                    ],
                    input="PAIR-CODE\n",
                    check=True,
                    capture_output=True,
                    text=True,
                )
                checked = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--worker-data-dir",
                        str(worker_data_dir),
                        "check-all",
                        "--timeout",
                        "0.5",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                added_payload = json.loads(added.stdout)
                checked_payload = json.loads(checked.stdout)
                self.assertTrue(added_payload["ok"])
                self.assertEqual(added_payload["coordinator"]["label"], "Local test")
                self.assertEqual(checked_payload["reachable_count"], 1)
                self.assertEqual(checked_payload["configured_count"], 2)
                self.assertEqual(
                    (worker_data_dir / "config/coordinator.json").read_bytes(),
                    primary_config,
                )
                self.assertEqual(
                    (worker_data_dir / "secrets/coordinator-token").read_bytes(),
                    primary_token,
                )
        finally:
            server.shutdown()
            server.server_close()

    def test_configuration_and_secret_are_persisted_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            saved = mushroom_worker_config.save_coordinator_config(
                worker_data_dir,
                rainmapper_url="http://rainmapper-ha-ui:8099/",
                token="secret-token",
            )
            loaded = mushroom_worker_config.load_coordinator_config(worker_data_dir, include_token=True)
            public_payload = json.loads(
                (worker_data_dir / "config/coordinator.json").read_text(encoding="utf-8")
            )

        self.assertEqual(saved["rainmapper_url"], "http://rainmapper-ha-ui:8099")
        self.assertTrue(saved["has_token"])
        self.assertEqual(loaded["token"], "secret-token")
        self.assertNotIn("token", public_payload)

    def test_invalid_url_does_not_write_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            with self.assertRaisesRegex(ValueError, "http"):
                mushroom_worker_config.save_coordinator_config(
                    worker_data_dir,
                    rainmapper_url="homeassistant.local",
                )
            self.assertFalse((worker_data_dir / "config/coordinator.json").exists())

    def test_token_can_be_cleared_without_contacting_the_coordinator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            mushroom_worker_config.save_coordinator_config(
                worker_data_dir,
                rainmapper_url="https://homeassistant.example",
                token="secret-token",
            )

            removed = mushroom_worker_config.clear_coordinator_token(worker_data_dir)
            loaded = mushroom_worker_config.load_coordinator_config(
                worker_data_dir,
                include_token=True,
            )

        self.assertTrue(removed)
        self.assertFalse(loaded["has_token"])
        self.assertEqual(loaded["token"], "")
        self.assertEqual(loaded["rainmapper_url"], "https://homeassistant.example")

    def test_additional_coordinators_do_not_rewrite_primary_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            mushroom_worker_config.save_coordinator_config(
                worker_data_dir,
                rainmapper_url="https://real-ha.example",
                token="r" * 40,
            )
            primary_config = (worker_data_dir / "config/coordinator.json").read_bytes()
            primary_token = (worker_data_dir / "secrets/coordinator-token").read_bytes()

            added = mushroom_worker_config.add_coordinator(
                worker_data_dir,
                rainmapper_url="http://rainmapper-ha-ui:8100/",
                token="l" * 40,
                label="Local laboratory",
            )
            loaded = mushroom_worker_config.load_coordinators(
                worker_data_dir, include_tokens=True
            )
            public = json.loads(
                (worker_data_dir / "config/additional-coordinators.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(primary_config, b'{\n  "schema_version": "0.1",\n  "rainmapper_url": "https://real-ha.example"\n}\n')
        self.assertEqual(primary_token, b"r" * 40 + b"\n")
        self.assertEqual(
            [row["rainmapper_url"] for row in loaded["coordinators"]],
            ["https://real-ha.example", "http://rainmapper-ha-ui:8100"],
        )
        self.assertEqual(loaded["coordinators"][0]["token"], "r" * 40)
        self.assertEqual(loaded["coordinators"][1]["token"], "l" * 40)
        self.assertEqual(added["label"], "Local laboratory")
        self.assertNotIn("token", public["coordinators"][0])

    def test_multicoordinator_limit_is_configurable_and_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            mushroom_worker_config.save_coordinator_config(
                worker_data_dir,
                rainmapper_url="https://real-ha.example",
                token="r" * 40,
            )
            first = mushroom_worker_config.add_coordinator(
                worker_data_dir,
                rainmapper_url="https://lab-one.example",
                token="a" * 40,
            )
            mushroom_worker_config.add_coordinator(
                worker_data_dir,
                rainmapper_url="https://lab-two.example",
                token="b" * 40,
            )
            with self.assertRaisesRegex(ValueError, "below"):
                mushroom_worker_config.set_max_coordinators(worker_data_dir, 2)
            self.assertEqual(
                mushroom_worker_config.load_coordinators(worker_data_dir)[
                    "max_coordinators"
                ],
                4,
            )
            self.assertTrue(
                mushroom_worker_config.forget_coordinator(
                    worker_data_dir, str(first["coordinator_id"])
                )
            )
            with self.assertRaisesRegex(ValueError, "primary"):
                mushroom_worker_config.forget_coordinator(worker_data_dir, "primary")
            self.assertEqual(
                len(
                    mushroom_worker_config.load_coordinators(worker_data_dir)[
                        "coordinators"
                    ]
                ),
                2,
            )

    def test_up_to_configured_number_of_coordinators_can_be_added(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            mushroom_worker_config.set_max_coordinators(worker_data_dir, 3)
            for index in range(3):
                mushroom_worker_config.add_coordinator(
                    worker_data_dir,
                    rainmapper_url=f"https://coordinator-{index}.example",
                    token=str(index) * 40,
                )
            with self.assertRaisesRegex(ValueError, "limit reached"):
                mushroom_worker_config.add_coordinator(
                    worker_data_dir,
                    rainmapper_url="https://coordinator-extra.example",
                    token="x" * 40,
                )

            loaded = mushroom_worker_config.load_coordinators(worker_data_dir)

        self.assertEqual(len(loaded["coordinators"]), 3)
        self.assertEqual(loaded["max_coordinators"], 3)

    def test_probe_requires_compatible_coordinator_response(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok": true, "kind": "rainmapper_worker_coordinator", "schema_version": "0.1"}'
        with mock.patch.object(mushroom_worker_config, "urlopen", return_value=response) as urlopen:
            result = mushroom_worker_config.probe_coordinator(
                "https://homeassistant.example/",
                token="secret-token",
                worker_id="worker_12345678",
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(result["schema_version"], "0.1")
        self.assertEqual(request.full_url, "https://homeassistant.example/api/mushrooms/workers/ping")
        self.assertEqual(request.headers["Authorization"], "Bearer secret-token")
        self.assertEqual(request.headers["X-rainmapper-worker"], "worker_12345678")

    def test_pairing_exchanges_temporary_code_without_putting_it_in_url(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok": true, "token": "abcdefghijklmnopqrstuvwxyz1234567890"}'
        identity = {
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "MacBook Pro",
        }
        with mock.patch.object(mushroom_worker_config, "urlopen", return_value=response) as urlopen:
            result = mushroom_worker_config.pair_coordinator(
                "https://homeassistant.example",
                pairing_code="abcd-1234",
                identity=identity,
                timeout=1,
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://homeassistant.example/api/mushrooms/workers/pair")
        self.assertNotIn("ABCD-1234", request.full_url)
        self.assertEqual(json.loads(request.data)["pairing_code"], "ABCD-1234")
        self.assertEqual(result["token"], "abcdefghijklmnopqrstuvwxyz1234567890")

    def test_probe_explains_when_pairing_is_required(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = (
            b'{"ok": true, "kind": "rainmapper_worker_coordinator", '
            b'"auth_required": true, "authenticated": false}'
        )
        with mock.patch.object(mushroom_worker_config, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "requires pairing"):
                mushroom_worker_config.probe_coordinator("https://homeassistant.example")


if __name__ == "__main__":
    unittest.main()
