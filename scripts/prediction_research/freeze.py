"""Freeze metadata and temporal membership before inspecting model performance."""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
from datetime import date, timedelta
import json
import subprocess
import sys

from common import ROOT, OUTPUT, TARGETS, digest, load, write_new

sys.path.insert(0, str(ROOT))
from rainmapper_core import mushroom_ml_biology_v3 as biology
from rainmapper_core import mushroom_ml_model_catalog as catalog


def episode_groups(rows):
    """Connected visits within 14 days in an area, including different species."""
    areas = defaultdict(list)
    for row in rows:
        areas[row["area_id"]].append(row)
    groups = {}
    for area, members in sorted(areas.items()):
        previous = None
        first = None
        for row in sorted(members, key=lambda r: (r["date"], r["observation_id"])):
            day = date.fromisoformat(row["date"])
            if previous is None or (day - previous).days > 14:
                first = row["date"]
            groups[row["observation_id"]] = f"{area}|{first}"
            previous = day
    return groups


def memberships(rows, year):
    """All-species date boundaries, with purge and whole-episode exclusion."""
    boundaries = [date(year - 2, 1, 1), date(year - 1, 1, 1), date(year, 1, 1), date(year + 1, 1, 1)]
    by_group = defaultdict(list)
    for row in rows:
        by_group[row["episode_id"]].append(date.fromisoformat(row["date"]))
    excluded = set()
    for group, dates in by_group.items():
        for boundary in boundaries:
            if (min(dates) < boundary <= max(dates)
                    or any(abs((day - boundary).days) <= 14 for day in dates)):
                excluded.add(group)
    result = {}
    for row in rows:
        day = date.fromisoformat(row["date"])
        if row["episode_id"] in excluded:
            part = "purged"
        elif day < boundaries[0]:
            part = "fit"
        elif day < boundaries[1]:
            part = "ranking"
        elif day < boundaries[2]:
            part = "threshold"
        elif day < date(year + 1, 1, 1):
            part = "external"
        else:
            part = "future"
        result[row["observation_id"]] = part
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="v2")
    args = parser.parse_args()
    if not args.revision.isalnum():
        parser.error("revision must be alphanumeric")
    subprocess.run(["git", "check-ignore", "tmp/prediction-research/probe.json"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    base = ROOT / "docker-data/mushroom-data"
    batch = ROOT / "docker-media/rainmapper/results/models/batches/operational_20260928T005344Z"
    obs = load(base / "mushroom_observations.json")["observations"]
    sites = load(base / "mushroom_known_sites.json")
    registry = load(base / "mushroom_ml_version_registry.json")
    production = load(batch / "manifest.json")
    # Freeze the installed design's species universe; never inspect its scores.
    shared_species = sorted(production["species_ids"])
    installed = [v["version_id"] for v in registry["versions"] if v.get("installed_generation_id")]
    profiles = [p for p in catalog.catalog_entries(registry) if p["version_id"] in installed]
    area_by_site = {s["micro_area_id"]: s["area_id"] for s in sites["micro_areas"]}
    rows, excluded = [], Counter()
    for observation in obs:
        if observation["species_id"] not in shared_species:
            excluded["outside_frozen_shared_species"] += 1
            continue
        target = biology.resolve_observation_target(observation)
        if target not in ("favorable", "unfavorable"):
            excluded["not_canonical_eligible_target"] += 1
            continue
        area = area_by_site.get(observation.get("micro_area_id"))
        if not area:
            excluded["missing_area"] += 1
            continue
        day = date.fromisoformat(str(observation["observed_at"])[:10])
        location = observation.get("location") or {}
        rows.append({"observation_id": observation["observation_id"],
                     "species_id": observation["species_id"], "area_id": area,
                     "micro_area_id": observation["micro_area_id"], "date": day.isoformat(),
                     "y": int(target == "favorable"),
                     "has_observation_point": all(isinstance(location.get(k), (int, float)) for k in ("lat", "lon"))})
    if len({r["observation_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate observation identity")
    groups = episode_groups(rows)
    for row in rows:
        row["episode_id"] = groups[row["observation_id"]]
    folds = {str(year): memberships(rows, year) for year in (2024, 2025, 2026)}
    counts = {}
    for year, members in folds.items():
        counts[year] = {}
        for species in TARGETS:
            counts[year][species] = {}
            for part in ("fit", "ranking", "threshold", "external", "purged"):
                subset = [r for r in rows if r["species_id"] == species and members[r["observation_id"]] == part]
                counts[year][species][part] = {
                    "n": len(subset), "favorable": sum(r["y"] for r in subset),
                    "unfavorable": sum(1-r["y"] for r in subset),
                    "episodes": len({r["episode_id"] for r in subset}),
                    "missing_point": sum(not r["has_observation_point"] for r in subset)}
    paths = [base / name for name in ("mushroom_observations.json", "mushroom_known_sites.json",
              "mushroom_reference_catalogs.json", "mushroom_ml_version_registry.json",
              "mushroom_ml_prediction_policy.json", "mushroom_profiles.json", "mushroom_gis_mappings.json")]
    paths += [ROOT / "docker-data/stations.txt", batch / "manifest.json",
              ROOT / "docker-media/rainmapper/results/artifacts/mushroom_observation_features_v0.json",
              ROOT / "docker-data/Data/weather-history/CURRENT.json"]
    weather = load(paths[-1])
    weather_manifest = ROOT / "docker-data/Data/weather-history" / weather["manifest_path"]
    paths.append(weather_manifest)
    paths += sorted((ROOT / "rainmapper_core").glob("*.py"))
    paths += [ROOT / "scripts" / name for name in ("build-biology-v3-benchmark.py",
              "build-biology-v4-benchmark.py", "build-biology-v5-raw-benchmark.py",
              "evaluate-biology-v6-smooth-hierarchical.py", "prediction-map-local-geography.py")]
    # Freeze small GIS publication metadata, never duplicate/hash large rasters here.
    geography = ROOT / "docker-media/rainmapper/geography"
    pointer = load(geography / "CURRENT.json")
    generation_path = geography / "generations" / pointer["generation"]
    paths += [geography / "CURRENT.json", generation_path / "manifest.json"]
    from rainmapper_core.mushroom_map_geography_runtime import published_geography_config
    geo_config = published_geography_config(geography)
    if geo_config.get("geography_sources"):
        from pathlib import Path
        paths.append(Path(geo_config["geography_sources"]))
    admitted = {r["observation_id"] for r in rows}
    observations_path = OUTPUT / f"observations-input-{args.revision}.json"
    input_payload = {"observations": [r for r in obs if r["observation_id"] in admitted]}
    if observations_path.exists():
        if load(observations_path) != input_payload:
            raise ValueError("Existing private observation snapshot differs")
    else:
        write_new(observations_path, input_payload)
    paths.append(observations_path)
    inputs = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]
    manifest = {"schema": 1, "kind": "prediction_research_frozen_cohort", "inputs": inputs,
                "targets": TARGETS, "shared_species": shared_species, "profiles": profiles,
                "rows": rows, "folds": folds, "counts": counts, "exclusions": dict(excluded),
                "revision": args.revision, "observations_input": str(observations_path.relative_to(ROOT)),
                "geography_config": geo_config,
                "grouping": "area, all species, consecutive gaps <=14 days; whole group purge near January boundaries",
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    write_new(OUTPUT / f"cohort-{args.revision}.json", manifest)
    print(json.dumps({"rows": len(rows), "exclusions": excluded, "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
