# Auditoría de evidencia física y operativa — Chispazo Clásico
**Fecha de corte:** 2026-11-21  
**Estado:** `MECHANISM_EVIDENCE_ONLY / NO_PUBLIC_PER_DRAW_PHYSICAL_PANEL`

## 1. Alcance y disciplina

Esta actualización audita documentación normativa, trazabilidad operativa y el contrato de datos de V265. No repite frecuencias, pares, tríos ni transiciones; no vuelve a entrenar modelos; no modifica V294 ni el histórico canónico. No se calcula un efecto físico porque no se localizó una tabla pública auténtica por concurso con pesos, identidades y tiempos.

## 2. Distinción operativa: electrónico no significa RNG

La página oficial clasifica Chispazo dentro de los **Sorteos Electrónicos** y separa sus dos eventos: Chispazo de las Tres (15:00) y Chispazo Clásico (21:00). El reglamento, sin embargo, describe una selección física: 28 esferas numeradas del 1 al 28 en una urna y extracción al azar de cinco, una por una, ante el inspector de SEGOB. La venta/captación y el archivo de participaciones son electrónicos; el resultado de Chispazo se obtiene mediante el equipo físico de esferas. No se debe modelar como si el resultado proviniera necesariamente de un generador electrónico de números. La Normateca lista por separado los procedimientos tradicionales SGVO-PRO-15, SGVO-PRO-08 (mantenimiento tradicional), SGVO-PRO-34 (bolas de madera/ábacos) y SGVO-PRO-28 (falla del motor de la Esfera Mayor). SGVO-PRO-34 se limita expresamente al boleo de madera de sorteos tradicionales y SGVO-PRO-28 a la Esfera Mayor; sus pesos, tolerancias y reglas de contingencia no se deben importar a Chispazo.

Fuentes:
- [Página oficial de Chispazo](https://loterianacional.gob.mx/Chispazo/Chispazo)
- [Reglamento Chispazo, arts. 5, 9 y 15](https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/ChizpasoDOF18062003.pdf)
- [Normateca de Lotería Nacional — normas sustantivas](https://loterianacional.gob.mx/Normateca/Sustantivas?id=2)

Para el conjunto de entrenamiento de Clásico, la etiqueta debe provenir de la modalidad publicada para cada concurso. La paridad del identificador no sustituye una etiqueta oficial de modalidad en un panel de evidencia física.

## 3. Procedimiento vigente y cronología respecto al cierre

La versión que la Normateca lista como vigente es **SGVO-PRO-05, revisión 39, DN-07 versión 09**, publicada el **20-03-2026**: [PDF oficial](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf).

La secuencia relevante de su sección V es:

1. **Inspección CS-02.** Se prepara y verifica el estado de los elementos del sorteo; si no están en buen estado se sustituye el equipo. Esta etapa aparece antes del cierre de venta.
2. **Confirmación de estuche.** Antes del cierre, el representante de Lotería confirma con SEGOB y el representante de Dirección General que el número de sorteo y los estuches que se usarán correspondan al evento. La norma no publica un identificador de máquina por concurso en este paso.
3. **Cierre de ventas.** SICAL debe mostrar el estado “Cerrado”. El Sumario de Sorteo incluye fecha, hora, número de sorteo y ventas; se imprime y se rubrica. La política 9 fija el cierre automático de sorteos nocturnos a las 21:00, sujeto a cambios autorizados. El horario programado no reemplaza el timestamp del Sumario de cada evento.
4. **Pesaje posterior al cierre.** La actividad 5 inicia el pesaje en presencia del Inspector SEGOB, representante de Dirección General y SGVO; las esferas se pesan una por una y en orden numérico. El registro es la **Tira de Pesaje**. Si el peso no cumple, se cambia el estuche y se vuelve al paso 4.1; si cumple, la tira se firma/rubrica y se anexa al acta.
5. **Colocación y verificación.** Las esferas se trasladan a los alimentadores de la máquina y Lotería/SEGOB verifican que correspondan al sorteo.
6. **Extracción.** El operador acciona la máquina con el Inspector SEGOB frente a ella; las esferas se mezclan y se capturan en exhibidores. Los representantes de Lotería y SEGOB registran y cotejan los números expresados por el presentador contra el testigo generado por éste.
7. **CS-11.** Después de la extracción se capturan los datos del sorteo y números ganadores en “Números Ganadores de los Sorteos CS-11”; se cotejan frente a la máquina, se leen en voz alta y se firman. El original se anexa al acta. El procedimiento público no expone el formulario completo ni permite confirmar qué campos adicionales contiene; en particular, no se da por probado que CS-11 incluya el RFID de cada esfera o timestamps por extracción.
8. **Acta y anexos.** El acta consigna lugar, fecha, horario, funcionarios, roles, firmas del Inspector SEGOB y, si existen, incidencias. La tabla de anexos de SGVO-PRO-05 marca expresamente para CHISPAZO: Sumario de cierre de venta, CS-11, Sumario de Sorteo y Tira de Pesaje. Las actas firmadas se escanean para el Órgano Interno de Control y se resguardan con anexos y soporte digital.

**Consecuencia temporal:** las mediciones de la Tira de Pesaje se generan después del cierre según el flujo vigente. No pueden alimentar una predicción que deba congelarse antes del cierre de ese mismo concurso. Existe un documento antiguo de proyecto, **SGM-PRO-06 “Preparación de Sorteos”, DN-07 v05, revisión 21** ([PDF en carpeta PROYECTO](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/PROYECTO/SUSTANTIVAS/sgm_p0_6_21.pdf)). Indicaba que Chispazo se pesara preferentemente antes del cierre de 21:15 y listaba 28 esferas amarillas o azules según la máquina, con límites históricos distintos. Su anexo de básculas describe impresión de fecha/hora al inicio y fin, pesos individuales, promedio, máximo, mínimo y rango; su anexo CS-02 histórico describe fecha, número de sorteo, hora de inspección y firmas, además de revisiones de compresor, consola, alimentador, turbina, trampa, cápsula, puerta, exhibidor, báscula, rollo y baterías. Estos campos son pistas para pedir los registros originales, no especificaciones actuales: el documento está en carpeta PROYECTO y no es la SGVO-PRO-05 vigente; además, “preferentemente” no demuestra el timestamp real de cada concurso. La revisión vigente 39 coloca el pesaje después del cierre. Para cualquier análisis histórico por fecha se requiere identificar la norma aplicable y los timestamps reales del evento.

## 4. Variables, documentos y utilidad prospectiva

| Variable | Registro o fuente | Momento conocido según la norma | ¿Puede entrar en predicción pre-cierre? |
|---|---|---|---|
| Estado de máquina/equipo | CS-02, inspección diaria | Antes del cierre en la secuencia publicada | **Potencial**, sólo con formulario auténtico, valor por concurso y timestamp anterior al cierre |
| Estuche seleccionado | Confirmación operativa previa; CS-11 es posterior | Se confirma antes del cierre; el registro público por concurso no está disponible | **Potencial**, sólo si el ID exacto se publica/verifica antes del cierre |
| ID de máquina/modelo/serie | Inventario y/o lectura RFID; no se identifica por concurso en el SOP público | Momento de lectura/asignación no publicado | **No actualmente**; requerir log RFID y timestamp |
| Tipo de esfera | Tira de Pesaje/manual operativo | Se identifica durante el pesaje posterior al cierre; el SOP contempla Smartballs y Ping Pong, pero no publica cuál se usa en cada Clásico | **No para el mismo concurso** sin evidencia pre-cierre distinta |
| Peso individual de las 28 esferas | Tira de Pesaje | Después del cierre; un peso por esfera, en orden numérico | **No** para pronóstico pre-cierre del mismo concurso |
| Peso mínimo, máximo y rango | Tira de Pesaje | Después del cierre | **No** para pronóstico pre-cierre del mismo concurso |
| Calibración de báscula | Calendario/certificado de calibración | La norma exige al menos anual; fecha y estado pueden conocerse antes, pero los certificados por báscula no son públicos | **Potencial como covariable de control**, si se vincula báscula, certificado vigente y concurso antes del cierre; no es sesgo por sí sola |
| Mantenimiento de máquina | Calendario anual y bitácoras/órdenes de mantenimiento | Puede existir antes del sorteo; detalle por máquina no público | **Potencial**, sólo con equipo identificado, intervención fechada y disponibilidad pre-cierre |
| RFID de máquina/esferas | Tags y sistema de reconocimiento RFID | La capacidad tecnológica está documentada; el momento y contenido de cada lectura no | **No actualmente**; falta ID/tag→número, equipo lector, lectura por evento y timestamp |
| Orden y tiempo de extracción | Captura en exhibidores y cámaras; video | Durante la ceremonia, después del cierre | **No** para predecir el mismo evento; sí para auditoría retrospectiva del mecanismo |
| CS-11/números ganadores | Formato CS-11 | Después de la extracción | **No** |
| Incidencias | Acta y Bitácora CS-09; CS-18 comunica riesgos | Durante/después del evento; registro consolidado post-evento | **No** como predictor del mismo evento salvo aviso público pre-cierre con hora verificable |
| Accesos/personas presentes | CS-12 y bitácoras de acceso | Durante el evento; acceso restringido | **No actualmente**; posible variable de auditoría, no señal predictiva demostrada |
| Video | Grabación desde pesaje hasta sorteo; versión editada anexada al acta | Desde el pesaje posterior al cierre hasta el resultado | **No** para predicción pre-cierre; sí para reconstruir mecanismo, secuencia y controles |
| Firma electrónica | Archivo de participaciones/cancelaciones; firma de reportes de ganadores | La firma del archivo de participaciones se genera inmediatamente después del cierre y se resguarda antes de la ceremonia; otros reportes se archivan después | **No**; acredita integridad de archivos, no el sesgo físico de una esfera |

Los parámetros publicados por SGVO-PRO-05 son:
- Smartballs: 4.25–5.25 g; diferencia máximo–mínimo no mayor de 0.30 g.
- Ping Pong: 2.30–3.00 g; diferencia máximo–mínimo no mayor de 0.15 g.

La norma no identifica públicamente qué tipo de esfera se utiliza en cada concurso Clásico ni publica las 28 mediciones reales. No inferirlo del producto o de una imagen.

## 5. RFID, mantenimiento, calibración y video: evidencia encontrada

### RFID y equipo
El Informe de Gestión Gubernamental 2018–2024 indica que el 7-03-2022 se entregaron 14 máquinas para sorteos electrónicos (10 Júpiter, 2 Mercury 5 y 2 Mercury 8), que las máquinas y esferas contaban con reconocimiento RFID, que la instalación inició el 8-03-2022 y concluyó el 10-03-2022. Esto prueba la existencia declarada de la tecnología en el inventario adquirido; **no** prueba qué máquina, estuche o tag se utilizó en cada concurso ni que exista un registro público de lectura.

El mismo informe afirma “10 juegos” para cada uno de siete productos (Tris, Chispazo, Gana Gato, Melate Retro, Melate, Revancha y Revanchita), pero declara un total de 60. La multiplicación literal da 70. Se registra como inconsistencia documental; no se usa el total para inferir el inventario.

El informe también refiere que, al cierre de junio de 2024, proyectos para 8 máquinas y 2 sistemas RFID, y para 4 balanzas de precisión, no habían sido autorizados. Esto sólo describe el estado reportado a esa fecha; no prueba qué compras ocurrieron después.

### Mantenimiento y calibración
SGVO-PRO-05 establece mantenimiento preventivo/correctivo de equipos conforme a calendario anual y calibración de básculas al menos una vez al año. No se localizaron públicamente las bitácoras por número de serie, órdenes de servicio, certificados de calibración, incertidumbre de medición ni historial de sustitución de piezas.

### Videograbaciones
La política 30 de SGVO-PRO-05 exige grabación desde el pesaje hasta la celebración del sorteo y establece que la grabación editada forme parte de las actas como testigo documental. La política 19 establece acceso restringido y registro de asistentes CS-12.

La licitación audiovisual LA-006HJY001-E90-2021 especificó grabación ininterrumpida desde el pesaje hasta el testigo ganador, tomas de báscula/impresora, traslado, alimentadores, extracción y esferas ganadoras; también especificó un archivo web de al menos 1,000 días por producto y publicación de videos editados antes de las 12:30 del día siguiente. Es una especificación contractual de 2021, no prueba por sí sola que el archivo siga accesible ni que el contrato continúe vigente en 2026.

Se localizó un ejemplo de video en el canal verificado **Lotería Nacional · Sorteos Electrónicos**: [Chispazo Clásico 12246, 12-09-2026](https://www.youtube.com/watch?v=W-fDm3RuYZY). Su existencia acredita una fuente audiovisual pública de un evento, no una tabla de pesos/IDs ni un panel de todos los concursos.

## 6. Auditoría del evaluador V265

Archivos inspeccionados:
- `src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py`
- `src/v265/CHISPAZO_V265_PHYSICAL_REGIME_SCANNER.py`
- `data/physical-metadata/V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv`
- `tests/test_v2692_preclose_timestamp_integrity.py`
- `reports/V265_PHYSICAL_REPORT.json`

Hallazgos concretos:
1. El evaluador exige `sphere_set_id`, `machine_id`, `available_before_close`, `close_time_local` y `metadata_known_time_local`; verifica cobertura completa y que el timestamp declarado sea anterior al cierre.
2. No exige ni consume `sphere_weight_01_g ... sphere_weight_28_g`, ID RFID por esfera, mapeo RFID→número, orden de extracción, timestamp de cada extracción, tipo de esfera, calibración, mantenimiento ni `source_url/source_sha256` por registro.
3. El score se condiciona por etiquetas de estuche/máquina y cuenta números observados. Eso es, como máximo, una prueba de **asociación predictiva por etiquetas de equipo/estuche**; no identifica un mecanismo físico ni demuestra sesgo de una esfera.
4. El test existente `test_v2692_preclose_timestamp_integrity.py` crea 40 filas sintéticas con etiquetas `S1/M1` y timestamps, sin pesos, RFID, orden ni procedencia documental. Sirve para comprobar el guard de tiempo; no valida autenticidad física. No se reutiliza como evidencia de sorteos reales.
5. El template FULL contiene columnas de pesos, `rfid_verified`, documento, URL y hash, pero no contiene observaciones reales; además no incluye IDs RFID individuales ni una secuencia de extracción por esfera.
6. El evaluador sólo calcula una prueba t unilateral y permite un ajuste Holm opcional por `p-family`; no implementa el anytime e-value requerido por el proyecto. Por tanto, no puede certificar por sí solo los gates del proyecto.

**Dictamen V265:** conservar como prototipo de asociación de regímenes, pero no etiquetar su salida como sesgo físico. No habilitar predicción física ni promoción hasta incorporar evidencia por esfera y fuente, y superar OOS, multiplicidad predeclarada/maxT y anytime e-value.

## 7. Datos públicos auténticos obtenidos y bloqueos

Datos documentales auténticos nuevos:
- SGVO-PRO-05 revisión 39 (publicado 20-03-2026): secuencia, formatos, umbrales de peso, mantenimiento/calibración, video, acta y custodia.
- Reglamento Chispazo (última reforma indicada 07-03-2012): 28 esferas, extracción de cinco al azar, inspector SEGOB y acta.
- Informe de Gestión 2018–2024: inventario y RFID instalados en marzo de 2022.
- Licitación audiovisual 2021: especificación de grabación continua y archivo.
- Video oficial de muestra: Clásico 12246, 12-09-2026.

No se localizó una base pública por concurso con CS-02, CS-11, tiras de pesaje, RFID, mantenimiento/calibración, CS-09, CS-12, timestamps de extracción o archivos originales con firma electrónica. Por ello no hay panel físico auténtico para ejecutar un OOS ni para estimar un efecto.

Bloqueos reales:
- falta la Tira de Pesaje de cada Clásico, con las 28 medidas y unidad;
- falta ID de máquina, ID de estuche y mapa de cada esfera RFID a su número;
- falta timestamp de cada lectura RFID y cada extracción;
- falta el formulario CS-02 y el esquema completo CS-11;
- faltan certificados de calibración y bitácoras de mantenimiento por equipo;
- faltan actas/anexos, CS-09/CS-12 y video original continuo con metadatos;
- falta conocer qué campos eran accesibles antes del cierre y por qué medio.

## 8. Próximo paso reproducible

Se añadió `reports/V265_SOLICITUD_TRANSPARENCIA_V2_20261121.txt`, acotada a Chispazo Clásico desde el 10-03-2022, para solicitar los documentos y metadatos que faltan. La solicitud pide explícitamente fecha/hora de disponibilidad respecto del cierre y que se declare cuando un campo no se genere o no se conserve.

No se corrió una regresión física ficticia ni se fabricaron filas. Cualquier resultado futuro se clasificará primero como evidencia de mecanismo; sólo será ventaja predictiva si supera los gates OOS, multiplicidad y anytime e-value.

## 9. Integridad del repositorio

Verificación previa a esta actualización:
- Branch de investigación: `research/v249-snapshot-integrity-20261119`.
- HEAD previo: `06410249e9d2d9a6f72cf0d49d8b5debecd4baec`.
- `main` observado: `424eee9dd906f8235541e97ae61026441083bbfe`.
- El archivo canónico tiene el mismo Git blob SHA-1 en el branch y en `main`: `2f5ff5bfbd779fe505736398e417b7211955958e`.
- SHA-256 registrado por el manifiesto de entrada de V264 para el histórico: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a` (hash previo registrado, no recalculado en esta auditoría).
- Blob SHA-1 del evaluador V265: `ca83e4af6ccd12f68ff0a725969561254b0be866`.
- Blob SHA-1 del template FULL: `4c707be9d7ea643ce6691aabb4a736e724551329`.
- Blob SHA-1 del reporte V265 previo: `f37ace64bc4c441be5eaf1398f59d9383af64899`.
- Blob SHA-1 del test de timestamps: `c398a5fe31876b6fdd8b20f1d256499f30ed8a65`.

Los SHA-1 anteriores son Git blob IDs, no SHA-256. No se obtuvo el binario original de los PDF oficiales para calcularles SHA-256 en esta ejecución; se conservan sus URLs y revisión/fecha exactas en vez de inventar hashes. El histórico, V294 y `main` no se modificaron.
