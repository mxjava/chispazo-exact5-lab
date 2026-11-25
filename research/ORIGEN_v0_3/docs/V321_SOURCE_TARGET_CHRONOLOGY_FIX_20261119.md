# V321 — corrección de cronología física y separación origen/objetivo

Fecha: 2026-11-19 (corte de investigación)
Rama: `research/origen-v0.3-engine-20261118`
Estado: corrección de ingeniería en rama de investigación; validación CI en curso. No es evidencia física ni estadística.

## Hallazgo confirmado

La versión previa de `physical_intake_v2.py` imponía `source_close <= source_draw <= measurement` y reutilizaba `draw_at` como si fuera tanto la extracción de origen como la del objetivo.

SGVO-PRO-05, revisión 39, describe:
1. Actividad 3.1: confirmar el número de sorteo y el estuche.
2. Actividad 4.1: verificar y documentar el cierre automático de ventas.
3. Actividad 5.1: pesar las esferas.
4. Actividades 5.4–5.5: firmar y entregar la tira de pesaje.
5. Actividad 5.6: depositar las esferas en los alimentadores.
6. Actividad 11.1: accionar la máquina para realizar el sorteo.

Por tanto, la secuencia física/de firma del origen es `set_assigned_at <= source_close <= measurement_at <= source_signed_at <= source_draw_at`. La disponibilidad/custodia del documento para el sistema de puntuación es un evento separado: `source_signed_at <= evidence_available_at <= custody_received_at < target_draw_close_at`. Esa disponibilidad/custodia puede ocurrir antes o después de la extracción de origen; no debe forzarse un orden entre `source_draw_at` y `evidence_available_at`.

Además, `target_draw_at` debe ser un campo independiente de `source_draw_at`, debe ocurrir al cierre de ventas objetivo o después, y el intervalo de mapeo debe cubrir el uso hasta `target_draw_at`.

Fuente primaria: SGVO-PRO-05 rev. 39, publicado 20-03-2026, actividades V.3.1, V.4.1, V.5.1, V.5.4–5.6 y V.11.1:
https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

## Corrección en V2

- Campo `draw_at` sustituido por `source_draw_at`.
- `target_draw_at` agregado como timestamp independiente obligatorio.
- Orden de evento físico: `assignment <= source_close <= measurement <= source_draw < target_close`.
- Orden de firma: `measurement <= source_signed_at <= source_draw_at`.
- Orden de disponibilidad/custodia: `source_signed_at <= evidence_available_at <= custody_received_at < target_draw_close_at`.
- Se permite disponibilidad/custodia anterior o posterior al sorteo de origen, siempre antes del cierre objetivo.
- El mapeo se comprueba hasta `target_draw_at`.
- Se agregan pruebas de pesaje post-cierre/pre-extracción, firma post-pesaje/pre-extracción, disponibilidad a ambos lados de la extracción, medición posterior a la extracción, extracción de origen anterior al cierre, extracción objetivo anterior al cierre y cobertura del mapeo hasta el objetivo.
- Plantilla y contrato V2 actualizados.

## Límites

La corrección solo valida coherencia temporal declarada. No autentica el reloj, documento, firma, custodio, mapeo físico ni continuidad del estuche. No se recibieron masas primarias ni calibración independiente. No se calcula PMF, ranking ni score; no se modifica ningún challenger.

## Protección

- `main`: sin cambios.
- Histórico canónico: sin cambios.
- V294: congelado.
- Producción: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
- Sin promoción ni merge.
