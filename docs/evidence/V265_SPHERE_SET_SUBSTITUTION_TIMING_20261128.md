# V265 — temporalidad del estuche: selección inicial frente a estuche efectivamente usado
**Corte: 28 de noviembre de 2026 · Chispazo Clásico electrónico**

## Fuentes oficiales y alcance

La Normateca vigente identifica SGVO-PRO-05, revisión 39, como el procedimiento para sorteos electrónicos y Chispazo aparece dentro de esa familia. La página oficial de Chispazo lo clasifica expresamente como sorteo electrónico y fija el Clásico a las 21:00. Este análisis no usa procedimientos de sorteos tradicionales.

- Normateca sustantiva vigente: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- Proyectos normativos históricos: https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0
- SGVO-PRO-05, revisión 39: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SGVO-PRO-28, alcance de fallas en motor de Esfera Mayor: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_28.pdf
- Chispazo oficial: https://www.loterianacional.gob.mx/Chispazo/Chispazo

## Estado del Manual de Apoyo SGVO-MAN-02

La Normateca de **Sustantivas Vigentes** lista SGVO-PRO-05, pero no lista el Manual de Apoyo para la Operación de Sorteos y Equipos Electrónicos (SGVO-MAN-02). Ese manual aparece en **Proyectos Normativos Históricas** con inicio 23/02/2026, fin 04/03/2026 y archivo identificado como sgvo_man_02p.pdf. Por tanto, la entrada acredita que hubo un proyecto publicado para revisión, no que exista una versión aprobada vigente. El contenido del PDF de proyecto no se obtuvo en esta revisión y no se usa como instrucción operativa.

SGVO-PRO-05 remite al Manual de Apoyo para detalles de operación e inspección; al no localizarse ese manual en la lista vigente, los detalles técnicos completos de CS-02, identificación de activos y ejecución del pesaje siguen siendo un bloqueo documental. No se debe llenar ese vacío con el borrador del proyecto ni con procedimientos de sorteos tradicionales.

## Exclusión estricta de procedimientos tradicionales

SGVO-PRO-28 tiene un nombre que podría inducir a confusión (“fallas en el motor de la esfera”), pero su propio alcance lo define para la Esfera Mayor y para sorteos tradicionales o los que sigan los mismos principios; además, lo asigna exclusivamente a áreas de Sorteos Tradicionales y Boleo. No se usa para inferir el mecanismo de extracción de Chispazo electrónico. La Normateca también identifica SGVO-PRO-08, SGVO-PRO-34 y SGVO-PRO-15 como procedimientos de sorteos tradicionales.

## Secuencia normativa relevante

1. **CS-02, antes del cierre:** la actividad 2.1 prepara y verifica el estado del equipo; si no está en buen estado, la actividad 2.2 ordena sustituirlo y volver a inspeccionar. El Plan de Calidad exige CS-02 antes de cada sorteo y contempla sustituir equipo o báscula si un elemento no cumple.
2. **Estuche inicial, antes del cierre:** la actividad 3.1 confirma con el Inspector SEGOB y el representante de la Dirección General que el número de sorteo y el estuche de esferas correspondan al sorteo.
3. **Cierre:** la actividad 4.1 comprueba que SICAL muestre Estado de Apuestas = Cerrado y verifica fecha, hora, número de sorteo y ventas.
4. **Pesaje, después del cierre:** la actividad 5.1 pesa las esferas una por una y en orden numérico. La Tira de Pesaje registra el peso de cada esfera y la firman el responsable del pesaje, el representante de la Dirección de Operación de Concursos, Juegos y Sorteos, el representante de la Dirección General y el Inspector SEGOB.
5. **Sustitución posterior al cierre:** si el peso no es correcto, la actividad 5.3 notifica y cambia el estuche, regresando a la actividad 4.1. Por tanto, el estuche final puede diferir del estuche confirmado antes del cierre.
6. **Aceptación y carga:** si el peso es correcto, se firma la Tira, se anexa al Acta y se depositan las esferas en los alimentadores.
7. **CS-11 retrospectivo:** el glosario define el CS-11 con fecha, nombre y número del sorteo, hora de realización, estuche seleccionado, resultados y nombres/firmas de elaboración, verificación, certificación y representante de la Dirección General. Se captura después de que las esferas aparecen en los exhibidores y se cotejan los números; no es una fuente pre-cierre.

## Consecuencia para datos y predicción

Hay dos variables distintas que el esquema actual no separa:

- **planned_sphere_set_id**: estuche confirmado antes del cierre en la actividad 3.1.
- **actual_sphere_set_id**: estuche que finalmente alimentó la máquina después del pesaje y de cualquier sustitución.

La primera puede ser una covariable prospectiva del mismo concurso únicamente si existe registro auténtico con timestamp anterior al cierre. La segunda puede conocerse después del cierre y antes de la extracción, pero no sirve para apostar ese mismo concurso porque las ventas ya están cerradas. Si se toma del CS-11, además, su fuente es posterior al resultado. Puede utilizarse en análisis explicativo retrospectivo, nunca retroinsertarse como predictor pre-cierre.

Si no hubo sustitución, ambos IDs podrían coincidir; no se debe asumir que siempre coinciden. La norma contempla explícitamente una sustitución después del cierre cuando el pesaje no cumple. No se obtuvo ningún CS-02, Tira de Pesaje ni CS-11 original de concurso que permita estimar la frecuencia real de sustitución.

## Hallazgo del contrato V265

V265 exige un único **sphere_set_id** junto con **available_before_close**, **close_time_local** y **metadata_known_time_local**. El código exige que el timestamp declarado preceda al cierre, pero no define si **sphere_set_id** significa estuche inicialmente planeado o estuche efectivamente usado. Tampoco tiene campos separados para sustitución, hora, causa, ID anterior y nuevo.

Esto es una **ambigüedad de exposición**, no una prueba de sesgo. Si **sphere_set_id** proviene del CS-11, es retrospectivo y no debe pasar como pre-cierre. Si proviene de la confirmación de la actividad 3.1, representa el plan inicial; no representa el estuche final en los concursos donde hubo sustitución. Una fecha declarada en un CSV no autentica el origen ni el significado del ID.

El guard de V265 permanece: **physical_bias_evidence=false**, **actionable_for_betting=false**, sin pesos por esfera, mapeo RFID esfera-número, orden de extracción, timestamps individuales ni procedencia autenticada. No implementa el gate anytime e-value.

## Contrato mínimo requerido antes de reabrir evaluación

Por concurso se necesitan campos separados y respaldados por originales:

- ID y timestamp de la selección/confirmación inicial antes del cierre.
- ID final del estuche efectivamente cargado.
- Indicador de sustitución, timestamp, motivo, ID anterior/nuevo y firmas de autorización.
- Tira de Pesaje con peso individual por esfera, correspondencia esfera-número, orden, báscula/serie y firmas.
- Logs RFID que distingan lectura de máquina, estuche y cada esfera, y que acrediten si registran o no orden/timestamp por extracción.
- Video original continuo y cadena de custodia para contrastar el orden de carga y la ejecución.

La evaluación prospectiva debe puntuar sólo la información autenticada que existía antes del cierre. El estuche final y los pesos posteriores al cierre pueden formar un conjunto de auditoría/explicación separado. Cualquier alegación de ventaja seguirá bloqueada hasta OOS, multiplicidad y anytime e-value.

## Clasificación

**DOCUMENTED_MECHANISM_ONLY / EXPOSURE_SCHEMA_AMBIGUITY**. No se analizaron resultados, frecuencias, pares, tríos ni transiciones. No se usaron registros sintéticos. No se obtuvieron datos originales por concurso. No se afirma sesgo físico ni ventaja predictiva.
