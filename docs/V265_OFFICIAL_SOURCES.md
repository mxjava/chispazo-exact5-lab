# V265 — Fuentes oficiales y trazabilidad

## Procedimiento vigente de Sorteos Electrónicos
- Normateca Lotería Nacional, `PROCEDIMIENTO SORTEOS ELECTRÓNICOS`, SGVO-PRO-05, revisión 39, DN-07 versión 09, cuya ficha de Normateca muestra actualización al 20-03-2026; el PDF conserva fecha de emisión original octubre de 2003.
- URL canónica: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Hechos relevantes:
  - inspección de equipo CS-02 antes del cierre;
  - confirmación del número de sorteo y estuche antes del cierre;
  - cierre de venta en SICAL y después pesaje/colocación de esferas;
  - parámetros de peso para Smartballs/Ping Pong y sustitución del estuche si no cumple;
  - la Tira de Pesaje registra el pesaje individual y se anexa al acta;
  - CS-11 captura datos del sorteo y números ganadores después de la extracción; el procedimiento público no expone el formulario completo ni confirma sus campos adicionales;
  - CS-11 y Tira de Pesaje se integran al acta;
  - mantenimiento anual de equipos, calibración de básculas al menos anual, registro de incidencias, acceso CS-12 y grabación desde pesaje hasta sorteo.

## Reglamento Chispazo
- URL: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/ChizpasoDOF18062003.pdf
- Publicado el 18-06-2003; última reforma indicada 07-03-2012.
- Artículos 5 y 9: números 1–28, 28 esferas y extracción de cinco al azar; artículo 15: acta con resultados e incidencias. El artículo 8 establece que el resultado oficial es el asentado en el Acta; la web, terminal, teléfono y mascarilla son informativos. El PDF conserva una discrepancia: artículo 2 menciona 25 números, pero los artículos 5 y 9 dicen 1–28/28 esferas; registrar la inconsistencia y usar los artículos 5 y 9 para la mecánica.

## Informe de Gestión Gubernamental 2018–2024
- URL: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf
- Registra entrega/instalación en marzo de 2022 de máquinas y juegos de esferas para sorteos electrónicos con reconocimiento RFID.
- Nota de auditoría: el informe declara 10 juegos para cada uno de siete productos, pero totaliza 60; la aritmética no coincide. No usar ese total para inferir inventario.

## Solicitudes de acceso a la información
- URL: https://www.loterianacional.gob.mx/Transparencia/SolicitudesAccesoInformacion

## Actualización de evidencia física y cronología — 2026-11-21

La ficha de Normateca separa Sorteos Electrónicos y Sorteos Tradicionales: https://loterianacional.gob.mx/Normateca/Sustantivas?id=2

Corrección de secuencia: en SGVO-PRO-05 revisión 39, la inspección CS-02 y la confirmación del número de sorteo/estuche aparecen antes del cierre; después se verifica el estado cerrado de SICAL y se realiza el pesaje y colocación de esferas. Por tanto, las mediciones de la Tira de Pesaje no se consideran disponibles para una predicción pre-cierre bajo esta secuencia. No usar como norma vigente el documento de proyecto **SGM-PRO-06 “Preparación de Sorteos”, DN-07 v05, revisión 21** (https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/PROYECTO/SUSTANTIVAS/sgm_p0_6_21.pdf): éste decía que Chispazo se pesara preferentemente antes del cierre de 21:15 y listaba colores amarillo/azul y otros rangos. Sus anexos históricos describen impresión de fecha/hora al inicio y fin del pesaje, pesos individuales y campos de inspección CS-02; son pistas para solicitar los originales, no especificaciones actuales. Está en carpeta PROYECTO y “preferentemente” no prueba el timestamp real de cada evento.

La norma vigente confirma:
- CS-02 antes del cierre.
- Pesaje individual en cada sorteo; Smartballs: 4.25–5.25 g y rango máximo 0.30 g; Ping Pong: 2.30–3.00 g y rango máximo 0.15 g.
- Tira firmada y anexada al acta.
- CS-11 posterior a la extracción; la revisión 39 publica como campos mínimos fecha, nombre/número de sorteo, hora del sorteo, estuche seleccionado, resultados y firmas de elaboración/verificación/certificación/representante DG. La hora es del evento, no por esfera; no se publica campo de RFID individual, orden ni timestamp de cada extracción. El procedimiento no define que el orden escrito de los resultados sea el orden físico de extracción.
- Calibración de básculas al menos anual; mantenimiento preventivo/correctivo según calendario anual.
- Incidencias en acta y Bitácora de Concursos y Sorteos (CS-09) cuando afectan resultados.
- Grabación desde el pesaje hasta la celebración como testigo documental; la versión editada anexada al acta es sólo el sorteo, por lo que para reconstruir el pesaje se necesita el máster continuo original y sus timecodes.
- CS-12 registra accesos a la sala durante el evento.

RFID: el Informe de Gestión 2018–2024 declara que las máquinas y esferas adquiridas para sorteos electrónicos tenían reconocimiento RFID y que la instalación quedó concluida el 10-03-2022. No afirma que los estuches como unidades independientes tengan tag RFID. No publica identificadores RFID por máquina/esfera, el mapeo etiqueta→número ni registros de lectura por concurso. El número de estuche de CS-11 no debe confundirse con un tag RFID. El total de juegos del informe es aritméticamente inconsistente (10 juegos para cada uno de 7 productos, pero total declarado 60); no usar ese total para inferir inventario.

V265: el evaluador exige IDs de máquina/estuche y timestamps de disponibilidad pre-cierre, pero no exige ni consume los 28 pesos individuales, RFID por esfera, orden/timestamp de extracción ni procedencia por fila. Por ello sólo puede evaluar asociaciones condicionadas a etiquetas de máquina/estuche; no puede acreditar sesgo físico de esferas. Ver `reports/V265_PHYSICAL_EVIDENCE_AUDIT_20261121.md`.

Regla de uso: ningún dato post-cierre (Tira de Pesaje, extracción, CS-11, acta, incidencias, video del evento o firma del archivo de participaciones) alimenta una predicción que deba congelarse antes del cierre. Los IDs de máquina/estuche o la inspección CS-02 sólo serían candidatos prospectivos si su valor exacto, procedencia y timestamp fueran verificables y accesibles antes del cierre.


## Corrección de inventario normativo — 2026-11-23

Se localizó una copia pública adicional de SGM-PRO-06 Preparación de Sorteos, revisión 22, DN-07 v05, en la ruta SUSTANTIVAS/VIGENTES/sgm_p0_6.pdf. La revisión registra último cambio en junio de 2017, pero el archivo no aparece en la lista actual de Normas Sustantivas Vigentes. Por ello su aplicabilidad actual queda sin confirmar. No es el mismo documento que SGVO-MAN-02, que sí aparece como proyecto normativo en la ventana 23-02-2026 a 04-03-2026.

La copia SGM-PRO-06 describe pesaje individual de 28 esferas Chispazo en orden numérico, valores y estadísticos impresos, fecha/hora al inicio y al final, y colores amarillo/azul según máquina. Su anexo dice preferentemente antes del cierre de 21:15. Esto entra en conflicto con SGVO-PRO-05 revisión 39, listado vigente y actualizado 20-03-2026, que describe pesaje después de verificar SICAL cerrado a las 21:00 y tiene otros rangos de peso en Política 6. No usar SGM-PRO-06 como norma operativa hasta recibir confirmación escrita.

SGVO-PRO-05 actividad 5.2 y Plan de Calidad remiten erróneamente a Política 8 para los pesos; Política 8 trata de la firma electrónica del archivo de participaciones. Los rangos están en Política 6. La rama de sustitución de estuche regresa a actividad 4.1; el texto no dice que se reabran ventas. Ver el informe y matriz V265_DOCUMENT_RECONCILIATION_20261123.
