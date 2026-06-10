# Rainmapper Docker

This repository can run Rainmapper inside Docker.

## Recommended approach

For Home Assistant, especially on a Raspberry Pi, the recommended approach is:

    MODE=update

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

`MODE=once` is kept as an alias for `MODE=update`.

## Run once with temporary parameters

Example:

    docker compose run --rm \
      -e DAYS_INIT=-1 \
      -e DAYS_END=0 \
      -e CREATE_WUNDERGROUND=false \
      rainmapper

Short variable names are accepted for manual commands. The longer `RAINMAPPER_...` names are also supported for compatibility with `docker-compose.yml`.

## Run modes

Update weather data and generate `Tomap` CSV files:

    docker compose run --rm \
      -e MODE=update \
      rainmapper

Generate map HTML files from existing `Tomap` CSV files:

    docker compose run --rm \
      -e MODE=maps \
      rainmapper

Update weather data and then generate map HTML files:

    docker compose run --rm \
      -e MODE=all \
      rainmapper

`MODE=maps` runs `Rainmapper_Client.py` and writes HTML files to:

    docker-data/Plots/

## Show Rainmapper help

Run:

    docker compose run --rm \
      -e MODE=help \
      rainmapper

## Service mode with Docker Compose

Run:

    docker compose up rainmapper

This starts the service defined in `docker-compose.yml`.

Important:

    docker compose up rainmapper

does not decide whether Rainmapper runs once or stays scheduled.

That behavior is controlled by:

    MODE=once
    MODE=update
    MODE=maps
    MODE=all
    MODE=schedule

With the recommended default:

    RAINMAPPER_MODE=once

the service runs once and then stops.

## Internal scheduled mode

Scheduled mode keeps the container alive and runs the update task every day at the configured time.

This is useful for testing or non-Home Assistant deployments.

Scheduled mode runs `Rainmapper.py` only. It does not generate map HTML files.

Temporary scheduled test:

    docker compose run --rm \
      -e MODE=schedule \
      -e SCHEDULE_TIME=23:50 \
      -e TIMEZONE=Europe/Madrid \
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

Before the first run, create the persistent folders:

    mkdir -p docker-data/Data docker-data/Tomap docker-data/Plots

Rainmapper can rebuild its CSV files in `docker-data/Data` on first run. If you already have historical CSV files, copy them into `docker-data/Data` before running the container.

This local folder is similar to what Home Assistant will later provide through persistent add-on storage.

## Wunderground stations

The Wunderground station list is read from:

    docker-data/stations.txt

This file is mounted into the container as:

    /app/stations.txt

To add or remove Wunderground stations, edit `docker-data/stations.txt`.

If the file does not exist yet, initialize it from the repository copy:

    cp stations.example.txt docker-data/stations.txt

## Environment variables

Execution mode:

    MODE=help
    MODE=once
    MODE=update
    MODE=maps
    MODE=all
    MODE=schedule
    RAINMAPPER_MODE=once
    RAINMAPPER_MODE=update
    RAINMAPPER_MODE=maps
    RAINMAPPER_MODE=all
    RAINMAPPER_MODE=schedule

Schedule:

    SCHEDULE_TIME=23:50
    TIMEZONE=Europe/Madrid
    RAINMAPPER_SCHEDULE_TIME=23:50
    RAINMAPPER_TIMEZONE=Europe/Madrid

Rainmapper options:

    CREATE_METEOCLIMATIC=true
    CREATE_METEOCAT=true
    CREATE_WUNDERGROUND=true
    DAYS_INIT=-7
    DAYS_END=0
    NOMAPS=false
    NOTOTALS=false
    DAYS_BUCKET=10
    MAX_THREADS=1
    MAX_ATTEMPTS=3
    METEOCLIMATIC_PATTERN=ESCAT

The longer names are also accepted:

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
    RAINMAPPER_METEOCLIMATIC_PATTERN=ESCAT

Google Maps API key:

    GMAP_API_KEY=your_api_key

## Example: full temporary run

    docker compose run --rm \
      -e CREATE_WUNDERGROUND=true \
      -e MAX_ATTEMPTS=3 \
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
    RAINMAPPER_NOMAPS=false
    RAINMAPPER_NOTOTALS=false
    RAINMAPPER_DAYS_BUCKET=10
    RAINMAPPER_MAX_THREADS=1
    RAINMAPPER_MAX_ATTEMPTS=3
    RAINMAPPER_METEOCLIMATIC_PATTERN=ESCAT
