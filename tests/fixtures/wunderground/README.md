# Fragmentos Wunderground

Capturados el 24/09/2026 de una consulta pública a ILAIGL7, sin ejecutar JavaScript.
Sólo se conservan cabeceras y una fila histórica para pruebas offline.

- `legacy-header.html`: cabecera Angular `.station-header`, altitud en pies.
- `web-components-header.html`: `dashboard-header-view`, altitud en metros.
- `legacy-history.html`: primera fila y encabezado de la tabla Angular.

Las respuestas originales proceden de
`https://www.wunderground.com/dashboard/pws/ILAIGL7/table/2028-09-30/2028-09-30/monthly`.
Aunque se solicitó una fecha futura, la tabla devolvió septiembre de 2026:
ese comportamiento constituye el caso de regresión, no una fecha aceptada.
El fragmento nuevo contiene coordenadas: la ausencia del selector antiguo no
equivale a ausencia de metadatos.
