"""Same bounded resident point readers for a coordinator or a remote worker."""
from __future__ import annotations

import atexit
from datetime import date, timedelta
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core.mushroom_map_ecology import prediction_candidates
from rainmapper_core.mushroom_map_weather import map_today


def load_config(path):
    path = Path(path).resolve()
    if path.stat().st_size > 16384:
        raise ValueError("map_config_limit")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("invalid_map_config")
    return data, path.parent


class ResidentReader:
    def __init__(self, python, script, arguments, *, timeout=10, max_request_bytes=2048):
        self.timeout, self.max_request_bytes = timeout, max_request_bytes
        self.command = [python, str(Path(__file__).resolve().parents[1]/"scripts"/script), *arguments]
        self.process = None
        self.answers = queue.Queue(maxsize=1)
        self.serial = 0
        atexit.register(self.close)

    def close(self):
        process = self.process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        if process:
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()
        self.process = None

    def _read(self, process, answers):
        try:
            while line := process.stdout.readline(65537):
                if len(line) > 65536:
                    raise ValueError("reader_result_limit")
                answers.put_nowait(json.loads(line))
        except Exception:
            pass
        finally:
            try:
                answers.put_nowait(None)
            except queue.Full:
                pass

    def call(self, payload):
        if self.process is None:
            self.answers = queue.Queue(maxsize=1)
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL)
            threading.Thread(target=self._read, args=(self.process,self.answers), daemon=True).start()
        self.serial += 1
        raw = json.dumps({"id":self.serial, **payload}, allow_nan=False).encode()+b"\n"
        if len(raw) > self.max_request_bytes:
            raise ValueError("reader_request_limit")
        try:
            self.process.stdin.write(raw)
            self.process.stdin.flush()
            result = self.answers.get(timeout=self.timeout)
            if not isinstance(result,dict) or result.pop("id",None) != self.serial:
                raise ValueError("reader_unavailable")
            return result
        except Exception:
            self.close()
            raise


class PointExecutor:
    """One query at a time; all paths come from administrator-owned configuration."""
    def __init__(self, config, root):
        self.lock = threading.Lock()
        self.root = Path(root)
        self.calendar_timezone = config.get('calendar_timezone', 'Europe/Madrid')
        map_today(self.calendar_timezone)  # Validate once, including geographic-only mode.
        def path(key):
            value = config.get(key)
            if not isinstance(value,str) or not value:
                raise ValueError("missing_map_path:"+key)
            return str((self.root/value).resolve())
        geography = ["--terrain-index",path("terrain_index"),"--soil-root",path("soil_root"),
                     "--dem-root",path("dem_root"),"--regional-root",path("regional_root")]
        if config.get("municipalities"):
            geography += ["--municipalities",path("municipalities"),"--municipalities-edition",str(config.get("municipalities_edition","unspecified"))]
        for key, flag in (("land_cover", "--land-cover"), ("geology", "--geology"),
                          ("land_cover_parts", "--land-cover-parts"), ("geology_parts", "--geology-parts"),
                          ("forest_index", "--forest-index"), ("forest_catalogs", "--forest-catalogs"),
                          ("profiles", "--profiles"), ("ecology_catalogs", "--ecology-catalogs"),
                          ("gis_mappings", "--gis-mappings"), ("openlandmap_ph", "--openlandmap-ph"),
                          ("geography_sources", "--geography-sources")):
            if config.get(key):
                geography += [flag, path(key)]
        if config.get('ecology_ph_source'):
            geography += ['--ecology-ph-source',config['ecology_ph_source']]
        self.model = None
        if config.get('models_root'):
            self.model = ResidentReader(config.get('model_python',sys.executable),'prediction-map-local-model.py',
                ['--registry-path',path('model_registry'),'--models-root',path('models_root'),
                 '--profiles-path',path('profiles'),'--data-root',path('weather_data'),
                 '--stations-file',path('weather_stations'),
                 '--calendar-timezone',self.calendar_timezone],timeout=90,max_request_bytes=65536)
        # Up to 32 requested IDs (80 chars each), plus the bounded point envelope.
        self.geography = ResidentReader(config.get("geography_python",sys.executable),"prediction-map-local-geography.py",geography,
                                        max_request_bytes=4096)
        self.weather = ResidentReader(config.get("weather_python",sys.executable),"prediction-map-local-weather.py",
                                     ["--data-root",path("weather_data"),"--stations-file",path("weather_stations"),
                                      "--calendar-timezone",self.calendar_timezone])

    def ready(self):
        with self.lock:
            geo = self.geography.call({"op":"capabilities"})
            weather = self.weather.call({"op":"capabilities"})
            model_ready = self.model is None or self.model.call({"op":"capabilities"}).get("model_ready") is True
            return geo.get("geography_ready") is True and weather.get("weather_ready") is True and model_ready

    def close(self):
        with self.lock:
            self.geography.close()
            self.weather.close()
            if self.model: self.model.close()

    def execute(self, request):
        request = contract.parse_request(json.dumps(request).encode())
        request.setdefault('calendar_timezone', self.calendar_timezone)
        with self.lock:
            started = time.perf_counter()
            result = contract.prediction_result(request) if self.model else contract.demo_result(request)
            result.update(self.geography.call({**request["point"], "start_date":request["start_date"],
                                              "horizon_days":request["horizon_days"],"model_inputs":self.model is not None,
                                              "species_ids":request['species_ids']}))
            if self.model and prediction_candidates(result.get('ecology', {}), request['species_ids']):
                result.update(self.model.call({'request':request,'geography':result}))
            result.pop('model_soil_water',None)
            end = min(date.fromisoformat(request["start_date"])-timedelta(days=1),
                      map_today(request['calendar_timezone'])-timedelta(days=1))
            result.update(self.weather.call({**request["point"], "altitude_m":result.get("terrain",{}).get("elevation",{}).get("value_m"),
                "end_day":end.isoformat(),"days":request["history_days"],
                "calendar_timezone":request['calendar_timezone']}))
            result["execution"] = {"mode":request.get("execution","local"),"compute_ms":round((time.perf_counter()-started)*1000,3)}
            contract.validate_result(result,request)
            contract.encode_result(result)
            return result
