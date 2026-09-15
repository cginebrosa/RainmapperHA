> **Procedimiento sustituido el 15/09/2026.** El paquete descrito abajo es una
> copia histórica recuperable. Para instalar la próxima versión se usa la
> [estructura portable compartida](shared-geography-consolidation-es.md), ya
> preparada en media, sin comandos ni enlaces en el primer arranque.
> No repetir extracción, importación ni publicación manual de esta guía antigua.

# Instalación de la cartografía del mapa en HA

Estado: candidata **local** HA 0.2.304 / worker 1.1.2. No publicada ni instalada
en HA real. Aceptación técnica local completada: circuito operativo, precálculo
activo, seis consultas HA/worker y smoke 1581/48.
[Informe final](../reports/prediction-map-geography-2026-09-15.json).

## Archivos preparados

Directorio local: `backups/ha-map-candidate-20260915/`.

- `prediction-map-local-20260914.tar.gz`: cartografía pública preparada para los
  lectores actuales. 3.510 archivos, 14.538.214.301 bytes sin comprimir.
- `.tar.gz.sha256`: SHA-256 del archivo comprimido.
- `.tar.gz.json`: tamaño, huella de publicación y resumen del paquete.
- Dentro del paquete: `SHA256SUMS`, manifiesto sellado y `publication.json`.
  Este último es una descripción, **no activa** la generación por sí solo.
- `images-arm64.tar`: exportación Docker de las dos imágenes locales verificadas;
  no sustituye la publicación multiarch en GHCR. `images-arm64.tar.sha256` verifica
  esta copia. Tags internos: `rainmapperha:local-ha-ui` y `rainmapper-worker:1.1.2`.
- `source-worktree.tar.gz`: fuentes actuales, incluidos archivos nuevos aún no
  confirmados en Git; con recibo SHA-256 y manifiesto de archivos. Sin volúmenes,
  credenciales del entorno ni `.git`. No sobrescribir datos privados con semillas.
- `before-local-acceptance.tar.gz`: recuperación local previa a las pruebas;
  no es un paquete para sobrescribir los datos de HA real.

El archivo comprimido ocupa 12.127.781.210 bytes. SHA-256:
`2238b9f8451bdead3b09d9371c5632e50289a9ef3cb31c93d7e9dfdbc60aecfc`.
Huella lógica de la cartografía:
`sha256:8ab40e26cddf9567b878611f11c39d079579eb455105839a40ac67610e3f1336`.

El paquete contiene las dependencias de los lectores preparados, no todos los
originales descargados. No supone cobertura ecológica nacional completa: GEODE
fuera de las capas preparadas y otras ampliaciones siguen en el TODO. No contiene
credenciales, usuarios, fichas privadas, observaciones, modelos ni meteorología.

## Importación futura, después de aceptar la candidata

Estas instrucciones se preparan para el operador; no se han ejecutado en la RPi4.

1. Copiar el paquete al almacenamiento de HA. Prever unos 25 GiB libres si se
   mantiene también el comprimido durante la extracción; la cartografía activa
   ocupa 13,54 GiB. Se puede extraer mediante streaming para evitar esa copia
   temporal adicional, conservando el paquete original en el Mac.
2. Extraer en `/media/rainmapper/prediction-map/`, sin sobrescribir una generación
   ya publicada. El paquete coloca sus archivos bajo
   `generations/local-20260914/`. PAX conserva timestamps de nanosegundos necesarios
   para los índices. El SHA del comprimido permite comprobar el transporte; no
   hay verificación periódica de los GiB en HA.
3. Publicar explícitamente desde el contenedor HA, una vez terminada la extracción:

   ```sh
   python /app/scripts/manage-prediction-map-volume.py publish \
     --publication-root /media/rainmapper/prediction-map \
     --generation local-20260914
   ```

   El comando recorre metadatos una vez y reutiliza los hashes preparados en el
   Mac. Si el método de copia perdió precisión en las fechas, añadir
   `--restore-timestamps` restaura los timestamps del manifiesto, tras comprobar
   tamaños; no convierte esto en una comprobación del contenido ni relee rásteres.
   Los datos importados deben proceder del paquete sellado y su transporte fiable.
4. Instalar la configuración del lector en
   `/share/rainmapper/prediction-map/config.json`. El ejemplo local preparado
   mantiene las rutas privadas habituales bajo `/share/rainmapper` y los modelos
   en `/media/rainmapper/mushroom-derived/ml_models`. No copiar encima de una
   configuración existente sin comparar sus rutas. No sobrescribir fichas,
   observaciones, usuarios ni ajustes de HA real con los del laboratorio.
5. Actualizar HA y el worker con las imágenes aceptadas/publicadas. La imagen
   nueva del worker incluye la configuración genérica del mapa; obtiene las
   referencias por sus coordinadores ya emparejados. Conservar íntegro su volumen
   y sus URLs. Un `RAINMAPPER_PREDICTION_MAP_CONFIG` explícito sigue teniendo
   prioridad, y permite limitar el mapa a las asociaciones elegidas.
6. Esperar a que la copia del worker esté preparada antes de consultar. Comprobar
   `/var/lib/rainmapper-worker/map-geography/coordinators/<id>/last-sync.json`:
   la primera vez descarga; al reiniciar sin cambios debe indicar cero bytes.
   La copia vive en el volumen persistente, nunca en la imagen.

## Qué sucede después

HA comprueba el pequeño `CURRENT.json`, no todos los archivos GIS. El sondeo del
worker transporta dos referencias independientes: cartografía y datos privados.
La cartografía se prepara en background, cediendo el canal entre bloques; las
consultas del mapa usan online. Cuando los datos están preparados y online está
ocupado, la consulta puede esperar en la cola acotada del mapa. Una caché pendiente
no se anuncia como preparada ni se sustituye silenciosamente por otra versión.

Un cambio de ficha no cambia la cartografía. Un cambio geográfico se prepara en
una generación nueva en el Mac, con hashes, y se publica explícitamente tras
importarlo. El worker conserva y comparte objetos sin cambios y descarga solo los
que faltan. No editar TIFF/GPKG de una generación activa.

El mapa conserva la URL protegida habitual, la autenticación y las preferencias
por usuario. El permiso de predicción es independiente del rol de administrador.
La preview continúa separada de la autenticación real.
