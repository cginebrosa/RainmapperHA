# Visor de estaciones Wunderground

- `code/station_research.py`: servidor local, solo loopback.
- `code/web/`: interfaz; `code/vendor/`: MapLibre y licencia.
- `code/tools/` y `code/checks/`: herramientas de adquisición/análisis y pruebas.
- `data/`: SQLite, entradas del análisis, caché, informes y salidas generadas.
  El HTML estático inicial en `data/viewer/` es una salida histórica, no la
  interfaz actual del servidor.

Arrancar con `./local-apps/wunderground/start.command`; abrir
[el visor](http://127.0.0.1:8123/). Si ya está abierto, basta abrir la URL:
no arrancar otro proceso en el mismo puerto. El lanzador antiguo de `scripts/`
se conserva como acceso compatible al nuevo.

`research.sqlite3` conserva revisiones, preliminares, consultas y caché. Con el
servidor abierto también hay archivos `-wal`/`-shm`: no copiar solo el principal.
Para trasladarlo hay que cerrar el visor o utilizar la API de backup de SQLite.
La clave WU sigue leyéndose de la configuración del repo, nunca del navegador.

[Guía de uso](../../docs/station-research-es.md).
