#!/usr/bin/env python3
"""Resident offline point-model adapter; no jobs or dataset mutation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_model_runtime import PointModelRuntime


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('registry-path','models-root','profiles-path','data-root','stations-file'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--calendar-timezone',default='Europe/Madrid')
    args=vars(p.parse_args()); runtime=PointModelRuntime(**args)
    while line:=sys.stdin.readline(65537):
        if len(line)>65536: raise ValueError('model_request_limit')
        request=json.loads(line)
        if request.get('op') == 'capabilities':
            try:
                runtime._refresh()
                ready = True
            except Exception:
                ready = False
            print(json.dumps({'id':request['id'],'model_ready':ready}),flush=True)
            continue
        try:
            result=runtime.predict(request['request'],request['geography'])
        except Exception as error:
            print(f'Point model unavailable: {type(error).__name__}: {error}',file=sys.stderr)
            result={'data_mode':'prediction','species':[], 'model_status':'unavailable',
                'provenance':{'engine':'existing_python_predictor','scientifically_validated':False}}
        raw=json.dumps({'id':request['id'],**result},allow_nan=False)
        if len(raw.encode())>32768: raise ValueError('model_response_limit')
        print(raw,flush=True)

if __name__=='__main__': main()
