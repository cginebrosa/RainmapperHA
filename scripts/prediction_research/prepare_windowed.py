"""Resume raw input preparation without materializing unused full-365 features."""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

from common import ROOT, OUTPUT, load, digest, verify_inputs, write_new, protect_originals

sys.path.insert(0, str(ROOT))
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_weather_workspace as weather_workspace
from readonly_weather import frozen_weather
from prepare_features import run


def project_windowed(sample):
    include_horizon = str(sample["metadata"]["temporal_contract_id"]).startswith("lag_event_")
    columns = raw.windowed_feature_columns(90, include_horizon=include_horizon)
    # No recalculation. Keep exactly the same values consumed by installed profiles.
    sample["predictive_features"] = {column: sample["predictive_features"][column] for column in columns}
    return sample


def main():
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    manifest = load(OUTPUT / "cohort-v2.json")
    verify_inputs(manifest)
    sources = OUTPUT / "prepared"
    # The first stage completed these four inputs before the memory stop in V5.
    source_files = [sources / f"v{v}-{mode}.json" for v in (3, 4) for mode in ("fixed", "lag")]
    provenance = []
    for path in source_files:
        value = load(path)
        samples = value["samples"]
        if not samples:
            raise ValueError(f"Empty completed source: {path.name}")
        ids = {(r["metadata"].get("source_v3_metadata") or r["metadata"])["observation_id"] for r in samples}
        if ids != {r["observation_id"] for r in manifest["rows"]}:
            raise ValueError(f"Source cohort mismatch: {path.name}")
        provenance.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path), "samples": len(samples)})
        del samples, value
    destination = OUTPUT / "windowed"
    destination.mkdir(exist_ok=False)
    source_manifest = sources / "MANIFEST.json"
    if not source_manifest.exists():
        write_new(source_manifest, {"kind": "isolated_research_completed_sources", "files": provenance})
    original_build = raw.build_v5_sample
    original_contract = raw.feature_set_contract

    def build(*args, **kwargs):
        return project_windowed(original_build(*args, **kwargs))

    def contract(temporal_contract_id):
        value = original_contract(temporal_contract_id)
        value["profiles"] = {key: cols for key, cols in value["profiles"].items() if raw.window_days_from_profile_id(key) is not None}
        value["research_projection"] = "Installed windowed profiles only; physical warm-up remains 365 days"
        return value

    data = ROOT / "docker-data/Data"
    sites = ROOT / "docker-data/mushroom-data/mushroom_known_sites.json"
    stations = ROOT / "docker-data/stations.txt"
    with frozen_weather(data) as generation:
        write_new(destination / "preflight.json", {
            "weather_generation": generation.generation_id,
            "weather_total_rows_upper_bound": sum(p.rows for p in generation.partitions),
            "weather_total_bytes": sum(p.size_bytes for p in generation.partitions),
            "source_files": provenance, "max_samples": len(manifest["rows"]) * 8,
            "retained_predictors_fixed": len(raw.windowed_feature_columns(90, include_horizon=False)),
            "retained_predictors_lag": len(raw.windowed_feature_columns(90, include_horizon=True)),
            "full_365_predictors_lag": len(raw.feature_columns(include_physical=True, include_state=True)) + 1,
            "weather_hashes_verified": True, "physical_lookback_days": 365})
        workspace = weather_workspace.activate_operational_workspace(
            data_dir=data, observations=ROOT / manifest["observations_input"], known_sites=sites, stations_file=stations)
        try:
            with patch.object(raw, "build_v5_sample", build), patch.object(raw, "feature_set_contract", contract):
                run("build-biology-v5-raw-benchmark.py", ["--data-dir", data, "--known-sites", sites,
                    "--stations-file", stations, "--v3-fixed", sources / "v3-fixed.json",
                    "--v3-lag", sources / "v3-lag.json", "--output-dir", destination])
            verify_inputs(manifest)
            write_new(destination / "summary.json", {"workspace": workspace.stats(), "inputs_verified_after": True})
        finally:
            weather_workspace.clear_active_workspace()


if __name__ == "__main__":
    main()
