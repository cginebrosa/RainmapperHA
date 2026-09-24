# HA 0.2.322 — filtro de observaciones y aviso GIS/EXIF (24/09/2026)

## Alcance

Release autorizada tras aceptación local. Añade Favorable / Desfavorable / Todas
sobre el selector de especies, con Todas al entrar. El catálogo de abundancias se
carga una vez por sesión y se libera al salir; sólo prediction_favorable numérico
igual a 1 es favorable. Puntos, grupos y recuentos siguen el filtro en memoria,
sin nuevas consultas de catálogo ni filtro por fecha histórica.

Al duplicar y aplicar EXIF de una foto tomada en otro punto, el formulario
retira las marcas GIS obsoletas y avisa antes de guardar. Conserva GIS aceptado
si se reemplaza sólo la imagen o se mantienen las coordenadas normalizadas.
La validación geográfica del servidor y los datos manuales no cambian.
No modifica entrenamiento, precálculo ni contratos operativos del worker.

## Validación

- Smoke: 1.754 pruebas, 52 skips, OK, 79,759 s.
  `/private/tmp/rainmapper-0.2.322-smoke-authorized.log`.
  El primer intento bajo sandbox falló en pruebas con sockets localhost por
  PermissionError; se repitió fuera del sandbox sin cambios de código.
- Navegador del filtro OK (`/private/tmp/rainmapper-observations-filter-browser.log`)
  y del flujo real de aplicación EXIF OK (`/private/tmp/rainmapper-gis-exif-browser.log`).
  11 pruebas GIS/duplicación dirigidas también OK.
- HA local reconstruido/recreado y 224 archivos efectivos coincidentes, huella
  `c14aa8c46ae023b27e5c1b9f279ac22d23e177b570e24e3d1076fa1887ce1bf2`.
  Evidencia `tmp/release-0.2.322/local-parity.json`.
- Tras validación sólo bump mecánico a 0.2.322, cache-busters, changelog y docs;
  la imagen local de aceptación conserva metadatos 0.2.321.

## Worker y datos protegidos

El usuario aclara que reconstruir/recrear el worker sólo es obligatorio si se
modifica código que ejecuta, dependencias, empaquetado, contratos o artefactos
que consume/produce. Una release de UI/presentación no lo requiere. Regla general
reflejada en AGENTS.md, docs/release-flow.md y docs/codex-start-here.md.

Se había iniciado un build por la regla anterior y terminó antes de detenerlo.
No se recreó ni reinició el worker: ID y StartedAt idénticos antes/después,
configuración, credenciales, identidad y coordinadores conservados. El trabajo
activo inicialmente finalizó durante la sesión. No se lanzó entrenamiento,
precálculo, SSH ni se cambiaron destinos o suspensiones.

Comparación de huellas: JSON privado del repo y política de predicción intactos.
El JSON de observaciones local cambió durante la sesión concurrente, por lo que
la comprobación global de igualdad detectó esa diferencia. No fue editado por
las acciones de release ni incluido en commit. No se restauraron datos privados.
Snapshots de evidencia: tmp/release-0.2.322/{before,after}.json.

## Publicación

Build multi-arquitectura terminado con código 0. Tags GHCR 0.2.322 y latest
verificados con digest común:
`sha256:473829410c365aa76c4b606c84956af72f7987ee8b2c24411ba25a5883efe67c`.
Ambos contienen linux/amd64 y linux/arm64.
Log: `/private/tmp/rainmapper-0.2.322-publish.log`.
Consultas: `tmp/release-0.2.322/ghcr-{0.2.322,latest}.txt`.

Un único commit `Release Home Assistant 0.2.322` reúne código, pruebas, bump,
changelog y cierre documental. Consultar Git para hash/estado de push.
Instalación real pendiente del usuario; el agente no la ha realizado.
