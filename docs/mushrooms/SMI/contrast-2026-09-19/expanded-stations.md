# Muestra ampliada para el experimento local

**Actualización:** la comparación local y una revisión adicional de calidad ya se
ejecutaron en [SMI-03](../baseline-2026-09-19/README.md). Este inventario conserva
el estado de la descarga inicial; cobertura numérica no equivale a aceptación instrumental.

Consulta realizada el 19/09/2026 al servicio público del [visor XMS-Cat del ICGC](https://visors.icgc.cat/mesurasols/).
Periodo: 21/07/2026–18/09/2026. Se conservan registros de media hora y todas las profundidades anunciadas por el visor.

**22 estaciones descargadas; 21 candidatas por cobertura.** Esto amplía las referencias disponibles para el experimento; todavía no se han calculado ni comparado los modelos locales en las 20 estaciones añadidas.

El criterio preliminar exige al menos 54 de los 60 días con 44 o más registros numéricos válidos por día, simultáneamente en lluvia y sondas a 5 y 20 cm. Se consideran numéricamente admisibles VWC entre 0 y 1 m³/m³ y lluvia no negativa. Este filtro comprueba cobertura y límites básicos; no sustituye el control de calidad instrumental. No hay timestamps duplicados.

| Estación | Días conjuntos / 60 | Cobertura preliminar |
|---|---:|---|
| Aguilar de Segarra | 60 | Suficiente |
| Borda Coll | 55 | Suficiente |
| Batlliu de Sort | 60 | Suficiente |
| Bolvir | 60 | Suficiente |
| Clot de les Peres | 60 | Suficiente |
| Coll de Paller | 56 | Suficiente |
| Clarella | 51 | Incompleta |
| Cantallops | 60 | Suficiente |
| Camí dels Nerets | 60 | Suficiente |
| El Boixer | 60 | Suficiente |
| El Miracle | 60 | Suficiente |
| Garriguella | 60 | Suficiente |
| La Cultia d'Àreu | 60 | Suficiente |
| Los Coscolls | 60 | Suficiente |
| Llívia | 60 | Suficiente |
| Mas dels Frares | 60 | Suficiente |
| Pessonada | 58 | Suficiente |
| Ribera de Sió | 60 | Suficiente |
| Serra de Costa Ampla | 60 | Suficiente |
| Torre del Lluvià | 60 | Suficiente |
| Pobla de Cérvoles | 60 | Suficiente |
| Vilosell | 60 | Suficiente |

## Uso en el experimento

- Comparar los mismos candidatos y reglas en toda la muestra, conservando los resultados desfavorables.
- Priorizar sondas a 5 y 20 cm para el depósito de 0–30 cm; mostrar 50 cm y profundidades mayores como contexto.
- Clot de les Peres tiene además 10 y 30 cm, con cobertura numérica suficiente en los 60 días. Permite un contraste más detallado del perfil, pendiente de revisar la instalación.
- Revisar fechas, coordenadas exactas, cobertura vegetal, riego y representatividad de los emplazamientos antes del cálculo local. La zona horaria publicada aún no está confirmada.
- Revisar ceros y cambios anómalos: por ejemplo, Bolvir contiene VWC=0 a 20 cm y Clot de les Peres contiene VWC=0 a 5 cm. No se han reemplazado ni declarado válidos instrumentalmente por pasar el filtro numérico.
- No excluir Clarella por un resultado de modelo: tiene 51 días completos y puede conservarse para un análisis por episodios con cobertura adecuada, separado del conjunto principal.
- Antes de ajustar parámetros, definir estaciones reservadas para evaluación. La separación debe considerar proximidad y entorno, no solo repartir nombres al azar.

## Evidencia y alcance

`expanded-stations.json.gz` conserva las respuestas de las 20 estaciones nuevas y referencias a `evidence.json.gz` para las dos existentes, sin duplicar esas series. Ocupa 449785 bytes. No contiene credenciales ni tokens.
`expanded-stations-summary.json` contiene conteos, rangos y cobertura por canal. El catálogo de canales se obtuvo del código público del visor; su SHA-256 está en la evidencia.
No se ha modificado ningún cálculo, HA real ni el worker. El experimento de dos capas todavía no está implementado.
