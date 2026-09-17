# Revisión de sustratos posterior a HA 0.2.307

Resultado local comprobado el 16/09/2026. El usuario confirma la subida de los dos JSON a HA real; no se han verificado allí sus huellas ni su consumo. El cambio de código del Predictor sigue solo en local.

## Resultado y alcance

La tanda comprendía 488 códigos de `geology_50000` sin clasificación de suelo aceptada: 471 con litología aceptada y 17 pendientes. Se revisaron sus descripciones y la evidencia disponible. No se ha completado la clasificación de todos los suelos:

| Resultado de esta tanda | Códigos |
| --- | ---: |
| Componente silíceo justificado | 95 |
| Componentes calcáreo y silíceo justificados | 32 |
| Componente calcáreo justificado | 18 |
| Suelo aún sin evidencia suficiente | 343 |

Los 145 casos justificados están aceptados. Los otros 343 mantienen la litología y el estado previo, sin aceptar una clasificación de suelo; sus notas y la auditoría explican la carencia. Una regla con litología aceptada y suelo vacío **no significa suelo validado**.

El inventario conserva los 1.055 códigos geológicos y las 1.336 identidades totales. Hay 712 códigos geológicos con algún componente de suelo aceptado y 343 sin él. Las otras 567 clasificaciones de suelo anteriores a esta tanda no se han modificado ni se presentan como una nueva revisión bibliográfica. Tampoco se han modificado los mappings MVC ni los identificadores de fuentes.

## Seguimiento de pendientes

Se añadieron diez aceptaciones tras la primera tanda: Qvm, Qvp, Qvpc, Qvt, Qvpb, Orst, Orst1, Gbs, Crgl y Caba. Para los piroclastos se cruzó la extensión cartográfica con la monografía de la Generalitat. Para Estana/Ansovell se corrigió la confusión entre nódulos disueltos y pérdida completa del carbonato; para Bellver se buscaron minerales de las facies finas. Gbs se contrastó con la denominación granitoide de la leyenda ICGC. Cada argumento y alcance figura en la auditoría.

Después se incorporaron Cb, PPa, POca y POlg: mineralogía de las lateritas en Mata-Perelló, descripción de Mediona en la guía ICEA/CREAF y petrografía de las facies Solsona/Berga en Cruset et al. (2016), §5.1. Las notas explicitan que la correlación es por formación/facies y no un muestreo de cada polígono; no se generalizan porcentajes ni pH. El PDF de la tesis que contiene Cruset se eliminó tras conservar texto, URL y huellas para ahorrar disco.

PEcga también queda aceptado como mixto tras contrastar Rupit en MAGNA 295, §1.3.7, pp.19–21, que agrupa explícitamente Bracons y Rupit.

De los 343 pendientes, 12 tienen investigación específica de la formación/facies con una limitación concreta documentada en las fuentes consultadas, y 331 aún no tienen investigación específica suficiente. La consulta genérica inicial no se cuenta como revisión terminada. Los 12 tampoco implican bibliografía agotada. El desglose reproducible está en `tmp/soil-review-after-0.2.307/research-depth-count.json`.

## Evidencia

Auditoría operativa: `docker-data/mushroom-data/gis-mapping-reviews/unresolved-substrates-2026-09-16.json` (985.024 bytes). Contiene por código descripción, estado anterior y posterior, motivo, fuente y localizador; las fuentes descargadas incluyen URL y SHA-256. Los documentos de consulta se conservan en `tmp/soil-review-after-0.2.307/sources` (aproximadamente 90 MiB). Son evidencia de trabajo, no paquetes de rollback ni archivos necesarios para el runtime de HA.

Se consultaron el inventario ICGC 1:50.000 edición 2024-12, el vocabulario geológico ICGC, memorias MAGNA del IGME y estudios específicos. Por ejemplo, Frontanyà tiene cuarzo/granito y calizas documentados en la memoria MAGNA 255, §1.3.8, unidad E, p.45 impresa. La auditoría conserva las referencias completas de cada decisión.

No se deriva textura, pH, drenaje, humus ni carbonato del horizonte superficial a partir del nombre de una roca. Silicatos cálcicos no equivalen a carbonatos; básico en petrología no equivale a pH básico. Las etiquetas describen componentes posibles del sustrato cartografiado. Las correlaciones de formaciones/facies que no pudieron justificarse permanecen pendientes; no se sustituye la ausencia de prueba por una regla de palabras clave.

## Verificación

- `build_review.py`: listas explícitas de códigos y justificaciones; 488 decisiones únicas; la cola de investigación conserva los 343 casos aún sin resolver, aunque tengan una primera evaluación.
- `verify_review.py`: comprueba las 1.336 identidades, IDs de catálogo, procedencia, integridad de fuentes y coincidencia con los dos lectores para los 1.055 códigos geológicos. Los cambios se limitan a los 488 registros auditados.
- `install_local.py`: activación atómica de auditoría y mappings, con comprobación previa de SHA para impedir sobrescribir cambios concurrentes.
- Comprobación ejecutada dentro de `rainmapper-local-rainmapper-ha-ui-1`: ambos lectores coinciden para los 1.055 códigos geológicos usando los catálogos efectivos del contenedor.
- SHA-256 del mapping validado y leído dentro de HA local: `054a92665b10e4d7d54801eced3657998eeab731fc31cb17b2d7d67fbc9c7f20`.

El archivo de mappings ocupa 256.816 bytes y representa las entradas mediante 477 reglas. El límite existente de 512 está en `rainmapper_core/mushroom_map_ecology.py`; la agrupación solo combina registros con todos los atributos comunes idénticos. No se elevó el límite ni se descartaron códigos para encajar. Las reglas pendientes sin edición se agrupan únicamente cuando todos sus atributos coinciden: los dos lectores reconstruyen el mismo contenido lógico. Las aceptadas sin edición siguen como registros exactos, conforme al contrato actual. Ninguna clasificación se modifica para encajar en el límite.

Esta comprobación valida carga e interpretación de mappings; no es una validación empírica de fructificación, ni una nueva ejecución de entrenamiento o precálculo. No se reinició ni se cambió el destino del worker.

## IFF

El predictor local usa `IFF:88/100` en tarjetas y detalle, conservando el tooltip. Fuente: `rainmapper-app/app/mushroom_predictor_ui.py`. Se reconstruyó HA local y se comprobó el mismo SHA-256 en host/contenedor: `7c5cf97a63d6cb63a88a1d2cdcaafe9ae543bd846e7bc47874344a455d53690b`. Prueba dirigida de redondeo superada. Este cambio tampoco está publicado.

## Limpieza local paralela

Informe de rutas y medidas: `tmp/disk-cleanup-20260916.json`.

- `backups`: 25,75 GiB → 10,6 MiB. Retirados el paquete obsoleto de mapas y tres archivos de fuentes de entregas antiguas.
- Retiradas 18 copias meteorológicas antiguas: 4,32 GiB.
- Docker reclamó 1,917 GB de caché de construcción.
- Espacio libre observado: aproximadamente 91 → 122 GiB. No se atribuye todo el crecimiento histórico de 50 GB sin una medición inicial comparable.

Se conservaron datos activos, observaciones del usuario, GBIF, fuentes GIS, media cartográfica activa, auditorías con lectores vigentes, volúmenes y Python 3.11. HA local y el worker seguían activos al terminar. No se borró nada de HA real. Para próximas entregas, evitar conservar simultáneamente cartografía comprimida y extraída tras aceptar la instalación; las justificaciones compactas sí deben conservarse.
