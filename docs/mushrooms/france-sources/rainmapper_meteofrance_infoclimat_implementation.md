# Rainmapper — meteorología para el corredor Quérigut–Font-Romeu

**Estado:** diseño adaptado al repositorio y a los datos operativos actuales

**Revisado:** 9 de septiembre de 2026

**Ámbito inicial:** corredor Quérigut–Formiguères–Les Angles–Font-Romeu, entre Ariège (D09) y Pyrénées-Orientales (D66).

**Especificación técnica para implementar:**
`rainmapper_meteofrance_implementation_spec.md`. Esa especificación concreta
configuración, runner separado, desfase, diagnósticos, UI y criterios de
aceptación, y prevalece para la implementación.

## 1. Decisión

La ampliación usará inicialmente los **CSV climatológicos diarios D66 de
Météo-France**. D09 sólo se añadirá si una microárea posterior demuestra que lo
necesita. Para el dato reciente no hace falta
crear otro proveedor: Rainmapper ya integra Wunderground y HA real ya tiene
configuradas `IFORMI6` (Formiguères) e `IFONTR8` (Font-Romeu).

Se separan dos canales:

1. **Histórico oficial diario**, sin credenciales, mediante Météo-France, para
   ampliar y contrastar entrenamiento y predicción.
2. **Histórico y dato reciente**, mediante el flujo Wunderground ya existente,
   para Formiguères y Font-Romeu.

La API de Wunderground devolvió observaciones actuales de ambas estaciones el
9 de septiembre de 2026. Por tanto, solicitar acceso a la API **Données
d'observation** de Météo-France ya no es requisito de la primera entrega. Queda
como posible redundancia oficial si la cobertura real de Wunderground resulta
insuficiente. La API climatológica continúa siendo innecesaria.

La red oficial inicial tendrá **dos estaciones configuradas**:

1. **Targasonne `66202001`**: serie completa; referencia del extremo Font-Romeu.
2. **Formiguères `66082004`**: serie completa; referencia central y principal apoyo de Quérigut.

Quedan como candidatas futuras, no como red inicial:

3. **Mijanes `09193400`**.
4. **Ascou-Pailhères `09023400`**.
5. **Les Angles `66004401`**.
6. **Font-Romeu-Galinera `66124402`**.

Infoclimat queda **fuera del plan de implementación**. La API sólo permitió dos
estaciones útiles, Osséja y Mérens-les-Vals, mientras que las dos localidades
prioritarias ya están cubiertas por Wunderground. No compensa añadir un quinto
proveedor, otro secreto y otra política de calidad para esa ganancia marginal.

No se introducirá ahora un framework nuevo de proveedores ni una base separada de estaciones físicas. Rainmapper ya identifica de forma inequívoca cada serie mediante:

```text
(source, station_code, local_date)
```

## 2. Encaje con el Rainmapper actual

### 2.1 Contrato meteorológico

El contrato canónico se define en `rainmapper_core/weather_history_contract.py`:

- clave: `source`, `station_code`, `local_date`;
- Parquet tipado y particionado por fuente/año;
- catálogo de estaciones con coordenadas, altitud y fechas;
- valores meteorológicos nulos representados como `null`, nunca como cero.

Las fuentes actuales son `aemet`, `meteocat`, `meteoclimatic` y `wunderground`. Añadir Francia implica extender de forma coherente:

- `KNOWN_SOURCES`;
- `DAILY_INCREMENTAL_FILES`;
- `LIVE_CSV_FILES`;
- metadatos del contrato IDW;
- pruebas y cualquier enumeración cerrada de fuentes.

El nuevo identificador será:

```text
meteofrance
```

No se cambiarán los identificadores existentes.

### 2.2 Flujo que debe reutilizarse

```text
recurso oficial Météo-France
→ descarga acotada y verificable
→ parser/mapeo francés
→ filas del contrato meteorológico canónico
→ pending batch / live CSV MeteoFrance_incremental.csv
→ weather-history particionado
→ catálogo de estaciones
→ selector e IDW existentes
```

Los CSV de proveedor son la cola viva acotada; el histórico particionado es el artefacto operativo persistido. No se creará otra base histórica francesa.

### 2.3 Selección e interpolación

Rainmapper ya:

- combina estaciones de distintas fuentes;
- limita la selección a 15 km;
- pondera por distancia horizontal con IDW;
- corrige temperatura según la diferencia entre altitud de estación y microárea;
- excluye de la corrección térmica estaciones sin altitud;
- conserva estaciones distintas aunque tengan nombres parecidos.

Por tanto, no se añadirá otra ponderación vertical genérica. La altitud ya interviene donde existe una corrección física implementada: temperatura. Para lluvia y humedad se mantendrá el contrato actual hasta disponer de evidencia para cambiarlo.

## 3. Fuente primaria: CSV diarios de Météo-France

Dataset oficial:

https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes

Metadatos de estaciones:

https://www.data.gouv.fr/datasets/informations-sur-les-stations-metadonnees

El conjunto diario ofrece recursos comprimidos por departamento y periodos. Para D09 y D66 se utilizarán los bloques necesarios de:

```text
RR-T-Vent
autres-parametres
```

Aquí **diario** significa que cada fila representa una estación y un día; no que Météo-France publique un fichero independiente por cada jornada. Cada recurso es una serie acumulada para un departamento y un intervalo de años.

En la consulta del 8 de septiembre de 2026, los cuatro recursos recientes eran:

| Departamento | Periodo | Bloque | Actualización |
|---|---|---|---|
| D09 | 2025–2026 | `RR-T-Vent` | diaria |
| D09 | 2025–2026 | `autres-parametres` | diaria |
| D66 | 2025–2026 | `RR-T-Vent` | diaria |
| D66 | 2025–2026 | `autres-parametres` | diaria |

Los periodos antiguos son también series de resolución diaria, pero sus ficheros se actualizan con menor frecuencia. Para mantener Rainmapper se vuelve a descargar el recurso reciente y se hace upsert por estación y fecha; no se interpreta el fichero completo como un único valor acumulado.

La descarga debe descubrir los recursos vigentes desde los metadatos del dataset; no debe fijar en código una URL que contenga un rango anual cambiante.

### Por qué no se usa primero la API de pedidos

Los ficheros departamentales:

- no requieren secreto;
- permiten reconstrucción reproducible;
- reducen llamadas y estados asíncronos;
- incluyen el histórico necesario para las observaciones de la zona;
- son pequeños cuando se limita el trabajo a D09 y D66.

La API climatológica queda como alternativa futura para consultas por estación o periodos concretos, no como dependencia de la primera entrega.

## 4. APIs Météo-France

### 4.1 Observaciones oficiales de tiempo real, sólo si hicieran falta

API oficial:

https://www.data.gouv.fr/dataservices/api-donnees-dobservation

Documentación:

https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/853639294/API%2BCibl%2Be%2BDonn%2Bes%2Bd%2BObservation

Esta API de Météo-France:

- requiere una cuenta y suscripción gratuita;
- conserva las últimas 24 horas;
- ofrece observaciones horarias y, según la estación, cada seis minutos;
- actualiza las observaciones horarias aproximadamente en la hora redonda más diez minutos;
- es síncrona y permite consultar una estación concreta.

No se solicitará ni se integrará en la fase inicial. Wunderground ya proporciona
el dato reciente de `IFORMI6` e `IFONTR8` mediante el código y las credenciales
existentes. Sólo si esa cobertura falla de forma relevante se obtendrá un token
y se consultará `/liste-stations` para confirmar cuáles de las estaciones
oficiales forman parte de la red de tiempo real. La presencia en los CSV
climatológicos no demuestra por sí sola que una estación esté disponible en
esta API.

Si se activa en el futuro, para MapLibre se guardará un estado de corta duración
separado del histórico climatológico:

```text
source
station_code
observed_at
temperature
humidity
rain
wind
quality/provenance
```

La capa debe mostrar la hora de la observación y su antigüedad. Un dato intradía nunca se escribirá como si fuera el resumen diario completo.

El predictor actual no utiliza el día en curso: su corte deseado es `issue_date - 1 day` y, si ese día aún no está completo, retrocede al último día completo disponible. Por tanto:

- el dato intradía de MapLibre no cambia las variables del predictor;
- los CSV diarios siguen siendo la fuente principal de entrenamiento y predicción;
- Wunderground puede aportar ayer mediante su resumen diario ya existente;
- cuando llegue el dato climatológico oficial, éste debe sustituir el agregado provisional mediante el upsert normal.

Si se reconsidera esta API, antes de elegir entre siete consultas por estación o
paquetes horarios de D09/D66 se medirán tamaño y cardinalidad reales. No se
transportará a HA un paquete departamental completo si resulta más costoso que
consultar únicamente las estaciones seleccionadas.

### 4.2 API climatológica, si se necesitara después

Servicio oficial:

https://www.data.gouv.fr/dataservices/api-donnees-climatologiques

Base:

```text
https://public-api.meteofrance.fr/public/DPClim/v1/
```

La API climatológica usa un pedido asíncrono:

```text
/commande-station/quotidienne
→ identificador de pedido
→ /commande/fichier
```

La autenticación vigente utiliza:

```http
Authorization: Bearer <token>
```

No se enviará el token como parámetro `apikey`. El token nunca se guardará en el repositorio. La fecha final de un pedido diario debe seguir el formato y la semántica inclusiva descritos por el Swagger vigente; no se asumirá que `00:00:00Z` incluye el último día completo.

Guía oficial:

https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/1447788546/Guide%2Bde%2Bd%2Bmarrage%2Brapide%2Bd%2Bcouvrir%2Bles%2BAPIs%2Bde%2BM%2Bt%2Bo-France

Límite publicado: 50 peticiones por minuto.

## 5. Mapeo al contrato Rainmapper

### 5.1 Identidad y fecha

| Météo-France | Rainmapper |
|---|---|
| `NUM_POSTE` | `station_code` |
| `NOM_USUEL` | `station_name` |
| `AAAAMMJJ` | `local_date` en formato `YYYYMMDD` |
| `LAT` | `lat` |
| `LON` | `lon` |
| `ALTI` | `altitude` |

Las coordenadas y altitud deben contrastarse con el catálogo oficial. La clave de upsert será:

```text
("meteofrance", station_code, local_date)
```

### 5.2 Variables

| Météo-France | Rainmapper | Regla |
|---|---|---|
| `RR` | `rain_mm` | mm; conservar `null` |
| `TN` | `min_temp_celsius` | °C |
| `TX` | `max_temp_celsius` | °C |
| `UN` | `min_humidity_percent` | % |
| `UX` | `max_humidity_percent` | % |
| `FFM` | `wind_avg_kmh` | multiplicar m/s por 3,6 |
| `FXI3S`, si existe; si no `FXI` | `wind_gust_kmh` | multiplicar m/s por 3,6 |
| dirección asociada a la racha elegida | `wind_gust_direction_deg` | grados |

El contrato operativo actual no guarda temperatura media ni humedad media como columnas independientes. `TM` y `UM` pueden conservarse en el artefacto raw/de auditoría, pero no justifican ampliar el contrato en esta entrega.

La dirección media y la dirección de racha tienen columnas canónicas, aunque no todos los consumidores las cargan actualmente. La integración debe preservarlas en el histórico sin afirmar que ya son predictores.

### 5.3 Nulos y precedencias

- Un campo vacío o inválido se transforma en `null`.
- `RR = 0` es lluvia observada de cero y debe conservarse.
- Nunca se sustituye lluvia, viento o humedad ausente por cero.
- `FXI3S` sólo gana a `FXI` si su valor es válido; su dirección debe proceder del mismo máximo elegido.
- No se calculará `UM` como `(UN + UX) / 2`.

## 6. Calidad y procedencia

Météo-France acompaña muchas variables con `Qxxx`. Según la documentación diaria:

```text
0 = valor definitivamente validado o protegido
1 = valor validado
2 = valor dudoso y en verificación
9 = valor filtrado que ha superado los primeros controles
```

Documento descriptivo oficial:

https://static.data.gouv.fr/resources/donnees-climatologiques-de-base-quotidiennes/20260603-085232/climatologie-donnees-quotidiennes-descriptif-20260603.pdf

Decisión para Rainmapper:

1. El parser validará tipos y rangos y no aceptará silenciosamente valores imposibles.
2. No se descartarán de forma general los valores con flag `9`.
3. El fichero descargado, sus hashes, fecha de consulta y flags permanecerán en staging o evidencia de auditoría.
4. El Parquet operativo seguirá siendo compacto; no contendrá un JSON raw ni un diccionario de calidad por cada fila.
5. Cualquier política de exclusión basada en `Qxxx` requerirá una auditoría específica y pruebas antes de cambiar datos de entrenamiento o predicción.

Validaciones mínimas:

```text
rain_mm >= 0
0 <= humidity <= 100
-50 <= temperature <= 55
wind_speed >= 0
0 <= wind_direction <= 360
coordenadas y altitud presentes en catálogo
```

Un valor anómalo se rechaza del contrato operativo y queda explicado en el informe de ingestión; no se convierte en cero.

## 7. Estaciones verificadas

La disponibilidad indicada aquí procede de los CSV oficiales diarios D09 y D66 de 2025–2026 comprobados el 8 de septiembre de 2026. Debe volver a calcularse al importar, no codificarse como una capacidad eterna.

### 7.1 Targasonne `66202001`

Ficha oficial:

https://donneespubliques.meteofrance.fr/metadonnees_publiques/fiches/fiche_66202001.pdf

```text
altitud: 1600 m
papel: estación oficial principal del extremo Font-Romeu
estado inicial: enabled
```

En la comprobación realizada ofrecía serie continua de lluvia, temperatura y humedad; el viento medio estaba prácticamente completo. Debe ser la primera prueba end-to-end.

### 7.2 Formiguères `66082004`

Ficha oficial:

https://donneespubliques.meteofrance.fr/metadonnees_publiques/fiches/fiche_66082004.pdf

```text
altitud: 1495 m
papel: estación oficial central y referencia principal para el sector Quérigut
estado inicial: enabled
```

En la comprobación realizada ofrecía serie continua de lluvia, temperatura, humedad y viento.

### 7.3 Railleu `66157001`

```text
altitud: 1366 m
papel: tercera estación base para lluvia y temperatura
estado inicial: excluded_outside_operational_scope
```

En los ficheros comprobados tenía la serie de lluvia y temperatura prácticamente
completa, pero no humedad ni viento diarios. Se excluye por decisión de ámbito:
queda demasiado lejos del corredor operativo y no se configurará como estación
de Rainmapper.

### 7.4 Red complementaria inicial

Estas cuatro estaciones se han evaluado, pero no forman parte de la primera
entrega porque mostraban periodos o variables incompletos:

```text
09193400  Mijanes
09023400  Ascou-Pailhères
66004401  Les Angles
66124402  Font-Romeu-Galinera
```

No se activarán por nombre. El importador calculará por estación y periodo:

- primera y última fecha;
- días disponibles por variable;
- porcentaje de cobertura;
- coordenadas y altitud;
- flags de calidad encontrados.

Sólo se importará alguna como estación complementaria si una microárea futura
demuestra un hueco. El selector actual ya omite un valor ausente para ese día y
variable.

Otras estaciones de alta montaña o más alejadas —Formiguère `66082400`, Capcir Nordique `66098400`, Puigmal-Nivôse `66067402`, Porte-Puymorens `66147402` y Saint-Pierre-dels-Forcats `66188401`— quedan fuera de la configuración inicial. Se reconsiderarán si una microárea o variable demuestra un hueco.

### 7.5 Quérigut `09239005`

No apareció en los ficheros regulares ni complementarios D09 de 2025–2026 comprobados. Estado:

```text
disabled_pending_official_data
```

No se utilizará hasta que una fuente oficial vigente demuestre datos suficientes. La zona de Quérigut sí está dentro de la fase inicial, pero se reconstruirá con las estaciones cercanas que realmente tienen datos.

### 7.6 Wunderground ya operativo

La generación canónica local activa del 8 de septiembre de 2026 contiene:

| Estación | Lugar | Altitud del catálogo HA | Histórico canónico local | Días / cobertura |
|---|---|---:|---|---:|
| `IFORMI6` | Formiguères | 1640 m | 2025-09-01 → 2026-09-08 | 292 / 373 (78,3 %) |
| `IFONTR8` | Font-Romeu-Odeillo-Via | 1953 m | 2022-11-04 → 2026-09-08 | 1.286 / 1.405 (91,5 %) |

`IFORMI6` tiene un backfill aproximado de un año. Su hueco más largo es de 47
días, entre el 3 de noviembre y el 21 de diciembre de 2025. `IFONTR8` tiene casi
cuatro años; su hueco más largo es de 61 días, entre el 31 de julio y el 1 de
octubre de 2023. Estos huecos impiden tratarlas como fuente única del histórico,
pero no reducen su valor como cobertura local y reciente.

Las dos estaciones respondieron también en la API de Wunderground el 9 de
septiembre de 2026. Ambas están en el catálogo canónico local y `stations.txt`
local ya incluye sus dos URLs. El CSV auxiliar local
`estacions_wunderground.csv` todavía sólo contiene `IFONTR8`; no debe utilizarse
ese snapshot auxiliar para concluir que falta el backfill de `IFORMI6`, porque el
catálogo y las particiones canónicas sí lo contienen.

## 8. Infoclimat/StatIC: evaluado y descartado para este corredor

OpenData:

https://www.infoclimat.fr/opendata/

Infoclimat exige clave, limita normalmente las peticiones a intervalos máximos
de siete días y aplica licencia por estación. Las pruebas se conservan como
evidencia de la evaluación, pero **no se implementará esta fuente** en el alcance
actual. No se hará scraping de HTML.

### Candidatas

| Estación | ID probado | Resultado API 2026-09-08 | Decisión |
|---|---|---|---|
| Osséja | `000EN` | `OK`; datos actuales; CC BY-NC | No integrar: ganancia insuficiente |
| Font-Romeu nueva | `STATIC0478` | `warning`; estación no autorizada | Desactivada |
| Mérens-les-Vals | `000BR` | `OK`; datos actuales; CC BY-NC | No integrar: fuera del corredor piloto |
| Font-Romeu anterior | `000RX` | `OK`; archivo accesible desde 2020-06-17 hasta 2026-05-26; CC BY | Sólo histórico; no fusionar con `STATIC0478` |
| Formiguères | `07737` y `MF66082004` | ambos `warning`; estación no autorizada | Usar Météo-France directa |
| Les Angles | `MF66004401` | `warning`; estación no autorizada | Usar Météo-France directa |
| Quérigut | `MF09239005` | `warning`; estación no autorizada | Sin fuente Infoclimat confirmada |

Fichas:

- https://www.infoclimat.fr/stations/metadonnees.php?id=000EN
- https://www.infoclimat.fr/stations/metadonnees.php?id=STATIC0478
- https://www.infoclimat.fr/stations/metadonnees.php?id=000BR
- https://www.infoclimat.fr/stations/metadonnees.php?id=000RX

Aunque `STATIC0478` aparece con actividad reciente y licencia Etalab en el
catálogo ampliado, la petición autenticada la rechazó. La presencia en catálogo
no demuestra disponibilidad para una clave concreta. Las pruebas completas,
incluida la diferencia entre sumar `pluie_1h` y usar el cierre `pluie_24h`, se
conservan en `rainmapper_infoclimat_static_handoff.md` como informe de una opción
descartada.

## 9. Duplicados y traslados

Rainmapper no deduplica por nombre y no debe empezar a hacerlo.

La clave `(source, station_code)` permite conservar por separado:

- estaciones de nombres iguales;
- traslados con códigos diferentes;
- redes distintas.

Para la fase 1 se mantendrá una lista explícita de exclusiones o réplicas conocidas. Distancia, diferencia de altitud y solapamiento temporal pueden generar un informe de posibles duplicados, pero nunca una fusión automática.

No hace falta crear todavía tablas `weather_station` y `weather_station_source`. Esa abstracción sólo se reconsiderará si aparecen múltiples réplicas reales que no puedan gestionarse con la identidad actual.

## 10. Descarga, actualización e idempotencia

### Météo-France

1. Descubrir los recursos D09 y D66 vigentes del dataset oficial.
2. Descargar únicamente los periodos necesarios para el histórico y la cola viva.
3. Verificar que la respuesta es un CSV comprimido válido y registrar hash/tamaño.
4. Unir `RR-T-Vent` y `autres-parametres` por `NUM_POSTE + AAAAMMJJ`.
5. Filtrar las estaciones configuradas.
6. Normalizar a filas Rainmapper.
7. Colapsar por `(source, station_code, local_date)` haciendo que el valor nuevo no nulo gane.
8. Capturar el pending batch antes de actualizar la cola viva, como exige el flujo particionado.
9. Aplicar el lote de forma atómica y promocionar una generación coherente.

Las descargas recientes pueden solaparse con datos ya existentes: el upsert debe ser idempotente y permitir correcciones oficiales.

### Wunderground existente

`IFORMI6` e `IFONTR8` seguirán el ciclo normal de actualización de
Wunderground. No se creará una descarga francesa separada. Los huecos históricos
se auditarán por estación y fecha; no se rellenarán inventando ceros ni copiando
automáticamente otra estación.

## 11. Cambios de código previstos

La implementación mínima debería concentrarse en:

```text
rainmapper_core/sources/meteofrance/       parser y descarga oficial
rainmapper_core/weather_history_contract.py
rainmapper_core/mushroom_observation_context.py
rainmapper_core/weather_live_csv.py
rainmapper_core/mushroom_weather_idw.py
tests dirigidos de parser, contrato, histórico e IDW
```

Antes de editar se debe buscar cualquier otra enumeración cerrada de fuentes. `weather_official_maintenance.py`, `weather_official_repair_state.py` y los scripts de reparación actuales sólo contemplan AEMET/Meteocat; no se ampliarán mecánicamente sin decidir si la nueva fuente participa realmente en ese flujo de reparación.

No se crearán en la fase 1:

```text
WeatherProvider ABC
AemetProvider / MeteocatProvider reescritos
base de estaciones físicas
nuevo formato de almacenamiento
conversión global de km/h a m/s
raw_payload por fila operativa
```

## 12. Pruebas

### Unitarias

- parser de ambos bloques oficiales;
- números con coma decimal, vacíos y valores anómalos;
- join por estación/fecha sin multiplicar filas;
- mapping de lluvia, temperatura, humedad, viento y racha;
- conversión exacta m/s → km/h;
- precedencia coherente de racha y dirección;
- conservación de `RR = 0` y de `null`;
- normalización a fuente `meteofrance`;
- upsert idempotente y corrección de días ya existentes;
- catálogo con coordenadas y altitud;
- lectura filtrada por `(source, station_code)`;
- IDW con estaciones españolas y francesas simultáneamente;
- temperatura corregida por altitud;
- rechazo de estaciones a más de 15 km.

### Integración local

- importar muestras fijas D09 y D66 sin red;
- materializar un pending batch;
- aplicarlo a una copia temporal de la cola viva y del histórico;
- validar manifiestos, hashes, particiones y catálogo;
- ejecutar reconstrucción meteorológica sobre las microáreas piloto;
- repetir la importación y demostrar que no aparecen duplicados.

Las pruebas de red serán opcionales y no formarán parte de la suite ordinaria.

## 13. Fases

### Fase 1 — Météo-France D66 y Wunderground existente

1. Mantener `IFORMI6` e `IFONTR8` en la lista Wunderground y auditar su
   actualización diaria.
2. Crear microáreas piloto y calcular qué estaciones caen dentro de 15 km.
3. Implementar el parser del recurso diario D66 de Météo-France.
4. Añadir `meteofrance` al contrato histórico existente.
5. Activar Targasonne y Formiguères como red oficial inicial.
6. Importar el histórico necesario y generar catálogo.
7. Reutilizar para MapLibre el dato reciente de Wunderground, mostrando fecha,
   antigüedad y si el día está incompleto.
8. Validar el circuito local meteorológico y la selección multifuente.

### Fase 2 — completar cobertura

1. Auditar huecos por microárea y variable.
2. Probar estaciones oficiales parciales sólo si cubren un hueco.
3. Si Wunderground no basta para la presentación reciente, evaluar entonces la
   API oficial de observaciones de Météo-France.
4. Extenderse hacia Haute-Ariège o Mérens únicamente cuando exista una microárea de ese ámbito.

### Fase 3 — mejoras justificadas

- evaluar flags `Qxxx` con datos reales;
- automatizar descubrimiento/correcciones si el flujo manual inicial lo necesita;
- reconsiderar una entidad física de estación sólo si los duplicados reales lo exigen.

## 14. Criterios de aceptación

- [ ] `meteofrance` está reconocido por todos los contratos necesarios y por sus pruebas.
- [ ] El recurso D66 se descubre sin fijar nombres anuales cambiantes.
- [ ] Targasonne y Formiguères se importan con fuente, código, coordenadas y altitud correctos.
- [ ] Railleu y las candidatas D09 quedan fuera de la configuración inicial.
- [ ] Los valores se normalizan al contrato actual; viento y racha quedan en km/h.
- [ ] Los nulos siguen siendo nulos y `RR = 0` sigue siendo cero observado.
- [ ] El histórico queda particionado y validado con clave `(source, station_code, local_date)`.
- [ ] La actualización repetida es idempotente y acepta correcciones oficiales.
- [ ] El catálogo permite seleccionar estaciones francesas con el filtro actual.
- [ ] La reconstrucción respeta el radio de 15 km y la corrección térmica por altitud.
- [ ] Una prueba combina aportaciones francesas y españolas sin colisiones.
- [ ] Los flags y la procedencia quedan auditables sin inflar el payload operativo.
- [ ] Wunderground aporta datos recientes de `IFORMI6` e `IFONTR8` mediante el flujo existente.
- [ ] MapLibre distingue claramente observación intradía, acumulado parcial y día completo.
- [ ] Ninguna observación intradía entra en el predictor como si fuera un día cerrado.
- [ ] Infoclimat no se integra en el alcance actual.
- [ ] Ningún secreto se guarda en el repositorio.

La primera entrega termina cuando Rainmapper puede reconstruir el histórico de
las microáreas del corredor **Quérigut–Font-Romeu con Targasonne y Formiguères**
y, por el canal Wunderground existente, presentar en MapLibre las estaciones del
corredor que estén disponibles en tiempo real.
