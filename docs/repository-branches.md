# Ramas y carpetas de trabajo

Separación del LLM realizada el 04/11/2026; organización simplificada el 07/11/2026
por indicación del usuario.

| Trabajo | Rama | Carpeta desde la raíz del repositorio |
| --- | --- | --- |
| Rainmapper y correcciones destinadas a HA | `inicial` | La carpeta raíz habitual `RainmapperHA/` |
| Asistente LLM local, MCP, corpus, RAG y experimentos | `feature/local-llm` | Rama guardada; sin carpeta de trabajo adicional |

`origin` es el remoto de GitHub. La rama de publicación es `inicial`, cuyo
upstream es `origin/inicial`; la rama antigua `main` no se utiliza para las
releases. Queda un solo checkout: la carpeta raíz. Los worktrees auxiliares de
AEMET y Wunderground se han retirado después de conservar y verificar su contenido;
también se ha podado la referencia del worktree temporal antiguo que ya no existía.
Las ramas antiguas se conservan; no se han borrado commits.

El flujo habitual es trabajar en `inicial` y abrir una rama cuando se acuerde
un trabajo largo. Para retomar el LLM se cambia de rama en esta misma carpeta,
después de guardar los cambios pendientes de la principal. No crear otro worktree
como organización permanente sin acordarlo con el usuario.

## Rama principal

En el momento de la separación, `inicial` y `origin/inicial` apuntan a
`612f162b2ab22e2ae06ad38375657dde841acc8c` (HA 0.2.340). Incluyen el refresco
diario de AEMET de 0.2.339, la recuperación Wunderground de 0.2.340 y las
excepciones manuales Meteoclimatic de 0.2.338.

La corrección común de coordenadas se publica en la release **0.2.341** desde
`inicial`, tras aceptar el usuario la validación operativa local. Incluye los
cuatro adaptadores, archivo Parquet/CSV, resumen agrupado y revisión de traslados
en el mapa. [Contrato](weather-coordinate-protection-es.md) y
[validación](reports/weather-coordinates-local-2026-11-04.md).
La imagen multi-arch está verificada en GHCR. El 07/11/2026 el usuario confirmó
que la había instalado y había funcionado en HA real; no se realizó una
inspección remota independiente.
[Publicación y validación](reports/release-ha-0.2.341-2026-11-07.md).

## Rama del asistente

El commit `8984b092174feb27f21fccbc070539fdd8999cd5` conserva el trabajo local
anterior: 480 archivos de código, pruebas, corpus, evaluaciones, configuración
sin credenciales y documentación de trabajo. Se ha comprobado que los contenidos
guardados coinciden con los archivos previos, incluidos los enlaces simbólicos.
El commit es un punto de conservación WIP, no una aceptación funcional nueva.
Conserva también el contexto histórico de sesiones que trataban varios asuntos.

La base del asistente sigue siendo HA 0.2.338. Antes de integrar futuros cambios
del asistente habrá que reconciliarlo con `inicial` y validar los componentes
afectados; no fusionar esta rama en la principal para obtener arreglos
meteorológicos que ya están publicados. Su punta sigue en `c20d3c6d`, con las
notas de separación posteriores al snapshot. No se ha hecho push de esta rama.
Los modelos, runtime y credenciales locales permanecen en el disco y fuera del
commit. Sus exclusiones se conservan también en `.git/info/exclude`, porque los
`.gitignore` de `assistant/`, `mcp/` y `.continue/` pertenecen a la rama LLM.

HA local ejecuta ahora la candidata de `inicial` con el compose base, sin la
extensión MCP del LLM. Se han conservado claves, volúmenes y agenda desactivada.
No se ha recreado el contenedor MCP separado ni el worker.

## Datos locales de observaciones

Durante la separación se conservaron intactos en el checkout de
`feature/local-llm`, fuera del commit del asistente:

- `mushroom-data/mushroom_observations.json`: archivo ya versionado con cambios
  locales; 441 observaciones frente a 49 en la versión de Git examinada.
- `mushroom_observations.json`: archivo sin versionar con 520 observaciones.

El 04/11 el usuario autorizó versionar ambos archivos. Se copiaron sin alterar
su contenido al checkout de `inicial` para incluirlos en el commit final del
trabajo operativo; no se añaden al commit del LLM ni a `.gitignore`.
Al devolver la carpeta raíz a `inicial` se restauraron esos mismos bytes.
Huellas SHA-256 verificadas antes y después del traslado:

- `mushroom-data/mushroom_observations.json`:
  `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
- `mushroom_observations.json`:
  `a7b63784ff444d73ab84824577788c1414630693359df454e46595ff277f9e8f`.

Son dos snapshots distintos: comparten 431 identificadores, con 16 registros
compartidos diferentes; el primero aporta 10 identificadores exclusivos y el
segundo 89. Ambos JSON se leen correctamente y no contienen identificadores
duplicados ni ausentes. Se conservan separados, sin fusionarlos ni asumir que
el archivo con más filas sustituye íntegramente al otro.

## Verificación de la separación

Se compararon por SHA-256 los 482 archivos pendientes: los 480 guardados y los
dos JSON de observaciones. Ninguno cambió durante la separación. Los archivos
LLM/MCP nuevos no están en el árbol de `inicial`. No se ejecutó entrenamiento,
precálculo ni se reinició ningún servicio.

`git diff --cached --check` del snapshot detectó espacios y líneas vacías que
ya estaban en las fuentes y transcripciones. Se conservaron literalmente para
no alterar corpus ni evidencias congeladas; no se declara ese control superado.
La documentación nueva de esta separación se comprueba por separado.

El 07/11 se verificaron por SHA-256 los 28 archivos pendientes al trasladarlos
a la raíz, incluidas las observaciones. Las puntas de ambas ramas no cambiaron.
Los stashes transitorios del traslado se eliminaron sólo después de verificar
la restauración. Se comprobó la conservación de los 90.311 archivos locales
ignorados fuera de los worktrees; no se borraron modelos, credenciales ni datos.
