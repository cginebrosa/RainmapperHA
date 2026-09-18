# Organización de media en HA — propuesta 17/09/2026

**Restricción expresa del usuario: no acceder por SSH a la RPi4 sin petición
explícita, tampoco para consultas. El 18/09 autorizó SSH para la migración de
media, su verificación y la retirada de duplicados GIS comprobados. Esta excepción
no autoriza otras operaciones. Parar, instalar y arrancar Rainmapper en HA real
sigue a cargo del usuario.**

Estado al 18/09: **HA local migrado y validado; HA real con seis movimientos
completados y duplicados GIS retirados tras verificación íntegra**. El usuario confirmó 0.2.310
instalada y Rainmapper parado; se revalidó con HA CLI antes de actuar. Autorizó
SSH para calcular hashes en la Raspberry sin transferir los rásteres al Mac.
La instalación/arranque de una imagen NO mueve ni borra carpetas.
**El usuario reserva para sí parar, instalar y arrancar Rainmapper en HA real.**

Geografía, meteorología y modelos abren las rutas nuevas usando la imagen
instalada 0.2.310 en un contenedor de diagnóstico sin red, con share de solo
lectura y recursos limitados. No se arranca Rainmapper ni se generan artefactos.
Recibo en `/media/rainmapper/media-migration-receipt.json`; evidencia local
`tmp/ha-media-migration-20260918/`.

[Informe final](../reports/ha-media-migration-2026-09-18.json): 1.550 archivos
reubicados con integridad comprobada; 4.942 duplicados retirados después de
verificar todos los SHA de origen/copia/manifiesto. Tamaño lógico retirado:
21.358.531.147 bytes, sin afirmar que sea el espacio físico liberado. Los cuatro
metadatos adicionales se conservan en `geography/imports/retired-legacy-metadata`.
Diez ficheros privados intactos, identidad del runtime conservada y ninguna
fuente publicada ausente; `active.sqlite3` pasa `quick_check`. Los tres lectores
vuelven a abrir correctamente después de retirar las carpetas antiguas.
Se indicó al usuario que puede arrancar Rainmapper; después confirmó que el
mapa de HA real funciona con ejecutor local y worker. Sin entrenamiento ni
precálculo nuevo.

## Inventario histórico previo — 17/09

Inspección por SMB LAN `192.168.0.121`, `/Volumes/media/rainmapper`, equivalente
a `/media/rainmapper` dentro de HA. No se utilizó el montaje `media-1` por Tailscale.
[Inventario y comparación](../reports/ha-media-audit-2026-09-17.json).
Inventario detallado local: `tmp/media-audit-20260917/inventory.json`.

| Carpeta actual | Tamaño lógico observado | Función / diagnóstico |
| --- | ---: | --- |
| `geography` | 15,63 GB | Geografía consolidada compartida, manifiestos y configuración |
| `mushroom-GIS` | 6,82 GB | Copia anterior de las fuentes GIS científicas |
| `prediction-map` | 14,54 GB | Publicación anterior de cartografía del mapa de predicciones |
| `mushroom-derived` | 157 MB | Modelos, artefactos y archivos de trabajos del worker mezclados bajo un mismo padre |
| `predictor_precompute` | 28,6 MB | SQLite activo del precálculo, recibo y revisión deseada |
| `runtime-cache` | 113,5 MB | Caché de transporte/runtime del Predictor |

GB/MB decimales, suma de tamaños de archivos; no espacio físico asignado ni
garantía de espacio liberado. Los directorios operativos pueden cambiar durante
el inventario. Se observó un `.upload` de precálculo al empezar, ausente al terminar;
no se tocó ni se considera basura por su nombre.

Los manifiestos antiguos reúnen **21.358.531.147 bytes de cartografía**.
Comprobadas todas sus referencias: 1.432 GIS y 3.510 mapa, presentes tanto en
las rutas anteriores como en las consolidadas y con tamaño correcto. Doce
muestras pequeñas coinciden por SHA-256 entre ambas rutas y con el manifiesto.
No se releyeron decenas de GB para recalcular hashes de los rásteres grandes.
La identidad completa de contenido procede de la copia verificada del 15/09;
esta auditoría actual revalida referencias/tamaños y las doce muestras.

Los originales se conservaron expresamente durante la migración. Ver
[consolidación y condiciones de retirada](shared-geography-consolidation-es.md).
`geography/imports` solo conserva tres manifiestos (1,18 MB);
`geography/generations` un manifiesto (0,81 MB). No son más copias de cartografía.
Los dos subárboles `geography/mushroom-GIS` y `geography/mushroom-map-GIS`
conservan fuentes complementarias y referencias compartidas; no borrar uno por
parecerse sus nombres.

## Rutas y límites de la comprobación previa

El código de `mushroom_gis_lab.gis_root` y `mushroom_soilgrids.default_cache_root`
prefiere la geografía consolidada salvo configuración explícita. El broker de
`rainmapper-app/app/mushroom_prediction_map_ui.py` busca primero configuración
explícita, después la privada de share y finalmente `geography/map-config.json`.
En HA real esta última existe, apunta a la publicación consolidada y a modelos
en `mushroom-derived/ml_models`; la configuración privada de share no existe.
`CURRENT.json` identifica `local-20260914`.

Actualización posterior: comprobado por SSH LAN el contenedor efectivo de HA
real, primero 0.2.308 y después 0.2.309 instalada por el usuario. Los resolutores
GIS/SoilGrids usan `geography/mushroom-GIS`; modelos/precálculos aún usan las
rutas anteriores. No hay override de configuración del mapa en el entorno.
Antes de retirar originales hay
que comprobar versión/rutas efectivas, ausencia de referencias antiguas y lectura
correcta de los consumidores afectados. No entrenar ni precalcular para ello.

El mapa meteorológico tiene rutas diferentes: `run.sh` enlaza `Data`, `Tomap`,
`Plots` y `PublicData` de `/share/rainmapper` a `/app`; esas carpetas existen
en HA real. `prediction-map` de media no es la carpeta del mapa meteorológico
antiguo. Su limpieza no reorganizaría automáticamente aquellas salidas.

## Estructura propuesta

Organizar por función y ciclo de vida, sin repetir datos por pantalla:

```text
/media/rainmapper/
  geography/                  # Una cartografía compartida por ambos consumidores
  results/
    models/                   # Modelos, versiones y lotes conservados
    artifacts/                # Reconstrucciones, features e informes
    predictor-precompute/     # Precálculo instalado y sus metadatos
  transfers/
    worker/                   # Entradas, candidatos, resultados y payloads de trabajos
  cache/
    predictor-runtime-archives/
```

Conservar la estructura interna y los manifiestos de `geography` en esta fase:
renombrar todas sus fuentes no aporta ahorro. `results` y `transfers` **no son
sinónimos de desechable**; mantener retención, referencias, promociones y evidencias
de cada artefacto según la [política vigente](mushroom-ml-storage-retention-spec-es.md).
Observaciones, fotos del usuario, fichas, registros y meteorología conservan
sus ubicaciones actuales en share; moverlos requiere otro alcance específico.

| Origen actual | Destino propuesto |
| --- | --- |
| `mushroom-derived/ml_models` | `results/models` |
| `mushroom-derived/mushroom-artifacts` | `results/artifacts` |
| `predictor_precompute` | `results/predictor-precompute` |
| `mushroom-derived/worker` | `transfers/worker` |
| `runtime-cache/predictor-runtime-archives` | `cache/predictor-runtime-archives` |

Implementación autorizada en dos pasos independientes:

1. Confirmar consumidores efectivos y autorizar retirada de las copias GIS
   anteriores: unos 21,36 GB lógicos. Mantener la nueva geografía y su evidencia.
2. Si el usuario acepta la estructura, adaptar resolutores/configuraciones y
   referencias persistidas, probar la migración en HA local/worker y después
   efectuarla en HA real con escritores detenidos. Trasladar dentro del mismo
   volumen sin duplicar GB, con detección de conflictos y verificación posterior.
   Conservar destinos del único worker y contratos; no regenerar modelos ni
   precálculos para un cambio de rutas. No basta renombrar carpetas en Finder.

No se autoriza ninguna limpieza automática, nueva política de retención ni
reanudación de la revisión científica GIS mediante este documento.

## Implementación y aceptación local

`rainmapper_core/media_layout.py` y `scripts/manage-media-layout.py` proporcionan
plan, migración explícita y retirada de cartografía antigua. Los resolutores
conservan rutas anteriores mientras no exista `.media-layout-v1.json` completo.
Un diario de migración incompleta bloquea el uso de rutas para evitar escribir
en una estructura a medio mover. Destinos ocupados o cruces de volumen abortan.

La migración registra huellas previas, usa renames y verifica todos los archivos,
directorios vacíos y destinos de enlaces después. Conserva entradas desconocidas
de `mushroom-derived` bajo `results`. Mantiene el recibo de la transición anterior
para no volver a copiar datos desde share al arrancar.

Se adaptan `models_root` de la configuración y las referencias absolutas de
`published-runtime.json`. Este último cambio preserva manifiesto científico,
fingerprint y `source_state`; no entrena ni publica otro runtime. La prueba local
detectó inicialmente esa dependencia y se corrigió antes de actuar en HA real.
No se reescriben rutas de procedencia histórica dentro de observaciones o evidencias.

HA local: ocho movimientos, 1.547 archivos conservados antes de los cambios
explícitos de metadatos; datos privados intactos. SQLite activo `quick_check=ok`.
Dos puntos consultados en local/worker con resultados científicos idénticos.
Paridad 202 archivos HA y 108 worker; ambos destinos del único worker conservados.
Smoke final: 1.621 tests, 48 omitidos. Evidencia `tmp/media-migration-20260917/`.
No se lanzó reconstrucción, entrenamiento ni precálculo operativo nuevo.

La publicación local ya tenía una ficha anterior a la ficha editable; comprobado
contra las huellas anteriores a la migración. El mapa combina las fichas vigentes.
`predictor_precompute_plan` usa `load_or_publish_manifest` para renovar la
publicación cuando se solicite otro precálculo; no se fuerza esa operación aquí.

Retirada de duplicados: antes del primer borrado se leen completos origen y copia
conservada, se contrastan SHA con el manifiesto y se revalidan los stat. Se evita
rehashear la misma copia canónica varias veces. Cualquier archivo adicional se
conserva bajo `geography/imports/retired-legacy-metadata`, nunca se elimina por
no figurar en el manifiesto. Es una comprobación de integridad para el borrado
autorizado, no un rehash rutinario al arrancar ni durante una predicción.
