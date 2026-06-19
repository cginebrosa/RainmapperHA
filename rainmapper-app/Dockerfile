FROM python:3.11-slim

LABEL io.hass.version="0.2.77" \
      io.hass.type="app" \
      io.hass.arch="aarch64|amd64"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RAINMAPPER_APP_VERSION=0.2.77

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
