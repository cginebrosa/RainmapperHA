"""Read the full map's geography adapter at evaluation observation points."""
from __future__ import annotations

import io
import json
import os
import runpy
import sys
from collections import Counter

from common import ROOT, OUTPUT, TARGETS, load, verify_inputs, write_new, protect_originals


def main():
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py using the existing GDAL Python")
    protect_originals()
    manifest = load(OUTPUT / "cohort-v2.json")
    verify_inputs(manifest)
    observations = {r["observation_id"]: r for r in load(ROOT / manifest["observations_input"])["observations"]}
    cases = [r for r in manifest["rows"] if r["species_id"] in TARGETS and any(
        membership[r["observation_id"]] in {"threshold", "external"} for membership in manifest["folds"].values())]
    requests = [{"id": "capabilities", "op": "capabilities"}]
    for row in cases:
        observation = observations[row["observation_id"]]
        location = observation["location"]
        requests.append({"id": row["observation_id"], "lat": location["lat"], "lon": location["lon"],
                         "start_date": row["date"], "horizon_days": 7, "model_inputs": True,
                         "water_history": False, "species_ids": list(TARGETS)})
    config = dict(manifest["geography_config"])
    base = ROOT / "docker-data/mushroom-data"
    config.update(profiles=str(base / "mushroom_profiles.json"),
                  ecology_catalogs=str(base / "mushroom_reference_catalogs.json"),
                  forest_catalogs=str(base / "mushroom_reference_catalogs.json"),
                  gis_mappings=str(base / "mushroom_gis_mappings.json"))
    keys = ("municipalities", "municipalities_edition", "terrain_index", "soil_root", "dem_root",
            "regional_root", "mvc50_index", "land_cover", "geology", "land_cover_parts", "geology_parts",
            "forest_index", "forest_catalogs", "profiles", "ecology_catalogs", "gis_mappings",
            "openlandmap_ph", "geography_sources", "ecology_ph_source")
    script = ROOT / "scripts/prediction-map-local-geography.py"
    argv = [str(script)]
    for key in keys:
        if config.get(key):
            argv.extend(["--" + key.replace("_", "-"), str(config[key])])
    output_path = OUTPUT / "geography.jsonl"
    write_new(OUTPUT / "geography-preflight.json", {"observation_points": len(cases),
              "requests": len(requests), "generation_metadata_frozen": True,
              "adapter": str(script.relative_to(ROOT)), "python": sys.executable})
    saved = sys.argv, sys.stdin, sys.stdout
    try:
        sys.argv = argv
        sys.stdin = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
        with output_path.open("x") as stream:
            sys.stdout = stream
            runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv, sys.stdin, sys.stdout = saved
    rows = [json.loads(line) for line in output_path.read_text().splitlines()]
    if rows[0].get("geography_ready") is not True:
        raise ValueError("Geography adapter initialization incomplete; inspect private log")
    if {r["id"] for r in rows[1:]} != {r["observation_id"] for r in cases}:
        raise ValueError("Missing geography observations")
    verify_inputs(manifest)
    summary = {"points": len(cases), "geography_ready": True,
               "ecology_statuses": dict(Counter(r.get("ecology", {}).get("status") for r in rows[1:])),
               "with_native_soil_context": sum(bool(r.get("model_soil_water")) for r in rows[1:]),
               "inputs_verified_after": True}
    write_new(OUTPUT / "geography-summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
