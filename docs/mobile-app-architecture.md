# Mobile App Architecture

## Objetivo
Definir una arquitectura inicial para una futura app iOS/Android de Rainmapper que permita consultar mapas de lluvia de forma controlada, con autenticacion, permisos por usuario/mapa o zona, y posible modelo de suscripcion.

Este documento es de diseno. No implica implementacion inmediata ni cambia el funcionamiento actual de Home Assistant.

## Estado de partida
- Home Assistant ejecuta Rainmapper en modo `serve`.
- Rainmapper genera CSV historicos, CSV `Tomap`, HTML Bokeh y GeoJSON para Leaflet/MapLibre.
- Los visores actuales se publican como contenido estatico en `/config/www` y se sirven via `/local/...`.
- Leaflet y MapLibre funcionan bien en iPhone. Desde `0.2.47`, MapLibre tambien incluye capas raster Hybrid y Topographic, ademas de estilos vectoriales.
- El acceso externo actual depende de HA/dominio/Cloudflare, sin autenticacion propia de Rainmapper.
- Docker local se mantiene como entorno de pruebas aislado para cambios de calado.

## Principio de arquitectura
La app movil no deberia depender directamente de Home Assistant como backend publico de producto.

Home Assistant puede seguir siendo el orquestador privado que genera datos y mapas. Para una app publica o bajo suscripcion, conviene introducir una capa backend/API separada que controle autenticacion, autorizacion, cache y exposicion de datos.

## Arquitectura propuesta por fases

### Fase 0: Visores actuales
Mantener Leaflet y MapLibre publicados desde HA para uso privado y validacion visual.

MapLibre queda como candidato preferente a visor unico si la validacion de las capas raster en HA/iPhone es correcta, porque ya puede cubrir mapa hibrido, topografico y estilos vectoriales en una sola tecnologia.

Uso:
- pruebas personales;
- validacion de datos y estilos;
- acceso via dominio/Cloudflare mientras no haya producto publico.

Limitacion:
- no hay control granular por usuario, mapa o zona;
- los GeoJSON pueden quedar accesibles si se conoce la URL;
- los tokens de mapas cliente pueden ser visibles en navegador.

### Fase 1: Backend/API ligera
Introducir una API propia que consuma los GeoJSON generados por Rainmapper y los sirva a clientes autenticados.

Responsabilidades:
- autenticar usuarios;
- autorizar acceso a mapas, zonas o capas;
- servir metadatos de periodos disponibles;
- servir GeoJSON filtrado;
- aplicar filtros de usuario como favoritos o lluvia minima;
- ocultar rutas internas de HA;
- preparar cache/CDN si el trafico crece.

Home Assistant seguiria generando datos. La API leeria datos publicados o sincronizados desde una ubicacion controlada.

### Fase 2: App movil
Construir app iOS/Android sobre la API.

Capacidades iniciales:
- login;
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

Orden de filtrado recomendado:
1. permisos del usuario;
2. zona/mapa seleccionado;
3. favoritos si estan activos;
4. lluvia minima;
5. orden visual o clustering en cliente si hace falta.

## Autenticacion
Opciones a evaluar:
- proveedor gestionado tipo Auth0, Firebase Auth, Supabase Auth o Cognito;
- autenticacion propia simple solo si el alcance es muy pequeno;
- integracion con pasarelas de suscripcion si se vende acceso.

Decision pendiente:
Elegir proveedor cuando se defina si la app sera publica, privada o comercial.

## Backend/API
Tecnologias posibles:
- Python/FastAPI si se quiere reutilizar conocimiento Python;
- Node/TypeScript si se prioriza ecosistema web/app;
- Supabase si se quiere combinar auth, base de datos y API rapidamente.

Endpoints iniciales orientativos:
- `GET /me`
- `GET /maps`
- `GET /maps/{map_id}/periods`
- `GET /maps/{map_id}/periods/{period}/stations`
- `GET /maps/{map_id}/stations/{station_id}`
- `GET /favorites`
- `PUT /favorites`

Parametros relevantes:
- `period`
- `min_rain_mm`
- `favorites_only`
- `bbox` o zona visible si se optimiza por viewport.

## Relacion con Home Assistant
Home Assistant deberia mantenerse como motor privado de generacion:
- descarga datos;
- preserva historicos;
- genera `Tomap`;
- genera GeoJSON;
- publica o sincroniza resultados.

La API publica no deberia necesitar permisos de administrador de HA ni exponer rutas internas de HA. Idealmente consume una copia de los artefactos generados desde una ubicacion controlada.

## Cache y publicacion
Para uso privado, HA/Cloudflare puede ser suficiente.

Para app publica:
- cachear GeoJSON por mapa/periodo/version de generacion;
- invalidar cache despues de cada `Run all`;
- evitar que URLs de datos privados sean publicas sin token;
- evaluar CDN solo para respuestas ya filtradas o para capas publicas.

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
- App nativa, cross-platform o PWA.
- Proveedor de autenticacion.
- Backend propio vs plataforma gestionada.
- Modelo de permisos: por mapa, zona, estacion o combinacion.
- Modelo comercial: gratis, privado, suscripcion, acceso por zona.
- Estrategia de cache/CDN.
- Si Bokeh se retira antes de construir app publica.

## Primer MVP recomendado
1. Mantener HA generando GeoJSON.
2. Crear API minima que lee GeoJSON y exige autenticacion.
3. Implementar permisos simples por mapa/zona.
4. Exponer endpoint de estaciones por periodo con `min_rain_mm` y `favorites_only`.
5. Crear prototipo movil con mapa, periodos, favoritos y filtro de lluvia minima.

## No objetivos iniciales
- Migrar historicos CSV a base de datos.
- Reemplazar Home Assistant como generador.
- Implementar pagos antes de validar uso real.
- Construir analitica avanzada de estaciones en la primera version.
