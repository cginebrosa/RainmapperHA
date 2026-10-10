# Inventario revalidado

El lote supervisado `inventory-retry` completó la verificación y guardó
`tmp/prediction-model-selection/inventory.json`. Incluye hashes y tamaños de todos
los archivos del estudio anterior, hashes de originales y protocolo, y recuentos
de las particiones. Las 15 fuentes/pruebas del cierre anterior conservan sus hashes.

Una revisión independiente comprobó los 22 benchmarks y los 168 registros de
ajuste `threshold` por corte: corresponden a `fit+ranking`, sin observaciones ni
episodios compartidos con Y−1, también considerando las otras especies de los
modelos compartidos. Se reutilizan artefactos y entradas; no se copian modelos ni
se entrenan otros.

| Corte | Especie | Ranking antiguo Y−2 (+/−) | Reciente Y−1 (+/−) | Externo (+/−) | Episodios externos |
|---|---|---:|---:|---:|---:|
| 2024 | Aereus | 2/4 | 5/3 | 12/5 | 9 |
| 2024 | Caesarea | 4/4 | 3/1 | 14/6 | 15 |
| 2025 | Aereus | 5/3 | 12/5 | 15/8 | 7 |
| 2025 | Caesarea | 3/1 | 14/6 | 13/13 | 11 |
| 2026 | Aereus | 12/5 | 15/8 | 9/6 | 4 |
| 2026 | Caesarea | 14/6 | 13/13 | 8/7 | 5 |

Recuentos de observaciones objetivo, antes de exclusiones propias del perfil.
Los episodios pueden contener ambas especies. En Y−1 de 2025, V3 físico caesarea
tiene 17 de 20 observaciones por falta de variables físicas en tres casos.
Los 68 casos objetivo anteriores a 2024 siguen interviniendo en desarrollo.

El panel de área nuevo previsto tiene 1.056/3.232/4.312 filas, con todas sus
probabilidades por estimador, para 2024/2025/2026. El externo conserva 116
observaciones y 812 emisiones por método. No es una prueba intacta: sus resultados
anteriores orientaron las hipótesis de este estudio.

## Recursos y primer incidente

El estudio anterior ocupa 1.229.992.044 bytes, incluidos sus documentos archivados
antes del cambio de nombre; acumuló 1.178,965958 segundos supervisados. El equipo
informó 32 GiB RAM, diez CPU lógicas y unos 162,27 GB libres. Se mantiene un solo
cálculo con un hilo y techo de 8 GiB por proceso; no se reserva esa memoria.

El primer intento de inventario se detuvo porque el sandbox denegó `ps`, necesario
para supervisar memoria. Se comprobó que el PID y su grupo ya no existían, se
conservó el fallo y se contabilizó conservadoramente todo el tiempo hasta esa
comprobación, incluida espera sin cálculo. El usuario permitió el supervisor con
acceso a `ps`; el reintento terminó en 1,35 segundos, con pico muestreado de unos
25,7 MB. La comprobación de permisos se trasladó antes de lanzar procesos.

Los ledgers de ambas carpetas mandan sobre estas cifras iniciales. El presupuesto
no se reinicia por crear esta investigación ni por reintentar un lote.
