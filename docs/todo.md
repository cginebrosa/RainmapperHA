# TODO

Prioridades vigentes. El estado inmediato y los comandos de continuidad están
en `docs/active-context.md`; este fichero conserva únicamente trabajo abierto y
resultados cerrados que condicionan esas prioridades.

## P0 — Validar y publicar la corrección de regeneración V2–V6

- [x] Identificar el fallo real de HA `0.2.256`: el tercer job dependía de un
  JSON del snapshot de laboratorio ausente en HA.
- [x] Sustituir esa dependencia por entradas V2–V6 derivadas del snapshot fresco
  de cada reconstrucción.
- [x] Añadir identidad `training-input-manifest.json`, validación de hashes y
  aviso de vigencia del Predictor.
- [x] Mantener una sola acción completa: reconstrucción + ML v0 + V2–V6; no
  añadir una regeneración parcial por el fallo puntual.
- [x] Retener resultados fallidos para diagnóstico y borrar staging únicamente
  después de una instalación íntegra.
- [x] Evitar datos reales en las imágenes: plantilla vacía en HA y ausencia de
  observaciones, snapshots, hold-outs, benchmarks y modelos entrenados.
- [x] Retirar el montaje temporal `Validación local`, su contenedor/volumen y
  los puertos 8103/8111 sin modificar el worker M1 normal.
- [x] Recuperar en el HA local de 8101 un ejecutor opt-in que calcula sobre el
  M1 sin emparejar otro worker y reutiliza los contratos del flujo externo.
- [x] Exigir tanto en UI como en backend que reconstrucción, ML v0 y V2–V6
  terminen antes de ofrecer una única promoción completa.
- [x] Construir e inspeccionar de nuevo la imagen HA local con el ejecutor
  completo; confirmar que el HA real continúa coordinador-only por defecto.
- [x] Lanzar desde `http://127.0.0.1:8101/mushrooms/workers` la reconstrucción
  completa con `Home Assistant local` y medir los tres trabajos encadenados.
- [x] Verificar el batch final: manifiesto de entradas, hashes, no operativo,
  staging limpio y ausencia de la antigua ruta de laboratorio.
- [x] Revisar visualmente Predictor/Comparar: aviso de vigencia, V2–V6 con sus
  algoritmos y cautelas, V2 solo cronológica y ninguna pareja especie+área
  incompatible retenida.
- [x] Ejecutar smoke completo y `git diff --check`: 863 pruebas y gates OK.
- [x] Diagnosticar `model_not_trained` en la ventana fija operativa de
  Edulis/Salteguet; no asumir que es el miembro V2 del batch comparativo.
- [x] Reproducir la lluvia IDW de Salteguet del 17/08 con estaciones finitas,
  fuentes habilitadas, radio y umbral de soporte; verificar ceros y `N/A`.
- [ ] Tras cerrar esas anomalías, detenerse e informar y pedir autorización
  explícita. Solo después
  leer `docs/release-flow.md`, verificar/bump de versiones y preparar/publicar.
- [ ] Instalar primero el worker corregido y después HA; solo entonces repetir
  la regeneración completa real y comprobar que el Predictor queda `current`.

## P1 — Mantener la comparación científica, sin promoción prematura

- [x] Comparar V2/V3/V4 sobre filas y meteorología IDW comunes, seis algoritmos
  y particiones 7/14, sin Brier medio entre especies.
- [x] Corregir `lag_event`: un ajuste por especie+contrato+estimador y filtros
  1/2/3/7 sobre el mismo hold-out.
- [x] Conservar predicciones hold-out fila a fila y analizar falsos
  positivos/negativos compartidos por especie, contrato, horizonte, fase y
  meteorología.
- [x] Ejecutar V5 raw regularizada: 12.280 predicciones; 2 victorias y 32
  derrotas de 34 frente al mejor miembro V2/V3/V4.
- [x] Ejecutar V6 suave/jerárquica: 4 victorias y 30 derrotas de 34 frente al
  mejor miembro V2/V3/V4/V5.
- [x] Concluir que los errores actuales no justifican un modelo de estado ni un
  jerárquico general y no muestran dos ventanas meteorológicas estables.
- [ ] Congelar V5/V6 y no añadir otra familia durante el gate de release.
- [ ] Mantener V2–V6 vivas mediante el registro genérico. Ninguna está aceptada,
  promovida o validada como mejor; V2 solo es la primera cronológicamente.
- [ ] No ensayar ensemble salvo que se materialice y supere al mejor miembro
  individual por especie y contrato.

## P1 — Worker multicoordinador

- [x] Documentar la arquitectura y el contrato de revocación en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- [ ] Migrar atómicamente la configuración monocoordinador conservando URL,
  token, identidad, volumen y caché existentes sin exigir pairing nuevo.
- [ ] Añadir el parámetro persistente y configurable `max_coordinators`, default
  4, con rechazo no destructivo tanto al superar el límite como al intentar
  reducirlo por debajo del número de asociaciones con credencial.
- [ ] Mantener heartbeat independiente por coordinador, un solo slot global de
  ejecución y arbitraje round-robin de claims cuando quede libre.
- [ ] Aislar estado y temporales por `(coordinator_id, job_id)` y devolver cada
  progreso, resultado, receipt y limpieza solo al coordinador de origen.
- [ ] Al recibir un `401` inequívoco, eliminar solo esa asociación; conservar
  credenciales ante timeout, DNS, desconexión o `5xx`.
- [ ] Rechazar con `409` la revocación desde un HA que tenga un job suyo activo.
- [ ] Añadir gestión CLI local para listar asociaciones sin secretos y olvidar
  coordinadores inaccesibles; no crear una UI o puerto entrante del worker.
- [ ] Probar dos coordinadores aislados, colisión de `job_id`, caída parcial,
  justicia, reinicio, límite configurable y cadena de tres jobs con una única
  promoción en origen.
- [ ] No instalar, reemparejar ni modificar el worker M1/HA reales durante estas
  pruebas y no mezclar su release con el P0 sin autorización expresa.

## P1 — Nuevas observaciones y repetición futura

- [ ] Cuando la plataforma corregida esté alineada, incorporar las cuatro
  salidas negativas recientes del usuario en cuatro microáreas/especies.
- [ ] Crear un snapshot inmutable nuevo; no sobrescribir
  `mushroom-ml-snapshot-20260816`.
- [ ] Repetir las comparaciones congeladas para medir sensibilidad por especie,
  campaña, contrato y partición antes de decidir cualquier candidatura.
- [ ] Repetir V5/V6 solo con nueva evidencia independiente suficiente; no usar
  el hold-out actual para elegir una familia posterior.

## P2 — Meteorología y Biology V4

- [x] Implementar IDW común, corrección térmica por DEM, balance climático,
  SoilGrids experimental y paridad train/inferencia.
- [x] Concluir que el balance no mejora Brier consistentemente y SoilGrids suele
  empeorar; conservar ambos evaluables pero desactivados.
- [x] Implementar localmente autocuración oficial con cola durable, bloques,
  backoff y reparación primero del histórico particionado.
- [ ] Validar en producción la autocuración y sus avisos Diagnostics/Errors en
  una release coordinada; no mezclar esa conclusión con el gate V2–V6.
- [ ] Corregir el matching geológico por subcadena (`gres`/`negres`) antes de
  usar esos proxies.
- [ ] Completar propiedades/quantiles SoilGrids solo si un experimento futuro
  los necesita.
- [ ] Futuro no prioritario: bootstrap autónomo del histórico en instalaciones
  vírgenes desde la observación más antigua y el lookback requerido.

## P3 — Integridad, privacidad y UX

- [ ] Revisar por separado la privacidad de
  `mushroom-data/mushroom_observations.json`, que sigue rastreado en el
  repositorio público aunque ya no se copie a la imagen HA.
- [ ] Añadir sanity checks confirmables al alta/edición/importación: temporada,
  altitud y primera observación especie-área/microárea.
- [ ] Mostrar advertencias y permitir continuar; nunca corregir, descartar ni
  reclasificar automáticamente una excepción real.
- [ ] Auditar identificaciones automáticas antiguas que pudieran contaminar
  artefactos previos.

## Riesgos que condicionan prioridades

- La instalación real todavía no incorpora la corrección V2–V6. No tratar su
  Predictor como plenamente actualizado.
- El umbral especial de soporte IDW de lluvia puede devolver `null` aun con
  estaciones válidas; falta decidir si es cautela correcta o falso vacío.
- La duración local observada ronda 20 minutos mientras V2–V6 permanezcan
  activas; es coste aceptado, no un motivo para crear un atajo incoherente.
- El soporte por especie y campaña es pequeño; los rankings son diagnósticos.
- Los horizontes lag reutilizan observaciones y no son muestras independientes.
- El worktree es grande y mixto; preservar cambios y PDF no rastreados.
