"""Reference-driven retention for multiversion model candidates and batches."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_benchmark_reports
from rainmapper_core import mushroom_ml_version_registry


def _size(path: Path) -> int:
    if path.is_symlink() or not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(_size(child) for child in path.iterdir())


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return payload


def _generation(version: dict[str, Any], generation_id: object) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in version.get("generations", [])
            if row.get("generation_id") == generation_id
        ),
        None,
    )


def plan_model_storage(*, models_root: Path, registry_path: Path) -> dict[str, Any]:
    """Keep only installed generations and evidence-only scientific benchmarks."""
    root = Path(models_root).resolve()
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    versions = {str(row["version_id"]): row for row in registry["versions"]}
    protected_batches: dict[str, list[str]] = {}
    protected_generations: dict[str, set[str]] = {
        version_id: set() for version_id in versions
    }
    errors: list[str] = []

    for version_id, version in versions.items():
        generation_id = version.get("installed_generation_id")
        if generation_id is None:
            continue
        generation = _generation(version, generation_id)
        if generation is None:
            errors.append(f"{version_id}: installed generation is missing")
            continue
        protected_generations[version_id].add(str(generation_id))
        batch_id = str(generation.get("batch_id") or "")
        if batch_id:
            protected_batches.setdefault(batch_id, []).append(f"installed:{version_id}")

    generation_removals: list[dict[str, str]] = []
    for version_id, version in versions.items():
        for generation in version.get("generations", []):
            generation_id = str(generation.get("generation_id", ""))
            if generation_id not in protected_generations[version_id]:
                generation_removals.append(
                    {
                        "version_id": version_id,
                        "generation_id": generation_id,
                        "batch_id": str(generation.get("batch_id") or ""),
                    }
                )

    batch_removals: list[dict[str, Any]] = []
    batches_root = root / "batches"
    if batches_root.exists():
        if batches_root.is_symlink() or not batches_root.is_dir():
            errors.append("batches is not a safe directory")
        else:
            for batch_root in batches_root.iterdir():
                try:
                    if batch_root.is_symlink() or not batch_root.is_dir():
                        raise ValueError("batch is not a safe directory")
                    batch_id = catalog._identifier(batch_root.name, "batch_id")
                    if batch_id in protected_batches:
                        continue
                    manifest = _json(batch_root / "manifest.json")
                    if manifest.get("batch_id") != batch_id:
                        raise ValueError("batch manifest identity mismatch")
                    batch_removals.append(
                        {"batch_id": batch_id, "size_bytes": _size(batch_root)}
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"batches/{batch_root.name}: {exc}")

    candidate_removals: list[dict[str, Any]] = []
    candidates_root = root / "candidates"
    if candidates_root.exists():
        if candidates_root.is_symlink() or not candidates_root.is_dir():
            errors.append("candidates is not a safe directory")
        else:
            for candidate_root in candidates_root.iterdir():
                try:
                    if candidate_root.is_symlink() or not candidate_root.is_dir():
                        raise ValueError("candidate is not a safe directory")
                    candidate_id = catalog._identifier(candidate_root.name, "candidate_id")
                    result_path = candidate_root / "multiversion_result.json"
                    manifest_path = candidate_root / "batch" / "manifest.json"
                    identified = False
                    if result_path.is_file():
                        result = _json(result_path)
                        if result.get("batch_id") != candidate_id:
                            raise ValueError("candidate result identity mismatch")
                        identified = True
                    if manifest_path.is_file():
                        manifest = _json(manifest_path)
                        if manifest.get("batch_id") != candidate_id:
                            raise ValueError("candidate manifest identity mismatch")
                        identified = True
                    if not identified:
                        raise ValueError("candidate identity is missing")
                    candidate_removals.append(
                        {"candidate_id": candidate_id, "size_bytes": _size(candidate_root)}
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"candidates/{candidate_root.name}: {exc}")

    promotion_history_removals: list[dict[str, Any]] = []
    history_root = root / "promotion-history"
    if history_root.exists():
        if history_root.is_symlink() or not history_root.is_dir():
            errors.append("promotion-history is not a safe directory")
        else:
            for record_root in history_root.iterdir():
                try:
                    if record_root.is_symlink() or not record_root.is_dir():
                        raise ValueError("promotion history entry is not a safe directory")
                    record = _json(record_root / "promotion.json")
                    if (
                        record.get("kind") != "mushroom_ml_version_promotion"
                        or record.get("promotion_id") != record_root.name
                    ):
                        raise ValueError("promotion identity mismatch")
                    promotion_history_removals.append(
                        {
                            "promotion_id": record_root.name,
                            "size_bytes": _size(record_root),
                        }
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"promotion-history/{record_root.name}: {exc}")

    benchmark_compactions: list[dict[str, Any]] = []
    benchmarks_root = root / "benchmarks"
    if benchmarks_root.exists():
        if benchmarks_root.is_symlink() or not benchmarks_root.is_dir():
            errors.append("benchmarks is not a safe directory")
        else:
            for benchmark_root in benchmarks_root.iterdir():
                try:
                    if benchmark_root.is_symlink() or not benchmark_root.is_dir():
                        raise ValueError("benchmark is not a safe directory")
                    benchmark_id = catalog._identifier(
                        benchmark_root.name, "benchmark_batch_id"
                    )
                    benchmark_plan = mushroom_ml_benchmark_reports.benchmark_evidence_plan(
                        root, benchmark_id
                    )
                    if benchmark_plan.get("status") == "installable":
                        benchmark_compactions.append(benchmark_plan)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"benchmarks/{benchmark_root.name}: {exc}")

    removable = [
        *batch_removals,
        *candidate_removals,
        *promotion_history_removals,
    ]
    return {
        "protected_batches": [
            {"batch_id": batch_id, "reasons": sorted(set(reasons))}
            for batch_id, reasons in sorted(protected_batches.items())
        ],
        "retained_rollbacks": [],
        "generation_removals": generation_removals,
        "batch_removals": batch_removals,
        "candidate_removals": candidate_removals,
        "promotion_history_removals": promotion_history_removals,
        "benchmark_compactions": benchmark_compactions,
        "recoverable_bytes": sum(int(row["size_bytes"]) for row in removable)
        + sum(int(row.get("recoverable_bytes", 0)) for row in benchmark_compactions),
        "errors": errors,
    }


def apply_model_storage_plan(
    *, models_root: Path, registry_path: Path, plan: dict[str, Any]
) -> dict[str, Any]:
    """Revalidate the plan, publish registry pruning, then remove unreferenced data."""
    fresh = plan_model_storage(models_root=models_root, registry_path=registry_path)
    keys = (
        "generation_removals",
        "batch_removals",
        "candidate_removals",
        "promotion_history_removals",
        "benchmark_compactions",
    )
    if any(fresh.get(key) != plan.get(key) for key in keys):
        raise ValueError("ML storage references changed after planning")
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    removals = {
        (str(row["version_id"]), str(row["generation_id"]))
        for row in plan.get("generation_removals", [])
        if isinstance(row, dict)
    }
    for version in registry["versions"]:
        version_id = str(version["version_id"])
        version["generations"] = [
            row
            for row in version.get("generations", [])
            if (version_id, str(row.get("generation_id", ""))) not in removals
        ]
    if removals:
        mushroom_ml_version_registry.save_registry(registry_path, registry)

    root = Path(models_root).resolve()
    removed_batches: list[str] = []
    removed_candidates: list[str] = []
    removed_promotion_history: list[str] = []
    compacted_benchmarks: list[str] = []
    errors: list[str] = []
    for collection, plan_key, key, removed in (
        ("candidates", "candidate_removals", "candidate_id", removed_candidates),
        ("batches", "batch_removals", "batch_id", removed_batches),
        (
            "promotion-history",
            "promotion_history_removals",
            "promotion_id",
            removed_promotion_history,
        ),
    ):
        for entry in plan.get(plan_key, []):
            identifier = str(entry.get(key, ""))
            target = root / collection / identifier
            try:
                if target.is_symlink() or not target.is_dir() or target.resolve().parent != (root / collection).resolve():
                    raise ValueError("planned model path is no longer a safe directory")
                shutil.rmtree(target.resolve())
                removed.append(identifier)
            except (OSError, ValueError) as exc:
                errors.append(f"{collection}/{identifier}: {exc}")
    for benchmark_plan in plan.get("benchmark_compactions", []):
        benchmark_id = str(benchmark_plan.get("batch_id", ""))
        try:
            result = mushroom_ml_benchmark_reports.compact_benchmark_to_evidence(
                root,
                benchmark_id,
                plan=benchmark_plan,
            )
            if result.get("status") == "evidence_only":
                compacted_benchmarks.append(benchmark_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"benchmarks/{benchmark_id}: {exc}")
    return {
        "removed_generations": [f"{version_id}/{generation_id}" for version_id, generation_id in sorted(removals)],
        "removed_batches": removed_batches,
        "removed_candidates": removed_candidates,
        "removed_promotion_history": removed_promotion_history,
        "compacted_benchmarks": compacted_benchmarks,
        "errors": errors,
    }
