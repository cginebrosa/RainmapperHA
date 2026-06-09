# Rainmapper Docker

This repository can run Rainmapper inside Docker.

## Recommended approach

For Home Assistant, especially on a Raspberry Pi, the recommended approach is:

    RAINMAPPER_MODE=once

Then Home Assistant should start the add-on when needed, for example every day at 23:50.

This avoids keeping a container alive all day just to run Rainmapper for a few minutes.

The internal scheduled mode also exists, but it is mainly useful for local tests or for systems where keeping the container running is acceptable.

## Build

Run:

    docker compose build rainmapper

## Run once

Run with the defaults from `docker-compose.yml`:

    docker compose run --rm rainmapper

This starts a temporary container, runs Rainmapper once, and removes the container when it finishes.

## Run once with temporary parameters

Example:

    docker compose run --rm \
      -e RAINMAPPER_DAYS_INIT=-1 \
      -e RAINMAPPER_DAYS_END=0 \
      -e RAINMAPPER_CREATE_WUNDERGROUND=false \
      rainmapper

## Service mode with Docker Compose

Run:

    docker compose up rainmapper

This starts the service defined in `docker-compose.yml`.

Important:

    docker compose up rainmapper

does not decide whether Rainmapper runs once or stays scheduled.

That behavior is controlled by:

    RAINMAPPER_MODE=once
    RAINMAPPER_MODE=schedule

With the recommended default:

    RAINMAPPER_MODE=once

the service runs once and then stops.

## Internal scheduled mode

Scheduled mode keeps the container alive and runs Rainmapper every day at the configured time.

This is useful for testing or non-Home Assistant deployments.

Temporary scheduled test:

    docker compose run --rm \
      -e RAINMAPPER_MODE=schedule \
      -e RAINMAPPER_SCHEDULE_TIME=23:50 \
      -e RAINMAPPER_TIMEZONE=Europe/Madrid \
      rainmapper

Stop with:

    Ctrl + C

To make scheduled mode the default, edit `docker-compose.yml`:

    RAINMAPPER_MODE: "schedule"
    RAINMAPPER_SCHEDULE_TIME: "23:50"
    RAINMAPPER_TIMEZONE: "Europe/Madrid"

Then run:

    docker compose up rainmapper

## Home Assistant future model

For Home Assistant, the intended model is:

    add-on starts
    Rainmapper runs once
    add-on stops

Then a Home Assistant automation starts the add-on every day.

Example idea:

    alias: Run Rainmapper daily
    trigger:
      - platform: time
        at: "23:50:00"
    action:
      - service: hassio.addon_start
        data:
          addon: local_rainmapper

The exact add-on name will be decided when the Home Assistant add-on structure is created.

## Persistent data

Docker uses this local folder for generated and persistent data:

    docker-data/

It is ignored by Git.

Before the first run, copy the current CSV data:

    mkdir -p docker-data/Data docker-data/Tomap docker-data/Plots
    cp Data/*.csv docker-data/Data/

This local folder is similar to what Home Assistant will later provide through persistent add-on storage.

## Environment variables

Execution mode:

    RAINMAPPER_MODE=once
    RAINMAPPER_MODE=schedule

Schedule:

    RAINMAPPER_SCHEDULE_TIME=23:50
    RAINMAPPER_TIMEZONE=Europe/Madrid

Rainmapper options:

    RAINMAPPER_CREATE_METEOCLIMATIC=true
    RAINMAPPER_CREATE_METEOCAT=true
    RAINMAPPER_CREATE_WUNDERGROUND=true
    RAINMAPPER_DAYS_INIT=-7
    RAINMAPPER_DAYS_END=0
    RAINMAPPER_NOMAPS=false
    RAINMAPPER_NOTOTALS=false
    RAINMAPPER_DAYS_BUCKET=10
    RAINMAPPER_MAX_THREADS=1
    RAINMAPPER_MAX_ATTEMPTS=3

Google Maps API key:

    GMAP_API_KEY=your_api_key

## Example: full temporary run

    docker compose run --rm \
      -e RAINMAPPER_CREATE_WUNDERGROUND=true \
      -e RAINMAPPER_MAX_ATTEMPTS=3 \
      rainmapper

## Current defaults

The current Docker Compose setup runs once with these defaults:

    RAINMAPPER_MODE=once
    RAINMAPPER_TIMEZONE=Europe/Madrid
    RAINMAPPER_DAYS_INIT=-7
    RAINMAPPER_DAYS_END=0
    RAINMAPPER_CREATE_METEOCLIMATIC=true
    RAINMAPPER_CREATE_METEOCAT=true
    RAINMAPPER_CREATE_WUNDERGROUND=true
    RAINMAPPER_NOMAPS: "false"
    RAINMAPPER_NOTOTALS: "false"
    RAINMAPPER_DAYS_BUCKET: "10"
    RAINMAPPER_MAX_THREADS: "1"
    RAINMAPPER_MAX_ATTEMPTS: "3"