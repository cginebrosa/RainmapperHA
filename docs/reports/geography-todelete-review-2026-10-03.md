# Revisión para retirar antiguos — 03/10/2026

El usuario confirma HA 0.2.331 instalada y funcionando. Solicita revisar si ya
pueden eliminarse los `-todelete`, incluido HA mediante los volúmenes montados.
La revisión inicial fue sólo de lectura; el borrado autorizado posteriormente
y sus mediciones están registrados al final. No autoriza otros trabajos operativos.

## Resultado local

| Carpeta | Archivos | Bytes lógicos | Bytes asignados a archivos |
|---|---:|---:|---:|
| `mushroom-GIS-todelete/` | 112 | 1.614.535.540 | 1.614.741.504 |
| `mushroom-map-GIS-todelete/` | 5.779 | 20.623.949.162 | 20.706.840.576 |
| Total | 5.891 | 22.238.484.702 | 22.321.582.080 |

Los bytes asignados se calculan con `st_blocks * 512`, deduplicando inodos;
`du -sk` añade una pequeña diferencia por directorios. No hay enlaces duros
múltiples en estas dos carpetas (`st_nlink=1` en todos sus archivos) ni symlinks.
La ganancia efectiva de espacio disponible se medirá tras borrar; esta cifra
no es una medición anticipada de espacio libre recuperado.

Los 5.891 archivos están relacionados con destinos conservados en
`geography-sources/inventory.json`. No hay destinos ausentes ni archivos nuevos
fuera del inventario. Revalidación contra la copia comprobada por SHA-256 del
28/09: tamaño/mtime actuales en ambos lados e inodo de los antiguos; 11.774 de
11.782 comprobaciones de metadatos sin cambios. Sólo se rehashean los ocho
archivos con metadatos distintos:

- Tres adaptaciones de README/herramientas coinciden con sus SHA posteriores
  documentados en `geography-sources/tool-adjustments.json`.
- Cinco `.DS_Store` difieren; son metadatos del Finder, no capas ni fuentes GIS.
- Ninguna diferencia pendiente en datos geográficos.

No se vuelven a leer ni hashear decenas de GB ya verificados. La verificación
actual es incremental; los SHA completos pertenecen a la copia del 28/09.

## Dependencias

- `git grep` y búsqueda literal en código/configuración: sin referencias a
  `-todelete` en código operativo. Exclusiones, documentación y pruebas sí lo citan.
- `docker inspect` de HA local y worker: ningún montaje de las carpetas antiguas.
  HA local monta `docker-media/rainmapper`; worker usa su volumen independiente.
- Ni fuentes ni geografía operativa local contienen symlinks a antiguos.
- Las raíces previas `mushroom-GIS/` y `mushroom-map-GIS/` siguen ausentes en el
  root del repositorio. La aceptación y pruebas se han realizado sin ellas.
- Los punteros `CURRENT.json` local y HA real siguen en la generación
  `local-mvc50-20260928`, huella
  `sha256:e4252f943945412ae4cfc38f81d685778fbdbadb2351f9523620cf9e262ddbea`.
  Metadatos científicos/territoriales presentes; no se modifica publicación alguna.

## HA real

`mount` confirma `//Carlos@100.111.77.48/share` en `/Volumes/share` y
`//Carlos@100.111.77.48/media` en `/Volumes/media-1`. Se usan los montajes del
usuario, sin montar ni abrir SSH.

Búsqueda completa de nombres de archivos/directorios que contienen `todelete`:

- `/Volumes/share`: 120 directorios recorridos, 623 archivos, cero coincidencias.
- `/Volumes/media-1`: 788 directorios recorridos, 5.318 archivos, cero coincidencias.
- Sin errores ni recorridos truncados. No se lee el contenido de archivos grandes.

Las carpetas `geography/mushroom-GIS` y `geography/mushroom-map-GIS` son parte de
la geografía operativa de HA: no se proponen para borrar. No se afirma nada sobre
otros sistemas de archivos de HA que no están expuestos en estos dos montajes.

## Propuesta concreta

Retirar exclusivamente las dos carpetas locales `mushroom-GIS-todelete/` y
`mushroom-map-GIS-todelete/` (unos 22,32 GB asignados a archivos). Conservar
`geography-sources/`, `docker-media/rainmapper/geography/`, el volumen del worker
y todo HA real. La revisión no encuentra una dependencia ni fuente geográfica
única que exija mantener los antiguos.

Las pruebas funcionales restantes de asignación/recuperación/importación siguen
como pendientes generales; no implican conservar otra copia completa cuando las
fuentes ya están preservadas y no hay dependencias de los antiguos. Esperar la
confirmación específica de este alcance antes de borrar, como acordó el usuario.
No se borró nada en la fase inicial de revisión; véase el cierre posterior.

Evidencia: `tmp/geography-retirement-20261003/` (`local.json`, `links.json`,
`ha-top-directories.json`, `ha-directory-scan.json`, script de revalidación local).

## Eliminación autorizada y completada — 03/10/2026

Tras preguntar por la conservación de originales, el usuario confirmó «pues
adelante». Se eliminaron exclusivamente `mushroom-GIS-todelete/` y
`mushroom-map-GIS-todelete/` del Mac a las 08:13 UTC. Revalidación final previa:
5.891 archivos cubiertos por el inventario, sin fuentes únicas ni destinos ausentes.

Medición `shutil.disk_usage` sobre el volumen del repositorio, en bytes decimales:

- Libre antes: **94.439.452.672 bytes (94,44 GB)**.
- Libre después: **116.266.102.784 bytes (116,27 GB)**.
- Aumento observado: **21.826.650.112 bytes (21,83 GB)**.

Es el cambio global de espacio libre durante la operación, no una equivalencia
exacta con los 22,32 GB previamente contabilizados por archivos. No se ha
investigado la diferencia ni se atribuye a una causa sin comprobarla.

Ambas carpetas ausentes tras el borrado. Comprobados antes/después tamaño,
mtime e inodo de los **5.897 archivos de `geography-sources/`** y los **3.600 de
`docker-media/rainmapper/geography/`**, sin cambios. No se modificaron HA real,
volumen/configuración del worker, datos privados ni otras carpetas. No se
lanzaron pruebas operativas ni reconstrucciones.

Recibo: `tmp/geography-retirement-20261003/deletion.json`; comprobación final
`pre-delete-check.log`. Retirada final completada; conservar las fuentes y la
geografía operativa. Los recorridos funcionales restantes siguen en TODO.
