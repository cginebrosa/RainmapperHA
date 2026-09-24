# Flujo de release HA

Referencia operativa completa para publicar una nueva versión de la imagen HA.
**Solo ejecutar con autorización explícita del usuario.**

## Pasos

HA local es la puerta de aceptación de HA real y debe reconstruirse desde el
código candidato. El worker sólo requiere reconstrucción/recreación si el cambio
le afecta; una release exclusiva de UI no obliga a tocarlo.

1. **Revisar estado del repo**
   ```bash
   git status --short
   git diff
   ```

2. **Reconstruir los componentes locales afectados desde el mismo código**

   Antes de probar una candidata, reconstruir HA local desde el estado actual
   del worktree. Reconstruir/recrear también el worker sólo si cambian código
   que ejecuta, dependencias, empaquetado, contratos o artefactos que consume o
   produce. UI/presentación no requiere reconstruir ni reiniciar el worker,
   aunque su imagen incluya módulos compartidos no utilizados por él. Esta es
   una regla general acordada el 24/09/2026, no una excepción de release.
   Para cada componente afectado, no reutilizar una imagen anterior aunque el
   contenedor esté sano o la etiqueta parezca correcta.

   Antes de recrear el worker, registrar su URL de coordinador persistida y su
   huella; después comprobar que no han cambiado. No sustituir nunca su destino
   por uno local ni por otro fallback. Recrear únicamente los servicios locales
   implicados y conservar sus volúmenes de datos.

   Verificar dentro de los contenedores afectados las versiones o huellas de los
   ficheros compartidos relevantes. La comprobación debe demostrar qué código
   ejecutan realmente; comparar solo el checkout o las etiquetas no sirve.

3. **Ejecutar el circuito funcional local mediante el worker**

   **Regla de alcance acordada con el usuario el 24/09/2026:** entrenamiento y
   precálculo son obligatorios sólo cuando el cambio afecte a esos procesos, sus
   entradas, contratos operativos, ejecución o artefactos. No exigirlos por tocar
   un archivo del coordinador o del worker si el cambio sólo afecta a interfaz,
   presentación o mensajes. No es una excepción por versión.

   Para cambios que afecten al circuito operativo de entrenamiento/precálculo,
   ejecutar las etapas afectadas y las dependencias necesarias para validarlas:

   1. Prueba de asignación y retorno al coordinador local.
   2. Reconstrucción operativa completa.
   3. Entrenamiento base y entrenamiento multiversión.
   4. Recepción, validación y promoción de la generación.
   5. Precálculo semanal mediante el worker.
   6. Recepción, validación y activación del precálculo.

   Auditar el registro persistente, los identificadores y huellas, los
   artefactos activos, la limpieza terminal y la ausencia de resultados
   parciales. Que la imagen compile o arranque no valida el circuito.

   Para cambios de UI, permisos o mensajes, bastan las pruebas dirigidas del
   comportamiento afectado, navegador cuando corresponda y el smoke obligatorio;
   no lanzar entrenamientos ni precálculos ajenos al cambio. Conservar la
   reconstrucción/paridad local del paso 2. El usuario sigue lanzando los trabajos
   operativos cuando sean necesarios.

   **No continuar hacia HA real hasta que la validación aplicable termine
   correctamente y el usuario acepte expresamente el resultado local.** Si después cambia
   código ejecutable, reconstruir los componentes afectados y repetir la
   validación proporcional afectada.

4. **Smoke test**
   ```bash
   PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
   ```
   El smoke test verifica: sintaxis Python/JS/shell, alineación de versiones en
   los tres sitios, cache-busters, fixtures GeoJSON y la suite completa de tests.
   No continuar si falla. Este es el único smoke completo ordinario de la
   release: debe ejecutarse sobre el código definitivo que se va a publicar.

5. **Bump de versión en los tres sitios** (el smoke test falla si no coinciden):
   - `rainmapper-app/config.yaml` → campo `version:`
   - `rainmapper-app/Dockerfile` → `LABEL io.hass.version=`
   - `rainmapper-app/Dockerfile` → `ENV RAINMAPPER_APP_VERSION=`

6. **Actualizar `rainmapper-app/CHANGELOG.md`**
   Añadir sección `## <version>` al principio del fichero con los cambios en
   inglés. Seguir el estilo de las entradas existentes: frases cortas en
   imperativo, mencionar ficheros o símbolos relevantes entre backticks.
   Este fichero es el que muestra HA en el diálogo de actualización.

7. **Actualizar cache-busters de los visores** si han cambiado JS o CSS:
   ```bash
   # Sustituir la versión anterior por la nueva en los dos index.html
   sed -i '' 's/v=0\.2\.X/v=0.2.Y/g' \
     rainmapper_core/viewers/maplibre-viewer/index.html \
     rainmapper_core/viewers/leaflet-viewer/index.html
   ```
   Si no han cambiado JS/CSS, el smoke test igualmente verifica que los
   cache-busters coincidan con la versión — actualizar siempre con el bump.

8. **Verificar el bump y los cache-busters.** De las comprobaciones del smoke
   test, solo `check_versions` y `check_viewer_asset_versions` dependen de lo
   que se acaba de tocar (versión en los 3 sitios, cache-busters de los dos
   visores); el resto (sintaxis, suite completa de tests, fixtures) no
   depende de esos ficheros y ya se validó en el paso 4. El script no admite
   ejecutar un subconjunto de comprobaciones, así que basta con verificar a
   mano:
   ```bash
   grep -n 'version:' rainmapper-app/config.yaml
   grep -n 'io.hass.version\|RAINMAPPER_APP_VERSION' rainmapper-app/Dockerfile
   grep -n 'v=0\.2\.' rainmapper_core/viewers/maplibre-viewer/index.html \
     rainmapper_core/viewers/leaflet-viewer/index.html
   ```
   Repetir el smoke test completo aquí solo si además se ha tocado código
   entre el paso 4 y el bump (poco habitual en este flujo).

9. **Publicar imagen multi-arch**
   ```bash
   ./scripts/build-push-ha-image.sh
   ```
   Construye para `linux/amd64` y `linux/arm64` y publica a GHCR con tag
   `<version>` y `latest`. Ir directamente con permisos elevados — el flujo
   normal falla en el sandbox.

   **Supervisión obligatoria del proceso:**
   - Ejecutar una sola instancia del script. No lanzar un segundo build porque
     el primero tarde o deje de mostrar salida.
   - Si la herramienta devuelve un identificador de sesión, conservarlo y
     consultar esa misma sesión cada 20–30 segundos, también durante el push.
     Informar brevemente al usuario al menos cada minuto. Un proceso activo o
     «pushing layers» no demuestra transferencia ni publicación terminada.
   - Si no hay avance, comprobar el registro y el progreso antes de describirlo
     como una subida lenta. No dejar esperas largas sin diagnóstico ni lanzar
     otro build simultáneo. Conservar logs de los intentos cancelados.
   - Si la release requiere también una versión nueva del worker, preparar su
     publicación sin cambiar los destinos configurados del único worker.
   - Al terminar, recuperar la misma sesión y verificar el resultado y GHCR.
   - Si la sesión local no devuelve el control pero GHCR confirma los tags,
     digest y plataformas, documentar el estado antes de decidir si procede
     interrumpir el cliente. No lanzar nunca otro build para sustituirlo.
   - Si la verificación remota falla o está incompleta, no hacer commit/push ni
     anunciar la release como publicada. Diagnosticar primero Docker, red y
     credenciales.
   - Al terminar, el script conserva localmente solo la versión HA más reciente
     más `latest` y acota la parte privada/reclamable de la caché reconstruible
     de Buildx a 8 GiB. Docker puede contabilizar aparte capas compartidas con
     imágenes conservadas; no representan una segunda ocupación exclusiva. Se
     puede desactivar puntualmente con `LOCAL_IMAGE_CLEANUP=0` o
     `LOCAL_BUILD_CACHE_CLEANUP=0`, pero no hacerlo como rutina.

10. **Verificar digest y plataformas** (obligatorio):
   ```bash
   docker buildx imagetools inspect ghcr.io/cginebrosa/rainmapperha:<version>
   docker buildx imagetools inspect ghcr.io/cginebrosa/rainmapperha:latest
   ```
   Confirmar que ambos tags tienen el mismo digest y contienen manifests para
   `linux/amd64` y `linux/arm64`. Si una consulta se queda esperando, limitarla,
   informar al usuario y reintentar una sola vez antes de diagnosticar Docker.

11. **Cerrar documentación, hacer un único commit y push**

   Tras verificar GHCR, actualizar la documentación de continuidad y los
   resultados finales de la release. Incluir código, pruebas, bump, changelog y
   documentación en **un solo commit**; no hacer un commit previo al build ni
   otro commit documental posterior.

   ```bash
   git add rainmapper-app/config.yaml \
           rainmapper-app/Dockerfile \
           rainmapper-app/CHANGELOG.md \
           rainmapper_core/viewers/maplibre-viewer/index.html \
           rainmapper_core/viewers/leaflet-viewer/index.html \
           # + cualquier otro fichero modificado en este release
   git commit -m "Release Home Assistant <version>

   <descripción breve de los cambios>"
   git push
   ```

12. **Avisar al usuario** para que instale y pruebe en HA.

## Notas

- Aplicar validación incremental: no repetir el smoke después de commit/push o
  de actualizar únicamente documentación. Repetir solo si cambió código,
  dependencias, empaquetado o artefactos ejecutables desde el último smoke.
- El changelog y los metadatos necesarios para construir la imagen se preparan
  antes del build. La documentación de continuidad y los hashes finales se
  cierran después de verificar GHCR y antes del único commit.
- No limpiar GHCR durante una instalación HA en curso. Conservar siempre:
  versión activa, `latest`, rollback inmediato y manifests auxiliares multi-arch.
  Ver procedimiento exacto de limpieza en `docs/decisions.md` (sección GHCR).
- No existe imagen HA de desarrollo/sideload. No crearla como atajo.
