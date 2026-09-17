# GBIF: observaciones externas y registro paralelo de setales candidatos

Decisión y propuesta del 16/09/2026. Investigación local; sin integración en HA,
sin entrenamiento ni modificación de observaciones/setales operativos.
Complementa [el recuento inicial](gbif-assessment-2026-09-16.md).

## Dos usos del mismo registro externo

Conservar un archivo externo de ocurrencias GBIF como evidencia original, del que
se deriven dos productos independientes:

1. Observaciones candidatas para reconstrucción meteorológica y experimentos ML.
2. Puntos o zonas de presencia histórica por especie para explorar posibles setales.

No hace falta que una ocurrencia sea apta para entrenar para que tenga interés
como referencia geográfica. Tampoco debe crearse un setal confirmado por cada
observación importada. Un punto histórico acredita una cita, no recurrencia ni
fructificación actual.

El corte de 19/06/2012 pertenece a la vía meteorológica/ML. Para descubrir zonas
se puede consultar también el histórico anterior, conservando antigüedad y fecha
desconocida: el recuento ya verificado para las tres especies pasa de 482 a 1.187
al eliminar el filtro de fecha. No son 1.187 setales distintos ni registros ya
revisados; la descarga completa sigue pendiente.

## Regla de abundancia acordada para diseñar la importación

El usuario pide asignar **Normal** cuando la fuente no permita determinar la
abundancia. Se adopta como regla de la futura importación experimental, con estas
condiciones de trazabilidad:

- `flush_abundance = normal` será una asignación por defecto, no una medición de GBIF.
- Conservar presencia y cantidades originales sin reemplazarlas por esta etiqueta.
- Registrar que la abundancia se ha asignado, el motivo y la versión de la regla.
- Cuando haya evidencia interpretable de abundancia, revisarla y preservar la
  transformación aplicada; no inventar umbrales de ejemplares por categoría.
- No modificar la regla del catálogo actual ni la abundancia de observaciones propias.

Verificación del catálogo **local actual**: exceptional, very_abundant, abundant,
normal y scarce tienen `prediction_favorable=1`; very_scarce y absent tienen 0.
También existe el valor técnico pending con 0. La función
`observation_prediction_target` consulta esa correspondencia
(`rainmapper-app/app/mushroom_profiles_ui.py:2722`). La distinción binaria vigente
es favorable/desfavorable; very_scarce puede contener ejemplares presentes.

Asignar Normal convierte las presencias externas admitidas en ejemplos favorables
por decisión experimental. **No crea ejemplos desfavorables.** Con los 482 registros
actualmente contados, todos PRESENT, el experimento «solo GBIF» seguiría teniendo
una sola clase si no se añade otro diseño o fuente de negativos. No presentar
puntos sin citas como ausencias verificadas. La comparación debe explicitar esta
limitación, reservar evaluación propia independiente y medir el efecto de la
asignación por defecto.

## Qué muestra una consulta real de registros

Se examinaron hasta tres registros por combinación especie/dataset: 9 de
Observation.org, 9 de iNaturalist, 8 de SIM y el único FungaCAT reciente, 27 en total.
Muestra por conveniencia, no aleatoria; no representa estadísticamente los 482.
Evidencia seleccionada y URLs: [gbif-sample-2026-09-16.json](gbif-sample-2026-09-16.json).

- Los nueve de Observation.org traen `individualCount=1`; los otros 18 no informan
  ese campo en la respuesta de búsqueda. Ninguno de los 27 trae `organismQuantity`
  ni `samplingEffort` en esa respuesta. No se afirma que esos campos falten en
  todo GBIF ni en todos los datos originales de los proveedores.
- El [original de GBIF 5918446779](https://api.gbif.org/v1/occurrence/5918446779/verbatim)
  confirma `individualCount=1` y `samplingProtocol=unknown`. Un ejemplar registrado
  no permite por sí solo convertir la abundancia de la salida a nuestras categorías.
- Los registros [5292098335](https://api.gbif.org/v1/occurrence/5292098335) y
  [5830995596](https://api.gbif.org/v1/occurrence/5830995596) informan 27.754 m de
  incertidumbre y explican que se aumentó por petición del observador. Son referencias
  de zona, no coordenadas utilizables como setal exacto; respetar esa generalización.
- [4899780063](https://api.gbif.org/v1/occurrence/4899780063) presenta `eventDate=2016-10-15`
  pero su nota dice `15-16/10/2016`. Es un ejemplo real de fecha que requiere revisión
  aunque GBIF informe día, mes y año.

Campos y significado: [documentación de GBIF](https://techdocs.gbif.org/en/data-use/download-formats).
No se han descargado fotos ni el conjunto completo de ocurrencias.

## Identificar las observaciones importadas

Usar los campos existentes `source.type=imported_dataset`, `source.label=GBIF · proveedor`
y `source.url` para la ficha original. Mantener `observer.name` para el observador
publicado; GBIF es agregador y no debe sustituir a la persona que observó.

Añadir una procedencia estructurada estable —diseño todavía sin implementar— con
proveedor GBIF, gbifID, occurrenceID, datasetKey, lote y fecha de descarga, licencia,
atribución, taxón original/interpretado, incertidumbre y flags. Incluir separadamente
el origen de la etiqueta Normal. Deduplicar por IDs y comprobar publicaciones
duplicadas entre fuentes antes de crear una observación nueva.

La búsqueda textual actual examina el JSON de la observación y encontraría GBIF
en `source.label` (`filtered_observation_rows`, `mushroom_profiles_ui.py:4914`).
Conviene añadir filtros explícitos Propias/GBIF/Todas y filtros de cohortes ML
que usen el identificador estructurado, no una búsqueda por nombre del observador.
La conservación de la nueva procedencia durante edición, exportación y trabajo
HA–worker necesitará pruebas cuando se implemente.

## Criterio inicial de incertidumbre espacial

El usuario propone usar únicamente registros con incertidumbre máxima declarada
de **1.000 m** y mantener los desconocidos para decidir más adelante. Se adopta
este criterio para diseñar el piloto; todavía no se ha aplicado a datos operativos.

| Incertidumbre original de GBIF | Tratamiento inicial | Recuento reciente de las tres especies |
| --- | --- | ---: |
| Valor válido entre 0 y 1.000 m, inclusive | Candidato; sujeto a los demás controles | 129 |
| Mayor que 1.000 m | Excluido del entrenamiento y de puntos candidatos precisos | 47 |
| Ausente | Desconocida; pendiente de revisión, fuera del entrenamiento inicial | 306 |

Recuentos de la consulta del 16/09/2026 conservada en
[la evidencia inicial](gbif-counts-2026-09-16.json), para Catalunya desde 19/06/2012.
No trasladar estos números al histórico ampliado sin consultar ese conjunto.
Valores inválidos o contradictorios, si aparecen al descargar, quedan en revisión.

Persistir el valor normalizado en el campo existente `location.precision_m`, en
metros, y conservar el original `coordinateUncertaintyInMeters` en la evidencia
de procedencia. Ausencia se representa como `null`, nunca como cero por defecto.
Separar dato original, decisión de uso y motivo de exclusión: así una revisión
podrá excluir o readmitir un registro sin borrar su incertidumbre ni su origen.

Si en el futuro se decide experimentar tratando los desconocidos como precisos
o como excluidos por precaución, hacerlo mediante una política explícita y
versionada del experimento. No sobrescribir el original con 0 ni afirmar que un
registro está ocultado deliberadamente solo porque no informa precisión. Una
incertidumbre declarada de 0 tampoco implica por sí sola exactitud demostrada.

El umbral de 1 km es un filtro inicial elegido para el piloto, no garantía de
homogeneidad meteorológica, altitudinal, de hospedadores o de suelo. Sigue siendo
necesaria la revisión de representatividad espacial antes del entrenamiento.
Los registros excluidos o pendientes permanecen en el archivo externo separado;
no se usan para extraer features de un supuesto punto preciso ni para ajustar modelos.

## Registro paralelo de setales candidatos

El usuario propone además, para una fase posterior a la revisión local, integrar
estas citas en el **mapa de predicción como zonas por especie**, con la política
de incertidumbre todavía por decidir. No confundir esa futura capa inferida con
los círculos del visor de investigación: los azules representan el radio publicado;
los rojos de 500 m son una convención visual pedida por el usuario para citas con
incertidumbre desconocida, que sigue siendo desconocida en los datos y filtros.
Ninguno delimita un setal ni una zona de fructificación validada.

Proponer una capa independiente en el mapa con filtros por especie, fuente,
fecha/antigüedad, precisión y número de eventos independientes. Cada ficha mostraría:

- Ubicación publicada y círculo/zona de incertidumbre cuando se conozca; si no se
  conoce, indicarlo sin atribuir precisión GPS al punto.
- Primera y última cita, años y fechas distintas, observaciones originales y enlaces.
- Evidencias por especie y estado: referencia histórica, candidato con citas
  repetidas o confirmado posteriormente mediante visita/revisión propia.
- Coincidencia con setales personales, conservando ambos orígenes y sin sobrescribirlos.

Agrupar solo después de deduplicar y evaluar precisión. La proximidad y las citas
repetidas justifican revisar una zona, pero no prueban que sea el mismo setal.
Evitar un radio universal no validado y no convertir un centroide en una ubicación
observada. Un mismo lugar puede sostener varias especies: separar lugar y evidencias
por especie para no multiplicar artificialmente puntos.

El esquema existente de microáreas tiene `representative_location`, `geometry`,
`location_precision_m` y `provenance` (`rainmapper_core/mushroom_known_sites.py:73`).
Ofrece una posible vía de promoción posterior, pero no contiene por sí solo el
registro nuevo de citas y estados propuesto. Mantenerlo paralelo hasta confirmar
qué puntos deben incorporarse a los setales propios.

## Secuencia propuesta

1. Descarga separada de todos los perfiles del catálogo local, con manifiesto de
   consultas y huellas. El usuario amplió expresamente las tres especies iniciales
   al catálogo completo y pidió conservar las fotografías en `media` para trabajar
   sin conexión. Mantener Catalunya y la ventana 19/06/2012–16/09/2026 en esta
   primera copia, sin filtros por incertidumbre, proveedor o licencia. La posible
   ampliación histórica para setales queda para otro paso. Datos y fotos excluidos
   de Git y del contexto Docker.
2. Auditoría de duplicados, fechas y precisión; dos decisiones de elegibilidad
   separadas: utilidad como candidato geográfico y utilidad para entrenamiento.
3. Presentar un mapa de candidatos y una tabla de observaciones importables,
   incluyendo Normal como valor asignado cuando corresponda.
4. Implementar importación y filtros de fuente/cohortes con conservación de datos
   propios; resolver explícitamente la clase negativa del experimento solo GBIF.
5. Ejecutar las comparaciones autorizadas en el entorno local/worker y promover
   únicamente tras evaluar resultados. Ninguna publicación o entrenamiento ahora.
