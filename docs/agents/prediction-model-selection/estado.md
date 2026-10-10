# Estado de la investigación del ganador

Fecha de cierre: 04/10/2026, Europe/Madrid.

**Comparación y análisis completados.** [Informe](resultados-2026-10-04.md) y
[tablas](tablas-2026-10-04.md). Ninguna alternativa supera toda la regla
predefinida. Mantener la referencia por ahora, conservando como hipótesis la
mejora exploratoria de la selección diaria para caesarea. No demuestra que el
procedimiento actual sea óptimo ni que ninguna alternativa aporte ventajas.

- **Autorización:** el usuario confirmó lanzar el nuevo agente de selección.
  Objetivo y límites en [goal.md](goal.md); cierre nativo en el registro de la sesión.
- **Diseño:** A reciente, B dos ventanas, C diario con B; cortes 2024–2026,
  exploratorios. [Protocolo](protocolo-ejecucion-2026-10-04.md) y dos anexos técnicos
  sellados antes de las inferencias a las que afectan. Ningún nuevo entrenamiento.
- **Cálculo:** inventario, tres rankings y tres evaluaciones completos. 116
  observaciones, 812 emisiones por variante; promedio con peso total 1 por visita.
  Análisis con 2.000 réplicas por episodios, matrices, cobertura y estabilidad.
- **Control:** tres catálogos antiguos reproducidos exactamente, 812 emisiones
  de control y 19.514 contratos compartidos B/C sin discrepancias. 35 pruebas
  dirigidas superadas. Auditorías independientes de exclusión, tablas y conclusión.
- **Incidentes conservados:** fallo inicial de observabilidad del supervisor;
  parsing de exclusiones antes de inferir en ranking2025; desacuerdo meteorológico
  B/C antes de la primera fila completa en evaluación2025. C conserva la ruta
  nativa de B cuando ésta ya es diaria; reintento completado. Fuentes exactas
  archivadas, sin repetir 2024 ni atribuirle retroactivamente el código posterior.
- **Hallazgo:** B se abstiene en toda caesarea2025. En 175 emisiones, la familia
  semanal supera Brier pero falla ROC; otras siete tienen huéspedes desconocidos.
  La selección diaria C mejora los aciertos conjuntos de caesarea, con algo más
  de falsos favorables y pérdida de oportunidades en 2026. Es señal exploratoria,
  no una candidata aprobada por la regla fijada.
- **Recursos:** unos 27 minutos de lotes en este estudio y 47 entre ambos,
  de 120 disponibles; pico RSS nuevo muestreado de 786 MB. Artefactos nuevos
  de unos 161 MB, 1,39 GB conjuntos, por debajo de 2 GiB. No son tamaños físicos
  de Finder ni medidas de latencia operativa.
- **Integridad:** `tmp/prediction-model-selection/closure.json` acredita los
  hashes de originales, estudio anterior, entradas, controles, análisis, archivos
  de fuentes y documentación final. El ledger `runs/closure.json` acredita la
  terminación de esa comprobación. No repetir etapas ya cerradas.
- **Protección:** originales y fuentes privadas conservados, sin cambios en
  modelos activos, HA real, worker ni coordinadores. Sin despliegues ni trabajos
  operativos. Un seguimiento prospectivo o una variante nueva será otro encargo.
