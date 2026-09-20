# Auditorías del SMI de Rainmapper

## Objetivo y límites acordados

Desarrollar un cálculo propio de agua disponible del suelo que resulte creíble.
Copernicus y las sondas públicas son referencias externas para contrastarlo;
no se pretende depender de sus descargas para la predicción operativa.

El usuario pide ampliar la muestra **del experimento local**, no tomar decisiones
generales a partir de Batlliu de Sort y Camí dels Nerets. También pide conservar
la trazabilidad para futuras sesiones.

Restricciones vigentes de esta auditoría: no tocar HA real ni el worker activo,
no crear imágenes o contenedores Docker adicionales y evitar copias o descargas
voluminosas. La consulta de fuentes públicas y las pruebas locales están autorizadas.

## Decisión vigente: SMI compartido

El usuario acepta regulada + Penman–Monteith + una capa (20/09/2026).
[SMI-07: implementación, justificación, modelos consumidores y migración](adoption-2026-09-20/README.md).
Código y pruebas locales; pendiente despliegue/circuito HA+worker autorizado.
El simple se conserva solo para comparación visual. La aceptación no valida
litros absolutos ni borra los resultados adversos de SMI-06.

## Registro de experimentos

[Elección práctica entre las ocho combinaciones](factorial-2026-09-20/README.md):
recomendación de regulada + ET nueva + una capa, comparación conjunta de
profundidades con IDW y límites de esa decisión. No implica cambios en el mapa.

| ID | Estado a 20/09/2026 | Evidencia |
|---|---|---|
| SMI-01 · Primer contraste | Ejecutado: 5 puntos consultados a Copernicus, 2 con valores; 2 estaciones ICGC contrastadas con cálculos locales | [Informe](contrast-2026-09-19/README.md), [gráficas](contrast-2026-09-19/comparison.html), CSV y respuestas comprimidas |
| SMI-02 · Ampliación de estaciones | Referencias descargadas: 22 estaciones, 21 candidatas por cobertura preliminar. Calidad revisada después en SMI-03 | [Inventario](contrast-2026-09-19/expanded-stations.md), cobertura por canal y respuestas comprimidas |
| SMI-03 · Referencia ampliada y separación de factores | Ejecutado en 22 estaciones: reglas de depósito × ET₀; sensibilidad a lluvia medida en 17. Sin ajuste de parámetros | [Informe](baseline-2026-09-19/README.md), [gráficas](baseline-2026-09-19/comparison.html), [protocolo](baseline-2026-09-19/PROTOCOL.md) |
| SMI-04 · Depósito regulado frente a dos capas | Ejecutado offline: 22 estaciones, IDW principal, controles de estructura y sensibilidades. **No promover la cascada ensayada**: pierde recargas y empeora superficie | [Informe](layers-2026-09-19/README.md), [gráficas](layers-2026-09-19/comparison.html), [protocolo](layers-2026-09-19/PROTOCOL.md) |
| SMI-05 · Las ocho combinaciones | Completadas las dos simples de dos capas; recomendación de regulada + ET nueva + una capa. Ranking pareado del total con 18 estaciones, evidencia conservada de las 22 | [Informe](factorial-2026-09-20/README.md), [ranking](factorial-2026-09-20/ranking.md), [protocolo](factorial-2026-09-20/PROTOCOL.md) |
| SMI-07 · Adopción | Referencia aceptada por el usuario y unificada en el código local. Paridad con 22 estaciones / 1.320 fechas, sin despliegue | [Decisión y migración](adoption-2026-09-20/README.md), [evidencia de paridad](adoption-2026-09-20/parity.json) |
| SMI-06 · Cambios en litros | Ejecutado: cuatro candidatos regulados, perfiles y horarios alternativos; 68 recargas y 27 secados comparables. Residuos condicionados, no validación de litros absolutos; mantener referencia provisional | [Informe](storage-2026-09-20/README.md), [protocolo](storage-2026-09-20/PROTOCOL.md), [registro de trabajo](storage-2026-09-20/process.md) |

[Documento de fuentes externas](rainmapper-external-soil-moisture-validation.md):
material de referencia; sus propuestas o snapshots no prueban la disponibilidad
actual de una fuente. Los informes de experimentos distinguen lo consultado de lo pendiente.

## Reproducir sin acceder a servicios

Desde la raíz del repositorio:

```sh
.venv/bin/python docs/mushrooms/SMI/contrast-2026-09-19/analyse.py
.venv/bin/python docs/mushrooms/SMI/contrast-2026-09-19/check_expanded_coverage.py
.venv/bin/python docs/mushrooms/SMI/baseline-2026-09-19/analyse.py
.venv/bin/python docs/mushrooms/SMI/layers-2026-09-19/test_model.py
.venv/bin/python docs/mushrooms/SMI/layers-2026-09-19/analyse.py
.venv/bin/python docs/mushrooms/SMI/factorial-2026-09-20/test_simple_layers.py
.venv/bin/python docs/mushrooms/SMI/factorial-2026-09-20/compare.py
.venv/bin/python docs/mushrooms/SMI/storage-2026-09-20/test_audit.py
.venv/bin/python docs/mushrooms/SMI/storage-2026-09-20/audit.py
```

El primero regenera 420 filas diarias, 44 métricas y el HTML autónomo del primer
contraste; necesita numpy, scipy y Bokeh. El segundo usa la biblioteca estándar
y recalcula la cobertura de las 22 estaciones. Ambos leen evidencia ya guardada;
no hacen consultas de red ni cambian los modelos operativos.
El tercero reproduce la auditoría ampliada (1.320 filas, 468 comparaciones),
incluida la paridad con las salidas locales guardadas y la conservación de masa.
Los comandos de `layers` prueban y reproducen SMI-04: 7 pruebas físicas/de historia,
2.340 comparaciones, 1.320 filas diarias y 72 episodios. La lluvia IDW es el
criterio operativo; la lluvia medida ayuda a diagnosticar discrepancias.
Los de `factorial` completan SMI-05: cuatro pruebas adicionales y comparación
de las ocho combinaciones, sin volver a descargar ni consultar servicios.

Las respuestas nuevas están en `expanded-stations.json.gz`; Batlliu y Nerets se
referencian desde `evidence.json.gz` para no duplicar datos. No guardar credenciales
en estos documentos ni en las evidencias.

Cada nuevo experimento debe dejar hipótesis, entradas y procedencia, versión o
huellas del código ejecutado, protocolo previo, resultados favorables y adversos,
limitaciones, decisión y pasos pendientes. No sobrescribir las conclusiones de
un experimento anterior con resultados calculados sobre entradas diferentes.
