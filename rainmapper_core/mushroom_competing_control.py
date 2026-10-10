"""Small coordinator state for asynchronous historical-selection updates.

Call under the coordinator's existing job lock. Detailed predictions and
validation fits live in the worker cache, never in this control file.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

KIND = 'competing_history_control_v1'
CAPABILITY = 'competing_history_update_v3'
JOB_TYPE = 'worker_competing_history_v1'
MAX_BYTES = 8192
MAX_REQUIRED_KS = 8
DIGEST = re.compile(r'^[0-9a-f]{64}$')


def normalize_ks(values):
    """Bound the distinct configured costs before planning any historical work."""
    from rainmapper_core.mushroom_map_competing import valid_k
    if not isinstance(values, (list, tuple)):
        raise ValueError('invalid_comparison_ks')
    result = set()
    for value in values:
        if not valid_k(value):
            raise ValueError('invalid_comparison_k')
        result.add(float(value))
        if len(result) > MAX_REQUIRED_KS:
            raise ValueError('Historical comparison supports at most 8 distinct configured K values; no work was queued.')
    if not result:
        raise ValueError('invalid_comparison_ks')
    return sorted(result)


def revision(dependencies):
    """Hash explicit dependencies; planning keeps fit history separate from K."""
    if not isinstance(dependencies, dict) or not dependencies or len(dependencies) > 32:
        raise ValueError('invalid_history_dependencies')
    if any(not isinstance(k, str) or len(k) > 64 or not isinstance(v, str) or
           not DIGEST.fullmatch(v) for k, v in dependencies.items()):
        raise ValueError('invalid_history_dependencies')
    raw = json.dumps(dependencies, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return {'kind': KIND, 'desired_revision': '', 'active_revision': '', 'job_id': '',
                'status': 'not_prepared', 'error': '', 'last_seconds': None}
    if len(raw) > MAX_BYTES:
        raise ValueError('history_control_limit')
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('kind') != KIND:
        raise ValueError('invalid_history_control')
    for name in ('desired_revision', 'active_revision'):
        if value.get(name) and not DIGEST.fullmatch(str(value[name])):
            raise ValueError('invalid_history_revision')
    for name in ('required_ks', 'prepared_ks', 'pending_ks', 'job_required_ks', 'job_comparison_ks'):
        if name in value:
            ks = value[name]
            if not isinstance(ks, list) or (ks and normalize_ks(ks) != ks):
                raise ValueError('invalid_history_comparison_ks')
    return value


def write(path, state):
    raw = json.dumps(state, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('history_control_limit')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(raw)
    temporary.replace(path)


def observe(path, dependencies):
    """Record the desired input revision without discarding an active result."""
    wanted = revision(dependencies)
    state = load(path)
    if state['desired_revision'] == wanted:
        return state
    state.update(desired_revision=wanted, dependencies=dependencies, error='')
    if not state.get('job_id'):
        state['status'] = 'ready' if wanted == state['active_revision'] else 'pending'
    write(path, state)
    return state


def needs_job(state):
    return bool(state.get('desired_revision') and not state.get('job_id') and
                (state['desired_revision'] != state.get('active_revision') or state.get('pending_ks')))


def attach_job(path, *, job_id, expected_revision):
    state = load(path)
    if not needs_job(state) or state['desired_revision'] != expected_revision:
        raise ValueError('history_job_duplicate_or_obsolete')
    if not re.fullmatch(r'worker_job_[A-Za-z0-9_-]{8,80}', job_id):
        raise ValueError('invalid_history_job_id')
    state.update(job_id=job_id, job_revision=expected_revision, status='queued')
    write(path, state)
    return state


def accepts_result(state, *, job_id, result_revision):
    return bool(state.get('job_id') == job_id and
                state.get('job_revision') == result_revision == state.get('desired_revision'))


def finish(path, *, job_id, result_revision, seconds, publish=None, error='', receipt_sha256=''):
    """Publish only a current successful result; preserve the prior one otherwise.

    Caller revalidates source revisions before this function and holds the same
    lock throughout the atomic artifact publication and state update.
    """
    state = load(path)
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError('invalid_history_duration')
    receipt = {'job_id': job_id, 'revision': result_revision,
               'sha256': receipt_sha256, 'error': str(error)[:500]}
    # Publication/control and the general job queue are separate atomic files.
    # A delivery retry after a crash between their writes must be harmless.
    if state.get('last_receipt') == receipt:
        return state
    if state.get('job_id') != job_id:
        raise ValueError('history_job_identity')
    accepted = not error and accepts_result(state, job_id=job_id, result_revision=result_revision)
    if accepted:
        if publish is None:
            raise ValueError('history_result_not_verified')
        publish()
        state.update(active_revision=result_revision,
                     updated_at=datetime.now(timezone.utc).isoformat(), status='ready', error='')
    else:
        state.update(status='failed' if error else 'pending', error=str(error)[:500])
    state.update(job_id='', job_revision='', last_seconds=round(seconds, 3), last_receipt=receipt)
    write(path, state)
    return state
