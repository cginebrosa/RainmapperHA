# SMI-03 · Referencia multicentro y separación de factores

Protocolo escrito antes de calcular las métricas ampliadas, 19/09/2026.

Objetivo: comprobar si la ventaja del depósito regulado persiste fuera de las dos
estaciones iniciales y distinguir el efecto de ET₀ y de la lluvia de entrada.
No se ajusta ningún parámetro ni se implementa el modelo de dos capas en este ensayo.

## Muestra y entradas

- Las 22 estaciones del inventario ICGC, sin selección por resultado del modelo.
- Coordenadas UTM de fichas oficiales, transformadas con PROJ y contrastadas con
  las geometrías del visor. Conservar las dos fuentes y distancias, no sus X/Y
  duplicadas. La lectura OCR exige comprobación cruzada. Si difieren más de 100 m,
  revisar visualmente antes de usar ese punto.
- Las fichas describen el perfil; la red se describe como emplazamientos en viñedos:
  https://www.icgc.cat/es/node/23771. No presentar este conjunto como validación de
  bosques ni asumir que no exista riego en cada emplazamiento.
- Entradas locales de 365 días hasta 18/09/2026; evaluación de los últimos 60.
  Capacidad del mapa 0–30 cm y altitud DEM en cada coordenada. Guardar entradas
  completas y huellas del código ejecutado; no reconstruir imágenes ni tocar el worker.

## Comparaciones sin ajustar

1. Depósito simple + Hargreaves (referencia anterior).
2. Depósito simple + ET₀ nueva.
3. Extracción regulada + Hargreaves.
4. Extracción regulada + ET₀ nueva (referencia actual del mapa).

Mantener parámetros del código actual y registrar su conservación de masa.
La comparación de reglas también incluye su diferente orden de drenaje/extracción;
no atribuir toda diferencia exclusivamente a la regulación del estrés.

Repetir las cuatro combinaciones sustituyendo exclusivamente la lluvia de los 60
días de evaluación por el pluviómetro, cuando todos esos días tengan 48 intervalos
válidos y únicos. La historia previa permanece IDW: es una prueba controlada de
sensibilidad a la entrada reciente, no una reconstrucción anual con lluvia medida.
No completar huecos del pluviómetro con ceros ni estimaciones silenciosas.

Ejecutar cada depósito desde extremos seco y lleno; no reiniciar al inicio de la
ventana visual. Si hay un hueco en meteorología, reiniciar incertidumbre, no asumir
que la reserva es cero. Publicar valor solo tras 90 días continuos y diferencia
entre extremos ≤max(1 mm, 1% de capacidad), como en la referencia existente.

## Observaciones y criterios

- VWC positivo y ≤1 m³/m³, al menos 44 medidas válidas por día, sin timestamps
  duplicados. Los ceros se conservan en evidencia pero no se aceptan como medidas
  fiables sin revisar el instrumento. No aplicar un filtro de saltos elegido para
  mejorar las correlaciones; registrar anomalías para revisión.
- Sondas a 5 y 20 cm como referencias principales, 50 cm como contexto.
- Correlaciones Pearson y Spearman, cambios diarios y dos mitades temporales.
  Calcular con al menos 30 pares diarios; comparar modelos en fechas comunes.
  No usar desfases elegidos a posteriori para mejorar el resultado.
- Comparar forma y cronología, no error absoluto entre SMI y m³/m³. No equiparar
  una sonda puntual al depósito integrado ni r a porcentaje de acierto.
- Conservar resultados individuales, mediana entre estaciones y casos adversos.
  Las estaciones cercanas no son réplicas completamente independientes.

## Decisión al terminar

Determinar qué limitaciones dominan y si se justifica pasar al prototipo multicapa.
No cambiar modelos operativos basándose solo en esta muestra. Esta es una auditoría
exploratoria de modelos fijados: cualquier ajuste posterior requiere un conjunto
nuevo/reservado de evaluación; estas estaciones no podrán llamarse prueba ciega.
