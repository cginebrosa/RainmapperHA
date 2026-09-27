# Release HA 0.2.326 — 27/09/2026

Usuario: «validado. Publicamos en HA». Publicación completada; instalación real
pendiente a cargo del usuario.

## Contenido

- Coordenadas e incertidumbre en las fichas de observaciones del mapa; cero se
  muestra como «0 m» y la etiqueta se abrevia en es/ca/en.
- Primera foto asociada como miniatura, ampliable dentro de la misma ficha con
  vuelta a datos. Lectura autenticada por ID/revisión y permiso de observaciones;
  vistas raster acotadas en memoria, sin modificar originales ni crear archivos.
- Inclusión de los scripts de reutilización de entradas V2–V6 ya instalados y
  validados en el worker. No cambia la política IDW, modelos ni suspensiones.
- Cierre documental de los diagnósticos de lluvia, memoria y curvas planas.
  Herramientas experimentales de lluvia sólo locales, excluidas de las imágenes.

## Validación

- HA local reconstruida/recreada y aceptada por el usuario. Se revalidaron hashes
  de módulo, adaptador, JS, CSS y etiquetas contra el contenedor; coincidencia.
- Tres scripts de evaluación/preparación idénticos en worktree, HA local y worker.
  El ciclo operativo del usuario con ese código ya había terminado y se verificó
  en el [informe de memoria](worker-evaluation-memory-2026-09-27.md).
- 33 pruebas dirigidas de API/observaciones correctas; navegador con miniatura,
  ampliación, vuelta a datos y ausencia de foto. Captura inspeccionada; HTTP local
  200 y vistas de una foto real local comprobadas dentro del contenedor.
- Smoke completo: **1.829 pruebas en 86,406 s, 52 omitidas, OK**, código 0.
  Registro `docker-data/release-0.2.326-smoke-authorized.log`. Primer intento en
  sandbox: seis errores de permiso al abrir servidores locales; repetición
  autorizada correcta, sin modificar código.
- Después del smoke sólo bump mecánico, cache-busters, changelog y documentación.
  Versiones/cache-busters verificados; `git diff --check` correcto.

## Publicación

Una instancia de `build-push-ha-image.sh`, supervisada hasta código 0. Registro:
`docker-data/release-0.2.326-build.log`. `docker buildx imagetools inspect` confirma:

- Tags `0.2.326` y `latest`: `sha256:dfaf8fc8417599d12fa16913189fb9480ffeb5a7cffcf74b841cc8c91c049f62`.
- amd64: `sha256:ee42323db69161dd925f46f04609eeb825a60f99a3e483f406119cb96dfc4c95`.
- arm64: `sha256:1ee42ad0c4cd08927c6c309fdcf5d24aefd871a256dc339cb48fd59a195ccef3`.

Código, pruebas, bump y documentación en un único commit de release posterior a
la verificación de GHCR. Observaciones privadas fuera del commit y de la imagen
(ésta copia el fichero vacío de defaults). No se reinició el worker ni se tocaron
coordinadores o datos reales; sin SSH, entrenamiento, precálculo ni runner.
