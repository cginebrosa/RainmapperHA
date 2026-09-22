# HA 0.2.319 — 22/09/2026

El usuario confirmó «funciona. publicamos HA» tras probar el detalle en HA local.
Imagen publicada; instalación en HA real a cargo del usuario.

## Alcance

- Lista de variables fuera del rango de entrenamiento con scroll, contador y
  carga adicional. Corrige el caso de 33 variables con solo tres ejemplos visibles.
- Consulta diagnóstica opcional por especie/día, páginas compactas de 32 filas,
  cargadas al abrir el desplegable. La consulta normal conserva sus límites e IFF.
- Comprobación de fecha y procedencia para no mezclar generaciones; avisos de
  error y datos cambiados. Página máxima sintética comprobada: menos de 8 KiB.
- Tests de empaquetado alineados con el worker 1.1.5 ya existente.
- Observaciones privadas del usuario excluidas del commit.

## Validación y excepción autorizada

HA local y worker reconstruidos/recreados desde el cambio; 217/117 archivos
efectivos sin diferencias con el checkout. Worker healthy e idle en ambos
carriles. Identidad y hashes de configuración/credenciales conservados, incluidos
los coordinadores `http://100.111.77.48:8100` y `http://rainmapper-ha-ui:8100`.
JavaScript servido por HA local con HTTP 200 y SHA256 idéntico al checkout.

- 97 pruebas dirigidas correctas también dentro de la imagen HA.
- Prueba de navegador: 47 consultas, paginación de 33 filas, scroll y errores.
- Confirmación funcional del usuario en HA local.
- Smoke completo: 1.725 pruebas, 52 skips, correcto; suite Python 82,406 s.
  Registro: `/private/tmp/rainmapper-0.2.319-smoke-final.log`.
- Primer intento: seis restricciones de sockets del sandbox y dos tests con
  expectativa de worker 1.1.4 obsoleta. Segundo intento con permisos adecuados y
  expectativas 1.1.5: correcto. No se cambió código de producción para resolverlos.
- Después del smoke solo bump mecánico, cache-busters y documentación;
  alineación de versiones y `git diff --check` comprobados.

El último circuito completo local es anterior a este cambio. No se ha repetido
entrenamiento ni precálculo. Ante la condición expresa de AGENTS.md para cambios
de contrato, el usuario autorizó excepcionalmente publicar con esta validación:
«Sí, publicar con la validación actual». La excepción se limita a esta release.

Imágenes locales con las que se aceptó el cambio (antes del bump mecánico):
- HA: `sha256:6c52d5e2bf5c9bba161239dcfb506937ecc56d6c8cfb36b08683b0641b845992`.
- Worker: `sha256:571041c90d6d587b124024cf69cec004b74f172d8db9d97300f9a14f5d44bc18`.

## Publicación verificada

Una ejecución de `build-push-ha-image.sh`, supervisada y terminada con código 0.
Registro: `/private/tmp/rainmapper-0.2.319-publish.log`.
Verificación con `docker buildx imagetools inspect` de ambos tags:

- `ghcr.io/cginebrosa/rainmapperha:0.2.319` y `latest`:
  `sha256:fcdf067a7ffc41a89d3715b6dc367348f57ce9711879c56bd0b28bf3b770e65e`.
- linux/amd64: `sha256:da30b05b70a7b19e2720cba13c209dd120808eef7f49f6076854f55996af7e9e`.
- linux/arm64: `sha256:23e205e479dc07cb71963d1d3286b7cb946907430e110072964545c199405ed1`.

No se ha instalado ni reiniciado HA real desde esta sesión. El worker ya tiene
el código compartido desplegado localmente; no se publica una imagen remota suya.
