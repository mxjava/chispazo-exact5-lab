# V321 — corrección de cronología física y separación origen/objetivo

Fecha: 2026-11-19 (corte de investigación)
Rama: `research/origen-v0.3-engine-20261118`
Estado: corrección de ingeniería propuesta en rama de investigación; pendiente de CI en este commit. No es evidencia física ni estadística.

## Hallazgo confirmado

La versión previa de `physical_intake_v2.py` imponía:

`source_close <= source_draw <= measurement`

y reutilizaba `draw_at` como si fuera tanto la extracción de origen como la del objetivo. Ambas decisiones eran incorrectas:

1. SGVO-PRO-05, revisión 39, ordena cerrar ventas (actividad 4.1), pesar las esferas (5.1), colocarlas en alimentadores (5.6) y después accionar la máquina para realizar el sorteo (11.1). Por tanto, para el sorteo de origen la cronología aplicable es `set_assigned_at <= source_close <= measurement_at <= source_draw_at`, no la inversa.
2. El intervalo `mapping_valid_from/to` debe cubrir el uso del mapeo hasta el sorteo objetivo. Comprobarlo solamente en el sorteo de origen no acredita que el mapeo siga vigente para el objetivo.
3. `target_draw_close_at` es el cierre de ventas del objetivo; el sorteo objetivo ocurre al cierre o después. La comprobación anterior rechazaba el orden normal al comparar el timestamp de origen con el cierre objetivo.

Fuente primaria: SGVO-PRO-05 rev. 39, publicado 20-03-2026, apartados V.4.1, V.5.1–5.6 y V.11.1. URL:
https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

## Corrección en V2

- Se sustituye el campo ambiguo `draw_at` por `source_draw_at`.
- Se agrega `target_draw_at` como timestamp independiente obligatorio.
- Se exige `assignment <= source_close <= measurement <= source_draw <= evidence_available <= custody_received < target_close`.
- Se exige `target_draw_at >= target_draw_close_at`.
- La vigencia del mapeo se comprueba hasta `target_draw_at`.
- Se agregan regresiones para pesaje después del cierre y antes de la extracción de origen, medición posterior a la extracción, extracción de origen antes del cierre, extracción objetivo anterior al cierre y cobertura del mapeo hasta el objetivo.
- La plantilla V2 refleja ambos timestamps.

## Límites

La corrección solo valida coherencia temporal declarada. No autentica el reloj, el documento, la firma, el custodio, el mapeo físico ni la continuidad del estuche. No se recibieron masas primarias ni calibración independiente. No se calcula PMF, ranking ni score y no se modifica ningún challenger.

## Protección

- `main`: sin cambios.
- Histórico canónico: sin cambios.
- V294: congelado.
- Producción: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
- Sin promoción ni merge.
