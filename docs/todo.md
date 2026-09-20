# TODO — cierre 21/09/2026

Arranque: [codex-start-here](codex-start-here.md) y [active-context](active-context.md).
Esta lista no autoriza trabajos ni publicaciones. Completados anteriores y detalle
histórico: [archivo del cierre](reports/session-context-before-close-2026-09-20.md).

## P0 · Instalación y seguimiento de HA 0.2.316

- [x] Publicar 0.2.316 con GIS/DEM revisable, hosts MFE25 de microáreas y bloques
  plegables en Workers. Tags/digest AMD64/ARM64 verificados.
- [x] Aceptación local: 792 ajustes correctos, precálculo revisión 71 activo,
  siete suspensiones conservadas; smoke final 1704 pruebas/52 omitidas.
- [ ] Usuario instala 0.2.316 cuando termine el entrenamiento real en curso.
- [ ] Revalidar versión e interfaz GIS en HA real y resultados persistidos;
  no repetir entrenamientos para diagnosticar ni lanzar precálculos.

## Seguimiento anterior de HA real 0.2.315

- [x] Publicar 0.2.315, verificar tags/digest AMD64/ARM64 y enviar `6bbd0e8`.
- [x] Usuario confirma instalación («Hecho»). Confirmación comunicada, no inspección remota.
- [ ] Revalidar versión efectiva y estado persistido antes de actuar. El usuario
  confirmó reconstrucción/entrenamiento/precálculo correctos; esa confirmación
  no sustituye una inspección del estado después de trabajos posteriores.
- [ ] Tras los trabajos del usuario, verificar contratos hídricos nuevos,
  generaciones recibidas/promovidas, precálculo recibido/activado y sus hashes;
  conservar las siete suspensiones de rovelló. No copiar resultados de HA local.
- [ ] Confirmar nombre/tooltip del modelo ES/CA/EN y cabecera SMI en mapa real.
- [ ] El usuario lanzará el precálculo. No iniciarlo ni repetir entrenamientos
  caros para diagnóstico o cierre documental.

## Completado · SMI, mapa y migraciones de 0.2.315

- [x] Contrastar 22 estaciones y ocho combinaciones, documentar límites absolutos
  y aceptar extracción regulada + PM + una capa 0–30 cm con meteorología IDW.
- [x] Compartir cálculo entre entrenamiento/precálculo/mapa; conservar simple
  sólo como referencia visual, historial independiente del periodo mostrado.
- [x] Capacidad/disponible en cabecera, SMI antes del balance, Terreno al final,
  leyendas cortas y ayudas separadas traducidas.
- [x] Mostrar modelo elegido por fecha y sus entradas reales, conservando los
  estados sin IFF/sin modelo y evitando cargar artefactos otra vez.
- [x] Migrar hiperparámetros verificados sin reutilizar pesos/métricas y permitir
  avance de solicitud precálculo 1.6→1.7 sin aceptar el resultado antiguo.
- [x] JSON de suspensiones exportable/importable, panel inicialmente cerrado.
- [x] Reconstruir HA local/worker existentes, conservar coordinadores; paridad
  211/114 archivos. Cadena local completa: 714 ajustes correctos, precálculo
  activado revisión 69. Smoke 1690 tests/48 omitidos, UI escritorio/móvil ES/CA/EN.
  [Evidencia](mushrooms/SMI/adoption-2026-09-20/validation.md).
- [x] Documentar adopción, consumidores, experimentos y migración; publicar
  [informe de release](reports/ha-release-0.2.315.json).

## P1 · Calidad predictiva, sin reabrir una investigación indefinida

- [ ] Auditar los tres falsos positivos del 18/09 (Vallcebre ×2 y Bellver/Riu);
  recuperar fecha/esfuerzo de visita y modelo/generación si existen. Capturas y
  coordenadas en [field-feedback](mushrooms/SMI/adoption-2026-09-20/field-feedback.md).
  No atribuir la causa al SMI ni introducir negativos automáticos.
- [ ] Antes de reactivar modelos suspendidos, comprobar sensibilidad a trazas
  de lluvia, independencia de vecinos KNN por observación, calibración y respuesta
  temporal. Versionar cualquier cambio del criterio de día lluvioso/racha seca.
  [Auditoría](reports/rovello-model-sensitivity-expanded-2026-09-19.md).
- [ ] Contrastar IFF en setales conocidos, incertidumbre espacial GIS/IDW y
  transferencia a puntos nuevos. Suavidad/correlación no acredita precisión.
- [ ] Retirar el simple visual cuando lo pida el usuario. No volver a utilizarlo
  como SMI operativo ni incorporar descargas externas a la operación.
- [ ] Revisar litros absolutos sólo ante evidencia útil nueva; la referencia
  orientativa ya está aceptada. No confundir contenido total de sondas con agua
  disponible ni profundidad puntual de 20 cm con toda la capa 0–30 cm.

## P2 · Operación y recursos, sólo cuando se solicite

- [ ] Indicador de worker: revisar estados tras cancelación y refresco, separando
  capacidad global de carriles y trabajos de cada coordinador. Semántica pendiente
  de acordar: usuario apunta a background por coordinador. La propuesta anterior
  «ocupado si cualquier carril» no está aceptada. No cambiar planificación para
  arreglar una tarjeta; pruebas dirigidas de ambos carriles y asociaciones.
- [ ] Medir transporte/hash/escritura/promoción/RAM/IO con artefactos existentes
  y límites RPi4; CLI por asociación/streaming siguen pendientes. No regenerar
  entradas costosas ni elevar límites como solución.
- [ ] Revisar crecimiento de disco con medidas físicas, no tamaños lógicos.
  La publicación ya acota caché Buildx a 8 GiB (capas compartidas aparte) y
  en esta release informó 4,692 GB recuperados. Evitar reinstalar dependencias
  por bumps requiere cambio de empaquetado y validación independiente.
- [ ] Cualquier limpieza adicional exige inventario actual, consumidores y hashes;
  preservar únicos, datos de visores, observaciones, auditorías y backups.
- [x] Duplicados GIS autorizados retirados en la sesión anterior; no repetir.
  [Registro](reports/local-gis-duplicate-cleanup-2026-09-19.json).
- [x] WU/GBIF trasladados a `local-apps`, código separado de datos; entorno antiguo
  de reconstrucción retirado. Datos privados no publicados.
- [ ] Validación geográfica independiente/AMD64 antes de retirar originales
  restantes; no rehacer consolidaciones ya acreditadas.
- [ ] Revalidar incidente meteorológico Barcelona/Erinya antes de actuar:
  [informe histórico](reports/weather-coordinate-conflict-2026-09-13.json).
- [ ] Runner externo/AWS/servidor doméstico y Python 3.14 son futuros, no migrar ahora.

## Pendientes del usuario y aplazamientos explícitos

- [ ] **GBIF:** revisión manual Pendiente/Dudosa/Aceptada/Rechazada; esperar lote
  aprobado antes de importar, entrenar o generar setales. Conservar revisión
  del navegador/JSON y fotografías. [Guía](../local-apps/gbif/docs/guide.md).
- [ ] **WU:** revisar calidad y aprobar candidatas antes de altas/backfill.
  143 nuevas/12 priorizadas fueron recuentos históricos, no estado actual;
  consultar `local-apps/wunderground/data/research.sqlite3`. [Uso](station-research-es.md).
- [ ] **GIS aplazado:** 343 pendientes de la tanda de 488 (331 sin investigación
  específica suficiente, 12 con limitación documentada, no irresolubles).
  Revalidar cola/hashes/fuentes al retomar; 567 aceptados previos no son revisión
  nueva. Conservar `tmp/soil-review-after-0.2.307/`.
  [Método](mushrooms/gis-soil-review-method-es.md), [informe](gis-review-2026-09-16.md).
- [ ] Consumo efectivo de mappings subidos en HA real/worker: paridad almacenada
  histórica no basta; comprobar sin regenerar modelos ni copiar por rutina.

## Producto y ciencia conservados — no ejecutar automáticamente

- [ ] Arbolado vecino: criterio/radio/distancia/procedencia; el vecino pH no lo sustituye.
- [ ] Vinosus y otras fichas: evidencia específica, sin restaurar rangos ni vetos globales.
- [ ] Regresión Safari/iPhone de gestos, estilos y modos; buscador ya aceptado,
  no equivale a validar toda la UI. No exponer administración local a Wi-Fi.
- [ ] GEODE/MFE nacional, esquemas regionales e índices; Francia ecología/geología
  y normalización forestal. DEM/SoilGrids no acreditan cobertura ecológica.
- [ ] Integración geográfica general SoilGrids por áreas, deltas y recursos,
  diferenciada del cálculo hídrico por microárea ya implementado. Separar cambios
  de presentación, almacenamiento y variables; preservar contratos/anotaciones.
- [ ] Revisar rangos provisionales con evidencia: no generalizar aereus a pH 7,5
  ni derivar pH desde litología. Verificar lectores si se amplían grupos de reglas.
- [ ] Superficie coloreada por zona visible: ampliación separada, no calcular
  todos los puntos del territorio por inferencia de la consulta puntual.
- [ ] Aplicabilidad multiespecie (Rovelló/Els Ports/07-09), sin tolerancia global;
  distinguir modelo ausente de modelo vetado.
- [ ] Catálogo de especies por área y evaluador hold-out persistido para Historial;
  distinguir entrenamiento pendiente, precálculo pendiente y corrupción.
- [ ] Auditar Llanega negra/Marçot/Múrgola negra cuando hold-outs tengan ambas clases.
- [ ] Microáreas francesas y Meteo-France frente a WU: bloque separado.
