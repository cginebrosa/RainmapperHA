FROM python:3.11-slim

LABEL io.hass.version="0.2.210" \
      io.hass.type="app" \
      io.hass.arch="aarch64|amd64"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RAINMAPPER_APP_VERSION=0.2.210

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gdal-bin \
        ffmpeg \
        libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2
RUN pip install --no-cache-dir -r requirements.txt

COPY stations.example.txt /app/
COPY users.example.json /app/
COPY mushroom-data/ /app/mushroom-data/
COPY scripts/validate-mushroom-data.py /app/scripts/validate-mushroom-data.py
COPY rainmapper_core/ /app/rainmapper_core/
COPY rainmapper-app/app/web_server.py /app/web_server.py
COPY rainmapper-app/app/mushroom_catalogs_ui.py /app/mushroom_catalogs_ui.py
COPY rainmapper-app/app/mushroom_gis_mappings_ui.py /app/mushroom_gis_mappings_ui.py
COPY rainmapper-app/app/mushroom_known_sites_ui.py /app/mushroom_known_sites_ui.py
COPY rainmapper-app/app/mushroom_profiles_ui.py /app/mushroom_profiles_ui.py
COPY rainmapper-app/app/mushroom_workers_ui.py /app/mushroom_workers_ui.py
COPY rainmapper-app/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
