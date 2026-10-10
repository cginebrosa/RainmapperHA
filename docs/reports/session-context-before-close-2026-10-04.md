# Contexto archivado antes del cierre — 04/10/2026

Snapshot histórico del contexto sustituido al cerrar la discusión de utilidad de
predicciones. No es el estado vivo ni una orden de retomar pendientes. Prevalecen
[active-context.md](../active-context.md), [todo.md](../todo.md) y
[decisions.md](../decisions.md). Se conserva el contenido previo; sólo se ajustan
los enlaces relativos por su traslado a `docs/reports/`.

---

# Contexto activo — cierre de investigación 04/10/2026

Leer [codex-start-here.md](../codex-start-here.md) y este documento basta para
continuar; [todo.md](../todo.md) sólo amplía pendientes. **La auditoría del disco
queda detenida por decisión del usuario**, con la conciliación incompleta.
El usuario autorizó documentar y lanzar el goal de investigación de predicciones,
con experimentos locales aislados y acotados. Primera comparación completada;
[resultado](../agents/prediction-thresholds/resultados-2026-10-03.md). Encargo y cierre en
[goal.md](../agents/prediction-thresholds/goal.md) y [estado.md](../agents/prediction-thresholds/estado.md).
No ejecutar nuevas limpiezas, despliegues ni trabajos operativos.

El usuario pidió después separar las investigaciones: la anterior se renombró
a `docs/agents/prediction-thresholds/` y la nueva está en
[prediction-model-selection](../agents/prediction-model-selection/README.md).
El usuario autorizó después lanzar el nuevo agente. **Comparación de selección
completada el 04/10**; [informe](../agents/prediction-model-selection/resultados-2026-10-04.md)
y [estado](../agents/prediction-model-selection/estado.md). A usa ranking reciente
Y−1, B acumula Y−2+Y−1, C selecciona diariamente con B; mismos modelos finales
por corte, sin nuevos ajustes. Tres cortes, 116 observaciones, 812 emisiones por
variante, 19.514 contratos compartidos B/C verificados y 35 pruebas superadas.
No promover B/C con esta evidencia exploratoria: aereus no mejora; caesarea B
mejora precisión y reduce falsos favorables, y C gana 11,43 aciertos ponderados
con 0,43 falsos favorables más frente a A. Ninguna supera la regla original;
eso no demuestra que sus intercambios carezcan de utilidad. B caesarea2025 se
abstiene por selección semanal seguida de veto ROC (175 emisiones) y huéspedes
desconocidos (siete).
Mantener la referencia no demuestra que sea óptima. Evidencia reutilizada y
exploratoria; reglas numéricas del agente, sin coste relativo elegido por el usuario.
Unos 47 minutos conjuntos de lotes sobre un techo de 120, no una estimación
de duración; pico RSS nuevo 786 MB. Originales y estudio previo conservados;
cierre técnico en `tmp/prediction-model-selection/closure.json`. No repetir
cálculos cerrados ni lanzar nuevas hipótesis o seguimiento sin otro encargo.

**Discusión de utilidad documentada el 04/10:** el usuario prefiere 10 consejos
favorables con nueve aciertos a 40 con 30, siempre que haya recomendaciones
suficientes; 90% no es un mínimo obligatorio acordado. El
[informe ampliado](../agents/prediction-model-selection/resultados-2026-10-04.md#indice-utilidad-oportunidades)
recoge `I_k = 100 × (TP − k × FP) / P`, con `P` = favorables reales, incluidos
los no detectados; no todos los casos ni sólo los consejos favorables. Con
`k = 3` **provisional**, caesarea A/B/C = −31,43 / +16,73 / −2,45 y aereus
A/B/C = −15,48 / −32,14 / −27,38 puntos. Son cálculos sobre resultados guardados,
no otro experimento ni porcentajes de acierto. Pendientes: coste definitivo,
mínimo de índice, cantidad/frecuencia útil de consejos, soporte independiente y
estabilidad por campaña. La nueva escala no garantiza por sí sola suficientes
consejos ni evidencia fiable. No cambiar retroactivamente criterios cerrados ni
promover variantes. El siguiente paso, si el usuario lo encarga, es concretar
esos requisitos antes de una nueva validación; no hay otro agente lanzado por
esta ampliación documental.

## Investigación de predicciones: primera comparación completada

- Protocolo: [docs/agents/prediction-thresholds/README.md](../agents/prediction-thresholds/README.md), con
  método, fases y límites del agente. Se estudiaron **Boletus aereus** y
  **Amanita caesarea**, selección del ganador y recomendación final del mapa.
- Preferencia del usuario: penalizar más los falsos favorables que los falsos
  desfavorables, conservando utilidad; no aceptar «siempre desfavorable» como mejora.
- Aclaración del protocolo: el código revisado ajusta los modelos productivos con
  todas las muestras elegibles; el antiguo 30 % no es independiente del ajuste final.
  El histórico puede reutilizarse en experimentos con modelos y ranking nuevos por
  partición. Repetir particiones no añade episodios independientes; la suficiencia
  y la necesidad de confirmación prospectiva se detallan en el informe final.
- El usuario confirmó la descarga a local. [Inventario en lectura del 03/10](../agents/prediction-thresholds/inventario-inicial-2026-10-03.md):
  copia montada por HA local con 544 observaciones y 113 setales. Aereus: 86 filas,
  53 favorables/33 desfavorables; caesarea: 98, 63/35. Grupos técnicos de 14 días:
  40 y 57; no acreditan por sí solos independencia. El usuario confirma que los
  16 GBIF de caesarea etiquetados `normal` son favorables igual que los demás:
  mantenerlos incluidos, sin exclusión, penalización ni revisión adicional por origen.
- En el lote local `operational_20260928T005344Z`, 85 IDs de aereus y 97 de caesarea
  aparecen en al menos un modelo pertinente. Sólo uno por especie está ausente de
  todos, ambos favorables; no bastan para una prueba final del equilibrio de errores.
  Meteorología hasta el 03/10 según manifiesto; dos artefactos derivados siguen
  fechados el 28/09 con 542 filas y no contienen esos dos IDs. El usuario confirma
  que ése fue el día del último entrenamiento: es lo esperado, no una incidencia
  ni motivo para relanzarlo. No se reconstruyeron.
- Investigación completada: cohorte privada de 499 registros elegibles del ámbito
  compartido, incluidos los 184 objetivos. Cortes externos 2024/25/26 fijados antes
  de calcular, con 116 observaciones externas distintas. Protocolo y mínimos B en
  [protocolo de ejecución](../agents/prediction-thresholds/protocolo-ejecucion-2026-10-03.md).
  Scripts aislados en `scripts/prediction_research/`; 1.512 ajustes completados,
  812 emisiones externas y bootstrap por grupos. Se usaron también los 68 casos
  objetivo anteriores a 2024 para desarrollo. El primer lote alcanzó 4 GiB;
  el usuario autorizó subir a 8 GiB por proceso. Se añadió un lector experimental
  sin leases operativos y protección de escrituras; conservar límites restantes.
  [Resultado](../agents/prediction-thresholds/resultados-2026-10-03.md): no promover B.
  Aereus pierde aciertos sin mejorar precisión favorable (76,7 % → 76,1 %);
  caesarea conserva el mismo umbral y resultado. Evidencia limitada y alta abstención;
  los cortes aereus2024/caesarea2025 no superan el soporte mínimo de ranking.
  Esto no es evaluación directa del modelo instalado. Once pruebas pasan;
  originales verificados, sin trabajos operativos. Unos 19,7 min de lotes y 1,23 GB
  privados. No repetir preparación, ajustes ni inferencias. La segunda investigación fue autorizada después y se describe arriba;
  un seguimiento prospectivo sigue requiriendo otro encargo.
  GBIF `normal` y fecha del último entrenamiento están aclarados. Conservar datos y modelos
  activos, HA real y worker/coordinadores. No se autorizan trabajos operativos.

## Estado operativo que no hay que rehacer

- **HA 0.2.331 instalada y funcionando**, confirmado por el usuario. Release
  `c28a514` en `inicial`; HEAD comprobado en este cierre. Publicación, paridad local
  y smoke final (1.859 pruebas / 55 omitidas) ya cerrados. Incluye círculos ES/CA/EN,
  edición por centro/radio y corrección GBIF de 16 decimales, además de organización
  geográfica local. [Evidencia](../reports/release-ha-0.2.331-2026-10-03.md).
  La confirmación del usuario no es una inspección nueva del runtime.
- Worker: última versión documentada **1.1.6**, coordinador primario
  `http://100.111.77.48:8100`, adicional `http://rainmapper-ha-ui:8100` e identidad
  `worker_1a9a232c20fe2ee2`. No se reinició ni modificó durante limpieza/cierre.
  No se afirma que esté ocioso ahora: revalidar sólo si la siguiente tarea lo exige.
- Entrenamiento y precálculo reales anteriores confirmados terminados; precálculo
  posterior a reorganización auditado en lectura (revisión 277, 987/987 combinaciones).
  Son evidencias históricas; no relanzarlos ni repetir auditorías cerradas.
- Geografía real activada y raíz correcta `/media/rainmapper/geography/`.
  Local: `docker-media/rainmapper/geography/`; worker: `geography/` en su volumen.
  **Operativa incluye todos los originales que aún necesitan sus consumidores.**
  `geography-sources/` conserva originales/descargas, expansión y preparaciones.
  `docker-media/` es persistencia de HA local, no basura ni una descarga prescindible.

## Limpiezas realizadas y límites de autorización

1. Eliminadas con autorización **sólo** `mushroom-GIS-todelete/` y
   `mushroom-map-GIS-todelete/` del Mac. Ausencia revalidada al cerrar; fuentes y
   operativa siguen presentes. Revisión previa: 5.891 archivos con destino conservado;
   aumento observado de libre **21,83 GB**. No recrear esas carpetas.
   [Plan cerrado](../mushrooms/geography-local-organization-plan-es.md) y
   [recibo/inventario](../reports/geography-todelete-review-2026-10-03.md).
   Share/media montados de HA no contenían `todelete` en la revisión; no se borró nada remoto.
2. Usuario acepta perder todas las conversaciones archivadas de Codex. Retirados
   **61/62 archivos** mediante CLI nativa y dos archivos huérfanos sin entrada en
   índice. Queda uno, revalidado al cerrar: **523.865.594 bytes**, sesión
   `01a073a6-7e39-77e2-8585-e5ab8cfcc5f0`, bajo `~/.codex/archived_sessions/`.
   `codex delete UUID --force` devuelve `Error: failed to delete session`.
   Archivo e índice conservados; causa desconocida, no editar SQLite manualmente.
   La autorización de retirada de ese archivo pendiente sigue vigente; no se
   extiende a sesiones activas ni a otras bases. No ejecutar de nuevo scripts
   de borrado en bloque: sus manifiestos/contadores incluyen intentos fallidos.
3. Eliminadas **247 carpetas temporales de pruebas de navegador**, tras comprobar
   uso/montajes/inodos. Se perdieron sus capturas, perfiles y logs; informes del repo
   conservados, pero sus enlaces a esas capturas pueden quedar rotos.
4. Limpieza Codex+navegador: libre **144,49 → 165,24 GB**, unos **20,76 GB**.
   El intervalo ya incluye los 0,60 GB del navegador; **no sumarlos otra vez**.
5. **Instaladores conservados:** VS Code instalado 1.139.1 / preparado 1.140.0;
   Docker instalado 4.78.0 / preparados 4.92.0 y 4.93.0, dos DMG montados y
   `com.docker.install/in_progress`. Son versiones observadas durante la auditoría,
   no una comprobación nueva del actualizador. Los 4,63 GB bajo `com.docker.install`
   eran contenidos montados, no otros 4,63 GB exclusivos además de sus DMG.
   Revalidar y acordar cómo terminar/descartar actualizaciones antes de retirarlos;
   no desmontar ni parar Docker/worker por iniciativa propia.

No borrar Lightroom, WhatsApp, fuentes, auditorías, caché Buildx ni volúmenes
sin acordar alcance. «Puedo borrar WhatsApp» fue una posibilidad planteada por el
usuario, no una orden de desinstalación; no se desinstaló ni se necesita para
explicar su tamaño aparente. No ampliar las autorizaciones anteriores.

## Disco: resultado corregido, no volver a confundir contabilidades

[Informe completo y fuentes](../reports/mac-disk-audit-2026-10-03.md).
Medidas del 03/10, no promesas de espacio recuperable ni lecturas futuras:

- Repo: **47,83 GB contando inodos una sola vez**, frente a ~57–58 GB al sumar
  carpetas por separado; **9,38 GB** compartidos por hardlinks entre docker-data
  y docker-media. Dentro del repo: fuentes 22,26 GB; docker-media ~16,4 GB
  (contiene geografía operativa). No sumar estas partes de nuevo al total.
- **WhatsApp resuelto:** suma por archivo ~263 GB, pero **2,443 GB contando una
  vez cada identificador de clon APFS**. La app muestra 2,31 GB. Inventario:
  555.323 archivos, 6.772 flujos distintos, 704 grupos repetidos, hasta 3.801
  referencias al mismo flujo. No son 263 GB físicos de vídeos ni hardlinks.
  Sólo se consultaron metadatos, no mensajes/multimedia. Causa de tantas
  referencias no investigada; no es necesaria para explicar la suma inflada.
- Chrome `X/com.google.Chrome.code_sign_clone`: 42,87 GB sumados → 5,274 GB
  contando clones una vez; pueden compartir también fuera de esa carpeta.
- Lightroom ~44,70 GB; Docker.raw **42,71 GB asignados**, no sus ~494 GB lógicos;
  aplicaciones instaladas 38,19 GB; Codex tras limpieza ~7,52 GB. No sumar
  volumen worker/imágenes/Buildx además de Docker.raw: ya están dentro.
- **Finder: 305,36 GB usados**, captura con bytes explícitos. No es confusión GB/GiB.
  `diskutil apfs list -plist` confirma System 17,09 + Data 288,28 ≈305,37 GB.
  **Contenedor completo: 329,08 GB**, incluyendo otros ~23,55 GB de Preboot,
  Recovery, Update y VM, más metadatos. No comparar ámbitos distintos.
- Finder disponible **179,82 GB incluye 14,5 GB purgables**; libre físico ~165,3 GB.
  No sumar purgables otra vez. Las cifras cambian durante el uso.
- Inventario corregido al ámbito Finder: **~269,6 GB atribuidos y ~35,8 GB aún
  sin atribuir**, sobre 305,36 GB. Es balance aproximado: redondeos, instantes
  distintos y posibles clones entre categorías. No afirmar conciliación exacta.
  La tabla inicial de 221,6 GB era incompleta y mezclaba ámbitos; quedó corregida.
- Acceso bloqueado incluso fuera del sandbox: Downloads, Trash, Photos Library,
  MobileSync, DocumentRevisions y Spotlight (`Operation not permitted`), fseventsd
  (`Permission denied`). No inferir que esas carpetas explican todo el resto ni
  eludir controles de privacidad. Para cerrar la cuenta hace falta acceso macOS
  adecuado o tamaños facilitados por el usuario, y revalidación proporcional.

## Próximos pasos por prioridad

1. **Umbrales y selección del ganador completados:** informes en
   `docs/agents/prediction-thresholds/` y `docs/agents/prediction-model-selection/`.
   No promover variantes ni repetir cálculos. Hipótesis para otro encargo: coherencia
   entre selección semanal y filtros, y utilidad de la selección diaria para
   caesarea con costes previamente acordados y posterior confirmación prospectiva.
   No reabrir la auditoría del disco ni lanzar trabajos operativos.
2. Aplazado: resolver el error de la sesión Codex pendiente (autorización de retirada
   documentada, pero las limpiezas no se retoman durante la investigación), sin
   perder sesiones activas ni manipular índices a mano. Preparar una actuación
   concreta sobre instaladores pendientes sólo tras comprobar su estado/uso.
3. Pruebas funcionales del usuario: asignación de observaciones, recuperación GIS
   en setales e importación GBIF. Edición circular local aceptada; no queda release
   pendiente por esos círculos. No suplir recorridos con entrenamientos automáticos.
4. Sólo si se prioriza: trabajo huérfano tras perder worker, tiempos crecientes de
   precálculo, consumidores MVC50 originales, setales fuera de áreas y topónimos
   GBIF. Detalles y aplazamientos en TODO; no son tareas automáticamente autorizadas.

## Evidencia y archivos para continuar sin releer historia

- `tmp/disk-audit-20261003/`: recibos `archived-deletion.json`,
  `browser-deletion.json`; `whatsapp-apfs.json`, `chrome-apfs.json`,
  `accounting-approximate.json`, `apfs-after.plist`; metadatos de instaladores y
  scripts. El JSON contable inicial usa **ámbito contenedor**; aplicar la
  corrección Finder del informe, no sus totales sin contexto.
- `apfs_metadata.py` consulta `getattrlistbulk`/identificadores de clones en lectura;
  no lee contenido de archivos. No usar suma simple de `du` para atribuir clones.
- `tmp/geography-retirement-20261003/deletion.json`: retirada de antiguos.
  Estos recibos están ignorados por Git; el informe versionable conserva conclusiones.
- Worktree: cambios documentales de cierre sin commit/push; HEAD `c28a514`.
  Privados preexistentes: `mushroom-data/mushroom_observations.json` modificado y
  `mushroom_observations.json` raíz sin seguimiento. **No añadir, revertir ni copiar.**
- HA local conocido: `rainmapper-local-rainmapper-ha-ui-1`, puerto 8101; worker
  `rainmapper-worker`. No se inspeccionaron/recrearon en este cierre documental.
- Volúmenes usados anteriormente: `/Volumes/share`, `/Volumes/media-1`.
  Usuario puede montarlos por Tailscale; Codex sólo usa montajes existentes tras
  verificar origen. No montar, no SSH, no escritura remota por defecto.

## Decisiones operativas/científicas que siguen vigentes

- Política territorial `territorial_sources_v1`: árboles MFE25→MVC50; bosque
  MVC50→Cobertes 2024; sustrato MVC50→geología 1:50.000; litología geológica.
  Sólo mapeos aceptados; no inferir suelo del bosque/pH. Campins/Qv3 queda no
  determinado, POa silíceo según mapping; caso cerrado, no añadir reglas por vecinos.
- Mantener entrenamiento existente (evaluación previa y ajuste final); IFF no es
  porcentaje de acierto y consultar filas de entrenamiento no prueba generalización.
  IDW sin filtro de consenso espacial; SMI regulado + PM + una capa, simple visual;
  conservar suspensiones y revalidar modo de recomendaciones antes de interpretarlo.
- Reparación Meteocat histórica cerrada: no ejecutar la candidata antigua
  `tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py`, perdería datos nuevos.
  Data y PublicData no se sincronizan por copiar uno de ellos.
- No tocar worker/coordinadores, lanzar jobs, desplegar ni repetir smoke/hash GIS
  por esta documentación. Progreso breve aproximadamente cada minuto.
- Detalles retirados de la ventana activa, sin pérdida de historia:
  [contexto archivado](../reports/session-context-before-close-2026-10-03.md).
  Decisiones canónicas en [decisions.md](../decisions.md); anexos sólo según tarea.
