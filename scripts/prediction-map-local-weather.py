#!/usr/bin/env python3
"""Read-only, resident weather adapter for the local map preview."""
import argparse
from datetime import date, timedelta
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_weather import PointWeatherReader, map_today


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",required=True)
    parser.add_argument("--stations-file",required=True)
    parser.add_argument("--calendar-timezone",default="Europe/Madrid")
    args=parser.parse_args()
    reader=PointWeatherReader(args.data_root,args.stations_file,calendar_timezone=args.calendar_timezone)
    from rainmapper_core.mushroom_map_history import HistoryReader, is_request
    history = HistoryReader(args.data_root, args.stations_file)
    while True:
        line=sys.stdin.readline(32769)
        if not line: break
        if len(line)>32768: raise ValueError("weather_request_too_large")
        request=json.loads(line)
        if request.get("op") == "capabilities":
            try:
                reader._refresh()
                ready=True
            except Exception:
                logging.getLogger(__name__).exception("Prediction map weather initialization failed")
                ready=False
            print(json.dumps({"id":request["id"],"weather_ready":ready}),flush=True)
            continue
        if is_request(request.get('history_request')):
            try:
                result = history.execute(request['history_request'])
            except Exception:
                logging.getLogger(__name__).exception("Historical weather query failed")
                result = {"error": "history_calculation_failed"}
            print(json.dumps({"id":request["id"], **result}, ensure_ascii=False, allow_nan=False), flush=True)
            continue
        try:
            cutoff=min(date.fromisoformat(request["end_day"]),
                       map_today(request.get('calendar_timezone',args.calendar_timezone))-timedelta(days=1))
            weather=reader.lookup(request["lat"],request["lon"],request.get("altitude_m"),
                end_day=cutoff,days=request.get("days",60),water_history=request.get('water_history',False),
                water_capacity_mm=request.get('water_capacity_mm'))
        except Exception:
            # Failure is explicit and does not discard municipality/terrain.
            logging.getLogger(__name__).exception("Prediction map weather query failed")
            weather={"status":"unavailable"}
        print(json.dumps({"id":request["id"],"weather":weather},ensure_ascii=False,allow_nan=False),flush=True)


if __name__=="__main__": main()
