# V265 — Fuentes oficiales y trazabilidad

## Procedimiento vigente de Sorteos Electrónicos
- Normateca Lotería Nacional, `PROCEDIMIENTO SORTEOS ELECTRÓNICOS`, SGVO-PRO-05, revisión 39, actualización marzo de 2026.
- URL: https://comercializadores.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Hechos relevantes:
  - pesaje para cada sorteo;
  - parámetros de peso para Smartballs/Ping Pong;
  - cambio de estuche si no cumple;
  - CS-11 registra número de sorteo y estuche seleccionado;
  - tira de pesaje registra peso de cada esfera;
  - CS-11 y tira de pesaje se integran al acta;
  - el flujo documentado ubica cierre de venta antes de pesaje, por lo que un análisis de explotabilidad debe comprobar disponibilidad pre-cierre.

## Reglamento Chispazo
- URL: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf
- El sorteo usa 28 esferas y extrae 5 al azar.

## Informe de Gestión Gubernamental 2018–2024
- URL: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf
- Registra adquisición/entrega en marzo de 2022 de máquinas de sorteos, juegos de esferas para Chispazo y RFID.
- Nota de auditoría: el propio informe contiene una inconsistencia aritmética en el total declarado de juegos; V265 no usa ese total como dato analítico.

## Solicitudes de acceso a la información
- URL: https://www.loterianacional.gob.mx/Transparencia/SolicitudesAccesoInformacion


## Actualización de evidencia física y cronología — 2026-11-21

Se verificó la versión que la Normateca lista como vigente:
- SGVO-PRO-05, revisión 39, DN-07 versión 09, publicada el 20-03-2026.
- URL canónica: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- La ficha de Normateca separa expresamente Sorteos Electrónicos y Sorteos Tradicionales: https://loterianacional.gob.mx/Normateca/Sustantivas?id=2

Corrección importante de secuencia: en la versión vigente, la inspección CS-02 y la confirmación del número de sorteo/estuche aparecen antes del cierre; después se verifica el estado cerrado de SICAL y, a continuación, se realiza el pesaje y la colocación de esferas. Por tanto, las mediciones de la tira de pesaje no se consideran disponibles para una predicción pre-cierre bajo esta secuencia. No se debe usar como norma vigente el documento antiguo de proyecto DN-07 v05 que describía un pesaje preferentemente antes del cierre.

La norma vigente confirma:
- CS-02 antes de cada sorteo.
- Pesaje individual de esferas en cada sorteo; Smartballs: 4.25–5.25 g y rango máximo 0.30 g; Ping Pong: 2.30–3.00 g y rango máximo 0.15 g.
- Tira firmada y anexada al acta.
- CS-11 posterior a la extracción; registra fecha, número de sorteo, número de estuche, correspondencia esfera/número y participantes.
- Calibración de básculas al menos anual; mantenimiento preventivo/correctivo según calendario anual.
- Incidencias en acta y, cuando afectan el resultado, en bitácora CS-09.
- Grabación desde el pesaje hasta la celebración; la grabación editada forma parte del acta.
- CS-12 registra accesos a la sala durante el evento.

RFID: el Informe de Gestión 2018–2024 declara que las máquinas y esferas adquiridas para sorteos electrónicos tenían reconocimiento RFID y que la instalación quedó concluida el 10-03-2022. No publica identificadores RFID por máquina/esfera, el mapeo etiqueta→número, ni registros de lectura por concurso. El total de juegos del informe es aritméticamente inconsistente (10 juegos para cada uno de 7 productos, pero total declarado 60); no usar ese total para inferir inventario.

V265: el evaluador exige IDs de máquina/estuche y timestamps de disponibilidad pre-cierre, pero no exige ni consume los 28 pesos individuales, RFID por esfera, orden/timestamp de extracción ni procedencia por fila. Por ello sólo puede evaluar asociaciones condicionadas a etiquetas de máquina/estuche; no puede acreditar sesgo físico de esferas. Ver `reports/V265_PHYSICAL_EVIDENCE_AUDIT_20261121.md`.

Regla de uso: ningún dato post-cierre (tira de pesaje, extracción, CS-11, acta, incidencias, video del evento o firma del archivo de participaciones) alimenta una predicción que deba quedar congelada antes del cierre. Los IDs de máquina/estuche o la inspección CS-02 sólo serían candidatos prospectivos si su valor exacto, procedencia y timestamp fueran verificables y accesibles antes del cierre.
