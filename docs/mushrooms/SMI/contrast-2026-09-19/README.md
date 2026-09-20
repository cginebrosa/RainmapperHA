# Primer contraste externo del SMI — 19 de septiembre de 2026

El objetivo es comprobar y mejorar **el cálculo propio de Rainmapper**. Estas
descargas son referencias de auditoría; no se han integrado en el mapa, en el
predictor, en HA real ni en el worker. No se han ajustado parámetros para acercar
las curvas a Copernicus.

## Resultado y decisión que permite tomar

La extracción regulada con la ET₀ nueva reproduce mejor la tendencia de humedad
en Vallcebre y Batlliu de Sort que el depósito simple. En Olvan la ventaja global
es modesta y no se sostiene al dividir el periodo en dos mitades. En Camí dels
Nerets el resultado es malo. **No queda validada la exactitud de los porcentajes
ni de los litros disponibles, ni la evapotranspiración real del bosque.**

El cálculo nuevo es un candidato razonable para seguir contrastando, no una
calibración terminada. Tampoco basta con hacer la curva más suave. La comparación
cambia a la vez ET₀ y extracción: estos resultados no permiten atribuir la mejora
exclusivamente a Penman–Monteith o exclusivamente a la regulación del depósito.

## Evidencia obtenida

Periodo: **21/07/2026–18/09/2026**, 60 días. Ambos cálculos locales conservaron
un historial total de 365 días, desde 19/09/2025, que incluye los 60 días
comparados; no se reiniciaron al principio de la ventana dibujada. La serie fue calculada en el contenedor existente
`rainmapper-local-rainmapper-ha-ui-1`. Las huellas de los tres módulos ejecutados
están en `evidence.json.gz → provenance.local_code_sha256`.

| Punto | Latitud, longitud | Días con SWI numérico / consultados |
|---|---|---:|
| Urús | 42.31870, 1.85001 | 0 / 60 |
| Vallcebre | 42.22774, 1.80512 | 60 / 60 |
| Bellver, 1572 m | 42.31107, 1.79181 | 0 / 60 |
| Bellver, 1825 m | 42.31461, 1.79936 | 0 / 60 |
| Olvan | 42.06237, 1.93813 | 60 / 60 |

Se consultó el píxel que contiene cada punto, alineado con la malla publicada
de 1/112°, mediante Statistical API y vecino más próximo: **un píxel por día**.
No se descargaron mapas completos de Europa. Las cinco series ocuparon unos
560 kB en las respuestas JSON. Urús y Bellver devolvieron DN=255 y dataMask=0:
son ausencias, no ceros, y no se sustituyeron por píxeles vecinos.

Se conservaron las ocho escalas T=2,5,10,15,20,40,60,100, todas sus QFLAG y SSF.
Para la comparación exploratoria se exigió dataMask=1, SWI DN entre 0 y 200 y
QFLAG ≥70%; este último es un umbral conservador de esta auditoría, no una regla
universal del producto. En ambos puntos todos los días lo superan; QFLAG T=10
es como mínimo 93,5%. Se aplicó factor 0,5 únicamente a valores numéricos SWI/QFLAG.

**Pendiente de calidad:** SSF devuelve 2 en los 60 días de ambos puntos. No se ha
confirmado la semántica de ese código para esta colección: la documentación de
la API/manual indica factor 1, mientras que el STAC del COG indica factor 0,5
para SSF. No se ha supuesto que signifique «descongelado», ni se ha aplicado una
regla de otra versión/producto. La lectura directa de la cabecera original por
OData devolvió 401 con este cliente OAuth, aunque Statistical API sí funciona.
Por ello, los resultados satelitales siguientes son **exploratorios**, pendientes
de aclarar SSF antes de una aceptación formal. La comparación con sondas no
depende de esa ambigüedad.

## Evolución: comparación sin ajustar parámetros

Correlación de Pearson entre las series diarias, por fecha publicada y sin
desplazamiento. Los 60 días están autocorrelacionados: **r no es un porcentaje
de acierto**, ni se presentan estos resultados como un test estadístico independiente.

| Ubicación y referencia | Depósito simple | Extracción regulada |
|---|---:|---:|
| Vallcebre · SWI T=10 | 0,469 | **0,835** |
| Olvan · SWI T=10 | 0,502 | **0,590** |
| Batlliu de Sort · sonda a 20 cm | 0,406 | **0,805** |
| Camí dels Nerets · sonda a 20 cm | −0,111 | **−0,689** |

Se muestra T=10 como una referencia intermedia, no porque sea el mejor resultado
ni porque equivalga exactamente a 0–30 cm. `metrics.csv` incluye las ocho T y las
sondas a 5, 20 y 50 cm. Por ejemplo, frente a T=2:
Vallcebre pasa de r=0,687 a 0,800; Olvan, de 0,748 a 0,803.

Las diferencias diarias concuerdan bastante menos que las tendencias:
frente a T=10, r de los cambios diarios del cálculo nuevo es 0,276 en Vallcebre
y 0,029 en Olvan. Al emparejar el cálculo con el SWI del día siguiente suben a
0,469 y 0,372, respectivamente. Esto es un diagnóstico de sensibilidad temporal,
no un desfase elegido para declarar éxito. Los compuestos satelitales cierran a
mediodía UTC y no coinciden con el cierre de un día local.

La separación en dos mitades evita resumir todo con una cifra favorable:

| Referencia T=10 | Primeros 30 días: simple / regulado | Últimos 30: simple / regulado |
|---|---:|---:|
| Vallcebre | 0,696 / 0,858 | 0,294 / 0,848 |
| Olvan | 0,879 / 0,830 | 0,346 / 0,335 |

En Olvan, por tanto, la mejora global no demuestra una ventaja consistente.

## Sondas: control en la ubicación real del instrumento

Se descargaron medidas a intervalos de 30 minutos del visor público XMS-Cat:

- Batlliu de Sort: 42.4285249875, 1.1243820190. 48 registros diarios durante 60 días.
- Camí dels Nerets: 42.1555139803, 0.9255981445. 48 registros en 59 días y 44 en uno.

El cálculo de Rainmapper se ejecutó en esas coordenadas, no se trasladó la sonda
a Vallcebre u Olvan. Las curvas usan medias diarias en la fecha publicada.
La zona horaria de los timestamps de XMS no quedó confirmada y la descarga no
incluye indicadores de control instrumental. No se convierten las sondas de
m³/m³ a porcentaje de agua disponible sin capacidad de campo y punto de marchitez
medidos en la estación.

Batlliu muestra concordancia favorable a 5 y 20 cm con el nuevo cálculo
(r=0,796 y 0,805; simple: 0,312 y 0,406). No basta para generalizar a todos los bosques.
En Camí dels Nerets, la sonda de 20 cm solo oscila entre 0,07054 y 0,07381 m³/m³
y no sigue nuestras recargas. Se desconoce si la discrepancia se debe a la
representatividad del perfil, infiltración, entradas, instrumento o modelo.
**No se elimina ese caso para mejorar el resultado.**

### La lluvia de entrada también necesita auditoría

| Estación | Pluviómetro XMS, mm | IDW Rainmapper, mm |
|---|---:|---:|
| Batlliu de Sort | 161,5 | 91,2 |
| Camí dels Nerets | 46,5 | 40,1 |

Son sumas del periodo, sin corregir el día con cuatro registros ausentes.
En Batlliu, el 24/08 el pluviómetro registra 37,7 mm y el IDW 3,2 mm.
La diferencia acumulada no se resuelve con mover unas horas la fecha de un evento.
Esto evidencia desacuerdo entre entradas, sin convertir automáticamente el
pluviómetro en verdad absoluta: también requiere comprobación de calidad.

Afinar ET₀ para compensar un episodio de lluvia mal representado podría empeorar
el modelo. Antes de ajustar parámetros conviene distinguir estos dos errores.

## Qué significa para un cálculo propio creíble

La muestra externa para el siguiente experimento se ha ampliado a **22 estaciones**,
con 21 candidatas por cobertura. Véase el [inventario y sus limitaciones](expanded-stations.md).
Las métricas de este informe siguen correspondiendo únicamente a los puntos del
primer contraste; no se han recalculado todavía los modelos en las estaciones añadidas.

1. **Conservar el nuevo cálculo como experimental.** Estos datos apoyan investigar
   su dinámica; no justifican llamar medidos o calibrados a sus litros.
2. **Separar las causas.** Repetir el contraste con lluvia medida en la estación,
   solo en el banco de pruebas, manteniendo los demás parámetros. Comparar además
   ET₀ antigua/nueva con la misma regla de extracción para aislar el efecto de cada cambio.
3. **Auditar recarga y secado por episodios.** Verificar cronología y totales de
   lluvia, respuesta a distintas profundidades y persistencia de humedad; no
   optimizar únicamente la correlación de una curva estacional.
4. **Validar fuera de los puntos usados para ajustar.** Más estaciones y estaciones
   del año, con fechas o ubicaciones reservadas. Mantener visibles los fallos.
5. **Solo después ajustar parámetros físicos justificables.** Capacidad, infiltración,
   reparto evaporación/transpiración y regulación. Radiación de ladera o cobertura
   necesitan una prueba específica; esta comparación no las valida.

No hace falta que el usuario mida evapotranspiración personalmente para avanzar:
las estaciones públicas permiten contrastar humedad del suelo. Pero esta prueba
no aísla ET real, ni demuestra que cada pérdida diaria estimada de agua sea correcta.
El objetivo de siguientes pruebas sigue siendo un cálculo autónomo a partir de
nuestras entradas, sin consultas operativas a Copernicus.

## Archivos y reproducción

- `comparison.html`: gráficas interactivas autónomas, sin servidor ni conexión.
- `evidence.json.gz`: respuestas numéricas de esta auditoría, metadatos y huellas;
  unos 79 kB comprimidos, sin credenciales ni tokens.
- `series.csv`: 420 filas de series diarias y marcas, incluidos los puntos sin SWI.
- `metrics.csv`: 44 comparaciones, todas las T, tres profundidades y dos modelos.
- `summary.json`: cobertura, indicadores y métricas estructuradas.
- `analyse.py`: regenera CSV, métricas y HTML desde la evidencia, sin red.

Desde la raíz del repositorio:

```sh
.venv/bin/python docs/mushrooms/SMI/contrast-2026-09-19/analyse.py
```

La generación comprueba unicidad de fechas, 60 días alineados, un píxel por
intervalo, límites de las variables y ausencia de timestamps duplicados en sondas.
Es verificación del procesamiento, no validación de la física del modelo.
También se comprobó la representación del HTML autónomo en Chrome sin interfaz.

## Fuentes

- [SWI europeo V2 y bandas de Sentinel Hub](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/clms/bio-geophysical-parameters/soil-moisture/soil-water-index/swi_europe_1km_daily_v2.html).
- [Manual SWI, edición 08/07/2025](https://land.copernicus.eu/en/technical-library/product-user-manual-soil-water-index-version-1/@@download/file): escala, flags, malla y periodo de los compuestos; T no es profundidad fija. SWI tampoco es una medida directa del agua disponible para plantas.
- [Statistical API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html) y [DN/dataMask de BYOC](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/Byoc.html).
- [Visor oficial XMS-Cat](https://visors.icgc.cat/mesurasols/), sus coordenadas públicas `assets/ParamSols.geojson` y servicio `netmon.icgc.cat/netmon/solsws.php`.
- STAC: colección `clms_swi_europe_1km_daily_v2_cog`; para contraste de metadatos,
  producto `c_gls_SWI1km_202609111200_CEURO_SCATSAR_V2.1.1_cog`, UUID
  `5ce2f4ca-5dc5-4ebb-b68a-604bdd5b0dbd`.
