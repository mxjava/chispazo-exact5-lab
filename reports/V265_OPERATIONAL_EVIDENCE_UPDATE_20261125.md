# V265 — Actualización operativa y de custodia documental de Chispazo Clásico
**Corte: 2026-11-25**

## Resultado nuevo

La consulta de la Normateca vigente y la lectura cruzada de SGVO-PRO-05 rev.39 descubren dos defectos de trazabilidad que no estaban explicitados en la matriz anterior: (1) el manifiesto del DVD semanal no enumera la Tira, CS-11 ni los Sumarios, aunque el procedimiento sí los lista como anexos del Acta; y (2) la distribución de CS-11 menciona cuatro ejemplares, pero sólo nombra el destino del original y dos copias. También se identificó una ventana de hasta cinco días hábiles para firmar un Acta cuando no puede imprimirse en el evento.

No se obtuvo ningún registro físico por concurso. La clasificación sigue siendo **MECHANISM_DOCUMENTATION_ONLY**.

## 1. Estado de Normateca y separación de modalidades

La lista oficial de Normas Sustantivas Vigentes, consultada el 25-11-2026, incluye SGVO-PRO-05 revisión 39, última actualización 20-03-2026. La misma lista ubica por separado los procedimientos tradicionales SGVO-PRO-08 (mantenimiento de equipo tradicional), SGVO-PRO-34 (bolas de madera y ábacos) y SGVO-PRO-15 (preparación y celebración del sorteo tradicional).

SGM-PRO-06 no aparece en esa lista. SGVO-MAN-02 aparece en la sección de proyectos y su PDF público está marcado reservado. Por tanto, ninguno reemplaza la autoridad actual de SGVO-PRO-05 para Chispazo electrónico.

Fuentes:
- https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0
- https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

## 2. Nuevo contexto para la contradicción del pesaje pre-cierre

Se localizó una copia SGM-PRO-06 revisión 21 en la carpeta `PROYECTO/SUSTANTIVAS`. Su texto dice que Chispazo se pesaría preferentemente antes del cierre de ventas de 21:15. Esto explica la presencia histórica de una instrucción pre-cierre, pero no demuestra que se ejecutara en un concurso concreto ni que siga vigente.

SGVO-PRO-05 rev.39 fija el cierre nocturno a las 21:00 y describe la actividad 5.1 de pesaje después de que SICAL muestra `Cerrado`. El Reglamento Chispazo, artículo 9, describe la introducción de 28 esferas en una urna antes del cierre y la extracción después. No se debe igualar urna con alimentadores ni usar la copia de proyecto para resolver el conflicto.

Fuentes:
- https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/PROYECTO/SUSTANTIVAS/sgm_p0_6_21.pdf
- https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- https://www.loterianacional.gob.mx/documentos/legal/reglamentojuegos/Reforma-Reg-Chispazo-marzo-2012.pdf

## 3. Anexos del Acta frente al DVD semanal

La tabla de integración del Acta marca expresamente para Chispazo:
- Sumario de Sorteo (cierre de venta);
- Números Ganadores CS-11;
- Sumario de Sorteo postresultado;
- Tira de Pesaje.

La política de resguardo semanal describe un DVD con la Relación de Ganadores y su firma electrónica, Información Básica, Resultados Obtenidos, Máscara Ganadora y Apuestas Consolidadas (esta última para Tris). La Tira, CS-11 y Sumarios no aparecen en ese manifiesto enumerado.

Esto no significa que falten del expediente: significa que la solicitud debe separar (a) originales físicos/anexos del Acta y (b) contenido digital del DVD semanal. No debe suponerse que el DVD sustituye a la Tira original.

## 4. Defecto de distribución de CS-11

La actividad 13.1 indica imprimir cuatro ejemplares. La actividad 13.6 indica sacar tres copias y entregar cuatro ejemplares, pero enumera sólo:
1. Original al representante SGVO para anexarlo al Acta.
2. Copia al Inspector SEGOB.
3. Copia al representante de Tecnologías de Información.

El cuarto ejemplar no tiene destinatario explícito en el texto público. Se requiere aclarar quién conserva esa copia. Es un defecto de especificación documental, no evidencia de que el control haya fallado en la práctica.

La matriz de calidad pide verificar fecha, número de sorteo, número de estuche, correspondencia esfera/número y nombres de participantes. CS-11 se genera después de la extracción y la verificación en exhibidores.

## 5. Latencia de Acta y dos firmas electrónicas diferentes

SGVO-PRO-05 permite que, si no es posible imprimir un Acta durante el evento, se firme el siguiente día hábil y como máximo dentro de cinco días hábiles, siempre que los resultados no se vean comprometidos; el hecho se registra en la bitácora. Por eso deben separarse `event_time`, `created_at`, `signed_at` y `scanned_at`.

También hay dos objetos distintos:
- La firma electrónica del archivo de participaciones/cancelaciones se genera inmediatamente después del cierre de ventas.
- La firma electrónica de la Relación de Ganadores se genera después de capturar los números ganadores.

La primera es un sello de integridad post-cierre, no una variable pre-cierre. La segunda es postresultado.

## 6. Archivos y tiempos de disponibilidad

- CS-02: inspección antes de cada sorteo; candidato pre-cierre sólo si el original incluye fecha/hora, máquina/báscula identificables y evidencia de disponibilidad anterior al cierre.
- Máquina y estuche: la selección inicial se confirma antes del cierre, pero puede cambiar después de un pesaje no conforme. Se necesita identidad del estuche finalmente utilizado y su timestamp.
- Sumario de cierre: se genera después del cierre y antes de ingresar ganadores; incluye fecha, hora de cierre, estado, ventas brutas, cancelaciones y netas.
- Tira: registra el peso de cada esfera y cuatro firmas; la definición pública actual no especifica timestamps de inicio/fin, ID por esfera ni RFID.
- CS-11, Acta, video, CS-09 y firma de Relación de Ganadores: retrospectivos.
- Mantenimiento y calibración: candidatos sólo con certificados/órdenes y timestamp de disponibilidad pre-cierre.
- CS-18: sólo candidato si el aviso concreto fue firmado/recibido antes del cierre; el procedimiento no fija un timestamp universal.

## 7. Archivo institucional: nueva ruta de recuperación

La página de Instrumentos de Control y Consulta Archivística publica enlaces al Cuadro General de Clasificación Archivística, Guía Simple, CADIDO 2017 e inventarios del Archivo de Trámite y de Concentración. Los PDF no pudieron inspeccionarse en esta ejecución por timeout/tamaño; no se afirma ninguna serie, plazo o ubicación concreta.

Fuente: https://www.loterianacional.gob.mx/Transparencia/InstrumentosControlConsultaArchivistica

## 8. V265

El evaluador continúa como `ASSOCIATION_SCREEN_ONLY`. No consume pesos individuales, mapeo RFID por esfera, orden de extracción ni timestamps por extracción; el guard impide afirmar sesgo físico o recomendar acción de apuestas. No se modificó V265 ni sus parámetros en este corte.

## 9. Reproducibilidad y pruebas

El script `scripts/audit_v265_operational_evidence_update.py` valida el JSON, la matriz CSV, los nuevos hallazgos de custodia y el `physical_evidence_guard()` real del evaluador V265. Las pruebas verifican:
- cuatro ejemplares CS-11 frente a un destino sin especificar;
- Tira/CS-11/Sumarios no enumerados en el manifiesto DVD;
- ausencia de registros físicos inventados;
- clasificación no predictiva y gates cerrados.

La auditoría no usa resultados de sorteos, simulaciones ni datos físicos sintéticos.

## 10. Bloqueos reales

Siguen faltando CS-02, Tiras originales, CS-11 y Actas por concurso, logs RFID y mapeo esfera-número, inventario/seriales, certificados de calibración, órdenes de mantenimiento, CS-09/12/18, máster de video con metadatos y dispositivos/archivos originales de firma electrónica.

Además se requiere:
1. Aclaración escrita de la secuencia urna/cierre/pesaje/alimentadores.
2. Confirmación del custodio del cuarto ejemplar de CS-11.
3. Confirmación de qué anexos se conservan en papel y cuáles existen en el DVD semanal.
4. Recuperar e inspeccionar los inventarios archivísticos para identificar serie, custodio y plazo de conservación.

**Dictamen:** evidencia de mecanismo y de custodia documental; no evidencia de sesgo físico ni ventaja predictiva. OOS, multiplicidad y anytime e-value no superados. V294 y el histórico canónico permanecen fuera de cambios.


## 11. Nueva ruta concreta de custodia y mantenimiento (hallazgo adicional del 25-11-2026)

El **SAF-MAN-12, Manual de Organización General, febrero de 2026, revisión 00**, identifica expresamente a la Subgerencia de Operación de Concursos, Juegos y Sorteos Electrónicos e Instantáneos como responsable de:
- revisar el calendario anual de mantenimiento preventivo y correctivo de la maquinaria electrónica;
- administrar la elaboración, custodia y archivo físico y digital de Actas, videograbaciones y registros operativos;
- facilitar documentos y expedientes originales bajo su resguardo para certificación.

Esto resuelve una parte del bloqueo de custodia: la solicitud de originales y copias certificadas debe dirigirse específicamente a esa Subgerencia, además de la Unidad de Transparencia.

Fuente oficial: https://www.loterianacional.gob.mx/documentos/Manual_de_Organizacion_General_de_Loteria_Nacional.pdf (sección 3.2.3.1).

El **Informe de Gestión Gubernamental 2018-2024** identifica el contrato **058-2024** para mantenimiento preventivo y correctivo de 21 máquinas de sorteos con controles y consolas, para Melate, Revancha, Revanchita, Melate Retro, Tris, Tris Multiplicador, Chispazo y Gana Gato. El informe lo incluye entre los contratos concluidos durante enero-junio de 2024. No publica números de serie, asignación por producto ni órdenes de trabajo por concurso.

Fuente oficial: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf (páginas 43 y 58).

El mismo informe reporta 14 máquinas adquiridas en 2022 y el contrato 058-2024 cubre 21 máquinas. No hay conciliación pública por activo. Esto no demuestra inconsistencia: puede incluir equipos previos o de reserva, pero no se puede inferir. Debe solicitarse el inventario patrimonial completo con modelo, serie, consola, RFID, producto asignado, fechas de alta/baja y condición de reserva.

### Ampliación concreta de recuperación documental

La solicitud V3 debe pedir a la Subgerencia custodio:
1. Expediente íntegro del contrato 058-2024, anexos técnicos, inventario de las 21 máquinas, órdenes de servicio, bitácoras preventivas/correctivas, entregables y actas de aceptación.
2. Conciliación entre las 14 máquinas adquiridas en 2022 y las 21 cubiertas por el contrato, con seriales y asignación por producto.
3. Calendario anual de mantenimiento y certificados/órdenes de calibración de básculas, con fechas de emisión, ejecución y recepción.
4. Inventario de Actas y anexos de Chispazo Clásico, incluyendo Tiras, CS-11, Sumarios, CS-02, CS-09, CS-12, CS-18 y másteres de video, con ubicación física/digital, custodio y plazos.
5. Para RFID: identificador de etiqueta, activo/esfera, lector, antena, timestamp de lectura, mapeo etiqueta-número de esfera y asignación a concurso.
6. Para cada archivo: fecha/hora de creación, recepción, firma, digitalización, transferencia y consulta; hash disponible; formato original; y registro de cadena de custodia.

El contrato 058-2024 es evidencia de que existió un servicio de mantenimiento de flota que incluía Chispazo; no prueba qué máquina se usó en un sorteo específico ni su estado en una fecha concreta. SAF-MAN-12 identifica al custodio, pero tampoco demuestra que cada archivo solicitado se conserve o esté completo.
