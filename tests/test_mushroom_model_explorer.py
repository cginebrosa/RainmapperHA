import tempfile
import threading
import unittest
from collections import OrderedDict
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.request import urlopen

import numpy as np

from rainmapper_core import mushroom_model_explorer
from rainmapper_core import mushroom_worker_service


class _LinearModel:
    coef_ = np.asarray([[0.25, -1.5]], dtype=float)


class _TreeModel:
    feature_importances_ = np.asarray([0.2, 0.8], dtype=float)


class _Pipeline:
    def __init__(self, classifier: object) -> None:
        self.named_steps = OrderedDict(
            (("imputer", object()), ("classifier", classifier))
        )


def _bundle(model: object) -> dict[str, object]:
    return {
        "model": model,
        "feature_cols": ["rain_cutoff_7d_mm", "temp_max_cutoff_7d_c"],
        "feature_support": {
            "rain_cutoff_7d_mm": {"min": 0, "mean": 12, "max": 70, "std": 8},
            "temp_max_cutoff_7d_c": {"min": 4, "mean": 18, "max": 33, "std": 5},
        },
        "training_row_count": 42,
        "training_species_ids": ["lactarius_deliciosus"],
        "fit_config": {},
        "artifact_ref": {
            "estimator_id": "logistic_regression_reduced_v1",
        },
    }


def _catalog(root: Path) -> mushroom_model_explorer.RuntimeCatalog:
    ref = {
        "batch_id": "batch_1",
        "generation_id": "generation_1",
        "version_id": "biology_v3",
        "temporal_contract_id": "lag_event_biology_v3",
        "profile_id": "common_idw_plus_physical_state",
        "estimator_id": "logistic_regression_reduced_v1",
        "species_id": "lactarius_deliciosus",
    }
    row = {
        "key": "/".join(ref.values()),
        "artifact_ref": ref,
        "supported_horizons": [1, 2, 3, 4, 5, 6, 7],
        "path": "unused.joblib",
        "sha256": "0" * 64,
    }
    runtime = mushroom_model_explorer.RuntimeChoice("shared", "Runtime compartido", root)
    return mushroom_model_explorer.RuntimeCatalog(
        runtime=runtime,
        registry={},
        rows=(row,),
        manifests={"batch_1": {}},
        species_names={"lactarius_deliciosus": "Rovelló — Lactarius deliciosus"},
    )


class MushroomModelExplorerTests(unittest.TestCase):
    def test_linear_summary_maps_exact_signed_coefficients(self) -> None:
        result = mushroom_model_explorer.summarize_bundle(
            _bundle(_Pipeline(_LinearModel()))
        )

        self.assertEqual(result["measure"], "coeficiente")
        self.assertEqual(result["training_row_count"], 42)
        self.assertEqual(
            [row["feature"] for row in result["weights"]],
            ["temp_max_cutoff_7d_c", "rain_cutoff_7d_mm"],
        )
        self.assertEqual(result["weights"][0]["direction"], "baja")
        self.assertEqual(result["weights"][1]["direction"], "sube")
        self.assertEqual(result["support"][0]["kind"], "precipitación")

    def test_tree_summary_does_not_invent_direction(self) -> None:
        result = mushroom_model_explorer.summarize_bundle(
            _bundle(_Pipeline(_TreeModel()))
        )

        self.assertEqual(result["measure"], "importancia")
        self.assertTrue(
            all(row["direction"] == "sin dirección" for row in result["weights"])
        )

    def test_mismatched_coefficients_are_not_assigned_to_features(self) -> None:
        bundle = _bundle(_LinearModel())
        bundle["feature_cols"] = ["rain_cutoff_7d_mm"]

        result = mushroom_model_explorer.summarize_bundle(bundle)

        self.assertEqual(result["weights"], [])
        self.assertIn("no coincide", result["explanation"])

    def test_page_does_not_load_artifact_until_inspection_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = _catalog(Path(temporary))
            with (
                mock.patch.object(
                    mushroom_model_explorer,
                    "discover_runtimes",
                    return_value=[catalog.runtime],
                ),
                mock.patch.object(
                    mushroom_model_explorer,
                    "load_runtime_catalog",
                    return_value=catalog,
                ),
                mock.patch.object(
                    mushroom_model_explorer, "inspect_catalog_row"
                ) as inspect,
            ):
                page = mushroom_model_explorer.render_page(
                    Path(temporary), "/models"
                )

        self.assertIn("Rovelló", page)
        inspect.assert_not_called()

    def test_page_loads_only_selected_artifact_after_explicit_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = _catalog(Path(temporary))
            summary = mushroom_model_explorer.summarize_bundle(
                _bundle(_Pipeline(_LinearModel()))
            )
            with (
                mock.patch.object(
                    mushroom_model_explorer,
                    "discover_runtimes",
                    return_value=[catalog.runtime],
                ),
                mock.patch.object(
                    mushroom_model_explorer,
                    "load_runtime_catalog",
                    return_value=catalog,
                ),
                mock.patch.object(
                    mushroom_model_explorer,
                    "inspect_catalog_row",
                    return_value=summary,
                ) as inspect,
            ):
                page = mushroom_model_explorer.render_page(
                    Path(temporary), "/models?inspect=1"
                )

        inspect.assert_called_once()
        self.assertIn("Variables aprendidas (2)", page)
        self.assertIn("temp_max_cutoff_7d_c", page)

    def test_inspection_uses_verified_loader_without_shared_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = _catalog(Path(temporary))
            row = catalog.rows[0]
            with mock.patch.object(
                mushroom_model_explorer.runtime_inference,
                "load_exact_artifact",
                return_value=_bundle(_LinearModel()),
            ) as load:
                mushroom_model_explorer.inspect_catalog_row(catalog, row)

        self.assertFalse(load.call_args.kwargs["cache"])
        self.assertIs(load.call_args.kwargs["artifact_row"], row)

    def test_worker_mounts_explorer_at_models_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            handler = mushroom_worker_service._handler_class(
                Path(temporary),
                "test",
                {"worker_id": "worker_test", "display_name": "Test", "host_name": "host"},
                {
                    "foreground": {"status": "idle"},
                    "background": {"status": "idle"},
                },
                threading.Lock(),
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/models", timeout=2
                ) as response:
                    body = response.read().decode("utf-8")
                    content_type = response.headers["Content-Type"]
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("Explorador de modelos", body)
        self.assertIn("No hay un runtime activo", body)


if __name__ == "__main__":
    unittest.main()
