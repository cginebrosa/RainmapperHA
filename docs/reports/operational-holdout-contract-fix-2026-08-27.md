# Corrección del hold-out operativo y validación local — 2026-08-27

## Alcance

Trabajo exclusivo en el laboratorio local, sin Tailscale, sin tocar HA real ni
el worker normal, sin cambiar retención y sin bump, publicación, instalación o
release. El worker local siguió ejecutándose dentro de la imagen HA local; no
se creó ningún worker adicional.

## Síntoma y causa comprobada

El batch local `local_operational_20260826T175244Z` había terminado sus 714
ajustes, pero su catálogo de calidad contenía perfiles completos con
`n_test = 0` y sin probabilidades hold-out:

- `altitude_v2/common_idw`;
- `biology_v3/core`;
- `biology_v4/climatic_balance`;
- `biology_v4/extended_weather`.

Los benchmarks materializados pueden conservar el contrato temporal en
`sample_id` sin repetirlo en `metadata.temporal_contract_id`. Al usar el
catálogo de tuning congelado, el evaluador intentaba buscar decisiones con un
contrato vacío o con el identificador interno de materialización. La excepción
se absorbía por estimador, las probabilidades quedaban vacías y la promoción
solo comprobaba que el perfil apareciese en el catálogo, no que tuviera casos
evaluados. Esto explica las abstenciones generalizadas del Predictor; copiar
meteorología reciente no podía reparar un catálogo de calidad ya inválido.

## Cambio estructural

1. `mushroom_ml_holdout.evaluate_dataset` recupera la identidad temporal de la
   metadata o del `sample_id` y la resuelve mediante el catálogo de tuning al
   contrato operativo de versión/perfil. Las filas de salida registran ese
   contrato operativo resuelto. Si hay catálogo de tuning pero no identidad de
   origen, el proceso falla explícitamente.
2. El job multiversión valida, antes de abrir el progreso y antes de entrenar o
   escribir un batch, que cada perfil seleccionado tenga al menos una entrada
   con `n_test > 0`. Un catálogo sin probabilidades ya no puede llegar a
   promoción.
3. El recomendador de la pantalla `Esta semana` excluye las abstenciones de la
   clasificación. Si todo se abstiene, muestra ausencia de señal en vez de
   presentar la primera especie —por orden interno— como la mejor predicción.
   Este filtro ocurre después del cálculo existente y no añade fits, lecturas o
   peticiones al Predictor.

No se añadieron módulos nuevos: se corrigieron tres módulos existentes y se
ampliaron sus pruebas.

## Evidencia dirigida previa al ciclo completo

- V4 `extended_weather`, contrato fijo y grupos de 7 días: 126/126 filas con
  probabilidades, 752 probabilidades, seis estimadores disponibles para
  Edulis; 6,25 s.
- V2 común, V3 físico y los dos perfiles V4, contratos fijo/lag y grupos 7/14:
  8.320 filas; 2.080/2.080 filas con probabilidades y 12.472 valores por
  perfil; 89,56 s.
- V3 core: 2.080/2.080 filas con probabilidades, 12.472 valores; 24,11 s.

Estos tiempos son ajustes temporales de evaluación dentro del reentrenamiento,
no coste del Predictor ni modelos publicados.

## Ciclo local completo corregido

Operación `6BAUyBn6P2Exoq2e`, snapshot
`sha256:619040b386bd90632db32b2e93dd1b4fc0ecb099e195d83e8d8ecc466738204a`:

- inicio: `2026-08-27T07:19:16.832+00:00`;
- fin: `2026-08-27T07:29:08.405+00:00`;
- total: **591,561 s (9 min 51,561 s)**;
- margen respecto al máximo de 600 s: **8,439 s**;
- reconstrucción: 98,592 s de cálculo y 1,834 s de verificación;
- ML v0: 24,982 s y 0,079 s de verificación;
- evaluación hold-out V2--V5: 162,672 s;
- evaluación hold-out V6: 26,031 s;
- entrenamiento final por versión: V2 12,887 s, V3 25,760 s, V4
  24,995 s, V5 32,911 s y V6 21,656 s;
- instalación y promoción: 3,270 s;
- 714/714 ajustes, cero fallos y 714 artefactos;
- 27.296 filas hold-out;
- 1.316.397.905 bytes leídos, 334.192.577 escritos, 5.799 ficheros
  leídos, 891 escritos, 2.473 hashes sobre 816.837.017 bytes, 826 copias por
  302.601.885 bytes y 97 `fsync`;
- cero peticiones de red y cero persistencias de cola: fue el ejecutor local en
  la misma imagen.

Los hashes físicos recalculados coinciden con el manifiesto:

- hold-out: `c03e470a5a7440fabec2f0a7164f24b91c44216777aa319b941235dcbfda8455`;
- calidad: `7376db3168df4425520695f59914493a4f16cc68c64dfe78214bdc8860b0eab3`;
- tuning: `fadaf3d84b6d501cfac664e86d0c851c21c878a58f1177a6177d8862bfc27ac5`.

El registro local apunta a las cinco generaciones del batch
`local_operational_20260827T072659Z`; todas tienen gate
`verified_operational_batch` aprobado y registran como generación anterior el
batch del 26 de agosto.

## Cobertura de calidad resultante

Los cinco perfiles afectados tienen ahora 431 entradas con `n_test > 0` de
432 y suman 12.472 casos evaluados de 12.480 cada uno. La entrada restante
corresponde a una partición sin casos evaluables, no a un perfil vacío. Los
perfiles V5 y V6 también superan la nueva barrera; ninguno queda con todas sus
entradas a cero.

## Pruebas

- 10 pruebas dirigidas del hold-out, barrera de promoción y recomendador;
- 32 pruebas vecinas de hold-out, tuning, calidad, preparación, trainer,
  informes y orquestación;
- suite completa: **1.039 pruebas, cero fallos, 50,950 s**;
- reconstrucción de la imagen HA exclusivamente local y arranque sano;
- ciclo completo descrito arriba.

## Interpretación y riesgos

Las mediciones anteriores de 534,571 s en frío y 473,654 s en caliente no son
líneas base válidas de aceptación semántica: parte de su menor coste procedía
de omitir evaluaciones hold-out. El ciclo corregido sí cumple integridad y el
objetivo de 10 minutos, pero con solo 8,439 s de margen. Debe repetirse una
medición caliente antes de atribuir estabilidad estadística al resultado.

La mayor fase individual sigue siendo la evaluación hold-out V2--V5
(162,672 s), seguida de la construcción compartida V3 fija (65,595 s). Una
optimización posterior debe atacar esos costes medidos sin volver a reducir la
cobertura. La barrera nueva evita que una regresión equivalente vuelva a
promocionarse silenciosamente.

## Release coordinada autorizada

Tras presentar la validación local, el usuario autorizó la release coordinada:

- HA `0.2.268` publicado en GHCR con tags `0.2.268` y `latest`, ambos con
  digest `sha256:cc94b6b272c7256ab4796358fcdbb20f65e731e7707e5349a42dadd52fb27c95`
  y manifests `linux/amd64` y `linux/arm64`;
- worker `1.0.19` construido como imagen local `linux/arm64`, ID
  `sha256:ea2927754c3d0f5a5f81dbe58407163a6cbe038dfc7b7d3e1f8c72ffa1ea039f`;
- paquete privado
  `rainmapper-worker-1.0.19-arm64.tar`, 293 MiB, SHA-256
  `8ae143e2973f99536103f0431af5bd0420287258affaff597ceefcf6ab8d6a67`.

El smoke de release pasó 1.039 pruebas y el test de empaquetado del worker pasó
sus siete casos después del bump. Esta publicación no instaló HA ni reemplazó
o reinició el worker normal.
