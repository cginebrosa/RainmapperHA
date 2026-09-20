"""Recheck adopted physics against frozen 22-station map calculations, offline."""
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from rainmapper_core.mushroom_map_hydrology import build_history
from rainmapper_core.mushroom_water_physics import reference_et_series, regulated_history, WATER_STATE_CONTRACT_ID


def main():
    source = ROOT/'docs/mushrooms/SMI/baseline-2026-09-19/local-inputs.json.gz'
    points = json.loads(gzip.decompress(source.read_bytes()))['points']
    checked=[]
    for point in points:
        args=point['inputs']
        old=point['map_weather']['water_balance']
        result=build_history(**args,days=len(old['smi_pct']))
        # Acceptance concerns the exact audited model: preserve numbers and holes.
        for key in ('smi_pct','smi_legacy_pct','balance_mm','et0_mm','et0_methods','smi_reasons'):
            assert result[key] == old[key], (point['code'],key)
        et=reference_et_series(args['interpolated'],args['latitude'],altitude_m=args['altitude_m'],wind_u2_m_s=args['wind_u2_m_s'])
        shared=regulated_history(args['interpolated']['daily_rain_idw_mm'],et['et0_mm'],args['capacity_mm'])
        for storage,pct in zip(shared['storage_mm'][-len(old['smi_pct']):],result['smi_pct']):
            assert (storage is None)==(pct is None)
            if storage is not None: assert abs(storage/args['capacity_mm']*100-pct)<=.00050001
        checked.append({'code':point['code'],'name':point['name'],'days':len(old['smi_pct']),
                        'mass_error_max_mm':shared['mass_error_max_mm'],'equal_to_frozen_map':True})
    paths=['rainmapper_core/'+name+'.py' for name in ('mushroom_water_physics','mushroom_map_hydrology',
        'mushroom_soil_water_state','mushroom_climatic_water_balance','mushroom_ml_area_weather_runtime',
        'mushroom_ml_weather_workspace','mushroom_ml_runtime_trainer','mushroom_ml_runtime_inference')]
    result={'kind':'accepted_smi_parity','contract':WATER_STATE_CONTRACT_ID,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'code_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths},
            'station_count':len(checked),'chart_days':sum(r['days'] for r in checked),'points':checked}
    (Path(__file__).parent/'parity.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ('contract','station_count','chart_days')}))

if __name__=='__main__': main()
