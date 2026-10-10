# Estado del estudio del umbral favorable

Actualización: 03/10/2026. **Primera comparación completada.**

Resultado: [informe final](resultados-2026-10-03.md),
[tablas](tablas-2026-10-03.md) y [reproducción](reproducibilidad.md).
No se recomienda activar B con esta evidencia. No se han promovido artefactos.

Carpeta renombrada de `prediction/` a `prediction-thresholds/` el 03/10/2026 a
petición del usuario. Documentación original preservada antes del cambio; scripts
y evidencia privada conservan sus rutas. El [estudio del ganador](../prediction-model-selection/README.md)
es otro encargo, preparado y revisado por un agente diferente; aún sin cálculos.

- **Autorizado:** el usuario solicitó documentar y lanzar el agente con el goal y
  las reglas de [goal.md](goal.md), incluidos experimentos locales acotados.
- **Activación:** goal creado el 03/10/2026 mediante `create_goal`, sin
  presupuesto de tokens solicitado. Agente principal responsable: esta conversación.
- **Completado:** protocolo general, inventario preliminar y aclaraciones de GBIF
  `normal` y fecha del entrenamiento operativo. Ver [inventario](inventario-inicial-2026-10-03.md).
- **Cohorte congelada:** 499 observaciones elegibles del ámbito compartido; 184 de
  las dos especies objetivo. Tres cortes externos 2024/25/26, con 116 observaciones
  externas distintas. Manifiesto privado `tmp/prediction-research/cohort-v2.json`.
  La revisión v2 cierra también el año externo sin partir grupos; no cambia los
  recuentos objetivo ni las filas. Se conserva el primer manifiesto.
- **Protocolo cerrado:** [ejecución](protocolo-ejecucion-2026-10-03.md), con ventanas
  separadas para ajuste, ranking, umbral y externo; mínimos y regla B fijados.
- **Auditoría del selector completada:** se necesita resolver siete targets por
  emisión; los siete horizontes de una observación no equivalen a una semana.
  Política local `shadow`; conservarla. Se ha localizado una vía de lectura GIS
  y meteorológica con los intérpretes ya existentes, sin instalar dependencias.
- **Auditorías delegadas terminadas:** `prediction_method_audit` revisó el selector,
  lectores y arnés en lectura. Confirmó que un manifiesto privado mínimo y bundles
  experimentales permiten usar `compare_prepared` y `resolve_species_week` originales
  sin instalar generaciones ni alterar el registry operativo. Sin ajustes delegados.
- **Preparación:** el primer lote terminó V3/V4 y fue detenido por el supervisor
  al superar 4 GiB en V5 (240,3 s; máximo observado 4.422.696.960 bytes). Se conservan
  sus salidas parciales. El usuario autorizó después **8 GiB por proceso**; límite
  actualizado en supervisor y goal. En ese momento aún no se habían ajustado modelos.
- **Corrección de aislamiento:** el lector genérico creaba un lease temporal junto
  al histórico y lo retiraba al cerrar. No alteraba registros meteorológicos, pero
  violaba el objetivo de no escribir allí. Se ha añadido un adaptador experimental
  que fija la generación sin leases, comprueba hashes y bloquea escrituras Python
  fuera del estudio. Su comprobación real pasó: hashes meteorológicos verificados,
  mismos metadatos de locks/leases y escritura ajena rechazada. También se limita Arrow.
- **Variables completadas:** bases V3/V4 y V5 windowed listas. Lote windowed:
  160,87 s, máximo RSS observado 2.743.468.032 bytes (2,55 GiB). Conserva calentamiento
  físico de 365 días; retiene exactamente variables instaladas 30/60/90.
- **Geografía de evaluación lista:** 128 puntos leídos por el adaptador completo,
  `geography_ready=true`; 123 devolvieron contexto de suelo. Esto no implica que
  todas las especies sean territorialmente compatibles. 14,21 s; 295.288.832 bytes RSS.
- **Entradas por perfil listas:** 22 benchmarks (11 perfiles × fijo/lag), con
  manifiesto y cobertura. Aereus: las 86 observaciones elegibles en todos; caesarea:
  98 en todos salvo V3 físico, 94 (cuatro favorables excluidos por ese contrato).
  Mantener los filtros y comparabilidad del catálogo, sin ocultar la diferencia.
- **Verificación:** once pruebas sintéticas de separación, proyección, selección
  de umbral, protección de destino, denominadores y bootstrap pareado por grupos
  pasan. Prueba mínima del supervisor completada tras autorización para consultar
  memoria de procesos fuera del sandbox. Registros privados en `runs/`.
- **Primer corte:** ranking 2024 completado (168/168 ajustes; 23,15 s),
  reajuste para desarrollo completado (168/168; 15,97 s) y evaluación semanal de
  desarrollo completada (12 observaciones, 84 emisiones; 48,12 s).
- **Umbral 2024 cerrado antes de externos:** 0,60 para ambas especies por soporte
  insuficiente en desarrollo (aereus 5 positivos/3 negativos; caesarea 3/1).
  Es la regla prefijada, no una conclusión de precisión ni una mejora. Elección y
  curva privadas en `fold-2024/threshold-choice.json`; cada observación conserva
  sus siete emisiones y la traza de semana completa, sin etiquetas inventadas.
- **Externo 2024 terminado:** 37 observaciones, 259 emisiones; evaluación de 166,75 s,
  máximo RSS observado 356.646.912 bytes. Modelos finales: 168/168.
- **2025 completado:** 49 externos, 343 emisiones; B=0,75 para aereus y 0,60
  para caesarea. En externo, la variante de aereus retira ocho falsos favorables y
  28 verdaderos favorables (emisiones, no salidas independientes), sin mejorar precisión.
- **2026 completado:** 30 externos, 210 emisiones; B=0,60 para ambas especies,
  por ausencia de mejora estricta admisible en desarrollo.
- **Total:** 1.512/1.512 ajustes; 116 observaciones externas, 812 emisiones;
  2.000 remuestreos por grupos/corte. El análisis comprueba fuentes y umbrales
  previos al reajuste externo. Se conservaron versiones anteriores del evaluador;
  la fuente inicial del entrenador fue recuperada exactamente contra su hash sellado.
- **Hallazgo:** abstención completa en aereus2024 y caesarea2025, explicada por
  evidencia insuficiente de ranking y filtros territoriales/estacionales; no por
  modelos ausentes. Esto corresponde al experimento, no acredita el comportamiento
  del artefacto instalado. Detalle y límites en el informe.
- **Recursos:** unos 19,7 minutos de lotes supervisados, incluidos fallos;
  aproximadamente 1,23 GB privados. Tras ampliar a 8 GiB, máximo RSS observado
  2.743.468.032 bytes. Fuente exacta: `tmp/prediction-research/runs/`.
- **Siguiente paso propuesto:** investigar estabilidad/cobertura del ranking y
  recoger validación prospectiva bajo un encargo nuevo. No ejecutar más experimentos
  ni trabajos operativos automáticamente por estas propuestas. Conservar el estudio.

No se han modificado datos originales, modelos activos, HA real ni worker.
