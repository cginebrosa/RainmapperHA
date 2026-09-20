# Comparación de SMI del mapa

**Actualización 20/09/2026:** referencia aceptada y unificada en el código de
entrenamiento/precálculo/inferencia. [Decisión y estado de despliegue SMI-07](SMI/adoption-2026-09-20/README.md).
El simple permanece solo como comparación visual.

## Informe histórico de implementación, 19/09/2026

Lo que sigue describe la revisión del 19/09, anterior a la adopción. Sus pruebas
no acreditan el despliegue de los cambios transversales del 20/09.

Implementación experimental exclusiva de la ficha del mapa. No modifica el IFF,
los datos de entrenamiento ni las funciones científicas operativas
`mushroom_soil_water_state.py` y `mushroom_climatic_water_balance.py`.
No se ha actualizado HA real ni el worker activo con esta revisión.

## Presentación

- Cabecera: capacidad disponible de 0–30 cm y reserva estimada del método de
  extracción regulada, en porcentaje y L/m². Corresponde al último día del
  histórico, no al día futuro seleccionado para el IFF. Pulsarla abre el detalle. En escritorio son dos líneas: municipio/coordenadas,
  altitud/pH y capacidad/disponibilidad; las coordenadas no se dividen.
- SMI antes del balance, escala compartida 0–100 %, dos colores y leyenda corta:
  **Extracción regulada** y **Depósito simple**. Cada nombre muestra su explicación
  propia al pasar el ratón, enfocarlo con teclado o tocarlo; Escape la oculta.
- **Balance climático diario: lluvia − ET₀**. No es el cambio de reserva ni una
  medición de la evapotranspiración real del bosque. La extracción regulada y el
  drenaje determinan el cambio de reserva: ΔS = lluvia − extracción − drenaje.
- Terreno es el último desplegable. Periodos 7/15/30/60 sincronizados con
  Meteorología observada; cambiar el periodo solo recorta las series recibidas.

Ambas curvas se recalculan para el mismo punto con igual lluvia, capacidad e
histórico de inicialización. La curva de depósito simple reutiliza la función
operativa, pero **no es una lectura del tensor de entrada del modelo de IFF**:
la selección del periodo de inicialización y el soporte espacial pueden diferir.
El IFF seleccionado tampoco tiene por qué utilizar una variable SMI.

## Métodos y límites

`mushroom_map_water_physics.py` implementa ET₀ diaria FAO Penman–Monteith,
referencia de césped, con temperatura/humedad IDW y altitud del punto.
La radiación se estima a partir de la amplitud térmica con coeficiente continental
0,16; no se mide ni se corrige por orientación, sombra o dosel. Viento: media
diaria XEMA con altura conocida, normalizada a 2 m; dentro de 15 km se prioriza
altitud similar y después distancia. Es una aproximación por estación, no viento
interpolado del punto. Sin viento válido se estima 2 m/s; mínimo FAO 0,5 m/s.
La ficha identifica estaciones y los días con viento estimado.

Cuando faltan humedad/altitud o no es calculable PM, se utiliza Hargreaves–Samani.
Los métodos usados se cuentan sobre todo el histórico de inicialización y se
explican en el tooltip y el desplegable de método. Sin lluvia/temperatura válida
se deja un hueco. El depósito simple utiliza siempre Hargreaves–Samani y resta
su demanda mientras quede agua: S = min(C, max(0, S + P − ET₀)).

El nuevo depósito es **un escenario de sensibilidad**, no un modelo forestal
calibrado ni una implementación completa del coeficiente dual FAO:

- Un único depósito de 0–30 cm. Reparto de referencia 50/50 entre dos vías de
  pérdida; ese reparto no se ha inferido de los árboles ni de mediciones.
- Evaporación reducida por la reserva relativa S/C, aproximación sencilla al
  secado superficial. No implementa la capa superficial ni el coeficiente Ke.
- Transpiración limitada por Ks = min(1, S / ((1−p) C)), con p=0,5.
- Integración analítica de las pérdidas durante el día. La lluvia entra al
  principio del día y el exceso drena antes de las pérdidas; el depósito simple
  aplica su orden operativo original (pérdidas y después drenaje).
- Banda de sensibilidad: reparto 0/50/100 % y p=0,3/0,5/0,7. Es una envolvente
  de escenarios, **no un intervalo de confianza**, y no incluye todos los errores.

No modela raíces profundas, interceptación, nieve, escorrentía, pedregosidad ni
exposición real. Una curva más suave no demuestra mayor exactitud sobre el terreno.
El nuevo cálculo no garantiza una ET₀ menor: la mejora del depósito consiste en
reducir la extracción al agotarse la reserva, no en forzar cifras más bajas.

Referencias de ecuaciones: [FAO-56 cap. 3](https://www.fao.org/4/x0490e/x0490e07.htm),
[ejemplo diario de validación, cap. 4](https://www.fao.org/4/x0490e/x0490e08.htm),
[estrés hídrico, cap. 8](https://www.fao.org/4/x0490e/x0490e0e.htm).

## Memoria anterior al periodo visible

`mushroom_map_hydrology.build_history` recibe hasta 365 días, independientemente
de mostrar 7, 15, 30 o 60. Cada día necesita ≥90 días consecutivos completos y
convergencia entre depósitos inicialmente vacío/lleno: diferencia ≤max(1 mm, 1%C).
Los huecos reinician esa comprobación. Una convergencia posterior no valida los
puntos anteriores. Cada método converge por separado; la banda requiere que
converjan todos sus escenarios. El método regulado muestra el centro entre sus
dos inicializaciones convergidas; el simple conserva la inicialización seca.

La capacidad es la suma de `(wv0033 − wv1500) × espesor(m)` para 0–5, 5–15 y
15–30 cm, SoilGrids Q0.50 a 250 m. Reserva en L/m² = C × SMI / 100.
No hay previsión de lluvia en estas curvas: son días completos hasta el corte.

## Comprobaciones de esta revisión

56 pruebas dirigidas correctas (hidrología, meteorología, contratos científicos
y runtime), más la prueba de navegador. Cobertura numérica: ejemplo publicado FAO (ET₀ 3,88 mm/día), respuesta
al viento/humedad, conservación de masa, solución analítica frente a integración
numérica independiente, huecos y convergencia. Igualdad de los valores comunes
al cambiar entre las cuatro ventanas; lluvia de 50 mm ocho días antes conservada
al visualizar siete días. Comparación del depósito simple con su función
operativa original. Suite de runtime del mapa y navegador de escritorio/móvil,
con colores distintos, leyendas, tooltips y cabecera sin desbordamiento.

Consultas completas con datos de HA local, generación meteorológica
`20260918T215356489746Z-e8b02c29756f`, corte 18/09/2026. Se verificaron capacidad,
lluvia IDW, temperatura corregida por altitud y SMI simple mediante recálculo
independiente en 60 fechas de cada punto; error de SMI <0,0005 puntos por redondeo.

| Punto | Capacidad L/m² | Depósito simple, 18/09 | Extracción regulada, 18/09 |
|---|---:|---:|---:|
| Capolat 42.07612, 1.75017 | 47,10 | 0 % | 18,919 % |
| Gósol 42.25138, 1.66155 | 47,70 | 0 % | 13,135 % |
| Urús 42.31870, 1.85001 | 38,05 | 0 % | 13,187 % |
| Saldes 42.19974, 1.76672 | 42,20 | 0 % | 19,098 % |

Saldes 04/09: ET₀ Hargreaves 4,3106 mm/día frente a PM 3,9983 mm/día,
con viento de Cadí Nord a 11,17 km y 2143 m. **No es la evaporación real de esa
ladera norte.** Este resultado no justifica corregir automáticamente por orientación.

Las cuatro respuestas meteorológicas ocupan unos 13 KB; las consultas completas
29–31 KB. La operación publica como máximo 60 valores por serie, reutiliza la
lectura IDW y mantiene el límite meteorológico de 32 KiB. Las verificaciones se
hicieron en Docker del Mac, no son un benchmark en la Raspberry Pi.

No hubo entrenamiento ni precálculo. Se retiró la imagen aislada de worker de
esta revisión a petición del usuario; no se inició su contenedor. La validación
se limita a HA local. Para una futura release sigue pendiente la paridad con el
worker dentro del circuito autorizado.

Mapa local: <http://127.0.0.1:8101/protected/prediction-map/index.html>.
Elegir **Servidor local** para comprobar esta revisión.
