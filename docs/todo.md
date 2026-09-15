# TODO

Prioridades al cierre del **15/09/2026**. Arranque suficiente:
`codex-start-here.md` + `active-context.md`. Esta lista amplía tareas;
[especificación central](mushrooms/prediction-map-specification-es.md) = diseño.

## P0 — Mapa de predicción: cerrar aceptación local y concretar integración

### Consolidación geográfica solicitada — revisión del 15/09

- [x] Inventariar las tres carpetas de HA y cruzar manifiestos/cachés del worker
  sin rehashear GiB. Duplicación worker 5,54 GB; ahorro potencial HA 5,74 GB, con
  límites de evidencia explícitos. [Diseño](mushrooms/shared-geography-consolidation-es.md).
- [x] Implementar almacén geográfico público común por SHA y vistas por consumidor;
  reutilizar el dataset GIS de reconstrucción y la publicación del mapa. Adaptar
  hashes/recibos, lectores sensibles a rutas/mtime y transporte incremental fuera
  del clic. Mantener autoridad HA, permisos por coordinador y contextos científicos.
- [x] Adopción y limpieza local: paridad GIS/mapa, circuito científico completo,
  imágenes finales verificadas y reinicio sin transporte/hash. Worker libera
  5,46 GB; versiones/punteros preservados.
  [Informe](reports/shared-geography-acceptance-2026-09-15.json).
- [x] Copiar y verificar en HA real el mapa y solo el delta GIS faltante, sin
  mover/borrar originales ni activar código. Entradas bajo `geography/imports`.
- [x] Sustituir la adopción al primer arranque por archivos ordinarios y manifiestos
  portables preparados previamente. Validado localmente sin red y media read-only.
- [x] Colocar y verificar las copias en las rutas definitivas de HA real.
  Originales conservados; sin comandos ni enlaces al instalar.
  [Informe portable](reports/shared-geography-portable-2026-09-15.json).
- [ ] Tras actualizar HA real, probar el circuito con sus datos y comprobarlo antes
  de que el usuario retire originales. [Guía](mushrooms/shared-geography-consolidation-es.md).

### Candidata local validada — 15/09

- [x] Aplicado a imágenes y contenedores locales: reconstrucción/entrenamientos
  en background junto al precálculo. Smoke 1565/48; paridad de código 193/101
  archivos HA/worker. HA real antiguo conserva su reparto hasta actualizarlo.
  [Informe y límites](reports/worker-background-chain-2026-09-15.json).

- [x] Aplicar/verificar localmente mapa unificado en URL habitual y permiso
  `can_use_prediction_map` por usuario para cualquier rol; autenticación y
  ajustes del visor compartidos. Reconstruido en ambas imágenes, verificado en
  contenedores y consultas reales con usuario básico; smoke 1552/48 y navegador OK.
- [x] Conectar datos privados del mapa a caché sincronizada del worker y probar
  sin montajes privados compartidos. Validado en imágenes locales, seis consultas
  con paridad exacta. [Evidencia y límites](mushrooms/prediction-map-private-cache-es.md).
- [x] GIS/DEM/OpenLandMap preparados con autoridad en `/media` de HA, publicación
  geográfica versionada y caché incremental del worker sin `/maps`. Transferencia
  real de 14,54 GB; reinicio sin transferencia/rehasheado. Cambios, reanudación y
  limpieza probados. Circuito operativo local completo y seis consultas idénticas;
  smoke 1581/48. [Informe](reports/prediction-map-geography-2026-09-15.json).
- [x] Preparar candidata HA 0.2.304 / worker 1.1.2 y paquete GIS con hashes;
  imágenes locales arm64 y fuentes recuperables en `backups/ha-map-candidate-20260915/`.
- [x] Aceptación del usuario y publicación multiarch HA 0.2.304: tags de versión
  y latest con mismo digest, amd64/arm64 verificados el 16/09/2026.
  [Release](reports/ha-release-0.2.304.json).
- [ ] Instalación y aceptación en HA real por el usuario: usar geografía ya
  preparada, probar permisos de predicción, worker y Safari/iPhone; preservar
  datos privados y originales hasta validar. [Guía vigente](mushrooms/shared-geography-consolidation-es.md).
- [ ] Prueba iPhone: acceso local restringido al visor, o tras aceptación y
  publicación explícita de HA real; no abrir administración local a la Wi‑Fi.

### Completado; no rehacer

- [x] Edición de afinidades: «-» elimina solo su fila; añadir filas en V0/Enriched,
  preservando metadatos y filas ocultas. Pruebas dirigidas y navegador local
  correctos. Recuperados los dos pinos de Fredolic desde backup, sin reponer
  el abeto blanco ni cambiar otros campos. Aplicado a HA local.

- [x] Tooltip inmediato por fecha en gráfica semanal, con todas las especies y
  colores del día, evitando acertar en curvas solapadas. Ratón/teclado y ausencia
  de valores probados; sin nuevas consultas. Aplicado en HA local.
- [x] Colores contrastados asignados solo a especies con curvas calculadas,
  estables durante la semana y compartidos con la lista. Regresión de tres curvas
  próximas entre 21 especies comprobada en navegador; aplicada en HA local.
- [x] Consultas del mapa comparten canal online/foreground con trabajos online;
  background independiente, máximo dos cálculos globales. Ocupado y desconectado
  diferenciados y aviso inicial experimental corregido. Validado/aplicado local.
- [x] Ayuda de suelo/pH en Ecología → Suelos, ES/CA/EN, con explicación de
  afinidades frente a apoyo, admisión condicionada y bloqueo de excepciones.
  [Guía](mushrooms/soil-ph-rule-help-es.md); aplicada y comprobada en HA local.
- [x] Especificación central, dos rutas del mismo MapLibre y extensión opcional.
- [x] Botón diana/dardo bajo IDW, modal cancelable y popup anclado; clic/hover
  sobre estación conserva meteorología. Terreno detallado desplegable.
- [x] Preview local sin autenticación real; ajustes temporales aislados. Grupo
  Predicción local/worker; persistencia con los demás ajustes diseñada/probada.
- [x] Municipio IGN nacional opcional, DEM/pH por ventanas, cubiertas/geología
  ICGC, arbolado MFE Catalunya y nombres/alias del catálogo local conectados.
- [x] Geometrías grandes resueltas mediante auxiliares preparados, sin elevar
  límites ni modificar originales. No reconstruir auxiliares por consulta.
- [x] Meteorología observada hasta 60 días en popup; viento opcional identificado
  de estación. Lecturas residentes y huecos explícitos.
- [x] Ampliación/revisión local de hosts y alias, conservando entradas del usuario;
  115 hosts tras añadir Eucalyptus. Promoción pendiente.
- [x] Revisión de literatura de 21 fichas y segunda pasada. Ventanas amplias
  aplicadas localmente: meses/hosts/hábitats/altitud, manteniendo procedencia.
- [x] `ecology.ph_min/ph_max` en mantenimiento, JSON, importación/guardado y
  validación; 21 rangos provisionales aplicados y revisables.
- [x] Filtro residente de hosts/meses/altitud y pH opcional conectado a preview.
  Padre de género ↔ especie admitido, hermanos específicos no equivalentes.
  Sin hosts, las fichas no ectomicorrícicas pueden entrar por hábitat revisado.
- [x] `PointExecutor`, broker efímero/canal remoto y adaptador semanal
  `resolve_species_week` preparados y probados aisladamente, sin activación remota.
- [x] Adaptadores de retención puntual y preparación hídrica/meteorológica 90/365
  usando rutinas existentes, ya conectados al motor del visor.
- [x] Último filtro v4: 67 pruebas dirigidas, API y Chrome según informe ICGC.
  Validación de esa revisión, no reejecutada durante el cierre documental;
  no equivale a Safari/iPhone ni a paridad de contenedores/release.

### Continuación inmediata, en este orden

- [ ] Tarjeta de worker: mostrar actividad de ambos carriles, para que «En espera»
  del primer plano no oculte precálculo de background en otro coordinador.

Decisión posterior del usuario: revisión visual a fondo/Safari y árboles vecinos
quedan aplazados en este TODO. Incremento autorizado ahora: volumen/configuración
portables y comparación del cálculo en HA local y el worker existente, conservando
sus coordinadores. Sin publicación HA real. La autorización autónoma posterior permitió el circuito
local de entrenamiento/precálculo, ya completado: no repetirlo.

- [x] Revisión ICGC completa: 1.055 códigos revisados, 1.046 con materiales en
  192 reglas compartidas, 14 materiales nuevos; nueve sin equivalencia segura.
  Catálogo/mappings/perfiles locales respaldados. Mezclas preservadas; reconocer
  un depósito no demuestra su composición. GEODE aplazado. Informe
  `prediction-map-icgc-substrates-2026-09-14.json`. No repetir esta revisión.
- [x] OpenLandMap pH España local: nueve TIFF, 368 MiB; media para selección,
  límites informativos y comparación SoilGrids, profundidad solo en Terreno.
  Vecino de pH hasta 1 km con distancia. No repetir descarga.
- [x] Matriz de suelo/pH de 21 fichas; ensayo configurable solo en aereus, máximo
  6,8. Silíceo+solapamiento puede admitir media superior, salvo mezcla con
  carbonatos/yeso; sin nuevos vetos universales ni cambios en otras 20 fichas.
- [x] Bibliografía contrastada: hospedador/suelo, roca vs horizonte superficial,
  lavado/descalcificación y separación entre presencia y fructificación.
  `prediction-map-ecological-factors-literature-es.md` contiene fuentes y propuesta.
- [x] Dos niveles y descarte antes de inferencia implementados; v6 añade temporada
  a la selección de cálculo/visibilidad, conservando el estado territorial separado.
- [x] Hábitats no ectomicorrícicos sin árboles, admitidos por el usuario; hosts
  específicos conservados. Coherencia de instantáneas forestal/ecológica,
  74 pruebas Python y Chrome. UI única Terreno y suelos posibles sin vetos.
- [x] Decisión posterior Rovelló: cuatro filas por ID existente, nombres distintos,
  probabilidades propias y sin grupo derivado. Observaciones intactas; sin modelos
  prestados entre especies. Salmonicolor/quieticolor sigue unido.
- [x] Conectados modelos/evidencia sellada y entradas puntuales al motor Python
  compartido: `PointExecutor` y preview. Sin inferencia en navegador.
- [x] Contrato/UI/broker en modo real, sin IDs demo; lista por probabilidad
  descendente del día, null al final y cero preservado.
- [x] Continuidad semanal, corte común, vetos y fallback probados; materialización
  perezosa equivalente al modo completo. Pruebas dirigidas y Chrome correctos.
- [x] Corregido MFE con geometría candidata inválida: recuperación en memoria
  conservando área, originales y límites; 12 pruebas y tres puntos reales.
- [x] Decisión cerrada tras comparar Olvan: Predictor por área; mapa por especie
  con entradas del punto, incluso dentro de áreas conocidas. No añadir selección
  territorial al mapa ni igualar porcentajes. Implementación actual conservada.
- [x] Retirar meses del filtro de especies posibles (v5 local). Conservar
  fenología en las fichas para el predictor; ajustar contrato/consumidores y textos
  «compatibles para esta fecha». Estado territorial independiente de fecha.
- [x] Decisión posterior v6: fuera de temporada no aparece ni invoca modelos.
  Las visibles muestran principal/secundaria según la ficha. 106 pruebas y Chrome.
- [x] Cabecera Terreno: suelos antes de árboles/hábitats, con etiquetas de mappings.
  Descartadas con nombre y motivos en líneas separadas; Chrome escritorio/móvil.
- [x] Decisión final de suelo/pH: conservar reglas actuales. Rechazada restricción
  adicional por litología; Montclar documentado como contraejemplo, sin editar datos.
- [x] Selección antes del modelo/contexto hídrico y salida temprana sin candidatas.
  Prueba de **cero llamadas al modelo para descartadas**, no solo ocultación UI.
  Compatibles sin modelo al final, null distinto de cero; abstención conservada.
- [x] Primer bloque de reglas explícitas suelo+pH por ficha: aereus,
  edulis, pinophilus y cibarius. Distinguir preferencias/requisitos/tolerancias,
  caliza cartografiada/descalcificación e incertidumbre. No veto universal por
  caliza ni pH inventado desde roca. Cada ajuste con motivo y caso esperado.
- [x] Pruebas funcionales de Vallcebre (fecha), La Selva/L'Aleixar (aereus y silíceo), La Vansa
  (caliza+pH ácido estimado), Olvan/Merlès y regresión forestal de Fogars.
  Motivos de exclusión/admisión condicionada visibles sin alterar porcentajes.
  Nueve puntos con lectores reales × enero/septiembre y API La Vansa; ver informe v5.
- [ ] Concretar recuperación forestal vecina solicitada, con criterio/radio y
  distancia/procedencia. **Aún no implementada**; el vecino de pH no la sustituye.
- [ ] Revisar contradicciones de vinosus y completar reglas del resto de fichas
  después de validar el primer bloque; conservar la ficha conjunta de Rovelló.
  Revisión pendiente, no autorización para reabrir ahora suelo/pH ni endurecer vetos.
- [ ] Validar porcentajes y compatibilidad frente a setales conocidos con las
  fichas actuales. No confundir validación funcional con transferencia científica.
- [x] Comparación del cálculo completo en HA local y worker existente: resultados,
  generaciones, primera consulta/repetición, concurrencia, tiempos totales/cálculo
  y memoria cgroup registrados. No extrapolar tiempos del Mac a RPi4.
- [ ] Ampliar mediciones representativas de cola/transporte/render, RAM incremental
  e IO físico en destino. No usar tiempos del lector como benchmark de predicción.

Incidencia anterior del runner: Barcelona corregida en catálogo local/HA real,
con backups y mediciones conservados. Regla de saltos con destino en España
aproximada (incluidas islas) implementada, sin desplegar código ni relanzar runner.
Erinya espera corrección de la fuente por decisión del usuario.
Ver `reports/weather-coordinate-conflict-2026-09-13.json`.


## P1 — Integración operativa del mapa, posterior al cálculo local

- [x] Consolidar cambios puntuales en imágenes reproducibles HA local/worker,
  recrear y verificar código efectivo, preservar datos/coordinadores y respaldar
  source/configuración. Completado 15/09; 1.551 tests (48 omitidos), navegador y
  paridad real. No equivale a release HA real ni a validación científica.
- [x] Corregir el desfase de medianoche y exponer zona horaria en Parámetros →
  Predicción, con ayuda ES/CA/EN, persistencia por dispositivo y transporte
  explícito HA–worker. Fecha inicial independiente del navegador; zona en cabecera.

- [x] Nombres forestales por idioma en el mapa: `ForestReader` entrega ES/CA/EN
  desde el catálogo local (115 hospedadores completos). Selector comprobado en
  navegador sin nuevas consultas; trece pruebas GDAL correctas. Aplicado en HA
  local/worker, coordinadores conservados; incorporado a ambas imágenes el 15/09.
  Los nombres de especies siguen las ediciones de sus fichas.
- [x] Exponer los siete campos de la regla conjunta suelo/pH en Ecología → Suelos
  (V0/Enriched) y nombre específico del mapa en Metadatos. Validación de guardado
  con catálogos locales, sin modificar los valores actuales. Pruebas dirigidas y
  controles de HA local comprobados en navegador escritorio/móvil, 14/09.
- [x] Volumen portable de lectores actuales, configuración y canal remoto activados
  en HA local y worker existente. Paridad de dos puntos, repetición/concurrencia,
  cancelación y worker desconectado sin fallback; URLs conservadas por hash.
  [Informe](reports/prediction-map-local-worker-integration-2026-09-14.json).
- [ ] Completar paquete **nacional**: integrar GEODE y MFE fuera de Catalunya,
  usando las descargas existentes. 14,54 GB actuales no son España completa;
  no recortar territorio. Índices/normalización y mappings aún necesarios.
- [x] Autenticación real y preferencias con los demás ajustes de dispositivo;
  retirar adaptación de preview al integrarla. Permisos UI/API y revocación.
- [x] Conectar mapa del worker a las generaciones privadas de su asociación,
  reutilizando sincronización y caché existentes. Probado con HA local sin
  montajes privados; despliegue RPi4 pendiente. No sustituir sus datos por el Mac.
- [x] Minimizar transporte del mapa: referencias compactas y cero descarga de
  objetos/manifiesto completo en clic con versiones ya verificadas; reutilizar
  meteorología del precálculo y fichas sin cambios. Sincronizar solo archivos o
  particiones ausentes/modificados, incluir catálogos/mappings necesarios y no
  invalidar datos iguales por editar una ficha. Fijar versiones por consulta,
  deduplicar preparación concurrente y preservar autorización por asociación.
  Validar cambio de ficha, meteorología incremental, reinicio y caché caliente;
  medidos bytes de control y objetos aparte. [Contrato y pruebas](mushrooms/prediction-map-private-cache-es.md).
- [ ] Ampliar regresión de estilos/gestos, Safari/iPhone y convivencia con mapa
  meteorológico. No cambiar comportamiento de la ruta meteorológica actual.
- [ ] Antes de integración GIS general, adaptar mantenimiento/consumidores legacy
  al bloque `exact_value_mapping_groups`; el mapa y validador ya lo leen.
- [ ] Promover explícitamente catálogo/fichas/mappings locales al repo y HA cuando
  estén aceptados. Preservar datos originales y ediciones concurrentes.
- [ ] Preparar volumen portable con GIS/DEM/SoilGrids/municipios e índices:
  imagen de arquitectura compatible + datos/manifiesto/instalador, destino limpio,
  reinicios/actualizaciones y coordinador intacto. No reconstruir desde HA real.
  Base actual instalada por enlaces, copia/reanudación probadas con fixtures;
  falta cierre nacional, máquina independiente y AMD64. ARM64 local comprobado.
- [ ] Ampliar normalización MFE25 a otros esquemas/regiones e índice GEODE cuando
  se amplíe ámbito; no bloquear Catalunya por completar todo el país.
- [ ] Auditar escala/incertidumbre útil de estaciones/IDW y transferencia del
  modelo a ubicaciones nuevas, sin prometer precisión meteorológica a metros.
- [x] Decisión RPi4: cálculo del mapa en worker en principio; HA coordina/entrega.
  Sin fallback local. La comparación con HA local comprueba paridad, no decide
  dónde calcular en producción ni extrapola rendimiento a la Raspberry.
- [ ] Solo si se solicita release: reconstrucción HA local/worker del mismo
  código, circuito local aplicable y aceptación expresa antes de HA real.
- [ ] Superficie coloreada por zona visible: ampliación separada a concretar;
  el clic/informe puntual no implica precálculo de todos los puntos de España.

## P2 — SoilGrids y enriquecimiento general, sin desplazar el mapa

- [x] Descargas/auditoría terminadas: 54 retenciones + nueve pH, 7.119 pares
  tesela/capa; huecos aceptados. No repetir sin motivo nuevo.
- [x] Diseño compartido RPi4: índice, ventanas, caché y concurrencia acotadas,
  sin hashes completos/proceso por capa en cada consulta; reparto HA/worker.
- [x] Lectores candidatos puntuales DEM/pH/retención y controles locales;
  esto no completa la migración de agregados/consumidores antiguos.
- [ ] Migración compatible para altas/cambios de áreas/microáreas y consumidores:
  CRS/NoData, ediciones, referencias antiguas y deltas sin perder ediciones.
  No interpretar todo cero de retención como NoData.
- [ ] Preparación remota previa al snapshot, réplicas de datos y aceptación de
  deltas en HA; medir RAM/IO/latencia y agregado de polígonos en RPi4.
- [ ] Concretar enriquecimiento en Setales/observaciones: pH geográfico,
  profundidad/incertidumbre/procedencia y agregación, preservando anotaciones.
  Separar mostrar datos, migrar almacenamiento y cambiar variables de modelos.
- [ ] Cambiar referencias solo tras validación. Caché antigua y backups se
  conservan; 30 días fue propuesta, no permiso de borrado automático.
- [x] 21 rangos de pH provisionales ya aplicados por decisión del usuario.
- [ ] Revisar esos rangos/ventanas ante evidencia nueva sin restaurar versiones
  antiguas ni ampliar globalmente aereus a 7,5, opción rechazada por el usuario.
- [ ] Francia: vegetación/ecología y geología aplazadas; municipios opcionales.
  DEM/SoilGrids comprobados puntualmente no acreditan ecología disponible.
- Referencias: diseño del lector y reparto en `mushrooms/`; detalles/inventarios
  históricos en [snapshot archivado](reports/session-context-before-close-2026-09-13.md).

## Pendientes conservados — Predictor y ciencia, no prioritarios frente al mapa

- [ ] Aplicabilidad multiespecie, caso Rovelló / Els Ports / 2026-09-07:
  diferencia absoluta/normalizada/dirección, sin tolerancia global inventada.
- [ ] Probabilidad vetada solo diagnóstica; distinguir sin modelo de modelo vetado.
- [ ] Catálogo explícito de especies posibles por área.
- [ ] Sustituir Historial por evaluador persistido hold-out; precálculo no incluye history.
- [ ] Mensajes distintos para reentrenamiento, precálculo, cobertura y corrupción.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando hold-outs externos
  tengan ambas clases. Auditoría de días secos cerrada: no cambiar contador/modelos.

## Pendientes conservados — Operación

- [ ] CLI del worker por `coordinator_id`, manteniendo otros destinos.
- [ ] Medir transferencia/hash/escritura/fsync/promoción antes de streaming RPi4.
- [ ] Runner meteorológico externo y AWS/servidor doméstico: futuro, no migrar ahora.
- [ ] GIS/DEM de microáreas francesas desde UI al retomar ese trabajo y Meteo-France
  frente a Wunderground; revalidar versión HA entonces.
- [ ] Confirmar si faltan controles visuales de contadores y runner mensual
  Wunderground; no repetir lo ya acreditado para la misma revisión.
- [x] HA real `0.2.303` confirmado instalado/funcionando por el usuario.
- [x] Selección semanal `lag_event` h1–h7 y fallback diario existentes conservados;
  meteorología observada del Predictor y aviso final del worker corregidos anteriormente.

No se autoriza ningún trabajo, borrado, cambio de coordinador ni publicación
por figurar en esta lista. El próximo bloque autorizado es la implementación local.
