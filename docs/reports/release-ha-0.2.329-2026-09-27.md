# Release HA 0.2.329 — 27/09/2026

Usuario solicita publicar tras probar el visor y decidir conservar el método
de entrenamiento actual. Imagen publicada; instalación en HA real pendiente.

## Contenido

- Comprobar predicción desde una observación con sus coordenadas, especie y fecha.
  Ficha completa de IFF/modelo, meteorología, SMI y terreno, con retorno al registro.
- Trazabilidad por artefacto mediante `training-observations.sqlite`: IDs reales
  del ajuste, conjuntos deduplicados e índices para consultas de pertenencia.
  Transporte, instalación e inclusión en el runtime verificados por digest.
- Panel compacto con especie, fecha, abundancia y SÍ verde / NO rojo. Ausencia
  de evidencia se presenta como SIN DATOS o SIN MODELO, nunca como NO.
- Altitud guardada bajo Fecha y bocadillo apuntando al marcador en sus anclajes.
- No cambia el reparto, la selección ni el ajuste de modelos. No se implementa
  el interruptor de ajuste final discutido; el usuario decide dejarlo como está.

## Validación

- Smoke completo: **1.838 pruebas / 52 omitidas, 86,989 s, OK**, código 0.
  `docker-data/release-0.2.329-smoke-unrestricted.log`. El intento inicial quedó
  limitado por seis pruebas con sockets localhost; se conserva su log separado.
- Navegador del mismo código funcional: 77 consultas y 25 de histórico, correcto;
  casos de uso/no uso/sin trazabilidad, altitud, bocadillo, meteorología/SMI,
  retorno, móvil y permisos. `docker-data/compact-training-browser.log`.
- Entrenamiento local lanzado por el usuario: lote
  `operational_20260927T184246Z`, 792/792 ajustes, cero fallos; resultado verificado
  e instalación de cinco versiones confirmada en el registro local.
- Índice instalado: 573.440 bytes, 792 modelos, 226 conjuntos completos,
  SHA/tamaño coincidentes con manifiesto y `PRAGMA quick_check=ok`.
- HA local reconstruida/recreada después del bump: etiqueta 0.2.329, HTTP 200,
  imagen `sha256:a2e8637b638e8f4524329aca1be51f2cd875a29b61eb70613e3369271cc4bd09`.
  19 archivos HA y nueve worker coinciden por SHA con el worktree;
  `docker-data/release-0.2.329-parity.log`.
- Worker ya reconstruido para trazabilidad, sin nuevo reinicio durante release:
  imagen `sha256:a31db15a6cb0bc201bd5b998ae18fffb4c6683a1607b8865c622c2d599187a6c`.
  Coordinadores comprobados: `http://100.111.77.48:8100` y
  `http://rainmapper-ha-ui:8100`, sin cambios.

## Publicación

Una instancia de `build-push-ha-image.sh`, supervisada hasta código 0.
Log `docker-data/release-0.2.329-build.log`. GHCR verificado:

- Tags `0.2.329` y `latest`:
  `sha256:4dac8eb4da389368663df905512ed183f132715d8b407802bf8de677607e8b72`.
- AMD64: `sha256:a722031f13baf77ba5ea05b036d0aa63ea6c21123eaf6b4b20c2f628e8695290`.
- ARM64: `sha256:f5b65c68a04921b9e368443f8d2d688816cca4fb5e6941b5c7e0c09b1a2b2376`.

Código, pruebas, bump, changelog y documentación se reúnen en un único commit
tras verificar GHCR. Observaciones privadas excluidas. Durante esta release no
se modifica HA real ni se lanzan runner, entrenamiento o precálculo.
