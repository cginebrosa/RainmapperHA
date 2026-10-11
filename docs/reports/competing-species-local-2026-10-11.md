# Selección y comparación: especies configurables

Validado en HA local, incluido el trabajo de cinco especies lanzado por el usuario.
El usuario confirmó su finalización y autorizó publicar HA 0.2.337. Ver
[recibo de release](release-ha-0.2.337-2026-10-11.md).

## Comportamiento

- Workers → Selección y comparación conserva el desplegable cerrado por defecto.
- Las 21 especies del catálogo se presentan con casillas en una cuadrícula:
  seis columnas y cuatro filas a 1600 px, dos columnas a 768 px, una a 375/320 px.
- Guardar especies persiste sin encolar cálculos. Comprobar y actualizar guarda
  y usa la selección. Los refrescos conservan las casillas editadas sin guardar.
- Preferencia global en `prediction-competing-settings.json`, junto al estado
  de selección/comparación; mismo alcance para ejecución manual y runner.
  No modifica las preferencias K de los dispositivos ni la predicción habitual.
- Valores iniciales compatibles: aereus y caesarea. En local se han guardado
  esas dos más deliciosus, edulis y pinophilus (pinícola en el catálogo).
- Se valida contra el catálogo y se impide cambiar el alcance de un trabajo
  activo. La autorización sigue siendo la de Workers y trabajos.
- La huella histórica incluye las especies; no se presenta una preparación
  anterior de dos especies como cobertura de cinco. Se mantienen los límites
  de memoria/payload existentes y las cachés compatibles de unidades y ajustes.

## Verificación ejecutada

93 pruebas dirigidas de control, entradas, backend, histórico, runner, mapa,
comparación y reutilización pasan en 11,582 s. Incluyen guardado sin lanzar
trabajos, alcance compartido, validación y exclusión durante un trabajo activo,
cambio de huella al ampliar especies y reutilización de seis unidades
independientes anteriores al ampliar de dos a cinco especies.

Navegador real contra HA local reconstruido: guardado y recarga de las cinco
especies, conservación del borrador durante el refresco, desplegable cerrado
por defecto, cuadrícula sin desbordamiento en 1600/768/375/320 px y sin errores
de JavaScript. La única acción POST fue guardar especies. Se bloqueó cualquier
otra acción POST desde el navegador de prueba; no se lanzaron cálculos.

Planificación de lectura en HA local, sin encolar: las cinco especies tienen
candidatos; 266 familias, 1027 candidatos, petición de 231113 bytes, por debajo
del límite de lectura de 512 KiB del worker. Esto verifica las entradas previstas.

La ejecución posterior se auditó en los artefactos persistidos:

- Trabajo `worker_job_paDOHshhqxHzSEcM`, completo al 100 %, sin error y con
  limpieza terminal completada. Estado de control `ready`, revisión activa y
  deseada coincidentes, sin K pendientes.
- Cálculo: 169,34 s. 172 s entre creación y finalización, incluidos 2 s de cola.
- Cinco especies preparadas para K=2 y K=4; las diez comparaciones están
  `ready`, con Iₖ finito para Habitual y A/B/C/D.
- Visitas comparables / totales por especie: caesarea 102/103, aereus 90/90,
  edulis 65/67, pinophilus 84/86, deliciosus 74/76. Las siete visitas restantes
  constan como `temporal_model_unavailable`; no son un fallo del trabajo.
- Artefacto de 567094 bytes, SHA-256
  `aa1ee08dc8a3fdc3bc435fe1ab6d3eae41e363eb1a7ca0f3ea81e022b93fb87c`,
  coincidente con el recibo de HA. Auditoría privada en
  `tmp/jobs/release-ha-0.2.337/local-job-audit.json`.

HA local y worker reconstruidos/recreados. Comparación de SHA-256 de siete
archivos efectivos de HA y cuatro de worker correcta. La huella del procedimiento
coincide en repositorio y ambos contenedores:
`a8b31f5b7be370026a8d16fd3bf1e5ebf06071cd53c46e89091a52e826e70421`.
La huella de productores de variables permanece
`f2031581c6ef56c751fe002d6c614a5c3ea237194a7964fe1c33f9a00a3b05f2`.

El worker conserva las huellas de sus dos configuraciones de coordinador y
los límites de 4 CPU / 8 GiB. Fuentes privadas de observaciones conservadas.
Compatibilidad revisada con el productor v2 de HA 0.2.336
`ba26a72beb218bb81d5b41ac8b95269c358b8aae9a32d2434ba9f97a4521b561`:
no cambia el cálculo numérico; la prueba de entrega mantiene las identidades
solicitadas con reproducción y ajuste duplicados prohibidos. Otros productores
no revisados siguen rechazados.

Evidencia privada: `tmp/jobs/competing-species-20261011/`, con `tests.log`,
`browser.json`, capturas, logs de construcción y `local-verification.json`.
