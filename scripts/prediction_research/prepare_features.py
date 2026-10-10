"""Build experimental training features using unchanged, read-only-input builders.

No jobs, model fitting, production output destinations, or candidate scores.
"""
from __future__ import annotations

import json
import os
import runpy
import sys

from common import ROOT, OUTPUT, load, verify_inputs, write_new, protect_originals

sys.path.insert(0, str(ROOT))
from rainmapper_core import mushroom_ml_weather_workspace as weather_workspace
from readonly_weather import frozen_weather


def run(name, arguments):
    path = ROOT / "scripts" / name
    print(json.dumps({"builder": name, "status": "starting"}), flush=True)
    previous = sys.argv
    try:
        sys.argv = [str(path), *map(str, arguments)]
        try:
            runpy.run_path(str(path), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (0, None):
                raise
    finally:
        sys.argv = previous


def main():
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    manifest = load(OUTPUT / "cohort-v2.json")
    verify_inputs(manifest)
    destination = OUTPUT / "prepared"
    destination.mkdir(exist_ok=False)
    data = ROOT / "docker-data/Data"
    sites = ROOT / "docker-data/mushroom-data/mushroom_known_sites.json"
    stations = ROOT / "docker-data/stations.txt"
    observations = ROOT / manifest["observations_input"]
    weather_context = frozen_weather(data)
    weather_context.__enter__()
    workspace = weather_workspace.activate_operational_workspace(
        data_dir=data, observations=observations, known_sites=sites, stations_file=stations)
    common = ["--data-dir", data, "--known-sites", sites, "--stations-file", stations]
    try:
        for temporal, contract in (("fixed", "fixed_gap_7d_biology_v3"), ("lag", "lag_event_biology_v3")):
            run("build-biology-v3-benchmark.py", [*common, "--observations", observations,
                 "--observation-features", ROOT / "docker-media/rainmapper/results/artifacts/mushroom_observation_features_v0.json",
                 "--feature-set", contract, "--output", destination / f"v3-{temporal}.json"])
        for temporal in ("fixed", "lag"):
            run("build-biology-v4-benchmark.py", [*common,
                 "--v3-benchmark", destination / f"v3-{temporal}.json", "--output", destination / f"v4-{temporal}.json"])
        verify_inputs(manifest)
        write_new(destination / "summary.json", {"workspace": workspace.stats(), "inputs_verified_after": True})
    finally:
        weather_workspace.clear_active_workspace()
        weather_context.__exit__(None, None, None)


if __name__ == "__main__":
    main()
