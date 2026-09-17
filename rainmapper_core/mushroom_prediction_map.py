"""Bounded point-query contract and explicit UI demonstration; no GIS or jobs.

The real worker execution endpoint remains unavailable until its dependencies
and geographic models have been validated. Demo results must never be persisted
or presented as scientific predictions.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VIEWER_PATH = "/protected/prediction-map"
API_PATH = "/api/mushrooms/prediction-map"
CONTRACT_ID = "prediction_map_point_v1"
PERMISSION = "can_use_prediction_map"
MAX_REQUEST_BYTES = 32 * 1024
MAX_RESULT_BYTES = 256 * 1024
MAX_SPECIES = 32
HISTORY_DAYS = (7, 15, 30, 60)


def validate_calendar_timezone(value):
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ValueError('invalid_calendar_timezone')
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError('invalid_calendar_timezone') from error
    return value


def can_access(user: object) -> bool:
    """Prediction access is explicit and independent of the user's role."""
    return isinstance(user, dict) and user.get(PERMISSION) is True


def parse_request(raw: bytes) -> dict:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("request_too_large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("invalid_json") from exc
    required = {"contract", "request_id", "point", "start_date", "horizon_days", "history_days"}
    if not isinstance(payload, dict) or set(payload) - required - {"species_ids", "execution", "calendar_timezone"} or not required <= set(payload):
        raise ValueError("invalid_fields")
    if 'calendar_timezone' in payload:
        validate_calendar_timezone(payload['calendar_timezone'])
    if payload.get("execution", "local") not in ("local", "worker"):
        raise ValueError("invalid_execution")
    if payload["contract"] != CONTRACT_ID:
        raise ValueError("unsupported_contract")
    request_id = payload["request_id"]
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", request_id):
        raise ValueError("invalid_request_id")
    point = payload["point"]
    if not isinstance(point, dict) or set(point) != {"lat", "lon"}:
        raise ValueError("invalid_point")
    for key, limit in (("lat", 90), ("lon", 180)):
        value = point[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid_point")
        if not -limit <= value <= limit or not math.isfinite(value):
            raise ValueError("invalid_point")
    if type(payload["horizon_days"]) is not int or not 1 <= payload["horizon_days"] <= 7:
        raise ValueError("invalid_horizon")
    if type(payload["history_days"]) is not int or payload["history_days"] not in HISTORY_DAYS:
        raise ValueError("invalid_history_days")
    start = payload["start_date"]
    if not isinstance(start, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
        raise ValueError("invalid_date")
    try:
        parsed = date.fromisoformat(start)
        if not 2000 <= parsed.year <= 2100:
            raise ValueError
    except ValueError as exc:
        raise ValueError("invalid_date") from exc
    species = payload.get("species_ids", [])
    if not isinstance(species, list) or len(species) > MAX_SPECIES:
        raise ValueError("invalid_species")
    if any(not isinstance(s, str) or not re.fullmatch(r"[a-z0-9_]{1,80}", s) for s in species):
        raise ValueError("invalid_species")
    if len(set(species)) != len(species):
        raise ValueError("duplicate_species")
    return {**payload, "species_ids": species}


def prediction_result(request):
    """Empty scientific envelope; compatible rows come only from point ecology."""
    start=date.fromisoformat(request['start_date'])
    return {'contract':CONTRACT_ID,'request_id':request['request_id'],'point':request['point'],
        'dates':[(start+timedelta(days=i)).isoformat() for i in range(request['horizon_days'])],
        **({'calendar_timezone':request['calendar_timezone']} if 'calendar_timezone' in request else {}),
        'data_mode':'prediction','status':'complete','species':[],
        'provenance':{'engine':'existing_python_predictor','scientifically_validated':False}}


def demo_result(request: dict) -> dict:
    """Return tiny deterministic examples, never inferred from the given point."""
    start = date.fromisoformat(request["start_date"])
    horizon = request["horizon_days"]
    species = [
        {"species_id": "demo_a", "label_key": "demo_a", "status": "available",
         "probabilities": [0.20, 0.30, 0.45, 0.60, 0.55, 0.40, 0.25][:horizon]},
        {"species_id": "demo_b", "label_key": "demo_b", "status": "available",
         "probabilities": [0.45, 0.40, None, 0.30, 0.35, 0.50, 0.65][:horizon]},
        {"species_id": "demo_c", "label_key": "demo_c", "status": "no_model",
         "probabilities": [None] * horizon},
    ]
    if request["species_ids"]:
        if set(request["species_ids"]) - {row["species_id"] for row in species}:
            raise ValueError("unknown_demo_species")
        species = [row for row in species if row["species_id"] in request["species_ids"]]
    result = {
        "contract": CONTRACT_ID, "request_id": request["request_id"],
        **({'calendar_timezone':request['calendar_timezone']} if 'calendar_timezone' in request else {}),
        "data_mode": "simulation", "status": "complete", "point": request["point"],
        "dates": [(start + timedelta(days=i)).isoformat() for i in range(horizon)],
        "species": species,
        "terrain": {"status": "not_connected"},
        "weather": {"status": "not_connected", "history_days": request["history_days"]},
        "provenance": {"fixture": "prediction_map_ui_demo_v1", "scientifically_validated": False},
    }
    # Cardinality is checked before constructing any example; this is the final
    # transport guard. The real producer must do the same before materializing.
    encode_result(result)
    return result


def encode_result(payload: dict) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(raw) > MAX_RESULT_BYTES:
        raise ValueError("result_too_large")
    return raw


def validate_result(result, request):
    """Validate point identity, bounded probabilities and ecological eligibility."""
    expected_dates=[(date.fromisoformat(request['start_date'])+timedelta(days=i)).isoformat()
                    for i in range(request['horizon_days'])]
    if (not isinstance(result,dict) or result.get('contract')!=CONTRACT_ID or
        result.get('request_id')!=request['request_id'] or result.get('point')!=request['point'] or
        result.get('dates')!=expected_dates or
        result.get('execution',{}).get('mode')!=request.get('execution','local') or
        result.get('provenance',{}).get('scientifically_validated') is not False):
        raise ValueError('invalid_result_identity')
    if ('calendar_timezone' in request and result.get('calendar_timezone') != request['calendar_timezone']):
        raise ValueError('invalid_result_calendar_timezone')
    rows=result.get('species')
    if not isinstance(rows,list) or len(rows)>MAX_SPECIES:
        raise ValueError('invalid_result_species')
    if result.get('data_mode')=='simulation':
        if rows!=demo_result(request)['species']:
            raise ValueError('invalid_demo_result')
        return
    if result.get('data_mode')!='prediction' or result.get('provenance',{}).get('engine')!='existing_python_predictor':
        raise ValueError('invalid_result_mode')
    ecology=result.get('ecology',{})
    ecological_rows=ecology.get('species',[])
    if not isinstance(ecological_rows,list) or len(ecological_rows)>MAX_SPECIES:
        raise ValueError('invalid_result_ecology')
    by_id={r.get('species_id'):r for r in ecological_rows}
    if len(by_id)!=len(ecological_rows): raise ValueError('duplicate_ecology_species')
    for row in ecological_rows:
        state = row.get('status')
        if (state not in ('compatible','incompatible','unknown') or
                row.get('daily_statuses') != [state]*len(expected_dates)):
            raise ValueError('invalid_result_ecology')
        phases = row.get('daily_season_phases')
        if (not isinstance(phases,list) or len(phases)!=len(expected_dates) or
                any(p not in ('main','secondary','out_of_season','unknown') for p in phases)):
            raise ValueError('invalid_result_season')
    seen=set()
    for row in rows:
        sid=row.get('species_id'); values=row.get('probabilities'); reasons=row.get('reasons')
        if (not isinstance(sid,str) or not re.fullmatch(r'[a-z0-9_]{1,80}',sid) or sid in seen or
            sid not in by_id or by_id[sid]['status'] != 'compatible' or
            not any(p in ('main','secondary') for p in by_id[sid]['daily_season_phases']) or
            ecology.get('status') != 'available' or ecology.get('abstention_reason') or
            request.get('species_ids') and sid not in request['species_ids'] or
            row.get('status') not in ('available','no_model') or
            not isinstance(values,list) or len(values)!=len(expected_dates) or
            not isinstance(reasons,list) or len(reasons)!=len(expected_dates)):
            raise ValueError('invalid_result_species')
        seen.add(sid)
        if 'applicability' in row or 'applicability_details' in row:
            refs=row.get('applicability'); details=row.get('applicability_details')
            if (not isinstance(refs,list) or len(refs)!=len(expected_dates) or
                    not isinstance(details,list) or len(details)>len(expected_dates) or
                    any(ref is not None and (type(ref) is not int or not 0<=ref<len(details)) for ref in refs)):
                raise ValueError('invalid_result_applicability')
            for detail in details:
                if (not isinstance(detail,dict) or detail.get('status') not in
                        ('within_observed_range','caution','outside_domain') or
                        type(detail.get('outside')) is not int or type(detail.get('total')) is not int or
                        not 0<=detail['outside']<=detail['total'] or
                        not isinstance(detail.get('examples'),list) or len(detail['examples'])>3):
                    raise ValueError('invalid_result_applicability')
                for example in detail['examples']:
                    if (not isinstance(example,dict) or not isinstance(example.get('feature'),str) or
                            len(example['feature'])>128 or any(type(example.get(k)) not in (int,float) or
                            not math.isfinite(example[k]) for k in ('value','training_min','training_max'))):
                        raise ValueError('invalid_result_applicability')
        states=by_id[sid].get('daily_statuses',[])
        if len(states)!=len(expected_dates): raise ValueError('invalid_result_ecology')
        for i,value in enumerate(values):
            if value is None: continue
            if (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1 or
                row['status']!='available' or reasons[i]!='calculated' or states[i]!='compatible' or
                by_id[sid]['daily_season_phases'][i] not in ('main','secondary') or
                ecology.get('status')!='available' or ecology.get('abstention_reason')):
                raise ValueError('invalid_result_probability')
    encode_result(result)
