# Matriz de evidencia física exigible — SGVO-PRO-05 revisión 39

**Consulta:** 2026-11-24  
**Fuente institucional:** Lotería Nacional, Normateca Interna, SGVO-PRO-05, *Procedimiento Sorteos Electrónicos*, revisión 39, publicado el 20-mar-2026.  
**URL:** https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

Esta matriz identifica registros que el procedimiento exige o describe. No afirma que Lotería Nacional haya entregado esos registros para un concurso concreto.

## Registros y controles descritos por el procedimiento

| Control | Requisito/documento descrito | Valor para ORIGEN | Lo que falta para acreditar un sorteo concreto |
|---|---|---|---|
| Pesaje por sorteo | Se pesan las esferas en cada sorteo. Smartballs: 4.25–5.25 g y dispersión máxima 0.30 g. Ping Pong: 2.30–3.00 g y dispersión máxima 0.15 g. Si no cumple, se cambia el estuche y se repite el pesaje. | Límites y proceso de aceptación/rechazo para metrología. | Tira original del sorteo, lecturas individuales, IDs de esfera/estuche, instrumento, calibración e incertidumbre. |
| Firmas de tira | La persona responsable firma la tira; recaba rúbricas del representante de la Subdirección General de Ventas y Operaciones, Inspector SEGOB y representante de Dirección General; la tira se anexa al acta. | Cadena de revisión y signatarios requeridos. | Original firmado, identidad y oficio de comisión de cada firmante, fecha/hora y custodia. |
| CS-11 | Se capturan números ganadores en cuatro ejemplares; se cotejan con las esferas en exhibidores, se leen en voz alta ante representantes e Inspector SEGOB y se firman. Original y copias se distribuyen entre áreas. | Evidencia primaria de correspondencia esfera/número y revisión presencial. | Los cuatro ejemplares originales o copias certificadas, firmas, estuche, fecha, concurso y cadena de entrega. |
| Acta del sorteo | Debe registrar lugar, fecha, horario, nombres, roles y firmas de representantes de Lotería Nacional, además del nombre, firma y número de oficio del Inspector SEGOB; incluye incidencias. | Identidad de participantes y hechos declarados durante el sorteo. | Acta completa firmada, anexos y constancia de remisión/resguardo. |
| Anexos Chispazo | El procedimiento lista para Chispazo: relación de ganadores CLSBR140; sumario de cierre; CS-11; sumario de sorteo; tira de pesaje. | Inventario documental oficial para el expediente. | Todos los anexos de un mismo concurso, con identificadores y hashes de bytes originales. |
| Archivo de participaciones | La firma electrónica del archivo de participaciones se graba antes del sorteo en dispositivo entregado al Inspector SEGOB y depositado en caja de seguridad; el texto indica acceso al OIC con la clave correspondiente. | Control de integridad/precedencia de participaciones. | Archivo original, firma/certificado, verificación criptográfica, acta de entrega, registro de depósito y evidencia de acceso/resguardo. |
| CS-12 | Registro de asistencia a la sala de sorteos durante el evento. | Evidencia de presencia y acceso. | CS-12 del concurso, identidades, horarios y bitácoras de acceso/mantenimiento. |
| CS-18 | Comunicación de Riesgo para reportar debilidades de control o riesgos potenciales. | Registro de incidentes/control que podría explicar desviaciones. | Formato presentado o constancia institucional de búsqueda/no existencia; no inferir ausencia por no verlo en la web. |
| Grabación | Se contrata grabación desde pesaje hasta celebración del sorteo; la grabación sirve como testigo documental. La versión editada del sorteo se incorpora al acta en DVD/CD/USB. | Posible corroboración audiovisual de pesaje, montaje y sorteo. | Archivo audiovisual original sin editar, metadatos, hash, contrato/entrega, continuidad y custodia; la copia editada no sustituye al original. |
| Resguardo semanal | El procedimiento describe entrega semanal en DVD de reportes y firmas electrónicas, con oficio del titular de TI, para adjuntarse a las actas. | Ruta institucional de archivo y retención. | DVD/imagen forense original, oficio, inventario, hash, recepción y ubicación de resguardo. |

## Implicaciones de implementación

1. El esquema ORIGEN debe conservar por separado el original digital/físico, la copia de consulta, el hash, el identificador del concurso, modalidad, hora oficial, fuente de adquisición, signatarios y cadena de custodia.
2. La tira de pesaje no debe reducirse a un promedio o a una declaración booleana. Se requieren las lecturas originales por esfera, identidad del estuche, tipo de esfera, equipo de medición y trazabilidad metrológica.
3. CS-11 vincula las esferas exhibidas con los números capturados. Debe tratarse como una relación física/número distinta del resultado web.
4. La firma electrónica del archivo de participaciones es un objeto distinto de la firma del acta, la tira de pesaje y la firma del recibo ORIGEN. No intercambiar sus roles ni sus claves.
5. La grabación editada que se anexa al acta no equivale al archivo audiovisual original. Preservar ambos cuando se obtengan.
6. La política describe la existencia de controles y archivos; no demuestra que los registros de un sorteo particular sean completos, auténticos, accesibles o conservados.

## Modalidades y alcance

El procedimiento identifica horarios operativos de sorteos electrónicos, incluidos 15:00 (De las Tres) y 21:00 (Nocturno). Para el contrato ORIGEN de Chispazo, conservar la regla específica del producto: De las Tres 15:00 y Clásico 21:00, verificada también en la página oficial del juego. No mezclar un expediente de 15:00 con la serie prospectiva Clásico 21:00.

## Límite de esta revisión

La revisión del PDF oficial no obtuvo:
- tira de pesaje ni lecturas de un sorteo objetivo;
- CS-11, acta o anexos de un concurso objetivo;
- archivo original de participaciones/cancelaciones y firma electrónica verificable;
- CS-12, CS-18 o bitácora de acceso;
- vídeo original ni medio semanal de resguardo;
- identidad/independencia de un custodio externo;
- tokens RFC 3161 ni anclaje de ledger independiente.

Por tanto, esta matriz es una especificación de adquisición y verificación, no evidencia física primaria ni prueba de sesgo de extracción.
