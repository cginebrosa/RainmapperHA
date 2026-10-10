"""Materialize installed training profiles and retain only model/audit fields."""
from __future__ import annotations

from collections import Counter, defaultdict
import gc
import json
import os
import sys

from common import ROOT, OUTPUT, TARGETS, load, verify_inputs, write_new, digest, protect_originals

sys.path.insert(0, str(ROOT))
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_holdout as holdout


def main():
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    cohort = load(OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    if not (OUTPUT / "windowed/summary.json").is_file():
        raise SystemExit("Windowed feature preparation did not complete")
    destination = OUTPUT / "benchmarks"
    destination.mkdir(exist_ok=False)
    files = {f"v{version}_{temporal}": OUTPUT / "prepared" / f"v{version}-{temporal}.json"
             for version in (3, 4) for temporal in ("fixed", "lag")}
    files.update({f"v5_{temporal}": OUTPUT / "windowed" / f"biology-v5-{temporal}.json"
                  for temporal in ("fixed", "lag")})
    payloads = {name: load(path) for name, path in files.items()}
    benchmarks = trainer.materialize_runtime_benchmarks(**payloads)
    allowed = {(p["version_id"], p["profile_id"]) for p in cohort["profiles"]}
    metadata_keys = ("observation_id", "species_id", "area_id", "micro_area_id", "target_date",
                     "cutoff_date", "horizon_days", "temporal_contract_id", "feature_set_id",
                     "validation_group_7d", "validation_group_14d", "water_state_contract_id")
    source_rows = {r["observation_id"]: r for r in cohort["rows"]}
    counts, entries = {}, []
    for key, benchmark in benchmarks.items():
        version, contract, profile = key.split("|")
        if (version, profile) not in allowed:
            continue
        compact = {name: value for name, value in benchmark.items() if name not in ("samples", "source")}
        # Matched profile materializers have already applied their actual gates.
        eligible_ids = {s["sample_id"] for s in holdout.eligible_samples(benchmark)}
        samples = []
        by_species = defaultdict(Counter)
        for sample in benchmark["samples"]:
            metadata = sample["metadata"]
            identity = metadata["observation_id"]
            if identity not in source_rows:
                raise ValueError("Benchmark observation escaped frozen cohort")
            row = source_rows[identity]
            if metadata["species_id"] != row["species_id"] or metadata["target_date"] != row["date"]:
                raise ValueError("Materialized sample identity changed")
            sample_y = int(sample["prediction_target"] == "favorable")
            if sample_y != row["y"]:
                raise ValueError("Canonical target changed during feature preparation")
            reduced_metadata = {k: metadata[k] for k in metadata_keys if k in metadata}
            # Retain original inner-split grouping and the frozen outer grouping separately.
            reduced_metadata["research_episode_id"] = row["episode_id"]
            samples.append({"sample_id": sample["sample_id"], "prediction_target": sample["prediction_target"],
                            "predictive_features": sample["predictive_features"],
                            "quality": sample["quality"], "metadata": reduced_metadata})
            if sample["sample_id"] in eligible_ids:
                by_species[row["species_id"]]["eligible_rows"] += 1
                by_species[row["species_id"]]["favorable" if row["y"] else "unfavorable"] += 1
            else:
                by_species[row["species_id"]]["excluded_rows"] += 1
        compact["samples"] = samples
        compact["research_source_key"] = key
        filename = f"{version}--{contract}--{profile}.json"
        path = destination / filename
        write_new(path, compact)
        # Check the compact representation preserves the actual eligibility decision.
        if eligible_ids != {s["sample_id"] for s in holdout.eligible_samples(compact)}:
            raise ValueError("Compaction changed training eligibility")
        entries.append({"key": key, "path": str(path.relative_to(ROOT)), "sha256": digest(path),
                        "samples": len(samples), "eligible_samples": len(eligible_ids)})
        counts[key] = {s: dict(by_species[s]) for s in TARGETS}
        print(json.dumps({"profile": key, "samples": len(samples), "eligible": len(eligible_ids)}), flush=True)
    del benchmarks, payloads
    gc.collect()
    verify_inputs(cohort)
    write_new(destination / "manifest.json", {"cohort_sha256": digest(OUTPUT / "cohort-v2.json"),
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in files.values()],
        "benchmarks": entries, "target_coverage": counts, "inputs_verified_after": True})


if __name__ == "__main__":
    main()
