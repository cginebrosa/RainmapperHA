"""Verify originals, sealed evidence and archived sources before closing the study."""
from __future__ import annotations
import os
from pathlib import Path
from scripts.prediction_model_selection.common import (
    ROOT, OUTPUT, OLD_OUTPUT, load, write_new, digest, verify_inputs, protect_originals,
)


def verify_record(record, *, allow_archived_source=False):
    path = ROOT / record["path"]
    if path.is_file() and digest(path) == record["sha256"]:
        return
    if allow_archived_source and path.suffix == ".py":
        archive = OUTPUT / "source-archive" / (record["sha256"] + ".py")
        if archive.is_file() and digest(archive) == record["sha256"]:
            return
    raise ValueError("Sealed file changed: " + record["path"])


def main():
    if os.environ.get("RAINMAPPER_MODEL_SELECTION_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    inventory = load(OUTPUT / "inventory.json")
    cohort = load(OLD_OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    verify_record(inventory["protocol"])
    for record in inventory["old_files"]:
        verify_record(record)
    control_count = 0
    for fold in (2024, 2025, 2026):
        ranking = OUTPUT / f"fold-{fold}"
        ranking_summary = load(ranking / "ranking-summary.json")
        if ranking_summary["status"] != "completed" or not ranking_summary["technical_control_old_catalog_exact"]:
            raise ValueError("Incomplete area ranking/control")
        provenance = load(ranking / "ranking-provenance.json")
        for path, sha in provenance["inputs"].items():
            verify_record({"path": path, "sha256": sha}, allow_archived_source=True)
        for record in provenance["outputs"]:
            verify_record(record)
        stage = OUTPUT / f"fold-{fold}/evaluation"
        summary = load(stage / "evaluation-summary.json")
        if summary["status"] != "completed" or summary["technical_control"]["status"] != "passed":
            raise ValueError("Incomplete evaluation/control")
        for record in load(stage / "evaluation-seal.json")["files"]:
            verify_record(record, allow_archived_source=True)
        for name, field in (("predictions.jsonl", "predictions_sha256"),
                            ("control-comparisons.jsonl", "control_comparisons_sha256"),
                            ("input-contract-comparisons.jsonl", "input_contract_comparisons_sha256")):
            if digest(stage / name) != summary[field]:
                raise ValueError("Closed prediction evidence changed")
        control_count += summary["technical_control"]["emissions"]
    if control_count != 812:
        raise ValueError("Incomplete 812-emission technical control")
    analysis_summary = load(OUTPUT / "analysis/summary.json")
    if analysis_summary["status"] != "completed" or not analysis_summary["inputs_verified_after"]:
        raise ValueError("Incomplete analysis")
    for record in analysis_summary["files"]:
        verify_record(record)
    for record in load(OUTPUT / "analysis/analysis-seal.json")["files"]:
        verify_record(record, allow_archived_source=True)
    for manifest in (OUTPUT / "runs").glob("*.sources.json"):
        for record in load(manifest)["files"]:
            suffix = Path(record["path"]).suffix
            archive = OUTPUT / "source-archive" / (record["sha256"] + suffix)
            if digest(archive) != record["sha256"]:
                raise ValueError("Exact executed source is not archived")
    private_ids = [r["observation_id"] for r in cohort["rows"]]
    docs = list((ROOT / "docs/agents/prediction-model-selection").glob("*.md"))
    for doc in docs:
        content = doc.read_text()
        if any(identifier in content for identifier in private_ids):
            raise ValueError("Private observation identifier in public report")
    outputs = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and not path.is_symlink() and "runs" not in path.relative_to(OUTPUT).parts:
            outputs.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size})
    sources = docs + list((ROOT / "scripts/prediction_model_selection").glob("*.py"))
    sources += list((ROOT / "tests").glob("test_prediction_model_selection*.py"))
    write_new(OUTPUT / "closure.json", {"status": "verified", "old_files_unchanged": len(inventory["old_files"]),
        "original_inputs_unchanged": True, "technical_control_emissions": control_count,
        "private_identifiers_absent_from_docs": True, "executed_sources_archived": True,
        "outputs": outputs, "delivery_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in sources]})
    print({"status": "verified", "technical_control_emissions": control_count,
           "old_files_unchanged": len(inventory["old_files"])})


if __name__ == "__main__":
    main()
