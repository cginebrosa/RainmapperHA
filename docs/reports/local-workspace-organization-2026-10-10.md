# Reorganización local — 10/10/2026

Solicitada por el usuario para separar pruebas, cachés y runtime de los datos
persistentes, manteniendo funcionales las rutas escritas en scripts e informes.
No se eliminan archivos ni se lanzan estudios, entrenamientos o trabajos operativos.

## Resultado

- 106 entradas trasladadas a sus destinos clasificados en `local/`.
- 13.856 archivos previos inventariados y comprobados tras los movimientos.
- 329 SQLite/Parquet derivados de pruebas quedan accesibles en `local/cache/`,
  con enlaces duros desde cada prueba: mismo contenido físico, sin duplicación.
- 43 scripts auxiliares corrigen sus expresiones para encontrar la raíz del
  repositorio. Se guardan los originales y sus hashes. Fuentes archivadas por
  hash y fixtures permanecen sin modificaciones.
- 110 accesos antiguos se conservan para compatibilidad. Las nuevas pruebas van
  en `tmp/jobs/`; esos accesos antiguos no son temporales eliminables.
- Se corrigen tres comprobaciones de confinamiento de herramientas locales para
  comparar rutas resueltas en ambos lados. No se amplían sus permisos de escritura.
- `local/` queda excluido de Git y del contexto Docker.

El índice privado `local/evidence/INDEX.md` identifica cada conjunto y su
procedencia. Los conjuntos históricos se conservan completos en esta fase;
reducirlos a evidencia mínima queda pendiente de revisión, sin borrado automático.

## Comprobaciones

- Inventario posterior: 13.856 archivos; identidad de fichero, tamaño, fecha y
  enlaces comprobados, 11.559 hashes de archivos pequeños sin cambios y 43
  originales de scripts corregidos conservados. Cero errores.
- Desde HA local: las 439 rutas de compatibilidad y acceso a cachés existen;
  `/config/www` disponible. El chequeo inicial se efectuó con enlaces simbólicos
  a cachés; después se convirtieron en enlaces duros, comprobando mismo inode.
- 23 pruebas dirigidas pasan con `.venv/bin/python -B -m unittest
  tests.test_prediction_model_selection_resources
  tests.test_prediction_research_protocol tests.test_prediction_model_selection_d`.
  La primera invocación con Python del sistema no pudo importar pandas/joblib;
  no se instalaron dependencias y se repitió con el entorno del proyecto.
- Sintaxis del script del navegador de observaciones correcta (`node --check`).
- `git diff --check` correcto. Rutas privadas verificadas como ignoradas por Git.
- HA local recreado únicamente para aplicar montajes, con la misma imagen
  `sha256:6de0a6409cd2b26255fa320385a924c1ed82699326c94f28a75252e2af29e530`.
  Sus 18 variables de configuración comparadas mantienen las mismas huellas;
  respuesta HTTP 200 en `127.0.0.1:8101`.
- Worker sin reconstrucción ni reinicio: imagen
  `sha256:703e499d07caa2bee2ba1316602a30dd94834e95bd6c0a2e4b66a50b38a40b66`.
  `/health` informa ambos carriles libres y cachés válidas en la comprobación.
  Huellas de ambos archivos de coordinadores idénticas antes y después.

No se han reejecutado los scripts archivados: varios realizan acciones externas
o cálculos costosos. Esta validación verifica la reorganización y sus rutas,
no renueva la validación científica de estudios antiguos.

## Evidencia y continuidad

Recibos privados: `local/evidence/2026-10-10-local-organization/`:
`plan.json`, `receipt.json`, `verification.json`, copias de scripts y huellas de
configuración (sin valores secretos). Mapa de accesos: `local/layout.json`.

Normas y conservación: [organización local](../local-workspace-layout-es.md).
El usuario puede ejecutar Selección y comparación; el cierre documental no
requiere más reinicios ni cambios de rutas operativas.
