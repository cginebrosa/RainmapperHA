#!/usr/bin/env python3
"""Rebuild official Meteocat/AEMET history in an isolated local candidate.

The source HA snapshot is never modified. Meteocat payloads are cached in
restartable date chunks; AEMET reuses the previously cached official JSON.
Rows are streamed into Rainmapper's immutable partition writer so a missing
measurement never replaces a valid historical value with null.
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.weather_history_dataset import resolve_weather_generation, sha256_file
from rainmapper_core.weather_history_pending import (
    acknowledge_pending_batch,
    build_pending_batch,
    list_pending_batches,
)
from rainmapper_core.weather_history_writer import archive_pending_batches
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv
from rainmapper_core.sources.sodapy_local import Socrata


MODELED_COLUMNS = (
    "Total",
    "max_temp_celsius",
    "min_temp_celsius",
    "max_humidity_percent",
    "min_humidity_percent",
)
CANONICAL_MODELED_COLUMNS = (
    "rain_mm",
    "max_temp_celsius",
    "min_temp_celsius",
    "max_humidity_percent",
    "min_humidity_percent",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_aemet_helper():
    path = REPO_ROOT / "scripts/aemet-backfill-30-days.py"
    spec = importlib.util.spec_from_file_location("rainmapper_aemet_backfill", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load AEMET helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inclusive_chunks(start: date, end: date, days: int) -> Iterator[tuple[date, date]]:
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=days - 1))
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def atomic_json_gzip(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    temporary.write_bytes(gzip.compress(encoded, compresslevel=6, mtime=0))
    os.replace(temporary, path)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json_gzip(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def meteocat_query(kind: str, start: date, end: date) -> str:
    start_text = f"{start.isoformat()}T00:00:00.000"
    end_text = f"{end.isoformat()}T23:59:59.999"
    if kind == "rain":
        return (
            "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, "
            "codi_variable, sum(valor_lectura) as valor_variable "
            f"WHERE (data_lectura BETWEEN '{start_text}' AND '{end_text}') "
            "AND codi_variable in ('35') AND valor_lectura >= 0 "
            "GROUP BY codi_estacio, codi_variable, ultima_lectura "
            "ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"
        )
    return (
        "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, "
        "codi_variable, max(valor_lectura) as max_valor_variable, "
        "min(valor_lectura) as min_valor_variable "
        f"WHERE (data_lectura BETWEEN '{start_text}' AND '{end_text}') "
        "AND codi_variable in ('40','42','3','44') "
        "GROUP BY codi_estacio, codi_variable, ultima_lectura "
        "ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"
    )


def download_meteocat(args: argparse.Namespace) -> int:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    chunks = list(inclusive_chunks(args.start, args.end, args.chunk_days))
    total = len(chunks) * 2
    completed = skipped = 0
    client = Socrata("analisi.transparenciacatalunya.cat", None, timeout=args.timeout)
    for index, (chunk_start, chunk_end) in enumerate(chunks, start=1):
        for kind in ("rain", "conditions"):
            stem = f"{kind}_{chunk_start:%Y%m%d}_{chunk_end:%Y%m%d}"
            payload_path = output / f"{stem}.json.gz"
            meta_path = output / f"{stem}.meta.json"
            if payload_path.is_file() and meta_path.is_file():
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                if metadata.get("status") in {"recovered", "empty_period"}:
                    skipped += 1
                    continue
            failure: Exception | None = None
            rows: list[dict[str, Any]] | None = None
            for attempt in range(1, args.attempts + 1):
                try:
                    rows = client.get(
                        "nzvn-apee",
                        query=meteocat_query(kind, chunk_start, chunk_end),
                        exclude_system_fields="true",
                    )
                    if not isinstance(rows, list):
                        raise RuntimeError("Meteocat response is not a JSON list")
                    if len(rows) >= 200_000:
                        raise RuntimeError("Meteocat result reached LIMIT 200000")
                    break
                except Exception as exc:  # transport errors vary by requests backend
                    failure = exc
                    if attempt < args.attempts:
                        time.sleep(min(2 ** (attempt - 1), 10))
            if rows is None:
                client.close()
                atomic_json(
                    meta_path,
                    {
                        "source": "meteocat",
                        "kind": kind,
                        "start_date": chunk_start.isoformat(),
                        "end_date_inclusive": chunk_end.isoformat(),
                        "requested_at": utc_now(),
                        "status": "request_failed",
                        "error": str(failure),
                    },
                )
                raise RuntimeError(f"Meteocat failed for {stem}: {failure}")
            atomic_json_gzip(payload_path, rows)
            atomic_json(
                meta_path,
                {
                    "source": "meteocat",
                    "kind": kind,
                    "start_date": chunk_start.isoformat(),
                    "end_date_inclusive": chunk_end.isoformat(),
                    "requested_at": utc_now(),
                    "status": "recovered" if rows else "empty_period",
                    "rows": len(rows),
                    "payload_sha256": sha256_file(payload_path),
                    "zero_semantics": "Only an observed numeric zero is dry; missing is null.",
                },
            )
            completed += 1
            done = completed + skipped
            print(
                f"meteocat {done}/{total} ({index}/{len(chunks)} {kind}) "
                f"{chunk_start}..{chunk_end}: {len(rows)} rows",
                flush=True,
            )
            time.sleep(args.pause)
    client.close()
    print(json.dumps({"completed": completed, "skipped": skipped, "total": total}))
    return 0


def _frame_batches(frame: pd.DataFrame, rows: int = 8_192) -> Iterator[pa.Table]:
    for offset in range(0, len(frame), rows):
        yield pa.Table.from_pandas(frame.iloc[offset : offset + rows], preserve_index=False)


def aemet_batches(raw_dir: Path, station_catalog_path: Path) -> Iterator[pa.Table]:
    helper = load_aemet_helper()
    catalog = helper.read_station_catalog_if_exists(station_catalog_path)
    paths = sorted(raw_dir.glob("????????_????????.json.gz"))
    for index, path in enumerate(paths, start=1):
        raw = read_json_gzip(path)
        frame = helper.build_daily_incremental_from_climatology(raw, catalog)
        if not frame.empty:
            yield from _frame_batches(frame)
        if index == 1 or index % 20 == 0 or index == len(paths):
            print(f"aemet normalized {index}/{len(paths)} cached chunks", flush=True)


def _meteocat_station_metadata(path: Path) -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return {
        str(row.get("Codi Estació") or "").strip(): row
        for row in frame.to_dict("records")
        if str(row.get("Codi Estació") or "").strip()
    }


def meteocat_batches(raw_dir: Path, station_catalog_path: Path) -> Iterator[pa.Table]:
    metadata = _meteocat_station_metadata(station_catalog_path)
    rain_paths = sorted(raw_dir.glob("rain_????????_????????.json.gz"))
    for rain_path in rain_paths:
        suffix = rain_path.name.removeprefix("rain_")
        conditions_path = raw_dir / f"conditions_{suffix}"
        if not conditions_path.is_file():
            raise RuntimeError(f"Missing paired Meteocat payload: {conditions_path}")
        daily: dict[tuple[str, str], dict[str, Any]] = {}
        for kind, path in (("rain", rain_path), ("conditions", conditions_path)):
            for raw in read_json_gzip(path):
                station = str(raw.get("codi_estacio") or "").strip()
                day = str(raw.get("ultima_lectura") or "")[:10]
                if not station or len(day) != 10:
                    continue
                values = daily.setdefault((station, day), {})
                code = str(raw.get("codi_variable") or "")
                if kind == "rain" and code == "35":
                    values["Total"] = raw.get("valor_variable")
                elif code == "40":
                    values["max_temp_celsius"] = raw.get("max_valor_variable")
                elif code == "42":
                    values["min_temp_celsius"] = raw.get("min_valor_variable")
                elif code == "3":
                    values["max_humidity_percent"] = raw.get("max_valor_variable")
                elif code == "44":
                    values["min_humidity_percent"] = raw.get("min_valor_variable")
        rows: list[dict[str, Any]] = []
        for (station_code, day), values in sorted(daily.items()):
            station = metadata.get(station_code, {})
            row = {
                "Codi Estació": station_code,
                "Data Lectura": f"{day} 02:00:01",
                "Estació": station.get("Estació", station_code),
                "Comarca": station.get("Comarca", ""),
                "Municipi": station.get("Municipi", ""),
                "Provincia": station.get("Provincia", ""),
                "Altitud": station.get("Altitud", ""),
                "Latitud": station.get("Latitud", ""),
                "Longitud": station.get("Longitud", ""),
                "Ultima Lectura": f"{day.replace('-', '/')} 02:00:01",
                "Variable": "Precipitació",
                "Total": values.get("Total"),
                "Unitat": "mm",
                "Data Local": day.replace("-", ""),
                "Hora Local": "02:00:01",
                **values,
            }
            if any(pd.notna(row.get(column)) for column in MODELED_COLUMNS):
                rows.append(row)
        if rows:
            yield from _frame_batches(pd.DataFrame(rows))


def prepare_candidate(snapshot_data: Path, candidate_data: Path) -> None:
    if candidate_data.exists():
        return
    if not (snapshot_data / "weather-history/CURRENT.json").is_file():
        raise RuntimeError(f"Snapshot has no partitioned weather history: {snapshot_data}")
    candidate_data.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(snapshot_data, candidate_data)


def ingest_source(
    candidate_data: Path,
    source: str,
    batches: Iterable[pa.Table],
    reference_day: date,
) -> dict[str, Any]:
    pending = list_pending_batches(candidate_data, source)
    if not pending:
        built = build_pending_batch(
            candidate_data,
            source,
            batches,
            run_id=f"official-gap-repair-{reference_day.isoformat()}-{source}",
        )
        pending = [] if built is None else [built]
    if len(pending) != 1:
        raise RuntimeError(f"Expected one pending batch for {source}, found {len(pending)}")
    batch = pending[0]
    before = resolve_weather_generation(candidate_data)
    archive = archive_pending_batches(candidate_data, reserve_bytes=0)
    live = apply_pending_to_live_csv(candidate_data, batch, reference_day=reference_day)
    acknowledge_pending_batch(batch)
    after = resolve_weather_generation(candidate_data, verify_hashes=True)
    return {
        "source": source,
        "before_generation": before.generation_id,
        "after_generation": after.generation_id,
        "pending_rows": batch.rows,
        "pending_input_rows": batch.input_rows,
        "collapsed_rows": batch.collapsed_rows,
        "years": list(batch.years),
        "archive_committed": archive.committed,
        "live_csv": live.to_dict(),
        "manifest_sha256": after.manifest_sha256,
    }


def build_candidate(args: argparse.Namespace) -> int:
    snapshot = args.snapshot_data.resolve()
    candidate = args.candidate_data.resolve()
    prepare_candidate(snapshot, candidate)
    reports: list[dict[str, Any]] = []
    if args.source in {"aemet", "all"}:
        reports.append(
            ingest_source(
                candidate,
                "aemet",
                aemet_batches(args.aemet_raw_dir.resolve(), snapshot / "estacions_aemet.csv"),
                args.reference_day,
            )
        )
    if args.source in {"meteocat", "all"}:
        reports.append(
            ingest_source(
                candidate,
                "meteocat",
                meteocat_batches(args.meteocat_raw_dir.resolve(), snapshot / "estacions_xema.csv"),
                args.reference_day,
            )
        )
    output = args.report.resolve()
    atomic_json(
        output,
        {
            "generated_at": utc_now(),
            "snapshot_data": str(snapshot),
            "candidate_data": str(candidate),
            "snapshot_current_sha256": sha256_file(snapshot / "weather-history/CURRENT.json"),
            "candidate_current_sha256": sha256_file(candidate / "weather-history/CURRENT.json"),
            "sources": reports,
            "home_assistant_write": False,
        },
    )
    print(json.dumps({"report": str(output), "sources": reports}, ensure_ascii=False))
    return 0


def history_metrics(data_dir: Path, sources: set[str]) -> dict[str, Any]:
    generation = resolve_weather_generation(data_dir, verify_hashes=True)
    partitions: dict[str, dict[str, Any]] = {}
    previous_dates: dict[tuple[str, str], date] = {}
    gap_events = {source: 0 for source in sources}
    gap_days = {source: 0 for source in sources}
    for partition in generation.partitions:
        if partition.source not in sources:
            continue
        label = f"{partition.source}/{partition.year}"
        metrics = {
            "source": partition.source,
            "year": partition.year,
            "rows": 0,
            "stations": set(),
            "rain_zero_rows": 0,
            "rain_positive_rows": 0,
            "null_counts": {column: 0 for column in CANONICAL_MODELED_COLUMNS},
        }
        parquet = pq.ParquetFile(generation.object_path(partition.path))
        columns = ["station_code", "local_date", *CANONICAL_MODELED_COLUMNS]
        for batch in parquet.iter_batches(batch_size=8_192, columns=columns):
            for row in batch.to_pylist():
                metrics["rows"] += 1
                station = str(row["station_code"])
                metrics["stations"].add(station)
                rain = row.get("rain_mm")
                if rain == 0:
                    metrics["rain_zero_rows"] += 1
                elif rain is not None and float(rain) > 0:
                    metrics["rain_positive_rows"] += 1
                for column in CANONICAL_MODELED_COLUMNS:
                    if row.get(column) is None:
                        metrics["null_counts"][column] += 1
                current = date(
                    int(str(row["local_date"])[:4]),
                    int(str(row["local_date"])[4:6]),
                    int(str(row["local_date"])[6:8]),
                )
                previous = previous_dates.get((partition.source, station))
                if previous is not None and current > previous + timedelta(days=1):
                    gap_events[partition.source] += 1
                    gap_days[partition.source] += (current - previous).days - 1
                if previous is None or current > previous:
                    previous_dates[(partition.source, station)] = current
        metrics["stations"] = len(metrics["stations"])
        partitions[label] = metrics
    return {
        "generation_id": generation.generation_id,
        "manifest_sha256": generation.manifest_sha256,
        "partitions": partitions,
        "internal_gap_events": gap_events,
        "internal_gap_days": gap_days,
    }


def partition_keys(generation, source: str, year: int) -> set[tuple[str, str]]:
    partition = next(
        (item for item in generation.partitions if item.source == source and item.year == year),
        None,
    )
    if partition is None:
        return set()
    keys: set[tuple[str, str]] = set()
    parquet = pq.ParquetFile(generation.object_path(partition.path))
    for batch in parquet.iter_batches(batch_size=32_768, columns=["station_code", "local_date"]):
        stations = batch.column("station_code").to_pylist()
        dates = batch.column("local_date").to_pylist()
        keys.update(zip(map(str, stations), map(str, dates)))
    return keys


def audit_candidate(args: argparse.Namespace) -> int:
    before_path = args.before_data.resolve()
    after_path = args.after_data.resolve()
    sources = set(args.source)
    before = history_metrics(before_path, sources)
    after = history_metrics(after_path, sources)
    before_generation = resolve_weather_generation(before_path)
    after_generation = resolve_weather_generation(after_path)
    comparisons: list[dict[str, Any]] = []
    identities = sorted(
        {
            (item.source, item.year)
            for generation in (before_generation, after_generation)
            for item in generation.partitions
            if item.source in sources
        }
    )
    total_missing = 0
    for source, year in identities:
        old_keys = partition_keys(before_generation, source, year)
        new_keys = partition_keys(after_generation, source, year)
        missing = len(old_keys - new_keys)
        total_missing += missing
        label = f"{source}/{year}"
        old_metrics = before["partitions"].get(label, {})
        new_metrics = after["partitions"].get(label, {})
        comparisons.append(
            {
                "source": source,
                "year": year,
                "rows_before": old_metrics.get("rows", 0),
                "rows_after": new_metrics.get("rows", 0),
                "added_keys": len(new_keys - old_keys),
                "missing_old_keys": missing,
                "null_counts_before": old_metrics.get("null_counts", {}),
                "null_counts_after": new_metrics.get("null_counts", {}),
                "rain_zero_before": old_metrics.get("rain_zero_rows", 0),
                "rain_zero_after": new_metrics.get("rain_zero_rows", 0),
            }
        )
    report = {
        "generated_at": utc_now(),
        "before_data": str(before_path),
        "after_data": str(after_path),
        "sources": sorted(sources),
        "before": before,
        "after": after,
        "comparisons": comparisons,
        "missing_old_keys": total_missing,
        "passes_no_loss_gate": total_missing == 0,
        "home_assistant_write": False,
    }
    atomic_json(args.report.resolve(), report)
    print(
        json.dumps(
            {
                "report": str(args.report.resolve()),
                "missing_old_keys": total_missing,
                "passes_no_loss_gate": total_missing == 0,
                "internal_gap_days_before": before["internal_gap_days"],
                "internal_gap_days_after": after["internal_gap_days"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if total_missing == 0 else 1


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download-meteocat")
    download.add_argument("--output-dir", type=Path, required=True)
    download.add_argument("--start", type=parse_iso_date, required=True)
    download.add_argument("--end", type=parse_iso_date, required=True)
    # The completed 2026-08-11 recovery used 15-day XEMA chunks (220/220
    # requests, no failures). Keep that proven provider-safe size instead of
    # assuming a monthly all-stations query remains below Socrata limits.
    download.add_argument("--chunk-days", type=int, default=15)
    download.add_argument("--timeout", type=int, default=90)
    download.add_argument("--attempts", type=int, default=4)
    download.add_argument("--pause", type=float, default=5.0)
    download.set_defaults(func=download_meteocat)

    build = subparsers.add_parser("build-candidate")
    build.add_argument("--snapshot-data", type=Path, required=True)
    build.add_argument("--candidate-data", type=Path, required=True)
    build.add_argument("--aemet-raw-dir", type=Path, required=True)
    build.add_argument("--meteocat-raw-dir", type=Path, required=True)
    build.add_argument("--reference-day", type=parse_iso_date, required=True)
    build.add_argument("--source", choices=("aemet", "meteocat", "all"), default="all")
    build.add_argument("--report", type=Path, required=True)
    build.set_defaults(func=build_candidate)

    audit = subparsers.add_parser("audit-candidate")
    audit.add_argument("--before-data", type=Path, required=True)
    audit.add_argument("--after-data", type=Path, required=True)
    audit.add_argument(
        "--source",
        action="append",
        choices=("aemet", "meteocat"),
        required=True,
    )
    audit.add_argument("--report", type=Path, required=True)
    audit.set_defaults(func=audit_candidate)

    args = parser.parse_args()
    if getattr(args, "start", None) and args.start > args.end:
        parser.error("--start must not be after --end")
    if getattr(args, "chunk_days", 1) <= 0:
        parser.error("--chunk-days must be positive")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
