# Active Context

Ventana operativa de RainmapperHA al cierre del 8 de septiembre de 2026. No es
un histórico. Revalidar siempre repositorio, contenedores, datos y servicios
antes de asumir que este estado sigue vigente.

## Estado comprobado del repositorio

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- La release HA `0.2.298` está publicada en GHCR; revalidar el commit de
  `inicial`, HEAD y `origin/inicial` al comenzar la próxima sesión.
- La fuente declara HA `0.2.298` y worker `1.1.0`; sus secuencias de versión son
  independientes.
- El único cambio previo al cierre era
  `mushroom-data/mushroom_observations.json`, con SHA-256
  `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
  Es dato del usuario: no editarlo, restaurarlo, borrarlo ni incluirlo en un
  commit. Los datos vivos del laboratorio están en `docker-data/`.

## HA 0.2.298

- GHCR `0.2.298` y `latest` se revalidaron al cierre y comparten el índice
  `sha256:0c0bb47d532146c9cfed16f02de277c27c917207a5765c032c44b9933e0f2785`.
  Contienen manifests `linux/amd64`
  `sha256:18aaba6e48bfdaeb4d1ba7e482fd6acf8b9e4e4235fcb4d68b10df4b33ed133f`
  y `linux/arm64`
  `sha256:04a9bdee109704b57ce6e18c257775db6791ba8115533f409d12b2279526908f`.
- HA local se reconstruyó desde el código funcional definitivo antes del bump
  mecánico y conserva la etiqueta `0.2.297`; su imagen efectiva es
  `sha256:2bb6456c346a40072b2ae2d7e81cd9f235e1913510d584f2f3008d896e608676`.
  Las huellas ejecutables comparadas coinciden con el workspace y la UI responde
  200. El smoke completo posterior pasó antes de publicar `0.2.298`.
- HA real no se ha actualizado todavía a `0.2.298`.

## Worker operativo

- `rainmapper-worker` está activo y healthy con la imagen local privada
  `rainmapper-worker:1.1.0`; el worker no se publica en GHCR.
- Imagen efectiva:
  `sha256:1bfb37b01867524214f2d8160cac05501bc62599768dff423b63174c6eac3e88`.
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

### Alta automática de especies en el catálogo de tuning

- Una especie que entra por primera vez recibe decisiones V2--V4 y V6
  declaradas. Sus 12 combinaciones V5 seleccionan configuración usando solo la
  partición de entrenamiento; si no hay evidencia suficiente queda registrado
  el fallback conservador ya definido.
- El catálogo emitido por el entrenamiento se incluye en el resultado del
  worker, se valida por identidad y SHA-256, se instala con el batch y se
  reutiliza en entrenamientos posteriores. Un hueco parcial en una especie ya
  representada o una forma nueva de modelo/versión/perfil sigue fallando de
  forma cerrada.
- La generación validada contiene 714 decisiones, 78 para
  `cantharellus_cibarius_sl`, incluidas 12 V5 con selección interna disponible,
  y ningún marcador provisional pendiente.

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

- Entrenamiento base: `worker_job_9kf7flIQdeWwcfo2`, nueve especies.
- Multiversión: `worker_job_YJB38dkADdODwIJF`, batch
  `operational_20260908T141228Z`, 714/714 artefactos promovidos y cero fallos.
- Precálculo: `worker_job_DlnlE-bWTd_F`, revisión deseada 44, 462 miembros.
- Artefacto de precálculo:
  `sha256:89b55ee5edabd9558e29e87f353f2bc64f364c021d7d1a2f5531ff7293d789a2`;
  runtime fingerprint:
  `sha256:79c6d9be5ceb81f503a932d96d7386a2051f709d909913ee592add4eb2357eb2`.
- SQLite: 31.604.736 bytes y SHA-256
  `90a0cb8b8f01e01d797c32aeede4f6003411dd12e739d0130b201b8b7acda7bd`.
  Cubre del 8 al 14 de septiembre, 78 áreas, nueve especies y cinco versiones.
- El smoke de release pasó 1.335 pruebas en `56,576 s`, además de sintaxis,
  fixtures y comprobaciones de histórico. Después solo cambiaron metadatos de
  versión, cache-busters, changelog y documentación.

## Próximos pasos, por prioridad

1. Instalar HA `0.2.298` en HA real
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

- HA real no se ha comprobado mediante endpoint en este cierre; no asumir que
  `0.2.298` está instalada hasta verificarla después de la actualización.
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
