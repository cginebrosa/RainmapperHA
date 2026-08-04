# Flujo de release HA

Referencia operativa completa para publicar una nueva versión de la imagen HA.
**Solo ejecutar con autorización explícita del usuario.**

## Pasos

1. **Revisar estado del repo**
   ```bash
   git status --short
   git diff
   ```

2. **Smoke test**
   ```bash
   PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
   ```
   El smoke test verifica: sintaxis Python/JS/shell, alineación de versiones en
   los tres sitios, cache-busters, fixtures GeoJSON y la suite completa de tests.
   No continuar si falla.

3. **Bump de versión en los tres sitios** (el smoke test falla si no coinciden):
   - `rainmapper-app/config.yaml` → campo `version:`
   - `rainmapper-app/Dockerfile` → `LABEL io.hass.version=`
   - `rainmapper-app/Dockerfile` → `ENV RAINMAPPER_APP_VERSION=`

4. **Actualizar `rainmapper-app/CHANGELOG.md`**
   Añadir sección `## <version>` al principio del fichero con los cambios en
   inglés. Seguir el estilo de las entradas existentes: frases cortas en
   imperativo, mencionar ficheros o símbolos relevantes entre backticks.
   Este fichero es el que muestra HA en el diálogo de actualización.

5. **Actualizar cache-busters de los visores** si han cambiado JS o CSS:
   ```bash
   # Sustituir la versión anterior por la nueva en los dos index.html
   sed -i '' 's/v=0\.2\.X/v=0.2.Y/g' \
     rainmapper_core/viewers/maplibre-viewer/index.html \
     rainmapper_core/viewers/leaflet-viewer/index.html
   ```
   Si no han cambiado JS/CSS, el smoke test igualmente verifica que los
   cache-busters coincidan con la versión — actualizar siempre con el bump.

6. **Segundo smoke test** para verificar que el bump y los cache-busters son correctos:
   ```bash
   PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
   ```

7. **Publicar imagen multi-arch**
   ```bash
   ./scripts/build-push-ha-image.sh
   ```
   Construye para `linux/amd64` y `linux/arm64` y publica a GHCR con tag
   `<version>` y `latest`. Ir directamente con permisos elevados — el flujo
   normal falla en el sandbox.

8. **Verificar digest** (opcional pero recomendado para releases importantes):
   ```bash
   docker buildx imagetools inspect ghcr.io/cginebrosa/rainmapperha:<version>
   ```

9. **Commit y push**
   ```bash
   git add rainmapper-app/config.yaml \
           rainmapper-app/Dockerfile \
           rainmapper-app/CHANGELOG.md \
           rainmapper_core/viewers/maplibre-viewer/index.html \
           rainmapper_core/viewers/leaflet-viewer/index.html \
           # + cualquier otro fichero modificado en este release
   git commit -m "Release Home Assistant <version>

   <descripción breve de los cambios>

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   git push
   ```

10. **Avisar al usuario** para que instale y pruebe en HA.

## Notas

- No retrasar la prueba en HA por documentación de cierre o hashes documentales.
- Documentación de continuidad (`docs/active-context.md`) se actualiza después
  del release o al cerrar sesión.
- No limpiar GHCR durante una instalación HA en curso. Conservar siempre:
  versión activa, `latest`, rollback inmediato y manifests auxiliares multi-arch.
  Ver procedimiento exacto de limpieza en `docs/decisions.md` (sección GHCR).
- No existe imagen HA de desarrollo/sideload. No crearla como atajo.
