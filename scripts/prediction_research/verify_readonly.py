"""Exercise the weather adapter and output guard against the downloaded snapshot."""
import json
import sys

from common import ROOT, OUTPUT, write_new, protect_originals

sys.path.insert(0, str(ROOT))
from rainmapper_core import weather_history_dataset as dataset
from rainmapper_core import mushroom_observation_context as weather
from readonly_weather import frozen_weather


def control_metadata(root):
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
            for name in ("locks", "leases") for p in (root / name).rglob("*") if p.is_file()}


def main():
    protect_originals()
    data = ROOT / "docker-data/Data"
    root = data / "weather-history"
    before = control_metadata(root)
    with frozen_weather(data) as generation:
        catalog = weather.load_stations_catalog(data)
        part = generation.partitions[-1]
        rows = list(dataset.iter_weather_history(data, columns=["source", "station_code", "local_date"],
                    sources={part.source}, start_date=part.max_local_date, end_date=part.max_local_date))
        with dataset.pin_weather_generation(data, generation.generation_id) as pinned:
            assert pinned is generation
        try:
            with dataset.pin_weather_generation(data, "different-generation"):
                raise AssertionError("Mismatched generation should be rejected")
        except ValueError:
            pass
        read_rows = sum(row.num_rows for row in rows)
        assert read_rows > 0 and len(catalog) > 0
    after = control_metadata(root)
    assert before == after, "Operational lock/lease metadata changed"
    # The audit hook rejects this BEFORE opening/creating any original file.
    try:
        (data / "research-must-not-create-this").open("w")
        raise AssertionError("Original write was not rejected")
    except PermissionError:
        pass
    receipt = {"same_generation": True, "weather_hashes_verified_before_after": True,
               "lock_lease_metadata_unchanged": True, "outside_write_rejected": True,
               "catalog_rows": len(catalog), "bounded_weather_rows_read": read_rows}
    write_new(OUTPUT / "readonly-verification.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
