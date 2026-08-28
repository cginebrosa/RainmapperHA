FROM python:3.11-slim

LABEL io.hass.version="0.2.271" \
      io.hass.type="app" \
      io.hass.arch="aarch64|amd64"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RAINMAPPER_APP_VERSION=0.2.271

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        ffmpeg \
        libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2
RUN pip install --no-cache-dir -r requirements.txt

COPY stations.example.txt /app/
COPY users.example.json /app/
COPY mushroom-data/mushroom_profiles.json \
     mushroom-data/mushroom_reference_catalogs.json \
     mushroom-data/mushroom_gis_mappings.json \
     mushroom-data/mushroom_known_sites.json \
     mushroom-data/mushroom_labels.json \
     mushroom-data/mushroom_ml_version_registry.json \
     /app/mushroom-data/
COPY rainmapper-app/defaults/mushroom_observations.json /app/mushroom-data/mushroom_observations.json
COPY scripts/validate-mushroom-data.py /app/scripts/validate-mushroom-data.py
COPY scripts/run-mushroom-rebuild-job.py /app/scripts/run-mushroom-rebuild-job.py
COPY scripts/run-mushroom-ml-train-job.py /app/scripts/run-mushroom-ml-train-job.py
COPY scripts/run-mushroom-ml-multiversion-job.py /app/scripts/run-mushroom-ml-multiversion-job.py
COPY scripts/prepare-mushroom-ml-multiversion-inputs.py /app/scripts/prepare-mushroom-ml-multiversion-inputs.py
COPY scripts/build-biology-v3-benchmark.py /app/scripts/build-biology-v3-benchmark.py
COPY scripts/build-biology-v4-benchmark.py /app/scripts/build-biology-v4-benchmark.py
COPY scripts/build-biology-v5-raw-benchmark.py /app/scripts/build-biology-v5-raw-benchmark.py
COPY scripts/evaluate-biology-v5-raw-benchmark.py /app/scripts/evaluate-biology-v5-raw-benchmark.py
COPY scripts/evaluate-biology-v6-smooth-hierarchical.py /app/scripts/evaluate-biology-v6-smooth-hierarchical.py
COPY rainmapper_core/ /app/rainmapper_core/
COPY rainmapper-app/app/web_server.py /app/web_server.py
COPY rainmapper-app/app/mushroom_catalogs_ui.py /app/mushroom_catalogs_ui.py
COPY rainmapper-app/app/mushroom_gis_mappings_ui.py /app/mushroom_gis_mappings_ui.py
COPY rainmapper-app/app/mushroom_known_sites_ui.py /app/mushroom_known_sites_ui.py
COPY rainmapper-app/app/mushroom_profiles_ui.py /app/mushroom_profiles_ui.py
COPY rainmapper-app/app/mushroom_predictor_ui.py /app/mushroom_predictor_ui.py
COPY rainmapper-app/app/mushroom_workers_ui.py /app/mushroom_workers_ui.py
COPY rainmapper-app/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
