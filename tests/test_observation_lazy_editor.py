"""Request lifetime, lazy editing and maintenance-listener regressions."""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from tests.test_web_server_auth import load_web_server_module


class ObservationLazyEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = load_web_server_module()
        cls.ui = cls.web.mushroom_profiles_ui

    def test_page_shares_one_read_but_next_page_sees_new_sites(self):
        rows = [{"observation_id": f"obs_{i}", "observed_at": "2026-10-01"} for i in range(25)]
        with patch.object(self.ui.mushroom_known_sites, "load_payload", return_value={}) as load:
            first = self.ui.render_observations_section(None, [], {}, {"observations": rows}, {})
            self.assertEqual(load.call_count, 1)
            self.assertEqual(first.count('data-observation-editor="'), 25)
            self.assertNotIn('value="update_observation"', first)
            load.return_value = {"areas": [{"area_id": "new", "name": "New site"}],
                                 "micro_areas": [{"micro_area_id": "micro", "area_id": "new", "name": "New micro"}]}
            second = self.ui.render_observations_section(None, [], {}, {"observations": rows}, {})
            self.assertEqual(load.call_count, 2)
            self.assertIn("New site", second)

    def test_snapshot_isolated_between_threads_and_reset_after_error(self):
        barrier = threading.Barrier(2)
        def load():
            return {"thread": threading.get_ident()}
        @self.ui.with_known_sites_snapshot
        def render():
            first = self.ui.known_sites_payload()
            barrier.wait(timeout=3)
            self.assertIs(first, self.ui.known_sites_payload())
            self.assertEqual(first["thread"], threading.get_ident())
        with patch.object(self.ui.mushroom_known_sites, "load_payload", side_effect=load) as loader:
            with ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(render) for _ in range(2)]
                for future in futures:
                    future.result()
            self.assertEqual(loader.call_count, 2)
        @self.ui.with_known_sites_snapshot
        def broken():
            self.ui.known_sites_payload()
            raise RuntimeError("fixture")
        with patch.object(self.ui.mushroom_known_sites, "load_payload", side_effect=[{"old": True}, {"new": True}]):
            with self.assertRaises(RuntimeError):
                broken()
            self.assertEqual(self.ui.known_sites_payload(), {"new": True})

    def test_editor_endpoint_preserves_context_and_only_renders_requested_row(self):
        handler = self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.send_json = Mock()
        store = Mock()
        store.load.side_effect = lambda kind: {
            "profiles": {"species_profiles": []}, "catalogs": {"catalogs": {}},
            "observations": {"observations": [{"observation_id": "one", "observed_at": "2026-10-01"},
                                                 {"observation_id": "two"}]},
        }[kind]
        with patch.object(self.web, "default_store", return_value=store), \
             patch.object(self.web, "load_archived_observations") as archive, \
             patch.object(self.ui.mushroom_known_sites, "load_payload", return_value={}):
            handler.serve_mushroom_observation_detail({"obs_id": ["one"], "page": ["3"],
                "page_size": ["25"], "obs_species": ["__all__"], "obs_q": ["<pine>"],
                "sort": ["observed_at"], "dir": ["asc"]}, editor=True)
            status, payload = handler.send_json.call_args.args
            self.assertEqual(status, 200)
            self.assertIn('id="edit-observation-one"', payload["html"])
            self.assertNotIn('id="edit-observation-two"', payload["html"])
            self.assertIn('name="return_page" value="3"', payload["html"])
            self.assertIn('&lt;pine&gt;', payload["html"])
            self.assertIn('name="observation_exif_images"', payload["html"])
            self.assertIn('data-observation-gis-recover', payload["html"])
            self.assertIn('data-observation-draft-map', payload["html"])
            archive.assert_not_called()
            for query, expected in (({}, 400), ({"obs_id": ["missing"]}, 404)):
                handler.serve_mushroom_observation_detail(query, editor=True)
                self.assertEqual(handler.send_json.call_args.args[0], expected)

    def test_editor_route_obeys_maintenance_listener_boundary(self):
        handler = self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.path = "/api/mushrooms/observation-editor?obs_id=one"
        handler.send_json = Mock()
        handler.serve_mushroom_observation_detail = Mock()
        with patch.object(handler, "listener_role", return_value="worker"):
            handler.do_GET()
            self.assertEqual(handler.send_json.call_args.args[0], 404)
            handler.serve_mushroom_observation_detail.assert_not_called()
        with patch.object(handler, "listener_role", return_value="backend"):
            handler.do_GET()
            handler.serve_mushroom_observation_detail.assert_called_once_with({"obs_id": ["one"]}, editor=True)
