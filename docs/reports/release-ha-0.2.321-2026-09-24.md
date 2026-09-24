# HA 0.2.321 — observaciones en el mapa (24/09/2026)

## Alcance

Publicación solicitada por el usuario tras aceptar el comportamiento en HA
local: capa de observaciones con permiso individual desactivado por defecto,
opción global móvil también desactivada, selector de especies, iconos de seta,
grupos desplegables con fechas y ficha. Repetir pulsación cierra ficha o grupo.
La ficha reúne hosts/bosque de campo y GIS aceptado, nombres comunes traducidos
y fase lunar de la fecha observada mediante una función offline reutilizable.
La capa conserva todas las fechas y funciona junto al histórico y la predicción.

Incluye los ajustes históricos pendientes: avisos diferenciados de
actualización/sincronización/ocupación/incompatibilidad/conexión y retorno directo
a hoy desde el calendario activo; el indicador superior conserva el selector.
No modifica los contratos operativos ni los artefactos de entrenamiento o
precálculo. La fase lunar no se integra en modelos en esta versión.

## Validación y nueva regla de alcance

El usuario aclara expresamente que entrenamiento y precálculo sólo deben ser
obligatorios cuando el cambio les afecte. Se actualizan `AGENTS.md`,
`docs/release-flow.md` y `docs/codex-start-here.md` como regla general, no excepción
por versión. Para esta entrega de UI/mensajes no se ejecutan trabajos operativos.

- Smoke definitivo: **1.751 pruebas, 52 skips, OK**, 79,162 s. Log:
  `/private/tmp/rainmapper-0.2.321-smoke.log`.
- Navegador real con mapa y API sintética: permisos/revocación, observaciones,
  spiderfy, fechas, ficha/GIS/luna, cierre y reapertura, compatibilidad con
  histórico/predicción y control móvil. Log final:
  `/private/tmp/rainmapper-observations-moon-browser.log`; resultado OK,
  74 consultas de demostración y 25 históricas.
- HA local y worker existente reconstruidos desde el mismo código y recreados;
  worker libre en foreground/background antes de reiniciarlo. Paridad efectiva
  **224/125 archivos**, sin diferencias. Evidencia en
  `tmp/release-0.2.321/{before,after,parity}.json`.
- Manifiesto HA:
  `33d91b11c01dab38081b99b1f165b67ed2cba5b1e19c1819880628d6153a0d97`.
  Manifiesto worker:
  `2784d396495e916c88e7068ad6e0aa7f191eef35de4b221012f6fc2638c87ff7`.
- Configuración y credenciales de ambos coordinadores, identidad del worker,
  observaciones privadas repo/local y política/suspensiones comparadas por
  huellas, sin cambios. No SSH ni acceso directo por Tailscale.
- Después del smoke/paridad sólo bump mecánico HA a 0.2.321, cache-busters,
  changelog y documentación. Las imágenes locales de aceptación conservan
  metadatos 0.2.320 y worker 1.1.6; no confundirlos con la imagen publicada.

## Publicación

Build multi-arquitectura terminado con código 0. GHCR comprobado para 0.2.321 y
latest, mismo digest:
`sha256:4ec6de37a3d926d1b555c6065152dd94a28ce90b68bc1be008ac008fa73a025d`.
Ambos contienen `linux/amd64` y `linux/arm64`, además de sus attestations.
Log `/private/tmp/rainmapper-0.2.321-publish.log` y consultas persistidas en
`tmp/release-0.2.321/ghcr-{0.2.321,latest}.txt`.

Código, pruebas, bump y cierre documental en un único commit
`Release Home Assistant 0.2.321`; consultar Git para hash y estado del push.
Observaciones privadas excluidas. Instalación en HA real a cargo del usuario;
última versión confirmada allí: 0.2.320.
