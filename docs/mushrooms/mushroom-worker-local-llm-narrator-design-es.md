# Narrador LLM local opcional para el Predictor

Estado: **propuesta documentada; no implementada ni incluida en la release
HA 0.2.243 / worker 1.0.5**.

## Objetivo

Un worker con recursos suficientes podría ejecutar en el futuro un modelo de
lenguaje pequeño y local para convertir la interpretación estructurada del
Predictor en una explicación más natural. Su función sería exclusivamente la
de **narrador**: no calcularía scores, no elegiría modelos y no decidiría el
dictamen.

La explicación determinista actual seguirá siendo la referencia funcional y
el fallback universal. El narrador pretende mejorar legibilidad, no precisión
predictiva.

## Límite de autoridad

La cadena autorizada será:

```text
datos + modelos -> interpretación determinista -> dictamen estructurado
                                             -> narrador local opcional
```

El LLM nunca podrá:

- cambiar `Favorable`, `Incierto`, `Poco probable` o una abstención;
- anular un veto ecológico;
- seleccionar qué estimadores son válidos o ponderarlos;
- presentar un score bruto como probabilidad calibrada;
- inventar lluvia, fechas, estaciones, especies, áreas o porcentajes;
- utilizar información que no figure en la entrada estructurada;
- recibir instrucciones libres del navegador o del usuario.

HA conserva la autoridad sobre UI, políticas, resultados, auditoría y
Diagnostics. El worker continúa siendo una calculadora sustituible.

## Despliegue propuesto

La capacidad será opcional y se negociará, por ejemplo, como
`predictor_narrative_v1`. No se incorporará un modelo pesado dentro de la imagen
base del worker: el runtime de inferencia y sus pesos se instalarán como un
servicio local independiente o un perfil opcional, para no aumentar el tamaño,
arranque y memoria de todos los workers.

M1, M5 u otros workers podrán anunciar la capacidad de forma independiente. Si
el worker seleccionado no la ofrece, está ocupado, excede el tiempo límite o
devuelve una respuesta inválida, HA utilizará inmediatamente el texto
determinista. No habrá fallback a un servicio de Internet.

La elección concreta de motor, modelo, cuantización y presupuesto de memoria se
aplaza hasta medir M1 y M5. Esta propuesta no autoriza descargar ningún modelo.

## Contrato de entrada

El narrador recibirá JSON estructurado, versionado y sin prompt libre. Como
mínimo:

- idioma, especie, área y fecha objetivo;
- dictamen final y color operativo ya decididos;
- compatibilidad y evidencia ecológica;
- episodio de lluvia, retraso, horizonte, estación, distancia y cobertura;
- soporte y consenso estadístico operativo;
- señal experimental, modelos que la sostienen y marca de fuera de dominio;
- rangos visibles autorizados y códigos de razón deterministas;
- versión del contrato de interpretación.

No necesita observaciones originales, credenciales de HA, tokens del worker,
rutas privadas ni acceso a los Parquet.

## Contrato de salida

La respuesta será pequeña y auditable:

- texto narrativo en el idioma solicitado;
- identificador y versión del modelo local;
- versión de plantilla/prompt;
- hash de la entrada estructurada;
- duración de inferencia y, si el runtime los ofrece, tokens de entrada/salida;
- resultado de las validaciones de seguridad.

El texto no sustituirá los campos técnicos ni el dictamen. Se mostrará como
explicación opcional con indicación clara de que está generada localmente.

## Validación y rechazo

Antes de aceptar una narración, el worker y HA comprobarán:

1. tamaño y tiempo máximos;
2. correspondencia del hash y versión del contrato;
3. presencia de todos los números, fechas, estaciones y nombres citados en la
   entrada autorizada;
4. ausencia de contradicciones con el dictamen, veto ecológico, soporte y
   carácter experimental de los shadows;
5. ausencia de instrucciones, enlaces o afirmaciones ajenas al resultado;
6. idioma y formato esperados.

Cualquier incumplimiento descarta la narración completa; no se intentará
repararla mediante otro LLM.

## Caché y observabilidad

La caché se indexará por fingerprint de entrada, idioma, modelo local y versión
de plantilla. Una reconstrucción, reentrenamiento o cambio de interpretación
invalidará naturalmente la entrada.

Diagnostics distinguirá al menos:

- espera de cola del narrador;
- carga fría del modelo;
- inferencia local;
- validación de salida;
- tiempo total añadido;
- hit/miss de caché y motivo de fallback.

El cálculo predictivo no esperará indefinidamente al narrador. El presupuesto
temporal deberá ser corto y configurable por código; el resultado determinista
siempre podrá entregarse sin él.

## Privacidad y seguridad

- Inferencia exclusivamente local y sin llamadas a Internet.
- El proceso del modelo no recibe secretos ni monta los datos de HA.
- Entrada cerrada y serializada por el worker; el navegador no construye el
  prompt.
- Salida tratada como datos no confiables hasta superar validación.
- Logs sin ubicaciones privadas adicionales ni contenido completo del prompt.

## Despliegue gradual

1. Benchmark de memoria, latencia y calidad en M1 y M5 con varios modelos
   pequeños, sin conectarlo a HA.
2. Modo sombra: generar narración y compararla con el texto determinista, sin
   mostrarla al usuario.
3. Evaluación con un conjunto congelado de casos centinela, incluyendo vetos,
   abstenciones, estaciones distintas, OOD y señales experimentales.
4. Visualización opcional en `Consultar fecha`, conservando siempre el texto y
   los datos técnicos deterministas.
5. Solo después, valorar su uso en `Esta semana`, `Por especie` e `Historial`.

## Criterios mínimos de aceptación

- cero cambios de dictamen respecto a la interpretación determinista;
- cero cifras o hechos inventados en el conjunto centinela;
- fallback correcto ante ausencia, timeout, salida inválida y falta de memoria;
- impacto de memoria y latencia medido por separado del Predictor;
- misma respuesta cacheada para la misma entrada y versión;
- funcionamiento completo de HA con workers sin esta capacidad.

Hasta cumplirlos, la explicación determinista seguirá siendo la única salida
operativa.
