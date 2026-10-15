# Protocolo estadístico confirmatorio Exact5

**Estado: `DRAFT — PENDING INDEPENDENT APPROVAL`. No autoriza iniciar una cohorte ni congelar predicciones.**

Este documento define el diseño que debe aprobarse antes de observar resultados de una cohorte prospectiva. No es una afirmación de ventaja predictiva ni una evaluación de una versión. Los valores de alfa, potencia, efecto mínimo detectable, tamaño de muestra, horizonte, población exacta y regla inferencial siguen pendientes; no deben completarse a partir de resultados ya observados.

En el checkout que motiva este borrador, `docs/STATUS.md` mantiene la producción en `BLOCKED / RESEARCH_ONLY_NO_EDGE`, el histórico versionado termina en el concurso 12249 y el ledger prospectivo no contiene registros efectivos. La reconstrucción histórica del target 12250 no es una observación prospectiva.

## Pregunta, estimando e hipótesis

La pregunta primaria es si, bajo una única versión congelada y una política de registro fijada antes de la cohorte, la probabilidad de que el resultado oficial de un concurso objetivo quede incluido en el portfolio pre-registrado de 30 combinaciones distintas supera la probabilidad nula uniforme provisional.

Para cada target programado `t`, se define:

- `R_t = 1` si existe un registro válido, completo, autenticado y anclado antes del cierre oficial del target; `R_t = 0` si los gates bloquean el registro o falla la congelación.
- `Y_t = 1` si, para `R_t = 1`, la combinación oficial de cinco números coincide exactamente con una de las 30 líneas congeladas; en otro caso `Y_t = 0`.
- `Y_t` no se define como cero cuando `R_t = 0`. Un target bloqueado permanece en el censo y afecta la cobertura, pero no es un intento Exact5 registrado.

El estimando primario es la tasa de `Y_t = 1` entre los registros válidos de la cohorte, bajo la versión y la política de registro preespecificadas. La inferencia debe respetar el mecanismo por el que se producen `R_t`; no se asumirá que una selección de targets con registro exitoso equivale automáticamente a una muestra binomial fija.

Hipótesis unilateral candidata:

```text
H0: p <= p0
H1: p > p0
p0 = 30 / 98,280
```

`p0` es provisional y sólo corresponde a un portfolio con exactamente 30 combinaciones distintas si cada resultado posible de cinco números distintos entre 1 y 28 es equiprobable. La igualdad `30/98,280 = 1/3,276` es combinatoria; no demuestra que el mecanismo oficial produzca resultados uniformes o sorteos independientes. Además, se localizó una discrepancia que debe resolverse: la [página informativa oficial](https://lotenal.gob.mx/Chispazo/Chispazo) describe el conjunto 1–28, mientras que el [texto de reglamento publicado en SIDOF](https://sidof.segob.gob.mx/notas/docFuente/718656) describe un conjunto 1–25. No se presume cuál instrumento o modificación rige hoy. Una persona independiente debe verificar y archivar el reglamento vigente, la modalidad de cada target y los supuestos de uniformidad e independencia antes de aprobar este nulo. Si resultara aplicable un universo distinto de 1–28, se debe detener el diseño: no basta con cambiar `p0`, porque el universo codificado y la validación de portfolios también tendrían que resolverse mediante un cambio gobernado separado. Si no pueden sostenerse los supuestos, este contraste no se ejecuta con ese `p0`.

El código define `DRAW_SIZE = 5`, los números 1 a 28 y `math.comb(28, 5) = 98,280`. El congelador y el evaluador exigen exactamente 30 líneas válidas y distintas. Estas comprobaciones verifican la estructura del portfolio y del espacio codificado, no la equidad del sorteo ni la validez externa de `p0`.

## Población y censo de targets

La población deberá ser una lista de concursos Chispazo futuros que cumplan una definición aprobada de modalidad, calendario y ventana temporal. No se seleccionarán targets después de conocer sus resultados. La modalidad o modalidades incluidas, fecha de inicio, fecha de cierre del calendario y regla para cancelaciones o cambios oficiales están **pendientes** de aprobación.

Antes del primer target, un custodio independiente debe crear, fechar, firmar y anclar un manifiesto con todos los targets programados de la cohorte. El manifiesto debe conservar la identidad del concurso, modalidad, fecha, cutoff oficial y fuente de cada target. Un target sólo entra a la población por la regla fijada en ese manifiesto; una cancelación oficial se clasifica con la regla aprobada y nunca extiende automáticamente la cohorte.

La fecha de inicio y el horizonte deben fijarse antes del primer resultado de la cohorte. Son alternativas de diseño que la revisión debe resolver:

| Decisión pendiente | Alternativas a comparar | Consecuencia que debe aprobarse | Responsable propuesto |
|---|---|---|---|
| Población y comienzo | Una modalidad predefinida o ambas; inicio en fecha calendario futura firmada | Cambia la población y la dependencia entre observaciones; no se permite elegir la modalidad con mejores resultados | Investigador principal y revisor estadístico independiente |
| Horizonte | Ventana calendario fija o número fijo de slots del calendario oficial | Ninguna opción permite extender el estudio después de ver resultados; los targets bloqueados no se reemplazan | Investigador principal y revisor estadístico |
| Cancelaciones/cambio de reglas | Clasificación por regla oficial fijada antes del inicio | Evita retirar targets selectivamente o cambiar el denominador a posteriori | Custodio del censo y revisor independiente |

La cobertura operativa se reportará como:

```text
coverage = número de targets programados con registro válido antes del cutoff
           / total de targets programados en el censo aprobado
```

Se publicarán siempre numerador, denominador y targets bloqueados por causa. Una cobertura baja limita la interpretación operativa aunque el análisis condicional de los registros resulte favorable; cualquier umbral mínimo de cobertura es una decisión pendiente y no se asigna aquí.

## Unidad, endpoint y congelación

La unidad de análisis es un concurso objetivo con un portfolio completo congelado antes del cutoff. El endpoint primario es binario a nivel del portfolio completo: al menos una de sus 30 líneas obtiene una coincidencia Exact5 en ese concurso. Las 30 líneas no son 30 observaciones independientes; para el endpoint sólo producen un `Y_t` por target.

Antes de iniciar se debe congelar una sola versión candidata con:

- SHA completo del commit, árbol tracked limpio, versión del protocolo y versión del entorno/dependencias;
- configuración completa, parámetros, semillas y reglas para cualquier aleatoriedad;
- definición del histórico permitido, corte temporal, hash de los inputs y artefactos de ranking;
- la política exacta de gates, target, hora oficial de cierre y portfolio de 30 líneas distintas;
- procedimiento de generación y verificación que no cambie durante la cohorte.

La versión, configuración y política se aprueban antes del primer target y quedan ligadas al registro y al manifiesto externo. No se cambian parámetros, semillas, selección ni reglas después de conocer cualquier resultado de la cohorte. Una modificación crea una versión distinta; no sustituye ni reinicia retroactivamente la cohorte original.

## Targets bloqueados y fallos operativos

Todos los targets del manifiesto permanecen en el censo, incluidos los bloqueados por gates, fuentes o cutoff inciertos, errores de proceso o fallos de escritura. Un target bloqueado no recibe portfolio ni resultado `Y_t`, no se cuenta como fallo Exact5 y no se reemplaza por otro target. Sí cuenta en el denominador de cobertura.

Cada target tendrá una clasificación de proceso inmutable, como mínimo: `registered_valid`, `no_registration_gate_block`, `freeze_failed`, `registration_integrity_failed`, `evaluation_pending`, `evaluation_complete`, `official_result_corrected` o `cancelled_under_predefined_rule`. La clasificación inicial se registra antes del resultado cuando corresponda; cualquier cambio posterior se añade como evento con fecha, autor, evidencia y motivo, sin borrar la historia anterior.

Un fallo de congelación anterior a una publicación válida significa que no hubo registro. Los temporales, parciales y logs se conservan como incidente, no como portfolio. Si existe registro válido pero falla el evaluador, el target no se elimina: se intenta recuperar la evaluación desde el registro inmutable, el histórico y ranking originales y la fuente oficial. Si sigue sin poder determinarse el endpoint, se informa como faltante y la conclusión confirmatoria queda pendiente o inconclusa según la regla aprobada. No se excluye por análisis de casos completos después de ver resultados. Se presentarán análisis de sensibilidad predefinidos para los endpoints irresueltos; esos límites no convertirán el faltante en un dato observado.

Las correcciones de un resultado oficial se conservan como eventos nuevos con la publicación original, corrección, URLs/capturas, horas y hashes. Antes de iniciar se debe fijar cuál versión oficial y qué ventana de adjudicación alimentan el endpoint primario. Se vuelve a evaluar el mismo registro con la corrección autorizada y se conserva la evaluación previa; nunca se sobrescribe el registro ni se escoge la publicación que favorece la conclusión.

## Método estadístico y supuestos

El contraste binomial unilateral exacto es una **opción candidata**, no una decisión aprobada. Sólo se usará si el revisor demuestra que la distribución de los endpoints que entran al análisis satisface las condiciones del método y que el tamaño `n` del análisis se fija sin selección dependiente de resultados. Para `X` éxitos de `n` targets registrados, el p-valor candidato sería `P[Binomial(n,p0) >= X]`; se reportaría además una estimación de `p` y un intervalo exacto compatible con el método aprobado.

La operación real tiene gates y puede producir un número aleatorio de registros: `R_t` puede depender de información histórica disponible antes del sorteo. Por ello, condicionar sin más el test binomial al número observado de registros no se considera automáticamente válido. Antes de elegir el test, la revisión estadística debe probar su validez para la regla de inclusión, el horizonte y la dependencia entre sorteos. Una alternativa a evaluar es un procedimiento de martingala/e-process válido bajo inclusión predecible y horizonte fijo; su fórmula, hipótesis, calibración y potencia deben quedar escritas y verificadas independientemente antes del primer target. No se habilita detenerse al cruzar un umbral salvo que se elija y apruebe expresamente un método secuencial con control de error correspondiente.

Si se confirma un diseño binomial de `n` fijo, el cálculo prospectivo se documentará con la distribución exacta. Para un alfa candidato `α`, el umbral sería el menor `c` tal que:

```text
P[Binomial(n, p0) >= c] <= α
```

Para una alternativa de planificación `p1 = p0 + Δ`, la potencia sería:

```text
P[Binomial(n, p1) >= c]
```

El tamaño `n` se elige antes de empezar para la potencia y el efecto mínimo detectable aprobados. Estas expresiones no son válidas automáticamente si el registro exitoso tiene tamaño aleatorio o selección dependiente de resultados; en ese caso se debe calcular potencia para el procedimiento aprobado, no reutilizar el cálculo binomial.

La lectura oficial actual del juego y el mecanismo exacto aplicable a cada modalidad se documentarán como evidencia fuente vigente. El sitio informativo oficial describe cinco números elegidos entre 1 y 28, pero esa descripción no demuestra uniformidad estadística ni independencia; tampoco sustituye la verificación del reglamento efectivo. Si las modalidades se combinan, se debe validar que la probabilidad nula y la dependencia sean compatibles con un único análisis; de lo contrario, la población o el método debe ajustarse antes del inicio.

## Alfa, potencia, efecto, muestra y parada: decisiones pendientes

No se aprueba ningún valor en esta tabla. Las opciones son ejemplos de decisiones que el protocolo final debe resolver, no recomendaciones ni parámetros del sistema.

| Parámetro | Opciones/decisión que debe fijarse | Consecuencia estadística | Aprobación requerida |
|---|---|---|---|
| Alfa unilateral familiar | Comparar niveles convencionales como 0.05, 0.01 u otro nivel justificado | Un alfa menor controla más estrictamente falsos positivos y exige más información para la misma potencia | Revisor estadístico independiente y comité del estudio |
| Potencia objetivo | Comparar 80%, 90% u otro valor justificado | Mayor potencia aumenta el tamaño/horizonte requerido para el mismo efecto | Revisor estadístico independiente |
| Efecto mínimo detectable `Δ` | Definir una diferencia absoluta `p1-p0` con relevancia científica/operativa | Un efecto menor requiere una muestra mayor; debe fijarse sin inspeccionar rendimientos observados | Investigador principal y revisor independiente |
| Muestra y horizonte fijo | Definir `n`, fechas de inicio/cierre y población/modalidades | La parada post hoc altera el error tipo I; los targets bloqueados no se reemplazan | Comité del estudio y revisor estadístico |
| Procedimiento inferencial | Binomial fijo si sus supuestos se justifican; método válido para inclusión predecible si no | El método debe corresponder al proceso real de gates, targets y faltantes | Estadístico independiente que no desarrolló el modelo |
| Umbral de cobertura | Definir si es condición para una interpretación operativa | No cambia un endpoint Exact5, pero limita la generalización de una tasa condicional a uso operativo | Comité del estudio, antes de inicio |
| Correcciones y faltantes | Fijar fuente final, ventana de adjudicación, recuperación y sensibilidad | Evita selección de evaluaciones disponibles después de conocer el resultado | Custodio de datos y auditor independiente |

La cohorte termina en la fecha/slot aprobado aunque no alcance la cantidad deseada de registros válidos. No se extiende por falta de potencia observada, por un resultado cercano al umbral ni para esperar un Exact5.

## Multiplicidad y análisis secundarios

El diseño confirmatorio tendrá un solo endpoint primario, un solo contraste y una sola versión candidata. Otros endpoints —hits parciales, métricas de ranking, masa Top30, subgrupos, modalidades o versiones— se etiquetan como secundarios/exploratorios y no justifican la afirmación primaria.

Si antes de iniciar se autorizan varios contrastes, versiones o endpoints confirmatorios, se define la familia de hipótesis y el control de multiplicidad (por ejemplo, asignación de alfa o un procedimiento preespecificado) antes de observar resultados. No se selecciona la versión, semilla, modalidad, fecha, subgrupo, métrica ni análisis que resulte más favorable. Los resultados de versiones distintas no se agrupan como si procedieran de un único sistema congelado.

## Desviaciones y análisis de sensibilidad

Una desviación es cualquier diferencia del manifiesto o del protocolo aprobado: cambio de versión/configuración, cutoff no demostrado, target omitido, registro tardío, input alterado, fallo de hash, cambio de reglas, corrección oficial, dato de resultado no verificable, duplicación de evaluación, falta de archivo, cambio de adjudicación o ruptura del horizonte.

Cada desviación se agrega al registro de incidentes con hora, responsable, artefactos y hashes, causa, impacto, decisión independiente y vínculo al target. No se corrige el protocolo retrospectivamente para el mismo target. Los análisis de sensibilidad se enumeran antes de la cohorte y no sustituyen el resultado primario: deben contemplar, según el método aprobado, targets con correcciones, resultados faltantes, cambios regulatorios y supuestos alternativos sobre uniformidad/dependencia. Si un supuesto esencial no se sostiene, la conclusión se limita a descripción o se declara no evaluable.

## Revisión, aprobación y publicación

Antes del primer target deben aprobar y firmar el protocolo, el censo/horizonte, la versión y hashes, el plan estadístico, la fuente oficial del reglamento, el proceso de cutoff/timestamp externo, el esquema de faltantes/correcciones y el formato del informe:

1. investigador principal responsable de la cohorte;
2. estadístico independiente del desarrollo y selección del modelo, que verifique el nulo, la inclusión por gates, el método, alfa, potencia, efecto y muestra;
3. auditor/custodio independiente de registros, evidencia fuente, ledger y reconciliación de todos los targets;
4. responsable de verificar el reglamento/mecanismo oficial y su aplicabilidad a las modalidades incluidas.

La aprobación debe quedar fechada, firmada y anclada junto con los SHA del protocolo, software y manifiesto. Una revisión automatizada o el paso de CI no sustituye estas firmas. Hasta que todas estén disponibles y los gates operativos cambien mediante el proceso gobernado, no se inicia la cohorte.

Se publicará un informe final independientemente del resultado, incluyendo resultados positivos, negativos, inconclusos y operativamente fallidos. El informe mostrará el censo completo, targets registrados y bloqueados, cobertura, registros válidos, evaluaciones completas/faltantes, correcciones, desviaciones, endpoint primario, método, hipótesis, estimación e intervalo, valor p o medida secuencial según el plan, alfa, potencia, efecto objetivo, todos los análisis secundarios y hashes de las fuentes. Un CI exitoso, la integridad de un registro, una prueba histórica, un Exact5 aislado o la ausencia de fallas no demuestra ventaja predictiva.

## Decisiones no aprobadas y bloqueos actuales

| Decisión/bloqueo | Estado actual | Responsable para cerrar |
|---|---|---|
| Nulo de 5/28, uniformidad e independencia/ley condicional del sorteo | `PENDIENTE`; comprobar reglamento vigente, modalidad y evidencia independiente del mecanismo | Revisor externo de reglas y estadístico independiente |
| Versión exacta candidata y autorización de producción | `PENDIENTE`; `docs/STATUS.md` indica `BLOCKED / RESEARCH_ONLY_NO_EDGE` | Gobernanza de modelos y auditoría independiente |
| Modalidades, comienzo, horizonte y censo completo | `PENDIENTE`; el histórico disponible acaba en 12249 y no hay cohorte actual | Investigador principal y custodio del censo |
| Alfa, potencia, `Δ`, tamaño, método inferencial y regla de parada | `PENDIENTE`; no hay valores aprobados | Estadístico independiente y comité del estudio |
| Cutoff por target y anclaje temporal externo | `PENDIENTE` | Custodio de evidencia y auditor independiente |
| Operación del ledger y cobertura inicial | Ledger efectivo vacío; no se han creado registros para este diseño | Responsable operativo, después de superar los gates |

V294 permanece congelada, V304 rechazada y V312/V313 en shadow. Este documento no cambia esos estados ni autoriza jugar, desplegar o registrar una predicción. No contiene ni genera datos prospectivos.

## Referencias técnicas y fuentes por verificar

- Código del espacio y tamaño del portfolio: `src/v264/CHISPAZO_V264_PARENT_REPAIR.py`, `src/pipeline/freeze_prediction.py` y `src/pipeline/evaluate_registration.py`.
- Estado de evidencia del checkout: `docs/STATUS.md` y `docs/VALIDATION_12250.md`.
- Información oficial de Chispazo que debe volver a verificarse antes de cada cohorte: [Lotería Nacional — Chispazo](https://lotenal.gob.mx/Chispazo/Chispazo) y [resultados oficiales](https://comercializadores.pronosticos.gob.mx/Chispazo/Resultados). Estas páginas informativas no prueban por sí solas uniformidad ni independencia.
- Referencia de software para el contraste binomial exacto: [R `stats::binom.test`](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html).
- Referencia metodológica para procedimientos time-uniformes basados en martingalas, si el diseño de inclusión lo requiere: [Howard et al., *Time-uniform, nonparametric, nonasymptotic confidence sequences*](https://doi.org/10.1214/20-AOS1991). La selección y calibración del método para esta cohorte quedan sujetas a revisión estadística independiente.
