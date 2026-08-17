# Ciclo de vida persistente de versiones ML micológicas

Estado: **IMPLEMENTADO EN LOCAL; NO DESPLEGADO**.

Este contrato separa cuatro conceptos que no deben volver a mezclarse:

- una **versión biológica** (`altitude_v2`, `biology_v3`, `biology_v4`, ...);
- sus **contratos temporales** (`fixed_gap_7d_*` y `lag_event_*`);
- los **seis estimadores ML** comparados dentro de cada especie y contrato;
- una **generación inmutable** de benchmark o de modelos, producida a partir de
  unos inputs concretos.

La fuente de verdad declarativa es
`mushroom-data/mushroom_ml_version_registry.json`. El código no contiene una
lista cerrada de V2/V3/V4 ni decide sus estados por nombre.

## Procedimiento de diez puntos

1. Registrar cada versión una sola vez con identificador, contratos, documento
   y contrato de identidad de sus inputs.
2. Mantener exactamente una versión `active` **solo como puntero técnico del
   runtime**; no significa validada, aceptada, científicamente preferible ni
   ganadora. Las demás permanecen disponibles como candidatas comparables.
3. No borrar una versión al desactivarla. Pasa a `reference` y conserva sus
   generaciones con retención permanente.
4. Construir cada benchmark con su contrato propio, sin reinterpretar después
   sus columnas ni sus targets.
5. Comparar versiones únicamente sobre observaciones y horizontes comunes, con
   el mismo target y la misma partición.
6. Informar resultados por versión, contrato temporal, especie y estimador. No
   promediar Brier entre especies: el resumen transversal solo cuenta
   victorias, empates, derrotas y contextos no evaluables.
7. Archivar cada benchmark o conjunto de modelos en un directorio identificado
   por contenido, junto a manifiesto, hashes e identidades de entrada. Una
   generación nueva se añade; nunca reemplaza a la anterior.
8. Permitir que una versión de referencia vuelva a ejecutarse, compararse o
   reactivarse usando una generación compatible. “No operativa” no significa
   eliminada ni abandonada.
9. Promover solo una generación `trained_model` concreta cuyo gate figure como
   `passed`. Un benchmark, una propuesta o un modelo no evaluado no puede
   convertirse en activo mediante un simple cambio de estado.
10. Hacer rollback cambiando la generación/version activa, no reconstruyendo el
    pasado ni renombrando artefactos. La historia de activaciones conserva la
    versión anterior, la nueva y la generación elegida.

## Huellas de `known_sites`

El SHA-256 del fichero completo se conserva porque permite demostrar qué bytes
se usaron. No es, sin embargo, una prueba adecuada de compatibilidad predictiva:
también cambia al editar un nombre, una nota o cualquier campo de interfaz.
Lo mismo sucede con el hash bruto del artefacto de features de entrenamiento:
en bundles nuevos queda como procedencia y no como veto de inferencia.

Cada versión declara en el registro qué campos de `known_sites` afectan a sus
variables. El motor genera:

- una huella semántica global;
- una huella independiente para cada área;
- el hash bruto completo como procedencia, sin usarlo como veto cuando existe
  el contrato semántico.

Consecuencias:

- cambiar nombre, descripción o notas no invalida modelos;
- cambiar geometría, punto representativo, área, archivo o altitud invalida las
  áreas afectadas según el contrato de esa versión;
- añadir una microárea en un área existente invalida esa área, porque puede
  cambiar la lluvia IDW media y la altitud representativa;
- añadir un área nueva no invalida las huellas de áreas ya existentes. El
  modelo general puede predecirla si dispone de sus variables, aunque esa área
  no estuviera en el snapshot de entrenamiento;
- incorporar los cambios a un entrenamiento futuro exige regenerar las
  variables afectadas, pero no se reentrena solo porque hayan cambiado bytes
  irrelevantes.

Los bundles antiguos, que solo guardan el hash bruto, siguen validándose con la
regla estricta heredada. Los bundles regenerados con el nuevo contrato usarán
la identidad semántica por área. Un bundle comparativo incompatible queda
marcado como no disponible con un motivo legible; no bloquea la predicción
activa. Una incompatibilidad del modelo activo sí debe impedir predecir.

## Componentes locales

- `rainmapper_core/mushroom_ml_version_registry.py`: validación, persistencia
  atómica, registro genérico, archivo inmutable y promoción con gate.
- `rainmapper_core/mushroom_ml_input_identity.py`: huellas declarativas globales
  y por área.
- `rainmapper_core/mushroom_ml_biology_v3_evaluation.py`: comparación emparejada
  de un número arbitrario de versiones.
- `scripts/evaluate-mushroom-ml-versions.py`: CLI genérico con argumentos
  repetibles `VERSION_ID=benchmark.json`.
- `scripts/preserve-mushroom-ml-generation.py`: archivado local aditivo por
  patrones, con manifiesto, hashes, identidades y gate de promoción.
- `rainmapper_core/mushroom_ml_comparison.py`: aislamiento de bundles sombra
  ausentes, corruptos o incompatibles.

La integración local mantiene V2--V6 en un lote comparativo no operativo con el
mismo estatus experimental. Ninguna de ellas es actualmente válida, aceptada,
preferida, promovida o ganadora. V2 aparece en la tarjeta superior únicamente
por cronología: fue la primera implementación conectada a esa tarjeta. No es un
baseline científico y su posición visual no puede usarse como criterio de
calidad o de promoción.

El Predictor debe mostrar para todas las versiones el rendimiento hold-out
específico de cada especie, contrato, horizonte y estimador, la predicción
actual individual, las extrapolaciones fuera de dominio y las cautelas propias
antes de interpretar una probabilidad. La vista comparable se organiza por
versión, con filas de perfil+contrato+horizonte y columnas de algoritmos. El
ranking transversal sigue evaluando calidad antes que acuerdo y nunca promedia
Brier entre especies.

Una consulta por área solo es válida cuando esa especie tiene observaciones en
el área. Al cambiar de especie se elimina el área seleccionada previamente. El
servicio normaliza una combinación incompatible a `todas las áreas`, incluso si
llega mediante URL, una respuesta preparada o una caché, y la interfaz no debe
renderizar una predicción especie+área inexistente.
