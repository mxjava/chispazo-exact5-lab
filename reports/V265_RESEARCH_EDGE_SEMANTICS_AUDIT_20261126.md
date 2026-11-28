# V265 — Auditoría semántica de la señal de asociación
**Corte: 26 de noviembre de 2026 · Rama de investigación · Sin promoción**

## Hallazgo nuevo

La revisión estática del evaluador V265 detecta un riesgo de interpretación que conviene cerrar antes de que alguien consuma sus reportes:

- El campo `research_edge` se calcula como `sample_ok AND mean_log_lift > 0 AND Holm-adjusted p < 0.05`.
- La función `validate_preclose_metadata` sólo comprueba la bandera declarada `available_before_close` y que `metadata_known_time_local < close_time_local`.
- El contrato de entrada sólo exige concurso, estuche, máquina, bandera de disponibilidad y dos timestamps.
- `physical_evidence_guard()` declara expresamente `source_provenance_required = false`.

Por tanto, un `research_edge=true` sólo podría significar una asociación estadística de etiquetas máquina/estuche bajo metadatos declarados por quien entrega el CSV. **No autentica el documento de origen, el momento real de disponibilidad, la identidad física ni una medición de esfera.**

La barrera existente sí conserva `physical_bias_evidence=false`, `actionable_for_betting=false` y `anytime_evalue_gate_implemented=false`. No encontré evidencia de que el guard promueva directamente una señal a sesgo físico. El problema nuevo es semántico y de procedencia: el nombre `research_edge` es más fuerte que la evidencia que el evaluador consume.

## Reconciliación oficial que sustenta el límite físico

### SGVO-PRO-05 es la norma vigente consultada

La Normateca Sustantivas Vigentes lista SGVO-PRO-05, última actualización 20-mar-2026. El PDF oficial identifica revisión 39, DN-07 versión 09 y fecha de publicación 20-mar-2026.

- [Normateca — Sustantivas Vigentes](https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2)
- [SGVO-PRO-05 revisión 39 (PDF oficial)](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)

### Defecto de referencia cruzada confirmado directamente

La Política 6 contiene los límites de peso:
- Smartballs: 4.25–5.25 g; dispersión máxima 0.30 g.
- Ping Pong: 2.30–3.00 g; dispersión máxima 0.15 g.

La Política 8 regula la firma electrónica del archivo de participaciones. Sin embargo, la actividad 5.2 y el Plan de Calidad 2 remiten a la Política 8 para validar los pesos. La referencia es incorrecta en el propio PDF vigente. No se corrigió por inferencia ni se sustituyó la política citada: queda como aclaración normativa pendiente.

### Cronología: urna, cierre y alimentadores

El artículo 9 del Reglamento Chispazo describe la introducción de 28 esferas en una urna antes del cierre de ventas. SGVO-PRO-05, en cambio, ordena confirmar sorteo/estuche, verificar SICAL en estado Cerrado, pesar individualmente las esferas, firmar la tira y después depositarlas en los alimentadores.

Esto exige aclarar oficialmente si “urna” en el Reglamento identifica el conjunto físico completo, el estuche o una etapa distinta de los alimentadores. No se presume que sean el mismo componente y no se presenta como incumplimiento probado.

- [Reglamento Chispazo, artículo 9 (PDF oficial)](https://www.loterianacional.gob.mx/documentos/legal/reglamentojuegos/Reforma-Reg-Chispazo-marzo-2012.pdf)

## Variables y disponibilidad respecto al cierre

| Variable / registro | Fuente | Momento | Uso prospectivo mismo sorteo |
|---|---|---|---|
| Estado e inspección de equipo | CS-02 | Antes de cada sorteo | Candidato, sólo con original, ID de activo y timestamp verificable |
| Máquina y estuche inicial | Confirmación 3.1 | Antes del cierre | Candidato, pero no equivale al estuche finalmente usado |
| Cierre, ventas brutas/cancelaciones/netas | Sumario SICAL | Después del cierre, antes de ingresar ganadores | No |
| Peso de cada esfera | Tira de Pesaje | Actividad 5.1 posterior a la comprobación de cierre en SGVO-PRO-05 | No para el mismo sorteo |
| Estuche final | Tira / sustitución 5.3 | Puede cambiar tras pesaje no conforme | Sólo si se prueba que quedó fijado y conocido antes del cierre definitivo |
| Identidad RFID | Inventario y logs RFID | No hay lecturas por concurso públicas | No disponible |
| Orden y tiempos de extracción | Video original | Durante el sorteo | Retrospectivo |
| Resultado CS-11 | CS-11 | Después de extracción y cotejo | No |
| Incidencia | Acta / CS-09 | Durante o después; CS-09 se registra al concluir | No, salvo un riesgo pre-cierre documentado aparte |
| Mantenimiento / calibración | Calendario, orden y certificado | Depende de fecha de emisión/recepción | Candidato si existía antes del cierre y está vinculado al activo |
| Firma de participaciones | Archivo y firma electrónica | Inmediatamente después del cierre | No |
| Firma de Relación de Ganadores | Archivo de ganadores | Después de capturar resultados | No |

La definición pública de CS-11 registra fecha, sorteo, hora, estuche seleccionado, resultados y firmas. No establece un campo público de peso por esfera, RFID individual, orden físico explícito o timestamp por extracción. La Tira se firma y se anexa al Acta, pero la definición pública no aporta por sí sola un mapeo esfera↔RFID ni timestamps individuales.

## Separación de modalidades

Chispazo está clasificado oficialmente como sorteo electrónico; la página de producto distingue De las Tres (15:00) de Clásico (21:00). La Normateca lista por separado los procedimientos tradicionales SGVO-PRO-08, SGVO-PRO-34 y SGVO-PRO-15. Las adquisiciones de bolas de madera de maple para sorteos tradicionales no se usan como evidencia de Chispazo.

El PDF oficial de mascarillas del 25-nov-2026 identifica:
- 12395 — Chispazo De las Tres — 01 13 19 23 28.
- 12396 — Chispazo Clásico — 05 07 21 24 28.

Este registro sólo confirma modalidad y publicación de resultado. No aporta procedencia física y no se añadió al histórico canónico, que termina en el concurso 12249.

- [Chispazo: modalidades y horarios](https://www.loterianacional.gob.mx/Chispazo/Chispazo)
- [Mascarilla oficial del 25-nov-2026](https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-25.pdf?v=25112026221906)

## Evidencia que no se obtuvo

No se recuperó ningún original por concurso:
- CS-02 con identificadores de máquina/báscula;
- Tira original con 28 pesos y firmas;
- CS-11 y Acta certificada;
- RFID por esfera, lector, antena y timestamp;
- inventario/seriales y asignación máquina-estuche-concurso;
- certificado de calibración u orden de mantenimiento vinculada a activo;
- CS-09/CS-12/CS-18;
- máster audiovisual y cadena de custodia;
- archivos originales y verificación independiente de firmas.

El procedimiento exige mantenimiento preventivo/correctivo por calendario anual y calibración de básculas al menos anual; no se encontró un calendario público ni un certificado asociado a un sorteo concreto en esta consulta.

## Reproducibilidad

El script `scripts/audit_v265_research_edge_semantics.py` inspecciona el AST del evaluador y comprueba:
1. el contrato de seis campos de metadatos;
2. la expresión exacta que alimenta `research_edge`;
3. los flags fail-closed del guard;
4. que el validador temporal no autentica procedencia documental.

La prueba `tests/test_v265_research_edge_semantics.py` verifica el JSON de auditoría contra el código fuente. No usa resultados de sorteos, datos sintéticos ni registros físicos inventados.

## Dictamen

**Evidencia de mecanismo/documentación, no de sesgo físico ni de ventaja predictiva.** El resultado `research_edge` de V265 debe leerse exclusivamente como pantalla de asociación máquina/estuche. Para elevarlo se necesitan pesos por esfera, IDs/mapeos, orden y timestamps, procedencia autenticada, 100 sorteos Clásico OOS intactos, multiplicidad controlada y anytime e-value ≥20 según los gates del proyecto.

V294 permanece congelado. El histórico canónico no se modifica. No se escribe a `main`, no se integra ni promociona nada.
