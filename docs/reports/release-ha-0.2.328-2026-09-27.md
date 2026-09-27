# Release HA 0.2.328 — 27/09/2026

Usuario valida local y solicita publicar para probar en móvil. Publicación
completada; instalación y prueba móvil pendientes a cargo del usuario.

## Contenido y validación

- Tabla de observaciones ocupa la altura disponible del panel, conservando
  paginación, cabecera y scroll. Prueba local: 12 → 18 filas completas a
  1728×1200; a 700×900 conserva scroll y acceso a la última fila.
- Ficha del mapa: Bosque/Bosc/Forest y espaciado compacto; miniatura y enlace
  permanecen visibles mientras los datos largos se desplazan. Foto ampliable
  y retorno conservados; enlace disponible también sin foto.
- Cómo llegar / Com arribar / Directions abre Google Maps con las coordenadas
  como destino, sin fijar origen ni transporte. Usuario elige sólo enlace,
  sin círculo. No se atribuye a Maps URLs soporte para círculos o texto propio.
- Navegador aislado con visor real: etiqueta, URL/destino, miniatura/enlace,
  ampliación/retorno, caso sin foto y suite del visor correctos. Evidencia local
  en `docker-data/observation-popup-layout/browser-directions.log`; layout de
  tabla en `docker-data/observation-table-layout`.
- HA local reconstruida/recreada desde el código aceptado. Paridad SHA-256:
  servidor `a00dbdb5bf0d2531b72d3db8ad1393282a5fa28aec605b93691c1c602468977c`;
  JS `8161a553e7fd5f3c1568578ac5968e7654233a10d934318a1ab3508b64241a03`;
  CSS `c5b9e92ffa556e8ef215951ac8dbe0581dd710f4a7e32a1215c2e3cf9cdc5823`;
  etiquetas `02927207f99ffc2db2907d2d36441fa63498d9b7ef6a9e996ed8515618a42b89`.
  Recursos servidos HTTP idénticos y etiquetas efectivas comprobadas.
- Smoke: **1.831 pruebas, 52 omitidas, 90,436 s, OK**, código 0.
  `docker-data/release-0.2.328-smoke.log`. Después sólo bump mecánico,
  cache-busters, changelog y documentación; versiones alineadas.

## Publicación

Una instancia de `build-push-ha-image.sh`, supervisada hasta código 0.
Registro `docker-data/release-0.2.328-build.log`. Verificación GHCR:

- Tags `0.2.328` y `latest`: `sha256:9cca5302c34674cf115caef37842edcac486f6e92b92a2917537c18dc865266d`.
- AMD64: `sha256:892a76e862d38bb320d3f4550d68623762ed6e58f7ca1820ea6148b3fb9e84c0`.
- ARM64: `sha256:1b36682cdd680e2d4dba7e9596e6280d83629cdb5b56a48efff6195f5a1ec73e`.

Único commit de código, pruebas, bump y documentación tras verificar GHCR.
Observaciones privadas excluidas. Worker, coordinadores, suspensiones y datos
reales intactos; sin entrenamiento, precálculo, runner ni SSH.
