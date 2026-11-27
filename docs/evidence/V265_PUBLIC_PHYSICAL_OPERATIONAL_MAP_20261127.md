# V265 — Mapa público de evidencia física y operativa
**Corte: 27 de noviembre de 2026 · Alcance: Chispazo Clásico electrónico**

## Delimitación de producto

Chispazo Clásico se evalúa bajo el procedimiento de Sorteos Electrónicos SGVO-PRO-05, que incluye Chispazo en su flujo operativo. No se trasladan a Chispazo los formatos, pesos, instrumentos ni reglas de los sorteos tradicionales. El Reglamento de Sorteos Tradicionales publicado en el DOF el 2 de enero de 2026 limita expresamente su objeto a sorteos tradicionales; se usa sólo para delimitar alcance, no como procedimiento de Chispazo.

## Fuentes oficiales consultadas

1. **Lotería Nacional — SGVO-PRO-05, revisión 39, DN-07 v09**, publicado en el PDF el 20-mar-2026 y listado en Normateca como Sustantivas Vigentes. PDF: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf ; Normateca: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
2. **Lotería Nacional — SAF-MAN-12, Manual de Organización General**, tipo público, emisión febrero 2026: https://www.loterianacional.gob.mx/documentos/Manual_de_Organizacion_General_de_Loteria_Nacional.pdf
3. **Lotería Nacional — Informe de Gestión Gubernamental 2018–2024**, páginas impresas 43–44 y 58: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf
4. **Lotería Nacional — Invitación IA-06-HJY-006HJY001-N-222-2026**, aprobada el 20-oct-2026, publicada el 29-oct-2026; fallo programado para 10-nov-2026: https://loterianacional.gob.mx/Documentos/Legal/AdqLic/IA-06-HJY-006HJY001-N-222-2026.PDF
5. **SEGOB/SIDOF — Reglamento de Sorteos Tradicionales**, publicado el 2-ene-2026: https://sidof.segob.gob.mx/notas/docFuente/5777789

El Manual SAF-MAN-12 identifica una Subgerencia específica para sorteos electrónicos e instantáneos, distinta de la Subgerencia de sorteos tradicionales. A la primera asigna supervisión del calendario anual de mantenimiento, control de incidencias, custodia de actas, videograbaciones y registros operativos, y la obligación de facilitar expedientes originales bajo su resguardo. Esto identifica la unidad responsable; no equivale a tener publicados los registros por concurso.

## Variables, documento y tiempo de conocimiento

| Variable o registro | Documento que la contiene o exige | Momento respecto al cierre | ¿Puede entrar a predicción pre-cierre del mismo concurso? |
|---|---|---|---|
| Estado del equipo y revisión previa | CS-02; actividad 2 del flujo principal de SGVO-PRO-05 | Inspección previa al cierre | Sólo condicionalmente: original firmado, timestamp verificable y activo identificado |
| Máquina y estuche seleccionados | Confirmación del número de concurso y estuche antes del cierre; SGVO-PRO-05 | Pre-cierre, pero puede cambiar si el estuche se sustituye tras el pesaje | Sólo con identificadores seriales/RFID autenticados y constancia de sustitución |
| Peso individual de cada esfera y aceptación del conjunto | Tira de Pesaje; políticas 6 y 7; se pesa una esfera a la vez y se verifica el rango y dispersión | Después del cierre SICAL verificado y antes de cargar las esferas | No para la predicción pre-cierre del mismo concurso. Es post-cierre; podría servir para auditoría retrospectiva |
| Orden de extracción y timestamp de cada esfera | No aparece como campo en la lista pública de CS-11 ni como telemetría pública recuperada | No acreditado | No |
| Identificación RFID de máquina, estuche y esfera individual | Informe 2018–2024 acredita que las máquinas y esferas adquiridas contaban con RFID; no publica mapeo ni logs | El sistema puede existir antes del cierre, pero cada lectura/evento no está publicado | Sólo si se obtiene el mapeo tag-serie-número y el log de lectura firmado, con hora anterior al cierre |
| Cierre SICAL, fecha, hora, concurso y ventas | Pantalla y copias del cierre en actividad 4.1 | En el cierre o inmediatamente después | No; fija el punto de corte y es posterior a la ventana de apuesta |
| Firma de archivos de Participaciones/Cancelaciones | Política 8 y Anexo 1 actividades 1.1–1.11 | Después de comprobar Sumario/SICAL Cerrado, antes del sorteo | No; post-cierre, pre-sorteo |
| CS-11 y Relación de Ganadores | Actividades 13.1–13.6 y Plan de Calidad | Después de extracción y cotejo | No; retrospectivo |
| Video del pesaje y sorteo | Servicio de videograbación desde pesaje hasta sorteo; versión editada se anexa al Acta | El original se genera durante/después del pesaje y sorteo | No para pre-cierre; sí para auditoría posterior |
| Incidencias y riesgos | Acta y bitácora CS-09 para incidencias asentadas; CS-18 comunica debilidades y riesgos potenciales | Depende del evento; la bitácora se actualiza al concluir el sorteo o al reportar el suceso | Sólo un evento y registro auténtico anteriores al cierre podrían ser contexto pre-cierre |
| Acceso a sala y mantenimiento | CS-12 registra asistencia a la sala durante el evento; limpieza/mantenimiento se anota en bitácoras de control de acceso | Durante el evento o al realizar mantenimiento | No sin registro real, hora, persona y relación demostrable con el equipo |
| Mantenimiento de máquina/consola | Calendario anual y registros bajo la unidad operativa; contrato 058-2024 histórico | Calendario puede conocerse antes; reporte real se conoce al ejecutarse y documentarse | Candidato contextual sólo si vinculado al activo y disponible antes del cierre |
| Calibración de báscula | SGVO-PRO-05 público no permitió verificar una frecuencia vigente de calibración; no se obtuvo certificado individual | Depende de certificado y fecha real | No se incorpora sin certificado vigente, ID de báscula y timestamp |
| Archivo Maestro de Transacciones (MJF) | Anexo 1, respaldo diario | Después de las 21:00; el procedimiento no fija su relación exacta con el fin físico del sorteo | No |

## Inventario RFID y mantenimiento: hechos públicos, no inferencias

El Informe de Gestión 2018–2024 señala que el 7-mar-2022 se entregaron 14 máquinas para sorteos electrónicos: 10 Júpiter, 2 Mercury 5 y 2 Mercury 8. También afirma que máquinas y esferas tenían reconocimiento RFID. El mismo texto dice 10 juegos para cada uno de siete productos —lo que aritméticamente daría 70—, pero reporta un total de 60 juegos. La inconsistencia 60/70 queda abierta; no se corrige por inferencia.

El informe también describe dos proyectos no autorizados al cierre de junio de 2024: adquisición de 8 máquinas y 2 sistemas RFID, y adquisición de 4 balanzas de precisión con impresoras térmicas. Esto no prueba que no existieran otros equipos ni describe el inventario actual; sí impide asumir que esas compras de respaldo se realizaron.

El mismo informe registra el contrato 058-2024 para mantenimiento preventivo/correctivo de 21 máquinas, controles y consolas de ocho productos, incluyendo Chispazo, y señala que concluyó dentro del periodo reportado al 30-jun-2024. El resumen público no aporta números de serie, máquina por concurso, orden de trabajo, fecha/hora de intervención, piezas cambiadas ni aceptación individual. Es evidencia histórica de contratación, no bitácora de mantenimiento por sorteo.

La invitación 222-2026 es distinta: su objeto es mantenimiento de equipos eléctricos de inmuebles. Incluye plantas de emergencia, UPS, subestación/transformador, bancos de capacitores, pararrayos, tableros y sistemas solares. Su anexo requiere reportes técnicos con equipo/serie, fecha y horas de inicio/fin, causa, refacciones, mediciones eléctricas antes/después, fotografías y firmas; la entrega del reporte se establece dentro de tres días hábiles del servicio. Es una fuente potencial de contexto de continuidad eléctrica, no mantenimiento de máquinas de extracción, estuches o básculas. La invitación programa fallo para el 10-nov-2026, pero el PDF de invitación no acredita adjudicación, contrato firmado ni servicios ejecutados; esos documentos y reportes no fueron recuperados en esta revisión.

## CS-11: corrección documental

La actividad 13.1 ordena cuatro ejemplares. La actividad 13.6 enumera el original para SVO y tres copias: una copia para el operador del área de Control de Datos, una para el Inspector SEGOB y otra para el representante DTT. La distribución normativa sí está completa. No se encontraron constancias de entrega/recepción por concurso; por tanto, no se afirma que los cuatro ejemplares hayan sido efectivamente entregados en cada sorteo.

## V265: contrato real del evaluador

El evaluador exige CONCURSO, sphere_set_id, machine_id, available_before_close, close_time_local y metadata_known_time_local. Consume etiquetas de máquina/estuche y comprueba una cronología declarada. No consume peso individual, mapeo RFID esfera-número, orden de extracción ni timestamps por extracción. El validador no exige documento fuente, URL, SHA-256, firma verificada ni cadena de custodia; source_provenance_required permanece falso. El guard sí fija physical_bias_evidence=false y actionable_for_betting=false, y no implementa el anytime e-value.

Por ello, research_edge sólo puede leerse como pantalla de asociación sobre etiquetas y resultados, no como prueba de sesgo físico. Una fecha declarada por quien carga el CSV no autentica que el dato existiera antes del cierre.

## Anclas de transcripción para pruebas reproducibles

- Chispazo Clásico se clasifica como sorteo electrónico.
- CS-02: inspección del equipo antes del cierre.
- Tira de Pesaje: medición individual después del cierre SICAL verificado.
- CS-11: cuatro ejemplares; tercera copia al operador del área de Control de Datos.
- El Informe 2018–2024 reporta 14 máquinas con RFID.
- El mismo informe declara 60 juegos de esferas para siete productos.
- El contrato 058-2024 incluye mantenimiento de 21 máquinas y Chispazo.
- La invitación IA-06-HJY-006HJY001-N-222-2026 cubre equipos eléctricos de inmuebles.
- No se obtuvieron originales por concurso de CS-02, Tira de Pesaje, RFID, CS-11, video, mantenimiento ni calibración.

## Dictamen

La evidencia pública describe controles y registros que el proceso debe generar. No se obtuvieron originales de concursos ni telemetría física. No se ejecutó análisis estadístico con resultados de sorteos ni datos sintéticos. La línea sigue clasificada como evidencia de mecanismo/operación, no ventaja predictiva.
