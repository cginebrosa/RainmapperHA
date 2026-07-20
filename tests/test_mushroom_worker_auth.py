import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_worker_auth


class MushroomWorkerAuthTests(unittest.TestCase):
    def test_issue_persists_only_hash_and_authenticates_exact_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "credentials.json"
            token = "a" * 32
            issued = mushroom_worker_auth.issue_credential(
                path,
                worker_id="worker_12345678",
                token=token,
                paired_at="2026-07-19T12:00:00+00:00",
            )
            stored_text = path.read_text(encoding="utf-8")
            stored = json.loads(stored_text)
            accepted = mushroom_worker_auth.authenticate(
                path,
                worker_id="worker_12345678",
                token=token,
            )
            wrong_worker = mushroom_worker_auth.authenticate(
                path,
                worker_id="worker_abcdefgh",
                token=token,
            )

        self.assertEqual(issued, token)
        self.assertTrue(accepted)
        self.assertFalse(wrong_worker)
        self.assertNotIn(token, stored_text)
        self.assertEqual(len(stored["workers"][0]["token_hash"]), 64)

    def test_pairing_again_rotates_token_and_revoke_disables_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "credentials.json"
            mushroom_worker_auth.issue_credential(
                path,
                worker_id="worker_12345678",
                token="a" * 32,
            )
            mushroom_worker_auth.issue_credential(
                path,
                worker_id="worker_12345678",
                token="b" * 32,
            )
            old_accepted = mushroom_worker_auth.authenticate(
                path,
                worker_id="worker_12345678",
                token="a" * 32,
            )
            new_accepted = mushroom_worker_auth.authenticate(
                path,
                worker_id="worker_12345678",
                token="b" * 32,
            )
            revoked = mushroom_worker_auth.revoke_credential(path, worker_id="worker_12345678")
            after_revoke = mushroom_worker_auth.authenticate(
                path,
                worker_id="worker_12345678",
                token="b" * 32,
            )

        self.assertFalse(old_accepted)
        self.assertTrue(new_accepted)
        self.assertTrue(revoked)
        self.assertFalse(after_revoke)


if __name__ == "__main__":
    unittest.main()
