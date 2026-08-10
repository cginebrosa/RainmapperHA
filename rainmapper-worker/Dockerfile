FROM python:3.11-slim

ARG RAINMAPPER_WORKER_VERSION=1.0.5

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
     rainmapper_core/mushroom_learned_model.py \
     rainmapper_core/mushroom_observation_context.py \
     rainmapper_core/mushroom_observation_features.py \
     rainmapper_core/mushroom_observations.py \
     rainmapper_core/mushroom_paths.py \
     rainmapper_core/mushroom_ml_experiments.py \
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
     rainmapper_core/mushroom_worker_dataset_cache.py \
     rainmapper_core/mushroom_worker_config.py \
     rainmapper_core/mushroom_worker_registry.py \
     rainmapper_core/mushroom_worker_service.py \
     rainmapper_core/mushroom_worker_transport.py \
     rainmapper_core/mushroom_worker_results.py \
     rainmapper_core/mushroom_ml_trainer.py \
     rainmapper_core/runtime_diagnostics.py \
     /app/rainmapper_core/
COPY scripts/run-mushroom-rebuild-job.py /app/scripts/run-mushroom-rebuild-job.py
COPY scripts/run-mushroom-ml-train-job.py /app/scripts/run-mushroom-ml-train-job.py
COPY scripts/manage-mushroom-worker-datasets.py /app/scripts/manage-mushroom-worker-datasets.py
COPY scripts/manage-mushroom-worker-config.py /app/scripts/manage-mushroom-worker-config.py
COPY scripts/run-mushroom-worker-service.py /app/scripts/run-mushroom-worker-service.py
COPY rainmapper-worker/entrypoint.sh /usr/local/bin/rainmapper-worker

RUN chmod 0755 /usr/local/bin/rainmapper-worker \
    && python -m py_compile \
        /app/rainmapper_core/mushroom_rebuild_contracts.py \
        /app/rainmapper_core/mushroom_rebuild_comparison.py \
        /app/rainmapper_core/mushroom_rebuild_pipeline.py \
        /app/rainmapper_core/mushroom_worker_dataset_cache.py \
        /app/rainmapper_core/mushroom_worker_config.py \
        /app/rainmapper_core/mushroom_worker_registry.py \
        /app/rainmapper_core/mushroom_worker_service.py \
        /app/rainmapper_core/mushroom_worker_transport.py \
        /app/rainmapper_core/mushroom_worker_results.py \
        /app/rainmapper_core/mushroom_ml_experiments.py \
        /app/rainmapper_core/mushroom_ml_experiment_trainer.py \
        /app/rainmapper_core/mushroom_ml_comparison.py \
        /app/rainmapper_core/mushroom_ml_predictor.py \
        /app/rainmapper_core/mushroom_prediction_interpretation.py \
        /app/rainmapper_core/mushroom_predictor_runtime.py \
        /app/rainmapper_core/mushroom_predictor_service.py \
        /app/rainmapper_core/runtime_diagnostics.py \
        /app/scripts/manage-mushroom-worker-datasets.py \
        /app/scripts/manage-mushroom-worker-config.py \
        /app/scripts/run-mushroom-worker-service.py \
        /app/scripts/run-mushroom-rebuild-job.py \
        /app/scripts/run-mushroom-ml-train-job.py \
        /app/rainmapper_core/mushroom_ml_trainer.py

VOLUME ["/var/lib/rainmapper-worker"]

ENTRYPOINT ["/usr/local/bin/rainmapper-worker"]
CMD ["--help"]
