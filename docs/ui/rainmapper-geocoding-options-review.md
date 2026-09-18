# Rainmapper — revisión de opciones para búsqueda de municipios y topónimos

## Objetivo

Rainmapper **ya utiliza Photon actualmente** en el mapa de predicciones/meteorología para buscar municipios y/o topónimos.

Lo que no está confirmado es **cómo lo ha implementado exactamente el código actual**. Es probable que esté utilizando el servidor público de Photon (`photon.komoot.io`), pero esto debe comprobarse directamente en el repositorio y no asumirse.

Por tanto, el objetivo ya no es diseñar una solución desde cero, sino:

1. **Auditar la integración Photon existente.**
2. Determinar exactamente qué endpoint, librería, parámetros y flujo utiliza Rainmapper.
3. Valorar si la implementación actual es adecuada.
4. Revisar sus implicaciones si Rainmapper termina siendo una aplicación comercial/de pago.
5. Comparar, sólo donde tenga sentido, alternativas o posibles evoluciones de la arquitectura actual.
6. Dar **preferencia explícita a soluciones en las que Rainmapper NO tenga que mantener ni actualizar índices OSM propios**.

Una prioridad de diseño es evitar que Rainmapper tenga que encargarse periódicamente de descargar, reconstruir, sincronizar o sustituir índices geográficos para mantener las búsquedas actualizadas.

**No implementar todavía cambios importantes.** Primero quiero un análisis técnico del código existente y una recomendación razonada.

---

## Contexto del proyecto

Rainmapper se ejecuta actualmente como aplicación/add-on sobre Home Assistant OS, en una Raspberry Pi.

La aplicación ya trabaja con mapas y datos geográficos y **ya tiene búsqueda mediante Photon implementada en el mapa de predicciones/meteorología**.

Antes de plantear ninguna arquitectura nueva, hay que localizar esa implementación y entenderla.

La funcionalidad actual permite o debe permitir resolver búsquedas del tipo:

- `Prades`
- `Montseny`
- `Setcases`
- `Coll de Pal`
- `La Pobla de Lillet`
- municipios de España
- topónimos de Francia, Andorra, Portugal, etc.

La búsqueda debería devolver candidatos con suficiente información para que Rainmapper pueda identificar correctamente el lugar seleccionado, idealmente incluyendo:

- nombre
- tipo de lugar
- municipio
- provincia/departamento/región cuando exista
- país
- latitud
- longitud
- identificadores OSM si están disponibles
- bounding box si está disponible

También sería útil poder usar:

- sesgo por proximidad a unas coordenadas
- filtro por país
- filtro por tipo de lugar
- idioma preferido
- autocomplete mientras el usuario escribe

---

# Paso 1 — Auditar primero la implementación Photon actual

Esta parte es prioritaria.

Buscar en todo el repositorio cualquier referencia relacionada con:

- `photon`
- `photon.komoot.io`
- `/api`
- `/reverse`
- `geocode`
- `geocoder`
- `autocomplete`
- búsquedas de municipios/topónimos
- componentes de búsqueda del mapa
- llamadas `fetch`, `axios`, `requests`, etc.
- configuración de URLs externas
- variables de entorno
- proxies backend
- caché
- normalización de resultados geográficos

Determinar exactamente:

1. **Dónde está implementado Photon**
   - frontend
   - backend
   - ambos

2. **Qué endpoint utiliza**
   - servidor público de Komoot
   - otro proveedor Photon
   - proxy propio
   - servicio local

3. **Qué operaciones se usan**
   - búsqueda directa
   - autocomplete
   - reverse geocoding
   - bias por coordenadas
   - filtro por idioma
   - filtro por país
   - límite de resultados

4. **Qué datos se extraen del resultado Photon**
   - nombre
   - municipio
   - región/provincia
   - país
   - coordenadas
   - OSM id/type
   - bounding box
   - tipo de lugar

5. **Qué hace Rainmapper después con esos resultados**
   - sólo mover/centrar el mapa
   - guardar coordenadas
   - guardar municipio/topónimo
   - rellenar campos de formularios
   - persistir resultados

6. **Si existe caché**
   - memoria
   - navegador
   - backend
   - base de datos

7. **Si existen fallbacks o manejo de errores**
   - timeout
   - reintentos
   - ausencia de resultados
   - indisponibilidad de Photon
   - rate limiting

8. **Si la URL de Photon está hardcoded o parametrizada**

9. **Si esta integración se reutiliza ya en otras pantallas o sólo en predicciones/meteorología**

El informe debe empezar por esta auditoría y mostrar los archivos y funciones concretas encontrados.

---

# Prioridad arquitectónica adicional: evitar mantenimiento de índices OSM

Esto debe tener un peso importante en la recomendación.

No quiero que la solución normal de Rainmapper requiera tareas como:

- descargar periódicamente extractos OSM
- reconstruir índices Photon
- mantener una instancia Nominatim sincronizada
- aplicar diffs/replication de OpenStreetMap
- sustituir dumps manualmente
- reservar espacio temporal para actualizar índices
- vigilar fallos de reindexación
- gestionar versiones de Java/OpenSearch/Nominatim asociadas al motor
- tener que decidir cada cuánto actualizar los datos

La expectativa es que las búsquedas de municipios y topónimos reflejen datos razonablemente actuales **sin que Rainmapper tenga que administrar esa actualización**.

Por tanto, en la comparativa se deben favorecer, salvo que exista una razón fuerte en contra:

1. servicios remotos mantenidos por terceros
2. servicios comerciales/freemium con índices gestionados
3. endpoints Photon/Nominatim gestionados externamente
4. arquitecturas en las que cambiar de proveedor sea sencillo

El autoalojamiento de Photon/Nominatim debe considerarse principalmente como:

- opción futura
- fallback estratégico
- requisito de independencia
- solución para volumen elevado
- necesidad de privacidad/control
- o caso donde el coste externo lo justifique

pero **no como opción preferida por defecto** si obliga a mantener índices OSM localmente.

---

# Alternativas a revisar

## 1. Photon público de Komoot

Endpoint público típico:

`https://photon.komoot.io/api/`

Photon utiliza datos de OpenStreetMap.

**Es posible que ésta sea ya la solución implementada actualmente en Rainmapper. Confirmarlo en el código.**

### Revisar

- si Rainmapper ya utiliza directamente este servicio público
- condiciones actuales de uso
- limitaciones
- rate limits explícitos o implícitos
- política respecto a aplicaciones comerciales
- autocomplete
- idiomas
- búsqueda de municipios y topónimos
- calidad de resultados en España/Francia/Andorra/Portugal
- geocodificación inversa
- estabilidad del servicio
- necesidad de User-Agent o identificación
- atribución requerida
- posibilidad de que el endpoint cambie o desaparezca

### Arquitectura posible

```text
Rainmapper
    |
    | HTTPS
    v
photon.komoot.io
```

Esta sería probablemente la opción más sencilla durante desarrollo y primeras versiones.

---

## 2. Photon autoalojado

Photon es open source y puede ejecutarse en infraestructura propia.

Esta opción debe analizarse, pero **no es la preferida de partida** debido al mantenimiento de índices.

Quiero saber si tendría sentido instalarlo como:

- add-on de Home Assistant
- contenedor Docker independiente
- servicio interno accesible desde Rainmapper
- servidor externo/VPS en una fase comercial

### Arquitectura local posible

```text
Home Assistant OS
|
+-- Rainmapper
|
+-- Photon
     |
     +-- índice OSM
```

Rainmapper podría consultar algo como:

```text
http://photon:2322/api?q=Prades
```

### Revisar especialmente

- requisitos actuales de Photon
- versión de Java necesaria
- RAM real necesaria
- almacenamiento necesario
- CPU
- comportamiento sobre ARM64
- compatibilidad con Raspberry Pi 4
- compatibilidad con Raspberry Pi 5
- posibilidad de limitar los datos geográficos

### Muy importante

No necesito necesariamente el planeta entero.

Investigar si podemos disponer de un índice únicamente para:

1. España
2. España + Francia + Andorra
3. España + Francia + Portugal + Andorra
4. Europa occidental

Determinar:

- tamaño de los índices
- RAM necesaria
- tiempo de arranque
- tiempo de actualización
- procedimiento de actualización de datos OSM
- si existen dumps ya preparados
- si pueden combinarse varios países
- dificultad de construir un índice personalizado

### Preguntas clave

1. ¿Es realista ejecutar Photon para el ámbito geográfico de Rainmapper en una Raspberry Pi 4 que también ejecuta Home Assistant y otros servicios?
2. ¿Qué mantenimiento continuo exigiría para que los resultados sigan razonablemente actualizados?
3. ¿Puede automatizarse de forma robusta?
4. ¿Qué ocurre si una actualización falla?
5. ¿Cuánto espacio adicional requiere una actualización/reemplazo de índice?
6. ¿Con qué frecuencia sería razonable actualizar?
7. ¿Existe alguna forma de autoalojar Photon sin asumir nosotros el mantenimiento del índice?

No asumir que es una buena opción simplemente porque técnicamente pueda ejecutarse.

---

## 3. Nominatim público

Revisar la API pública de Nominatim/OpenStreetMap.

### Comprobar

- condiciones actuales de uso
- límites de peticiones
- prohibición o no de autocomplete
- uso comercial
- política de caché
- User-Agent
- disponibilidad
- geocodificación directa
- geocodificación inversa
- calidad para municipios/topónimos

Tengo entendido que la instancia pública de Nominatim tiene restricciones bastante más fuertes que Photon, especialmente para autocomplete.

Confirmarlo con documentación actual.

---

## 4. Nominatim autoalojado

Evaluar también si un Nominatim propio tendría sentido frente a Photon.

Comparar:

- complejidad de instalación
- RAM
- almacenamiento
- CPU
- actualizaciones
- tiempo de importación
- rendimiento
- calidad de búsquedas
- autocomplete
- Raspberry Pi
- mantenimiento

No asumir que Nominatim es mejor simplemente por ser el geocodificador oficial de OSM.

---

## 5. Servicios comerciales o freemium

Investigar al menos algunas alternativas relevantes, por ejemplo:

- Geoapify
- LocationIQ
- OpenCage
- MapTiler Geocoding
- HERE
- TomTom
- Google Places/Geocoding, si tiene sentido

Para cada una, indicar:

- coste aproximado
- free tier
- autocomplete
- calidad de topónimos
- restricciones
- uso comercial
- atribución
- dependencia de proveedor
- posibilidad de almacenar/cachear resultados
- condiciones sobre almacenamiento permanente

No quiero necesariamente utilizar una API comercial, pero quiero conocer la alternativa.

---

## 6. Overpass API

Determinar si Overpass podría ser útil para alguna parte del problema.

Por ejemplo:

- obtener atributos adicionales de un objeto OSM ya identificado
- buscar objetos concretos por tags

Pero verificar si sería una mala elección como motor principal de autocomplete/geocodificación.

---

# Caché local en Rainmapper

Independientemente del proveedor elegido, estudiar la posibilidad de incorporar caché.

La caché **no debe usarse como sustituto de tener datos geográficos actuales**. Su objetivo es:

- reducir peticiones repetidas
- mejorar latencia
- disminuir dependencia temporal del proveedor
- absorber pequeñas caídas del servicio

Para búsquedas nuevas, Rainmapper debería seguir pudiendo consultar un proveedor que mantenga sus datos actualizados externamente.

Ejemplo:

```text
Usuario busca "Prades"
        |
        v
Rainmapper consulta caché local
        |
        +-- encontrado -> devolver
        |
        +-- no encontrado
                |
                v
             API externa
                |
                v
          guardar resultado
```

Proponer:

- estructura de tabla
- clave normalizada de búsqueda
- coordenadas de sesgo
- país
- idioma
- proveedor
- TTL
- invalidación
- almacenamiento permanente de resultados seleccionados por el usuario

Distinguir entre:

1. **caché de búsquedas**
2. **lugares ya seleccionados y guardados por el usuario**

Los segundos no deberían depender de que el proveedor externo siga disponible.

---

# Abstracción del proveedor

Quiero evitar acoplar Rainmapper directamente a Photon.

Evaluar una interfaz interna similar a:

```python
class GeocoderProvider:
    def search(
        self,
        query: str,
        latitude: float | None = None,
        longitude: float | None = None,
        country_codes: list[str] | None = None,
        language: str | None = None,
        limit: int = 10,
    ) -> list[Place]:
        ...
```

Y una representación normalizada:

```python
@dataclass
class Place:
    name: str
    display_name: str
    latitude: float
    longitude: float
    country: str | None
    country_code: str | None
    region: str | None
    municipality: str | None
    place_type: str | None
    osm_type: str | None
    osm_id: str | None
    bounding_box: tuple | None
    provider: str
    provider_id: str | None
```

De esta manera podríamos empezar con Photon y cambiar posteriormente a:

- otro endpoint Photon gestionado
- Geoapify
- OpenCage
- LocationIQ
- Nominatim gestionado
- Photon propio sólo si algún día compensa
- otro proveedor

sin modificar la UI ni el modelo de datos.

La URL/endpoint no debería quedar acoplada a la lógica de la pantalla.

---

# Uso comercial futuro

Rainmapper podría acabar siendo una aplicación de pago.

Por tanto, revisar expresamente para cada alternativa:

- si el uso comercial está permitido
- licencias
- obligaciones de atribución
- limitaciones del endpoint público
- dependencia de un servicio gratuito sin SLA
- posibilidad de autoalojamiento
- costes futuros
- riesgo de bloqueo por volumen
- posibilidad de caching
- condiciones sobre almacenar resultados derivados de OSM

No confundir:

- licencia del software Photon
- licencia de los datos OpenStreetMap
- condiciones de uso del servidor público `photon.komoot.io`

Son tres asuntos diferentes.

---

# Home Assistant

Revisar si existe actualmente:

- algún add-on de Home Assistant para Photon
- algún add-on de Nominatim
- alguna integración existente de Photon
- algún contenedor ARM64 que pudiera adaptarse fácilmente a un add-on

Si no existe un add-on mantenido, valorar qué esfuerzo tendría crear uno.

Un posible add-on tendría aproximadamente:

```text
addon-photon/
|
+-- config.yaml
+-- Dockerfile
+-- run.sh
+-- rootfs/
```

Pero no quiero desarrollarlo si realmente no aporta una ventaja clara frente a utilizar una API remota.

En particular, **no quiero crear un add-on Photon únicamente para trasladar a Home Assistant la responsabilidad de mantener y actualizar los índices OSM**.

---

# Escenarios a comparar

Quiero al menos estas cuatro arquitecturas:

## A. Photon público

```text
Rainmapper -> photon.komoot.io
```

## B. Photon público + caché Rainmapper

```text
Rainmapper -> cache local -> photon.komoot.io
```

## C. Photon local en Home Assistant

```text
Rainmapper -> Photon add-on -> índice OSM local
```

## D. Photon propio en servidor externo

```text
Rainmapper
    |
    v
geo.rainmapper.xxx
    |
    v
Photon
```

Para C y D, incluir explícitamente el coste operativo del mantenimiento de índices y no sólo CPU/RAM/disco.

La comparativa debe responder si realmente hay una ventaja suficiente para asumir ese mantenimiento frente a usar un servicio gestionado.


---

# Criterios de evaluación

Para cada opción, puntuar o describir:

| Criterio | Evaluación |
|---|---|
| Calidad búsqueda de municipios | |
| Calidad búsqueda de topónimos | |
| Autocomplete | |
| España | |
| Francia | |
| Andorra | |
| Portugal | |
| Geocodificación inversa | |
| Latencia | |
| Dependencia de Internet | |
| RAM | |
| Disco | |
| CPU | |
| ARM64/Raspberry Pi | |
| Complejidad de instalación | |
| Mantenimiento | |
| Actualización de datos OSM | |
| ¿Quién mantiene los índices? | |
| Trabajo operativo periódico | |
| Riesgo de datos obsoletos | |
| Automatización de actualizaciones | |
| Coste actual | |
| Coste con 100 usuarios | |
| Coste con 1.000 usuarios | |
| Uso comercial | |
| SLA | |
| Riesgo de bloqueo | |
| Caché permitida | |
| Atribución requerida | |

---

# Pruebas reales

Si es razonablemente sencillo, realizar algunas búsquedas reales contra las APIs que puedan probarse públicamente.

Usar ejemplos como:

- Prades
- Setcases
- Montseny
- Coll de Pal
- La Pobla de Lillet
- Llo
- Saillagouse
- Andorra la Vella
- Sierra de Guadarrama
- Montseny Natural Park

Comprobar:

- calidad del resultado principal
- ambigüedad
- estructura JSON
- tipos de lugar
- datos administrativos
- idioma
- velocidad de respuesta

---

# Qué quiero como resultado

Crear un informe en Markdown, sin implementar todavía cambios importantes.

El informe debe incluir:

## 1. Situación actual

Explicar con precisión **cómo está implementado Photon hoy en Rainmapper** dentro del mapa de predicciones/meteorología.

No partir de hipótesis: localizar en el código la implementación real.

Indicar:

- archivos implicados
- funciones/componentes
- endpoint utilizado
- si se llama desde frontend o backend
- parámetros enviados a Photon
- formato de respuesta utilizado
- campos que Rainmapper conserva
- si existe autocomplete
- si existe búsqueda inversa
- si existe bias geográfico
- si existe caché
- timeouts/reintentos
- manejo de errores
- configuración relacionada
- cualquier otro proveedor geográfico existente (Google Maps, OSM, etc.)

Si efectivamente usa `photon.komoot.io`, indicarlo expresamente.

## 2. Comparativa

Comparar las alternativas anteriores.

## 3. Recomendación para ahora

Partiendo de la integración Photon **ya existente**, determinar si conviene:

- dejarla exactamente como está
- mejorarla
- encapsularla detrás de un provider
- añadir caché
- parametrizar el endpoint
- mover la llamada de frontend a backend o viceversa
- añadir fallback
- cambiar de servicio

La prioridad es **reutilizar lo que ya funciona** si es técnicamente razonable.

Además, la recomendación para la fase actual debería favorecer una solución en la que **el mantenimiento y actualización de los datos geográficos recaiga en el proveedor externo, no en Rainmapper**.

La solución actual debería seguir siendo:

- sencilla
- gratuita o casi gratuita
- con poco mantenimiento
- compatible con futura comercialización

No proponer una reescritura sólo por razones arquitectónicas si la implementación actual ya es suficiente.

## 4. Recomendación para futuro comercial

Si actualmente Rainmapper utiliza `photon.komoot.io`, analizar específicamente hasta qué punto esa dependencia es razonable para una aplicación de pago y cuándo dejaría de serlo.

Antes de recomendar Photon propio, estudiar preferentemente si existen **servicios gestionados** que permitan seguir usando Photon/OSM o geocodificación equivalente sin que Rainmapper tenga que mantener índices.

Explicar qué cambiaría si Rainmapper tiene:

- ~10 usuarios
- ~100 usuarios
- ~1.000 usuarios
- más volumen

## 5. Diseño técnico recomendado

Proponer:

- módulo/provider
- interfaz
- modelo de datos
- caché
- configuración
- fallback
- timeouts
- rate limiting
- manejo de errores

## 6. Cambios concretos necesarios

Enumerar los archivos que habría que:

- crear
- modificar
- eliminar

pero **sin aplicar todavía los cambios**, salvo pequeñas pruebas aisladas necesarias para verificar comportamiento.

## 7. Fuentes

Incluir enlaces a documentación oficial actual de:

- Photon
- OpenStreetMap
- Nominatim
- proveedores comerciales analizados

No basarse únicamente en documentación antigua, blogs o respuestas de terceros.

---

# Restricciones

- **No sustituir Photon ni rediseñar la solución antes de inspeccionar la implementación actual.**
- Tratar el código existente como punto de partida.
- Evitar recomendar índices OSM locales como solución principal salvo que haya una ventaja clara y cuantificada.
- Penalizar en la comparativa las opciones que requieran mantenimiento periódico de índices.
- Preferir, si es viable, servicios con datos gestionados y actualizados externamente.
- No introducir dependencias pesadas sin justificar.
- No desplegar un servidor Photon/Nominatim todavía.
- No modificar datos existentes.
- No romper la UI actual.
- No añadir claves API al repositorio.
- No asumir que una Raspberry Pi puede soportar un índice concreto: verificar requisitos.
- No asumir que un endpoint gratuito puede utilizarse comercialmente: verificar términos actuales.
- No implementar antes de presentar el análisis.

---

# Pregunta final que debe responder el informe

> Dado que Rainmapper ya usa Photon en el mapa de predicciones/meteorología, ¿está bien implementada la solución actual, qué habría que mejorar ahora si procede y cuál debería ser su camino de evolución si la aplicación termina siendo comercial, dando preferencia a una arquitectura en la que Rainmapper no tenga que mantener y actualizar índices OSM propios?

