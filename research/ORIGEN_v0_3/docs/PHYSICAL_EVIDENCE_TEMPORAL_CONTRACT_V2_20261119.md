# ORIGEN — contrato temporal de evidencia física V2
Fecha: 2026-11-19
Estado: contrato de investigación; separación source/target y orden físico implementados parcialmente en V2. La autenticidad, custodia y continuidad siguen sin validación primaria.
Rama: `research/origen-v0.3-engine-20261118`

## Resultado de inspección del código existente

Inspección de `physical_intake.py` (blob `68e553d0acacbc8c1b0bc935ad23b67a09592690`), `mapping_history.py` (blob `5622a8744851bd3fa8d32b810d6192eb2d176547`) y plantilla V1 (blob `743300774be827956e23a1b44787f8def7849a7b`).

Defectos/limitaciones confirmados:

1. La plantilla V1 omite exactamente dos columnas que el validador exige: `mapping_valid_to` y `draw_at`. Además, no contiene ninguno de los campos nuevos de disponibilidad/custodia definidos aquí.
2. El validador exige actualmente `set_assigned_at < draw_close_at`, `measurement_at < draw_close_at` y `mapping_valid_from < draw_close_at`. Esto mezcla el momento del evento físico con la elegibilidad predictiva. Un pesaje documentado después del cierre del sorteo de origen puede ser evidencia válida del estado físico de ese sorteo y, si hay continuidad demostrada, potencialmente servir para un sorteo posterior. No debe ser descartado como registro histórico solo por ser posterior al cierre de su sorteo de origen.
3. El esquema no registra cuándo el archivo/evidencia quedó realmente disponible para el laboratorio o para el proceso que habría generado la predicción. Un `measurement_at` anterior al cierre no prueba que el documento existiera entonces.
4. `mapping_history.py` comprueba consistencia estructural de intervalos, pero declara expresamente que no autentica identidad física, reloj, firmas ni documentos.

## Principio temporal obligatorio

Separar tres conceptos que nunca deben colapsarse:

- **Tiempo del evento:** cuándo ocurrió el pesaje, asignación, mapeo o sorteo (`measurement_at`, `set_assigned_at`, `mapping_valid_from/to`, `draw_at`).
- **Tiempo de disponibilidad/custodia:** cuándo un tercero o sistema de custodia verificable recibió, selló o publicó los bytes exactos (`evidence_available_at`, `custody_received_at`).
- **Tiempo de decisión:** cierre de ventas del sorteo objetivo (`target_draw_close_at`).

La elegibilidad predictiva requiere evidencia auténticamente disponible y sellada ANTES del cierre del sorteo objetivo. No requiere que el pesaje de origen haya ocurrido antes del cierre de su propio sorteo. La continuidad del conjunto físico y del mapeo esfera↔número entre el evento de origen y el sorteo objetivo debe probarse por intervalos y registros primarios.

## Contrato V2 propuesto

Cada fila representa una esfera física dentro de un conjunto identificado. Los 28 registros de un conjunto/sorteo de origen deben compartir identidad de sorteo, set, máquina, tipo de esfera, timestamps de contexto y referencias de fuente.

Campos temporales y de custodia añadidos:

- `evidence_available_at`: timestamp RFC3339 con offset; primer instante verificable en que los bytes de la evidencia fuente estaban disponibles para el sistema que puntúa.
- `custody_received_at`: timestamp RFC3339 con offset de recepción por custodio independiente.
- `custodian_id`, `custodian_role`: identidad y rol verificables del custodio (no texto libre autocertificado).
- `custody_receipt_ref`: referencia al recibo/registro externo de custodia.
- `custody_receipt_sha256`: hash SHA-256 del recibo.
- `source_signed_at`, `source_signer_id`, `source_signature_ref`: tiempo, identidad y referencia de firma del acta/boleta, cuando exista.
- `trusted_timestamp_ref`: referencia a sello de tiempo confiable o registro de publicación inmutable.
- `source_contest_id`: sorteo al que pertenece el evento físico.
- `source_draw_at`: hora de extracción del sorteo de origen; reemplaza el campo ambiguo `draw_at`.
- `target_contest_id`: sorteo para el que se pretende usar la evidencia; puede ser posterior al sorteo de origen.
- `target_draw_at`: hora de extracción del sorteo objetivo; es distinta de `source_draw_at` y debe ser igual o posterior a `target_draw_close_at`.

No sustituir la evidencia oficial original por un CSV transcrito. Conservar documento original, bytes, hash recalculado, recibo de custodia y cadena de transformaciones.

## Reglas de validación separadas

### A. Integridad estructural (registro histórico)
- Validar 28 esferas, números 1..28 sin duplicados, sphere_id único, tipo y límites metrológicos aplicables, unidades, resolución, certificado vigente al momento de medición, modalidad y enlace al sorteo.
- Validar intervalos de mapeo sin solapamientos incompatibles y que el mapeo esté vigente en el evento al que se refiere.
- Permitir que pesaje/asignación ocurran después del cierre del sorteo de origen si los documentos y el procedimiento así lo establecen. Marcar cronología, no descartar automáticamente.
- No convertir un fallo de disponibilidad predictiva en fallo de integridad histórica.

### B. Elegibilidad predictiva (por target)
Para cada `target_contest_id`:
- `evidence_available_at < target_draw_close_at` y `custody_received_at < target_draw_close_at`.
- `target_draw_at >= target_draw_close_at`; validar la vigencia del mapeo hasta `target_draw_at`, no hasta el sorteo de origen.
- Para el evento de origen, SGVO-PRO-05 rev. 39 ordena asignación/confirmación, cierre de ventas, pesaje, firma/entrega de la tira, colocación en alimentadores y extracción. El contrato V2 separa `set_assigned_at <= draw_close_at <= measurement_at <= source_signed_at <= source_draw_at` de `source_signed_at <= evidence_available_at <= custody_received_at < target_draw_close_at`. La disponibilidad/custodia puede ocurrir antes o después de la extracción de origen; no se fuerza una relación entre `source_draw_at` y `evidence_available_at`.
- El recibo/custodio/sello debe verificarse de forma independiente; hashes recalculados sobre los bytes exactos.
- Fuente, firma, certificado y reloj deben pasar verificación independiente.
- Probar continuidad del `sphere_set_id`, máquina y mapeo esfera↔número durante todo el intervalo hasta el sorteo objetivo. Si hubo sustitución, re-pesaje, remapeo, incidente o hueco documental, excluir la característica afectada o poner el target en cuarentena.
- Si la evidencia se recibió después del cierre objetivo, clasificar `BLOCKED_PROVENANCE` para ese target aunque el documento declare una fecha de medición anterior.
- El tiempo de medición puede ser posterior al cierre del sorteo de origen y aun así ser elegible para un target posterior, siempre que disponibilidad y continuidad estén demostradas.

### C. Salida explícita
Emitir dos etiquetas independientes:
- `historical_record_status`: `STRUCTURE_VALID`, `QUARANTINED` o `INVALID`.
- `predictive_eligibility`: `ELIGIBLE_PRE_CLOSE`, `INELIGIBLE_POST_CLOSE`, `BLOCKED_PROVENANCE` o `BLOCKED_CONTINUITY`.

Nunca usar `STRUCTURE_VALID` como sinónimo de autenticado o elegible.

## Pruebas de aceptación necesarias antes de implementar

1. Plantilla V2 contiene cada columna obligatoria y puede leerse con DictReader; plantilla V1 falla con error de columnas claro.
2. Pesaje después del cierre del sorteo de origen se conserva como registro histórico estructuralmente válido cuando el resto de evidencia es válida.
3. Ese mismo pesaje no es elegible para el sorteo cuyo cierre ya pasó.
4. Evidencia recibida/sellada antes del cierre objetivo y con continuidad íntegra puede resultar elegible para un target posterior.
5. Documento con `measurement_at` anterior pero `evidence_available_at` posterior al cierre objetivo queda `INELIGIBLE_POST_CLOSE`.
6. Falta de custodio, recibo, sello verificable o fuente primaria produce `BLOCKED_PROVENANCE`, no PASS.
7. Rehash de bytes distintos, hash incorrecto, recibo alterado, cadena rota o referencia inexistente produce cuarentena.
8. Zona horaria ausente, timestamp ambiguo, `available_at >= target_close` y `custody_received_at >= target_close` bloquean elegibilidad.
9. Cambio de sphere_set, máquina, esfera, mapeo, calibración vencida, sustitución o incidente intermedio bloquea continuidad para el target afectado.
10. No confundir el sorteo de origen con el objetivo: `source_draw_at` y `target_draw_at` son campos distintos. El mapeo debe cubrir el intervalo desde la asignación hasta el sorteo objetivo.
11. La secuencia física y de firma `set_assigned_at <= draw_close_at <= measurement_at <= source_signed_at <= source_draw_at` se basa en SGVO-PRO-05 rev. 39 (actividades 3.1, 4.1, 5.1, 5.4–5.6 y 11.1). La disponibilidad/custodia se valida por separado y debe ocurrir antes del cierre objetivo; puede ser anterior o posterior a la extracción de origen. Si cambia el procedimiento, revisar estas reglas contra la fuente primaria antes de modificarlas.
11. Las pruebas deben cubrir ambos sentidos del mapeo y límites cerrados de intervalos; además, deben probar que la tira se firma después del pesaje y antes de la extracción, y que la disponibilidad/custodia puede ocurrir a ambos lados de la extracción de origen pero siempre antes del cierre objetivo.
12. Ninguna prueba debe escribir en el histórico canónico, V294, main o challengers.

## Alcance y estado

Este documento es una especificación de diseño, no una implementación, no una certificación de fuente y no evidencia de ventaja. No modifica V1, `physical_intake.py`, V265, challengers ni histórico canónico. La siguiente fase es implementar el contrato en módulos aislados y probarlo en una rama de investigación separada, con revisión del diff y CI antes de considerarlo aceptado.
