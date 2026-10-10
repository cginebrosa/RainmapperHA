# Comparación común de Habitual y A/B/C/D · 06/10/2026

## Corrección posterior: ninguna consulta de punto lanza histórico

El usuario rechaza el disparo automático introducido en la primera entrega.
Se retiró el callback de `/queries` y su función de planificación. El mapa sólo
consume selección y comparación ya preparadas, también si falta evidencia o se
consulta con otra K. Guardar ajustes no dispara histórico. Se conserva el trabajo
del runner y el botón explícito de Workers; éste respeta la K personal del
dispositivo o hereda la del add-on. Una K aún sin nota se prepara desde ese botón.

La comparación ya es la fase final del mismo trabajo histórico: las semanas se
predicen mientras el ajuste temporal de cada familia sigue en memoria y se
guardan para resolver las cinco reglas. No se añadió un segundo entrenamiento
ni se cambió el protocolo de cálculo para esta corrección. No se cancela,
reinicia ni invalida el trabajo que ya estaba ejecutándose.

Verificación posterior: 17 pruebas de backend/runner/comparación aprobadas;
tras añadir la herencia de K al botón de Workers, las ocho de backend pasan.
La regresión realiza doce POST de consulta con puntos/K distintos y comparación
activada/desactivada, sin evidencia preparada: todos aceptados para predicción,
cero solicitudes de histórico, cero bundles o estados de trabajos creados.

Sólo HA local reconstruido/recreado para esta corrección. HTTP 200 y ausencia
del disparador verificados en el contenedor. Paridad 30/23 archivos, sin diferencias;
huella del procedimiento inalterada. Worker no reiniciado. El trabajo
`worker_job_ZFACRJa4VG_0ze9s` seguía ejecutándose tras recrear HA, preparando
semanas de V3 (15/17). El porcentaje publicado volvió al 10 % durante esa fase:
no usarlo para inferir reinicio o duración; pendiente corregir esa telemetría.

Lo que sigue documenta la entrega anterior y sus comprobaciones; la regla de
disparo del mapa anterior queda reemplazada por esta corrección.

Disponible en HA local, con pruebas sintéticas aprobadas. Pendiente ejecutar y
medir el nuevo trabajo con observaciones reales. No se ha publicado HA ni cambiado
la versión 0.2.333, ni promovido modelos o repetido estudios cerrados.

## Resultado y significado

Competing selection añade Habitual a cuatro reglas conservadas: A 12 meses
semanal, B 24 semanal, C 24 diario, D todo el histórico semanal. Las cuatro eligen
por mayor Iₖ dentro de su ventana. Habitual conserva el orden nativo y produce
el IFF principal y la gráfica, también al activar el experimento.

El nuevo **Iₖ de comparación** usa visitas comunes y mide cada procedimiento
completo. El borde verde señala el máximo de las cinco notas, incluidos empates.
Las notas de selección, cantidades, aciertos/fallos y soporte quedan plegados.
Sin resultados para K o sin soporte comparable no se fabrica ganador. Verde
es descriptivo, no demostración de superioridad ni aprobación de un mínimo útil.

El worker reproduce semanas completas desde modelos de validación ajustados
con años anteriores; para ordenar cada semana usa evidencia anterior a su
emisión, separada 14 días y excluyendo su episodio. Cada visita pesa uno y cada
horizonte 1/7. Ausencia técnica excluye la visita para los cinco; abstención
ordinaria permanece en el denominador. Se conservan observaciones originales.

La comparación reconstruye reglas actuales con el contexto de áreas históricas,
inventario actual de familias, temporadas y política actual. No reproduce
exactamente catálogos/modelos instalados en cada fecha ni valida el punto pulsado.
El IFF del punto puede variar; la nota común pertenece a especie/K/histórico.

## Proceso y límites de recursos

Módulos nuevos `mushroom_competing_comparison`, `mushroom_competing_panels` y
`mushroom_competing_replay`; integración en runner histórico, contrato, runtime,
API y presentación. Capabilities `competing_history_update_v2` y
`map_competing_selection_v2`; sólo workers compatibles reciben el nuevo contrato.

Semanas privadas en SQLite (96 MiB), 375.000 celdas como máximo previsto;
paquete por visita/familia de 128 KiB e índice deduplicado por generación de
2 MiB. HA recibe un artefacto resumido de máximo 1 MiB. El cambio sólo de K
reutiliza la generación, sin preparar variables ni ajustar modelos, y reproduce
elecciones/contadores. Se conservan hasta ocho resúmenes K compatibles para no
borrar la comparación de otro usuario. Si hay otro trabajo activo, se conserva;
una K distinta pendiente se vuelve a solicitar en la siguiente consulta.

Planificación real, sin ajuste ni predicción: 87 familias, 311 candidatos,
especificación 79.820 bytes, 184 visitas antes de elegibilidad. Previsión de
317.608 celdas / 81.307.648 bytes; 15,672 s para revisar entradas. Recibo
`tmp/competing-comparison-input-check.json`. La huella de procedimiento de ese
recibo precede los últimos ajustes de código; las cardinalidades acreditan esa
lectura, no una ejecución del nuevo trabajo. Duración y tamaño final desconocidos.

## Comprobaciones ejecutadas

- 83 pruebas dirigidas: comparación común, Habitual, empates, abstenciones,
  visitas compartidas, aislamiento temporal, semanas completas, caché/K,
  contratos, recepción autenticada, mezcla de resúmenes por K y empaquetado.
- Suite conjunta de backend/autenticación: 359 pruebas, una falló por el import
  antiguo `test_mushroom_predictor_precompute` sin `tests` en PYTHONPATH. Esa
  prueba pasó al repetirla con `PYTHONPATH=tests`; no se cambió su implementación.
  Después se repitió el backend dentro de las 83 pruebas tras endurecer el enlace
  del resultado con su generación de entradas.
- 49 pruebas dentro de `rainmapper-worker:1.1.6`, contenedor aislado `--network none`,
  tests montados en lectura, sin datos privados. Incluyen preparadores reales
  V3/V4/V5 y las combinaciones V6 del fixture, replay y capas de caché.
- Navegador compartido completo aprobado tras el último ajuste CSS. Fixture
  Habitual/A empatados en verde, cinco tarjetas, detalles plegados; 320/390 px
  sin desbordamiento y ficha dentro de pantalla. Capturas en
  `/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-MIQfcx`.
  Resizing de una ficha abierta en escritorio mantiene su ancla anterior: la
  prueba móvil abre una ficha nueva, como una consulta desde móvil. No se ha
  corregido ni validado el cambio de orientación de una ficha ya abierta.
- `git diff --check` sin errores.

Comando de pruebas dirigidas:

```sh
.venv/bin/python -m unittest tests.test_mushroom_competing_comparison tests.test_mushroom_competing_backend tests.test_mushroom_competing_control tests.test_mushroom_competing_inputs tests.test_mushroom_competing_history tests.test_mushroom_competing_tuning tests.test_mushroom_map_competing tests.test_mushroom_map_model_runtime tests.test_mushroom_map_queries tests.test_mushroom_competing_runner tests.test_mushroom_worker_packaging
```

## Ejecución local y paridad

Reconstruidos y recreados `rainmapper-ha-ui` con `rainmapper-local/docker-compose.yml`
y `rainmapper-worker` con `docker-compose.worker.yml` +
`docker-compose.prediction-map-worker.yml`. Sin scripts de arranque/limpieza.
Verificado código efectivo de 30 archivos HA y 23 worker: cero diferencias con
el worktree. Recibo `tmp/competing-comparison-local-20261006/parity.json`.
HA local respondió HTTP 200; worker idle, ambos carriles sin trabajo activo.

Huella de procedimiento igual en Mac, HA local y worker:
`ce683820f90f3e87cb2e8cdee471ba4ff466acbd6f4bab468d79555965b8cdd5`.

Antes y después del worker se comprobaron exactamente:

| Configuración | URL | SHA-256 del archivo |
| --- | --- | --- |
| Principal | `http://100.111.77.48:8100` | `5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10` |
| Adicional | `http://rainmapper-ha-ui:8100` | `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0` |

No se ejecutaron trabajos operativos, entrenamiento operativo, precálculo ni
estudios. El usuario lanza los trabajos. Se conservaron fuentes privadas y
cambios previos; no hubo release, commit ni push.

## Pendiente de aceptación real

El artefacto anterior existente mide 573.310 bytes, corte 05/10, 169 casos,
275 candidatos y 25.923 celdas; no contiene la nueva comparación común.
La primera preparación nueva necesita probabilidades para semanas completas;
el antiguo resumen de días observados no basta. Falta medir tiempo, soporte,
ausencias, publicación y presentación con esas observaciones, además de un
cambio sólo de K. No se promete duración de pocos minutos ni incrementalidad
completa por especie. La ampliación a todas las especies requiere partición y
medición del trabajo y sus dependencias compartidas.

Durante la comprobación del usuario, su consulta real solicitó automáticamente
`worker_job_ZFACRJa4VG_0ze9s`, origen `map`, inicio 16:16:08 UTC del 06/10.
El worker lo ejecutaba en el carril de fondo; primera lectura 10 %, V3 fixed,
meteorología 105/111. La ficha enseñaba «Iₖ de comparación: —» y pendiente porque
el nuevo resumen todavía no estaba publicado. No se solicitó un trabajo duplicado.
Última lectura de esta intervención: ejecución al 33 %, preparación V5,
800/1487 ventanas meteorológicas, 259 s. Recibo
`tmp/competing-comparison-local-20261006/first-job-status.json`.
