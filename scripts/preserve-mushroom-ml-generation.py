#!/usr/bin/env python3
"""Preserve one ML generation in the permanent local version archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_version_registry


def _key_value(value: str) -> tuple[str, str]:
    key, separator, resolved = value.partition("=")
    if not separator or not key.strip() or not resolved.strip():
        raise argparse.ArgumentTypeError("expected NAME=VALUE")
    return key.strip(), resolved.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--default-registry", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--version-id", required=True)
    parser.add_argument(
        "--kind", choices=sorted(mushroom_ml_version_registry.GENERATION_KINDS), required=True
    )
    parser.add_argument("--include", action="append", required=True)
    parser.add_argument(
        "--input-identity", action="append", type=_key_value, required=True
    )
    parser.add_argument(
        "--promotion-gate-status",
        choices=("not_evaluated", "passed", "failed"),
        default="not_evaluated",
    )
    parser.add_argument("--metadata-json", default="{}")
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    artifacts: dict[str, Path] = {}
    for pattern in args.include:
        matches = sorted(path for path in source_root.glob(pattern) if path.is_file())
        if not matches:
            parser.error(f"include pattern matched no files: {pattern}")
        for source in matches:
            relative = source.relative_to(source_root).as_posix()
            artifacts[relative] = source
    identities = dict(args.input_identity)
    if len(identities) != len(args.input_identity):
        parser.error("duplicate input identity name")
    try:
        metadata = json.loads(args.metadata_json)
    except json.JSONDecodeError as exc:
        parser.error(f"invalid metadata JSON: {exc}")
    if not isinstance(metadata, dict):
        parser.error("metadata JSON must contain an object")

    mushroom_ml_version_registry.ensure_seeded(
        default_path=args.default_registry,
        persistent_path=args.registry,
    )
    result = mushroom_ml_version_registry.persist_generation(
        args.registry,
        args.archive_root,
        version_id=args.version_id,
        kind=args.kind,
        artifacts=artifacts,
        input_identities=identities,
        metadata=metadata,
        promotion_gate_status=args.promotion_gate_status,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "generation": result["generation"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
