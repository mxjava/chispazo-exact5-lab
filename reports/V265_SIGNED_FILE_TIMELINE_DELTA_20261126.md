# V265 — Corrección de cronología de firmas electrónicas y distribución CS-11
**Corte documental: 27 de noviembre de 2026 · SGVO-PRO-05 revisión 39 · Sólo evidencia oficial pública**

## Hallazgo 1: la firma electrónica de participaciones es post-cierre y pre-sorteo

La lectura conjunta de la política 8 y del Anexo 1 de SGVO-PRO-05 permite precisar esta secuencia:

1. El flujo principal verifica en SICAL que el estado de apuestas sea "Cerrado", y registra fecha, hora, número de sorteo y ventas (actividad 4.1; PDF pp. 12–13).
2. El Anexo 1 verifica primero que el Sumario esté en estado "Cerrado" (actividad 1.1; p. 34).
3. Después recibe las firmas electrónicas de los archivos de Participaciones y Cancelaciones (1.2), copia la firma a la carpeta del sorteo y genera el formato correspondiente (1.3).
4. Para los sorteos nocturnos de las 21:00, la recepción y copia de los archivos de participaciones/cancelaciones de los productos que tuvieron venta en el día se realiza en paralelo.
5. Se comprueba que los archivos no estén dañados, se cargan y se concilian las ventas. Si la firma cambia para sorteos nocturnos ya realizados, se informa al representante de Dirección General y se deja nota al OIC (actividades 1.5–1.11; pp. 34–35).
6. La política 8 establece que el dispositivo con la firma electrónica del archivo de participaciones se entrega al Inspector de SEGOB y se deposita en una caja de seguridad antes de la celebración del sorteo (p. 5).

**Interpretación:** la firma de participaciones/cancelaciones es un control de integridad posterior a la comprobación de cierre SICAL y anterior al sorteo. No es una variable conocida antes del cierre. Tampoco es evidencia física de las esferas.

No se publica el timestamp efectivo de recepción, copia, validación, grabación o depósito. La secuencia normativa no sustituye los logs reales del concurso.

## Hallazgo 2: MJF es un archivo distinto y su tiempo exacto frente al sorteo no está fijado

El procedimiento indica que, al final del día y después de las 21:00, se graban en CD/DVD los archivos de participaciones y cancelaciones con sus firmas; además, se deposita el Archivo Maestro de Transacciones (MJF) con su formato impreso de firma electrónica. El OIC retira posteriormente la información para su resguardo (p. 33; actividad 4.1 de p. 38).

No se debe confundir:
- firma del archivo de participaciones/cancelaciones, custodiada antes de celebrar el sorteo;
- firma de la Relación de Ganadores, generada después de capturar los resultados;
- respaldo diario MJF, grabado después de las 21:00.

El procedimiento no fija el timestamp del depósito MJF respecto al final físico de cada sorteo. Debe pedirse el log de grabación y depósito, no inferirlo de la hora programada.

## Hallazgo 3: corrección de la lectura anterior de CS-11

La revisión completa de la actividad 13.6 (PDF p. 17) resuelve la supuesta ambigüedad que se había reportado el 26 de noviembre. La actividad 13.1 ordena imprimir cuatro ejemplares. La actividad 13.6 ordena sacar tres copias y enumera los tres destinos:

- original para la Subdirección General de Ventas y Operaciones, para anexarlo al Acta;
- copia para el Inspector de SEGOB;
- copia para el representante de la Dirección de Tecnologías de la Información y Telecomunicaciones;
- copia para el operador del área de Control de Datos, para ingresar los números al sistema de Selección de Ganadores.

Por tanto, **la distribución normativa de los cuatro ejemplares sí está enumerada**. Se retira la afirmación anterior de que faltaba el custodio de la tercera copia. Lo que aún no está publicado son las constancias reales de entrega/recepción de cada ejemplar para cada concurso. La corrección no demuestra que los cuatro ejemplares se hayan distribuido en un sorteo particular.

## Efecto temporal

| Registro | Momento normativo | Clasificación para predicción pre-cierre del mismo Clásico |
|---|---|---|
| CS-02 | Inspección antes del cierre | Candidato condicional si el original aporta timestamp, activo y firma verificables |
| Confirmación inicial de estuche | Antes del cierre | Candidato condicional; no equivale al estuche final si hay sustitución |
| Sumario SICAL | Después del cierre | No pre-cierre |
| Firma participaciones/cancelaciones | Después de verificar "Cerrado", antes del sorteo | No pre-cierre |
| Tira de Pesaje | Después del cierre verificado | No pre-cierre para ese concurso |
| CS-11 | Después de extracción/cotejo | Retrospectivo |
| Firma Relación de Ganadores | Después de captura de resultados | Retrospectivo |
| MJF diario | Después de las 21:00 | Relación exacta con el fin físico del sorteo no especificada |
| Mantenimiento/calibración | Depende de orden, certificado y recepción | Candidato sólo si el registro real está vinculado al activo y disponible antes del cierre |

## Fuente oficial primaria

- Normateca Sustantivas Vigentes: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-05 revisión 39, PDF oficial: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Lectura directa de páginas 5–6, 12–17, 24–25, 33–38; actividades 4.1, 5.1–5.6, 13.1–13.6 y Anexo 1 actividades 1.1–1.19.

## Reproducibilidad y límites

El script de auditoría comprueba de forma determinista la transcripción incorporada al repositorio. La prueba compara el JSON guardado con la salida del script.

La prueba no descarga ni autentica el PDF oficial, no valida firmas institucionales y no examina originales de concursos. Es una auditoría de consistencia de la transcripción; la autenticidad documental procede de la URL oficial y la revisión indicada, no del script.

No se obtuvieron logs reales de firma, caja de seguridad, CD/DVD, MJF ni constancias de entrega/recepción de los cuatro ejemplares de CS-11. No se generaron registros sintéticos ni se ejecutó análisis de resultados.

## Dictamen

**Evidencia de mecanismo y custodia normativa, no evidencia de sesgo físico ni ventaja predictiva.** La firma de participaciones es post-cierre/pre-sorteo; la firma de ganadores es postresultado; MJF es respaldo diario posterior a las 21:00 con relación temporal exacta al fin del sorteo no especificada. La distribución de CS-11 está enumerada, pero falta evidencia de entrega/recepción por concurso.

V265 continúa como ASSOCIATION_SCREEN_ONLY; research_edge no autentica procedencia. V294 permanece congelado. El histórico canónico no se modifica. Sin escrituras a main, merge ni promoción. OOS, multiplicidad y anytime e-value siguen sin superar.
