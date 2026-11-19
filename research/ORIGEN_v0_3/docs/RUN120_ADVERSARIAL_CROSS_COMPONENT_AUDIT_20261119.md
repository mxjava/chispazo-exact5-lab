# Exact5 Run120 — auditoría adversarial independiente de Run119

**Estado:** `MODEL_IMPLEMENTATION_DEFECT` + `BLOCKED_PROVENANCE` + `NO_EDGE_EVIDENCE`.  
**Producción:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Alcance y preservación

Auditoría de sólo lectura del paquete Run119 y de la rama `research/run119-pmf-custody-20261119`. No hubo replay retrospectivo, generación de predicciones, puntuación de resultados oficiales, cambio de challenger, escritura a `main`, fusión ni promoción.

- Run119 ZIP SHA-256: `c2dbac999643fb08c7e64e658e6c371ea18f6432a45b5c956ddfac9981e554b1`.
- Run119 SHA256SUMS: 7/7 archivos verificados.
- Python 3.13.5; 24 pruebas PMF + 17 ledger = 41 aprobadas con `PYTHONPATH=src`; compileall PASS.
- Ejecución inicial de pytest sin PYTHONPATH falló en collection por `ModuleNotFoundError: origen`; el workflow Run119 sí define `PYTHONPATH: src`.
- Auditoría exhaustiva independiente: `combination_rank` coincide con `itertools.combinations(range(1,29),5)` en 98,280/98,280 resultados.
- PMF uniforme: 98,280 pesos unitarios, normalizador exacto 98,280, payload canónico de 393,284 bytes y log-lift cero en las muestras verificadas.

## Hallazgos reproducidos

### R120-01 — estado SEALED no está enlazado a los bytes del PMF

`build_target_ledger()` acepta cualquier hash SHA-256 sintácticamente válido como `payload_manifest_sha256`. `verify_target_ledger()` sólo recibe el manifiesto de objetivos y el ledger; no recibe el manifiesto PMF ni el payload. Una entrada SEALED con hash sintético `bbbb…bbbb` devuelve `PASS_COMPLETE_RELATIVE_TO_MANIFEST`.

Ese estado significa completitud relativa al manifiesto suministrado, no que exista un PMF real sellado antes del cierre. Se requiere un verificador conjunto que compruebe los bytes exactos del manifiesto PMF, su hash, el payload, objetivo, fecha, modalidad, cierre, época del candidato y timestamp de recepción del custodio.

### R120-02 — scoring no exige el ledger completo

`score_sealed_sequence()` recibe una lista de registros, no el manifiesto oficial de objetivos ni el ledger. Devuelve `complete_target_ledger=NOT_CHECKED_BY_THIS_MODULE`; un subconjunto de un solo objetivo produce `n_scored=1`, aunque el estado final siga bloqueado por procedencia.

Se necesita una compuerta superior que compare exactamente el conjunto de Clásicos esperados con todos los estados terminales y después compare la subserie SEALED con los PMF/resultados puntuados. Ningún objetivo FAILED, LATE o QUARANTINED puede desaparecer del denominador OOS.

### R120-03 — el ledger valida fecha local, pero no hora oficial Clásico

El manifiesto acepta `2026-11-20T01:00:00Z`, equivalente a 19:00 del 19/11 en `America/Mexico_City`, para un objetivo CLASSIC del 19/11. La página oficial de Chispazo publica Clásico a las 21:00. La validación actual sólo verifica que la fecha local coincida.

Se requiere validar 21:00 local para el calendario normal o exigir una excepción oficial autenticada. No inferir modalidad por paridad del ID.

### R120-04 — timezone y URI del calendario no están restringidos

El constructor PMF acepta `timezone_name="UTC"` y una URI `https://example.invalid/not-official` y devuelve `PASS_CRYPTOGRAPHIC_INTEGRITY_ONLY`. La respuesta sí declara que la autenticación externa sigue pendiente, pero una compuerta específica de México debe exigir `America/Mexico_City`, HTTPS, host oficial permitido y bytes de fuente cuyo hash se verifique; excepciones sólo mediante evidencia oficial autenticada.

### R120-05 — hash de resultado sólo se valida por formato

`score_sealed_sequence()` comprueba que `official_result_sha256` tenga forma SHA-256, pero no recibe los bytes de la fuente oficial. Por tanto, el hash no queda vinculado al sorteo, modalidad, fecha ni combinación suministrados. Hace falta un verificador de resultado que capture bytes, calcule el hash, extraiga los campos oficiales y los compare antes del scoring.

## Estado de GitHub

- Run119 HEAD: `5c43c6ff284d14e66fecae70256d076769295906`.
- `main`: `424eee9dd906f8235541e97ae61026441083bbfe`.
- Comparación: rama divergente, 210 commits adelante y 2 detrás; no reconciliada.
- Blob canónico CSV en main y Run119: `2f5ff5bfbd779fe505736398e417b7211955958e`, idéntico.
- PR #8 sigue Draft/Open/Unmerged y apunta a `research/origen-v0.3-engine-20261118`, no a Run119.
- Verificación importante: los paths `research/ORIGEN_v0_3/src/origen/pmf_custody.py` y `target_ledger.py` no existen todavía en la rama GitHub Run119 (Contents API 404). El paquete ZIP es una referencia local descargable de 41 pruebas, aún no integración de código ni CI del repositorio.

## Próxima compuerta

Implementar `verify_exact5_run()` para enlazar: manifiesto oficial de objetivos → ledger → manifiesto PMF de cada SEALED → payload PMF → evidencia de custodia/timestamp → bytes del resultado oficial → secuencia puntuable. Debe rechazar cualquier diferencia de conjuntos y validar el cierre Clásico de 21:00 local.

La auditoría reproducible Run120 está disponible como paquete local: `Exact5_Run120_AdversarialAudit_20261119.zip`, SHA-256 `5a919ed09338e393467ecfde6c3d3a60b187c4f3dfcc8844e52cb4713cff2a2b`.

**No hay nuevos objetivos OOS puntuados. V294 permanece congelado. El histórico canónico permanece intacto.**
