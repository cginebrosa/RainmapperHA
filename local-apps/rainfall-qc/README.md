# Ensayo local de calidad espacial de lluvia

Herramientas de diagnóstico; no forman parte del runner, predictor o worker.
Datos y resultados en `docker-data`. No modificar el histórico original para
hacer consensuar las estaciones. No activar políticas operativas desde aquí.

## Plan

1. **Datos actuales y trazabilidad.** Sincronizar la generación activa de HA a
   `docker-data/Data/weather-history`, reutilizando particiones locales con el
   mismo SHA. Publicar el CURRENT local sólo después de comprobar los archivos.
   Leer HA únicamente; conservar las exclusiones vigentes de estaciones WU para
   el ensayo. Los archivos antiguos del almacén local no se purgan automáticamente.
2. **Piloto reproducible.** Comparar IDW actual, peso reducido para ceros
   sospechosos, peso reducido para valores altos con persistencia y exclusión
   completa de ceros sospechosos. Conservar originales; reglas experimentales
   explícitas, sin ajuste de parámetros para mejorar resultados retrospectivos.
3. **Validación de utilidad.** Estaciones oficiales apartadas de la estimación,
   sin usarlas tampoco en el consenso. Excluir su grupo de coordenadas casi
   coincidentes. Desglosar días secos, húmedos y lluvia intensa, años, estaciones,
   error diario y semanal, sesgo, pérdida de cobertura y cambios contraproducentes.
   Los registros oficiales son referencias, no verdad certificada individualmente.
4. **Ensayo de fallos y casos verificados.** Futura ampliación: ceros artificiales,
   lectura bloqueada, valores multiplicados, períodos incompletos y tormentas
   localizadas. Comparar detección del fallo y daño introducido en lecturas sanas.
   Incorporar cobertura subdiaria real en los episodios donde se pueda recuperar.
   Reservar estaciones/episodios no usados para ajustar reglas antes de aceptar
   una política. No elegir umbrales sobre el mismo conjunto que prueba su mejora.
5. **Decisión.** Mantener el método actual si no hay ganancia consistente. Sólo
   después de evidencia suficiente plantear integración versionada común a
   entrenamiento e inferencia, con auditoría y coste acotado. Los trabajos
   operativos los lanza el usuario; este laboratorio no los ejecuta.

## Ejecución

Sincronización autorizada de meteorología (escribe sólo en el destino local):

```sh
.venv/bin/python local-apps/rainfall-qc/copy_snapshot.py \
  --source /Volumes/share/rainmapper/Data/weather-history \
  --target docker-data/Data/weather-history
```

`docker-data/diagnostics/rainfall-qc/stations.txt` es la copia de las exclusiones
de WU usada en el ensayo; no contiene configuración de coordinadores. Se tomó
de `/Volumes/share/rainmapper/stations.txt` el 26/09/2026.

```sh
.venv/bin/python local-apps/rainfall-qc/run_pilot.py
```

El piloto lee la generación apuntada por CURRENT y verifica los SHA de las
particiones utilizadas. Emplea observaciones desde 01/01/2024 a 25/09/2026;
los días finales de 2023 sólo permiten aplicar las reglas temporales iniciales.
Las salidas se reemplazan en el mismo directorio, no se acumula una copia de
datos por ejecución: `docker-data/diagnostics/rainfall-qc/pilot/`.

## Reglas de la primera variante, pendientes de validar

- IDW base: contrato canónico, radio 15 km, potencia 2, distancia mínima 100 m,
  saneamiento y regla vigente de positivos consecutivos repetidos → cero.
- Vecinas de control: hasta 5 km y 300 m de diferencia de altitud.
- Agrupar posiciones a menos de 250 m como aproximación conservadora a posibles
  sensores duplicados; no supone demostrar que realmente sean el mismo sensor.
- Exigir al menos tres grupos con datos y dos redes representadas. La estación
  que se evalúa y su grupo quedan fuera de sus vecinas de control.
- Cero sospechoso: valor ≤0,2 mm, al menos 80 % de grupos vecinos con ≥5 mm y
  mediana vecina ≥10 mm. Peso experimental 0,25, o cero en la variante de descarte.
- Alto sospechoso: valor ≥20 mm y >4 veces máximo(mediana vecina,1), mediana
  vecina ≤1 mm, y condición repetida en al menos uno de los dos días anteriores.
  Peso experimental 0,25. No usar días futuros.
- Sin apoyo suficiente: peso original; no producir consenso artificial.

Son parámetros de exploración, no umbrales meteorológicos certificados.
No se modela aún exposición orográfica, radar ni el estado instrumental de cada
sensor. La disponibilidad subdiaria no existe en el histórico diario para poder
aplicarla a todo el conjunto. Tampoco se han deducido ceros a partir de ausencias.

## Resultado inicial, 26/09/2026

Generación real copiada a local `20260926T204049825478Z-635f090343b7`:
46 particiones, 5.550.605 registros; 6.642.355 bytes transferidos y 46.019.469
reutilizados localmente (incluye catálogo). Se eliminó la copia temporal creada
antes de que el usuario indicara usar directamente `docker-data`.

Selección final: 24 referencias (12 Meteocat y 12 AEMET), 23.631 jornadas y
3.331 bloques completos de siete días. Ocho Meteocat son casos ya investigados;
el resto se elige con semilla fija y requisitos de disponibilidad, por lo que
esto no es una evaluación ciega de una política definitiva.
48 comprobaciones coinciden con la función canónica de IDW (tolerancia 1e-10).

| Variante | MAE diario (mm) | MAE semanal (mm) | Jornadas modificadas |
| --- | ---: | ---: | ---: |
| Actual | 1,091417 | 4,274069 | 0 |
| Reducir peso de ceros sospechosos | 1,091530 | 4,274402 | 63 |
| Añadir filtro de altos persistentes | 1,091530 | 4,274402 | 63 |
| Descartar ceros sospechosos | 1,091566 | 4,274608 | 63 |

No hay mejora global en este piloto. La reducción de peso mejora >1 mm una
jornada y empeora >1 mm otra; el descarte mejora dos y empeora tres. No se
detectaron altos que cumplieran la persistencia exigida, por lo que esa variante
no queda evaluada efectivamente. 75 estaciones/fechas distintas reciben alguna
marca según la referencia excluida. Las marcas son sospechas, no errores probados.

Sólo 44.599 de 210.287 contribuciones estación/día evaluadas tienen suficientes
vecinas para aplicar consenso; hay apoyo para al menos alguna estación en 5.314
de las 23.631 jornadas de referencia. La baja cobertura explica parte del pequeño
efecto. No demuestra que todo control espacial sea inútil ni que las estaciones
sin apoyo sean correctas. Quitar requisitos para aumentar cobertura requerirá
nueva validación, no se hace automáticamente buscando mejores métricas.

Tiempo del cálculo observado: 2,352 s en este Mac; no extrapolar a Raspberry Pi.
Resultados comprimidos y resúmenes: aproximadamente 314 kB. Sin entrenamientos,
precálculos, reinicios ni escrituras en HA. Recomendación: mantener operativo el
IDW actual y ampliar primero los casos con calidad de referencia comprobada.
