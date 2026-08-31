from __future__ import annotations

import hashlib
import html
import json
from typing import Any

from mushroom_profiles_ui import ui_label
from rainmapper_core import mushroom_worker_registry


def _text(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _label(key: str) -> str:
    return ui_label(key)


def refresh_signature(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _metric(value: object, digits: int = 4) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.{digits}f}"
    return "—"


def _seconds(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return f"{float(value):.1f}s"
    return "—"


def render_benchmark_report(
    report: dict[str, object] | None,
    *,
    error: str = "",
) -> str:
    if error:
        return (
            '<section class="workers-panel benchmark-report-panel">'
            f'<div class="catalog-alert error">{_text(error)}</div></section>'
        )
    if not isinstance(report, dict):
        return ""
    selection = report.get("selection")
    selection = selection if isinstance(selection, dict) else {}
    summary = report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    duration = report.get("duration_summary")
    duration = duration if isinstance(duration, dict) else {}
    metrics = report.get("metrics")
    metrics = metrics if isinstance(metrics, list) else []
    rows = []
    for raw in metrics:
        row = raw if isinstance(raw, dict) else {}
        support = f'{int(row.get("n_test", 0) or 0)}/{int(row.get("n_test_total", 0) or 0)}'
        rows.append(
            "<tr>"
            f'<td title="{_text(row.get("version_id"))}">{_text(row.get("version_id"))}</td>'
            f'<td title="{_text(row.get("profile_id"))}">{_text(row.get("profile_id"))}</td>'
            f'<td title="{_text(row.get("species_id"))}">{_text(row.get("species_id"))}</td>'
            f'<td title="{_text(row.get("temporal_family"))} · h{_text(row.get("horizon_days"))}">{_text(row.get("temporal_family"))} · h{_text(row.get("horizon_days"))}</td>'
            f'<td title="{_text(row.get("estimator_id"))}">{_text(row.get("estimator_id"))}</td>'
            f'<td>{_metric(row.get("brier_score"))}</td>'
            f'<td>{_metric(row.get("prevalence_brier_score"))}</td>'
            f'<td>{_metric(row.get("brier_delta_vs_prevalence"))}</td>'
            f'<td>{_metric(row.get("roc_auc"))}</td>'
            f'<td>{_metric(row.get("expected_calibration_error"))}</td>'
            f'<td>{_text(support)} · {_text(row.get("test_positive_count", 0))}/'
            f'{_text(row.get("test_negative_count", 0))}</td>'
            f'<td>{_text(row.get("abstention_count", 0))}</td>'
            f'<td>{_metric(row.get("fit_duration_seconds"), 3)} s</td>'
            f'<td title="{_text(row.get("fit_status"))}{" · " + _text(row.get("fit_failure_reason")) if row.get("fit_failure_reason") else ""}">{_text(row.get("fit_status"))}'
            f'{" · " + _text(row.get("fit_failure_reason")) if row.get("fit_failure_reason") else ""}</td>'
            "</tr>"
        )
    failures = report.get("fit_failures")
    failures = failures if isinstance(failures, list) else []
    failure_html = ""
    if failures:
        failure_html = (
            '<details class="benchmark-failures"><summary>'
            + _text(_label("ui.worker_benchmark_failures"))
            + f" ({len(failures)})</summary><ul>"
            + "".join(
                f'<li><code>{_text((row.get("artifact_ref") or {}).get("version_id"))}/'
                f'{_text((row.get("artifact_ref") or {}).get("profile_id"))}/'
                f'{_text((row.get("artifact_ref") or {}).get("species_id"))}/'
                f'{_text((row.get("artifact_ref") or {}).get("estimator_id"))}</code> — '
                f'{_text(row.get("reason"))}</li>'
                for row in failures
                if isinstance(row, dict) and isinstance(row.get("artifact_ref"), dict)
            )
            + "</ul></details>"
        )
    profiles = selection.get("profiles")
    profiles = profiles if isinstance(profiles, list) else []
    profile_names = ", ".join(
        str(row.get("profile_name") or row.get("profile_id") or "")
        for row in profiles
        if isinstance(row, dict)
    )
    return f'''
    <section class="workers-panel benchmark-report-panel">
      <div class="worker-panel-head"><h2>{_text(_label('ui.worker_benchmark_report'))}</h2><a class="button-link" href="./workers">{_text(_label('ui.close'))}</a></div>
      <dl class="benchmark-report-summary">
        <div><dt>Batch</dt><dd><code>{_text(report.get('batch_id'))}</code></dd></div>
        <div><dt>Snapshot</dt><dd><code>{_text(report.get('snapshot_id'))}</code></dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_profiles'))}</dt><dd>{_text(profile_names)}</dd></div>
        <div><dt>{_text(_label('ui.species'))}</dt><dd>{_text(str(summary.get('species_count', 0)))}</dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_fits'))}</dt><dd>{_text(str(summary.get('successful_fit_count', 0)))} / {_text(str(summary.get('planned_fit_count', 0)))}</dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_failed_fits'))}</dt><dd>{_text(str(summary.get('failed_fit_count', 0)))}</dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_metrics').capitalize())}</dt><dd>{_text(str(summary.get('metric_count', 0)))}</dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_predictions'))}</dt><dd>{_text(str(summary.get('holdout_prediction_count', 0)))}</dd></div>
        <div><dt>{_text(_label('ui.worker_benchmark_fit_time'))}</dt><dd>{_metric(duration.get('total_fit_seconds'), 3)} s</dd></div>
      </dl>
      <p class="meta">{_text(_label('ui.worker_benchmark_no_average'))}</p>
      <div class="workers-table-wrap benchmark-report-table"><table><thead><tr>
        <th>Version</th><th>Profile</th><th>Species</th><th>Contract</th><th>Estimator</th>
        <th>Brier</th><th>Prevalence</th><th>Delta</th><th>ROC-AUC</th><th>ECE</th>
        <th>{_text(_label('ui.worker_benchmark_support'))}</th><th>{_text(_label('ui.worker_benchmark_abstentions'))}</th>
        <th>{_text(_label('ui.worker_benchmark_fit_time'))}</th><th>{_text(_label('ui.status'))}</th>
      </tr></thead><tbody>{''.join(rows)}</tbody></table></div>
      {failure_html}
    </section>'''


def render_benchmark_history(reports: list[dict[str, object]]) -> str:
    if not reports:
        return f'<p class="meta">{_text(_label("ui.worker_benchmark_history_empty"))}</p>'
    history_rows = []
    for row in reports:
        summary = row.get("summary")
        summary = summary if isinstance(summary, dict) else {}
        selection = row.get("selection")
        selection = selection if isinstance(selection, dict) else {}
        profiles = selection.get("profiles")
        profile_names = [
            str(profile.get("profile_name") or profile.get("profile_key") or "")
            for profile in profiles or []
            if isinstance(profile, dict)
            and str(profile.get("profile_name") or profile.get("profile_key") or "")
        ]
        evidence = []
        planned = summary.get("planned_fit_count")
        successful = summary.get("successful_fit_count")
        if planned is not None and successful is not None:
            evidence.append(f"{successful}/{planned} fits")
        failed = summary.get("failed_fit_count")
        if failed is not None:
            evidence.append(f"{failed} failures")
        metrics = summary.get("metric_count")
        if metrics is not None:
            evidence.append(f'{metrics} {_label("ui.worker_benchmark_metrics")}')
        predictions = summary.get("holdout_prediction_count")
        if predictions is not None:
            evidence.append(f"{predictions} hold-out")
        profile_summary = ", ".join(profile_names) or (
            f'{summary.get("profile_count", 0)} {_label("ui.worker_benchmark_profiles").lower()}'
        )
        batch_id = str(row.get("batch_id") or "")
        delete_form = (
            '<form class="worker-revoke-form benchmark-history-delete" method="post" action="">'
            '<input type="hidden" name="worker_action" value="delete_benchmark">'
            f'<input type="hidden" name="batch_id" value="{_text(batch_id)}">'
            f'<button type="submit" data-confirm="{_text(_label("ui.worker_benchmark_delete_confirm"))}" '
            'onclick="event.stopPropagation(); return confirm(this.dataset.confirm)">'
            f'{_text(_label("ui.worker_benchmark_delete"))}</button></form>'
        )
        history_rows.append(
            '<div class="benchmark-history-item">'
            '<a class="benchmark-history-row" href="?benchmark='
            + _text(batch_id)
            + '"><span><strong>'
            + _text(profile_summary)
            + '</strong><small>'
            + _text(row.get("created_at"))
            + ' · '
            + _text(batch_id)
            + '</small></span><span>'
            + _text(" · ".join(evidence))
            + '</span></a>'
            + delete_form
            + '</div>'
        )
    return '<div class="benchmark-history benchmark-history-scroll" data-preserve-refresh-scroll>' + "".join(history_rows) + "</div>"


def render_worker_flash(
    message: str = "",
    *,
    error: bool = False,
) -> str:
    if not message:
        return ""
    return f'<div class="catalog-alert{" error" if error else ""}">{_text(message)}</div>'


def worker_cards_refresh_signature(
    worker_statuses: list[dict[str, object]],
    *,
    default_executor: str = "home_assistant",
) -> str:
    stable_statuses = [
        {key: value for key, value in worker_status.items() if key != "checked_at"}
        for worker_status in worker_statuses
    ]
    return refresh_signature(
        {"default_executor": default_executor, "worker_statuses": stable_statuses}
    )


def format_worker_checked_at(value: object) -> str:
    checked_at = str(value or "-")
    return checked_at[:19].replace("T", " ") if "T" in checked_at else checked_at


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
    checked_at = format_worker_checked_at(worker_status.get("checked_at", "-"))
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
                '<form method="post" action=""><input type="hidden" name="worker_action" value="run_worker_ml_multiversion">'
                f'<input type="hidden" name="worker_id" value="{_text(worker_id)}">'
                f'<button type="submit">{_text(_label("ui.worker_run_scientific_benchmark"))}</button></form>'
                if {
                    mushroom_worker_registry.ML_MULTIVERSION_TRAINING_CAPABILITY,
                    mushroom_worker_registry.ML_JOB_PURPOSE_CAPABILITY,
                    mushroom_worker_registry.ML_BENCHMARK_REPORT_CAPABILITY,
                }.issubset(set(payload.get("capabilities") or []))
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
    worker_tools = (
        '<details class="worker-tools">'
        f'<summary>{_text(_label("ui.worker_tools"))}</summary>'
        '<div class="worker-technical-identity">'
        f'<span>{_text(_label("ui.worker_id"))}: <code>{_text(worker_id)}</code></span>'
        f'<span>{_text(_label("ui.worker_version"))}: {_text(payload.get("worker_version", "-"))}</span>'
        '</div>'
        f'{note}{revoke_action}</details>'
    )
    return f"""
        <article class="worker-card" data-worker-id="{_text(worker_id)}">
          <header><div><span class="worker-kicker">rainmapper-worker</span><h2>{_text(display_name)}{f' <span class="worker-default-badge">{_text(_label("ui.worker_default_badge"))}</span>' if is_default else ''}</h2><span class="worker-host-line">{_text(host_name)} · {_text(architecture)}</span></div><span class="worker-state {status_class}">{_text(status_text)}</span></header>
          <dl>
            <div><dt>{_text(_label('ui.worker_capabilities'))}</dt><dd>{_text(', '.join(str(item) for item in capabilities) or '-')}</dd></div>
            <div><dt>{_text(_label('ui.worker_dataset_cache'))}</dt><dd>{_text(cache_status)}{f'<small>{_text(cache_detail)}</small>' if cache_detail else ''}</dd></div>
            <div><dt>{_text(_label('ui.worker_last_check'))}</dt><dd data-worker-last-check>{_text(checked_at)}</dd></div>
            {pairing_detail}
          </dl>
          {f'<details class="worker-error"><summary>{_text(_label("ui.worker_technical_detail"))}</summary><code>{_text(error)}</code></details>' if error else ''}
          {worker_tools}
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
    local_ha_compute_enabled: bool = False,
) -> str:
    choices = []
    if local_ha_compute_enabled:
        choices.append(
            f'<label class="worker-choice"><input type="radio" name="executor" value="home_assistant"{" checked" if selected_executor == "home_assistant" else ""}>'
            f'<span class="worker-choice-surface"><span class="worker-choice-icon">HA</span><span class="worker-choice-copy"><strong>{_text(_label("ui.worker_local_ha_executor"))}</strong>'
            f'<small>{_text(_label("ui.worker_local_ha_executor_help"))}</small></span><span class="worker-choice-mark">✓</span></span></label>'
        )
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
            and "ml_job_purpose_v1" in set(payload.get("capabilities") or [])
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
    completed_operational_parents = {
        str(job.get("triggered_by_job_id", ""))
        for job in jobs
        if job.get("job_type") == "worker_ml_multiversion_v1"
        and job.get("job_purpose") == "operational"
        and job.get("status") == "complete"
        and job.get("triggered_by_job_id")
    }
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
            "worker_ml_train_v0": _label("ui.worker_ml_train_job_type"),
            "worker_ml_multiversion_v1": (
                _label("ui.worker_operational_training_job")
                if job.get("job_purpose") == "operational"
                else _label("ui.worker_scientific_benchmark_job")
            ),
            "worker_predictor_v1": _label("ui.worker_predictor_job_type"),
            "worker_predictor_precompute_v1": _label(
                "ui.worker_predictor_precompute_job_type"
            ),
            "local_predictor_precompute": _label(
                "ui.worker_predictor_precompute_job_type"
            ),
            "local_full_update": _label("ui.worker_local_full_update_job"),
            "local_ml_benchmark": _label("ui.worker_scientific_benchmark_job"),
        }.get(job_type, _label("ui.worker_rebuild_job"))
        if job.get("job_purpose") == "benchmark" and job.get("profile_keys"):
            profile_labels = job.get("profile_labels")
            exact_profiles = (
                [str(value) for value in profile_labels]
                if isinstance(profile_labels, list) and profile_labels
                else [str(value) for value in job.get("profile_keys", [])]
            )
            job_type_text = "Benchmark · " + ", ".join(exact_profiles)
        status = str(job.get("status", "unknown") or "unknown")
        status_text = {
            "queued": _label("ui.worker_status_queued"),
            "claimed": _label("ui.worker_status_claimed"),
            "running": _label("ui.worker_status_running"),
            "cancel_requested": _label("ui.worker_status_cancel_requested"),
            "cancelled": _label("ui.worker_status_cancelled"),
            "complete": _label("ui.worker_status_complete"),
            "failed": _label("ui.worker_status_failed"),
            "superseded": _label("ui.worker_status_superseded"),
        }.get(status, status)
        promotion_status = str(job.get("promotion_status", "") or "")
        display_status = status
        if promotion_status == "promoting":
            if bool(job.get("promotion_active", True)):
                display_status = "running"
                status_text = _label("ui.worker_promoting")
            else:
                display_status = "failed"
                status_text = _label("ui.worker_promotion_interrupted")
        discard_status = str(job.get("discard_status", "") or "")
        if discard_status == "requested":
            display_status = "running"
            status_text = _label("ui.worker_candidate_discarding")
        elif discard_status == "acknowledged":
            display_status = "complete"
            status_text = _label("ui.worker_candidate_discarded")
        promotion_percent = max(0, min(100, int(job.get("promotion_percent", 0) or 0)))
        progress_html = (
            '<div class="worker-promotion-progress">'
            f'<progress max="100" value="{promotion_percent}" aria-label="{_text(_label("ui.worker_promotion_progress"))}"></progress>'
            f'<span>{promotion_percent}%</span></div>'
            if promotion_status == "promoting" and bool(job.get("promotion_active", True))
            else f'{_text(job.get("overall_percent", 0))}%'
        )
        destination = str(job.get("worker_display_name", "") or "-")
        opens_progress_modal = bool(job.get("opens_rebuild_modal")) or (
            job_type == "worker_predictor_precompute_v1"
        )
        local_job = bool(job.get("opens_rebuild_modal")) or job.get("executor") == "home_assistant"
        job_display_name = _label("ui.worker_local_job") if local_job else job_id[:12]
        job_reference = (
            f'<a href="?rebuild_job={_text(job_id)}" title="{_text(job_id)}"><strong>{_text(job_display_name)}</strong></a>'
            if opens_progress_modal
            else f'<code title="{_text(job_id)}">{_text(job_display_name)}</code>'
        )
        actions = "-"
        result = job.get("result")
        result = result if isinstance(result, dict) else {}
        precompute_telemetry = job.get("precompute_telemetry")
        precompute_telemetry = (
            precompute_telemetry if isinstance(precompute_telemetry, dict) else {}
        )
        precompute_timing_parts = []
        if job_type == "worker_predictor_precompute_v1":
            for label_key, telemetry_key in (
                ("ui.worker_precompute_runtime_sync", "runtime_sync_seconds"),
                ("ui.worker_precompute_calculation", "calculation_seconds"),
                ("ui.worker_precompute_transfer", "estimated_transfer_seconds"),
                ("ui.worker_precompute_ha_activation", "ha_publish_seconds"),
                ("ui.worker_precompute_worker_activation", "worker_activation_seconds"),
            ):
                if telemetry_key in precompute_telemetry:
                    precompute_timing_parts.append(
                        f"{_label(label_key)} {_seconds(precompute_telemetry.get(telemetry_key))}"
                    )
        precompute_timing_text = " · ".join(precompute_timing_parts)
        duration_html = _text(job.get("elapsed", "-"))
        if precompute_timing_text:
            duration_html += (
                f'<small class="meta" title="{_text(precompute_timing_text)}">'
                f'{_text(precompute_timing_text)}</small>'
            )
        benchmark_batch_id = str(result.get("batch_id", "") or "")
        profile_keys = job.get("profile_keys")
        profile_count = len(profile_keys) if isinstance(profile_keys, list) else 0
        result_summary = result.get("summary")
        result_summary = result_summary if isinstance(result_summary, dict) else {}
        profile_count = profile_count or int(result_summary.get("profile_count", 0) or 0)
        benchmark_action_label = _label(
            "ui.worker_view_report" if profile_count == 1 else "ui.worker_view_comparison"
        )
        benchmark_action = (
            f'<a class="button-link" data-benchmark-report-link href="?benchmark={_text(benchmark_batch_id)}">{_text(benchmark_action_label)}</a>'
            if status == "complete"
            and job.get("job_purpose") == "benchmark"
            and result.get("benchmark_report_available") is True
            and benchmark_batch_id
            else ""
        )
        if job_type in {
            "worker_claim_probe",
            "worker_snapshot_transport_probe",
            "worker_candidate_rebuild",
            "worker_ml_train_v0",
            "worker_ml_multiversion_v1",
            "worker_predictor_v1",
            "worker_predictor_precompute_v1",
        }:
            action_parts = []
            if benchmark_action:
                action_parts.append(benchmark_action)
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
                action_parts.append(
                    '<form class="worker-job-action danger" method="post" action="">'
                    '<input type="hidden" name="worker_action" value="abandon_worker_job">'
                    f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                    f'<button type="submit" data-confirm="{_text(_label("ui.worker_abandon_confirm"))}" '
                    'onclick="return confirm(this.dataset.confirm)">'
                    f'{_text(_label("ui.worker_abandon_job"))}</button></form>'
                )
            if (
                operational_enabled
                and job_type == "worker_ml_train_v0"
                and status == "complete"
                and job.get("promotion_eligible")
                and promotion_status not in {"promoting", "promoted"}
            ):
                full_update = bool(job.get("triggered_by_job_id"))
                if full_update and job_id in completed_operational_parents:
                    action_parts.append(
                        '<form class="worker-job-action" method="post" action="">'
                        '<input type="hidden" name="worker_action" value="promote_full_update">'
                        f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                        f'<button type="submit" data-confirm="{_text(_label("ui.worker_promote_full_update_confirm"))}" '
                        'onclick="return confirm(this.dataset.confirm)">'
                        f'{_text(_label("ui.worker_promote_full_update"))}</button></form>'
                    )
            elif promotion_status == "promoting":
                action_parts.append(
                    f'<span class="meta">{_text(_label("ui.worker_promoting"))}</span>'
                )
            if (
                job_type == "worker_candidate_rebuild"
                and status in {"complete", "cancelled", "failed"}
                and promotion_status not in {"promoted", "discarding"}
                and (promotion_status != "promoting" or not bool(job.get("promotion_active", True)))
                and discard_status not in {"requested", "acknowledged"}
            ):
                action_parts.append(
                    '<button type="button" class="danger" data-discard-worker-candidate '
                    f'data-job-id="{_text(job_id)}" data-job-label="{_text(job.get("scope", job_id))}">'
                    f'{_text(_label("ui.worker_discard_candidate"))}</button>'
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
        elif job_type == "local_predictor_precompute" and status == "running":
            actions = (
                '<form class="worker-job-action danger" method="post" action="">'
                '<input type="hidden" name="worker_action" value="cancel_local_precompute">'
                f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                f'<button type="submit">{_text(_label("ui.worker_cancel_job"))}</button></form>'
            )
        elif job_type == "local_ml_benchmark" and status == "running":
            actions = (
                '<form class="worker-job-action danger" method="post" action="">'
                '<input type="hidden" name="worker_action" value="cancel_local_benchmark">'
                f'<input type="hidden" name="job_id" value="{_text(job_id)}">'
                f'<button type="submit">{_text(_label("ui.worker_cancel_job"))}</button></form>'
            )
        elif benchmark_action:
            actions = benchmark_action
        scope_text = str(job.get("scope", "-") or "-")
        if job.get("job_purpose") == "benchmark" and result_summary:
            scope_parts = []
            planned = result_summary.get("planned_fit_count")
            successful = result_summary.get("successful_fit_count")
            if planned is not None and successful is not None:
                scope_parts.append(f"{successful}/{planned} fits")
            if result_summary.get("failed_fit_count") is not None:
                scope_parts.append(f'{result_summary.get("failed_fit_count")} failures')
            if result_summary.get("metric_count") is not None:
                scope_parts.append(f'{result_summary.get("metric_count")} metrics')
            if result_summary.get("holdout_prediction_count") is not None:
                scope_parts.append(f'{result_summary.get("holdout_prediction_count")} hold-out')
            scope_text = " · ".join(scope_parts) or scope_text
        job_rows.append(
            f'<tr data-job-id="{_text(job_id)}" id="job-{_text(job_id)}" data-job-purpose="{_text(job.get("job_purpose", ""))}">'
            f'<td data-sort-value="{_text(job_display_name)}">{job_reference}</td>'
            f'<td data-sort-value="{_text(job.get("sort_timestamp", job.get("created_at", "")))}"><time datetime="{_text(job.get("created_at", ""))}">{_text(job.get("date_time", "-"))}</time></td>'
            f'<td data-sort-value="{_text(job_type_text)}" title="{_text(job_type_text)}">{_text(job_type_text)}</td>'
            f'<td data-sort-value="{_text(destination)}" title="{_text(destination)}">{_text(destination)}</td>'
            f'<td data-sort-value="{_text(status_text)}"><span class="job-status {_text(display_status)}">{_text(status_text)}</span></td>'
            f'<td data-sort-value="{_text(scope_text)}" title="{_text(scope_text)}">{_text(scope_text)}</td>'
            f'<td data-sort-value="{_text(job.get("phase", "-"))}" title="{_text(job.get("phase", "-"))}">{_text(job.get("phase", "-"))}</td>'
            f'<td data-sort-value="{promotion_percent if promotion_status == "promoting" else _text(job.get("overall_percent", 0))}">{progress_html}</td>'
            f'<td data-sort-value="{_text(job.get("elapsed_seconds", 0))}">{duration_html}</td>'
            f'<td class="worker-job-actions" data-sort-value="{1 if actions != "-" else 0}">{actions}</td>'
            "</tr>"
        )
    if not job_rows:
        return f'<p class="meta">{_text(_label("ui.worker_no_recent_jobs"))}</p>'
    return (
        '<div class="workers-table-wrap worker-jobs-history" data-preserve-refresh-scroll><table class="worker-jobs-table" data-sortable-worker-jobs data-sort-column="1" data-sort-direction="desc"><thead><tr>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="0" data-worker-sort-type="text">{_text(_label("ui.worker_job"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="descending"><button class="worker-sort-button" type="button" data-worker-sort-column="1" data-worker-sort-type="time">{_text(_label("ui.worker_date_time"))}<span aria-hidden="true">↓</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="2" data-worker-sort-type="text">{_text(_label("ui.worker_job_type"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="3" data-worker-sort-type="text">{_text(_label("ui.worker_destination"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="4" data-worker-sort-type="text">{_text(_label("ui.status"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="5" data-worker-sort-type="text">{_text(_label("ui.rebuild_scope"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="6" data-worker-sort-type="text">{_text(_label("ui.worker_phase"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="7" data-worker-sort-type="number">{_text(_label("ui.worker_progress"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="8" data-worker-sort-type="number">{_text(_label("ui.worker_duration"))}<span aria-hidden="true">↕</span></button></th>'
        f'<th aria-sort="none"><button class="worker-sort-button" type="button" data-worker-sort-column="9" data-worker-sort-type="number">{_text(_label("ui.worker_actions"))}<span aria-hidden="true">↕</span></button></th></tr></thead>'
        f'<tbody>{"".join(job_rows)}</tbody></table></div>'
    )


def render_page(
    *,
    worker_statuses: list[dict[str, object]],
    eligible_observation_count: int,
    jobs: list[dict[str, object]],
    pipeline: str,
    operational_enabled: bool = False,
    local_ha_compute_enabled: bool = False,
    default_executor: str = "home_assistant",
    pairing_required: bool = False,
    flash: str = "",
    flash_error: bool = False,
    flash_clear_when_idle: bool = False,
    operational_versions: list[dict[str, object]] | None = None,
    benchmark_profiles: list[dict[str, str]] | None = None,
    selected_benchmark_profiles: list[str] | None = None,
    benchmark_history: list[dict[str, object]] | None = None,
    selected_benchmark_report: dict[str, object] | None = None,
    benchmark_report_error: str = "",
    precompute_summary: dict[str, object] | None = None,
) -> str:
    default_worker_status = next(
        (
            row
            for row in worker_statuses
            if isinstance(row.get("payload"), dict)
            and f'worker:{row["payload"].get("worker_id", "")}' == default_executor
        ),
        None,
    )
    selected_executor = (
        "home_assistant"
        if local_ha_compute_enabled and default_executor == "home_assistant"
        else default_executor if default_executor.startswith("worker:") else ""
    )
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
            and "ml_job_purpose_v1" in set(payload.get("capabilities") or [])
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
        local_ha_compute_enabled=local_ha_compute_enabled,
    )
    if not selected_executor:
        for worker_status in worker_statuses:
            payload = worker_status.get("payload")
            payload = payload if isinstance(payload, dict) else {}
            if (
                operational_enabled
                and worker_status.get("reachable")
                and payload.get("paired")
                and payload.get("job_api") == "candidate_rebuild_v0"
                and "ml_job_purpose_v1" in set(payload.get("capabilities") or [])
            ):
                selected_executor = f'worker:{payload.get("worker_id", "")}'
                break

    default_options = (
        [
            f'<option value="home_assistant"{" selected" if default_executor == "home_assistant" else ""}>{_text(_label("ui.worker_local_ha_executor"))}</option>'
        ]
        if local_ha_compute_enabled
        else []
    )
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

    benchmark_options = (
        [
            f'<option value="home_assistant"{" selected" if default_executor == "home_assistant" else ""}>{_text(_label("ui.worker_local_ha_executor"))}</option>'
        ]
        if local_ha_compute_enabled
        else []
    )
    for worker_status in worker_statuses:
        payload = worker_status.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        worker_id = str(payload.get("worker_id", "") or "")
        if (
            not worker_id
            or not worker_status.get("reachable")
            or not payload.get("paired")
            or mushroom_worker_registry.ML_MULTIVERSION_TRAINING_CAPABILITY
            not in set(payload.get("capabilities") or [])
            or mushroom_worker_registry.ML_JOB_PURPOSE_CAPABILITY
            not in set(payload.get("capabilities") or [])
            or mushroom_worker_registry.ML_BENCHMARK_REPORT_CAPABILITY
            not in set(payload.get("capabilities") or [])
        ):
            continue
        executor = f"worker:{worker_id}"
        benchmark_options.append(
            f'<option value="{_text(executor)}"{" selected" if executor == default_executor else ""}>{_text(str(payload.get("display_name", worker_id) or worker_id))}</option>'
        )
    selected_benchmark_profile_keys = set(selected_benchmark_profiles or [])
    benchmark_profile_controls = "".join(
        '<label class="benchmark-profile-choice">'
        f'<input type="checkbox" name="benchmark_profile" value="{_text(row.get("profile_key"))}"'
        f'{" checked" if row.get("profile_key") in selected_benchmark_profile_keys else ""}>'
        '<span class="benchmark-profile-surface">'
        '<span class="benchmark-profile-mark" aria-hidden="true">✓</span>'
        '<span class="benchmark-profile-copy">'
        f'<strong>{_text(row.get("version_name"))}</strong>'
        f'<small>{_text(row.get("profile_name"))}</small>'
        '</span></span></label>'
        for row in benchmark_profiles or []
    )
    benchmark_history_html = render_benchmark_history(benchmark_history or [])
    benchmark_report_html = render_benchmark_report(
        selected_benchmark_report,
        error=benchmark_report_error,
    )
    precompute_summary = dict(precompute_summary or {})
    precompute_worker_id = str(precompute_summary.get("preferred_worker_id", ""))
    precompute_worker_compatible = bool(
        precompute_summary.get("preferred_worker_compatible")
    )
    precompute_worker_name = str(
        precompute_summary.get("preferred_worker_name", precompute_worker_id)
        or precompute_worker_id
    )
    if precompute_worker_id and not precompute_summary.get("preferred_worker_reachable"):
        precompute_worker_name += f' · {_label("ui.worker_disconnected")}'
    precompute_status = str(precompute_summary.get("status", "missing"))
    precompute_status_text = _label(
        {
            "active": "ui.worker_precompute_active",
            "pending": "ui.worker_precompute_queued_state",
            "queued": "ui.worker_precompute_queued_state",
            "running": "ui.worker_precompute_calculating_state",
            "publishing": "ui.worker_precompute_publishing_state",
            "outdated": "ui.worker_precompute_outdated",
            "invalid": "ui.worker_precompute_invalid",
            "failed": "ui.worker_status_failed",
            "cancelled": "ui.worker_status_cancelled",
        }.get(precompute_status, "ui.worker_precompute_missing")
    )
    precompute_window = ""
    if precompute_summary.get("coverage_start") and precompute_summary.get("coverage_end"):
        precompute_window = (
            f'{precompute_summary.get("coverage_start")} → '
            f'{precompute_summary.get("coverage_end")}'
        )
    precompute_force = precompute_status == "active"
    precompute_job_id = str(precompute_summary.get("active_job_id", ""))

    recent_jobs = render_recent_jobs(
        jobs,
        worker_statuses,
        operational_enabled=operational_enabled,
    )
    worker_cards_signature = worker_cards_refresh_signature(
        worker_statuses,
        default_executor=default_executor,
    )
    worker_choices_signature = refresh_signature(worker_choices)
    recent_jobs_signature = refresh_signature(recent_jobs)
    available_operational_versions = operational_versions or []
    selected_operational_versions = {
        str(row.get("version_id") or "")
        for row in available_operational_versions
        if row.get("installed") is True
    }
    if not selected_operational_versions:
        selected_operational_versions = {
            str(row.get("version_id") or "")
            for row in available_operational_versions
        }

    def operational_version_badges(row: dict[str, object]) -> str:
        badges = []
        if row.get("installed") is True:
            badges.append(
                f'<em>{_text(_label("ui.worker_version_installed"))}</em>'
            )
        if row.get("preferred") is True:
            badges.append(
                f'<em>{_text(_label("ui.worker_version_preferred"))}</em>'
            )
        return "".join(badges)

    operational_version_controls = "".join(
        '<label class="operational-version-choice">'
        f'<input type="checkbox" name="operational_version" value="{_text(row.get("version_id"))}"'
        f'{" checked" if str(row.get("version_id") or "") in selected_operational_versions else ""}>'
        '<span class="operational-version-surface">'
        '<span class="operational-version-mark" aria-hidden="true">✓</span>'
        '<span class="operational-version-copy">'
        f'<strong>{_text(row.get("version_name"))}</strong>'
        f'<small>{_text(" · ".join(str(value) for value in (row.get("profile_names") or []) if str(value or "")))}</small>'
        '</span><span class="operational-version-badges">'
        f'{operational_version_badges(row)}'
        '</span></span></label>'
        for row in available_operational_versions
    )
    pairing_action = ""
    if pairing_required:
        pairing_action = f'''
          <form class="worker-toolbar-action" method="post" action="">
            <input type="hidden" name="worker_action" value="create_worker_pairing">
            <button type="submit">{_text(_label("ui.worker_pairing_button"))}</button>
          </form>
        '''
    return f"""
    <style>
      .maintenance-top-toolbar{{margin:0 0 8px!important;gap:6px!important}}.maintenance-top-toolbar .button-link{{padding:6px 10px!important;font-size:10px!important}}
      .worker-toolbar-spacer{{flex:1 1 24px}}.worker-toolbar-actions{{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap;margin-left:auto}}
      .worker-toolbar-action,.worker-default-form{{display:flex!important;align-items:center;gap:6px;margin:0!important}}.worker-toolbar-action button,.worker-default-form button{{height:32px;min-height:32px;padding:6px 10px;font-size:10px;font-weight:700}}
      .worker-default-form select{{width:210px;height:32px;min-height:32px;padding:5px 8px;font-size:11px}}
      .workers-head{{display:flex;align-items:baseline;gap:10px;margin:0 0 7px;padding:0 0 7px;border-bottom:1px solid var(--line)}}
      .workers-head h1{{flex:0 0 auto;margin:0;font-size:23px}}.workers-head p{{margin:0;color:var(--muted);font-size:12px}}
      .workers-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:start;gap:8px;margin:7px 0}}
      .worker-status-cards,.worker-destination-choices{{display:contents}}
      .worker-card{{display:flex;flex-direction:column;min-width:0;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:9px 11px;box-shadow:0 6px 16px rgba(0,0,0,.08)}}
      .worker-card header{{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:6px}}.worker-card h2{{margin:0;font-size:16px}}
      .worker-kicker{{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
      .worker-default-badge{{display:inline-block;margin-left:4px;padding:1px 5px;border:1px solid var(--accent);border-radius:999px;color:var(--accent);font-size:9px;font-weight:700;vertical-align:middle}}
      .worker-host-line{{display:block;margin-top:1px;color:var(--muted);font-size:10px}}.worker-card code{{font-size:10px;font-weight:600}}
      .worker-state{{border:1px solid currentColor;border-radius:999px;padding:2px 6px;font-size:10px;font-weight:700;background:rgba(255,255,255,.025)}}.worker-state.ok{{color:var(--ok)}}.worker-state.warning{{color:var(--accent)}}.worker-state.danger{{color:var(--danger)}}.worker-state.muted{{color:var(--muted)}}
      .worker-card dl{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 10px;margin:0 0 5px}}.worker-card dl div{{min-width:0}}
      .worker-card dt{{font-size:10px;color:var(--muted)}}.worker-card dd{{margin:0;font-size:12px;font-weight:650;overflow-wrap:anywhere}}.worker-card dd small{{display:block;margin-top:1px;color:var(--muted);font-size:9px;font-weight:500}}
      .worker-tools{{margin-top:2px;padding-top:5px;border-top:1px solid var(--line);font-size:10px}}.worker-tools>summary{{cursor:pointer;color:var(--muted);font-weight:650}}.worker-technical-identity{{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0;color:var(--muted)}}
      .worker-note{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px 5px;margin-top:0;padding:6px 0 0;border-top:1px solid var(--line)}}.worker-note strong,.worker-note span{{grid-column:1/-1}}.worker-note strong{{font-size:11px}}.worker-note span,.worker-error{{font-size:10px;color:var(--muted)}}.worker-note form{{margin:1px 0 0}}.worker-note button{{width:100%;padding:4px 5px;font-size:10px}}.worker-error{{margin:0 0 5px}}.worker-error summary{{cursor:pointer}}.worker-error code{{display:block;margin-top:4px;white-space:normal;overflow-wrap:anywhere}}
      .worker-revoke-form{{margin:6px 0 0}}.worker-revoke-form button{{width:100%;padding:5px 7px;font-size:11px;color:var(--danger)}}
      .worker-local-note{{margin:0;padding-top:5px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}}
      .worker-empty-card{{align-items:center;justify-content:center;min-height:120px;color:var(--muted);text-align:center}}
      .workers-panel{{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:10px 11px;margin:7px 0;box-shadow:0 6px 16px rgba(0,0,0,.06)}}.workers-panel h2{{margin:0;font-size:16px}}
      .worker-default-issue{{margin:10px 0 0}}
      .worker-panel-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:5px}}
      .worker-metrics{{display:flex;gap:5px;flex-wrap:wrap;margin:0}}.worker-metrics span{{padding:2px 6px;border:1px solid var(--line);border-radius:999px;background:var(--bg);font-size:10px;color:var(--muted)}}.worker-metrics strong{{color:var(--fg)}}
      form.worker-rebuild-form{{display:block;width:100%;margin:0}}
      .worker-form-section{{margin-top:6px}}.worker-form-heading{{display:flex;align-items:baseline;gap:7px;margin-bottom:4px}}.worker-form-heading strong{{font-size:12px}}.worker-form-heading small{{color:var(--muted);font-size:10px}}
      .worker-destination-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}}
      .worker-rebuild-form .worker-choice,.worker-rebuild-form .worker-scope-choice{{display:block;position:relative;margin:0;min-width:0}}
      .worker-rebuild-form input[type="radio"]{{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;margin:0!important;padding:0!important;opacity:0;pointer-events:none}}
      .worker-choice-surface{{display:grid;grid-template-columns:25px minmax(0,1fr) auto;align-items:center;gap:6px;min-height:40px;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);cursor:pointer;transition:border-color .15s,background .15s}}
      .worker-choice-icon{{display:grid;place-items:center;width:23px;height:23px;border:1px solid var(--line);border-radius:6px;color:var(--muted);font-size:10px;font-weight:800}}
      .worker-choice-copy{{display:flex;flex-direction:column;gap:0;min-width:0}}.worker-choice-copy strong{{font-size:12px}}.worker-choice-copy small{{color:var(--muted);font-size:9px}}
      .worker-choice-mark{{display:grid;place-items:center;width:17px;height:17px;border:1px solid var(--line);border-radius:50%;color:transparent;font-size:10px}}
      .worker-choice input:checked + .worker-choice-surface{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.18)}}.worker-choice input:checked + .worker-choice-surface .worker-choice-icon{{border-color:var(--accent);color:var(--accent)}}.worker-choice input:checked + .worker-choice-surface .worker-choice-mark{{border-color:var(--accent);background:var(--accent);color:#07151d}}
      .worker-choice input:focus-visible + .worker-choice-surface,.worker-scope-choice input:focus-visible + span{{outline:2px solid var(--accent);outline-offset:2px}}
      .worker-choice input:disabled + .worker-choice-surface{{opacity:.52;cursor:not-allowed}}
      .worker-scope-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}}
      .worker-scope-choice>span{{display:flex;flex-direction:column;gap:0;min-height:35px;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);cursor:pointer}}.worker-scope-choice strong{{font-size:11px}}.worker-scope-choice small{{color:var(--muted);font-size:9px}}
      .worker-scope-choice input:checked + span{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.18)}}.worker-scope-choice input:disabled + span{{opacity:.45;cursor:not-allowed}}
      .worker-species-field{{margin-top:8px}}.worker-species-field[hidden]{{display:none}}.worker-species-field label{{display:block;margin:0 0 4px;color:var(--muted);font-size:11px}}.worker-species-field select{{width:100%;max-width:560px}}
      .operational-version-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}}.operational-version-choice{{display:block;position:relative;min-width:0;margin:0}}.operational-version-choice input[type="checkbox"]{{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;margin:0!important;padding:0!important;opacity:0;pointer-events:none}}.operational-version-surface{{display:grid;grid-template-columns:19px minmax(0,1fr) auto;align-items:center;gap:7px;min-height:48px;padding:7px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);cursor:pointer}}.operational-version-mark{{display:grid;place-items:center;width:17px;height:17px;border:1px solid var(--line);border-radius:5px;color:transparent;font-size:11px;font-weight:900}}.operational-version-copy{{display:flex;flex-direction:column;min-width:0}}.operational-version-copy strong{{font-size:12px}}.operational-version-copy small{{color:var(--muted);font-size:9px;line-height:1.25;white-space:normal}}.operational-version-badges{{display:flex;align-items:flex-end;flex-direction:column;gap:3px}}.operational-version-badges em{{padding:1px 5px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:8px;font-style:normal;white-space:nowrap}}.operational-version-choice input:checked + .operational-version-surface{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.18)}}.operational-version-choice input:checked + .operational-version-surface .operational-version-mark{{border-color:var(--accent);background:var(--accent);color:#07151d}}.operational-version-choice input:focus-visible + .operational-version-surface{{outline:2px solid var(--accent);outline-offset:2px}}
      .worker-submit-row{{display:flex;align-items:center;justify-content:flex-end;margin-top:6px;padding-top:6px;border-top:1px solid var(--line)}}.worker-submit-row button{{min-width:155px;padding:6px 9px;font-size:11px}}
      .workers-table-wrap{{overflow:auto;margin-top:4px}}.workers-table-wrap table{{width:100%;min-width:1120px;table-layout:fixed;border-collapse:collapse;font-size:11px}}.workers-table-wrap th,.workers-table-wrap td{{padding:4px 5px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.workers-table-wrap th{{font-size:10px;font-weight:700;color:var(--muted)}}
      .worker-jobs-history{{max-height:286px;overscroll-behavior:contain}}.worker-jobs-history thead th{{position:sticky;top:0;z-index:2;background:var(--card)}}
      .workers-table-wrap th:nth-child(1){{width:105px}}.workers-table-wrap th:nth-child(2){{width:150px}}.workers-table-wrap th:nth-child(3){{width:190px}}.workers-table-wrap th:nth-child(4){{width:105px}}.workers-table-wrap th:nth-child(5){{width:100px}}.workers-table-wrap th:nth-child(6){{width:190px}}.workers-table-wrap th:nth-child(7){{width:190px}}.workers-table-wrap th:nth-child(8){{width:75px}}.workers-table-wrap th:nth-child(9){{width:75px}}.workers-table-wrap th:nth-child(10){{width:145px}}
      .workers-table-wrap code{{font-size:10px}}.workers-table-wrap time{{font-variant-numeric:tabular-nums}}.worker-sort-button{{display:inline-flex;align-items:center;gap:3px;width:100%;margin:0;padding:0;border:0;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}}.worker-sort-button span{{margin-left:auto;font-size:9px}}
      .job-status.complete,.job-status.claimed{{color:var(--ok)}}.job-status.queued,.job-status.running{{color:var(--accent)}}.job-status.failed,.job-status.cancelled,.job-status.cancel_requested{{color:var(--danger)}}.job-status.superseded{{color:var(--muted)}}
      .worker-job-actions{{white-space:normal!important;overflow:visible!important}}.worker-job-action{{display:inline-flex;gap:4px;align-items:center;margin:0 4px 2px 0}}.worker-job-action:last-child{{margin-right:0}}.worker-job-action select{{min-width:90px;max-width:120px;padding:4px;font-size:11px}}.worker-job-action button{{padding:4px 6px;font-size:11px;white-space:nowrap}}
      .worker-job-actions>button{{margin:0 4px 2px 0;padding:4px 6px;font-size:11px;white-space:nowrap}}
      .worker-promotion-progress{{display:flex;align-items:center;gap:5px;min-width:68px}}.worker-promotion-progress progress{{width:46px;height:8px;accent-color:var(--accent)}}.worker-promotion-progress span{{font-variant-numeric:tabular-nums}}
      .worker-discard-dialog{{width:min(520px,calc(100vw - 32px));padding:0;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--fg);box-shadow:0 20px 70px rgba(0,0,0,.55)}}.worker-discard-dialog::backdrop{{background:rgba(0,0,0,.68)}}
      .worker-discard-dialog form{{display:block;margin:0;padding:18px}}.worker-discard-dialog h2{{margin:0 0 9px;font-size:19px}}.worker-discard-dialog p{{margin:7px 0;color:var(--muted);line-height:1.45}}.worker-discard-dialog code{{color:var(--fg)}}.worker-dialog-actions{{display:flex;justify-content:flex-end;gap:8px;margin-top:18px;padding-top:12px;border-top:1px solid var(--line)}}
      .benchmark-form{{display:block!important;width:100%;margin:10px 0 0!important}}.benchmark-form-head{{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:9px}}.benchmark-executor{{display:grid;gap:4px;width:min(340px,100%);color:var(--muted);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}}.benchmark-executor select{{width:100%;height:34px;min-height:34px;padding:5px 8px;font-size:11px;text-transform:none;letter-spacing:normal}}
      .benchmark-profile-fieldset{{min-width:0;margin:0;padding:0;border:0}}.benchmark-profile-fieldset legend{{margin:0 0 6px;padding:0;color:var(--fg);font-size:12px;font-weight:750}}.benchmark-profile-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin:0}}.benchmark-profile-choice{{display:block;position:relative;min-width:0;margin:0}}.benchmark-profile-choice input[type="checkbox"]{{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;margin:0!important;padding:0!important;opacity:0;pointer-events:none}}.benchmark-profile-surface{{display:grid;grid-template-columns:20px minmax(0,1fr);align-items:center;gap:8px;min-height:54px;padding:8px 9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);cursor:pointer;transition:border-color .15s,background .15s,box-shadow .15s}}.benchmark-profile-mark{{display:grid;place-items:center;width:18px;height:18px;border:1px solid var(--line);border-radius:5px;color:transparent;font-size:12px;font-weight:900}}.benchmark-profile-copy{{display:flex;flex-direction:column;gap:1px;min-width:0}}.benchmark-profile-copy strong{{font-size:12px;line-height:1.2;white-space:normal}}.benchmark-profile-copy small{{color:var(--muted);font-size:10px;line-height:1.25;white-space:normal}}.benchmark-profile-choice input:checked + .benchmark-profile-surface{{border-color:var(--accent);background:#102a38;box-shadow:0 0 0 1px rgba(3,169,244,.16)}}.benchmark-profile-choice input:checked + .benchmark-profile-surface .benchmark-profile-mark{{border-color:var(--accent);background:var(--accent);color:#07151d}}.benchmark-profile-choice input:focus-visible + .benchmark-profile-surface{{outline:2px solid var(--accent);outline-offset:2px}}.benchmark-submit-row{{display:flex;align-items:center;justify-content:flex-end;margin-top:9px;padding-top:8px;border-top:1px solid var(--line)}}.benchmark-submit-row button{{min-width:190px;height:34px;min-height:34px;padding:6px 11px;font-size:11px;font-weight:750}}
      .benchmark-history{{display:grid;gap:7px}}.benchmark-history-scroll{{max-height:260px;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding-right:4px}}.benchmark-history-item{{display:flex;align-items:stretch;gap:6px}}.benchmark-history-row{{flex:1;min-width:0;display:flex;justify-content:space-between;gap:12px;padding:9px;border:1px solid var(--line);border-radius:8px;color:inherit;text-decoration:none}}.benchmark-history-row span:first-child{{display:grid;gap:2px}}.benchmark-history-row small{{color:var(--muted)}}.benchmark-history-delete{{flex:0 0 auto;align-self:center;margin:0}}.benchmark-history-delete button{{width:auto;padding:5px 9px;font-size:10px}}
      .precompute-panel{{display:grid;gap:10px}}.precompute-summary{{display:flex;flex-wrap:wrap;gap:8px 16px;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg)}}.precompute-summary strong{{color:var(--fg)}}.precompute-actions{{display:flex;align-items:end;gap:8px;flex-wrap:wrap}}.precompute-actions label{{display:grid;gap:4px;min-width:260px;color:var(--muted);font-size:10px}}.precompute-actions select{{height:34px}}.precompute-actions form{{display:flex;align-items:end;gap:8px;margin:0}}
      .benchmark-report-summary{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}}.benchmark-report-summary div{{padding:8px;border:1px solid var(--line);border-radius:8px;overflow:hidden}}.benchmark-report-summary dt{{color:var(--muted);font-size:11px}}.benchmark-report-summary dd{{margin:4px 0 0;overflow-wrap:anywhere}}
      .benchmark-report-table table{{width:min(100%,1380px);min-width:1220px;table-layout:fixed}}.benchmark-report-table th:nth-child(1){{width:86px}}.benchmark-report-table th:nth-child(2){{width:58px}}.benchmark-report-table th:nth-child(3){{width:150px}}.benchmark-report-table th:nth-child(4){{width:78px}}.benchmark-report-table th:nth-child(5){{width:170px}}.benchmark-report-table th:nth-child(6){{width:62px}}.benchmark-report-table th:nth-child(7){{width:78px}}.benchmark-report-table th:nth-child(8){{width:62px}}.benchmark-report-table th:nth-child(9){{width:68px}}.benchmark-report-table th:nth-child(10){{width:54px}}.benchmark-report-table th:nth-child(11){{width:100px}}.benchmark-report-table th:nth-child(12){{width:80px}}.benchmark-report-table th:nth-child(13){{width:78px}}.benchmark-report-table th:nth-child(14){{width:82px}}.benchmark-report-table th,.benchmark-report-table td{{padding-left:4px;padding-right:4px}}.benchmark-failures{{margin-top:12px}}
      @media(max-width:1050px){{.worker-toolbar-spacer{{display:none}}.worker-toolbar-actions{{flex-basis:100%;justify-content:flex-start;margin-left:0}}.workers-grid,.worker-destination-grid,.operational-version-grid,.benchmark-profile-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
      @media(max-width:700px){{.workers-grid,.worker-destination-grid,.worker-scope-grid,.operational-version-grid,.benchmark-profile-grid,.benchmark-report-summary{{grid-template-columns:1fr}}.worker-panel-head{{display:block}}.workers-head{{align-items:flex-start;flex-direction:column;gap:2px}}.worker-metrics{{justify-content:flex-start;margin-top:6px;text-align:left}}.worker-toolbar-actions{{align-items:stretch;flex-direction:column}}.worker-default-form{{align-items:stretch;flex-direction:column}}.worker-default-form select{{width:100%;max-width:none}}.benchmark-form-head{{display:block}}.benchmark-executor{{width:100%}}.benchmark-submit-row button{{width:100%}}.worker-note{{grid-template-columns:1fr}}}}
    </style>
    <div class="catalog-toolbar maintenance-top-toolbar">
      <a class="button-link" href="../">{_text(_label('ui.back'))}</a>
      <a class="button-link" href="./workers">{_text(_label('ui.worker_refresh'))}</a>
      <a class="button-link" href="./profiles">{_text(_label('ui.species'))}</a>
      <a class="button-link" href="./catalogs">{_text(_label('ui.worker_reference_catalogs'))}</a>
      <a class="button-link" href="./gis-mappings">{_text(_label('ui.worker_gis_mappings'))}</a>
      <a class="button-link" href="./known-sites">{_text(_label('ui.known_sites'))}</a>
      <span class="worker-toolbar-spacer"></span>
      <div class="worker-toolbar-actions">
        {pairing_action}
        <form class="worker-default-form" method="post" action="">
          <input type="hidden" name="worker_action" value="set_default_executor">
          <select name="default_executor" aria-label="{_text(_label('ui.worker_default_executor'))}" title="{_text(_label('ui.worker_default_executor_help'))}">{''.join(default_options)}</select>
          <button type="submit">{_text(_label('ui.worker_default_save'))}</button>
        </form>
      </div>
    </div>
    <div class="workers-head"><h1>{_text(_label('ui.workers_jobs'))}</h1><p>{_text(_label('ui.workers_jobs_help'))}</p></div>
    {benchmark_report_html}
    <div id="worker-flash-region" data-clear-when-idle="{'1' if flash_clear_when_idle else '0'}">{render_worker_flash(flash, error=flash_error)}</div>
    {f'<div class="catalog-alert error worker-default-issue"><strong>{_text(_label("ui.worker_default_attention"))}</strong><br>{_text(default_issue)}<br>{_text(_label("ui.worker_choose_available"))}</div>' if default_issue else ''}
    <div class="workers-grid">
      <article class="worker-card">
        <header><div><span class="worker-kicker">rainmapper-ha-ui</span><h2>{_text(_label('ui.home_assistant'))}</h2></div><span class="worker-state ok">{_text(_label('ui.worker_available'))}</span></header>
        <dl>
          <div><dt>Pipeline</dt><dd>{_text(pipeline)}</dd></div>
          <div><dt>{_text(_label('ui.worker_role'))}</dt><dd>{_text(_label('ui.worker_local_compute') if local_ha_compute_enabled else _label('ui.worker_coordinator'))}</dd></div>
        </dl>
        <p class="worker-local-note">{_text(_label('ui.worker_local_compute_help') if local_ha_compute_enabled else _label('ui.worker_coordinator_help'))}</p>
      </article>
      <div id="worker-status-cards" class="worker-status-cards" data-refresh-signature="{worker_cards_signature}">{worker_cards}</div>
    </div>
    <section id="new-worker-rebuild" class="workers-panel">
      <div class="worker-panel-head"><h2>{_text(_label('ui.worker_new_rebuild'))}</h2><div class="worker-metrics"><span>{_text(_label('ui.worker_eligible_observations'))}: <strong>{eligible_observation_count}</strong></span></div></div>
      <form class="worker-rebuild-form" method="post" action="">
        <input type="hidden" name="worker_action" value="start_rebuild">
        <input type="hidden" name="scope" value="all">
        <input type="hidden" name="operational_selection_present" value="1">
        <div class="worker-form-section"><div class="worker-form-heading"><strong>1 · {_text(_label('ui.execute_on'))}</strong><small>{_text(_label('ui.worker_destination_help'))}</small></div>
          <div class="worker-destination-grid">
            <div id="worker-destination-choices" class="worker-destination-choices" data-refresh-signature="{worker_choices_signature}">{worker_choices}</div>
          </div>
        </div>
        <div class="worker-form-section"><div class="worker-form-heading"><strong>2 · {_text(_label('ui.rebuild_scope_all'))}</strong><small>{eligible_observation_count} {_text(_label('ui.worker_eligible_observations')).lower()}. {_text(_label('ui.worker_scope_help'))}</small></div></div>
        <div class="worker-form-section"><div class="worker-form-heading"><strong>3 · {_text(_label('ui.worker_operational_versions'))}</strong><small>{_text(_label('ui.worker_operational_versions_help'))}</small></div><div class="operational-version-grid">{operational_version_controls}</div></div>
        <div class="worker-submit-row"><button class="primary" type="submit"{" disabled" if not selected_executor else ""}>{_text(_label('ui.start_rebuild'))}</button></div>
      </form>
    </section>
    <section class="workers-panel precompute-panel">
      <div class="worker-panel-head"><h2>{_text(_label('ui.worker_precompute_title'))}</h2></div>
      <p class="meta">{_text(_label('ui.worker_precompute_help_local') if precompute_summary.get('local_executor') else _label('ui.worker_precompute_help'))}</p>
      <div class="precompute-summary">
        <span>{_text(_label('ui.status'))}: <strong>{_text(precompute_status_text)}</strong></span>
        <span>{_text(_label('ui.worker_precompute_worker'))}: <strong>{_text(precompute_worker_name or '—')}</strong></span>
        <span>{_text(_label('ui.worker_precompute_fingerprint'))}: <strong><code>{_text(precompute_summary.get('runtime_fingerprint', '—'))}</code></strong></span>
        <span>{_text(_label('ui.worker_precompute_planned_artifact'))}: <strong><code>{_text(precompute_summary.get('planned_artifact_id', '—'))}</code></strong></span>
        <span>{_text(_label('ui.worker_precompute_active_artifact'))}: <strong><code>{_text(precompute_summary.get('artifact_id', '—') or '—')}</code></strong></span>
        {f'<span>{_text(_label("ui.worker_precompute_window"))}: <strong>{_text(precompute_window)}</strong></span>' if precompute_window else ''}
        {f'<span>Revision: <strong>{_text(precompute_summary.get("desired_revision", 0))}</strong></span>' if precompute_summary.get("desired_revision") else ''}
        {f'<span>Job: <strong><a href="#job-{_text(precompute_job_id)}"><code>{_text(precompute_job_id)}</code></a> · {_text(precompute_summary.get("active_job_status", ""))}</strong></span>' if precompute_job_id else ''}
      </div>
      <div class="precompute-actions">
        <form method="post" action="">
          <input type="hidden" name="worker_action" value="run_predictor_precompute">
          <input type="hidden" name="worker_id" value="{_text(precompute_worker_id)}">
          <button{' class="primary"' if precompute_worker_compatible else ''} type="submit"{' disabled' if not precompute_worker_compatible else ''}>{_text(_label('ui.worker_precompute_launch'))}</button>
        </form>
        {('<form method="post" action=""><input type="hidden" name="worker_action" value="run_predictor_precompute"><input type="hidden" name="force" value="1"><input type="hidden" name="worker_id" value="' + _text(precompute_worker_id) + '"><button type="submit">' + _text(_label('ui.worker_precompute_force')) + '</button></form>') if precompute_force and precompute_worker_compatible else ''}
      </div>
    </section>
    <section class="workers-panel">
      <div class="worker-panel-head"><h2>{_text(_label('ui.worker_scientific_benchmark'))}</h2></div>
      <p class="meta">{_text(_label('ui.worker_scientific_benchmark_help'))}</p>
      <form class="benchmark-form" method="post" action="">
        <input type="hidden" name="worker_action" value="run_ml_benchmark">
        <input type="hidden" name="benchmark_selection_present" value="1">
        <div class="benchmark-form-head">
          <label class="benchmark-executor"><span>{_text(_label('ui.execute_on'))}</span><select name="executor">{''.join(benchmark_options)}</select></label>
        </div>
        <fieldset class="benchmark-profile-fieldset">
          <legend>{_text(_label('ui.worker_benchmark_profiles'))}</legend>
          <div class="benchmark-profile-grid">{benchmark_profile_controls}</div>
        </fieldset>
        <div class="benchmark-submit-row"><button type="submit"{" disabled" if not benchmark_options else ""}>{_text(_label('ui.worker_run_scientific_benchmark'))}</button></div>
      </form>
      <h3>{_text(_label('ui.worker_benchmark_history'))}</h3>
      {benchmark_history_html}
    </section>
    <section class="workers-panel"><h2>{_text(_label('ui.worker_recent_jobs'))}</h2><div id="worker-recent-jobs" data-refresh-signature="{recent_jobs_signature}">{recent_jobs}</div></section>
    <dialog id="worker-discard-candidate-dialog" class="worker-discard-dialog">
      <form method="post" action="">
        <input type="hidden" name="worker_action" value="discard_worker_candidate">
        <input type="hidden" name="job_id" value="">
        <h2>{_text(_label('ui.worker_discard_candidate_title'))}</h2>
        <p>{_text(_label('ui.worker_discard_candidate_confirm'))}</p>
        <p><code data-discard-job-label></code></p>
        <div class="worker-dialog-actions">
          <button type="button" data-close-discard-dialog>{_text(_label('ui.cancel'))}</button>
          <button type="submit" class="danger">{_text(_label('ui.worker_discard_candidate'))}</button>
        </div>
      </form>
    </dialog>
    <script>
    (()=>{{const form=document.querySelector('.worker-rebuild-form');if(!form)return;const submit=form.querySelector('button[type="submit"]');const sync=()=>{{const executor=form.querySelector('input[name="executor"]:checked');submit.disabled=!executor||executor.disabled;}};form.addEventListener('change',sync);sync();}})();
    (()=>{{
      const dialog=document.getElementById('worker-discard-candidate-dialog');if(!dialog)return;
      const jobInput=dialog.querySelector('input[name="job_id"]');const jobLabel=dialog.querySelector('[data-discard-job-label]');
      document.addEventListener('click',event=>{{
        const trigger=event.target.closest('[data-discard-worker-candidate]');
        if(trigger){{jobInput.value=trigger.dataset.jobId||'';jobLabel.textContent=trigger.dataset.jobLabel||jobInput.value;if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');return;}}
        if(event.target.closest('[data-close-discard-dialog]')||event.target===dialog)dialog.close();
      }});
    }})();
    (()=>{{
      const cards=document.getElementById('worker-status-cards');
      const destinations=document.getElementById('worker-destination-choices');
      const jobs=document.getElementById('worker-recent-jobs');
      const flashRegion=document.getElementById('worker-flash-region');
      if(!cards||!destinations||!jobs||!flashRegion)return;
      const appBasePath=window.location.pathname.replace(/\\/mushrooms\\/workers\\/?$/,'');
      const statusUrl=`${{appBasePath}}/api/mushrooms/workers/status`;
      let timer=0,requestController=null,interactionUntil=0,leaving=false;
      let jobSortColumn=1,jobSortDirection='desc',jobSortType='time';
      const jobSortValue=(raw,type)=>{{
        if(type==='number'){{const value=Number(raw);return Number.isFinite(value)?value:0;}}
        if(type==='time'){{const numeric=Number(raw);if(Number.isFinite(numeric))return numeric;const parsed=Date.parse(raw);return Number.isFinite(parsed)?parsed:0;}}
        return String(raw||'');
      }};
      const applyJobSort=()=>{{
        const table=jobs.querySelector('[data-sortable-worker-jobs]');if(!table)return;
        const body=table.tBodies[0];if(!body)return;
        const rows=Array.from(body.rows);
        rows.sort((left,right)=>{{
          const leftValue=jobSortValue(left.cells[jobSortColumn]?.dataset.sortValue,jobSortType);
          const rightValue=jobSortValue(right.cells[jobSortColumn]?.dataset.sortValue,jobSortType);
          const result=jobSortType==='text'
            ?leftValue.localeCompare(rightValue,undefined,{{numeric:true,sensitivity:'base'}})
            :leftValue-rightValue;
          return jobSortDirection==='asc'?result:-result;
        }});
        rows.forEach(row=>body.appendChild(row));
        table.dataset.sortColumn=String(jobSortColumn);table.dataset.sortDirection=jobSortDirection;
        table.querySelectorAll('th').forEach((header,index)=>{{
          const active=index===jobSortColumn;
          header.setAttribute('aria-sort',active?(jobSortDirection==='asc'?'ascending':'descending'):'none');
          const indicator=header.querySelector('[aria-hidden="true"]');if(indicator)indicator.textContent=active?(jobSortDirection==='asc'?'↑':'↓'):'↕';
        }});
      }};
      const schedule=()=>{{if(leaving)return;window.clearTimeout(timer);timer=window.setTimeout(refresh,2000);}};
      const postponeRefresh=()=>{{interactionUntil=Math.max(interactionUntil,Date.now()+4000);}};
      const stopRefresh=()=>{{leaving=true;window.clearTimeout(timer);requestController?.abort();}};
      const replaceRegion=(region,htmlValue,signature)=>{{
        if(typeof htmlValue!=='string'||typeof signature!=='string'||region.dataset.refreshSignature===signature)return false;
        const scrollPositions=Array.from(region.querySelectorAll('[data-preserve-refresh-scroll]')).map(node=>({{top:node.scrollTop,left:node.scrollLeft}}));
        region.innerHTML=htmlValue;region.dataset.refreshSignature=signature;
        Array.from(region.querySelectorAll('[data-preserve-refresh-scroll]')).forEach((node,index)=>{{const position=scrollPositions[index];if(position){{node.scrollTop=position.top;node.scrollLeft=position.left;}}}});
        return true;
      }};
      document.addEventListener('pointerdown',event=>{{if(event.target.closest('a,button,input,select,textarea'))postponeRefresh();}},true);
      document.addEventListener('keydown',event=>{{if((event.key==='Enter'||event.key===' ')&&event.target.closest('a,button,input,select,textarea'))postponeRefresh();}},true);
      document.addEventListener('scroll',event=>{{if(event.target instanceof Element&&event.target.matches('[data-preserve-refresh-scroll]'))postponeRefresh();}},true);
      document.addEventListener('submit',event=>{{
        stopRefresh();
        const submitter=event.submitter;
        if(submitter){{submitter.disabled=true;submitter.setAttribute('aria-busy','true');}}
      }},true);
      document.addEventListener('click',event=>{{
        const sortButton=event.target.closest('[data-worker-sort-column]');
        if(sortButton){{
          const nextColumn=Number(sortButton.dataset.workerSortColumn);
          if(nextColumn===jobSortColumn)jobSortDirection=jobSortDirection==='asc'?'desc':'asc';
          else{{jobSortColumn=nextColumn;jobSortDirection='asc';}}
          jobSortType=sortButton.dataset.workerSortType||'text';applyJobSort();return;
        }}
        const link=event.target.closest('a[href]');if(!link||event.defaultPrevented)return;
        const target=new URL(link.href,window.location.href);
        const localAnchor=target.origin===window.location.origin&&target.pathname===window.location.pathname&&target.search===window.location.search&&Boolean(target.hash);
        if(!localAnchor)stopRefresh();
      }},true);
      const refresh=async()=>{{
        if(document.hidden||leaving){{schedule();return;}}
        try{{
          requestController=new AbortController();
          const response=await fetch(statusUrl,{{cache:'no-store',headers:{{Accept:'application/json'}},signal:requestController.signal}});
          if(!response.ok)return;
          const payload=await response.json();
          if(!payload.ok)return;
          if(payload.flash_update===true&&typeof payload.flash_html==='string'){{
            flashRegion.innerHTML=payload.flash_html;
            flashRegion.dataset.clearWhenIdle=payload.flash_clear_when_idle===true?'1':'0';
          }}
          if(payload.worker_activity_active===false&&flashRegion.dataset.clearWhenIdle==='1'){{
            flashRegion.replaceChildren();
            flashRegion.dataset.clearWhenIdle='0';
          }}
          document.querySelectorAll('[data-worker-id]').forEach(card=>{{
            const checked=payload.worker_last_checks?.[card.dataset.workerId];
            const node=card.querySelector('[data-worker-last-check]');
            if(node&&typeof checked==='string'&&node.textContent!==checked)node.textContent=checked;
          }});
          if(Date.now()<interactionUntil)return;
          const selected=document.querySelector('input[name="executor"]:checked')?.value||'';
          replaceRegion(cards,payload.worker_cards_html,payload.worker_cards_signature);
          const destinationsChanged=replaceRegion(destinations,payload.worker_choices_html,payload.worker_choices_signature);
          const jobsChanged=replaceRegion(jobs,payload.recent_jobs_html,payload.recent_jobs_signature);
          if(jobsChanged)applyJobSort();
          const restored=Array.from(document.querySelectorAll('input[name="executor"]')).find(item=>item.value===selected);
          if(restored&&!restored.disabled)restored.checked=true;
          if(destinationsChanged)document.querySelector('.worker-rebuild-form')?.dispatchEvent(new Event('change',{{bubbles:true}}));
        }}catch(error){{if(error.name!=='AbortError')void error;}}finally{{requestController=null;schedule();}}
      }};
      document.addEventListener('visibilitychange',()=>{{if(!document.hidden)refresh();}});
      applyJobSort();
      schedule();
    }})();
    </script>
    """
