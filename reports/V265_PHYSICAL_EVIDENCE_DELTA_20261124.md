# V265 — Actualización de evidencia física y operativa de Chispazo Clásico
**Corte documental: 2026-11-24**

## Resultado nuevo

Esta actualización reconcilia la versión vigente de SGVO-PRO-05 con el Reglamento específico de Chispazo, la lista actual de Normateca, el manual de apoyo que sigue listado como proyecto/reservado, una copia histórica de SGM-PRO-06 y el informe institucional RFID 2018–2024.

No se obtuvieron registros físicos por concurso. No se analizaron resultados, frecuencias, pares, tríos ni transiciones. La clasificación es **MECHANISM_DOCUMENTATION_ONLY**, no sesgo físico ni ventaja predictiva.

## 1. Estado normativo: qué sí es vigente y qué no

1. **SGVO-PRO-05, revisión 39, DN-07 v09** aparece en la lista actual de Normas Sustantivas Vigentes, con actualización 20-03-2026. Es el procedimiento operativo de referencia para sorteos electrónicos.
2. **SGVO-MAN-02, Manual de Apoyo para la Operación de Sorteos y Equipos Electrónicos**, aparece en Normateca bajo Proyectos Normativos (23-02-2026 a 04-03-2026). El PDF consultable se identifica como tipo **RESERVADO**, revisión 09. No se debe tratar como manual público vigente ni usar sus detalles técnicos para certificar la operación actual.
3. **SGM-PRO-06, Preparación de Sorteos, revisión 22, DN-07 v05** sigue accesible en una URL cuyo directorio contiene `VIGENTES`, pero no aparece en el índice actual de Normas Sustantivas Vigentes. Su último cambio identificado es junio de 2017. Debe clasificarse como copia pública histórica/no indexada, no como autoridad operativa actual.

La existencia de un archivo en un directorio con nombre `VIGENTES` no sustituye su inclusión en la lista normativa actual. Tampoco se deben confundir SGM-PRO-06 y SGVO-MAN-02: son documentos diferentes.

## 2. Cronología vigente de SGVO-PRO-05

La revisión 39 establece la siguiente secuencia:

1. CS-02: inspección del funcionamiento de equipos antes de cada sorteo.
2. Actividad 3.1: se confirman número de sorteo y estuche inicial con el Inspector de SEGOB.
3. Actividad 4.1: se muestra el estado SICAL `Cerrado`; se verifican fecha, hora, número de sorteo y ventas y se imprime el Sumario de cierre.
4. Actividad 5.1: después de esa verificación se pesan las esferas una por una y en orden numérico.
5. Actividad 5.2: se verifican los límites de peso.
6. Actividad 5.3: si el estuche no cumple, se sustituye y se regresa a actividad 4.1. El procedimiento no dice que se reabran ventas.
7. Se firma la Tira, se integra al Acta y se colocan las esferas en los alimentadores en orden progresivo.
8. Se verifica la correspondencia de las esferas colocadas.
9. Se realiza la extracción; CS-11 se captura, lee en voz alta y verifica frente a representantes e Inspector.
10. Se integra y firma el Acta con resultados e incidencias.

### Límites de peso vigentes — Política 6

- Ping Pong: 2.30–3.00 g por esfera; diferencia máxima del conjunto 0.15 g.
- Smartballs: 4.25–5.25 g por esfera; diferencia máxima del conjunto 0.30 g.

SGVO-PRO-05 no publica una correspondencia por concurso entre máquina Chispazo y tipo de esfera. No se debe inferir que todas las máquinas Chispazo utilizan el mismo tipo.

### Defecto de referencia cruzada

La actividad 5.2 y el punto 2 del Plan de Calidad remiten a la Política 8 para revisar el peso. Los límites están en Política 6. La Política 8 regula la firma electrónica del archivo de participaciones. Es un error editorial verificable; no cambia los valores expresamente escritos en Política 6.

## 3. Cronología aún no resuelta entre Reglamento y procedimiento

El artículo 9 del Reglamento Chispazo dice que las 28 esferas se introducen en una urna antes del cierre de ventas; después se cierra la captación, se genera y firma el archivo de participaciones y se extraen cinco esferas.

SGVO-PRO-05, en cambio, verifica primero el cierre SICAL y después pesa las esferas y las coloca en los alimentadores.

No se puede resolver esta diferencia suponiendo que `urna` y `alimentadores` son el mismo componente o que describen la misma etapa. La copia histórica SGM-PRO-06 rev22 añade que Chispazo se pesaría **preferentemente** antes del cierre que allí aparece como 21:15; no es la norma actual indexada y no desplaza el cierre nocturno de 21:00 en SGVO-PRO-05.

**Dictamen temporal:** bajo la secuencia vigente SGVO-PRO-05, el peso del mismo sorteo es post-cierre. El Reglamento y la documentación histórica exigen aclarar por escrito el significado físico de urna, estuche y alimentadores y cuál es el orden real ejecutado. No se habilita el peso del mismo sorteo como predictor pre-cierre.

## 4. Tira de Pesaje: qué está documentado y qué no

La definición pública vigente de SGVO-PRO-05 dice que la Tira registra el peso de cada esfera y debe ser firmada por:
- responsable del pesaje;
- representante de la Dirección de Operación de Concursos, Juegos y Sorteos;
- representante de la Dirección General;
- Inspector de SEGOB.

El procedimiento vigente no especifica en su esquema público campos de:
- fecha/hora de inicio y fin;
- número de esfera impreso junto a cada peso;
- RFID individual;
- mapeo RFID-número;
- orden de extracción;
- timestamp por extracción.

La copia histórica SGM-PRO-06 rev22 sí describe, para sus instrucciones de báscula, impresión de fecha/hora al inicio y al final, peso individual y estadísticos (cantidad, promedio, máximo, mínimo y dispersión). También describe 28 esferas Chispazo y colores amarillo/azul según máquina. Es información útil para orientar una solicitud de expedientes, pero su estatus actual no está confirmado. No se debe atribuir ese esquema a la Tira actual sin obtener el manual aprobado y los originales.

## 5. CS-02 y manual de apoyo

SGVO-PRO-05 requiere inspección diaria del equipo antes de cada sorteo y prevé sustituir equipo/báscula si no cumple. El procedimiento remite al Manual de Apoyo para los detalles, pero ese manual SGVO-MAN-02 aparece como proyecto/reservado en la Normateca consultada.

Los detalles de presión de compresor 27–30 psi y la lista técnica extensa de componentes provienen de la copia histórica SGM-PRO-06 rev22, no de una ficha CS-02 actual aprobada y listada. No se usan como límites vigentes.

Se necesita el CS-02 original de cada concurso, con número/serie de máquina y báscula, hora, responsable, resultado y observaciones, junto con el manual controlado y vigente.

## 6. CS-11 no es el Acta

La norma llama al CS-11 **“Números Ganadores de los Sorteos”**. Es un formato que se integra al expediente y se adjunta al Acta; no es el Acta misma.

CS-11 registra fecha, nombre y número de sorteo, hora, estuche seleccionado, resultados y firmas de elaboración, verificación, certificación y representación de Dirección General. El Plan de Calidad verifica además fecha, número de sorteo, número de estuche, correspondencia esferas/números y nombres de participantes.

Se genera después de la extracción. Por ello no es una variable pre-cierre del mismo sorteo.

El Reglamento establece que el resultado jurídicamente oficial es el asentado en el Acta; la web, terminal, teléfono y mascarilla son informativos. Para reconstruir el resultado legal deben recuperarse Acta y anexos originales.

## 7. RFID: dato institucional y límite de identificación

El Informe de Gestión Gubernamental 2018–2024 (p. 43) declara:
- 10 máquinas Júpiter, 2 Mercury 5 y 2 Mercury 8: 14 entregadas el 07-03-2022;
- instalación y puesta en marcha concluida el 10-03-2022;
- reconocimiento RFID en máquinas y esferas;
- 10 juegos para cada uno de siete productos, pero total reportado 60, aunque 10 × 7 = 70.

El mismo informe describe un proyecto posterior de 8 máquinas y 2 sistemas RFID que **no estaba autorizado al cierre de junio de 2024**. Esto no demuestra el inventario actual después de esa fecha; sólo impide afirmar que esa ampliación se hubiera aprobado entonces. Tampoco asigna las 14 máquinas a Chispazo. El SGVO-MAN-02 reservado/proyecto enumera Júpiter, Emerald y Unicorn en apartados de equipos Chispazo, mientras que el informe institucional sólo da el inventario agregado y no la asignación por producto. Es una pista para solicitar inventario y bitácoras, no prueba de despliegue por concurso.

No se publican IDs de tags, eventos de lectores, mapeo etiqueta→número de esfera, asignación máquina-estuche por concurso ni evidencia de un tag RFID independiente en cada estuche. El número de estuche de CS-11 no equivale a RFID.

## 8. Mantenimiento, calibración, incidencias, video y firma

- **Mantenimiento:** SGVO-PRO-05 exige calendario anual de mantenimiento preventivo/correctivo de equipos y del set. No se obtuvieron órdenes por máquina/serie.
- **Calibración:** las básculas deben calibrarse al menos una vez al año. No se obtuvieron certificados, serie de báscula ni historial de vigencia por sorteo.
- **Incidencias:** las que afecten resultados se registran en el Acta y en la Bitácora de Concursos y Sorteos CS-09. La actividad de bitácora se ejecuta después de la celebración; es retrospectiva para ese concurso.
- **Riesgos:** CS-18 Comunicación de Riesgo permite reportar debilidades y riesgos, pero el procedimiento público no fija un timestamp universal. Sólo sería prospectivo si la entrada concreta estuviera firmada y disponible antes del cierre.
- **Accesos:** CS-12 registra a quienes ingresan a la sala durante el evento; no es por defecto una variable pre-cierre.
- **Video:** SGVO-PRO-05 exige grabación desde el pesaje hasta la celebración. La versión editada (sólo el sorteo) se integra al Acta. Para reconstruir pesaje y preparación se requiere el máster continuo, metadatos originales, timecodes y cadena de custodia.
- **Firmas electrónicas:** son dos objetos distintos. (1) El archivo de participaciones/cancelaciones recibe firma inmediatamente después del cierre y se resguarda antes de la ceremonia: control de integridad de ventas, no dato físico ni pre-cierre. (2) La Relación de Ganadores recibe su propia firma electrónica después de capturar los resultados y se incorpora al Acta: evidencia de integridad postresultado.

## 9. V265 — revisión del contrato real

Se contrastó el código actual y la plantilla FULL:
- el evaluador exige CONCURSO, sphere_set_id, machine_id, available_before_close, close_time_local y metadata_known_time_local;
- la plantilla contiene 28 columnas de pesos por esfera, una bandera `rfid_verified` y columnas de procedencia;
- el evaluador no consume los 28 pesos, RFID individual/mapeo a número, orden de extracción, timestamps por extracción ni procedencia documental;
- incluye t-test unilateral y Holm, pero el archivo de familia `--p-family` es opcional;
- no implementa un gate anytime e-value.

El guard actual conserva:
- `evidence_class = ASSOCIATION_SCREEN_ONLY`
- `physical_bias_evidence = false`
- `actionable_for_betting = false`

**Dictamen:** V265 sigue siendo un filtro de asociaciones máquina/estuche. No demuestra sesgo físico y no autoriza acción prospectiva.

## 10. Matriz de disponibilidad prospectiva

El CSV asociado clasifica 23 variables. En resumen:
- **Candidatos condicionales pre-cierre:** CS-02, ID/asignación de máquina, estuche inicial, mantenimiento, calibración; requieren originales autenticados, IDs y timestamps.
- **Bloqueados para el mismo sorteo:** pesos según la secuencia vigente, CS-11, Acta, extracción, CS-09, CS-12, video del evento y firma del archivo de participaciones.
- **Sin tiempo demostrable:** CS-18 hasta obtener timestamp de la entrada.
- **RFID:** bloqueado hasta obtener tags individuales, lectura y mapeo a esfera/número.

Los pesos de un sorteo anterior sólo podrían usarse como variables rezagadas si se prueba que el mismo conjunto físico siguió asignado al sorteo siguiente y que la información estaba disponible antes del cierre siguiente.

## 11. Análisis ejecutado y reproducibilidad

Se ejecutó una reconciliación determinista de:
1. índice actual de Normateca y su sección de proyectos;
2. SGVO-PRO-05 rev39;
3. Reglamento Chispazo;
4. copia histórica SGM-PRO-06 rev22;
5. Informe de Gestión Gubernamental 2018–2024;
6. código y plantilla FULL de V265.

No se usaron resultados de sorteos, datos sintéticos, simulaciones ni estimaciones de efectos. El script `scripts/audit_v265_physical_evidence_delta.py` valida el JSON y la matriz y vuelve a ejecutar la auditoría estática V265 existente. La prueba asociada verifica la clasificación no predictiva y que no se fabricaron registros.

## 12. Bloqueos reales

No se obtuvieron documentos originales por concurso:
- CS-02;
- Tira de Pesaje;
- CS-11 y Acta;
- logs RFID;
- inventario/seriales y asignación máquina-estuche;
- certificados de calibración;
- órdenes de mantenimiento;
- CS-09, CS-12 y CS-18;
- video máster y metadatos;
- archivo de participaciones/cancelaciones y firma electrónica.

Se requiere además:
1. copia controlada vigente del SGVO-MAN-02 y aclaración de su estatus;
2. aclaración escrita de la secuencia urna/cierre/pesaje/alimentadores;
3. corrección de la referencia cruzada a Política 8 en actividad 5.2 y Plan de Calidad;
4. identificación oficial de tipo de esfera por máquina Chispazo.

## Fuentes oficiales

1. [SGVO-PRO-05 rev39 — PDF](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)
2. [Normas Sustantivas Vigentes — Normateca](https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2)
3. [Proyectos Normativos — Normateca](https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0)
4. [SGVO-MAN-02 — PDF en Proyectos, tipo reservado](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/PROYECTO/sgvo_man_02p.pdf)
5. [SGM-PRO-06 rev22 — copia histórica/no listada actualmente](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgm_p0_6.pdf)
6. [Reglamento del Sorteo Chispazo](https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/ChizpasoDOF18062003.pdf)
7. [Página oficial Chispazo](https://loterianacional.gob.mx/Chispazo/Chispazo)
8. [Informe de Gestión Gubernamental 2018–2024, p. 43](https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf)
9. [Dirección General de Juegos y Sorteos — Inspección y Vigilancia](https://www.juegosysorteos.gob.mx/es/Juegos_y_Sorteos/inspecciones_lotenal_pronosticos)

## Integridad del proyecto

- Branch de trabajo: `research/v249-snapshot-integrity-20261119`.
- Sin escrituras en `main`, sin merge y sin promoción.
- Sin cambios al histórico canónico ni a V294.
- No se alteraron parámetros predictivos.
- La coincidencia del Git blob del histórico en `main` y en el branch se verificó antes de esta actualización: `2f5ff5bfbd779fe505736398e417b7211955958e`.
- CI del commit final de código/pruebas `e826d5c7341a3b51f9b59d67341af46ac9d4e476`: `compileall` aprobado y `pytest -q` aprobado con 262 pruebas, 2 omitidas, en 39.64 s. [Ejecución](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45414890943).

**Conclusión:** la evidencia pública describe un mecanismo físico y un procedimiento de control, pero no proporciona datos físicos auténticos por concurso. No se declara sesgo, señal ni ventaja predictiva. OOS, multiplicidad y anytime e-value permanecen sin superar.
