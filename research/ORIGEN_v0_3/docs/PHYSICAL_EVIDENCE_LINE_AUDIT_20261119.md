# Auditoría de línea de evidencia física y operativa — Chispazo Clásico

**Fecha de corte:** 2026-11-19  
**Estado:** ACTUALIZACIÓN DOCUMENTAL Y AUDITORÍA DE IMPLEMENTACIÓN; SIN REGISTROS FÍSICOS PRIMARIOS RECIBIDOS; SIN RESULTADO DE SESGO.  
**Clasificación de la línea física:** `BLOCKED_PROVENANCE`.

## 1. Alcance y protección del laboratorio

Esta actualización se limita a fuentes oficiales, documentos operativos publicados, inventario de archivos del repositorio y auditoría estática del evaluador V265. No repite frecuencias, pares, tríos ni transiciones ya cerrados. No ejecuta un nuevo análisis de resultados históricos ni construye números candidatos.

Se mantienen las barreras del proyecto:
- V294 permanece congelado.
- No se modifica `main`.
- El histórico canónico `data/history/Chispazo_through_12249.csv` permanece idéntico.
- No se infiere una ventaja predictiva de la existencia de RFID, tolerancias de peso, máquinas o controles administrativos.

## 2. Identificación correcta de la modalidad

La página oficial clasifica Chispazo dentro de **Sorteos Electrónicos** y separa explícitamente los productos tradicionales. Chispazo usa una máquina para seleccionar cinco números del 1 al 28; el portal publica Chispazo de las Tres a las 15:00 y Chispazo Clásico a las 21:00.

Fuentes:
- [Chispazo — página oficial](https://loterianacional.gob.mx/Chispazo/Chispazo)
- [Normas Sustantivas Vigentes — Lotería Nacional](https://loterianacional.gob.mx/Normateca/Sustantivas?id=2)
- [SGVO-PRO-05 — Procedimiento Sorteos Electrónicos, revisión 39](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)
- [SGVO-PRO-15 — Procedimiento de Preparación y Celebración del Sorteo Tradicional](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_15.pdf)
- [SGVO-PRO-08 — Mantenimiento de equipo e instrumentos de sorteos tradicionales](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_08.pdf)

**Regla de separación:** los expedientes, pesajes, bolas de madera, ábacos, esferas manuales y procedimientos de sorteos tradicionales no se incorporan a la línea de Chispazo. Para Chispazo se aplica la cadena de sorteo electrónico y sus propios registros.

## 3. Hallazgos nuevos en SGVO-PRO-05 vigente

La Normateca identifica SGVO-PRO-05 como norma sustantiva vigente, revisión 39, con última actualización/publicación el **20-03-2026**. Es la fuente operativa prioritaria para este análisis.

### 3.1 Secuencia documentada y disponibilidad temporal

La secuencia pública de actividades es relevante para decidir si una variable puede entrar en una predicción anterior al cierre:

1. **CS-02 — inspección de equipo:** se prepara y verifica el equipo antes de cada sorteo. Si no cumple, se sustituye. El formato CS-02 es el registro de esa inspección.
2. **Confirmación del sorteo y estuche:** antes del apartado “Cierre de Venta”, el representante de Lotería confirma con SEGOB y Dirección General que el número de sorteo y los estuches de esferas correspondan al sorteo.
3. **Cierre de venta:** el representante de TI muestra el estado “Cerrado” de SICAL y verifica fecha, hora, número de sorteo y ventas; se imprime y rubrica el **Sumario de Sorteo (Cierre de Venta)**.
4. **Pesaje:** a continuación, la actividad 5.1 pesa las esferas una por una y en orden numérico; la tira de pesaje es el registro.
5. **Aceptación o sustitución:** si el peso no cumple, se cambia el estuche y el flujo vuelve a la actividad 4.1. Si cumple, la tira se firma y recibe rúbricas de Operaciones, SEGOB y Dirección General.
6. **Carga:** la tira se anexa al Acta y las esferas se colocan en los alimentadores en orden progresivo.
7. **Extracción y verificación:** la máquina mezcla las esferas; los números capturados en exhibidores se registran y cotejan. Después se captura el formato CS-11.

El procedimiento fija el cierre automático de los sorteos nocturnos a las **21:00**, salvo modificación autorizada. El portal también publica el Clásico a las 21:00.

**Consecuencia temporal:** el flujo de SGVO-PRO-05 coloca el cierre (actividad 4) antes del pesaje (actividad 5). Por tanto, el peso medido para el estuche finalmente utilizado **no queda acreditado como dato disponible antes del cierre** por la sola existencia de la tira. Además, si el estuche falla la prueba, puede sustituirse después del cierre. El estuche inicialmente confirmado antes del cierre no necesariamente es el estuche final utilizado. Para cualquier estudio prospectivo se requieren la hora efectiva de cada pesaje, la hora de cada sustitución y la hora en que quedó fijado el estuche definitivo.

No se debe codificar `available_before_close=true` a partir de una suposición, de la fecha impresa en un documento o del orden de un número de concurso.

### 3.2 Umbrales oficiales de pesaje

La política 6 de SGVO-PRO-05 indica:
- **Smartballs:** 4.25–5.25 g por esfera; diferencia máximo-mínimo del conjunto no mayor a 0.30 g.
- **Ping-pong:** 2.30–3.00 g por esfera; diferencia máximo-mínimo no mayor a 0.15 g.
- Si no se cumple, se selecciona otro estuche y se vuelve a pesar.

Estos límites son criterios de aceptación del equipo, **no mediciones observadas de cada concurso ni prueba de probabilidades desiguales**. El procedimiento no identifica públicamente qué tipo de esfera se usó en cada concurso de Chispazo; debe obtenerse del expediente real.

**Inconsistencia editorial detectada:** la actividad 5.2 ordena comprobar los parámetros de peso según la “Política número 8”, pero la política 8 trata la firma electrónica del archivo de participaciones. Los límites de masa están en la política 6. No se corrige por inferencia: debe pedirse aclaración o fe de erratas a Lotería Nacional.

### 3.3 Acta, CS-11 y otros registros

- **Acta de Sorteo:** documento distinto del CS-11. Debe contener lugar, fecha, horario, roles y firmas de los representantes y del inspector SEGOB, resultados e incidencias. Se le anexan los reportes aplicables.
- **CS-11:** el nombre oficial es “Números Ganadores de los Sorteos”. No es el Acta. Se capturan los números, se cotejan contra los exhibidores, se leen en voz alta y se firma/recaba firma de Lotería y SEGOB. El original se anexa al Acta.
- **Tira de pesaje:** se identifica como anexo del Acta y contiene el registro de pesaje individual según el procedimiento. La especificación pública no expone un diccionario completo de campos, resolución, identificador de báscula ni sello de tiempo por esfera.
- **Sumario de cierre:** registra el estado cerrado y datos del sorteo/ventas; es posterior al cierre y no es una covariable física.
- **CS-09:** bitácora de concursos y sorteos. Las incidencias que afecten resultados deben asentarse en el Acta y en CS-09.
- **CS-12 y bitácoras de acceso:** el acceso a la sala se registra; el personal que realiza limpieza o mantenimiento debe anotarse en bitácoras de control de acceso bajo vigilancia. Son fuentes para reconstruir intervenciones y custodia, no mediciones de probabilidad.
- **CS-18:** formato de comunicación de riesgos, útil como registro complementario de debilidades de control.

### 3.4 Video y firma electrónica

SGVO-PRO-05 establece que cámaras de la sala registran los números expresados al capturarse las esferas en los exhibidores y contempla personal de una empresa contratada para la grabación de sorteos. Esto acredita un control de grabación, pero el texto público no garantiza que el archivo conservado cubra íntegramente el pesaje, identificación RFID, carga, sustituciones y extracción, ni publica sus metadatos o plazo de retención.

La “Firma Electrónica” del procedimiento corresponde a archivos de participaciones/cancelaciones y reportes asociados. La firma se graba en dispositivo, se verifica con SEGOB y se deposita en caja de seguridad; el Acta y anexos digitales se resguardan. Es evidencia de integridad de archivos de operación/apuestas, **no una firma de las masas, de la asignación física esfera-número ni de un registro RFID**.

## 4. RFID, máquinas, mantenimiento y calibración

El Informe de Gestión Gubernamental 2018–2024 documenta la entrega en marzo de 2022 de 14 máquinas electrónicas (10 Júpiter, 2 Mercury 5 y 2 Mercury 8), y afirma que máquinas y esferas cuentan con reconocimiento RFID. También identifica a Smartplay International Inc. como proveedor.

Dos límites documentales:
1. El informe dice “10 juegos” para cada uno de siete productos, pero suma 60 juegos; 10 × 7 = 70. La cifra total no es consistente y no se usa como dato analítico.
2. El informe acredita la existencia del sistema RFID, pero no publica IDs de tags, lecturas por concurso, lector/antena, mapeo esfera física ↔ número impreso, fecha/hora de lectura ni bitácora de cambios. Tampoco demuestra que el estuche final y el mapeo sean conocidos antes del cierre.

SGVO-PRO-05 asigna:
- mantenimiento preventivo/correctivo de equipos conforme a calendario anual;
- calibración de las básculas al menos una vez al año (la periodicidad puede cambiar por volumen);
- mantenimiento preventivo/correctivo del set de sorteos conforme a calendario anual.

El Informe de Gestión 2018–2024 también menciona el contrato 058-2024 de mantenimiento preventivo/correctivo de 21 máquinas de sorteos electrónicos, incluyendo Chispazo. Es evidencia de una contratación de servicio, no un historial público por número de serie, fecha, componente, reparación o resultado de prueba.

**No se localizaron públicamente** certificados de calibración por báscula, órdenes de trabajo por máquina, bitácoras de mantenimiento de cada estuche, inventario vigente por número de serie, lecturas RFID por concurso ni expedientes de sustitución/remapeo.

## 5. Conflicto con una copia documental antigua

Se localizó una copia de SGM-PRO-06, “Preparación de Sorteos”, revisión 22, en una ruta antigua de la Normateca. Esa copia:
- menciona Chispazo con 28 esferas;
- da un intervalo de 2.2–2.9 g y rango máximo de 0.15 g;
- indica pesaje “preferentemente” antes de un cierre a las 21:15.

No aparece en la página actual de **Normas Sustantivas Vigentes**, mientras que SGVO-PRO-05 revisión 39 sí aparece actualizado el 20-03-2026. Sus límites y horario difieren de SGVO-PRO-05 y del cierre nocturno a las 21:00 establecido por este último. Por ello, SGM-PRO-06 se conserva como antecedente documental, pero no se usa para fijar los umbrales ni la disponibilidad pre-cierre actual. Se solicita a la entidad confirmar expresamente si sigue teniendo alguna aplicación residual y qué documento gobierna el pesaje de Chispazo.

## 6. Auditoría del evaluador V265

Código auditado: `src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py`  
Git blob SHA-1: `ca83e4af6ccd12f68ff0a725969561254b0be866`.

El evaluador exige por concurso `sphere_set_id`, `machine_id`, `available_before_close`, `close_time_local` y `metadata_known_time_local`, además de cobertura exacta del histórico. Después estima frecuencias históricas de números condicionadas por estuche/máquina y puntúa el conjunto de cinco números.

**No consume ni exige**:
- las 28 masas individuales;
- identificador físico único de cada esfera;
- correspondencia demostrada esfera física ↔ número 1–28;
- tipo de esfera, resolución de medición o identificador de báscula;
- certificado/intervalo de calibración;
- orden de carga o de extracción;
- eventos/lecturas RFID;
- cambios de estuche, remapeos, mantenimiento o incidencias;
- video original o timestamp verificable por una fuente independiente.

Por tanto, V265 es un **proxy histórico de régimen estuche/máquina**, no un evaluador de sesgo físico por masa. El timestamp y el booleano que acepta no autentican por sí solos el origen ni la hora real de disponibilidad.

Se detecta además una brecha de guardrail: el campo `actionable_for_betting` puede activarse con cobertura, media positiva y p-valor Holm, sin exigir el Exact5 anytime e-value ≥20, dos salidas pre-cierre selladas y custodia independiente. Ese booleano no debe usarse para promoción ni para recomendar números. Hasta que el evaluador se endurezca con todos los gates, su salida se limita a investigación retrospectiva de proxies.

El reporte existente `reports/V265_PHYSICAL_REPORT.json` mantiene la decisión `RESEARCH_ONLY_METADATA_REQUIRED`; no contiene mediciones físicas observadas.

## 7. Inventario de datos físicos en el repositorio

En el head auditado:
- `data/physical-metadata/V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv`: sólo encabezado; no contiene observaciones. Su esquema ancho no incluye ID físico por esfera ni mapeo demostrable.
- `data/physical-metadata/PHYSICAL_EVIDENCE_LONG_FORM_TEMPLATE_V1.csv`: sólo encabezado; es el esquema adecuado de captura de una fila por esfera, con identidad, masa, timestamps, calibración y referencia documental.
- `research/ORIGEN_v0_3/src/origen/physical_intake.py`: validador estructural fail-closed; no autentica documentos, firmas, relojes ni certificados.

No hay registros primarios de pesaje, RFID, calibración, mantenimiento, incidencias o video incorporados al repositorio. No se ejecutó un modelo físico porque el conjunto de datos auténticos es vacío. No se generaron predicciones ni se alteró el histórico.

## 8. Pruebas reproducibles ya disponibles

El endurecimiento V320 del validador cubre límites de masa, rango por conjunto, tipo de esfera, mapeo, IDs duplicados, timestamps con zona, calibración, conflictos de máquina/báscula, fechas y preservación de bytes del CSV.

- [ORIGEN aislado — run 44470250160](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44470250160): éxito; 153 pruebas según el registro V320.
- [CI raíz — run 44470250079](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44470250079): éxito; compilación y suite raíz completadas.
- Los fixtures de esas pruebas son sintéticos y sólo prueban el validador. No son registros de Lotería Nacional ni evidencia de sesgo.

## 9. Integridad y hashes

Estado verificado antes de esta actualización documental:
- Research branch `research/origen-v0.3-engine-20261118`: `70c434beefcc96d5307d95c4f71a4bbc5397834c`.
- `main`: `424eee9dd906f8235541e97ae61026441083bbfe`; no se escribió en esta rama.
- PR #8: abierto, draft y sin merge.
- Histórico canónico: 505,274 bytes; Git blob SHA-1 `2f5ff5bfbd779fe505736398e417b7211955958e`; SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`. El blob es idéntico en `main` y en la rama de investigación.
- Plantilla larga: Git blob SHA-1 `743300774be827956e23a1b44787f8def7849a7b` (341 bytes).
- Plantilla V265 ancha: Git blob SHA-1 `4c707be9d7ea643ce6691aabb4a736e724551329` (810 bytes).
- Validador físico: Git blob SHA-1 `dcfe7bf332f67daab153512104ad33e3d7086422`.
- Reporte V265: Git blob SHA-1 `f37ace64bc4c441be5eaf1398f59d9383af64899`.

Los hashes Git de archivos individuales son SHA-1 de objetos Git, no SHA-256 del archivo plano. No se obtuvo el binario original de los PDFs oficiales en este entorno; por tanto no se inventa un SHA-256 para esas fuentes. Sus URLs oficiales y revisiones quedan identificadas arriba.

## 10. Solicitud documental pendiente y decisión

La solicitud de transparencia V2 del repositorio sigue siendo un borrador no presentado. Debe ampliarse con:
1. aclaración formal de la secuencia de pesaje y cierre, y de la referencia errónea a la política 8 en el paso 5.2;
2. CS-02, CS-11, Acta y anexos completos por concurso/modalidad;
3. tira original por concurso con 28 masas, tipo de esfera, resolución, báscula, calibración y hora individual;
4. ID RFID de máquina y esfera, estuche, mapeo físico-número, lecturas RFID y hora de asignación/cambio;
5. orden de carga y secuencia de extracción con marcas temporales;
6. órdenes de mantenimiento, sustituciones, incidencias, CS-09, CS-12 y bitácoras de acceso;
7. grabaciones originales sin edición desde el pesaje hasta la extracción, metadatos y política de conservación;
8. archivos de participaciones/cancelaciones, firmas electrónicas, verificaciones y relación con el concurso, distinguiéndolos de los registros físicos.

**Decisión:** evidencia pública de que existen controles y registros operativos de pesaje, inspección, RFID, video, incidencias y custodia electrónica. No existe todavía evidencia pública a nivel de concurso que enlace, con tiempo verificable, las 28 masas y los IDs físicos con los números 1–28 y el estuche/máquina finalmente usados. Sin ese enlace, no se puede estimar una propensión física por número. La línea sigue **`BLOCKED_PROVENANCE`**, no `EDGE_SUPPORTED`.


## 11. Muestras de transmisiones públicas localizadas

El canal verificado **Lotería Nacional · Sorteos Electrónicos** mantiene al menos grabaciones públicas de emisiones de Chispazo Clásico, por ejemplo:
- [Chispazo Clásico 12168 — 2026-08-03](https://www.youtube.com/watch?v=-VVW2A3JxZI)
- [Chispazo Clásico 12196 — 2026-08-17](https://www.youtube.com/watch?v=4N9VS8ayuVs)

Estos enlaces acreditan disponibilidad de transmisiones públicas de sorteos concretos, no la entrega del archivo maestro de cámara ni de la grabación íntegra de la preparación. En esta actualización no se extrajeron fotogramas ni metadatos de esos videos; por tanto no se afirma ningún orden de extracción, tiempo de pesaje o mapeo esfera-número derivado de ellos. Para un análisis reproducible se requiere descargar/recibir el original con metadatos y verificar continuidad, reloj, hash y correspondencia con el Acta/CS-11 del concurso.


## 12. Contraste adicional con SIDOF/SEGOB: inconsistencia interna del Reglamento Chispazo

Se cotejó el texto del **Reglamento del Concurso Chispazo** publicado por Lotería Nacional (última reforma indicada: 7 de marzo de 2012) con los documentos SIDOF/SEGOB. El PDF consolidado oficial de Lotería presenta una inconsistencia interna:
- Artículo 2: dice que el participante elige dentro de un conjunto de **25 números**.
- Artículo 5: define la selección entre **1 y 28**.
- Artículo 9: dispone introducir **28 esferas** numeradas del 1 al 28 y extraer cinco.
- Artículo 8: establece que el resultado oficial es el asentado en el Acta del artículo 15; los resultados de terminal, teléfono, sitio web y mascarilla son informativos si difieren.

El texto base de 2002 alojado en SIDOF sí describía originalmente 25 esferas; no debe confundirse con el texto consolidado posterior, cuyo artículo 9 fue reformado en 2006 para 28 esferas. El acuerdo de reforma de 2012 en SIDOF modifica artículos de comercialización y otros artículos, pero no corrige la referencia a 25 números del artículo 2. La inconsistencia 25 vs. 28 permanece en el PDF consolidado consultado.

La terminología del artículo 9 habla de “urna”, mientras que la página actual de Chispazo lo clasifica como Sorteo Electrónico y SGVO-PRO-05 revisión 39 describe la operación mediante máquinas de sorteos electrónicos. Para la mecánica operativa actual prevalece la fuente operativa vigente; el reglamento requiere una aclaración/versión consolidada alineada.

Fuentes oficiales:
- [Lotería Nacional — Reglamento Chispazo consolidado, última reforma indicada 07-03-2012](https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf)
- [SIDOF/SEGOB — Reglamento Chispazo, texto base de 2002](https://sidof.segob.gob.mx/notas/docFuente/718656)
- [SIDOF/SEGOB — acuerdo de reforma de 2012](https://sidof.segob.gob.mx/notas/docFuente/5211955)
- [Lotería Nacional — descripción vigente de Chispazo](https://loterianacional.gob.mx/Chispazo/Chispazo)
- [Lotería Nacional — SGVO-PRO-05, revisión 39](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)

Esto es una **inconsistencia normativa/documental**, no evidencia de sesgo ni prueba de incumplimiento. No se usa el texto histórico de 25 esferas para inferir el mecanismo físico actual. La solicitud documental debe pedir aclaración del artículo 2, copia certificada de la versión vigente del Reglamento Chispazo y de todas sus reformas posteriores, así como el fundamento que vincula ese reglamento con SGVO-PRO-05 revisión 39.
