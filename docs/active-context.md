# Active Context

Ventana operativa de RainmapperHA al cierre del 8 de septiembre de 2026. No es
un histórico. Revalidar siempre repositorio, contenedores, datos y servicios
antes de asumir que este estado sigue vigente.

## Estado comprobado del repositorio

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HEAD y `origin/inicial`:
  `6055dabc72a2ac7837a297f27cf905251d8fe2ae`
  (`Release Rainmapper HA 0.2.297`).
- La fuente declara HA `0.2.297` y worker `1.1.0`; sus secuencias de versión son
  independientes.
- El único cambio previo al cierre era
  `mushroom-data/mushroom_observations.json`, con SHA-256
  `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
  Es dato del usuario: no editarlo, restaurarlo, borrarlo ni incluirlo en un
  commit. Los datos vivos del laboratorio están en `docker-data/`.

## HA 0.2.297

- GHCR `0.2.297` y `latest` se revalidaron al cierre y comparten el índice
  `sha256:07d3eb86efcfc2e6ba2ed02193c19d1503efba021a6256c95b858d71e24fcbfe`.
  Contienen manifests `linux/amd64`
  `sha256:b243a1a8f690dee500fe7f16642f96c2d725c19fc770ffa87f340771c9e08d38`
  y `linux/arm64`
  `sha256:48b6c6b35aa5ae888bb26293722706e28f900db7d755f3eef4d4f8410453ab2f`.
- HA local fue reconstruida y recreada al final desde HEAD. Contenedor e imagen
  efectiva `sha256:f227a9de4095cfcd75779b79b617778b332aa94dd8e8621434e5ae9ade74531f`
  declaran `io.hass.version=0.2.297`; `http://127.0.0.1:8101/` responde 200.
- Se compararon cinco ficheros centrales del gate, runtime, explorador y UI
  dentro del contenedor con el workspace y sus SHA-256 coinciden exactamente.
- No se ha comprobado en esta sesión si HA real ya instaló `0.2.297`. La imagen
  publicada y la paridad local están listas; verificar la versión real antes de
  asumir su instalación.
- La release conserva el último SQLite autocontenido mientras se sustituye el
  runtime meteorológico, resuelve consultas fechadas que cruzan medianoche y
  evita reencolar deseos ya publicados. Las consultas cubiertas leen respuestas
  selladas e indexadas sin revalidación profunda por petición.

## Worker operativo

- `rainmapper-worker` está activo y healthy con la imagen local privada
  `rainmapper-worker:1.1.0`; el worker no se publica en GHCR.
- Imagen efectiva:
  `sha256:5e8c89874f0d355d3a1ab8e997f664dcb40eb7b31b0bd1bf1cc7a4aa638ab38b`.
  Etiqueta, entorno y `/health` declaran `1.1.0`.
- Identidad: `worker_1a9a232c20fe2ee2`, nombre `M1 Personal`. Ambos carriles
  están idle; caché GIS/dataset y caché Predictor figuran válidas.
- Asociaciones persistidas revalidadas sin exponer credenciales:
  - principal: `http://100.111.77.48:8100`;
  - adicional `coordinator_fde2e9b1c6c1f5b2`:
    `http://rainmapper-ha-ui:8100`;
  - límite local: cuatro coordinadores.
- Está prohibido cambiar esas URLs sin autorización expresa para el destino
  concreto. Reconstruir, recrear, reiniciar o probar el worker no autoriza a
  modificar asociaciones.
- El runtime lógico está aislado por coordinador y reutiliza objetos físicos
  comunes por SHA-256. El CLI por `coordinator_id` continúa incompleto.

## Trabajo funcional cerrado

### Modelos constantes

- El entrenamiento calcula degeneración por `split_id`, especie y candidata
  exacta. Con al menos dos resultados y rango de probabilidades
  `<= 0,000001`, marca `constant_prediction=true`.
- La selección sellada excluye esa candidata para toda la especie con
  `constant_species_prediction`; el selector compartido vuelve a comprobar el
  veto, por lo que el precálculo lo hereda sin añadir coste a una consulta.
- No se rechaza un algoritmo por no tener coeficientes. Random Forest, KNN u
  otros siguen siendo aptos si sus predicciones hold-out no son constantes.
- En la generación promovida se comprobaron 2.880 entradas primarias y 3.456
  alternas, con 181 candidatas constantes en cada catálogo. Ninguna de las 280
  selecciones selladas ni de los 420 miembros del precálculo eligió una
  candidata constante.

### Explorador de modelos

- `rainmapper_core/mushroom_model_explorer.py` aporta una aplicación de solo
  lectura montada en `/models` por el servidor HTTP del worker. La instancia
  local responde en `http://127.0.0.1:8110/models`.
- Leer los selectores solo abre catálogo y manifiestos. El artefacto elegido se
  deserializa únicamente al pulsar `Inspeccionar este modelo`, mediante el
  loader que verifica SHA-256 y sin incorporarlo a la caché compartida.
- Muestra estructura real, variables, coeficientes o importancias cuando el
  estimador los expone, rangos de entrenamiento y configuración. Los signos y
  pesos no se presentan como causalidad. Algoritmos sin peso global fijo se
  explican como tales.
- Sigue siendo una aplicación aislable y no existe todavía enlace desde HA.

### Entrenamiento y precálculo validados

- Entrenamiento base: `worker_job_xZdVZ0guMm_7yZB4`, ocho especies.
- Multiversión: `worker_job_OnGu9WeqHDWfV55V`, batch
  `operational_20260908T000329Z`, 636/636 artefactos promovidos.
- Precálculo: `worker_job_dIio5biEkD59`, revisión deseada 43, 420 miembros.
- Artefacto de precálculo:
  `sha256:7d07a53d570a6a9968d22d637d0f5aa2e790aede5f63301eed1bb8586ea338b0`;
  runtime fingerprint:
  `sha256:6289597ea738727f2f2f9b194de43811cfb00383d3870c4de7ebf3be8eca6c46`.
- SQLite: 30.478.336 bytes. Las copias activas comprobadas compartían SHA-256
  `1990c6e20b6c7ef014ed71a7353d6505d0c114007f1c6b5e67252a015d74a4d1`.
- La suite completa anterior a la release pasó 1.331 pruebas en `57,644 s`.
  Después solo se cambiaron documentación y metadatos de versión; no se repitió
  el smoke por no aportar cobertura nueva.

## Próximos pasos, por prioridad

1. Verificar qué versión ejecuta HA real. Si sigue en 0.2.296, instalar 0.2.297
   y comprobar únicamente arranque, versión y lectura del precálculo existente;
   no repetir entrenamiento ni precálculo sin una causa nueva.
2. Auditar de forma multiespecie las abstenciones por aplicabilidad. Separar
   tolerancia absoluta, desviación normalizada, tipo de variable y dirección de
   extrapolación. Caso inicial: Rovelló / Els Ports / 2026-09-07.
3. Diseñar cómo mostrar una probabilidad calculada pero vetada como dato
   diagnóstico, sin color de recomendación, ranking ni mensaje favorable.
4. Medir en la Raspberry Pi 4 la publicación HA--worker por fases antes de
   implementar streaming incremental o cambiar la política de `fsync`.
5. Completar administración CLI por `coordinator_id` sin alterar otros
   coordinadores.

## Riesgos y dudas activas

- No consta en una fuente consultada durante este cierre qué versión ejecuta HA
  real. No asumir que 0.2.297 está instalada.
- La aplicabilidad actual puede vetar por una desviación normalizada alta aunque
  la diferencia absoluta sea pequeña. No ampliar umbrales globalmente sin la
  auditoría multiespecie.
- Una probabilidad vetada puede mejorar la transparencia, pero debe quedar
  inequívocamente separada de una recomendación.
- La optimización de streaming está documentada, no implementada. SHA-256 no
  sustituye la validación semántica, la autorización ni la promoción atómica.
- `mushroom_observations.json` sigue modificado y protegido fuera de Git.

## Archivos relevantes

- Entrada de continuidad: `docs/codex-start-here.md`.
- Prioridades: `docs/todo.md`.
- Decisiones: `docs/decisions.md`.
- Arquitectura: `docs/architecture.md`.
- Explorador: `rainmapper_core/mushroom_model_explorer.py` y
  `tests/test_mushroom_model_explorer.py`.
- Gate de constantes: `rainmapper_core/mushroom_ml_quality_catalog.py`,
  `rainmapper_core/mushroom_ml_reliability_audit.py` y
  `rainmapper_core/mushroom_ml_runtime_inference.py`.
- Worker y runtime multicoordinador:
  `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_predictor_runtime.py` y
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- Rendimiento e integridad HA--worker:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
- Selección/aplicabilidad:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.
