# SMI-07 · Adopción del estado hídrico compartido

Decisión del usuario, 20/09/2026: adoptar **extracción regulada + Penman–Monteith
+ una capa de 0–30 cm** para entrenamiento, precálculo e inferencia del mapa.
El depósito simple original queda exclusivamente como comparación visual en el
mapa, pendiente de retirada. Esta decisión acepta una estimación orientativa;
no certifica litros absolutos ni evapotranspiración real del bosque.

## Justificación y evidencia

La secuencia completa está en el [índice de auditorías](../README.md).

- [SMI-03](../baseline-2026-09-19/README.md): 22 estaciones, separación de la
  regla de extracción y de ET₀. El simple descuenta demanda sin atenuarla durante
  el secado; el regulado incorpora disponibilidad y estrés progresivos.
- [SMI-04](../layers-2026-09-19/README.md): la cascada de dos capas ensayada
  pierde recargas profundas y empeora superficie. Más complejidad no garantizó
  mejor respuesta; no se promociona esa estructura.
- [SMI-05](../factorial-2026-09-20/README.md): ocho combinaciones. Comparación
  conjunta de profundidades con lluvia IDW; 18 estaciones comunes. Mediana de
  correlación de la referencia 0,667 frente a 0,640/0,624/0,615 de las otras
  reguladas. Son diferencias próximas y no prueban exactitud de cantidades.
- [SMI-06](../storage-2026-09-20/README.md): 1.206 cambios diarios, 68 recargas,
  27 secados. La referencia tiene mediana de residuo absoluto diario 1,034 L/m²,
  recarga +3 días 3,252, secado 5 días 1,692. No domina todas las métricas:
  dos capas mejora algunas recargas y Hargreaves algunos secados. Sesgos
  condicionados de +2,49 L/m² en recarga y +1,33 en pérdida de cinco días.
  No son precisión certificada del SMI ni sesgo de los litros restantes.

Se adopta una referencia práctica y reproducible apoyada en el conjunto de
resultados, no un supuesto ganador universal. La entrada principal del contraste
fue **lluvia IDW**, como en los puntos operativos. Las sondas externas se usan
para auditoría, sin añadir una dependencia de Copernicus/ICGC al cálculo.

## Contrato físico aceptado

`regulated_pm_single_layer_v1` en
[el módulo compartido](../../../../rainmapper_core/mushroom_water_physics.py).
La antigua ruta `mushroom_map_water_physics.py` es una compatibilidad de imports,
sin copia de las ecuaciones. HA y worker importan el mismo código.

- ET₀ FAO Penman–Monteith de referencia: temperatura/humedad IDW, temperatura
  corregida por altitud, presión según altitud. Radiación estimada con amplitud
  térmica y coeficiente continental 0,16. No se inventa una corrección de dosel,
  sombra u orientación. Viento XEMA diario con altura conocida, normalizado a
  2 m; dentro de 15 km prioriza altitud similar y distancia. Sin viento admisible,
  2 m/s estimados. Sin humedad/altitud suficiente o PM no calculable, fallback
  explícito Hargreaves. `reference_et_series` devuelve el método diario; el mapa
  muestra recuentos de todo el historial. Ausencia de temperatura no es ET₀ cero.
- Una reserva: evaporación proporcional a S/C y transpiración con
  Ks=min(1,S/((1−p)C)), p=0,5, reparto 50/50. Integración analítica diaria.
  Lluvia al inicio del día, exceso drenado antes de extraer. ΔS=P−extracción−drenaje.
  No representa raíces profundas, interceptación, nieve o escorrentía.
- Capacidad C: suma `(wv0033−wv1500) × espesor en m` en 0–5/5–15/15–30 cm;
  SoilGrids Q0.50 a 250 m. Describe tierra fina, sin corrección por piedras.
  SMI=100×S/C; L/m² disponibles=S. No es contenido total volumétrico de una sonda.
- Historia de hasta 365 días, independiente de la ventana visible. Cada fecha
  publicada exige ≥90 días completos consecutivos y diferencia entre arranques
  seco/lleno ≤max(1 mm,1%C). Se usa la media de ambos. Un hueco reinicia la
  incertidumbre. No se publican fechas anteriores basándose en una convergencia
  posterior. Los cambios de 7/14 días requieren esos días válidos adicionales.
- En ML se utiliza fracción 0–1; en el mapa porcentaje 0–100. Por áreas se
  calcula primero cada microárea y después se agregan las reservas disponibles.
  No se simula un único suelo sobre la meteorología media de toda el área.

**Balance climático** sigue siendo lluvia−ET₀. No se renombra como cambio de
reserva: la extracción regulada puede ser inferior a ET₀ y hay drenaje.

## Rutas unificadas

| Ruta | Implementación |
|---|---|
| Física y elección de ET₀ | `mushroom_water_physics.py` |
| Estado SoilGrids/variables agregadas | `mushroom_soil_water_state.py` |
| Entrenamiento con caché | `mushroom_ml_weather_workspace.py` |
| Constructores de datos independientes | `scripts/build-biology-v4-benchmark.py`, `scripts/build-biology-v5-raw-benchmark.py` |
| Inferencia/precálculo | `mushroom_ml_area_weather_runtime.py`, `mushroom_ml_runtime_features.py` |
| Mapa e histórico comparativo | `mushroom_map_hydrology.py`, `mushroom_map_weather.py` |

V4 recibe la misma ET₀ calculada por microárea antes de promediar, en vez de
recalcular Hargreaves sobre temperaturas medias del área. El lector meteorológico
común conserva ahora `wind_source_height_m`; no se limita al lector del mapa.
El precálculo usa los adaptadores de inferencia, sin otra implementación de SMI.
Los perfiles con reserva piden 365 días también en la ruta sin catálogo; los
perfiles de balance climático sin reserva conservan 90 días. Las estaciones
excluidas tampoco pueden aportar viento a la ET₀. La selección espacial del
viento se calcula una vez por serie, no una vez por día.

## Qué modelos consumen estas variables

Comprobado contra los perfiles de `mushroom_ml_version_registry.json`, columnas
V3+/V4, `mushroom_ml_raw_weather.py` y `mushroom_ml_smooth_hierarchical.py`.

| Versión/perfil registrado | Estado hídrico usado |
|---|---|
| V2 `common_idw` | No usa SMI ni balance climático |
| V3 `core` | No usa SMI ni balance climático |
| V3+ `common_idw_plus_physical_state` | Cuatro balances por ventanas y siete variables de reserva: media, mínimo, cambios 7/14, recarga, déficit y secado |
| V4 `extended_weather` | No usa SMI ni balance climático |
| V4 `climatic_balance` | Balance climático por ventanas; no SMI |
| V5 `raw_primary_plus_physical_state` | ET₀, balance y fracción del suelo diarios (365 días), más siete variables de reserva |
| V6 `smooth_weather_physical_state` | Mismos canales físicos diarios mediante su transformación temporal, más variables de reserva |
| V5w/V6w de 30/60/90 días | Siete variables de reserva calentadas con 365 días; no los canales físicos diarios completos |

El constructor V4 también admite un bloque `soil_water`, pero **no es un perfil
registrado del catálogo actual**. No confundir capacidad del código con modelos
instalados. No se han consultado los ganadores actuales de HA real.
HGB/KNN/SVM/logística/árboles consumen las variables de su **perfil**: su nombre
de estimador no decide si utilizan SMI. Tampoco toda predicción de rovelló lo usa.

## Migración sin mezclar significados

- Cambian los contratos de estado y balance a v2; la revisión de entrenamiento
  incorpora `regulated_pm_single_layer_v1`. Cambian la identidad del runtime y
  el esquema del precálculo a 1.7, invalidando resultados de la semántica previa.
- Los constructores V4/V5 marcan el contrato de sus datos; V3+ y los perfiles
  derivados lo propagan. El entrenador rechaza datos físicos sin ese contrato.
- Los nuevos pesos físicos guardan el contrato. Tanto la carga como la inferencia
  rechazan pesos antiguos que contengan variables hídricas. **No basta con cambiar
  el JSON ni hacer solo precálculo: hay que reconstruir datos y reentrenar.**
- Los pesos sin variables hídricas no se rechazan por esta comprobación.
  No se reactiva ningún estimador suspendido ni se cambian reglas de selección.
- Las auditorías y sus snapshots quedan congelados. No recalcular un informe
  histórico con la implementación nueva y atribuirle sus métricas antiguas.

## Validación local y límite de entrega

[verify.py](verify.py) y [parity.json](parity.json): igualdad exacta con los valores
archivados de las **22 estaciones / 1.320 fechas** para SMI regulado, simple,
ET₀, balance, métodos y huecos. Conservación de masa verificada. El archivo
registra hashes del código y de la entrada, sin copiar los datos de nuevo.

`tests/test_mushroom_water_unification.py`: paridad entre mapa, caché de entrenamiento,
inferencia y constructores V4/V5 reales, con/sin caché; escala del SMI; ventanas;
huecos; fallback; entrenamiento reducido real e inferencia; rechazo de pesos
antiguos. Las pruebas preexistentes cubren fórmulas FAO, integración, transporte
meteorológico, contratos de runtime/precálculo y registros. La prueba de navegador
comprueba ambas curvas, leyendas, tooltips y diseño escritorio/móvil.

Resultado del 20/09/2026: **322 pruebas dirigidas superadas**. Tras corregir
el historial del perfil físico en la ruta sin catálogo, se repitieron sus
pruebas y las de paridad compartida: **42 superadas**. El navegador terminó
con `ok: true`; `git diff --check`, sin incidencias. Comandos reproducibles en
[validation.md](validation.md). Los scripts antiguos de auditoría que ensayan
Hargreaves no forman parte del circuito operativo; sus informes históricos no
se regeneraron ni se reinterpretaron como resultados de este contrato.

**Publicado en HA 0.2.315; instalación confirmada por el usuario al cierre del
20/09.** Los resultados anteriores describen las pruebas iniciales del checkout.
Después se reconstruyeron HA local y worker desde el mismo código, conservando
coordinadores; reconstrucción/base promovidos, 714 ajustes correctos y precálculo
recibido/activado revisión 69. Smoke final 1690 pruebas/48 omitidas y paridad
efectiva 211/114 archivos. [Circuito, hashes y publicación](validation.md).
Los nuevos trabajos y artefactos de HA real aún no se han verificado: la
confirmación de instalación no acredita reconstrucción, entrenamiento o precálculo.

Ver también [la revisión pública de Mycora](mycora.md).
