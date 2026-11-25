# Chispazo — mapa de evidencia física y documental según procedimientos oficiales

**Fecha de revisión:** 2026-11-25  
**Clasificación:** mapa de requisitos de adquisición; NO es evidencia física de un sorteo  
**Producción:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`

## 1. Fuentes institucionales verificadas

### Fuente primaria para sorteos electrónicos

Lotería Nacional publica en la carpeta **SUSTANTIVAS/VIGENTES** el documento:

- Clave: **SGVO-PRO-05**
- Título: **PROCEDIMIENTO SORTEOS ELECTRÓNICOS**
- Área emisora: Subdirección General de Ventas y Operaciones
- Tipo: Público
- Fecha de emisión que muestra el PDF: octubre de 2003
- Nivel de revisión: **39**
- Extensión indicada: 38 hojas
- URL: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

La carpeta pública lo clasifica como vigente. El documento identifica expresamente a **CHISPAZO** en la matriz de productos a los que aplican los registros Sumario de Sorteo (cierre de venta), Números Ganadores CS-11, Sumario de Sorteo y Tira de Pesaje. La fecha de emisión no es la fecha de revisión; no debe presentarse como si la revisión 39 hubiera sido emitida en octubre de 2003.

### Documento distinto que también aparece en VIGENTES

También está publicado:

- Clave: **SVO-PRO-05**
- Título: **SORTEOS**
- Área emisora: Subdirección General de Ventas y Operaciones
- Tipo: Público
- Fecha de emisión: octubre de 2003
- Nivel de revisión: **38**
- URL: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/svo_p_05.pdf

No es el mismo documento ni debe confundirse con SGVO-PRO-05. También incluye Chispazo en la matriz de anexos, pero contiene límites Smartballs distintos (4.2–5.2 g frente a 4.25–5.25 g en SGVO-PRO-05 rev. 39). Ambos aparecen en la ruta pública VIGENTES. No se encontró en las páginas consultadas una declaración explícita de derogación o sustitución de SVO-PRO-05 rev. 38. **No combinar umbrales ni resolver por inferencia cuál controla**: solicitar confirmación institucional del documento aplicable a Chispazo y al tipo de esfera usado en cada sorteo.

## 2. Diferencia operativa entre De las Tres y Clásico

La página oficial de Chispazo indica dos sorteos diarios:

- **De las Tres:** 15:00, hora local.
- **Clásico:** 21:00, hora local.

El Anexo 1 de SGVO-PRO-05 distingue la conciliación informática:
- Para sorteos de las 15:00 (entre otros horarios diurnos), cotejar ventas netas del **Sumario de Sorteo** de SICAL contra **Apuestas Consolidadas** del sistema de Selección de Ganadores.
- Para sorteos nocturnos, cotejar ventas brutas, cancelaciones y ventas netas contra la pantalla **Ventas Diarias** de SICAL y el sistema de Selección de Ganadores.

Por tanto, cada paquete de evidencia debe llevar modalidad y horario explícitos; no se deben intercambiar los registros de conciliación de 15:00 y 21:00. La norma describe el flujo de horarios; la página del producto es la fuente que asigna 15:00 a De las Tres y 21:00 a Clásico.

## 3. Registros que el procedimiento exige o identifica para Chispazo

| Registro | Base procedimental | Verificaciones mínimas al recibirlo |
|---|---|---|
| Sumario de Sorteo (cierre de venta) | SGVO-PRO-05, matriz de registros; Anexo 1 | Número y fecha del sorteo, hora/modalidad, estado cerrado, ventas brutas, cancelaciones y netas; conciliación adecuada a 15:00 o nocturno |
| Archivos de participaciones y cancelaciones + firma electrónica por archivo | SGVO-PRO-05, Anexo 1, políticas 1–4 | Bytes originales, firma correspondiente a cada archivo, identidad del firmante/PSICAL, verificación criptográfica, resultado de integridad y conciliación; no aceptar solo una captura de pantalla |
| Tira de Pesaje original | SGVO-PRO-05, actividades 5.1–5.5 y glosario | Peso individual de cada esfera, orden numérico, fecha/hora, número de sorteo, tipo/número de estuche, identificación de báscula y firmas requeridas; verificar que fue anexada al Acta |
| Formato Números Ganadores de los Sorteos CS-11 | SGVO-PRO-05, actividades 13.1–13.6 y glosario | Fecha, nombre del sorteo, número, hora, estuche seleccionado, resultados y nombres/firmas de quien elabora, verifica, certifica y representante de Dirección General; cotejo con exhibidores y lectura en voz alta ante representantes |
| Acta y anexos | SGVO-PRO-05, actividades 21–26 | Lugar, fecha, horario, roles y firmas; incidencias; Tira de Pesaje y CS-11 anexos; original y anexos; copia escaneada remitida al OIC; dispositivo electrónico de anexos digitales |
| Reportes digitales anexos | SGVO-PRO-05, actividad 24.1 | Información Básica, Máscara Ganadora, Relación de Ganadores, Apuestas Consolidadas y Resultados Obtenidos, según corresponda al producto |
| Bitácora CS-09 | SGVO-PRO-05, actividad 25.1 | Exigirla cuando hubo incidencia o retraso de generación/impresión de reportes; no inferir que existe una incidencia si no se entrega |
| Calibración de báscula y mantenimiento | SGVO-PRO-05, políticas 25–26 | Certificado de calibración vigente para la fecha del sorteo, trazabilidad del equipo y registro de mantenimiento; la política establece calibración al menos anual |

### Tira de Pesaje: contenido y firmas

SGVO-PRO-05 define la Tira de Pesaje como el documento donde se registra el peso de cada esfera. El glosario identifica las firmas de:
1. responsable del pesaje de esferas;
2. representante de la Dirección de Operación de Concursos, Juegos y Sorteos;
3. representante de la Dirección General; y
4. Inspector de SEGOB.

La actividad 5.1 indica que el pesaje se hace esfera por esfera y en orden numérico, en presencia del Inspector de SEGOB y representantes de Dirección General y SGVO. La actividad 5.4 indica firma del responsable y revisión/rúbrica de SGVO, Inspector de SEGOB y Dirección General; la 5.5 manda anexar la tira al Acta.

Los criterios de la revisión 39 son:
- Ping Pong: cada esfera entre **2.30 y 3.00 g**; diferencia entre menor y mayor no superior a **0.15 g**.
- Smartballs: cada esfera entre **4.25 y 5.25 g**; diferencia entre menor y mayor no superior a **0.30 g**.

La revisión 39 también exige calibración de las básculas al menos una vez al año. No se obtuvo en esta revisión un certificado de calibración ni una Tira de Pesaje real.

### CS-11: identidad del sorteo y resultado

El glosario de SGVO-PRO-05 define que CS-11 registra fecha, nombre del sorteo, número de sorteo, hora, estuche seleccionado, resultados y nombres/firmas de quien elabora, verifica, certifica y del representante de Dirección General.

Las actividades 13.1–13.6 indican cuatro ejemplares; cotejo de los números capturados contra los exhibidores; lectura en voz alta ante representantes de Lotería Nacional e Inspector de SEGOB; firma y distribución del original para el Acta y copias a SEGOB, TI y operador. El plan de calidad también identifica fecha, número de sorteo, número de estuche, correspondencia esfera/resultado y nombres de participantes.

### Acta, anexos y custodia institucional

SGVO-PRO-05 describe la generación del Acta, su revisión y firmas de representantes, el escaneo y envío al Órgano Interno de Control, la entrega del original con anexos y la recepción del Acta, anexos y dispositivo electrónico para guarda y custodia por la Subgerencia responsable. El DVD/dispositivo contiene firmas electrónicas y reportes digitales usados como anexos.

Esto identifica una cadena documental institucional esperada, pero no prueba que una cadena concreta se haya ejecutado para un concurso determinado. Se necesitan el original, anexos, acuses de envío/recepción y registro de custodia del concurso específico.

## 4. Umbrales y controles: no mezclar revisiones

La revisión 39 de SGVO-PRO-05 es el procedimiento específico titulado **Sorteos Electrónicos** y está publicada bajo VIGENTES. La revisión 38 de SVO-PRO-05, también bajo VIGENTES, contiene Smartballs 4.2–5.2 g. La diferencia es material para cualquier validador automático.

Regla para ORIGEN:
- conservar por separado ambos documentos y sus metadatos;
- registrar la revisión usada por cada regla;
- no cambiar tolerancias de producción ni crear un validador que acepte/rechace evidencia hasta obtener confirmación institucional del instrumento que controla para Chispazo;
- nunca inferir la calibración real de una báscula a partir de los límites nominales del procedimiento.

El producto Chispazo usa números del 1 al 28. Un control de completitud de 28 lecturas de esfera es una comprobación cruzada del rango del producto, no una frase atribuida al procedimiento. Si el formato original no muestra las 28 esferas, conservar la anomalía y solicitar aclaración, no completar datos faltantes.

## 5. Paquete de adquisición por concurso

Para cada concurso, separado en De las Tres 15:00 o Clásico 21:00, solicitar y preservar:

1. Acta original completa y todos sus anexos, anverso/reverso y firmas.
2. Tira de Pesaje original, legible, sin recortar, con todas las lecturas y firmas.
3. CS-11 original y copias disponibles, incluida la hoja con datos de concurso, estuche y firmantes.
4. Sumario de cierre de venta y Sumario posterior; capturas/exportaciones originales de SICAL y del sistema de Selección de Ganadores.
5. Archivos de participaciones y cancelaciones en bytes originales, firmas electrónicas por archivo, certificados/clave pública y procedimiento oficial de validación.
6. Relación de Ganadores, Máscara Ganadora, Información Básica, Apuestas Consolidadas y Resultados Obtenidos, según aplique; conservar firmas electrónicas y soporte digital original.
7. Certificado de calibración de la báscula aplicable a la fecha y registro de mantenimiento.
8. Identificación del estuche, tipo de esfera, máquina/urna y participantes; oficios de comisión del Inspector de SEGOB y suplencias.
9. Acuses de escaneo/envío al OIC, entrega/recepción del original y anexos, dispositivo electrónico y registros de guarda/custodia; CS-09 si hubo incidencia o retraso.

Para cada objeto: conservar el archivo/soporte original, registrar quién lo entregó y recibió, cuándo, canal, formato, tamaño, SHA-256 calculado localmente sobre los bytes originales, firma/certificado, resultado de verificación y toda transformación derivada. No sustituir el original por OCR, transcripción, PDF reimpreso o captura de pantalla.

## 6. Estado de evidencia del concurso del 25-11-2026

La revisión pública de resultados/mascarillas no produjo ninguno de los documentos físicos anteriores. El resultado público, una mascarilla o el horario del sorteo no sustituyen Acta, Tira de Pesaje, CS-11, Sumario de cierre, archivos firmados ni cadena de custodia.

No se recibió evidencia física o institucional auténtica del 25-Nov. No se capturó ningún original, no hay hash de artefacto físico y no se efectuó append al histórico canónico. No se altera V294.

## 7. Fuentes oficiales

- [SGVO-PRO-05 — Procedimiento Sorteos Electrónicos, revisión 39 (PDF)](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)
- [SVO-PRO-05 — Sorteos, revisión 38 (PDF)](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/svo_p_05.pdf)
- [Chispazo — horarios y reglas del producto](https://www.loterianacional.gob.mx/Chispazo/Chispazo)
- [Resultados oficiales](https://www.loterianacional.gob.mx/Chispazo/Resultados)
- [Mascarillas oficiales](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas)
