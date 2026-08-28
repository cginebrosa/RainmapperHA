FROM python:3.11-slim

ARG RAINMAPPER_WORKER_VERSION=1.0.27

LABEL org.opencontainers.image.title="Rainmapper Worker" \
      org.opencontainers.image.description="Portable contract-driven Rainmapper compute worker" \
      org.opencontainers.image.version="${RAINMAPPER_WORKER_VERSION}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RAINMAPPER_WORKER_VERSION=${RAINMAPPER_WORKER_VERSION}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gdal-bin \
        gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 rainmapper-worker \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/rainmapper-worker rainmapper-worker \
    && mkdir -p /var/lib/rainmapper-worker \
    && chown rainmapper-worker:rainmapper-worker /var/lib/rainmapper-worker

RUN pip install --no-cache-dir \
        numpy==2.4.6 \
        pandas==2.2.2 \
        pyarrow==25.0.0 \
        scikit-learn==1.9.0

COPY rainmapper_core/__init__.py \
     rainmapper_core/mushroom_gis_lab.py \
     rainmapper_core/mushroom_known_sites.py \
     rainmapper_core/mushroom_learned_model.py \
     rainmapper_core/mushroom_ml_biology_v3.py \
     rainmapper_core/mushroom_ml_biology_v3_evaluation.py \
     rainmapper_core/mushroom_ml_biology_v3_physical.py \
     rainmapper_core/mushroom_ml_biology_v4.py \
     rainmapper_core/mushroom_ml_benchmark_reports.py \
     rainmapper_core/mushroom_ml_raw_weather.py \
     rainmapper_core/mushroom_ml_smooth_hierarchical.py \
     rainmapper_core/mushroom_ml_sparse_group.py \
     rainmapper_core/mushroom_ml_holdout.py \
     rainmapper_core/mushroom_ml_input_identity.py \
     rainmapper_core/mushroom_ml_version_registry.py \
     rainmapper_core/mushroom_ml_model_catalog.py \
     rainmapper_core/mushroom_ml_tuning_catalog.py \
     rainmapper_core/mushroom_operational_training_scope.py \
     rainmapper_core/mushroom_ml_weather_workspace.py \
     rainmapper_core/mushroom_ml_multiversion_plan.py \
     rainmapper_core/mushroom_ml_multiversion_transport.py \
     rainmapper_core/mushroom_ml_runtime_trainer.py \
     rainmapper_core/mushroom_ml_runtime_inference.py \
     rainmapper_core/mushroom_ml_runtime_features.py \
     rainmapper_core/mushroom_ml_area_weather_runtime.py \
     rainmapper_core/mushroom_ml_multiversion_comparison.py \
     rainmapper_core/mushroom_ml_quality_catalog.py \
     rainmapper_core/mushroom_climatic_water_balance.py \
     rainmapper_core/mushroom_soil_water_state.py \
     rainmapper_core/mushroom_observation_context.py \
     rainmapper_core/mushroom_observation_features.py \
     rainmapper_core/mushroom_observations.py \
     rainmapper_core/mushroom_paths.py \
     rainmapper_core/mushroom_ml_experiments.py \
     rainmapper_core/mushroom_ml_error_analysis.py \
     rainmapper_core/mushroom_ml_experiment_trainer.py \
     rainmapper_core/mushroom_ml_comparison.py \
     rainmapper_core/mushroom_ml_predictor.py \
     rainmapper_core/mushroom_prediction_interpretation.py \
     rainmapper_core/mushroom_predictor_runtime.py \
     rainmapper_core/mushroom_predictor_service.py \
     rainmapper_core/mushroom_rebuild_contracts.py \
     rainmapper_core/mushroom_rebuild_comparison.py \
     rainmapper_core/mushroom_rebuild_pipeline.py \
     rainmapper_core/mushroom_rebuild_snapshot.py \
     rainmapper_core/mushroom_store.py \
     rainmapper_core/mushroom_worker_dataset_cache.py \
     rainmapper_core/mushroom_worker_config.py \
     rainmapper_core/mushroom_worker_registry.py \
     rainmapper_core/mushroom_worker_jobs.py \
     rainmapper_core/mushroom_worker_service.py \
     rainmapper_core/mushroom_worker_transport.py \
     rainmapper_core/mushroom_worker_results.py \
     rainmapper_core/mushroom_performance_telemetry.py \
     rainmapper_core/mushroom_weather_idw.py \
     rainmapper_core/mushroom_ml_trainer.py \
     rainmapper_core/runtime_diagnostics.py \
     rainmapper_core/weather_history_contract.py \
     rainmapper_core/weather_history_dataset.py \
     /app/rainmapper_core/
COPY mushroom-data/mushroom_ml_version_registry.json /app/mushroom-data/mushroom_ml_version_registry.json
COPY scripts/run-mushroom-rebuild-job.py /app/scripts/run-mushroom-rebuild-job.py
COPY scripts/run-mushroom-ml-train-job.py /app/scripts/run-mushroom-ml-train-job.py
COPY scripts/run-mushroom-ml-multiversion-job.py /app/scripts/run-mushroom-ml-multiversion-job.py
COPY scripts/prepare-mushroom-ml-multiversion-inputs.py /app/scripts/prepare-mushroom-ml-multiversion-inputs.py
COPY scripts/build-biology-v3-benchmark.py /app/scripts/build-biology-v3-benchmark.py
COPY scripts/build-biology-v4-benchmark.py /app/scripts/build-biology-v4-benchmark.py
COPY scripts/build-biology-v5-raw-benchmark.py /app/scripts/build-biology-v5-raw-benchmark.py
COPY scripts/evaluate-biology-v5-raw-benchmark.py /app/scripts/evaluate-biology-v5-raw-benchmark.py
COPY scripts/evaluate-biology-v6-smooth-hierarchical.py /app/scripts/evaluate-biology-v6-smooth-hierarchical.py
COPY scripts/manage-mushroom-worker-datasets.py /app/scripts/manage-mushroom-worker-datasets.py
COPY scripts/manage-mushroom-worker-config.py /app/scripts/manage-mushroom-worker-config.py
COPY scripts/run-mushroom-worker-service.py /app/scripts/run-mushroom-worker-service.py
COPY rainmapper-worker/entrypoint.sh /usr/local/bin/rainmapper-worker

RUN chmod 0755 /usr/local/bin/rainmapper-worker \
    && python -m py_compile \
        /app/rainmapper_core/mushroom_rebuild_contracts.py \
        /app/rainmapper_core/mushroom_ml_biology_v3.py \
        /app/rainmapper_core/mushroom_ml_biology_v3_evaluation.py \
        /app/rainmapper_core/mushroom_ml_biology_v3_physical.py \
        /app/rainmapper_core/mushroom_ml_biology_v4.py \
        /app/rainmapper_core/mushroom_ml_benchmark_reports.py \
        /app/rainmapper_core/mushroom_ml_raw_weather.py \
        /app/rainmapper_core/mushroom_ml_smooth_hierarchical.py \
        /app/rainmapper_core/mushroom_ml_sparse_group.py \
        /app/rainmapper_core/mushroom_ml_holdout.py \
        /app/rainmapper_core/mushroom_ml_input_identity.py \
        /app/rainmapper_core/mushroom_ml_version_registry.py \
        /app/rainmapper_core/mushroom_ml_model_catalog.py \
        /app/rainmapper_core/mushroom_ml_tuning_catalog.py \
        /app/rainmapper_core/mushroom_operational_training_scope.py \
        /app/rainmapper_core/mushroom_ml_weather_workspace.py \
        /app/rainmapper_core/mushroom_ml_multiversion_plan.py \
        /app/rainmapper_core/mushroom_ml_multiversion_transport.py \
        /app/rainmapper_core/mushroom_ml_runtime_trainer.py \
        /app/rainmapper_core/mushroom_ml_runtime_inference.py \
        /app/rainmapper_core/mushroom_ml_runtime_features.py \
        /app/rainmapper_core/mushroom_ml_area_weather_runtime.py \
        /app/rainmapper_core/mushroom_ml_multiversion_comparison.py \
        /app/rainmapper_core/mushroom_ml_quality_catalog.py \
        /app/rainmapper_core/mushroom_climatic_water_balance.py \
        /app/rainmapper_core/mushroom_soil_water_state.py \
        /app/rainmapper_core/mushroom_rebuild_comparison.py \
        /app/rainmapper_core/mushroom_rebuild_pipeline.py \
        /app/rainmapper_core/mushroom_worker_dataset_cache.py \
        /app/rainmapper_core/mushroom_worker_config.py \
        /app/rainmapper_core/mushroom_worker_registry.py \
        /app/rainmapper_core/mushroom_worker_jobs.py \
        /app/rainmapper_core/mushroom_worker_service.py \
        /app/rainmapper_core/mushroom_worker_transport.py \
        /app/rainmapper_core/mushroom_worker_results.py \
        /app/rainmapper_core/mushroom_performance_telemetry.py \
        /app/rainmapper_core/mushroom_ml_experiments.py \
        /app/rainmapper_core/mushroom_ml_error_analysis.py \
        /app/rainmapper_core/mushroom_ml_experiment_trainer.py \
        /app/rainmapper_core/mushroom_ml_comparison.py \
        /app/rainmapper_core/mushroom_ml_predictor.py \
        /app/rainmapper_core/mushroom_prediction_interpretation.py \
        /app/rainmapper_core/mushroom_predictor_runtime.py \
        /app/rainmapper_core/mushroom_predictor_service.py \
        /app/rainmapper_core/runtime_diagnostics.py \
        /app/rainmapper_core/weather_history_contract.py \
        /app/rainmapper_core/weather_history_dataset.py \
        /app/scripts/manage-mushroom-worker-datasets.py \
        /app/scripts/manage-mushroom-worker-config.py \
        /app/scripts/run-mushroom-worker-service.py \
        /app/scripts/run-mushroom-rebuild-job.py \
        /app/scripts/run-mushroom-ml-train-job.py \
        /app/scripts/run-mushroom-ml-multiversion-job.py \
        /app/scripts/prepare-mushroom-ml-multiversion-inputs.py \
        /app/scripts/build-biology-v3-benchmark.py \
        /app/scripts/build-biology-v4-benchmark.py \
        /app/scripts/build-biology-v5-raw-benchmark.py \
        /app/scripts/evaluate-biology-v5-raw-benchmark.py \
        /app/scripts/evaluate-biology-v6-smooth-hierarchical.py \
        /app/rainmapper_core/mushroom_ml_trainer.py \
    && find /app -type d -name __pycache__ -prune -exec rm -rf '{}' +

VOLUME ["/var/lib/rainmapper-worker"]

ENTRYPOINT ["/usr/local/bin/rainmapper-worker"]
CMD ["--help"]
