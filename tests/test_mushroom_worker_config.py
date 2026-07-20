import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_worker_config


class MushroomWorkerConfigTests(unittest.TestCase):
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
