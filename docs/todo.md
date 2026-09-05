# TODO

Prioridades vivas al cierre del 4 de septiembre de 2026. El estado operativo
breve está en `docs/active-context.md`; las decisiones duraderas, en
`docs/decisions.md`.

## P0 — Auditar el significado científico antes de publicar

Hito concluido para Rovelló, Edulis, Pinícola, Aereus y Ou de reig, con los
ganadores operativos V2--V6 y ambos cortes de grupos, documentado en
`docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
Las pruebas pendientes y la batería Python preparada están inventariadas en
`docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`.
Llanega negra, Marçot y Múrgola negra se aplazan porque sus hold-outs externos
contienen una sola clase; no porque se haya fijado un mínimo arbitrario.

- [x] Trazar las features que consume realmente cada versión y cada candidato
  operativo: lluvia por ventanas/retardos, temperatura, humedad, altitud,
  balance y estado físico para las cinco especies auditables. Documentar
  origen, transformación y uso efectivo.
- [x] Reproducir Rovelló/Riu de Cerdanya y explicar el 100 %: predictor lineal,
  intercepto, variables dominantes, extrapolación, redondeo, calibración y razón
  del fallback global de especie sin evidencia de área.
- [x] Ejecutar ablaciones por grupos de variables y perturbaciones controladas
  usando exactamente los mismos splits `fruiting_groups_14d`; comparar Brier,
  calibración, ROC-AUC y acierto al recomendar salir para los ganadores V2--V6
  de las cinco especies auditables, con el corte de 7 días como estabilidad.
- [x] Auditar probabilidades extremas 0/100 por especie, área, versión y familia.
  No hay saturación general en V2--V6; los errores de unos exactos se concentran
  en KNN V4. Excluir KNN empeora el ganador global, por lo que una eventual
  calibración debe compararse fuera de muestra sin recortar porcentajes de forma
  cosmética.
- [ ] Repetir la evaluación hold-out agrupada cuando entren suficientes
  observaciones nuevas. Incluir Llanega negra, Marçot y Múrgola negra cuando su
  conjunto externo tenga ambas clases. No requiere archivar cada precálculo
  diario ni dirigir las salidas al campo según la predicción.

## P0 — Señal hídrica antecedente

- [ ] Definir el concepto sin asumir causalidad: intervalo exacto, acumulado o
  episodios, umbrales, retardos, cobertura, procedencia meteorológica e
  incertidumbre espacial.
- [ ] Mostrar, si se adopta, la atribución completa: fechas, cantidad, fuente,
  estaciones/celdas contribuyentes y diferencia de predicción al retirar el
  episodio.
- [x] Comparar ventanas candidatas y la interacción lluvia × suelo con los
  mismos grupos hold-out para las cinco especies auditables. La interacción no
  mejora de forma estable; no crear V7 ni modificar V2--V6. No copiar «lluvia
  de activación» de Sporas.io ni usar sus probabilidades como ground truth.
- [x] Mantener `MOD_0001`: los cálculos ecológicos continúan disponibles como
  diagnóstico, pero no vetan ni reetiquetan la predicción mientras no exista
  evidencia para reintroducirlos.

## P0 — Gate de release pendiente

- [ ] Verificar la publicación del SQLite deduplicado en un entorno equivalente
  a HA y evitar falsos fallos del upload: el endpoint publicado mantiene el
  bloqueo durante la validación completa y el intento real con worker `1.0.37`
  abandonó la espera a los 300 s. En HA local el contrato 1.6 publica 29.233.152
  bytes, 420 miembros y cero páginas libres en 8m34s; falta medir transporte y
  activación en la RPi4 para decidir si hay que acotar el bloqueo/streaming.
- [x] Publicar la imagen y el repositorio de HA `0.2.292`. En GHCR, `0.2.292` y
  `latest` comparten el digest
  `sha256:9f1e111f292037f6d0d6a2dafe9d458d6d35dd9549182986ef5edd5a0230f6d1`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- [ ] Instalar HA `0.2.292` en HA real y confirmar desde Diagnostics la versión
  efectivamente arrancada.
- [x] Revisar la coherencia de contratos/manifiestos y ejecutar el smoke de
  release sobre el código definitivo: 1.280 pruebas superadas, metadatos y
  cache-busters alineados y `git diff --check` limpio.
- [x] Reconstruir el worker local privado `1.0.38` y verificarlo healthy, idle y
  con cachés GIS/Predictor válidas. No se publicó una imagen remota del worker.
- [ ] Instalar en el orden correcto: HA compatible, entrenamiento y después
  precálculo. En HA local el Predictor se calcula directamente; el worker no es
  un requisito para ese flujo.
- [ ] Verificar en HA real las tres vistas, tooltips, selector automático,
  `MOD_0001`, cancelación/relanzamiento y reutilización del precálculo. No lanzar
  ni vigilar trabajos sin petición del usuario.

## P1 — Predictor y datos

- [x] Activar la cadena de fallback por aplicabilidad mediante un entrenamiento
  y un precálculo nuevos. El artefacto 1.6 conserva 420 miembros finales y la
  UI sirve Rovelló/La Masella del 8 de septiembre al 99 % sin abstención; la
  desviación de lluvia queda como advertencia, no como veto.
- [x] Auditar por separado la aplicabilidad de las variables de precipitación:
  comparar el límite actual por mínimo/máximo y 3 desviaciones con alternativas
  robustas para una distribución con muchos ceros y episodios intensos
  (`log1p`, cuantiles o distancia específica de cola), usando exactamente los
  mismos grupos hold-out. La variante `log1p` no fue estable; lluvia como aviso
  sin veto aumentó cobertura de forma concordante sin relajar el resto de
  variables. Su implementación operativa sigue pendiente de autorización.
- [x] Implementar y probar la política candidata de lluvia como advertencia sin
  veto propio; se conserva el veto actual para las demás variables. En la
  comprobación directa de Rovelló/La Masella del 8 de septiembre, los `32,14`
  mm quedaron como aviso y el candidato V5w dejó de abstenerse (`99,8511 %`).
- [ ] Crear el catálogo explícito de especies posibles por área. Permitirá usar
  fallback global de especie donde no hay observaciones territoriales sin
  inventar fiabilidad de área.
- [ ] Sustituir el Historial no disponible en HA por el evaluador persistido del
  catálogo hold-out definido en la especificación de fiabilidad.
- [ ] Mejorar los mensajes de incompatibilidad de contratos: distinguir
  claramente `requiere reentrenamiento`, `requiere precálculo` y artefacto
  corrupto o fuera de cobertura.
- [ ] Investigar el SQLite de cero bytes en la raíz del directorio local de
  precálculo y documentar/eliminar su creación solo cuando se conozca su dueño.

## P2 — Rendimiento y observabilidad

- [ ] Medir en condiciones comparables el precálculo deduplicado: tiempo total,
  tiempo por especie/área, lecturas meteorológicas, inferencias y tamaño. Ya se
  verificaron 8m34s, 29.233.152 bytes y 143 payloads físicos; falta explotar la
  telemetría por especie/área y separar lecturas e inferencias.
- [ ] Instrumentar latencia de resultados reutilizados entre ingress,
  transferencia y renderizado del detalle técnico.
- [ ] Continuar la optimización por perfil medido, no por fuerza bruta, según
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.

## Completado en esta sesión

- [x] Selector de fiabilidad `1.2`: área y especie compiten con Wilson inferior
  al 95 %, con empate territorial y selección sellada durante entrenamiento.
- [x] Comparación automática de todas las versiones operativas instaladas;
  retirada de preferida y casillas del flujo Predictor.
- [x] Entrenamiento operativo `local_operational_20260905T194632Z` de cinco
  versiones y 406 observaciones elegibles: 636/636 ajustes y cero fallos.
- [x] Precálculo revisión 39, contrato 1.6, completo e íntegro: 29.233.152 bytes,
  420 miembros finales, 143 payloads físicos, 623 respuestas lógicas y cero
  páginas libres.
- [x] Corrección del ciclo cancelar→relanzar del precálculo.
- [x] Rediseño de la tarjeta resumen, evidencia decisiva, tooltips y badges.
- [x] Propagación transversal de fecha, mm, días y umbral del episodio de lluvia.
- [x] `MOD_0001`: retirada temporal de los vetos ecológicos conservando cálculos,
  trazabilidad, marcadores de código y pruebas.
- [x] Fallback por aplicabilidad activo: cadena fiable sellada en el catálogo,
  selección del primer candidato en dominio y materialización compacta del
  resultado final. Restaurada también la ventana tras lluvia como diagnóstico
  explícitamente no operativo.
- [x] Revisión exploratoria de Sporas.io y documentación de sus límites como
  referencia opaca, incluido el concepto pendiente de señal hídrica antecedente.
- [x] Documentación del filtro Wunderground dirigido y su limpieza posterior en
  la arquitectura y el handoff meteorológico.
