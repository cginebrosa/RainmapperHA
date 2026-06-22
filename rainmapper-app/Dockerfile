FROM python:3.11-slim

LABEL io.hass.version="0.2.91" \
      io.hass.type="app" \
      io.hass.arch="aarch64|amd64"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RAINMAPPER_APP_VERSION=0.2.91

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2
RUN pip install --no-cache-dir -r requirements.txt

COPY stations.example.txt /app/
COPY users.example.json /app/
COPY rainmapper_core/ /app/rainmapper_core/
COPY rainmapper-app/app/web_server.py /app/web_server.py
COPY rainmapper-app/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
