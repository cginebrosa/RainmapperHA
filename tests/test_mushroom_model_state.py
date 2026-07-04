import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rainmapper_core import mushroom_model_state


class MushroomModelStateTests(unittest.TestCase):
    def test_mark_and_clear_species_pending_uses_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "mushroom_model_v0_state.json"
            with patch.dict("os.environ", {"RAINMAPPER_MUSHROOM_MODEL_STATE_PATH": str(state_path)}, clear=False):
                marked = mushroom_model_state.mark_species_pending(["boletus_pinophilus", "boletus_edulis"])

                self.assertTrue(state_path.exists())
                self.assertEqual(
                    marked["pending_rebuild_species_ids"],
                    ["boletus_edulis", "boletus_pinophilus"],
                )

                cleared = mushroom_model_state.clear_species_pending(["boletus_edulis"])

                self.assertEqual(cleared["pending_rebuild_species_ids"], ["boletus_pinophilus"])
                self.assertTrue(cleared["last_partial_rebuild_at"])


if __name__ == "__main__":
    unittest.main()
