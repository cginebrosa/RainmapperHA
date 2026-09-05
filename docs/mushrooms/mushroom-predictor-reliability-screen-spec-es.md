# Pantalla de Fiabilidad del Predictor

Estado: especificación acordada; implementación aplazada hasta validar en local
y desplegar en HA real el selector fiable, el entrenamiento y el precálculo ya
construidos.

## Objetivo

Añadir al Predictor una pestaña independiente llamada **Fiabilidad** que permita
entender, sin ejecutar predicciones, qué candidato ha demostrado mayor
fiabilidad para cada especie, área y horizonte operativo y por qué fue elegido.

La pantalla será una lectura del `quality-audit-catalog.json` sellado durante el
entrenamiento. No recalculará métricas, no ordenará candidatos con una política
distinta y no modificará la selección operativa publicada.

## Separación respecto a Historial

- **Historial** conserva inicialmente su función actual: revisar observaciones
  pasadas y sus resultados retrospectivos.
- **Fiabilidad** explica la evaluación hold-out del entrenamiento, la selección
  sellada y las alternativas comparables.
- No se presentarán las fichas agregadas de Historial como si resumieran las
  filas de Fiabilidad: usan unidades y poblaciones diferentes.
- La retirada o simplificación futura de Historial será una decisión separada,
  posterior a probar Fiabilidad con datos reales.

## Navegación principal

La pestaña tendrá, en este orden:

1. selector de especie;
2. selector de área;
3. siete pastillas de horizonte: `Día 1` a `Día 7`;
4. resumen del candidato seleccionado;
5. evidencia que justifica la selección;
6. ranking completo de candidatos aplicables;
7. diagnósticos avanzados desplegables.

Las pastillas representan horizontes, no fechas de calendario. Cada una debe
mostrar o explicar también «Predicción a N días». Al cambiar de pastilla solo se
leen datos ya cargados o indexados del catálogo; no se lanza ningún cálculo.

## Selección de especie y área

- La especie inicial será la última usada por el usuario o la primera disponible.
- El área mostrará únicamente áreas operativas de esa especie.
- Si existe ámbito territorial en el catálogo, se muestra su ranking y ganador.
- Si no existe evidencia territorial, se mostrará claramente:
  «No hay auditoría suficiente para esta área; se usa la evidencia global de la
  especie para elegir el candidato».
- En fallback, la pantalla diferenciará:
  - candidato elegido con evidencia global de especie;
  - futuras probabilidades calculadas con meteorología y features del área.
- Para cualquier ganador mostrará, una junto a otra, la evaluación territorial
  y la evaluación global de especie del mismo candidato. No sustituirá una por
  otra ni comparará métricas de candidatos diferentes.
- Una abstención no se etiquetará nunca como fallback ganador.

## Resumen del candidato seleccionado

Para la especie, área y día elegidos se mostrará:

- estado: ganador territorial, fallback de especie o abstención;
- versión;
- perfil y ventana meteorológica;
- familia y contrato temporal exacto;
- horizonte;
- estimador;
- métrica principal `Fiable cuando dice ir`, en porcentaje y fracción `x/x`;
- observaciones hold-out únicas;
- floradas o grupos temporales de 14 días;
- límite inferior de Wilson;
- fecha, snapshot y publicación del entrenamiento.

El resumen rotulará los dos ámbitos como `Evidencia del área` y `Evidencia
global de la especie`, y señalará aparte cuál de ellos decidió la selección. En
cada ámbito mostrará Wilson, acierto observado `x/x`, observaciones y floradas;
si no existe evaluación se verá `no disponible`, y si existe pero no superó
los gates se verá `no elegible` con su motivo.

No se mostrará una «probabilidad actual» en esta pantalla. La probabilidad para
una fecha concreta pertenece a `Esta semana`, `Por especie` y `Consultar fecha`.

Si el estado es abstención, se explicará que ningún candidato superó los gates
objetivos. No se elegirá la versión preferida ni el porcentaje bruto más alto
como sustituto.

## Ranking de candidatos

El ranking mostrará una fila por candidato individual y nunca sumará métricas
de candidatos distintos. Cada fila identificará sin abreviaturas ambiguas:

- versión;
- perfil/ventana;
- contrato temporal y familia;
- horizonte;
- estimador;
- elegible o descartado;
- rango dentro de los elegibles;
- motivo de exclusión, cuando corresponda;
- `Fiable cuando dice ir`;
- `Encuentra favorables`;
- `Fiable cuando dice no ir`;
- `Encuentra desfavorables`;
- observaciones, floradas y abstenciones;
- Wilson, Brier frente a prevalencia, ROC-AUC, calibración y cobertura.

Todas las proporciones se mostrarán como porcentaje y fracción. Si el
denominador es cero se mostrará `—`, no `0 %`.

El orden inicial será el ranking sellado cuya prioridad principal es
`Fiable cuando dice ir`. Podrán ofrecerse órdenes informativos adicionales:

- `Encuentra favorables`;
- `Fiable cuando dice no ir`;
- `Equilibrio`.

Cambiar el orden visual no cambia el ganador operativo, que permanecerá
destacado y etiquetado como «seleccionado durante el entrenamiento».

## Tooltips obligatorios

Todo concepto técnico tendrá una ayuda breve en lenguaje normal y, cuando sea
útil, un detalle ampliado. Como mínimo:

- Día N / horizonte;
- fiabilidad cuando recomienda ir;
- favorables encontrados;
- fiabilidad cuando recomienda no ir;
- desfavorables encontrados;
- observaciones hold-out;
- floradas de 14 días;
- Wilson;
- Brier y prevalencia;
- ROC-AUC;
- calibración;
- cobertura y abstención;
- ganador territorial;
- fallback de especie;
- versión, perfil, ventana, familia temporal, contrato, horizonte y estimador;
- cada motivo de inelegibilidad.

Los tooltips no deberán presentar Wilson como probabilidad de la fecha ni una
florada como una única observación.

## Fuente de datos y validación

La pantalla leerá el `quality-audit-catalog.json` del mismo batch instalado que
aporta el `quality-catalog.json` operativo. Antes de mostrar datos validará:

- esquema `1.0` del catálogo de auditoría;
- SHA-256 declarado en el manifiesto;
- coincidencia de `snapshot_id` y `selection_id` con el catálogo compacto;
- split oficial `fruiting_groups_14d`;
- coherencia del rango 1 con el ganador sellado;
- completitud de los siete días de cada ámbito disponible.

El catálogo ampliado vive en `/media`, se transporta con la publicación runtime
y no se copia a `/share`. La UI no leerá hold-outs crudos ni modelos para
reconstruir información ausente.

## Estados de error y ausencia

- Catálogo ausente: «Este entrenamiento no incluye auditoría de fiabilidad».
- Esquema incompatible: «La auditoría requiere actualizar y reentrenar».
- Digest o identidades incoherentes: fallo cerrado, sin mostrar ranking parcial.
- Área sin ámbito territorial: evidencia de especie separada y explicación de
  fallback, si existe.
- Especie/día sin ganador: abstención y motivos de los candidatos descartados.
- Catálogo válido pero sin alternativa aplicable: mensaje explícito, sin
  inventar comparaciones.

## Rendimiento y seguridad operativa

- Abrir o navegar por Fiabilidad no ejecuta inferencia, entrenamiento,
  precálculo ni llamadas al worker.
- El catálogo se valida una vez por identidad de publicación y puede mantenerse
  en una caché acotada.
- Los filtros y órdenes deben operar sobre el ámbito solicitado, sin renderizar
  las 18.220 evaluaciones de una vez.
- La pantalla es estrictamente de solo lectura; no ofrece overrides ni cambia
  `preferred_version_id`.
- Debe funcionar aunque no exista todavía un SQLite de precálculo, siempre que
  la publicación runtime y el catálogo de auditoría sean válidos.

## Accesibilidad y presentación

- Las pastillas deben ser botones accesibles por teclado, con estado activo y
  `aria-label` descriptivo.
- Los colores no serán el único indicador de ganador, abstención o descarte.
- Tablas amplias tendrán versión compacta para móvil y detalle desplegable.
- Identidades técnicas completas podrán copiarse desde el detalle, sin dominar
  la vista principal.

## Pruebas de aceptación

1. Cambiar especie, área o Día N no ejecuta predicciones ni crea jobs.
2. El ganador visible coincide exactamente con el catálogo compacto.
3. Una abstención de especie aparece como abstención, nunca como fallback.
4. Todo ganador muestra evidencia territorial y global del mismo candidato;
   un área sin auditoría territorial muestra `no disponible` y mantiene la
   evidencia global separada.
5. Porcentajes, fracciones, observaciones y floradas coinciden con el catálogo.
6. Cambiar el orden informativo no cambia el ganador destacado.
7. Los siete horizontes están completos y explican su significado.
8. Todos los términos enumerados tienen tooltip y navegación por teclado.
9. Un digest, esquema o `selection_id` incorrecto falla cerrado.
10. La pantalla funciona en HA local y real sin cálculo científico online.
11. Una pareja futura declarada posible pero sin observaciones usa únicamente
    el fallback de su especie, calcula con features locales y no inventa
    fiabilidad territorial.

## Secuencia de implementación acordada

1. Terminar la prueba local del entrenamiento, selector, precálculo y vistas
   ordinarias ya implementados.
2. Con autorización explícita, desplegar esa base en HA real y verificarla.
3. Solo después implementar la pestaña Fiabilidad sobre el contrato ya
   desplegado.
4. Probarla en local con varias especies, áreas, fallbacks y abstenciones.
5. Decidir separadamente si Historial se conserva, simplifica o retira.

La creación de esta especificación no autoriza ningún bump, build, publicación
ni cambio en HA real.
