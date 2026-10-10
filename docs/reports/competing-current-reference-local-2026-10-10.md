# Referencia actual en predicciones retrospectivas · 10/10/2026

El usuario autoriza que el mapa use la última preparación compatible para elegir
A/B/C/D y mostrar sus Iₖ, incluidos los de la selección habitual. La fecha y
coordenadas consultadas siguen determinando las entradas del IFF. Aplica tanto
al modo histórico como a «Comprobar predicción».

`PointModelRuntime.predict` usa `prediction-competing.json.cutoff` para el ranking
y la comparación; conserva `request.start_date` para resolver y calcular la semana.
La respuesta incorpora `selection_date`; HA y visor validan la comparación contra
esa referencia y el K solicitado. El visor muestra la fecha de referencia. Si no
existe comparación para ese K, sigue pendiente: ningún clic lanza trabajos.

La capability del mapa `map_competing_selection_v3` evita entregar el contrato
nuevo a un coordinador que rechazaba notas posteriores a la fecha del punto.
En un HA anterior, Competing selection puede recurrir al cálculo local mediante
el fallback ya existente hasta actualizar HA. No se cambian coordinadores.

Los acumulados históricos, sus lectores y su generación permanecen intactos.
La huella científica sigue siendo
`02c86d9fa9133c91f8424effeced1e4d3bb1d9f2e20bfe16bfbf02f3e347be0d`.
No se han ejecutado selección/comparación, entrenamientos ni precálculos.

## Validación

- 86 pruebas dirigidas correctas, más una prueba adicional del contrato: 87
  distintas. Incluyen consultas históricas con/sin observación, mismo IFF habitual,
  corte meteorológico antiguo, K pendiente, enlace de fechas y workers antiguos.
- Navegador compartido: correcto, incluida comparación preparada posterior a la
  consulta, ganadores, configuración desactivada y presentación móvil 320/390 px.
- Reconstruidas y recreadas imágenes locales HA y worker. Antes de recrear el
  worker se comprobó `idle` en ambos carriles. Código efectivo igual al worktree:
  seis archivos en HA y cuatro en worker. Configuración efectiva y ambos archivos
  de coordinadores con las mismas huellas antes/después; worker sano e idle.
- Consulta real en HA local al punto del usuario (Olvan, 17/09/2019): IFF habitual
  `0.536884` (54/100), idéntico con/sin Competing selection. Los cuatro criterios
  devuelven predicciones y la comparación usa referencia 10/10/2026, 90 visitas,
  54 favorables. I₄: habitual −19,84; A −11,11; B/C −14,02; D −14,29. A gana.
- Archivo de evidencia idéntico antes/después; no se transporta su histórico
  completo. Observaciones privadas también conservadas.

Evidencia privada: `tmp/jobs/competing-current-reference-20261010/` contiene
`tests.log`, `browser.log`, logs de build, `verification.json`, `point-check.json`
y los scripts de verificación. Un primer auxiliar apuntaba a `local.json`, cuya
ruta antigua de modelos no existe; se corrigió el auxiliar para usar `config.json`
sin modificar configuración operativa. La prueba final terminó correctamente.

Tras esta validación local, el usuario autorizó «publicamos HA». El cambio se
publicó en [HA 0.2.335](release-ha-0.2.335-2026-10-10.md), con smoke completo
correcto y tags/plataformas comprobados en GHCR. No se ha instalado ni modificado
HA real desde aquí; su instalación y prueba quedan a cargo del usuario.
