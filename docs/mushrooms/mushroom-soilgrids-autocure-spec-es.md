# Autocura SoilGrids antes del reentrenamiento operativo

Estado: implementada en laboratorio el 2026-08-27; pendiente de validación
integrada completa y de una entrega autorizada a HA real.

## Problema observado

HA real conservaba 63 microáreas activas: 59 con contexto SoilGrids completo y
cuatro en `pending`. Las cuatro pendientes eran `setcases_izquierda_rio`,
`setcases_la_collada`, `vallter_ulldeter` y `espinavell_ritort`. El error común
era la ausencia de `/media/rainmapper/mushroom-GIS/soilgrids/manifest.json`.

El guardado de una microárea intentaba agregar los rásteres antes de inicializar
la caché. Si faltaba el manifiesto, la excepción se convertía directamente en
un contexto pendiente y nunca se alcanzaba la rama que crea el manifiesto y
materializa las teselas. Tampoco existía un reintento global al reconstruir.

La caché pertenece a `/media`, no a `/share`: los aproximadamente 382 MiB del
laboratorio no deben entrar en el backup ordinario de Home Assistant.

## Contrato de la solución

La reconstrucción operativa crea primero un job persistente con estado
`preparing` y fase localizada «Reconciliando GIS y SoilGrids». En ese estado el
worker no puede reclamarlo. Antes de congelar el snapshot:

1. se carga una única copia de `mushroom_known_sites.json`;
2. se reutilizan sin abrir rásteres todos los contextos cuyo contrato, versión,
   hash de geometría y estado ya son vigentes;
3. solo se reintentan microáreas sin contexto o con contexto pendiente/obsoleto;
4. la caché ausente se puede inicializar antes de la primera agregación;
5. cada reparación se aplica a una copia en memoria;
6. si hubo reparaciones y el fichero vivo no cambió durante el cálculo, se
   promociona mediante el escritor atómico y su copia recuperable;
7. si el fichero cambió concurrentemente, se preserva el nuevo fichero y se
   pospone la promoción hasta la siguiente reconstrucción;
8. solo entonces se congela el bundle inmutable y el job pasa a `queued`.

La cancelación se comprueba entre teselas y entre microáreas. Un fallo local de
red, WCS, GDAL, manifiesto o ráster no detiene el mantenimiento completo: deja
la microárea pendiente, registra el motivo y continúa. Los perfiles que no
necesitan SoilGrids permanecen operativos. Los cálculos físicos exigen un
contexto `complete`, por lo que una microárea pendiente no aporta datos
inventados a esos perfiles.

## Telemetría y visibilidad

La cola conserva durante la preparación y al finalizar:

- duración monotónica de la fase;
- microáreas totales, procesadas, vigentes, intentadas y reparadas;
- descargas y reutilizaciones de tesela;
- peticiones y bytes descargados;
- ficheros promovidos y leídos;
- hashes de activos y bytes hasheados;
- ventanas ráster leídas;
- escrituras de manifiesto y `fsync`;
- advertencias por microárea.

El último informe se escribe atómicamente en
`mushroom-data/diagnostics/soilgrids-reconciliation-latest.json`. Predictor y
Setales muestran un aviso amarillo global si quedan microáreas sin contexto
vigente; cada microárea afectada lleva además la marca «SoilGrids pendiente».
El aviso aclara que solo quedan fuera los perfiles que necesitan ese contexto y
que la reconstrucción completa volverá a intentarlo.

## Medición dirigida con datos reales

Se leyó el `mushroom_known_sites.json` montado de HA real sin modificarlo y se
reconcilió sobre una copia en memoria contra la caché local completa:

- 63 microáreas activas;
- 59 reutilizadas por identidad, sin agregación;
- 4 intentadas y 4 reparadas;
- 0 peticiones, 0 descargas y 0 advertencias;
- 63 contextos finales `complete`;
- duración monotónica: 52,259 s.

Ese coste corresponde a la primera autocura: agrega las 54 coberturas de los
cuatro contextos pendientes. Una vez promocionados, las siguientes
reconstrucciones solo comprueban contrato y hash de geometría. La prueba no
escribió en HA real ni en su `share`.

## Riesgos y validación pendiente

- La primera autocura puede tardar más si faltan teselas y la red de SoilGrids
  es lenta; el timeout sigue siendo acotado y el fallo es local, no global.
- La agregación inicial todavía abre una ventana GDAL por cobertura y
  microárea. Los 52,259 s no ponen en riesgo el objetivo de diez minutos y no
  se repiten en caliente, pero su posible deduplicación queda condicionada a
  mediciones con más microáreas pendientes.
- Falta ejecutar el proceso operativo completo en el laboratorio con la copia
  fresca de `known_sites` y observaciones reales, comprobar visualmente fase,
  cancelación y avisos antes de cualquier bump, build o publicación. La
  validación estática y automatizada pasa 53 pruebas dirigidas, la suite
  completa de 1.051 pruebas, compilación, JSON y `git diff --check`.
