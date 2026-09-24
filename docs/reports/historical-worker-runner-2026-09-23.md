# Histórico: aviso de worker no disponible durante el runner

Diagnóstico inicial del 23/09/2026, mediante lecturas sin reinicios. El usuario
aclara que al capturar el aviso no había trabajos worker; el precálculo comenzó
después de terminar el runner. No atribuir la captura al carril background
ocupado observado posteriormente.

## Hechos comprobados

HA real ejecuta 0.2.320 según `/share/rainmapper/diagnostics/runtime_state.json`,
leído mediante SMB LAN. Worker 1.1.6 responde en `/health`; foreground idle y
background ejecutando `worker_job_tK6ox8g7j2UD` al comenzar esta investigación.
Ambos carriles se reservan independientemente en `mushroom_worker_service.py`.

Cronología real del 23/09, hora Europe/Madrid (UTC+02):

| Hora | Evidencia |
| --- | --- |
| 11:00:17 | Inicio del runner programado, `runtime_metrics.jsonl` |
| 11:04:03.463 | Cambio de `Data/weather-history/CURRENT.json`, mtime persistido |
| 11:06:51.768 | Publicación de `cache/predictor-runtime-archives/published-runtime.json` |
| 11:06:51.817 | Fin correcto del runner, registro diagnóstico |
| 11:07:04.144 | Sincronización del mapa en el worker, `primary/map/last-sync.json` |
| 11:07:07.104 | Worker toma el precálculo originado por el runner, log y registro HA |

Generación meteorológica actual en HA y copia worker:
`20260923T090403454263Z-a49f34feae52`. Copia de mapa sincronizada:
`sha256:1e61cc4d1385ba2ce8c22bb77632a61842d20f5a5dea9ac7949dc96e79f1cfc1`.
No se regeneró ninguna copia para obtener estas pruebas.

## Mecanismo confirmado en el código publicado (0.2.320)

- `MapPublication.reference()` (`mushroom_map_runtime.py:188`) exige que las
  referencias actuales coincidan con la firma de la copia publicada; de lo
  contrario devuelve `map_data_not_ready`.
- `refresh()` del mismo módulo, al comparar `CURRENT.json` con la copia del
  Predictor sellada, devuelve `map_weather_publication_pending` si no coinciden.
  Así evita mezclar generaciones durante el runner.
- `serve_worker_api()` (`mushroom_prediction_map_ui.py:94`) marca al worker no
  elegible mientras no haya referencia coherente/sincronizada, aunque responda.
- `QueryBroker.submit()` (`mushroom_map_queries.py:75`) traduce la ausencia de un
  worker elegible para histórico a `executor_unavailable`.
- `historical-mode.js:217` captura **cualquier** error del worker y presenta el
  texto genérico `execution_fallback`: no distingue datos en actualización,
  worker ocupado, timeout, fallo de cálculo o respuesta inválida.

Prueba dirigida existente repetida: `test_missing_publication_stale_weather_or_models_fail_closed`
en `tests/test_mushroom_map_runtime.py`, 1 test, OK. Reproduce el rechazo ante
desfase de meteorología/modelos sin necesitar un trabajo activo.

## Conclusión y límites

Hay una ventana comprobada de unos 2 min 48 s entre el cambio meteorológico y
la publicación para el worker, seguida de sincronización. Este mecanismo encaja
con el aviso observado durante el runner; el mensaje no demuestra que el worker
estuviera caído u ocupado. La consulta concreta de la captura no conserva su
código de error en la evidencia consultada: no afirmar causalidad individual
con certeza absoluta.

También constan timeouts/`URLError` intermitentes de la asociación principal,
anteriores y posteriores a esa ventana. No se ha aislado su causa ni deben
presentarse como explicación demostrada de aquella consulta. No se probó la ruta
Tailscale directamente ni se modificó el coordinador.

Corrección acordada: distinguir datos aún publicándose/sincronizándose de una
indisponibilidad real y conservar una causa precisa en el fallback del histórico.
No retirar la protección de coherencia ni servir mezclas de generaciones como
arreglo. La continuidad con una generación anterior sellada requiere un diseño
específico que preserve también modelos y suspensiones vigentes.

Evidencia acotada local: `tmp/historical-worker-20260923/runner-timeline.json` y
`worker-window.log`. SMB LAN montado en `/Volumes/share` y `/Volumes/media`
desde `192.168.0.121`; los nombres de montaje cambiaron respecto a otras sesiones.
HTTP LAN de controles devolvió 403 por requerir Ingress; no se eludió ese control.
Sin SSH, escrituras en HA, entrenamientos, precálculos ni reinicios de worker.

## Corrección implementada y desplegada sólo en HA local

Autorizada por el usuario con «pues lo hacemos» después del diagnóstico.

- El coordinador comunica al broker una causa acotada cuando la copia del mapa
  está publicándose, sincronizándose o requiere capacidades que faltan. El estado
  expira con el heartbeat; al quedar preparado se elimina la causa anterior.
- El histórico conserva esa causa al pasar a local, con textos en ca/es/en para
  actualización, sincronización, ocupado, incompatibilidad, timeout, respuesta
  inválida, conexión y otros fallos. La cancelación del usuario no activa fallback.
  La fecha del progreso usa DD/MM/AAAA.
- Se mantienen las comprobaciones de generaciones y la cola de un worker
  preparado pero ocupado. No se ha alterado el contrato del worker ni su proceso.
  Esta corrección aclara el aviso; no elimina la ventana de publicación del runner
  ni demuestra cuál fue el error concreto de la captura.

Validación: 52 pruebas dirigidas de histórico, broker, handlers y runtime; prueba
de navegador completa OK, incluyendo diez casos nuevos de avisos/fallback en tres
idiomas. La primera invocación Python tuvo un error de importación del fixture de
runtime; corregida mediante `PYTHONPATH=tests`. La prueba nueva de navegador tuvo
un error de clave en el propio test; corregido y ejecución completa posterior OK.
Logs finales: `/private/tmp/rainmapper-history-reasons-tests-final.log` y
`/private/tmp/rainmapper-history-reasons-browser.log`.

HA local reconstruido y recreado sin trabajos locales pendientes; HTTP 200.
Paridad efectiva de sus 220 archivos sin diferencias, evidencia
`tmp/historical-worker-20260923/local-parity.json`. Worker conserva el mismo ID,
arranque e imagen; hashes de coordinadores/tokens, política de suspensiones y
observaciones privadas coinciden con las huellas previas.

Sin bump, commit ni publicación nueva. HA real permanece en 0.2.320. El worker
no se reconstruyó ni reinició; esta comprobación local no sustituye la validación
conjunta exigida antes de una futura release.
