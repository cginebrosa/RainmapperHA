# Mobile App Architecture

Nota de estado 2026-06-26: el repo actual ya tiene autenticacion ligera, endpoints internos del add-on HA y datos protegidos para el visor MapLibre usado en pruebas privadas. Eso no equivale a la API externa definitiva de una app comercial iOS/Android: la futura app no deberia depender directamente de Home Assistant ni de rutas internas del add-on. La copia activa del repo esta en `/Users/carlosginebrosa/Developer/RainmapperHA`; no usar la copia antigua de iCloud.

## Objetivo
Definir una arquitectura inicial para una futura app iOS/Android de Rainmapper que permita consultar mapas de lluvia de forma controlada, con autenticacion, permisos por usuario/mapa o zona, y posible modelo de suscripcion.

Este documento es de diseno. No implica implementacion inmediata ni cambia el funcionamiento actual de Home Assistant.

## Estado de partida
- Home Assistant ejecuta Rainmapper en modo `serve`.
- Rainmapper genera CSV historicos, CSV `Tomap`, HTML Bokeh y GeoJSON para Leaflet/MapLibre.
- Leaflet y Bokeh siguen publicados como contenido estatico via `/local/...`; MapLibre tiene una ruta protegida propia en `/protected/maplibre/index.html` servida por `web_server.py`, con fallback publico temporal en `/local/rainmapper-maplibre` mientras se valida Cloudflared.
- Leaflet y MapLibre funcionan bien en iPhone segun validacion manual/reportada por el usuario; pendiente de confirmacion automatizada. Desde `0.2.48`, MapLibre incluye capas raster Hybrid/Topographic, estilos vectoriales y Satellite+.
- El acceso externo actual depende de HA/dominio/Cloudflare segun reporte del usuario. Rainmapper ya tiene autenticacion ligera, `/auth/*` y `/protected/maplibre/*` para MapLibre protegido, pero no es todavia la API/auth comercial prevista para una app iOS/Android. La configuracion Cloudflare no esta versionada en este repo y queda pendiente de confirmar fuera del repositorio.
- Docker local se mantiene como entorno de pruebas aislado para cambios de calado.

## Principio de arquitectura
La app movil no deberia depender directamente de Home Assistant como backend publico de producto.

Home Assistant puede seguir siendo el orquestador privado que genera datos y mapas. Para una app publica o bajo suscripcion, conviene introducir una capa backend/API separada que controle autenticacion, autorizacion, cache y exposicion de datos.

## Direccion preferente de prototipo
La direccion preferente para explorar la app movil es:

```text
Home Assistant / Rainmapper
  genera GeoJSON
        |
        v
Cloudflare R2
  almacena artefactos publicados por mapa/periodo
        |
        v
Cloudflare Worker API
  sirve endpoints, filtra datos y aplica auth/permisos cuando toque
        |
        v
App cross-platform
  React Native + MapLibre React Native
```

Motivos:
- Cloudflare ya forma parte del despliegue externo actual segun reporte del usuario; pendiente de confirmar fuera del repositorio.
- R2 encaja con artefactos GeoJSON versionados. El encaje exacto en el free tier queda pendiente de confirmar con limites/precios vigentes cuando se implemente.
- Workers permite una API ligera sin administrar VPS.
- React Native permite una base de codigo comun iOS/Android y MapLibre tiene soporte React Native para ambas plataformas.
- MapLibre ya es el visor principal recomendado del proyecto, por lo que reutilizar el mismo modelo mental reduce riesgo.

Esta direccion no implica construir aun la API ni la app. Sirve como referencia para disenar contratos de datos, rutas de publicacion y decisiones futuras.

## Arquitectura propuesta por fases

### Fase 0: Visores actuales
Mantener Leaflet y MapLibre publicados desde HA para uso privado y validacion visual.

MapLibre queda como candidato preferente a visor unico si la validacion de las capas Hybrid/Topographic/Satellite+ en HA/iPhone se mantiene correcta. La validacion actual es manual/reportada por el usuario; pendiente de confirmacion automatizada. MapLibre ya puede cubrir mapa hibrido, topografico raster y satelite con orientacion vectorial en una sola tecnologia.

Uso:
- pruebas personales;
- validacion de datos y estilos;
- acceso via dominio/Cloudflare mientras no haya producto publico.

Limitacion:
- el control actual es suficiente para pruebas privadas del visor, pero no cubre permisos comerciales por mapa/zona/capa de producto;
- los GeoJSON protegidos del visor principal requieren sesion Rainmapper; las rutas `/local/...` y fallbacks deben seguir tratandose como excepciones/fallbacks operativos, no como backend de producto;
- los tokens de mapas cliente pueden ser visibles en navegador.

### Fase 1: Backend/API ligera
Introducir una API propia externa que consuma los GeoJSON generados por Rainmapper y los sirva a clientes autenticados. Para el prototipo, la opcion preferente es Cloudflare Worker leyendo GeoJSON desde Cloudflare R2. Esta API futura es distinta de la API interna HA ya existente para login, settings y datos protegidos del visor MapLibre.

Responsabilidades:
- autenticar usuarios;
- autorizar acceso a mapas, zonas o capas;
- servir metadatos de periodos disponibles;
- servir GeoJSON filtrado;
- aplicar filtros de usuario como favoritos o lluvia minima;
- ocultar rutas internas de HA;
- preparar cache/CDN si el trafico crece.

Home Assistant seguiria generando datos. La API leeria datos publicados o sincronizados desde una ubicacion controlada.

Estructura R2 orientativa:

```text
rainmapper/
  maps/
    catalunya/
      latest.json
      periods/
        01d.geojson
        07d.geojson
        14d.geojson
        21d.geojson
        30d.geojson
        60d.geojson
        90d.geojson
```

`latest.json` deberia contener metadatos de publicacion, version/generacion, periodos disponibles y rutas de artefactos.

### Fase 2: App movil
Construir app iOS/Android sobre la API. La opcion preferente de prototipo es React Native con MapLibre React Native.

Capacidades iniciales:
- login, cuando se active auth;
- seleccion de mapa/zona autorizada;
- seleccion de periodo de lluvia;
- mapa con estaciones;
- detalle de estacion;
- lista de favoritos;
- filtro por lluvia minima en el periodo seleccionado;
- persistencia de preferencias por usuario.

### Fase 3: Producto/suscripcion
Anadir control comercial si aplica.

Capacidades:
- planes o suscripciones;
- permisos por mapa, zona o conjunto de estaciones;
- control de caducidad de acceso;
- auditoria basica de uso;
- gestion de usuarios.

## Opciones de datos para la app

### Opcion A: GeoJSON estatico directo
La app consume directamente GeoJSON generados por Rainmapper.

Ventajas:
- simple;
- bajo coste;
- reutiliza lo ya generado.

Inconvenientes:
- dificil aplicar permisos por usuario;
- dificil ocultar datos no autorizados;
- cache y revocacion de acceso mas complicadas;
- no permite filtros privados por usuario salvo en cliente.

Uso recomendado:
- pruebas privadas;
- no recomendado como producto publico con permisos.

### Opcion B: API que sirve GeoJSON filtrado
La app pide datos a una API que lee GeoJSON o CSV generados y devuelve solo lo autorizado.

Ventajas:
- permite auth y permisos;
- permite favoritos y filtros server-side;
- evita exponer todo el dataset;
- permite metricas de uso;
- prepara cache controlada.

Inconvenientes:
- requiere backend;
- requiere despliegue y mantenimiento;
- aumenta complejidad frente al visor estatico.

Uso recomendado:
- opcion preferente para app publica o bajo suscripcion.

### Opcion B1: Cloudflare R2 + Worker API
Variante concreta de la opcion B para el prototipo.

Rainmapper/HA sube o sincroniza GeoJSON a R2. Un Worker expone endpoints `api.nomentero.com` que leen R2, aplican filtros y devuelven JSON a la app.

Ventajas:
- aprovecha Cloudflare ya existente segun reporte del usuario; pendiente de confirmar fuera del repositorio;
- reduce operacion frente a un VPS;
- permite cache perimetral;
- no expone rutas internas de Home Assistant;
- free tier probablemente suficiente para pruebas y beta pequena, pendiente de confirmar con limites/precios vigentes antes de implementar.

Inconvenientes:
- la logica seria TypeScript/JavaScript, no Python;
- hay que implementar sincronizacion HA -> R2;
- si los GeoJSON crecen mucho, filtrar en cada request puede volverse caro;
- auth/suscripciones pueden requerir D1, KV o proveedor externo.

Uso recomendado:
- primera arquitectura tecnica para API/app movil si se avanza hacia producto.

### Opcion C: API con base de datos propia
Migrar o replicar datos a una base de datos consultable por API.

Ventajas:
- consultas mas flexibles;
- mejor escalabilidad;
- historicos y analitica mas potentes.

Inconvenientes:
- mayor coste de migracion;
- mas superficie de operacion;
- requiere disenar schema y jobs de ingestion.

Uso recomendado:
- fase posterior si GeoJSON/CSV dejan de ser suficientes.

## Modelo de permisos inicial
Entidad minima:
- usuario;
- mapa o zona;
- permiso de acceso;
- fecha de expiracion opcional;
- lista de estaciones permitidas opcional.

Reglas iniciales:
- un usuario solo puede pedir mapas/zonas autorizadas;
- la API filtra estaciones no autorizadas antes de responder;
- los favoritos no conceden permisos, solo seleccionan dentro de lo ya permitido;
- el filtro de lluvia minima reduce resultados dentro del periodo elegido, no altera historicos.

## Favoritos de estaciones
Objetivo:
Permitir que un usuario mantenga una lista de estaciones favoritas y vea solo esas estaciones en el mapa.

Diseno inicial:
- favoritos asociados a usuario y zona/mapa;
- se guardan por codigo de estacion (`Codi Estació`);
- la API valida que la estacion favorita pertenece al conjunto autorizado;
- la app permite activar/desactivar vista "favoritos".

Comportamiento:
- si la lista esta vacia, mostrar todas las estaciones autorizadas;
- si el modo favoritos esta activo, mostrar solo favoritas con datos en el periodo;
- si una favorita no tiene dato en el periodo seleccionado, no aparece o aparece como "sin dato" segun decision de UX futura.

## Filtro por lluvia minima
Objetivo:
Mostrar solo estaciones que superen una cantidad minima de lluvia en el periodo seleccionado.

Diseno inicial:
- filtro numeric en mm;
- se aplica sobre el acumulado del periodo seleccionado (`Total` o propiedad equivalente);
- puede combinarse con favoritos;
- valor por defecto: 0 mm o sin filtro.
- el visor MapLibre actual incorpora un slider cliente `Min rain` como validacion temprana de UX; en producto, la API tambien deberia aceptar `min_rain_mm` para no depender solo del cliente.

Orden de filtrado recomendado:
1. permisos del usuario;
2. zona/mapa seleccionado;
3. favoritos si estan activos;
4. lluvia minima;
5. orden visual o clustering en cliente si hace falta.

## Autenticacion
Opciones a evaluar:
- proveedor gestionado tipo Auth0, Firebase Auth, Supabase Auth o Cognito;
- Cloudflare Access/Zero Trust para pruebas privadas o acceso interno;
- D1/KV + tokens propios solo para prototipos muy controlados;
- autenticacion propia simple solo si el alcance es muy pequeno;
- integracion con pasarelas de suscripcion si se vende acceso.

Decision pendiente:
Elegir proveedor cuando se defina si la app sera publica, privada o comercial. Para prototipo privado, se puede empezar sin auth publica o con Cloudflare Access. Para producto, la autorizacion debe aplicarse en API/backend.

## Backend/API
Tecnologias posibles:
- Cloudflare Workers + R2 como opcion preferente de prototipo;
- Python/FastAPI si se quiere reutilizar conocimiento Python;
- Node/TypeScript si se prioriza ecosistema web/app;
- Supabase si se quiere combinar auth, base de datos y API rapidamente.

Endpoints iniciales orientativos:
- `GET /health`
- `GET /maps`
- `GET /maps/{map_id}/periods`
- `GET /maps/{map_id}/periods/{period}/stations`
- `GET /maps/{map_id}/stations/{station_id}`
- `GET /me`
- `GET /favorites`
- `PUT /favorites`

Parametros relevantes:
- `period`
- `min_rain_mm`
- `favorites_only`
- `bbox` o zona visible si se optimiza por viewport.

Primer contrato orientativo para estaciones:

```json
{
  "map_id": "catalunya",
  "period": "21d",
  "generated_at": "2026-06-17T23:55:00+02:00",
  "stations": []
}
```

## Relacion con Home Assistant
Home Assistant deberia mantenerse como motor privado de generacion:
- descarga datos;
- preserva historicos;
- genera `Tomap`;
- genera GeoJSON;
- publica o sincroniza resultados.

La API publica no deberia necesitar permisos de administrador de HA ni exponer rutas internas de HA. Idealmente consume una copia de los artefactos generados desde una ubicacion controlada.

Para Cloudflare, esa ubicacion controlada seria R2. La sincronizacion HA -> R2 puede empezar manualmente o con script posterior a `Run all`, y mas adelante integrarse como opcion de publicacion adicional.

## Cache y publicacion
Para uso privado, HA/Cloudflare puede ser suficiente; pendiente de confirmar fuera del repositorio segun la configuracion real de Cloudflare.

Para app publica:
- cachear GeoJSON por mapa/periodo/version de generacion;
- invalidar cache despues de cada `Run all`;
- evitar que URLs de datos privados sean publicas sin token;
- evaluar CDN solo para respuestas ya filtradas o para capas publicas.

Con Cloudflare:
- R2 almacena artefactos por mapa/periodo;
- Worker puede cachear respuestas por `map_id`, `period`, filtros y version de generacion;
- `latest.json` puede actuar como manifiesto para invalidacion simple;
- no publicar el bucket R2 directamente si contiene datos que deban quedar bajo permisos.

## Prototipo cross-platform
Opcion preferente:
- React Native;
- MapLibre React Native;
- llamadas HTTP a Cloudflare Worker API;
- estado local simple para periodo, capa, favoritos y filtro de lluvia minima.

Por que no nativo al principio:
- nativo Swift/Kotlin daria mas control, pero duplica esfuerzo;
- el primer objetivo es validar experiencia, API y modelo de datos.

Por que no PWA como producto final inicial:
- PWA seria muy rapida para prototipo visual, pero la app futura puede necesitar distribucion en stores, login nativo, pagos/subscripciones y mejor integracion movil.
- Aun asi, una PWA sigue siendo una alternativa valida para validar UX antes de invertir en app nativa/cross-platform.

Pruebas sin stores:
- iOS: simulador Xcode y dispositivo propio desde Xcode; para beta externa, TestFlight.
- Android: emulador Android Studio o dispositivo real via ADB; para beta, internal testing de Google Play.

Software/hardware minimo:
- Mac con Xcode para compilar/probar iOS;
- Android Studio para Android;
- iPhone real para validar mapa/gestos/rendimiento;
- Android real recomendable mas adelante;
- cuenta Apple Developer solo cuando se necesite distribucion formal/TestFlight externa o App Store.

## Seguridad
Riesgos:
- exposicion de GeoJSON completos por URL publica;
- tokens de tiles visibles en cliente;
- permisos aplicados solo en la app cliente;
- acceso directo a HA desde clientes moviles;
- falta de revocacion si se comparten URLs estaticas.

Reglas:
- aplicar permisos en backend, no solo en cliente;
- no guardar API keys reales en Git;
- restringir tokens de mapas por dominio si el proveedor lo permite;
- no exponer `/config/www` como fuente publica de datos privados en un producto comercial.

## Decisiones pendientes
- Confirmar React Native + MapLibre como stack de prototipo cross-platform.
- Proveedor de autenticacion.
- Backend propio vs plataforma gestionada.
- Confirmar Cloudflare R2 + Worker API como primer backend/API de prototipo.
- Modelo de permisos: por mapa, zona, estacion o combinacion.
- Modelo comercial: gratis, privado, suscripcion, acceso por zona.
- Estrategia de cache/CDN.
- Si Bokeh se retira antes de construir app publica.

## Primer MVP recomendado
1. Mantener HA generando GeoJSON.
2. Definir manifiesto `latest.json` y estructura R2.
3. Sincronizar GeoJSON de HA/Rainmapper a R2.
4. Crear Worker API minima sin producto publico: `health`, `maps`, `periods`, `stations`.
5. Anadir `min_rain_mm` en API.
6. Crear prototipo React Native + MapLibre con mapa y selector de periodo.
7. Anadir favoritos y auth/permisos cuando el flujo base este validado.

## No objetivos iniciales
- Migrar historicos CSV a base de datos.
- Reemplazar Home Assistant como generador.
- Implementar pagos antes de validar uso real.
- Construir analitica avanzada de estaciones en la primera version.
