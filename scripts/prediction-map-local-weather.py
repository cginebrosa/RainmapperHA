#!/usr/bin/env python3
"""Read-only, resident weather adapter for the local map preview."""
import argparse
from datetime import date, timedelta
import json
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
    while True:
        line=sys.stdin.readline(2049)
        if not line: break
        if len(line)>2048: raise ValueError("weather_request_too_large")
        request=json.loads(line)
        if request.get("op") == "capabilities":
            try:
                reader._refresh()
                ready=True
            except Exception:
                ready=False
            print(json.dumps({"id":request["id"],"weather_ready":ready}),flush=True)
            continue
        try:
            cutoff=min(date.fromisoformat(request["end_day"]),
                       map_today(request.get('calendar_timezone',args.calendar_timezone))-timedelta(days=1))
            weather=reader.lookup(request["lat"],request["lon"],request.get("altitude_m"),
                end_day=cutoff,days=request.get("days",60))
        except Exception as error:
            # Failure is explicit and does not discard municipality/terrain.
            print(f"Weather unavailable: {type(error).__name__}",file=sys.stderr)
            weather={"status":"unavailable"}
        print(json.dumps({"id":request["id"],"weather":weather},ensure_ascii=False,allow_nan=False),flush=True)


if __name__=="__main__": main()
