# Ayuda de la regla conjunta de suelo y pH

Guía de Ecología → Suelos, disponible en la misma pantalla mediante **Ayuda: cómo funcionan el suelo y el pH**, en español, catalán e inglés. Funcionamiento contrastado con el código el 14/09/2026.

## pH del suelo

El mínimo y el máximo definen el rango de la especie. En la configuración actual del mapa se compara con la estimación de OpenLandMap; SoilGrids se muestra como comparación. Dentro del rango supera el control; fuera queda incompatible salvo la excepción descrita abajo. Si falta el pH y hay límites, queda con información insuficiente. Un límite vacío significa no definido, no cero. Estos límites siguen funcionando con la regla conjunta desactivada.

## Aplicar regla conjunta de suelo/pH

Activa este bloque para esta especie. En No, no se aplican sus exigencias ni excepciones; siguen funcionando pH, hospedadores o hábitat, altitud y temporada. No es un interruptor que desactive todos los filtros del mapa.

## Exigir tipo de suelo identificado

En Sí, si los mappings GIS no aportan ninguna categoría de suelo, la especie queda con información insuficiente aunque cumpla todo lo demás. En No, la falta de suelo por sí sola no la bloquea. Exige alguna categoría, no necesariamente resolver calizo frente a silíceo. Una litología como conglomerado o brecha no basta si el mapping no aporta una categoría de suelo. No se deduce descalcificación ni se crea una categoría de suelo a partir del pH estimado.

## Suelos de apoyo (lista no exhaustiva)

Son suelos que aportan evidencia favorable. No son los únicos permitidos: encontrar otro suelo no excluye automáticamente la especie y puede dar una admisión condicionada si supera los demás controles. Coincidir con un suelo de apoyo tampoco basta para admitirla. Además, estos suelos pueden permitir la excepción de pH, cuando está activada y se cumplen sus demás condiciones.

## Suelos con admisión condicionada al pH

Si se identifica uno de estos suelos y el pH está dentro del rango, la admisión se señala como condicionada. Por sí solos no permiten rescatar un pH fuera del rango: esa es la función de los suelos de apoyo junto con la excepción. Marcar Calizo aquí no demuestra descalcificación ni lo convierte en un suelo excluido. Tampoco evita un fallo en hospedadores, altitud o temporada.

## Suelos excluidos explícitamente

Estos sí producen exclusión al detectarse. Si una unidad mezcla un suelo excluido y otro de apoyo, el resultado es información insuficiente: no sabemos cuál corresponde exactamente al setal. No se puede guardar el mismo tipo a la vez como excluido y de apoyo, ni como excluido y condicionado. Un incumplimiento de otro control puede mantener el resultado incompatible.

## Si el pH estimado queda fuera del rango

No admitir excepciones mantiene el rechazo del pH fuera del rango. La opción de solapamiento exige todo lo siguiente: suelo de apoyo identificado; ningún suelo excluido ni bloqueador; estimación OpenLandMap con intervalo válido; e intervalo que se solape con el rango de la ficha. No sustituye un pH ausente ni permite saltarse los demás filtros.

## Suelos que bloquean la excepción de pH

Impiden usar la excepción si aparecen en el punto. No equivalen a suelos excluidos: con pH dentro del rango este control no los veta. Por ejemplo, Calizo puede figurar como condicionado y como bloqueador: admite pH dentro del rango, pero no permite rescatar un valor fuera de él.

## Referencia que justifica la regla

Registra el documento o evidencia que justifica la configuración. Es obligatoria para guardar una regla activa y no modifica el cálculo por sí misma.

## Ejemplo de excepción de pH

Ejemplo hipotético: máximo de ficha 6,8, estimación 7,0 e intervalo 6,4–7,6. Con suelo de apoyo, excepción activada y sin bloqueos, puede admitirse de forma condicionada. No amplía el máximo de la ficha ni afirma que el pH real sea 6,4: reconoce incertidumbre. No demuestra descalcificación.

## Diferencia con Soil Affinities y Litología

Las afinidades de debajo describen tipo, relación, procedencia y valor. En el filtro territorial una coincidencia positiva puede indicar preferencia, pero no obliga a pertenecer a esas preferencias. Un valor 0,85 no es un 85 % de probabilidad. Evitar en Litología no se convierte automáticamente en prohibición. Los vetos explícitos se configuran arriba, en Suelos excluidos.

## Si Silíceo ya está en Soil Affinities, ¿por qué repetirlo?

Son dos usos del mismo dato. Silíceo en Soil Affinities describe una preferencia; en el filtro territorial esa preferencia no permite saltarse el límite de pH. Silíceo en Suelos de apoyo autoriza expresamente a usarlo como respaldo para la excepción, si está activada y cumple las demás condiciones. No hace falta ponerlo en ambos para que la especie aparezca en suelo silíceo con pH válido. La segunda selección hace falta para permitir esa excepción. Se separan para no convertir automáticamente una preferencia en permiso para admitir un pH fuera del rango.

## Por qué puede aparecer ou de reig y no aereus

Caso comprobado el 14/09/2026 en 42.02746, 1.73187: ambos cumplían hospedadores, altitud, pH 6,4 y temporada principal. El mapping identificaba brechas y conglomerados, pero no una categoría de suelo. Aereus exigía suelo identificado y quedó con información insuficiente; ou de reig no tenía esa exigencia. Es una diferencia de reglas, no evidencia de ausencia. Con esos datos, poner solo Exigir tipo de suelo identificado en No para aereus elimina ese bloqueo y conserva los demás controles. El ejemplo describe aquella configuración, no fija los valores de las fichas actuales.

## Guardar y resultado en el mapa

Abrir esta ayuda no cambia ni guarda nada. Los ajustes se aplican al pulsar Guardar perfil de especie. Poner Aplicar regla en No y guardar elimina la regla de la ficha; conserva pH y afinidades. Consulta de nuevo el punto para evaluar los cambios. Incompatible y con información insuficiente son resultados distintos, aunque ninguno aparece entre las compatibles. Las descartadas no invocan modelos; las compatibles sin modelo permanecen al final con Sin probabilidad calculada, que no significa cero. La fecha filtra las temporadas principal y secundaria y el predictor calcula la probabilidad temporal.

## Fuentes y mantenimiento

Texto compartido con las claves `ui.soil_help_*` de [mushroom_labels.json](../../mushroom-data/mushroom_labels.json). Mantener esta guía y las traducciones sincronizadas si cambia el comportamiento.

- [Evaluación territorial y validación de reglas](../../rainmapper_core/mushroom_map_ecology.py).
- [Ayuda y controles de la ficha](../../rainmapper-app/app/mushroom_profiles_ui.py).
- [Guardado de la ficha](../../rainmapper-app/app/web_server.py).
