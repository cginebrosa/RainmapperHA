# Organización local del workspace

Organización aplicada el 10/10/2026. Las rutas son relativas al repositorio.

| Ruta | Contenido y conservación |
| --- | --- |
| `docker-data/` | Estado persistente de la aplicación y diagnósticos que escribe el servicio. No limpiar como temporales. |
| `docker-media/`, `geography-sources/` | Multimedia y fuentes originales. No se mueven ni se eliminan mediante esta organización. |
| `local/runtime/` | Recursos requeridos por la instalación local. `mushroom-lab/config-www` se monta en HA local como `/config/www`. |
| `local/cache/` | Derivados reutilizables. Las cachés históricas trasladadas se conservan; requieren revisar regeneración y dependencias antes de purgarlas. |
| `local/evidence/` | Auditorías, mediciones, capturas y scripts privados. Los conjuntos anteriores se conservan completos en esta migración; su reducción es una revisión posterior. |
| `tmp/jobs/` | Nuevos trabajos temporales, cada uno en su propia carpeta. No guardar aquí fuentes únicas ni estado requerido al arrancar. |
| `docs/reports/` | Informes resumidos, aptos para versionar y sin datos privados. |

`local/` y `tmp/` están excluidos de Git y del contexto de construcción Docker.
El índice privado está en `local/evidence/INDEX.md`; el mapa de rutas en
`local/layout.json`. No añadir `local/` a una imagen de HA o worker.

## Compatibilidad de las rutas existentes

Las rutas anteriores de `tmp/` y los accesos históricos a auditorías en
`docker-data/` se conservan como **enlaces de compatibilidad**, sin duplicar datos.
No son temporales eliminables. Los logs e informes antiguos siguen describiendo
las rutas usadas cuando se ejecutaron. Los ficheros fuente archivados por hash
se conservan intactos; las correcciones de rutas de scripts auxiliares tienen
copias previas en el recibo privado de la migración.

HA local monta `local/` en `/app/local` y `/share/local`, de forma que los enlaces
relativos funcionan tanto desde `/app/tmp` como desde `/share/rainmapper`.
Esos montajes son exclusivos del laboratorio; no cambian el contrato de HA real
ni los coordinadores del worker. Al reproducir una comprobación antigua en un
contenedor desechable, montar el repositorio completo o también `local/` junto a
`tmp/`; montar únicamente una carpeta con enlaces deja sus destinos fuera.

Los SQLite/Parquet de las pruebas de rendimiento conservan además accesos por
enlace duro dentro de cada prueba: comparten los mismos datos con `local/cache/`
sin duplicar bloques, y su ruta resuelta permanece dentro del conjunto de prueba.
Para liberar esos datos algún día habrá que revisar ambos accesos; retirar sólo
uno no libera necesariamente espacio.

Los scripts que obtenían la raíz con un número fijo de `parents[n]` se adaptan
cuando esa expresión apuntaba al repositorio antes de la migración. Las
comprobaciones de confinamiento comparan rutas resueltas en ambos lados, sin
ampliar el conjunto de directorios autorizados.

## Nuevos trabajos y retención

- Crear temporales en `tmp/jobs/AAAA-MM-DD-nombre/`, con un README que identifique
  finalidad, responsable, estado y fecha de cierre. Un trabajo abierto o de estado
  desconocido nunca es candidato a limpieza.
- Al cerrar, guardar en `local/evidence/AAAA-MM-DD-nombre/` el resumen, comandos,
  revisión de código, mediciones finales y comprobantes necesarios. Evitar
  conservar todos los intermedios por defecto.
- Las cachés van en `local/cache/` con explicación de sus fuentes y regeneración;
  no aplicarles el mismo criterio de edad que a los temporales.
- Política propuesta para temporales cerrados: revisión a los 30 días. Los fallos
  pendientes, archivos únicos y enlaces de compatibilidad quedan excluidos.
  **Esta reorganización no activa borrados automáticos ni elimina archivos.**
- No seguir enlaces simbólicos ni sumar enlaces duros como si fueran copias
  independientes al inventariar espacio. El tamaño lógico no es espacio liberable.

No ejecutar los scripts archivados para comprobar una mudanza: algunos realizan
entrenamientos, subidas, limpiezas o escrituras. Validar rutas, sintaxis, huellas,
montajes y salud de los servicios; las ejecuciones operativas siguen su autorización
propia.
