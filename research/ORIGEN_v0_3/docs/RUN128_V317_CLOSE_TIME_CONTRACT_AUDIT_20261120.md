# Exact5 Run128 — auditoría del contrato de cierre de V317 y estado oficial

**Captura:** 20-11-2026 03:58:36, America/Mexico_City  
**Rama:** `research/run123-official-timing-audit-20261120`  
**Disposición:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`

## 1. Estado oficial del día

- La página dedicada de resultados de Chispazo sigue publicando como último resultado el concurso **12384**, Clásico del 19-11-2026: **01 02 09 21 25**. La página indica como siguiente fecha el 20-11, pero aún no muestra resultado de hoy.
- El índice de mascarillas sigue teniendo como fecha más reciente el **19-11-2026**.
- A diferencia de la captura Run127, la página directa del portal de comercializadores ahora sí muestra **12385, 20-11-2026, 15:00**. Esto corrobora el objetivo de las 15:00 como De las Tres.
- La página oficial de Chispazo mantiene el horario De las Tres 15:00 y Clásico 21:00. Ninguna fuente abierta identifica aún el ID del Clásico del 20-11.

La captura se hizo antes de las 15:00; no se esperaba todavía una mascarilla o resultado del día. La discrepancia Run127 se conserva como observación histórica: el portal directo estaba desactualizado entonces y ya se actualizó en esta captura.

## 2. Defecto concreto en el contrato de entrada de V317

Revisé estáticamente los archivos exactos de la rama:

- `src/origen/physical_intake.py`, blob `dcfe7bf332f67daab153512104ad33e3d7086422`, líneas 109, 111 y 118.
- `tests/test_physical_intake.py`, blob `07e3e3e3c4d4668acd9da83b84a9ee6bfc05eb5c`, líneas 19 y 43.
- Prerregistro V317, blob `3e09df57c021fd1a4f6f964d04265efaba325a61`.

El validador convierte `draw_close_at` a hora de Ciudad de México y comprueba que la **fecha** local coincide con `draw_date`; luego comprueba que asignación, medición y mapeo sean anteriores a ese timestamp. No contrasta la hora con la modalidad ni exige que el cierre provenga de un evento SICAL autenticado o de una excepción autorizada.

### Contraejemplo que ya está en la suite

El fixture de `test_complete_preclose_contest_is_structurally_usable` declara:

- Modalidad: `CLASSIC`
- Cierre: `2026-11-20T19:00:00-06:00`
- El test espera que el concurso sea estructuralmente usable.

Pero la página oficial de Chispazo indica Clásico a las **21:00**. SGVO-PRO-05 revisión 39, política 9, establece cierre de ventas a las 21:00 para sorteos nocturnos y 15:00 para De las Tres; sólo permite modificaciones con autorización y notificación institucional. El validador no detecta que el fixture de Clásico está dos horas adelantado.

**Consecuencia:** un timestamp incorrecto o prematuro podría hacer que mediciones posteriores al cierre real parezcan anteriores al cierre registrado. Eso debilita el gate temporal de V317 y cualquier sello pre-cierre construido sobre él.

## 3. Control requerido antes de habilitar intake

Sin cambiar código en esta ejecución, dejo definidos los controles necesarios:

1. Vincular `TRES → 15:00` y `CLASSIC → 21:00` en hora local.
2. Exigir referencia verificable al cierre SICAL: URI/folio/evento inmutable y hash de la evidencia disponible.
3. Aceptar horarios distintos sólo con autorización/circular y confirmación de aplicación en SICAL, según política 9.
4. Añadir negativos: `CLASSIC 19:00`, `TRES 21:00`; positivos: horarios oficiales y excepciones autorizadas documentadas.
5. Mantener la regla estricta: toda característica debe estar disponible antes del cierre **real autenticado**, no sólo antes de un campo de fecha/hora suministrado.

No se editó `physical_intake.py`, no se alteró el prerregistro, no se ejecutó pytest y no se hizo scoring. Es una auditoría estática reproducible por blobs y líneas, no una prueba de ejecución.

## 4. Recuperación Run121

El manifiesto `RUN121_PACKAGE_MANIFEST.json` declara ZIP SHA-256 `db24189fcbe0d5fe50db3292afd3bda3e9d17f700dc9110c46e97306ae1cfce2`, pero también dice expresamente `code_committed_to_github_branch=false`. La rama contiene informes y manifiesto, no los módulos ejecutables del paquete. La consulta de releases devolvió una lista vacía. El ZIP exacto sigue sin recuperarse y no repetí las 62 pruebas sintéticas.

## 5. Integridad

- V294 congelado.
- Histórico canónico sin escrituras; blob esperado preservado como referencia.
- No se recalculó el SHA-256 del CSV desde bytes en esta captura.
- Sin escrituras a `main`, sin merge, promoción, cambios de challenger ni puntuaciones prospectivas.

## 6. Clasificación

- Contrato de horario/cierre del intake V317: `MODEL_IMPLEMENTATION_DEFECT`.
- Evidencia física primaria: `BLOCKED_PROVENANCE`.
- Ventaja predictiva: `NO_EDGE_EVIDENCE`.
- Producción: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

Fuentes oficiales: [SGVO-PRO-05 revisión 39](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf), [horarios de Chispazo](https://www.loterianacional.gob.mx/Chispazo/Chispazo), [resultados dedicados](https://comercializadores.loterianacional.gob.mx/Chispazo/Resultados), [índice de mascarillas](https://www.loterianacional.gob.mx/Mascarillas/Mascarillas), [portal de comercializadores](https://comercializadores.loterianacional.gob.mx/).
