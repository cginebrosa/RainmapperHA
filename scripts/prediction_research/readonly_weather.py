"""Pin the downloaded weather snapshot without operational locks or leases.

Only this process's resolver is adapted. Data readers, filters and feature
calculations are unchanged. No services or persisted settings are modified.
"""
from contextlib import contextmanager, ExitStack
import sys
from unittest.mock import patch

import pyarrow as pa

from common import ROOT, digest, load
from rainmapper_core import weather_history_dataset as dataset


@contextmanager
def frozen_weather(data_dir=None):
    data_dir = (data_dir or ROOT / "docker-data/Data").resolve()
    root = dataset.weather_history_root(data_dir).resolve()
    pointer_path = root / "CURRENT.json"
    pointer_sha = digest(pointer_path)
    pointer = load(pointer_path)
    generation = dataset.resolve_weather_manifest(
        root, root / pointer["manifest_path"],
        expected_generation_id=pointer["generation_id"],
        expected_sha256=pointer["manifest_sha256"], verify_hashes=True)
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)

    def check():
        if digest(pointer_path) != pointer_sha:
            raise ValueError("Weather CURRENT changed during frozen research")

    def resolve(path, *, verify_hashes=False):
        if dataset.weather_history_root(path).resolve() != root:
            raise ValueError("Unexpected weather input root")
        check()
        if verify_hashes:
            dataset.validate_weather_generation(generation, verify_hashes=True)
        return generation

    @contextmanager
    def pin(path, generation_id=None, *, lease_seconds=3600):
        if lease_seconds <= 0:
            raise ValueError("Invalid reader duration")
        chosen = resolve(path)
        if generation_id is not None and generation_id != chosen.generation_id:
            raise ValueError("Requested weather generation differs from frozen inputs")
        yield chosen
        check()

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(dataset, "resolve_weather_generation", resolve))
            stack.enter_context(patch.object(dataset, "pin_weather_generation", pin))
            # PointWeatherReader imports its resolver by name, so freeze that alias too.
            map_weather = sys.modules.get("rainmapper_core.mushroom_map_weather")
            if map_weather is not None:
                stack.enter_context(patch.object(map_weather, "resolve_weather_generation", resolve))
            yield generation
    finally:
        check()
        dataset.validate_weather_generation(generation, verify_hashes=True)
