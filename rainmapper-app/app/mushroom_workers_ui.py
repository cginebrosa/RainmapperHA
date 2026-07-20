from __future__ import annotations

import html
from typing import Any

from mushroom_profiles_ui import ui_label


def _text(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _label(key: str) -> str:
    return ui_label(key)


def _worker_card(
    worker_status: dict[str, object],
    *,
    default_executor: str = "home_assistant",
) -> str:
    payload = worker_status.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    reachable = bool(worker_status.get("reachable"))
    dataset_cache = payload.get("dataset_cache")
    dataset_cache = dataset_cache if isinstance(dataset_cache, dict) else {}
    capabilities = payload.get("capabilities")
    capabilities = capabilities if isinstance(capabilities, list) else []
    worker_id = str(payload.get("worker_id", "") or "")
    is_default = default_executor == f"worker:{worker_id}"
    display_name = str(payload.get("display_name", "") or _label("ui.worker_external"))
    host_name = str(payload.get("host_name", "") or "-")
    architecture = str(payload.get("architecture", "") or "-")
    if reachable:
        status = str(payload.get("status", "unknown"))
        status_text = {
            "idle": _label("ui.worker_idle"),
            "busy": _label("ui.worker_busy"),
            "needs_dataset": _label("ui.worker_needs_dataset"),
        }.get(status, status)
        status_class = "warning" if status == "needs_dataset" else "ok"
    elif worker_status.get("configured"):
        status_text = _label("ui.worker_disconnected")
        status_class = "danger"
    else:
        status_text = _label("ui.worker_not_configured")
        status_class = "muted"
    cache_status = str(dataset_cache.get("status", "-") or "-")
    if cache_status == "valid":
        cache_status = _label("ui.worker_cache_valid")
    cache_detail = ""
    if dataset_cache:
        file_count = dataset_cache.get("file_count", "-")
        size_bytes = int(dataset_cache.get("size_bytes", 0) or 0)
        size_gib = size_bytes / (1024**3)
        cache_detail = f'{file_count} {_label("ui.worker_cache_files")} · {size_gib:.2f} GiB'
    checked_at = str(worker_status.get("checked_at", "-") or "-")
    if "T" in checked_at:
        checked_at = checked_at[:19].replace("T", " ")
    error = str(worker_status.get("error", "") or "")
    pairing_detail = ""
    if "paired" in payload:
        pairing_detail = (
            f'<div><dt>{_text(_label("ui.worker_authentication"))}</dt>'
            f'<dd>{_text(_label("ui.worker_paired") if payload.get("paired") else _label("ui.worker_not_paired"))}</dd></div>'
        )
    claim_probe_available = reachable and payload.get("job_api") in {
        "claim_probe_v0",
        "lifecycle_probe_v0",
        "snapshot_transport_v0",
        "candidate_rebuild_v0",
    }
    if claim_probe_available:
        note = (
            '<div class="worker-note">'
            f'<strong>{_text(_label("ui.worker_probe_available"))}</strong>'
            f'<span>{_text(_label("ui.worker_probe_help"))}</span>'
            '<form method="post" action=""><input type="hidden" name="worker_action" value="probe_worker_claim">'
            f'<input type="hidden" name="worker_id" value="{_text(worker_id)}">'
            f'<button type="submit">{_text(_label("ui.worker_probe_button"))}</button></form>'
            + (
                '<form method="post" action=""><input type="hidden" name="worker_action" value="probe_worker_snapshot_transport">'
                f'<input type="hidden" name="worker_id" value="{_text(worker_id)}">'
                f'<button type="submit">{_text(_label("ui.worker_transport_button"))}</button></form>'
                if payload.get("job_api") in {"snapshot_transport_v0", "candidate_rebuild_v0"}
                else ""
            )
            + (
                '<form method="post" action=""><input type="hidden" name="worker_action" value="run_worker_candidate_rebuild">'
                f'<input type="hidden" name="worker_id" value="{_text(worker_id)}">'
                f'<button type="submit">{_text(_label("ui.worker_candidate_button"))}</button></form>'
                if payload.get("job_api") == "candidate_rebuild_v0"
                else ""
            )
            + "</div>"
        )
    else:
        note = (
            '<div class="worker-note">'
            f'<strong>{_text(_label("ui.worker_job_api_pending"))}</strong>'
            f'<span>{_text(_label("ui.worker_job_api_pending_help"))}</span>'
            "</div>"
        )
    revoke_action = ""
    if payload.get("paired"):
        revoke_action = (
            '<form class="worker-revoke-form" method="post" action="">'
            '<input type="hidden" name="worker_action" value="revoke_worker_pairing">'
            f'<input type="hidden" name="worker_id" value="{_text(worker_id)}">'
            f'<button type="submit" data-confirm="{_text(_label("ui.worker_pairing_revoke_confirm"))}" '
            'onclick="return confirm(this.dataset.confirm)">'
            f'{_text(_label("ui.worker_pairing_revoke"))}</button></form>'
        )
    return f"""
        <article class="worker-card">
          <header><div><span class="worker-kicker">rainmapper-worker</span><h2>{_text(display_name)}{f' <span class="worker-default-badge">{_text(_label("ui.worker_default_badge"))}</span>' if is_default else ''}</h2><span class="worker-host-line">{_text(host_name)} · {_text(architecture)}</span></div><span class="worker-state {status_class}">{_text(status_text)}</span></header>
          <dl>
            <div><dt>{_text(_label('ui.worker_id'))}</dt><dd><code>{_text(worker_id)}</code></dd></div>
            <div><dt>{_text(_label('ui.worker_version'))}</dt><dd>{_text(payload.get('worker_version', '-'))}</dd></div>
            <div><dt>{_text(_label('ui.worker_capabilities'))}</dt><dd>{_text(', '.join(str(item) for item in capabilities) or '-')}</dd></div>
            <div><dt>{_text(_label('ui.worker_dataset_cache'))}</dt><dd>{_text(cache_status)}{f'<small>{_text(cache_detail)}</small>' if cache_detail else ''}</dd></div>
            <div><dt>{_text(_label('ui.worker_last_check'))}</dt><dd>{_text(checked_at)}</dd></div>
            {pairing_detail}
          </dl>
          {f'<details class="worker-error"><summary>{_text(_label("ui.worker_technical_detail"))}</summary><code>{_text(error)}</code></details>' if error else ''}
          {note}
          {revoke_action}
        </article>
        """


def render_worker_cards(
    worker_statuses: list[dict[str, object]],
    *,
    default_executor: str = "home_assistant",
) -> str:
    cards = "".join(
        _worker_card(worker_status, default_executor=default_executor)
        for worker_status in worker_statuses
    )
    if cards:
        return cards
    return f'<article class="worker-card worker-empty-card"><p>{_text(_label("ui.worker_no_registered"))}</p></article>'


def render_worker_choices(
    worker_statuses: list[dict[str, object]],
    *,
    operational_enabled: bool = False,
    default_executor: str = "home_assistant",
    selected_executor: str = "",
) -> str:
    choices = []
    for worker_status in worker_statuses:
        payload = worker_status.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        worker_id = str(payload.get("worker_id", "") or "")
        display_name = str(payload.get("display_name", "") or _label("ui.worker_external"))
        host_name = str(payload.get("host_name", "") or "-")
        available = bool(
            operational_enabled
            and worker_status.get("reachable")
            and payload.get("paired")
            and payload.get("job_api") == "candidate_rebuild_v0"
        )
        detail = (
            _label("ui.worker_operational_local_ready")
            if available
            else _label("ui.worker_job_api_pending")
        )
        executor = f"worker:{worker_id}"
        default_badge = (
            f' <span class="worker-default-badge">{_text(_label("ui.worker_default_badge"))}</span>'
            if executor == default_executor
            else ""
        )
        choices.append(
            f'<label class="worker-choice"><input type="radio" name="executor" value="{_text(executor)}"{" checked" if available and executor == selected_executor else ""}{"" if available else " disabled"}>'
            f'<span class="worker-choice-surface"><span class="worker-choice-icon">W</span><span class="worker-choice-copy"><strong>{_text(display_name)}{default_badge}</strong>'
            f'<small>{_text(host_name)} · {_text(detail)}</small></span><span class="worker-choice-mark">✓</span></span></label>'
        )
    return "".join(choices)


def render_recent_jobs(
    jobs: list[dict[str, object]],
    worker_statuses: list[dict[str, object]] | None = None,
    *,
    operational_enabled: bool = False,
) -> str:
    workers: list[tuple[str, str]] = []
    for worker_status in worker_statuses or []:
        payload = worker_status.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        worker_id = str(payload.get("worker_id", "") or "")
        if worker_id:
            workers.append((worker_id, str(payload.get("display_name", worker_id) or worker_id)))
    job_rows = []
    for job in jobs:
        job_id = str(job.get("job_id", "") or "")
        job_type = str(job.get("job_type", "") or "")
        job_type_text = {
            "worker_claim_probe": _label("ui.worker_claim_probe"),
            "worker_snapshot_transport_probe": _label("ui.worker_transport_probe"),
            "worker_candidate_rebuild": _label("ui.worker_candidate_rebuild"),
        }.get(job_type, _label("ui.worker_rebuild_job"))
        status = str(job.get("status", "unknown") or "unknown")
        status_text = {
            "queued": _label("ui.worker_status_queued"),
            "claimed": _label("ui.worker_status_claimed"),
            "running": _label("ui.worker_status_running"),
            "cancel_requested": _label("ui.worker_status_cancel_requested"),
            "cancelled": _label("ui.worker_status_cancelled"),
            "complete": _label("ui.worker_status_complete"),
            "failed": _label("ui.worker_status_failed"),
        }.get(status, status)
        destination = str(job.get("worker_display_name", "") or "-")
        job_reference = (
            f'<a href="?rebuild_job={_text(job_id)}"><code>{_text(job_id[:12])}</code></a>'
            if job.get("opens_rebuild_modal")
            else f'<code>{_text(job_id[:12])}</code>'
        )
        actions = "-"
        if job_type in {
            "worker_claim_probe",
            "worker_snapshot_transport_probe",
            "worker_candidate_rebuild",
        }:
            action_parts = []
            if status in {"queued", "claimed", "running"}:
                action_parts.append(
                    '<form class="worker-job-action" method="post" action="">'
                    '<input type="hidden" name="worker_action" value="cancel_worker_job">'
                    f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                    f'<button type="submit">{_text(_label("ui.worker_cancel_job"))}</button></form>'
                )
            if status == "running" or (
                status == "cancel_requested" and job.get("cancel_mode") != "force"
            ):
                action_parts.append(
                    '<form class="worker-job-action danger" method="post" action="">'
                    '<input type="hidden" name="worker_action" value="force_cancel_worker_job">'
                    f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                    f'<button type="submit">{_text(_label("ui.worker_force_cancel_job"))}</button></form>'
                )
            elif status == "cancel_requested":
                action_parts.append(
                    f'<span class="meta">{_text(_label("ui.worker_status_force_cancel_requested"))}</span>'
                )
            if (
                operational_enabled
                and job_type == "worker_candidate_rebuild"
                and status == "complete"
                and job.get("promotion_eligible")
                and job.get("promotion_status") != "promoted"
            ):
                action_parts.append(
                    '<form class="worker-job-action" method="post" action="">'
                    '<input type="hidden" name="worker_action" value="promote_worker_candidate">'
                    f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                    f'<button type="submit" data-confirm="{_text(_label("ui.worker_promote_confirm"))}" '
                    'onclick="return confirm(this.dataset.confirm)">'
                    f'{_text(_label("ui.worker_promote_candidate"))}</button></form>'
                )
            if status in {"queued", "claimed"} and not job.get("started_at"):
                alternatives = [(worker_id, name) for worker_id, name in workers if worker_id != job.get("target_worker_id")]
                if alternatives:
                    options = "".join(
                        f'<option value="{_text(worker_id)}">{_text(name)}</option>'
                        for worker_id, name in alternatives
                    )
                    action_parts.append(
                        '<form class="worker-job-action reassign" method="post" action="">'
                        '<input type="hidden" name="worker_action" value="reassign_worker_job">'
                        f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                        f'<select name="new_worker_id" aria-label="{_text(_label("ui.worker_reassign_job"))}">{options}</select>'
                        f'<button type="submit">{_text(_label("ui.worker_reassign_job"))}</button></form>'
                    )
            actions = "".join(action_parts) or "-"
        job_rows.append(
            "<tr>"
            f'<td>{job_reference}</td>'
            f'<td><time datetime="{_text(job.get("created_at", ""))}">{_text(job.get("date_time", "-"))}</time></td>'
            f'<td title="{_text(job_type_text)}">{_text(job_type_text)}</td>'
            f'<td title="{_text(destination)}">{_text(destination)}</td>'
            f'<td><span class="job-status {_text(status)}">{_text(status_text)}</span></td>'
            f'<td title="{_text(job.get("scope", "-"))}">{_text(job.get("scope", "-"))}</td>'
            f'<td title="{_text(job.get("phase", "-"))}">{_text(job.get("phase", "-"))}</td>'
            f'<td>{_text(job.get("overall_percent", 0))}%</td>'
            f'<td>{_text(job.get("elapsed", "-"))}</td>'
            f'<td class="worker-job-actions">{actions}</td>'
            "</tr>"
        )
    if not job_rows:
        return f'<p class="meta">{_text(_label("ui.worker_no_recent_jobs"))}</p>'
    return (
        '<div class="workers-table-wrap"><table><thead><tr>'
        f'<th>{_text(_label("ui.worker_job"))}</th><th>{_text(_label("ui.worker_date_time"))}</th><th>{_text(_label("ui.worker_job_type"))}</th><th>{_text(_label("ui.worker_destination"))}</th>'
        f'<th>{_text(_label("ui.status"))}</th><th>{_text(_label("ui.rebuild_scope"))}</th>'
        f'<th>{_text(_label("ui.worker_phase"))}</th><th>{_text(_label("ui.worker_progress"))}</th><th>{_text(_label("ui.worker_duration"))}</th>'
        f'<th>{_text(_label("ui.worker_actions"))}</th></tr></thead>'
        f'<tbody>{"".join(job_rows)}</tbody></table></div>'
    )


def render_page(
    *,
    worker_statuses: list[dict[str, object]],
    profiles: list[dict[str, object]],
    eligible_observation_count: int,
    pending_species_count: int,
    jobs: list[dict[str, object]],
    pipeline: str,
    operational_enabled: bool = False,
    default_executor: str = "home_assistant",
    selected_scope: str = "all",
    selected_species_id: str = "",
    pairing_required: bool = False,
    flash: str = "",
    flash_error: bool = False,
) -> str:
    if selected_scope not in {"all", "pending", "species"}:
        selected_scope = "all"
    if selected_scope == "pending" and pending_species_count == 0:
        selected_scope = "all"
    default_worker_status = next(
        (
            row
            for row in worker_statuses
            if isinstance(row.get("payload"), dict)
            and f'worker:{row["payload"].get("worker_id", "")}' == default_executor
        ),
        None,
    )
    selected_executor = default_executor
    default_issue = ""
    if default_executor != "home_assistant":
        payload = (
            default_worker_status.get("payload")
            if isinstance(default_worker_status, dict)
            else {}
        )
        payload = payload if isinstance(payload, dict) else {}
        display_name = str(payload.get("display_name", "") or default_executor.removeprefix("worker:"))
        available = bool(
            operational_enabled
            and default_worker_status
            and default_worker_status.get("reachable")
            and payload.get("paired")
            and payload.get("job_api") == "candidate_rebuild_v0"
        )
        if not available:
            default_issue = _label("ui.worker_default_unavailable").replace("{worker}", display_name)
            selected_executor = ""
    worker_cards = render_worker_cards(
        worker_statuses,
        default_executor=default_executor,
    )
    worker_choices = render_worker_choices(
        worker_statuses,
        operational_enabled=operational_enabled,
        default_executor=default_executor,
        selected_executor=selected_executor,
    )
    species_options = []
    for profile in sorted(profiles, key=lambda row: str(row.get("scientific_name", "")).casefold()):
        species_id = str(profile.get("species_id", "") or "").strip()
        if not species_id:
            continue
        scientific_name = str(profile.get("scientific_name", "") or species_id)
        species_options.append(
            f'<option value="{_text(species_id)}"{" selected" if species_id == selected_species_id else ""}>{_text(scientific_name)}</option>'
        )

    default_options = [
        f'<option value="home_assistant"{" selected" if default_executor == "home_assistant" else ""}>{_text(_label("ui.home_assistant"))}</option>'
    ]
    for worker_status in worker_statuses:
        payload = worker_status.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        worker_id = str(payload.get("worker_id", "") or "")
        if not worker_id:
            continue
        executor = f"worker:{worker_id}"
        display_name = str(payload.get("display_name", "") or worker_id)
        status_suffix = "" if worker_status.get("reachable") else f' · {_label("ui.worker_disconnected")}'
        default_options.append(
            f'<option value="{_text(executor)}"{" selected" if executor == default_executor else ""}>{_text(display_name + status_suffix)}</option>'
        )

    recent_jobs = render_recent_jobs(
        jobs,
        worker_statuses,
        operational_enabled=operational_enabled,
    )
    pairing_action = ""
    pairing_security = ""
    if pairing_required:
        pairing_action = f'''
          <form class="worker-toolbar-action" method="post" action="">
            <input type="hidden" name="worker_action" value="create_worker_pairing">
            <button type="submit">{_text(_label("ui.worker_pairing_button"))}</button>
          </form>
        '''
        pairing_security = (
            f'<span class="meta worker-pairing-security" title="{_text(_label("ui.worker_pairing_security"))}">'
            f'{_text(_label("ui.worker_pairing_help"))}</span>'
        )
    show_species = bool(selected_executor) and selected_scope == "species"
    return f"""
    <style>
      .maintenance-top-toolbar{{margin:0 0 8px!important;gap:6px!important}}.maintenance-top-toolbar .button-link{{padding:6px 10px!important;font-size:10px!important}}
      .worker-toolbar-spacer{{flex:1 1 24px}}.worker-toolbar-actions{{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap;margin-left:auto}}
      .worker-toolbar-action,.worker-default-form{{display:flex!important;align-items:center;gap:6px;margin:0!important}}.worker-toolbar-action button,.worker-default-form button{{height:32px;min-height:32px;padding:6px 10px;font-size:10px;font-weight:700}}
      .worker-default-form select{{width:210px;height:32px;min-height:32px;padding:5px 8px;font-size:11px}}
      .workers-head{{display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;margin:0 0 8px;padding:0 0 8px;border-bottom:1px solid var(--line)}}
      .workers-head h1{{margin:0 0 .15rem;font-size:26px}}.workers-head p{{margin:0;color:var(--muted);max-width:760px;font-size:13px}}
      .workers-head-meta{{display:flex;align-items:center;justify-content:flex-end;gap:7px;flex-wrap:wrap;max-width:620px;text-align:right}}.worker-pairing-security{{font-size:10px}}
      .workers-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-items:start;gap:10px;margin:10px 0}}
      .worker-status-cards,.worker-destination-choices{{display:contents}}
      .worker-card{{display:flex;flex-direction:column;min-width:0;border:1px solid var(--line);border-radius:12px;background:var(--card);padding:13px 15px;box-shadow:0 8px 22px rgba(0,0,0,.1)}}
      .worker-card header{{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:9px}}.worker-card h2{{margin:1px 0 0;font-size:18px}}
      .worker-kicker{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
      .worker-default-badge{{display:inline-block;margin-left:4px;padding:1px 5px;border:1px solid var(--accent);border-radius:999px;color:var(--accent);font-size:9px;font-weight:700;vertical-align:middle}}
      .worker-host-line{{display:block;margin-top:2px;color:var(--muted);font-size:11px}}.worker-card code{{font-size:11px;font-weight:600}}
      .worker-state{{border:1px solid currentColor;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:700;background:rgba(255,255,255,.025)}}.worker-state.ok{{color:var(--ok)}}.worker-state.warning{{color:var(--accent)}}.worker-state.danger{{color:var(--danger)}}.worker-state.muted{{color:var(--muted)}}
      .worker-card dl{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 18px;margin:0 0 10px}}.worker-card dl div{{min-width:0}}
      .worker-card dt{{font-size:11px;color:var(--muted)}}.worker-card dd{{margin:1px 0 0;font-size:14px;font-weight:650;overflow-wrap:anywhere}}.worker-card dd small{{display:block;margin-top:1px;color:var(--muted);font-size:11px;font-weight:500}}
      .worker-note{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px 6px;margin-top:0;padding:9px 0 0;border-top:1px solid var(--line)}}.worker-note strong,.worker-note span{{grid-column:1/-1}}.worker-note strong{{font-size:12px}}.worker-note span,.worker-error{{font-size:11px;color:var(--muted)}}.worker-note form{{margin:2px 0 0}}.worker-note button{{width:100%;padding:5px 7px;font-size:11px}}.worker-error{{margin:0 0 8px}}.worker-error summary{{cursor:pointer}}.worker-error code{{display:block;margin-top:5px;white-space:normal;overflow-wrap:anywhere}}
      .worker-revoke-form{{margin:6px 0 0}}.worker-revoke-form button{{width:100%;padding:5px 7px;font-size:11px;color:var(--danger)}}
      .worker-local-note{{margin:0;padding-top:9px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}}
      .worker-empty-card{{align-items:center;justify-content:center;min-height:180px;color:var(--muted);text-align:center}}
      .workers-panel{{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:14px 15px;margin:10px 0;box-shadow:0 8px 22px rgba(0,0,0,.08)}}.workers-panel h2{{margin:0;font-size:17px}}
      .worker-default-issue{{margin:10px 0 0}}
      .worker-panel-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:9px}}
      .worker-metrics{{display:flex;gap:6px;flex-wrap:wrap;margin:0}}.worker-metrics span{{padding:4px 8px;border:1px solid var(--line);border-radius:999px;background:var(--bg);font-size:11px;color:var(--muted)}}.worker-metrics strong{{color:var(--fg)}}
      form.worker-rebuild-form{{display:block;width:100%;margin:0}}
      .worker-form-section{{margin-top:10px}}.worker-form-heading{{display:flex;align-items:baseline;gap:8px;margin-bottom:6px}}.worker-form-heading strong{{font-size:13px}}.worker-form-heading small{{color:var(--muted);font-size:11px}}
      .worker-destination-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
      .worker-rebuild-form .worker-choice,.worker-rebuild-form .worker-scope-choice{{display:block;position:relative;margin:0;min-width:0}}
      .worker-rebuild-form input[type="radio"]{{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;margin:0!important;padding:0!important;opacity:0;pointer-events:none}}
      .worker-choice-surface{{display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:8px;min-height:48px;padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--bg);cursor:pointer;transition:border-color .15s,background .15s}}
      .worker-choice-icon{{display:grid;place-items:center;width:26px;height:26px;border:1px solid var(--line);border-radius:7px;color:var(--muted);font-size:12px;font-weight:800}}
      .worker-choice-copy{{display:flex;flex-direction:column;gap:1px;min-width:0}}.worker-choice-copy strong{{font-size:13px}}.worker-choice-copy small{{color:var(--muted);font-size:11px}}
      .worker-choice-mark{{display:grid;place-items:center;width:17px;height:17px;border:1px solid var(--line);border-radius:50%;color:transparent;font-size:10px}}
      .worker-choice input:checked + .worker-choice-surface{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.18)}}.worker-choice input:checked + .worker-choice-surface .worker-choice-icon{{border-color:var(--accent);color:var(--accent)}}.worker-choice input:checked + .worker-choice-surface .worker-choice-mark{{border-color:var(--accent);background:var(--accent);color:#07151d}}
      .worker-choice input:focus-visible + .worker-choice-surface,.worker-scope-choice input:focus-visible + span{{outline:2px solid var(--accent);outline-offset:2px}}
      .worker-choice input:disabled + .worker-choice-surface{{opacity:.52;cursor:not-allowed}}
      .worker-scope-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}}
      .worker-scope-choice>span{{display:flex;flex-direction:column;gap:1px;min-height:42px;padding:7px 10px;border:1px solid var(--line);border-radius:9px;background:var(--bg);cursor:pointer}}.worker-scope-choice strong{{font-size:12px}}.worker-scope-choice small{{color:var(--muted);font-size:10px}}
      .worker-scope-choice input:checked + span{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.18)}}.worker-scope-choice input:disabled + span{{opacity:.45;cursor:not-allowed}}
      .worker-species-field{{margin-top:8px}}.worker-species-field[hidden]{{display:none}}.worker-species-field label{{display:block;margin:0 0 4px;color:var(--muted);font-size:11px}}.worker-species-field select{{width:100%;max-width:560px}}
      .worker-submit-row{{display:flex;align-items:center;justify-content:flex-end;margin-top:10px;padding-top:9px;border-top:1px solid var(--line)}}.worker-submit-row button{{min-width:165px;padding:7px 10px;font-size:12px}}
      .workers-table-wrap{{overflow:auto;margin-top:5px}}.workers-table-wrap table{{width:100%;min-width:1260px;table-layout:fixed;border-collapse:collapse;font-size:12px}}.workers-table-wrap th,.workers-table-wrap td{{padding:5px 6px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.workers-table-wrap th{{font-size:11px;font-weight:700;color:var(--muted)}}
      .workers-table-wrap th:nth-child(1){{width:105px}}.workers-table-wrap th:nth-child(2){{width:150px}}.workers-table-wrap th:nth-child(3){{width:190px}}.workers-table-wrap th:nth-child(4){{width:105px}}.workers-table-wrap th:nth-child(5){{width:100px}}.workers-table-wrap th:nth-child(6){{width:190px}}.workers-table-wrap th:nth-child(7){{width:190px}}.workers-table-wrap th:nth-child(8){{width:75px}}.workers-table-wrap th:nth-child(9){{width:75px}}.workers-table-wrap th:nth-child(10){{width:145px}}
      .workers-table-wrap code{{font-size:11px}}.workers-table-wrap time{{font-variant-numeric:tabular-nums}}
      .job-status.complete,.job-status.claimed{{color:var(--ok)}}.job-status.queued,.job-status.running{{color:var(--accent)}}.job-status.failed,.job-status.cancelled,.job-status.cancel_requested{{color:var(--danger)}}
      .worker-job-actions{{white-space:normal!important;overflow:visible!important}}.worker-job-action{{display:inline-flex;gap:4px;align-items:center;margin:0 4px 2px 0}}.worker-job-action:last-child{{margin-right:0}}.worker-job-action select{{min-width:90px;max-width:120px;padding:4px;font-size:11px}}.worker-job-action button{{padding:4px 6px;font-size:11px;white-space:nowrap}}
      @media(max-width:1050px){{.worker-toolbar-spacer{{display:none}}.worker-toolbar-actions{{flex-basis:100%;justify-content:flex-start;margin-left:0}}}}
      @media(max-width:850px){{.workers-grid,.worker-destination-grid{{grid-template-columns:1fr}}.worker-scope-grid{{grid-template-columns:1fr}}.worker-panel-head,.workers-head{{display:block}}.worker-metrics,.workers-head-meta{{justify-content:flex-start;margin-top:8px;text-align:left}}.worker-toolbar-actions{{align-items:stretch;flex-direction:column}}.worker-default-form{{align-items:stretch;flex-direction:column}}.worker-default-form select{{width:100%;max-width:none}}.worker-note{{grid-template-columns:1fr}}}}
    </style>
    <div class="catalog-toolbar maintenance-top-toolbar">
      <a class="button-link" href="../">{_text(_label('ui.back'))}</a>
      <a class="button-link" href="?">{_text(_label('ui.worker_refresh'))}</a>
      <a class="button-link" href="./profiles">{_text(_label('ui.species'))}</a>
      <a class="button-link" href="./catalogs">{_text(_label('ui.worker_reference_catalogs'))}</a>
      <a class="button-link" href="./gis-mappings">{_text(_label('ui.worker_gis_mappings'))}</a>
      <a class="button-link" href="./known-sites">{_text(_label('ui.known_sites'))}</a>
      <span class="worker-toolbar-spacer"></span>
      <div class="worker-toolbar-actions">
        <a class="button-link primary-link" href="#new-worker-rebuild">{_text(_label('ui.worker_new_rebuild'))}</a>
        {pairing_action}
        <form class="worker-default-form" method="post" action="">
          <input type="hidden" name="worker_action" value="set_default_executor">
          <select name="default_executor" aria-label="{_text(_label('ui.worker_default_executor'))}" title="{_text(_label('ui.worker_default_executor_help'))}">{''.join(default_options)}</select>
          <button type="submit">{_text(_label('ui.worker_default_save'))}</button>
        </form>
      </div>
    </div>
    <div class="workers-head"><div><h1>{_text(_label('ui.workers_jobs'))}</h1><p>{_text(_label('ui.workers_jobs_help'))}</p></div><div class="workers-head-meta"><span class="meta">{_text(_label('ui.worker_default_executor'))}: <strong>{_text(next((str(row.get('payload', {}).get('display_name', '')) for row in worker_statuses if isinstance(row.get('payload'), dict) and f"worker:{row.get('payload', {}).get('worker_id', '')}" == default_executor), _label('ui.home_assistant')))}</strong></span>{pairing_security}</div></div>
    {f'<div class="catalog-alert{" error" if flash_error else ""}">{_text(flash)}</div>' if flash else ''}
    {f'<div class="catalog-alert error worker-default-issue"><strong>{_text(_label("ui.worker_default_attention"))}</strong><br>{_text(default_issue)}<br>{_text(_label("ui.worker_choose_available"))}</div>' if default_issue else ''}
    <div class="workers-grid">
      <article class="worker-card">
        <header><div><span class="worker-kicker">rainmapper-ha-ui</span><h2>{_text(_label('ui.home_assistant'))}{f' <span class="worker-default-badge">{_text(_label("ui.worker_default_badge"))}</span>' if default_executor == 'home_assistant' else ''}</h2></div><span class="worker-state ok">{_text(_label('ui.worker_available'))}</span></header>
        <dl>
          <div><dt>Pipeline</dt><dd>{_text(pipeline)}</dd></div>
          <div><dt>{_text(_label('ui.worker_role'))}</dt><dd>{_text(_label('ui.worker_fallback'))}</dd></div>
        </dl>
        <p class="worker-local-note">{_text(_label('ui.worker_ha_fallback_help'))}</p>
      </article>
      <div id="worker-status-cards" class="worker-status-cards">{worker_cards}</div>
    </div>
    <section id="new-worker-rebuild" class="workers-panel">
      <div class="worker-panel-head"><h2>{_text(_label('ui.worker_new_rebuild'))}</h2><div class="worker-metrics"><span>{_text(_label('ui.worker_eligible_observations'))}: <strong>{eligible_observation_count}</strong></span><span>{_text(_label('ui.worker_pending_species'))}: <strong>{pending_species_count}</strong></span></div></div>
      <form class="worker-rebuild-form" method="post" action="">
        <input type="hidden" name="worker_action" value="start_rebuild">
        <div class="worker-form-section"><div class="worker-form-heading"><strong>1 · {_text(_label('ui.execute_on'))}</strong><small>{_text(_label('ui.worker_destination_help'))}</small></div>
          <div class="worker-destination-grid">
            <label class="worker-choice"><input type="radio" name="executor" value="home_assistant"{" checked" if selected_executor == "home_assistant" else ""}><span class="worker-choice-surface"><span class="worker-choice-icon">HA</span><span class="worker-choice-copy"><strong>{_text(_label('ui.home_assistant'))}{f' <span class="worker-default-badge">{_text(_label("ui.worker_default_badge"))}</span>' if default_executor == 'home_assistant' else ''}</strong><small>{_text(_label('ui.worker_ha_fallback_help'))}</small></span><span class="worker-choice-mark">✓</span></span></label>
            <div id="worker-destination-choices" class="worker-destination-choices">{worker_choices}</div>
          </div>
        </div>
        <div class="worker-form-section"><div class="worker-form-heading"><strong>2 · {_text(_label('ui.rebuild_scope'))}</strong><small>{_text(_label('ui.worker_scope_help'))}</small></div>
          <div class="worker-scope-grid">
            <label class="worker-scope-choice"><input type="radio" name="scope" value="all"{" checked" if selected_scope == "all" else ""}><span><strong>{_text(_label('ui.rebuild_scope_all'))}</strong><small>{eligible_observation_count} {_text(_label('ui.worker_eligible_observations')).lower()}</small></span></label>
            <label class="worker-scope-choice"><input type="radio" name="scope" value="pending"{" checked" if selected_scope == "pending" else ""}{' disabled' if pending_species_count == 0 else ''} data-base-disabled="{'1' if pending_species_count == 0 else '0'}"><span><strong>{_text(_label('ui.rebuild_scope_pending'))}</strong><small>{pending_species_count} {_text(_label('ui.worker_pending_species')).lower()}</small></span></label>
            <label class="worker-scope-choice"><input type="radio" name="scope" value="species"{" checked" if selected_scope == "species" else ""}><span><strong>{_text(_label('ui.rebuild_scope_species'))}</strong><small>{_text(_label('ui.worker_species'))}</small></span></label>
          </div>
          <div class="worker-species-field"{"" if show_species else " hidden"}><label for="worker-species-id">{_text(_label('ui.worker_species'))}</label><select id="worker-species-id" name="species_id"{"" if show_species else " disabled"}>{''.join(species_options)}</select></div>
        </div>
        <div class="worker-submit-row"><button class="primary" type="submit"{" disabled" if not selected_executor else ""}>{_text(_label('ui.start_rebuild'))}</button></div>
      </form>
    </section>
    <section class="workers-panel"><h2>{_text(_label('ui.worker_recent_jobs'))}</h2><div id="worker-recent-jobs">{recent_jobs}</div></section>
    <script>
    (()=>{{const form=document.querySelector('.worker-rebuild-form');if(!form)return;const select=form.querySelector('select[name="species_id"]');const field=form.querySelector('.worker-species-field');const submit=form.querySelector('button[type="submit"]');const sync=()=>{{const executor=form.querySelector('input[name="executor"]:checked');const scopes=Array.from(form.querySelectorAll('input[name="scope"]'));scopes.forEach(item=>{{item.disabled=item.dataset.baseDisabled==='1';}});const scope=form.querySelector('input[name="scope"]:checked');const show=Boolean(executor&&scope&&scope.value==="species");select.disabled=!show;field.hidden=!show;submit.disabled=!executor||executor.disabled||(show&&!select.value);}};form.addEventListener('change',sync);sync();}})();
    (()=>{{
      const cards=document.getElementById('worker-status-cards');
      const destinations=document.getElementById('worker-destination-choices');
      const jobs=document.getElementById('worker-recent-jobs');
      if(!cards||!destinations||!jobs)return;
      const statusUrl=new URL('../../api/mushrooms/workers/status',window.location.href);
      let timer=0;
      const schedule=()=>{{window.clearTimeout(timer);timer=window.setTimeout(refresh,2000);}};
      const refresh=async()=>{{
        if(document.hidden){{schedule();return;}}
        try{{
          const response=await fetch(statusUrl,{{cache:'no-store',headers:{{Accept:'application/json'}}}});
          if(!response.ok)return;
          const payload=await response.json();
          if(!payload.ok)return;
          const selected=document.querySelector('input[name="executor"]:checked')?.value||'';
          cards.innerHTML=payload.worker_cards_html;
          destinations.innerHTML=payload.worker_choices_html;
          jobs.innerHTML=payload.recent_jobs_html;
          const restored=Array.from(document.querySelectorAll('input[name="executor"]')).find(item=>item.value===selected);
          if(restored&&!restored.disabled)restored.checked=true;
          document.querySelector('.worker-rebuild-form')?.dispatchEvent(new Event('change',{{bubbles:true}}));
        }}catch(error){{void error;}}finally{{schedule();}}
      }};
      document.addEventListener('visibilitychange',()=>{{if(!document.hidden)refresh();}});
      schedule();
    }})();
    </script>
    """
