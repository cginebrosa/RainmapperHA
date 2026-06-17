# Historical Data Safety

## Objetivo
Los historicos CSV son el activo principal de Rainmapper. Antes de tocar codigo que pueda escribir en `Data/`, especialmente cambios en `Rainmapper.py`, pandas, merges, fechas, deduplicado o columnas, el cambio debe probarse sobre una copia y con backup disponible.

## Regla operativa
No ejecutar cambios de escritura contra historicos reales sin una de estas protecciones:

- backup reciente creado con `scripts/backup-data.sh`;
- ejecucion en una copia temporal de `docker-data` o `/share/rainmapper`;
- validacion antes/despues con `scripts/check-history.py`.

## Backup local
Para respaldar datos locales:

```bash
./scripts/backup-data.sh docker-data
```

Para respaldar solo `Data/`:

```bash
./scripts/backup-data.sh Data
```

El backup se crea por defecto en `backups/` como `.tar.gz`. Esa carpeta no debe versionarse.

## Validacion de historicos
Validar CSV existentes:

```bash
./scripts/check-history.py docker-data/Data
```

Comparar una copia posterior contra una copia anterior:

```bash
./scripts/check-history.py /tmp/rainmapper-after/Data --compare-before /tmp/rainmapper-before/Data
```

La comparacion falla si desaparece un CSV, cambian columnas o baja el numero de filas. Si un cambio esperado reduce filas, usar `--allow-row-drop` solo despues de justificarlo en la tarea.

## Flujo recomendado para cambios de pandas o escritura CSV
1. Ejecutar `./scripts/smoke-test.sh`.
2. Crear backup: `./scripts/backup-data.sh docker-data`.
3. Copiar datos a una ruta temporal fuera del historico real.
4. Ejecutar el cambio contra esa copia.
5. Validar con `./scripts/check-history.py`.
6. Revisar `Tomap` y visores generados.
7. Solo despues ejecutar contra datos reales.

## Limitaciones
`check-history.py` valida estructura basica y cambios obvios. No detecta todavia todos los problemas semanticos posibles, como lluvias anormalmente altas, fechas incorrectas dentro de columnas no normalizadas o cambios meteorologicos sutiles. Es una red de seguridad operativa, no un test funcional completo.
