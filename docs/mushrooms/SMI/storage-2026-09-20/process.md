# Registro de trabajo · SMI-06

20/09/2026. El usuario autoriza ejecutar la auditoría de cantidades y documentar
durante el proceso para permitir continuar a otra sesión.

1. Consultado el grafo del proyecto RainmapperHA antes de descubrir código.
   Leídos el plan de agua absoluta y las entradas/resultados de SMI-03/04/05.
   Revisada la implementación efectiva de capacidad: integra FC−WP por espesor,
   con capacidad de tierra fina y sin inventar corrección por piedras.
2. Reconsultada FAO (https://www.fao.org/4/t0231e/t0231e05.htm): definición de
   agua total, conversión gravimétrica usando densidad y agua disponible. La
   consulta web a `https://www.icgc.cat/es/node/23771` devolvió error interno;
   no se ha supuesto que eso pruebe caída del servicio o ausencia de metadatos.
3. Revisados los esquemas y textos de fichas ya archivados. Se decide calcular
   cambios condicionados, sin fabricar una validación absoluta; el inventario
   deja pendientes explícitos. No se han vuelto a descargar las fichas ni sondas.
4. Escrito `PROTOCOL.md` antes de ejecutar métricas, fijando perfiles, horarios,
   umbral descriptivo de episodios, ventanas y peso igual por estación.
5. Implementado `audit.py` independiente de servicios, usando salidas congeladas
   y observaciones de media hora. `test_audit.py`: cinco pruebas pasan.
6. Ejecutado el análisis: 22 estaciones, 1.320 fechas, 73 episodios IDW, 8.214
   casos incluyendo sensibilidades, cuatro candidatos por caso. Verificadas
   huellas de SMI-05 y exacta igualdad de cobertura de los candidatos.
7. Revisados cobertura, sensibilidad pareada, subconjunto con secado confirmado
   por lluvia medida y ejemplos Batlliu/MDF. Los resultados no dan un ganador
   único para cantidades. Redactado README con ventajas y casos adversos.

8. Comprobación independiente del ejemplo Batlliu: lectura cruda 23:30 y
   suma de trapecios hasta 30 cm reproducen +9,4167 L/m² (10–13 agosto).
   Comprobadas 32.856 identidades de residuos, huellas, fechas únicas y
   cardinalidades. `git diff --check` sin errores.
9. Búsqueda pública adicional dirigida: [fuentes y límites](sources.md).
   Localizada evidencia histórica de calibración y una pista sobre sondas
   de potencial hídrico. No se han descargado esos canales ni añadido datos
   nuevos a las métricas de SMI-06.

## Aclaración solicitada sobre el mapa local

El usuario preguntó si la referencia elegida ya corresponde al SMI nuevo del
mapa de HA local: **sí, los módulos comprobados coinciden**. Elegir referencia
en SMI-05 no supuso otro despliegue. Las frases históricas «no se ha cambiado
el mapa» deben leerse como ausencia de nuevos cambios durante la auditoría,
no como ausencia del cálculo regulado previamente implementado.

Comprobación de solo lectura, sin reinicio ni cambio de contenedor:

```sh
docker exec rainmapper-local-rainmapper-ha-ui-1 python -c 'import hashlib,pathlib; import rainmapper_core.mushroom_map_water_physics as m; p=pathlib.Path(m.__file__); print(p); print(hashlib.sha256(p.read_bytes()).hexdigest())'
docker exec rainmapper-local-rainmapper-ha-ui-1 python -c 'import hashlib,pathlib; import rainmapper_core.mushroom_map_hydrology as m; p=pathlib.Path(m.__file__); print(p); print(hashlib.sha256(p.read_bytes()).hexdigest()); print(m.MAX_HISTORY_DAYS)'
```

- Física local y snapshot usado en SMI-03/05:
  `f053eae6f5215ab8792f1f953fe59761c2ca711e7775ef57ad1acc3b82806fb5`.
- Hidrología local y fichero del repo:
  `e0d2db912db87a23523e549ed0639c3ba0da2156cfa01bccd8ab0059281cd954`.
- `MAX_HISTORY_DAYS=365`. Módulos en `/app/rainmapper_core/`.
- PM se utiliza con las aproximaciones documentadas; el código conserva
  Hargreaves como alternativa cuando no puede calcular PM. No afirmar que
  todos los puntos/fechas usan siempre PM.

Solo se consultó HA **local**. No se accedió al worker activo ni a HA real.
Una huella de fichero confirma el módulo disponible en el contenedor, no
constituye por sí sola una prueba de todas las rutas del navegador o de cada
respuesta online. No presentar esta comprobación como un nuevo smoke completo.

## Para continuar

Leer primero README y su decisión. El siguiente paso de FC/WP estimados por
horizonte **no está ejecutado**. No repetir estos cálculos esperando resolver
esa carencia ni cambiar el modelo operativo sin nueva decisión. No se han
hecho ajustes de parámetros ni una búsqueda exhaustiva de metadatos públicos.
El worktree contiene cambios ajenos; no limpiar/revertir archivos basándose
en esta auditoría. Se conserva todo el ensayo en la carpeta SMI-06.
