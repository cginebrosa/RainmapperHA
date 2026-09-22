# HA 0.2.319 — revalidación SMB, 22/09/2026

## Alcance y acceso

Lectura de archivos de HA real mediante SMB LAN `192.168.0.121/share`, montado
en `/Volumes/share-1`, comprobado con `mount`. Los montajes existentes
`/Volumes/share` y `/Volumes/media` apuntaban a Tailscale y no se utilizaron.
Sin SSH, reinicios, cambios de coordinadores, entrenamientos ni precálculos.

## Instalación comprobada; detalle funcional pendiente

`/Volumes/share-1/rainmapper/diagnostics/runtime_state.json` declara:

- `app_version`: `0.2.319`.
- `boot_id`: `20260922T032645Z-boot-299b2b50`.
- `started_at`: `2026-09-22T03:26:45.197Z` (05:26:45 CEST).
- `pending_operations` y `pending_snapshots`: vacíos en el estado leído.

`runtime_metrics.jsonl:1646` contiene el arranque de esa versión y boot. Los
registros posteriores de los runners programados también identifican 0.2.319.
Esto confirma la versión declarada por el proceso, junto a la instalación
confirmada por el usuario; no comprueba el digest del contenedor.

No hay evidencia suficiente en SMB para validar la lista completa de variables
ni su presentación en ninguno de los dos ejecutores. El código actual mantiene
las consultas en `QueryBroker.queries` en memoria y las elimina tras 120 s:
`rainmapper_core/mushroom_map_queries.py:16`, `:32`, `:50` y `:86`.
No escribe sus páginas en disco. La búsqueda de `applicability`, `map.query` y
`prediction.map` en el registro de métricas no devolvió evidencia del detalle.
El directorio `mushroom-data/diagnostics/` sólo contenía los tres informes de
reconciliación de almacenamiento/SoilGrids inventariados.

Completar esta aceptación requiere consultar el mapa vivo y comprobar las páginas
hasta alcanzar el total, sus valores/rangos y su procedencia para cada ejecutor.
Se ha preguntado al usuario por la ampliación de SMB a consultas HTTP LAN; no se
ha ejecutado esa prueba ni se presenta la validación local histórica como real.

## Política y conservación

`mushroom_ml_version_registry.json` referencia
`mushroom_ml_prediction_policy.json`. El archivo separado conserva siete
suspensiones y no incluye `recommendation_policy`. SHA-256 del archivo leído:
`d993bbea760ca8f84f74bae6d6d209e570e4b1638e8fdc61b4503c7dd042ddc7`.
La resolución del código usa la política separada (`mushroom_ml_policy_store.py:66`)
y su valor por defecto es `legacy` (`mushroom_recommendation_policy.py:16`).
No se inspeccionó la política de un runtime ya residente ni se modificó el archivo.

## Registros preparados para la siguiente medición

Copias locales de los cuatro archivos diagnósticos, sin importar datos en ningún
servicio, en `tmp/ha-0.2.319-smb-20260922/`:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| runtime_state.json | 298 | f71a4558ddefdfea854321cf26ee4512c68d96c8b163b66685761d183bb0c03c |
| runtime_metrics.jsonl | 1804287 | 1133e6b36cd85549e3edd0da1c700d61569a93f7f8c542a3516486702ebbb82c |
| runtime_summary.jsonl | 7536103 | 7bb032179ddac01e8f98d38cdd47eedd00e6cb536daef08b124d8cbed138cb51 |
| runtime_anomalies.jsonl | 74874 | 4a7b99126170d409bae44cad9d54acb602102ca9a0e6b02cdf55eef427dc17dc |

Son lecturas sucesivas de registros activos, no un snapshot atómico. La copia de
métricas contiene 114 eventos del boot del servidor actual, entre 03:26:45 y
09:16:38 UTC: arranque, coordinación y runners. Los procesos hijos tienen otros
boot IDs y deben correlacionarse por operación padre al analizar el conjunto.

| Muestra del servidor PID 7 (UTC) | RSS MiB | Cgroup actual MiB |
|---|---:|---:|
| Arranque 03:26:45 | 244,625 | 341,184 |
| Recuperación 600 s, 08:17:31 CEST / 06:17:31 UTC | 279,547 | 764,211 |
| Recuperación 600 s, 11:16:38 CEST / 09:16:38 UTC | 227,285 | 538,156 |

Estas son muestras persistidas, no medidas instantáneas al consultar SMB. No hay
desglose `memory.stat` de caché de archivos/anónima/kernel en los campos de esos
eventos. **Cgroup menos RSS del servidor no equivale a caché medida**: puede
incluir otros procesos y conceptos de memoria. No concluir fuga ni mejora del
precálculo desde estas muestras de runner. El análisis de memoria por fases y
cachés queda como siguiente bloque solicitado, sin generar carga diagnóstica.

## Revisión documental

HEAD comprobado: `dda52e8`, `Release Home Assistant 0.2.319`. Se revisaron los
diffs documentales pendientes, no todos los informes históricos. Se contrastaron
los límites de paginación, política y recepción con el código actual. Antes de
corregir enlaces se comprobó por comparación automatizada que el archivo de
cierre contenía íntegro el `active-context.md` anterior de HEAD.

Se corrigieron 32 enlaces relativos rotos por trasladar el contenido a `reports/`,
sin cambiar el texto histórico; se actualizó el estado de instalación en contexto,
TODO y decisiones. Revisión de enlaces y `git diff --check`, sin pruebas de código
por tratarse exclusivamente de documentación. Sin commit/push en esta revisión.
Observaciones privadas excluidas y conservadas.
