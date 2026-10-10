# Vídeo de observación y cierre del progreso — 06/10/2026

## Diagnóstico comprobado

El vídeo privado indicado por el usuario es un MP4 H.264/AAC, 478 × 850,
31,161733 s y 6.713.964 bytes. FFmpeg 7.1.5 de la imagen HA rechazaba su matriz
de color reservada con `Invalid color space`. Se reprodujo el fallo con el
archivo original, sin modificarlo. Su reproducción en el Mac no ejercita esa
conversión del servidor.

La fecha de captura `0000:00:00 00:00:00` y la ausencia de GPS explican el aviso
EXIF de la vista previa, pero no deben impedir adjuntar sólo el archivo.
El guardado asíncrono devolvía `ok: true` aunque la acción hubiera registrado
un error de guardado, ocultando el fallo al volver a la página.

## Corrección

- `rainmapper-app/app/web_server.py`, `run_observation_video_conversion`:
  conversión normal primero. Sólo ante `Invalid color space` y un vídeo H.264
  se copia temporalmente el flujo con `h264_metadata=matrix_coefficients=2`
  (matriz sin especificar), y se reintenta la conversión una vez. No se modifican
  los fotogramas del original ni se presupone una matriz BT.709.
- Conversión y cartel usan el mismo tratamiento. Los límites existentes de
  duración y dimensiones se mantienen; otros errores se propagan.
- Resultado de la acción aislado por petición mediante `ContextVar`; los fallos
  de guardado asíncrono devuelven HTTP 422 con el mensaje concreto. La interfaz
  muestra el error y conserva borrador y archivo seleccionado.
- `render_mushroom_rebuild_progress_modal`: botón **Cerrar** visible también
  durante la ejecución. Retira el modal y detiene sus siguientes consultas;
  no solicita cancelación del trabajo.

El cambio de coordenadas conserva su requisito de respuesta DEM válida. Es una
limitación separada, pendiente de revisión; no intervino en la prueba de adjunto.

## Validación local

- `tests/test_observation_video_upload.py`: cuatro pruebas sobre reintento
  acotado, errores ajenos/no H.264, adjunto sin EXIF/DEM y respuestas asíncronas.
- Suite `tests.test_web_server_auth`: 353 pruebas aprobadas. Tras añadir el cierre
  visible, cinco pruebas dirigidas aprobadas, incluida la del modal.
- Guardado real en un almacén aislado usando el vídeo y una copia de la
  observación: correcto en 2,0 s en esa prueba, sin consultar DEM ni cambiar
  fecha, coordenadas o microárea. Resultado H.264/AAC, 270 × 480, 906.910 bytes,
  con cartel JPEG. No se guardó ni modificó la observación real.
- Navegador en HA local: vista previa permite adjunto sin metadatos; un error
  de guardado interceptado se muestra y conserva el formulario/archivo. Revisión
  visual a 390 px. Cierre de progreso comprobado sin petición de cancelación.
- HA local reconstruido/recreado después del último cambio y HTTP 200 comprobado.
  SHA-256 de `web_server.py` igual en repositorio y contenedor:
  `58b040a2c59b440bcc870c0c85d19f1bed980a8478954c88a0dd4f9b2be71d74`.
  Worker sin reconstruir/reiniciar; no se lanzaron ni cancelaron trabajos.

Recibos privados en `tmp/observation-video-20261006/`: `auth-tests.log`,
`final-tests.log`, `isolated-save.json`, `browser.json`, `save-error-mobile.png`
y `build-ha-final.log`. Original conservado, SHA-256
`3587a1aaa3545e87a01c39e45806a4cbaca3e7d73021e600d293ad5341d17ed7`.

El reintento cubre este defecto de cabecera H.264 también en otros archivos;
no garantiza convertir cualquier vídeo dañado o formato incompatible. Las
pruebas no validan la selección/comparación histórica que ejecuta el usuario.
