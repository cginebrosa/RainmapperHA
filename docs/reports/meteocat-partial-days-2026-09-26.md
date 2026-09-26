# Meteocat: días parciales sobrescriben totales — 26/09/2026

Investigación solicitada tras publicar HA 0.2.324, mientras el usuario la instala.
Posteriormente el usuario autorizó corregir el código en local y reparar la copia
de HA descargada en `docker-data/Data`, para subirla a real tras comprobarla.
La reparación se validó primero en una candidata separada y después se aplicó
a real con el add-on parado, confirmado por el usuario. Sin SSH, entrenamiento
ni precálculo.

## Resultado confirmado

Los registros persistidos de Meteocat YB (Olot) y W9 (la Vall d’en Bas) no
conservan los totales diarios completos de los días comprobados:

| Fecha de septiembre | YB oficial / guardado (mm) | W9 oficial / guardado (mm) | Meteoclimatic Olot A / B guardado (mm) |
|---|---:|---:|---:|
| 08 | 0,2 / 0,1 | 3,1 / 0,1 | 0 / 0 |
| 09 | 54,8 / 0 | 44,7 / 0 | 55,2 / 54,8 |
| 16 | 7,1 / 0 | 14,5 / 0,1 | 7,6 / 8,4 |
| 18 | 0,2 / 0 | 0,2 / 0 | 0,4 / 0,4 |

A: ESCAT1700000017800A (Olot - Pla de Dalt).
B: ESCAT1700000017800B (Olot-SPM).
Los totales oficiales de la tabla se agregan por día UTC, como la consulta
actual de Rainmapper; Meteoclimatic usa sus resúmenes del día local. La pérdida
constatada compara la misma estación Meteocat y su propio grupo diario, por lo
que no depende de equiparar jornadas de redes distintas.

Fuente original: [lecturas XEMA, dataset nzvn-apee](https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json),
filtrada por YB/W9, septiembre 2026 y variables 35, 40, 42, 3. La consulta completa
abarca 01–25/09; la primera comprobación de YB acredita 48 lecturas por variable y
día entre 08–20/09. Datos de Rainmapper: `Data/Meteocat_incremental.csv` y
`Data/Meteoclimatic_incremental.csv` del volumen share.

## Mecanismo y evidencia

1. `rainmapper_core/rainmapper.py:get_query_date` convierte medianoche local a
   UTC. En septiembre, el inicio cae a las 22:00 del día UTC anterior.
2. `get_myquery_rain_all` y `get_myquery_conditions_all` recortan por ese intervalo,
   pero agrupan con `date_trunc_ymd(data_lectura)` por día UTC. El primer grupo
   contiene sólo 22:00–23:30, cuatro lecturas de media hora por variable.
3. `get_results_rain_xema` asigna fecha a ese grupo a partir de medianoche UTC
   más dos horas y un segundo. No lo desplaza al día local siguiente ni indica
   que contiene sólo parte del día.
4. `save_incremental_meteocat` captura el lote para el histórico y llama a
   `upsert_incremental`; éste sustituye los valores previos por los nuevos no
   nulos. Un cero parcial es un número válido y sobrescribe la lluvia completa.
5. Según avanza la ventana de actualización, el día que queda en su borde
   inicial se sobrescribe con ese fragmento. Los defaults publicados son -7/0.

Prueba directa: nueva consulta oficial restringida a `date_extract_hh(data_lectura)>=22`
para 01–18/09. Coinciden **72/72 valores por estación, 144/144 en total**:
lluvia, temperatura máxima, temperatura mínima y humedad máxima. No es una
conjetura basada sólo en las diferencias entre estaciones.

El defecto es compartido por la consulta, no exclusivo de YB. La auditoría
posterior abarca todas las estaciones Meteocat disponibles entre 01/08 y 25/09;
los resultados están al final de este informe.

## Histórico y alcance

Los mismos valores erróneos de 08, 09, 16 y 18/09 aparecen en el histórico activo
consultado: generación `20260926T190531320283Z-35a8373436e6`, partición Meteocat
2026 de 50.570 filas / 689.574 bytes. Se leyó esa partición pequeña y sólo las
columnas necesarias. No es únicamente un fallo de visualización.

No se ha auditado si estos registros se incorporaron a modelos o precálculos
existentes. No se ha ejecutado ninguna operación de ese tipo.

## Corrección de código validada en HA local

`meteocat_daily_query_bounds` recupera las fechas de calendario solicitadas por
el runner y consulta grupos UTC enteros. Se aplica en las cuatro consultas XEMA
(lluvia, condiciones, consulta individual y viento). Conserva la identidad diaria
UTC existente, también usada por el backfill oficial; no migra los históricos
a días locales ni cambia los intervalos de los otros proveedores.

Pruebas dirigidas: 12 correctas, incluyendo verano/invierno, ambos cambios de
hora, cambio de año, ventana móvil y corrección oficial legítima a cero. Smoke:
**1.819 pruebas, 52 omitidas, OK**, script código 0. HA local reconstruida y
recreada; paridad de 228 archivos sin diferencias, huella
`b21300f7f29f6d70791f5b74010709cbf4eef67dbce149a4cdb722ecb83f715a`.
Worker/coordinadores y observaciones privadas sin tocar. El usuario acepta el resultado
local y autoriza publicar 0.2.325, ya verificada en GHCR para ambas arquitecturas
([release](release-ha-0.2.325-2026-09-26.md)). Instalación pendiente; 0.2.324 no lleva este fix.

## Auditoría y candidata de datos

Consultas oficiales completas 01/08–25/09/2026, lluvia y temperatura/humedad
máximas y mínimas, con respuestas comprimidas cacheadas. Se comparan sólo los
valores presentes en la fuente oficial; no se convierten ausencias en cero.

- **188 estaciones, 6.700 filas corregidas, 24.034 celdas**. De ellas, **1.171**
  corresponden a lluvia. No se añaden ni eliminan claves estación/fecha.
- 01–08/08 y 19–25/09: sin diferencias en las variables comparadas.
- 09–14/08: diferencias menores, crecientes hacia el 14; pueden incluir revisiones
  oficiales y no se atribuyen todas automáticamente al mismo defecto.
- 15/08–18/09: deterioro generalizado, unas 184–188 estaciones/día.
- No se ha comparado contra la API cada día anterior al 01/08: no se certifica
  que todo el histórico previo esté libre de otros defectos.
- CSV candidato: mismas **33.707 filas** y todas las columnas ajenas a la
  reparación conservadas. Se han preservado incluso los metadatos vacíos del
  CSV que difieren de los metadatos disponibles en el archivo histórico.
- Histórico candidato: misma cardinalidad total, **5.550.603 filas**; sólo cambia
  Meteocat 2026, con sus **50.570 filas**. Las otras 45 particiones mantienen
  exactamente sus objetos y hashes, incluidos todos los años anteriores.
- Todos los CSV de otras fuentes permanecen idénticos byte a byte. La copia
  original `docker-data/Data` permanece intacta, verificada por hashes.

Casos recuperados: YB 09/09 **54,8 mm**, 16/09 **7,1 mm**;
W9 09/09 **44,7 mm**, 16/09 **14,5 mm**, tanto CSV como histórico.

Candidata: `tmp/meteocat-repair-20260926/candidate`.
Generación candidata: `20260926T194213372640Z-00b560dfee2a`.
Partición nueva: `data-827a5e727578d117d1020071968bcf86edfc35fc4bdde4cf253e91dc8de47ded.parquet`.
Auditoría: `baseline.json`, `audit-raw.json`, `applied.json`; consultas en `raw/`.
Scripts reproducibles `prepare.py`, `audit_raw.py`, `apply_candidate.py` y
`prepare_deployment.py` en el mismo directorio (artefactos locales ignorados por Git).

## Transferencia a HA real completada

Paquete preparado: **4 archivos, 7.694.984 bytes**, descritos y con hashes en
`tmp/meteocat-repair-20260926/deployment-plan.json`: partición nueva, manifest,
CSV Meteocat y puntero CURRENT. No se sustituye la carpeta Data completa.
Antes de escribir se comprobaron los 70 archivos del baseline contra real: sin
diferencias, sin lotes pendientes. El usuario confirmó 0.2.325 instalada y add-on
parado. Se aplicaron los cuatro archivos y se releyeron hashes/generación desde
SMB; resultado `verified` a las **20:09:52 UTC del 26/09/2026**.

Nueva generación real: `20260926T194213372640Z-00b560dfee2a`. CSV e histórico
conservan sus cardinalidades. Los cuatro casos YB/W9 de 09 y 16/09 están
recuperados en ambos soportes. Los otros 68 archivos del baseline permanecen
idénticos, incluidos todos los CSV ajenos y las particiones históricas previas.
Registro local: `tmp/meteocat-repair-20260926/deployed.json` y script `deploy_real.py`.

Inicialmente se guardó un respaldo en real para el cambio CSV/CURRENT. El usuario
indicó que ya tiene copia local de **todo `share/rainmapper`** y no quiere copias
adicionales en HA. Se retiró exclusivamente ese respaldo creado por la reparación,
verificando antes los hashes originales de `docker-data/Data`; evidencia en
`deployed.json` y `remove_real_backup.py`. No dejar ese respaldo como recurso
restaurable en instrucciones futuras: ya no existe en HA.

Se indicó que puede arrancar el add-on; arranque aún no confirmado. Los mapas
no se han regenerado. Entrenamiento/precálculo los lanza el usuario.

Evidencia inicial: `tmp/station-compare-20260926/`: `official-yb-w9-september.json`,
`meteocat-last-two-hours.json`, `stored-yb-w9.json`, `archive-yb-w9.json` y extractos
Meteoclimatic A/B. No se han incorporado observaciones privadas al informe.
