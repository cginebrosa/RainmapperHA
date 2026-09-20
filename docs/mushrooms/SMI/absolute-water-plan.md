# Cantidades absolutas · propuesta tras aceptar el SMI de referencia

20/09/2026. El usuario acepta regulada + ET nueva + una capa 0–30 cm. Quiere
mejorar la proximidad a observaciones reales, no mantener investigación sin una
decisión operativa. No está dispuesto a instalar o medir evapotranspiración.

## Separar tres comprobaciones

1. **Cambios de reserva en L/m²:** reconstruir un perfil volumétrico 0–30 cm
   desde sondas y metadatos de profundidad/instalación. Estimar la integral por
   espesor y su sensibilidad a la interpolación. Una variación media de 0,03
   m³/m³ en 0,30 m equivale a 9 L/m²: ejemplo aritmético, no resultado observado.
   Esto permite evaluar magnitud de recargas y pérdidas, no solo correlación,
   sin necesitar aún fijar el nivel de agua no disponible. Una sonda a 20 cm
   por sí sola no mide esa integral. No imponer pesos iguales a las sondas.
2. **Capacidad disponible:** contrastar SoilGrids con FC/WP y profundidad real
   de suelo por horizonte donde exista información independiente. Capacidad
   disponible = integral de FC−WP; no es agua total ni saturación.
3. **Reserva disponible absoluta:** integrar humedad observada menos WP y
   comparar con el modelo en L/m²; convertir a porcentaje usando FC−WP.
   Mantener también los valores observados sin recortar para no ocultar agua
   transitoria sobre FC o anomalías. Si faltan umbrales medidos, presentar rango
   condicionado y separar validación independiente de comprobación con estimaciones.

No cambiar otra vez de familia de modelo durante estas comprobaciones. Mantener
IDW como entrada principal. El pluviómetro sigue siendo diagnóstico secundario.

## Evidencia ya revisada para evaluar viabilidad

En `baseline-2026-09-19/station-metadata.json`, las fichas archivadas incluyen
encabezados de humedad **gravimétrica** a −33 y −1500 kPa. No se han confirmado
visualmente todas las cifras ni la cobertura completa por horizonte.

Se volvió a inspeccionar visualmente la copia de ficha de Batlliu: valores 28 y
16% gravimétricos para 0–12 cm; horizonte C 12–25 sin esos valores y R desde
25 cm. No extrapolar esos dos números a los 30 cm ni convertirlos directamente
a m³/m³. Se requiere densidad aparente apropiada y coherencia de fracción de
tierra fina/piedras; también confirmar representatividad respecto a las sondas.

No se localizó densidad en el texto de las 22 fichas archivadas; el OCR no prueba
ausencia en todas las fuentes. Queda por comprobar si ICGC publica análisis más
completos, calibración instrumental y metadatos de instalación. No escribir a
terceros sin autorización explícita.

## Resultado que debería producir el próximo ensayo

- Inventario de estaciones con datos suficientes para cambios de almacenamiento,
  capacidad y reserva absoluta; no exigir las 22 si faltan referencias fiables.
- Sesgo (sobrestima/subestima) y error absoluto en L/m², por estación y por episodio;
  separar incertidumbre de integración vertical, calibración y umbrales del suelo.
- Comparación de la capacidad del mapa con la independiente donde sea posible.
- No definir mínimo observado=0% ni máximo observado=100%: sesgaría la validación
  y ambos extremos dependen del periodo. Tampoco usar exclusivamente SoilGrids
  para construir la referencia y luego declararlo validado contra ella.
- Si hace falta calibrar, reservar otro periodo o grupo de estaciones **antes**
  de ajustar y comprobar después la mejora allí. Solo trasladar a operación lo
  que pueda calcularse con la información disponible en puntos arbitrarios.

Fuentes primarias metodológicas:
[FAO-56, capítulo 8, ecuación 82](https://www.fao.org/4/x0490e/x0490e0e.htm),
[FAO, mediciones de humedad y agua expresada como profundidad](https://www.fao.org/4/t0231e/t0231e05.htm),
[ficha ICGC de Batlliu](https://datacloud.icgc.cat/datacloud/descarregues-web/bd/sols/xms_cat_BDS.pdf).

Actualización 20/09/2026: [SMI-06](storage-2026-09-20/README.md) ejecuta la
comparación condicionada de cambios en litros con cuatro candidatos, integración
vertical y horarios alternativos. La validación independiente de capacidad y
litros disponibles absolutos sigue pendiente. No se han modificado HA real,
worker ni código del cálculo operativo.
