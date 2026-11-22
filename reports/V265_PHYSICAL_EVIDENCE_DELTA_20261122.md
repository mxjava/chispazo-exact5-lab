# V265 — Evidencia física y operativa: delta 2026-11-22

## Alcance y límites

Auditoría documental de fuentes oficiales vigentes consultables al 22-11-2026 y revisión estática del evaluador V265 existente. No se descargaron ni se recibieron actas, tiras de pesaje, registros RFID, certificados de calibración, órdenes de mantenimiento ni másteres de video por concurso. No se fabricaron registros, no se ejecutaron pruebas de asociación sobre resultados y no se repitieron análisis de frecuencias, pares, tríos o transiciones.

**Clasificación:** evidencia de mecanismo y de control documental. No es evidencia de sesgo físico ni ventaja predictiva.

## 1. Clasificación correcta del producto

La página oficial de Lotería Nacional coloca Chispazo en **Sorteos Electrónicos** y separa los Sorteos Tradicionales. Chispazo Clásico se celebra a las 21:00; Chispazo de las Tres a las 15:00. Por tanto, para Chispazo Clásico aplican el reglamento Chispazo y el procedimiento público SGVO-PRO-05, no los procedimientos de bolas de madera de sorteos tradicionales.

Fuentes:
- https://loterianacional.gob.mx/Chispazo/Chispazo
- https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf

## 2. SGVO-PRO-05 vigente y cronología observada

La Normateca de Normas Sustantivas Vigentes identifica SGVO-PRO-05 como **Procedimiento Sorteos Electrónicos**, nivel de revisión 39, DN-07 versión 09, con última actualización publicada el **20-03-2026**. El PDF es de tipo público.

Fuente:
- https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

La página oficial de SEGOB describe que su área de Inspección y Vigilancia da fe, legalidad y transparencia a sorteos realizados por instituciones como Lotería Nacional. Esto confirma la función de testigo del Inspector que SGVO-PRO-05 asigna a la ceremonia, sin convertir a Lotería Nacional en un permisionario ordinario de sorteos.
Fuente: https://www.juegosysorteos.gob.mx/es/Juegos_y_Sorteos/inspecciones_lotenal_pronosticos (actualizada 12-08-2026).

### Secuencia del procedimiento (hojas 12–16, 24–25 y glosario)

1. **Inspección de equipo:** antes de cada sorteo se llena CS-02. Si el equipo o báscula no cumple, se sustituye.
2. **Confirmación inicial:** antes del apartado de cierre, el representante de Ventas y Operaciones confirma con el Inspector SEGOB y el representante de Dirección General que el número de sorteo y los estuches a utilizar correspondan al concurso.
3. **Cierre SICAL:** se muestra el estado “Cerrado” y se verifican fecha, hora, número de sorteo y ventas. El Sumario de cierre se imprime, rubrica y distribuye.
4. **Pesaje:** después de esa actividad, se pesa cada esfera en orden numérico. El registro es la Tira de Pesaje. La Política 6 fija dos familias de tolerancias:
   - Smartballs: 4.25–5.25 g por esfera y rango máximo de 0.30 g entre la más ligera y la más pesada.
   - Ping Pong: 2.30–3.00 g por esfera y rango máximo de 0.15 g.
   El procedimiento no identifica públicamente cuál tipo se asigna específicamente a Chispazo Clásico.

   **Defecto de referencia interna:** las tolerancias están en la Política 6 (hoja 5), pero la actividad 5.2 (hoja 13) y el Plan de Calidad, actividad 2 (hoja 25), remiten a la Política 8. En este mismo documento, la Política 8 trata la firma electrónica del archivo de participaciones, no los pesos. Se conserva la fuente explícita de tolerancias de la Política 6, pero la referencia cruzada 5.2/Plan de Calidad queda como defecto documental que debe aclarar/corregir Lotería Nacional.
5. **Rechazo y cambio de estuche:** si el peso no es correcto, se notifica el cambio de estuche y se regresa a la actividad 4.1 (verificación/cierre SICAL). Por tanto, el estuche confirmado inicialmente no necesariamente es el estuche final si falla el pesaje. Para usar el estuche como covariable prospectiva se necesita la secuencia de cambios y la hora de fijación del estuche final respecto del último cierre.
6. **Aceptación y colocación:** la Tira de Pesaje se firma y se anexa al Acta; las esferas se colocan en los alimentadores en orden progresivo y se verifica que correspondan al sorteo.
7. **Firma del archivo de participaciones:** el procedimiento contempla la recepción y resguardo de las firmas electrónicas de participaciones/cancelaciones después del cierre y antes de la celebración.
8. **Extracción y CS-11:** el equipo se acciona ante el Inspector SEGOB; se registran los números al ser capturadas las esferas y las cámaras los graban. CS-11 se captura, verifica y firma después de la extracción.

### Ambigüedad normativa que no debe resolverse por inferencia

El artículo 9, fracción I, del Reglamento Chispazo dice que se introducen 28 esferas en una urna; la fracción II sitúa después el cierre de ventas. En cambio, la secuencia detallada de SGVO-PRO-05 sitúa el pesaje individual y la colocación en alimentadores después del cierre. Puede tratarse de etapas o usos distintos de “urna” y “alimentadores”, pero las fuentes públicas no permiten reconciliarlo. Se requiere aclaración oficial del paso físico exacto, especialmente para fijar el timestamp de la carga final.

También debe aclararse la referencia cruzada de pesaje: Política 6 contiene los rangos, mientras actividad 5.2 y Plan de Calidad citan Política 8, que regula la firma electrónica de participaciones. No se debe tratar esa remisión como una especificación alternativa de pesaje.

Fuente: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf (art. 9) y SGVO-PRO-05 (hojas 12–16).

## 3. Qué contiene cada registro y cuándo puede conocerse

| Registro / variable | Lo que sí documenta la fuente | Momento relativo al cierre | Uso prospectivo |
|---|---|---|---|
| CS-02 / estado de equipo | Inspección diaria de funcionamiento antes de cada sorteo; sustituir equipo o báscula no conforme | Antes del cierre en la secuencia de actividades | Potencial, si se obtiene el CS-02 auténtico y se prueba su hora de captura y disponibilidad |
| Máquina / modelo / serie | El procedimiento exige equipo operativo; no publica el campo de serie por concurso | Desconocido por sorteo | Potencial sólo con inventario/bitácora de asignación timestamped antes del cierre |
| Estuche inicialmente confirmado | Se confirma con SEGOB y Dirección General antes del cierre | Pre-cierre | Potencial sólo como “intención inicial”; no equivale al estuche final si el pesaje falla |
| Estuche final | CS-11 registra “Estuche seleccionado”; el cambio por peso no conforme retorna a la actividad 4.1 | La selección final puede quedar fijada tras un rechazo y nuevo cierre; CS-11 es post-extracción | No usar sin historial de sustituciones y timestamp del estuche final antes del cierre definitivo |
| Peso por esfera | Pesaje de cada esfera en orden numérico; Tira de Pesaje; límites de aceptación | Después del cierre en SGVO-PRO-05 | No para predecir el mismo concurso; sí para auditoría retrospectiva y, si se conoce antes del siguiente cierre, para un concurso posterior |
| Tipo de esfera | Política 6 define Smartballs y Ping Pong; no hay asignación pública por producto | Se conoce durante la operación; timestamp de selección no publicado | Potencial para sorteos posteriores sólo con registro previo y tipo verificado |
| Calibración de báscula | Calendario; calibración al menos anual | Certificado podría anteceder al cierre | Potencial como estado de instrumento si se obtiene certificado vigente y trazabilidad |
| Mantenimiento de máquina / set | Calendario anual de mantenimiento preventivo y correctivo | Órdenes anteriores pueden ser pre-cierre | Potencial sólo con fechas, equipo/serie, trabajo, piezas y cierre de orden |
| RFID de máquina/esferas | Informe institucional 2018–2024 declara reconocimiento RFID en máquinas y esferas | El informe no aporta eventos por concurso | Potencial sólo si se obtiene ID, lector, lectura, asociación esfera-número y timestamp pre-cierre |
| CS-11 | Fecha, nombre, número, hora del sorteo, estuche seleccionado, resultados y firmas de elaboración/verificación/certificación/Dirección General | Post-extracción | No para el mismo sorteo; registro de auditoría |
| Video original | Servicio de grabación desde el pesaje hasta la celebración; grabación como testigo documental | Incluye actividades post-cierre | No para el mismo sorteo; permite reconstrucción retrospectiva de secuencia si conserva timecode y reloj sincronizado |
| Video editado | Sólo el sorteo, como anexo electrónico al Acta | Post-extracción | No |
| Firma electrónica de participaciones/cancelaciones | Firma/algoritmo para integridad del archivo, guardado en dispositivo y caja de seguridad | Después del cierre y antes de la ceremonia | No como covariable física; sí como control de integridad del universo de ventas |
| CS-09 | Bitácora de concursos y sorteos; incidencias y sucesos relevantes | Principalmente durante/después del evento; la inclusión depende del hecho y del Acta | Sólo si la hora de ocurrencia y la hora de conocimiento prueban disponibilidad pre-cierre |
| CS-12 | Registro de personas que ingresan a sala durante el evento | Durante el evento; no se fija hora por variable en el procedimiento público | No sin timestamps y prueba de que el acceso antecedió al cierre |
| CS-18 | Comunicación voluntaria de debilidades de control y riesgos potenciales | La política no fija un momento único | Potencial sólo si existe reporte con timestamp anterior al cierre |
| Sumario de cierre | Nombre, número, fecha, CDC, estado cerrado, hora de cierre, ventas brutas, cancelaciones y ventas netas | Después del cierre, antes de cargar números ganadores | No para predicción pre-cierre; control de cierre |
| Acta | Antecedentes, resultados e incidentes; es la fuente oficial del resultado según Reglamento | Después de la ceremonia | No |

La matriz detallada se conserva en `reports/V265_PHYSICAL_EVIDENCE_MATRIX_20261122.csv`.

## 4. RFID: alcance real de la evidencia pública

El Informe de Gestión Gubernamental 2018–2024 dice que el 7 de marzo de 2022 se entregaron 14 máquinas (10 Júpiter, 2 Mercury 5 y 2 Mercury 8), que la instalación y puesta en marcha concluyó el 10 de marzo de 2022, y que las máquinas y esferas tienen reconocimiento RFID.

El mismo párrafo dice “10 juegos de esferas para cada producto” y enumera siete productos (Tris, Chispazo, Gana Gato, Melate Retro, Melate, Revancha y Revanchita), pero afirma un total de 60 juegos. La multiplicación de lo descrito da 70. Se registra como inconsistencia documental; no se corrige el inventario por inferencia.

El informe no publica:
- códigos RFID de máquinas o esferas;
- mapeo RFID ↔ número impreso de esfera;
- lector/antena y eventos de lectura por concurso;
- asignación de máquina y estuche a cada Chispazo Clásico;
- evidencia de RFID independiente para el estuche como contenedor.

En el primer semestre de 2024 se propuso adquirir 8 máquinas y 2 sistemas RFID, pero el informe dice que el proyecto no fue autorizado al cierre de junio de 2024. Esto no demuestra cuál es el inventario posterior; se requiere el inventario vigente.

Fuente: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf (p. 43, líneas 1936–1966 del texto indexado).

## 5. Manual SGVO-MAN-02: bloqueo documental

SGVO-PRO-05 remite al SGVO-MAN-02 para las especificaciones de inspección CS-02 y la operación de equipos. Sin embargo:
- la lista actual de Normas Sustantivas Vigentes publica SGVO-PRO-05, pero no lista SGVO-MAN-02;
- el Manual de Apoyo SGVO-MAN-02 aparece en la sección de **Proyectos Normativos**, con ventana publicada 23-02-2026 a 04-03-2026;
- el PDF de esa entrada se identifica a sí mismo como **TIPO: RESERVADO**.

No se utiliza ese borrador/reservado como procedimiento operativo vigente. La falta de una versión pública controlada impide validar los campos y criterios técnicos detallados de CS-02, inspección de máquina, básculas y operación. Debe solicitarse la versión controlada aplicable y su estatus de aprobación.

Fuentes:
- https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0
- https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/PROYECTO/sgvo_man_02p.pdf

## 6. Video, incidencias, acceso y firmas

SGVO-PRO-05, política 30, requiere contratar grabación desde el pesaje hasta el sorteo; dice que esas grabaciones sirven como testigos documentales para aclaraciones, pero que la versión editada que se incorpora al Acta contiene sólo el sorteo. No se encontró públicamente el máster continuo, sus metadatos, reloj de cámara, sincronización ni cadena de custodia.

CS-09 registra incidencias y sucesos relevantes. La definición de “incidencia” se refiere a hechos fuera del procedimiento que afectan resultados; por tanto, un CS-09 vacío no demuestra por sí solo que nunca hubo una desviación menor. CS-18 es una comunicación que el personal puede utilizar para reportar debilidades y riesgos; no es un registro exhaustivo garantizado. CS-12 identifica personas que ingresan a la sala durante el evento, pero el procedimiento público no proporciona una tabla pública de entradas/salidas por minuto.

La firma electrónica del archivo de participaciones/cancelaciones es una protección de integridad del archivo de ventas. Se genera después del cierre y se resguarda antes de la ceremonia. No es un registro de medición de esferas ni una firma electrónica de la Tira de Pesaje. CS-11 y el Acta tienen firmas de responsables después de la extracción.

## 7. Datos públicos auténticos disponibles

La página oficial de Datos Abiertos enumera:
- Números Ganadores;
- Venta de participaciones en sorteos y concursos;
- Ganadores;
- Ingresos por ventas;
- Estructuras de premiación.

El histórico público de Chispazo se ofrece como CSV de resultados. No aparece un conjunto público de datos de CS-02, CS-11, tiras de pesaje, RFID, calibración, mantenimiento, CS-09/CS-12/CS-18 o video original. La descarga de la hoja de ventas está publicada como Excel; no se obtuvo su binario en esta ejecución. No se calcularon estadísticas sobre estos conjuntos.

Fuentes:
- https://loterianacional.gob.mx/DatosAbiertos/DatosAbiertos
- https://www.loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv

## 8. Auditoría del evaluador V265

La plantilla FULL contiene 48 columnas, incluidas 28 columnas de pesos individuales, `rfid_verified`, `source_document`, `source_url` y `source_sha256`. No contiene un identificador RFID individual por esfera ni columnas de orden/timestamp por extracción.

El evaluador V265 sólo exige:
- `CONCURSO`;
- `sphere_set_id`;
- `machine_id`;
- `available_before_close`;
- `close_time_local`;
- `metadata_known_time_local`.

El código usa las etiquetas máquina/estuche y aplica una comprobación de timestamp pre-cierre. No consume los 28 pesos, no consume un mapeo RFID esfera↔número, no consume orden de extracción ni timestamp individual, y no exige ni verifica `source_document/source_url/source_sha256`. La columna booleana `rfid_verified` de la plantilla no sustituye un identificador ni una lectura RFID por esfera.

El contraste estadístico es un t-test unilateral; Holm puede aplicarse mediante `--p-family`, que es opcional. No existe gate anytime e-value en V265. Por tanto, una asociación máquina/estuche no prueba sesgo físico. Se añadió una barrera de afirmación: V265 ahora informa `ASSOCIATION_SCREEN_ONLY`, `physical_bias_evidence=false` y `actionable_for_betting=false`, sin alterar probabilidades, priors ni cálculo de log-lift.

Artefactos:
- `scripts/audit_v265_evidence_contract.py`
- `tests/test_v265_evidence_claim_guard.py`
- `reports/V265_EVALUATOR_CONTRACT_AUDIT_20261122.json`

## 9. Gate para cualquier análisis físico futuro

No ejecutar un análisis de sesgo hasta tener, por concurso y con procedencia autenticada:
1. máquina/serie y estuche final;
2. identificador RFID individual de cada esfera y mapeo RFID↔número;
3. peso de cada esfera, tipo, balanza y certificado de calibración vigente;
4. orden de extracción y timestamps individuales derivados del video original sincronizado;
5. CS-02, Tira de Pesaje, CS-11, CS-09/CS-12/CS-18 y órdenes de mantenimiento/incidencias;
6. timestamp de captura, timestamp de disponibilidad y prueba de disponibilidad anterior al cierre definitivo.

Después, separar el análisis de mecanismo del análisis predictivo. Cualquier ventaja requerirá los gates del proyecto: OOS prequential intacto, familia de hipótesis predeclarada con control de multiplicidad y anytime e-value. Hasta entonces, evidencia de mecanismo únicamente.

## 10. Integridad y alcance de cambios

- Branch de trabajo: `research/v249-snapshot-integrity-20261119`.
- No escribir en `main`; no merge ni promoción.
- No modificar V294.
- No modificar `data/history/Chispazo_through_12249.csv`.
- No ejecutar análisis de frecuencias, pares, tríos o transiciones.
- Cambios de código limitados a una barrera semántica para impedir que V265 declare sesgo físico o acciónabilidad sin las mediciones y gates necesarios.
- La auditoría no afirma haber recibido o inspeccionado registros operativos por concurso.
