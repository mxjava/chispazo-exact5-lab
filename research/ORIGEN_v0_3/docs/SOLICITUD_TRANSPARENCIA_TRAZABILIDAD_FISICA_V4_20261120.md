# Solicitud técnica de información — trazabilidad física Chispazo (v4)

**Fecha de preparación:** 20-11-2026  
**Estado:** BORRADOR PARA PRESENTAR; no enviada.  
**Objeto:** obtener registros primarios para comprobar o descartar una asociación física reproducible con la extracción. La solicitud no presupone sesgo y no pide datos personales innecesarios.

## 1. Base documental y precisión temporal

La referencia pública vigente localizada es **SGVO-PRO-05, Procedimiento Sorteos Electrónicos, revisión 39, publicada el 20-03-2026**:

https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

En su secuencia de actividades, el procedimiento coloca primero el cierre de ventas (actividad 4.1) y después el pesaje y colocación de esferas (actividad 5.1 en adelante). La actividad 5.1 describe el pesaje una por una y en orden numérico; las actividades 5.4–5.5 prevén firmas/rúbricas y anexar la tira al Acta. La política 9 establece los horarios de cierre. Por ello, **no se presume que las masas del mismo concurso estuvieran disponibles antes del cierre**.

Se solicita que la institución confirme el orden y las horas efectivas con los registros originales. Si alguna medición, asignación de estuche o correspondencia física-numérica se fijó antes del cierre, deberá identificarse el documento y su marca temporal que lo pruebe. Una medición posterior al cierre, aunque sea anterior al inicio material de la extracción, no se considera disponible para predecir ese mismo concurso antes del cierre de ventas.

La Normateca de proyectos también lista un archivo `sgvo_man_02p.pdf` titulado *Manual de Apoyo para la Operación de Sorteos y Equipos Electrónicos*, pero el propio PDF aparece como `TIPO: RESERVADO` y revisión 09. No se invoca como norma vigente. Se solicita la versión actualmente autorizada y su estatus:

https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0

## 2. Universo solicitado

Desde el 25-09-2017 hasta la fecha de respuesta, para cada concurso de Chispazo, con identificación expresa de número, fecha y modalidad (**Clásico** o **De las Tres**). El análisis principal del laboratorio se limita a Clásico; se solicita De las Tres como control operativo sólo si utiliza el mismo tipo de equipo, estuche, báscula o proceso.

Si el volumen impide una entrega integral, entregar primero los 100 concursos Clásicos más recientes con expediente completo, además del inventario del universo documental, periodo de conservación, formatos disponibles y documentos inexistentes/dados de baja. Una entrega parcial deberá identificarse como tal y no presentarse como universo completo.

## 3. Registros por concurso

### A. Cronología completa y cierre de ventas

Para cada concurso, entregar los registros originales o copias legibles que permitan reconstruir:

- hora programada y hora efectiva del cierre automático de ventas;
- pantalla/registro SICAL que acredita estado `Cerrado`, fecha, hora, número de concurso y ventas;
- hora de inicio y fin del pesaje;
- hora de cada medición individual, si el sistema la registra; si sólo existe hora inicial/final de la tira, indicarlo expresamente;
- hora de impresión/cierre de la tira, firma y rúbricas;
- hora de traslado y colocación de esferas en alimentadores;
- hora de inicio efectivo de la extracción y hora de publicación/captura de resultados;
- zona horaria, fuente de reloj, sincronización y cualquier corrección de hora.

**Pregunta expresa:** ¿Existe alguna medición individual, asignación del estuche/máquina o correspondencia esfera-número que quede fijada y disponible antes del cierre de ventas? Si la respuesta es sí, entregar el registro y la evidencia temporal. Si la respuesta es no, confirmar que el pesaje del concurso se realiza después del cierre conforme a la secuencia de SGVO-PRO-05.

### B. Tira de pesaje completa

- Tira original completa con el peso individual de las 28 esferas, unidad, precisión/resolución y orden de impresión.
- Peso mínimo, máximo, promedio, rango, número de objetos y resultado de aceptación/rechazo.
- Tipo de esfera (Smartballs/Ping Pong), identificador de estuche y concurso/modalidad.
- Hora inicial y final impresa por la báscula, si se genera.
- Firmas/rúbricas requeridas y constancia de revisión; pueden testarse nombres y firmas autógrafas en versión pública, preservando rol, folio, fecha y existencia de validación.
- Tiras de estuches rechazados, re-pesajes, selección de estuche sustituto y motivo.

### C. Identidad física y correspondencia con números

- Identificador físico individual de cada esfera, si existe, y correspondencia exacta con el número impreso 1–28.
- Si no existe identificador físico único, describir el método documentado para preservar identidad desde el pesaje hasta la carga y extracción.
- Número de estuche, orden de pesaje, posición/orden de carga en alimentador y cambios de orden.
- Formato CS-11 completo y sus anexos; el procedimiento indica que se verifica fecha, número de sorteo, número de estuche y correspondencia esfera-versus-número.
- Sustituciones, remapeos, cambios de estuche, cambios de máquina y correspondencia antes/después, con hora y motivo.

### D. Equipo y metrología

- Marca, modelo, identificador y número de serie de báscula; resolución, precisión e incertidumbre declarada.
- Certificado de calibración vigente para la fecha de cada pesaje, trazabilidad, tolerancia y fechas de validez. La política 25 de SGVO-PRO-05 establece calibración de básculas al menos una vez al año; entregar el calendario anual, certificados y evidencia de cualquier calibración extraordinaria.
- Inspecciones, mantenimiento, ajustes, fallas y sustituciones de báscula.
- Identificador/modelo/serie de máquina, alimentador y equipo de esferas utilizados en cada concurso.
- Confirmación del tipo de esfera y límites operativos aplicados.

### E. Acta y archivo de participaciones

- Acta completa del sorteo y anexos, vinculados por concurso y modalidad.
- Sumario de sorteo (cierre de ventas), CS-11, tira de pesaje y reportes de cierre.
- Grabación original íntegra desde el pesaje hasta la celebración del sorteo, con archivos fuente, metadatos, identificador de cámara, timecode, sincronización del reloj, fecha de edición y hash disponible. Entregar también el fragmento editado que se incorporó al Acta y la cadena de custodia/retención del original; si el original no se conserva, informarlo expresamente.
- Archivo de participaciones/cancelaciones y su firma electrónica: identificador, tamaño, hash disponible, fecha/hora de generación y firma, certificado/cadena de confianza y validación.
- Constancia de entrega al Inspector de SEGOB, folio, dispositivo, depósito en caja de seguridad, sello/bitácora de custodia y accesos/retiros por el Órgano Interno de Control.
- Confirmación expresa de si la firma electrónica del archivo se genera inmediatamente después del cierre, como indica el Anexo 1 de SGVO-PRO-05, y de qué hora se dispone para acreditar cada paso.
- Distinguir este archivo de participaciones de cualquier dato físico de esferas; su custodia posterior al cierre no demuestra que las masas estuvieran disponibles antes del cierre.

### F. Archivo de reportes e incidencias

- Respaldo semanal previsto por la política 12, índice del DVD/dispositivo y lista de reportes por concurso.
- Reportes Chispazo `CLSBR140` (Relación de Ganadores) y `CLSAR110` (Máscara Ganadora), sumario de sorteo, CS-11 y anexos.
- Actas, bitácoras e incidencias CS-09; comunicaciones de riesgo CS-18; registros de acceso a sala CS-12; bitácoras de limpieza/mantenimiento; y registros de grabación de cámaras desde el pesaje hasta el sorteo.
- Si un Acta se firmó después, bitácora y justificación del diferimiento conforme a la política aplicable.

## 4. Aclaración normativa solicitada

En SGVO-PRO-05 revisión 39, la actividad 5.2 y el plan de calidad parecen remitir a la “Política número 8” para verificar los parámetros de peso; sin embargo, los límites de peso se encuentran en la política 6 y la política 8 trata de la firma electrónica del archivo de participaciones. Se solicita:

1. confirmar cuál es la referencia normativa correcta;
2. informar si existe fe de erratas, aclaración o versión corregida;
3. entregar la versión autorizada vigente del Manual SGVO-MAN-02 o confirmar que el archivo de proyecto `sgvo_man_02p.pdf` no es la versión operativa vigente.

Esta pregunta identifica una inconsistencia de referencias del documento; no presupone incumplimiento en la operación.

## 5. Integridad, formato y conservación

- Preferencia por CSV/XLSX para tablas y PDF nativo o escaneo legible para actas, tiras y constancias.
- Preservar bytes originales, metadatos, folios, marcas de tiempo, hashes existentes y vínculo entre documentos.
- Entregar catálogo de campos/diccionario de datos y reglas de conservación.
- Indicar expresamente documentos no generados, no localizados, dados de baja o no conservados, junto con periodo de retención y fundamento.
- Entregar versión pública con datos personales testados, preservando identificadores técnicos, roles, folios, fechas, marcas temporales y evidencia de existencia/validación de firmas.

## 6. Preguntas críticas

1. ¿El pesaje del concurso ocurre después del cierre automático de ventas? ¿Qué registros acreditan la hora exacta?
2. ¿Existe alguna masa o mapping del mismo concurso disponible antes del cierre? ¿Cuál es su evidencia primaria?
3. ¿La identidad esfera física ↔ número impreso es estable entre concursos o se verifica por concurso mediante CS-11?
4. ¿Existe identificador físico único por esfera? Si no, ¿cómo se mantiene la identidad tras pesar y cargar?
5. ¿Qué documento prueba cuándo se asignaron estuche y máquina?
6. ¿Se conservan todos los estuches rechazados, re-pesajes, sustituciones y remapeos?
7. ¿Qué versión autorizada del Manual SGVO-MAN-02 rige actualmente?
8. ¿Qué registros permiten distinguir sin ambigüedad Clásico de De las Tres?

## 7. Uso científico y límites

La solicitud busca registros operativos, no prueba un sesgo. Para un predictor del mismo concurso, una variable sólo es elegible si se demuestra que estaba disponible antes del cierre de ventas. Los registros de pesaje generados después del cierre no pueden convertirse retrospectivamente en características pre-cierre.

Si las masas sólo están disponibles después del cierre, una hipótesis sobre el concurso siguiente requeriría demostrar continuidad del mismo conjunto físico, mapping esfera-número, máquina/feeder y calibración antes del siguiente cierre. Ese diseño tendría que preregistrarse por separado; no se permite reparar retrospectivamente una especificación temporal incompatible ni elegir números con información posterior al cierre.

Al recibir los registros, se preservarán originales inmutables, se calcularán hashes, se validará metrología y cadena documental, y se excluirá cualquier fila sin modalidad, mapping o cronología acreditada. No se retuneará V294 ni se afirmará ventaja sin evaluación prospectiva independiente.

**Esta solicitud es un borrador. No ha sido presentada ni enviada por el laboratorio.**
