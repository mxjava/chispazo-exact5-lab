# V265 — Auditoría de evidencia física y operativa de Chispazo Clásico

**Corte:** 2026-11-21  
**Fuentes:** Lotería Nacional, Normateca y SIDOF/SEGOB.  
**No se repitieron frecuencias, pares, tríos ni transiciones. No se modificaron V294 ni el histórico canónico.**

## Dictamen

Chispazo Clásico es un **Sorteo Electrónico**, a las 21:00. La Normateca vigente identifica SGVO-PRO-05, revisión 39, con actualización 20-03-2026. No se deben importar controles ni registros de sorteos tradicionales.

La documentación pública acredita inspección CS-02, confirmación previa del estuche planeado, pesaje de cada esfera, límites por tipo, sustitución si falla, carga progresiva, CS-11, cámaras, actas, incidencias, mantenimiento anual, calibración anual de básculas y capacidad RFID de máquinas/esferas.

**Bloqueo decisivo:** no se localizaron archivos públicos por concurso con pesos individuales, IDs de máquina/estuche, lecturas RFID y horas, orden/timestamps de extracción, CS-02, CS-11/Acta, tiras de pesaje, calibraciones, mantenimiento, incidencias o grabaciones originales. No hay evidencia suficiente para probar sesgo físico ni para una predicción prospectiva.

## 1. Modalidad: electrónica, no tradicional

- La página oficial clasifica Chispazo como Sorteo Electrónico y distingue De las Tres (15:00) y Clásico (21:00): https://loterianacional.gob.mx/Chispazo/Chispazo
- La Normateca vigente incluye Chispazo en Sorteos Electrónicos y lista SGVO-PRO-05: https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-34 (peso/diámetro de bolas de madera y ábacos) y SGVO-PRO-08 (mantenimiento de equipos tradicionales) son de **Sorteos Tradicionales**. Sus registros de bolas de madera, ábacos, CS-28/CS-22 y mantenimiento no son datos de Chispazo:
  - https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_34.pdf
  - https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_08.pdf

## 2. Cronología contra el cierre de ventas

El artículo 8 del Reglamento, reformado en la publicación de SEGOB/SIDOF de 2012, identifica el Acta como resultado oficial de Chispazo; la web y la mascarilla son informativas. El video no sustituye el Acta. SGVO-PRO-05 sí exige una grabación documental desde el pesaje hasta el sorteo y que la versión editada del sorteo se anexe al Acta.

| Variable / documento | Momento según SGVO-PRO-05 | Prospectivo para el mismo sorteo |
|---|---|---|
| CS-02, inspección de equipo | Antes de cada sorteo y antes del paso de cierre | Potencial; el formato, sus campos y timestamps por concurso no están publicados. |
| Estuche planeado, actividad 3.1 | Confirmación previa al cierre | Potencial; no se lista un registro separado ni se publican IDs por concurso. |
| Sumario SICAL | Se genera al cierre; incluye concurso, fecha/hora, estado cerrado, ventas, cancelaciones y netas | Es el límite, no una entrada pre-cierre. |
| Tira de pesaje | Después de 4.1 y antes de cargar las esferas; peso individual en orden numérico | No para el mismo sorteo. Podría servir a sorteos posteriores si el mismo set permanece y el dato se conoce antes del siguiente cierre. |
| Sustitución de estuche | Después del cierre si falla el pesaje; se repite el pesaje | El estuche final puede diferir del planeado antes del cierre. |
| Carga progresiva | Después del pesaje y antes del sorteo | Orden de carga, no orden de extracción. |
| Firmas electrónicas de participaciones/cancelaciones | Después del cierre y antes del sorteo | Custodia/integridad del archivo de ventas; no es dato físico. |
| Video de cámaras | Durante la extracción; grabación contratada desde el pesaje hasta el sorteo | Retrospectivo; no hay originales por concurso ni timestamps por esfera publicados. |
| CS-11 y Acta | Después de la extracción | Retrospectivo; no es entrada del mismo sorteo. |
| Incidencias / CS-09 | Se documentan después del suceso si afecta el resultado | Retrospectivo para ese sorteo; podría informar sorteos futuros si se resuelve antes del próximo cierre. |
| Mantenimiento/calibración | Calendario anual; básculas calibradas al menos una vez al año | Sólo para futuros sorteos si se publican fechas, activo, certificado y vigencia antes del cierre. |

**Parámetros oficiales de pesaje:** Smartballs 4.25–5.25 g y rango máximo entre la más ligera y la más pesada de 0.30 g; Ping Pong 2.30–3.00 g y rango máximo 0.15 g. Si una esfera incumple, se cambia el estuche y se repite el pesaje. La tira registra el peso de cada esfera y se firma/anexa al Acta; el procedimiento público no enumera sus campos temporales ni publica tiras reales.

**Matiz normativo:** el art. 9 del Reglamento describe 28 esferas en la urna antes del cierre, luego cierre y firma del archivo de participaciones, y después extracción. El procedimiento operativo SGVO-PRO-05 detalla el pesaje después del paso de cierre y antes de cargar los alimentadores. No se aclara públicamente si la “urna” es una etapa de preparación distinta de la carga final. Hace falta la bitácora de eventos para fijar el momento real; no se inventa un timestamp.

## 3. Qué contiene cada documento y qué falta

- **CS-02:** inspección del equipo antes de cada sorteo. El procedimiento público no enumera campos ni identifica la máquina/serie por concurso.
- **Tira de pesaje:** peso individual de cada esfera, pesada en orden numérico; firmas y anexo al Acta. No se localizó una tira pública por concurso ni se especifican timestamps en el texto publicado.
- **CS-11:** el plan de calidad enumera fecha, número de sorteo, número de estuche, esferas frente a números anotados y nombres de participantes; el paso 13.5 exige firmas. No define ID de máquina, RFID, pesos ni timestamp individual de extracción.
- **Acta / CS-09:** recoge incidencias que se apartan del procedimiento y afectan el resultado; el Acta y anexos se escanean al OIC y se resguardan.
- **Video:** la política 30 de SGVO-PRO-05 exige contratar grabación desde el pesaje hasta la celebración del sorteo, como testigo documental; la versión editada (sólo el sorteo), en DVD/CD/USB, forma parte del Acta. Las cámaras registran los números al aparecer en exhibidores. Hay transmisiones públicas de algunos sorteos, pero no se localizaron originales por concurso ni timestamps estructurados por esfera. El video es anexo probatorio del Acta, no resultado oficial independiente.
- **Firma electrónica:** protege archivos de participaciones y cancelaciones después del cierre; se entrega al Inspector y queda bajo custodia del OIC. No mide el mecanismo físico.
- **Mantenimiento/calibración:** mantenimiento preventivo/correctivo según calendario anual; calibración de básculas al menos anual. No se localizaron bitácoras, IDs de básculas ni certificados por equipo.
- **SGVO-MAN-02:** SGVO-PRO-05 lo cita para preparar/operar equipos. No aparece en el índice público de normas vigentes consultado; se encontró sólo una entrada en el registro histórico de proyectos normativos (23-02-2026 a 04-03-2026). No pude verificar la versión vigente ni los campos completos de CS-02.

### RFID: capacidad, no evidencia por concurso

El Informe de Gestión Gubernamental 2018–2024, p.43, afirma que se entregaron 14 máquinas el 07-03-2022 (10 Júpiter, 2 Mercury 5, 2 Mercury 8), que la instalación terminó el 10-03-2022 y que máquinas y esferas tienen RFID. También dice 10 juegos por producto, incluido Chispazo, pero enumera siete productos y reporta total de 60 juegos (7 × 10 = 70): inconsistencia que impide aceptar ese total sin aclaración.

El informe señala que una propuesta de 2024 de 8 máquinas, 2 sistemas RFID y 4 balanzas/impresoras no estaba autorizada al cierre de junio de 2024; no determina el inventario de 2026. No se hallaron tag IDs, logs RFID, hora/lector de lectura ni asignación de máquina/estuche por concurso. RFID acredita capacidad de identificación, no que exista telemetría pública por sorteo.

## 4. Evaluador V265.1: alcance y defectos de gate

Archivo: `src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py` (Git blob SHA-1 `0010b5f07c6cbfcb78201180fbe758d68e61b031`).

1. Usa `planned_sphere_set_id_preclose` y `machine_id` como variables de régimen. `final_sphere_set_id_postweigh` y su hora se conservan sólo para auditoría; no entran al predictor. No ingiere pesos por esfera, RFID, orden/timestamps de extracción, incidencias, mantenimiento ni calibración.
2. Exige cobertura exacta de concursos, `available_before_close=True`, `metadata_known_time_local < close_time_local`, URL de fuente y sintaxis SHA-256. El timestamp sigue siendo genérico y aportado por el registro: no se autentica independientemente ni demuestra disponibilidad campo por campo. La sintaxis de SHA-256 no prueba que se hayan capturado los bytes originales.
3. Añade un guard explícito de modalidad: cada fila de metadata debe identificar `SLOT=21:00` (o una etiqueta Clásico permitida). Falta de SLOT, De las Tres y valores desconocidos bloquean el evaluador. No se usa la secuencia de IDs para clasificar silenciosamente.
4. Soporta mínimo de 100 filas prequential OOS y ajuste Holm sobre un p-family. No ingiere el **anytime e-value** del proyecto ni custodia independiente. Para evitar falsa autorización, `actionable_for_betting` está ahora fijado a `false` y el evaluador siempre emite bloqueos externos. Sigue siendo investigación, no un gate de producción.
5. Es una asociación condicionada por máquina/estuche planeado, no una prueba de sesgo físico. Para estudiar mecanismo se requieren pesos por esfera, IDs verificables, calibración, RFID, orden de extracción y timestamps trazables.

El `V265_PHYSICAL_REGIME_SCANNER` usa resultados históricos como proxies, no mediciones físicas. No se repitieron análisis cerrados. La validación de esta rama, tras corregir fixtures que omitían SLOT en metadata, terminó en CI run `44932594545`: `compileall` aprobado, **278 pruebas aprobadas, 2 omitidas, 0 fallidas**.

## 5. Análisis reproducible nuevo

Se añadió un auditor de cronología documental, sin crear registros ficticios:

- `scripts/audit_v265_public_evidence.py`
- `data/physical-metadata/V265_PUBLIC_PROCEDURE_TIMELINE_20261121.json`
- `reports/V265_PUBLIC_EVIDENCE_AUDIT_20261121.json`
- `tests/test_v265_public_evidence_audit.py`

Valida el orden de 2.1, 3.1, 4.1, 5.1, 5.6, 11.1 y 13.1, separa etapas pre-cierre/post-cierre y bloquea la conclusión si no hay datos físicos por concurso. **8 pruebas locales aprobadas.** No estima sesgo, efecto mecánico ni log-lift.

## 6. Bloqueos y evidencia que falta

Por concurso, con fuente, hora y vínculo verificable:

1. CS-02 completo, ID/modelo/serie de máquina y timestamp de inspección.
2. CS-11 y Acta firmada, con estuche planeado y final.
3. Tira original con los 28 pesos, tipo de esfera, báscula/ID, unidad, timestamp y firmas.
4. RFID: tag IDs, lector, resultado de lectura, timestamp y fallas.
5. Video original desde el pesaje hasta el sorteo y versión editada anexa al Acta, con timestamps/identificación de evento y secuencia de extracción bola por bola.
6. CS-09, bitácora, incidencias y sustituciones/repeticiones.
7. Calendario/órdenes de mantenimiento y certificados de calibración.
8. Definición oficial del momento de fijación del estuche final y aclaración de la secuencia “urna” vs pesaje/carga.

La solicitud de transparencia V265 debe ampliarse a CS-02, Acta/CS-11, tiras originales, RFID/logs, videos, timestamps, certificados de básculas y bitácoras. Pedir CSV/XLSX si existe base consolidada; en su defecto, documentos por concurso.

## 7. Fuentes oficiales

- Normateca vigente: https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-05 Rev.39: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Página oficial Chispazo: https://loterianacional.gob.mx/Chispazo/Chispazo
- Reglamento Chispazo: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf
- Reforma SEGOB/SIDOF de 2012, art. 8: https://sidof.segob.gob.mx/notas/docFuente/5236917
- Informe de Gestión Gubernamental 2018–2024, p.43: https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf
- SGVO-PRO-34 tradicional: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_34.pdf
- SGVO-PRO-08 mantenimiento tradicional: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_08.pdf
- Transmisión oficial de ejemplo, Chispazo Clásico 11880 (12-03-2026): https://www.youtube.com/watch?v=0yFt8VedP1Y

## 8. Integridad

- Histórico canónico `data/history/Chispazo_through_12249.csv`: Git blob SHA-1 `2f5ff5bfbd779fe505736398e417b7211955958e` tanto en `main` como en el branch base.
- V265 evaluator: Git blob SHA-1 `ca83e4af6ccd12f68ff0a725969561254b0be866`.
- `main` no se modificó; V294 no se modificó; no hubo promoción ni escritura al histórico.
- Los SHA-256 de los PDF oficiales no se reportan porque la consulta entregó texto indexado y no bytes originales. Los hashes de artefactos del repositorio se entregan como Git blob SHA-1 en el registro de commit.

**Clasificación final:** evidencia de procedimiento y capacidad de control; no hay evidencia pública por sorteo para medir mecanismo, prueba de sesgo físico ni ventaja predictiva prospectiva. Toda señal futura debe superar OOS, multiplicidad y anytime e-value.
