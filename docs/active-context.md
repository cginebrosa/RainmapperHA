# Active Context

Ventana operativa de RainmapperHA al cierre del 8 de septiembre de 2026. No es
un histórico. Revalidar siempre repositorio, contenedores, datos y servicios
antes de asumir que este estado sigue vigente.

## Estado comprobado del repositorio

- Ruta: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- La fuente declara HA `0.2.297` y worker `1.1.0`. Son secuencias de versión
  independientes. El commit de release debe revalidarse con `git rev-parse
  HEAD` y `git ls-remote origin refs/heads/inicial` al comenzar otra sesión.
- `mushroom-data/mushroom_observations.json` también está modificado y pertenece
  al usuario. No editarlo, restaurarlo, borrarlo ni incluirlo ciegamente en un
  commit. Los datos vivos del laboratorio están en `docker-data/mushroom-data/`.

## HA 0.2.297

- HA `0.2.297` está publicada en GHCR. Los tags `0.2.297` y `latest` comparten
  el índice `sha256:07d3eb86efcfc2e6ba2ed02193c19d1503efba021a6256c95b858d71e24fcbfe`.
  Se verificaron los manifests `linux/amd64`
  `sha256:b243a1a8f690dee500fe7f16642f96c2d725c19fc770ffa87f340771c9e08d38`
  y `linux/arm64`
  `sha256:48b6c6b35aa5ae888bb26293722706e28f900db7d755f3eef4d4f8410453ab2f`.
- HA local está activa con `rainmapperha:local-ha-ui`; su imagen declara
  `io.hass.version=0.2.297`.
- `0.2.297` aún no estaba instalada en HA real al cerrar esta ventana. La imagen
  ya está publicada y queda lista para que el usuario la instale después del
  commit/push de la fuente.
- La release conserva el último SQLite autocontenido mientras se publica un
  runtime meteorológico nuevo, señalándolo como desactualizado; no deja el
  Predictor vacío durante esa sustitución.
- La vigencia no exige que el precálculo se haya iniciado el mismo día. Sigue
  siendo utilizable si hoy cae dentro de su cobertura y coinciden sus
  identidades e integridad.
- `Esta semana`, `Por especie` y `Consultar fecha` leen la respuesta sellada e
  indexada del SQLite. No reconstruyen cientos de miembros ni repiten la
  validación profunda en cada consulta. En las comprobaciones de UI, las vistas
  agregadas fueron prácticamente inmediatas; `Consultar fecha` también quedó
  rápida después de eliminar su recomposición redundante.
- El detalle `Versiones operativas y disponibilidad` se oculta en las vistas
  donde queda vacío y se conserva en `Consultar fecha`, donde sí tiene datos.
- La navegación directa muestra un modal y bloquea clics repetidos mientras la
  petición está en curso.
- La release evita reencolar un deseo de precálculo ya publicado cuando, tras
  reiniciar el coordinador, su entrada histórica ya fue compactada.

## Worker multicoordinador

- El contenedor `rainmapper-worker` está activo y healthy con la imagen privada
  local `rainmapper-worker:1.1.0`. El worker no se publica en GHCR.
- Etiqueta, variable de entorno y endpoint de salud declaran `1.1.0`. Se
  compararon las huellas de cinco ficheros clave entre host y contenedor y
  coincidieron.
- Conserva la identidad `worker_1a9a232c20fe2ee2` y dos asociaciones:
  - principal: `http://100.111.77.48:8100`;
  - adicional `HA local`: `http://rainmapper-ha-ui:8100`.
- Está prohibido cambiar cualquiera de esos destinos sin autorización expresa
  para ese destino concreto. Reconstruir, recrear, reiniciar o probar el worker
  no autoriza a modificar sus asociaciones.
- El servicio admite varios coordinadores, credenciales independientes y dos
  carriles globales: uno para entrenamiento/reconstrucción y otro para
  precálculo. El circuito local completo terminó correctamente con ambos
  coordinadores conservados.
- El fallo reproducido alrededor del 64 % era del worker: verificaba el hash de
  `quality-catalog.json.gz`, pero intentaba leer sus bytes comprimidos como JSON.
  El lector ya verifica, descomprime y reutiliza el catálogo durante toda la
  comparación. El precálculo posterior materializó los 420 miembros esperados.
- La caché de runtime mantiene un árbol lógico distinto por
  coordinador y reutiliza objetos físicos idénticos mediante SHA-256. El
  coordinador principal conserva por compatibilidad la raíz histórica; los
  adicionales usan `predictor-runtime/coordinators/<coordinator_id>/`; ambos
  comparten `predictor-runtime/objects/`.
- La suite completa validada antes de la release pasó 1.331 pruebas en
  `57,644 s`. Después solo cambiaron documentación y metadatos de versión, por
  lo que no se repitió el smoke completo.
- El CLI todavía no permite listar, seleccionar, cambiar URL, reemparejar,
  limpiar credenciales u olvidar un coordinador concreto por `coordinator_id`.
  El diseño vinculante es
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.

## Último precálculo real observado

- Job: `worker_job_dIio5biEkD59`; terminó correctamente y publicó la revisión
  deseada 43.
- Artefacto:
  `sha256:7d07a53d570a6a9968d22d637d0f5aa2e790aede5f63301eed1bb8586ea338b0`;
  runtime fingerprint:
  `sha256:6289597ea738727f2f2f9b194de43811cfb00383d3870c4de7ebf3be8eca6c46`.
- SQLite: `30.478.336` bytes. La copia activa de HA y la copia lógica del
  coordinador local en el worker compartían SHA-256
  `1990c6e20b6c7ef014ed71a7353d6505d0c114007f1c6b5e67252a015d74a4d1`.
- El batch multiversión `operational_20260908T000329Z` produjo 636/636
  artefactos y el precálculo materializó 420 miembros operativos.
- La auditoría del transporte e integridad queda en
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
  Determina que HA aún bufferiza cuerpos completos y rehace algún SHA, pero no
  autoriza retirar validación semántica ni durabilidad sin medir primero.

## Control local de modelos constantes

- Está implementado, reentrenado y aplicado al precálculo un gate de
  degeneración basado en las probabilidades hold-out.
- Se calcula por `split_id`, especie y candidato exacto (versión, perfil,
  contrato, horizonte y estimador). Con al menos dos resultados, un rango
  máximo menos mínimo `<= 0,000001` marca `constant_prediction=true`.
- La selección sellada excluye ese candidato para toda la especie y propaga el
  veto a sus ámbitos territoriales con el motivo
  `constant_species_prediction`. No se excluyen algoritmos por carecer de
  coeficientes: Random Forest, KNN y otros siguen siendo válidos si sus salidas
  hold-out varían.
- El catálogo compacto conserva media, desviación, rango e indicador constante
  una sola vez por evaluación de
  especie/candidato/split. El gate operativo compartido vuelve a comprobar el
  indicador como defensa; por ello el precálculo hereda la regla sin ejecutar
  análisis de modelos durante la consulta.
- La batería completa pasa 1.331 pruebas, incluidas las dirigidas de catálogo,
  selección, fallback del servicio que usa el precálculo y explicación de UI.
- En la generación promovida se auditaron 2.880 entradas primarias y 3.456
  alternas. Había 181 candidatas constantes en cada catálogo. Las 280 filas de
  selección sellada coincidían exactamente con el catálogo y ninguna eligió un
  modelo constante; tampoco lo hizo ninguno de los 420 miembros del precálculo.
- En ese mismo corpus, media, desviación, rango, indicador y política añadieron
  487.491 bytes al JSON compacto y 84.879 bytes una vez comprimido con gzip. No
  se añaden al SQLite por cada área/día ni se recalculan durante la consulta.

## Revisión pendiente: abstención de Rovelló en Els Ports

Caso exacto inspeccionado en el SQLite activo del worker:
`lactarius_deliciosus / els_ports / 2026-09-07`.

- La tarjeta muestra `Sin recomendación fiable`. No equivale a una probabilidad
  del 0 %.
- El candidato preferido es LR-V3, retardo `h1`, elegido mediante fallback de
  evidencia de especie. Su evidencia global es 16 observaciones: 13 positivas,
  3 negativas, 13/13 recomendaciones favorables acertadas y límite conservador
  del 77,19 %.
- Els Ports solo aporta una observación positiva. El 1/1 observado da 100 %, pero
  su límite conservador es 20,65 % y el ámbito se excluye por clase única. Por
  eso el área no decide y se usa la fiabilidad global de la especie.
- El modelo sí existe y calculó `0,000016`, aproximadamente `0,0016 %`, con
  etiqueta desfavorable. La abstención se produce después porque dos de sus 27
  variables quedan fuera del dominio aprendido:
  - humedad máxima de 8--14 días: `88,062 %`, frente a mínimo de entrenamiento
    `89,001 %`; desviación normalizada `4,451`;
  - temperatura máxima de 7 días: `33,151 °C`, frente a máximo de entrenamiento
    `30,933 °C`; desviación normalizada `3,015`.
- El primer caso difiere menos de un punto porcentual y no parece un motivo
  razonable de bloqueo por sí solo. La temperatura difiere más de dos grados y
  supera 30 °C, por lo que sí puede constituir una extrapolación material. Esta
  valoración queda como hipótesis a revisar, no como cambio aprobado.
- En `h7` se excluyen 36 candidatas por aplicabilidad y 6 por miembro no
  disponible; en `h1`, 27 y 5 respectivamente. No queda una candidata aplicable
  y fiable, y el selector se abstiene.
- El texto visible `aplicabilidad · modelo no disponible` mezcla causas. En el
  candidato principal el modelo estaba disponible; fue rechazado por
  aplicabilidad. Debe revisarse esa explicación.
- Propuesta para evaluar, **no implementada**: mostrar la probabilidad calculada
  aunque exista abstención, con un estado visual inequívoco que diga que el
  modelo se abstiene y que esa cifra no es una recomendación. En este caso la
  probabilidad ya es extremadamente desfavorable, por lo que ocultarla no cambia
  la decisión práctica, pero sí reduce la transparencia.
- Antes de modificar el veto hay que auditar más casos y separar tolerancia
  absoluta, desviación estadística, naturaleza de la variable y sentido de la
  extrapolación. No sustituir esa revisión por ampliar límites globales.

## Próximos pasos

1. Revisar las reglas de bloqueo de aplicabilidad con el caso de Els Ports y una
   muestra multiespecie; decidir también cómo presentar probabilidades de
   modelos abstencionistas.
2. Instalar HA `0.2.297` cuando el usuario lo decida y comprobar únicamente el
   arranque/versión y el uso del precálculo ya publicado; no repetir trabajos
   pesados sin una causa nueva.
3. Completar la administración CLI por `coordinator_id` antes de considerar
   terminada la función multicoordinador.
4. Instrumentar la publicación HA--worker y, si las medidas lo justifican,
   implementar el streaming descrito en el handoff sin debilitar validación,
   atomicidad ni recuperación.

## Riesgos y dudas activas

- El worker es una imagen local privada `1.1.0`; no buscarla ni publicarla en
  GHCR. Antes de recrearlo, preservar y revalidar exactamente sus dos URLs.
- La actual aplicabilidad combina distancia normalizada y límites observados de
  forma que una diferencia absoluta pequeña puede bloquear. No cambiarla sin
  medir falsos bloqueos y extrapolaciones realmente peligrosas.
- Mostrar una probabilidad vetada puede mejorar la explicación, pero debe evitar
  que color, orden o texto la conviertan de nuevo en recomendación.
- Los datos de observaciones modificados siguen fuera de Git y deben preservarse.
- La optimización de streaming está documentada, no implementada en 0.2.297.
  No confundir el hash incremental con la validación semántica del artefacto.

## Archivos relevantes

- Inicio de continuidad: `docs/codex-start-here.md`.
- Prioridades: `docs/todo.md`.
- Decisiones: `docs/decisions.md`.
- Arquitectura: `docs/architecture.md`.
- Worker multicoordinador:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- Runtime/caché: `rainmapper_core/mushroom_predictor_runtime.py`.
- Servicio del worker: `rainmapper_core/mushroom_worker_service.py`.
- Rendimiento e integridad HA--worker:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
- Precálculo: `rainmapper_core/mushroom_predictor_precompute.py`.
- Selección fiable:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.
- UI del Predictor: `rainmapper-app/app/mushroom_predictor_ui.py`.
- Datos vivos locales: `docker-data/mushroom-data/`.
