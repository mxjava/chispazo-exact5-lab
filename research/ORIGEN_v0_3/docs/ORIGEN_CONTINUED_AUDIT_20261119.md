# ORIGEN v0.3 — auditoría técnica continuada
Fecha: 2026-11-19
Rama: `research/origen-v0.3-engine-20261118`
Alcance: auditoría de ingestión física, continuidad de mapeo, preregistro V317, kernel Plackett–Luce y barrera de promoción V265.

## Resumen ejecutivo

Estado global: `BLOCKED_PROVENANCE / RESEARCH_ONLY_NO_EDGE`.

Esta revisión no encontró evidencia física primaria de Chispazo ni una calibración independiente de beta. No se calculó ranking ni se generaron picks. Se verificó que el kernel Plackett–Luce implementa la probabilidad del conjunto no ordenado mediante suma de órdenes; no se identificó defecto matemático en esa recurrencia. Sí se identifican brechas de esquema/procedencia que impiden demostrar que una medición y su correspondencia esfera-número eran conocidas antes del cierre.

## Artefactos inspeccionados

| Archivo | Git blob SHA |
|---|---|
| `research/ORIGEN_v0_3/src/origen/physical_intake.py` | `68e553d0acacbc8c1b0bc935ad23b67a09592690` |
| `research/ORIGEN_v0_3/src/origen/mapping_history.py` | `5622a8744851bd3fa8d32b810d6192eb2d176547` |
| `research/ORIGEN_v0_3/tests/test_physical_intake.py` | `3c07d9f112ebd66531134e445e66583365d7de87` |
| `research/ORIGEN_v0_3/tests/test_mapping_history.py` | `9fa00cdb7016abda3a6c6f522fefc8c8e36d5986` |
| `research/ORIGEN_v0_3/PREREGISTRATION_V317_PHYSICAL_MASS_PLACKETT_LUCE.md` | `3e09df57c021fd1a4f6f964d04265efaba325a61` |
| `research/ORIGEN_v0_3/src/origen/plackett_luce.py` | `f8b331485a76dc6552c9a05e7104ebaf8cb99971` |
| `data/physical-metadata/PHYSICAL_EVIDENCE_LONG_FORM_TEMPLATE_V1.csv` | `743300774be827956e23a1b44787f8def7849a7b` |
| `src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py` | `ca83e4af6ccd12f68ff0a725969561254b0be866` |

## Hallazgos

### F1 — Plantilla incompatible con el contrato del validador (confirmado; ya reportado)

La plantilla CSV no contiene `mapping_valid_to` ni `draw_at`, mientras `REQUIRED_COLUMNS` y `validate_physical_csv` los exigen. Un archivo creado directamente desde la plantilla falla antes de validar filas. Las pruebas existentes no detectan el defecto porque sus fixtures fabrican ambas columnas manualmente.

Clasificación: `MODEL_IMPLEMENTATION_DEFECT` en el flujo de captura. No es evidencia de sesgo.

### F2 — Falta el instante en que la evidencia estuvo disponible para el custodio/modelo (brecha nueva)

El esquema contiene `measurement_at`, `mapping_valid_from`, `mapping_valid_to`, `set_assigned_at`, `draw_close_at`, hash del documento y referencia. No contiene un campo que registre cuándo el documento fuente quedó firmado, capturado o disponible para el proceso de predicción (por ejemplo, `evidence_available_at` / sello verificable de recepción).

Esos tiempos no son equivalentes:
- `measurement_at`: cuándo se afirma que se hizo el pesaje.
- `mapping_valid_from/to`: intervalo efectivo declarado para la correspondencia.
- `evidence_available_at`: cuándo quedó disponible evidencia verificable de esos datos.

Sin el último dato, un documento incorporado después del cierre podría declarar retrospectivamente una medición anterior al cierre. El SHA-256 prueba identidad de bytes sólo si se conserva y recalcula el archivo; no prueba cuándo existían esos bytes. El propio módulo advierte que no autentica firmas, relojes, certificados ni hashes de fuente.

Impacto: el validador puede dar `STRUCTURE_VALID` a una estructura temporal plausible sin demostrar disponibilidad pre-cierre. V317 exige custodia independiente y tiempos autenticados antes del cierre, por lo que el validador estructural por sí solo no satisface ese gate.

Corrección mínima propuesta (no aplicada): incorporar `evidence_available_at`, identificador/rol de custodio y referencia de sello verificable; exigir `evidence_available_at < draw_close_at` para elegibilidad predictiva. Mantener por separado `measurement_at` para investigación mecanística. Si la evidencia se obtuvo después del cierre, conservarla como mecanismo/forense y excluirla del predictor pre-cierre.

Pruebas necesarias: evidencia disponible antes del cierre; evidencia capturada después del cierre aunque `measurement_at` sea anterior; firma/custodia ausente; reloj sin zona horaria; hash de bytes recalculado contra el archivo preservado.

Clasificación: `MODEL_IMPLEMENTATION_DEFECT` de contrato de procedencia / `BLOCKED_PROVENANCE` para evaluación predictiva.

### F3 — No se adopta como regla universal que el pesaje deba ocurrir después de asignar el estuche

Una pasada automatizada previa sugirió exigir `set_assigned_at <= measurement_at`. Esta revisión no acepta esa regla como defecto universal: un juego de esferas puede medirse antes de asignarse a un concurso y luego conservar identidad y mapeo válidos. La condición correcta depende de demostrar continuidad física, mapeo y disponibilidad pre-cierre. No se debe introducir una restricción temporal que descarte mediciones previas legítimas sin fundamento documental.

### F4 — V265 contiene una bandera de acción que no implementa todos los gates Exact5

En `src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py`, `actionable` depende de `research_edge`, disponibilidad pre-cierre y cobertura completa. `research_edge` depende de muestra mínima, media positiva y p-valor Holm. Esa bandera no incorpora el anytime e-value Exact5 >=20, dos salidas prospectivas independientes selladas, custodia independiente ni la confirmación de al menos 100 sorteos Classic OOS con modalidad primaria.

Impacto: `actionable_for_betting` no debe interpretarse como autorización para apostar, promover ni afirmar ventaja. No se modificó V265 ni ningún challenger. El gate global del proyecto sigue siendo más estricto que la bandera heredada.

Corrección segura propuesta: deprecar/renombrar la bandera como `research_gate_candidate_only` o forzarla a falso hasta integrar todos los gates. Cualquier cambio futuro requiere revisión aislada y pruebas específicas; no forma parte de este commit.

Clasificación: `MODEL_IMPLEMENTATION_DEFECT` en la semántica de promoción; sin evidencia de edge.

### F5 — Auditoría de mapping_history sin defecto confirmado

El auditor revisa ambas direcciones de correspondencia (ID físico -> número y número -> ID físico), detecta intervalos superpuestos cerrados con mapeos incompatibles y cuarentena ambas filas afectadas. Las pruebas cubren remapeo, duplicidad inversa, intervalos no superpuestos, asignación fuera de intervalo, vigencia en extracción, timestamps sin zona y sets distintos.

Límite restante: el módulo sólo valida estructura declarada; no autentica identidad física, reloj, fuente o firma. Esto es una limitación explícita, no un bug oculto.

### F6 — Kernel V317 Plackett–Luce: revisión matemática sin defecto encontrado

`log_plackett_luce_set_probability` suma recursivamente las probabilidades de todas las posibles últimas extracciones del conjunto; cada denominador elimina sólo los elementos extraídos antes. Por tanto marginaliza el orden de las 5 bolas y no confunde el resultado no ordenado con una permutación específica. Las pruebas comparan contra enumeración de 120 órdenes y normalización de los 98,280 conjuntos, además de beta=0 uniforme.

La preregistración correctamente exige beta firmado desde calibración física independiente, congelado antes de inspeccionar resultados; prohíbe buscar beta con resultados ganadores. No hay calibración independiente ni registros físicos primarios: V317 sigue bloqueado, sin estimación empírica.

## Acciones y pruebas

- Esta auditoría es documental/estática; no se afirma haber ejecutado pytest localmente.
- Los resultados de CI previamente registrados (194 pruebas ORIGEN y 393 raíz en la ejecución citada por la automatización) son pruebas de software con fixtures; no prueban autenticidad física ni ventaja predictiva.
- No se modificó código de V265, challengers, V294, `main` ni el histórico canónico.
- No se incorporaron resultados a la historia ni se generaron scores.

## Próximo trabajo priorizado

1. Diseñar versión V2 de esquema y plantilla con disponibilidad/custodia de evidencia, manteniendo campos de evento físico separados.
2. Añadir pruebas de regresión para la captura y la elegibilidad temporal.
3. Revisar la barrera V265 sin tocar el challenger: especificar un contrato de promoción Exact5 que requiera todos los gates.
4. Obtener y preservar archivos originales por concurso: Acta, CS-11, tira de pesaje, identificadores RFID, asignación del estuche, registros de máquina, calibración y grabación íntegra.
5. Obtener calibración independiente de beta; si no existe, mantener V317 bloqueado.
6. Ejecutar evaluación prospectiva sólo con Classic de modalidad primaria confirmada, datos pre-cierre autenticados y dos salidas selladas.

## Estado final

- V294: FROZEN.
- Histórico canónico: intacto.
- Challengers: sin modificaciones.
- Evidencia física: no recibida.
- Beta V317: no calibrada independientemente.
- Edge: no demostrado.
- Producción: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
