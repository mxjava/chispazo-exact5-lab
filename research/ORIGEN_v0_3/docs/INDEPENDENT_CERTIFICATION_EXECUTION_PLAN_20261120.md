# ORIGEN v0.3 — ruta ejecutable de certificación independiente

Fecha: 2026-11-20  
Estado: PLAN DE CIERRE; no es certificado ni evidencia de que terceros hayan aceptado participar.  
PR: #10 — rama `fix/origen-v03-integrity-guards-20261120`

## Decisión de arquitectura

No intentar convertir el workflow actual del repositorio del generador en custodio. La separación de funciones debe ser real: el repositorio Exact5 produce un paquete; una persona/organización independiente lo recibe, verifica y conserva bajo su propia identidad y control. La firma del workflow del generador solo puede etiquetarse como **ORIGINATOR_BUILD_ATTESTATION**, nunca como custodia independiente.

La ruta propuesta evita publicar una predicción viva en Git:
1. El generador produce bytes canónicos del payload y manifiesto por concurso.
2. El generador cifra el payload para la clave pública del custodio (o lo entrega por un canal privado acordado). El hash del payload en claro y el hash del ciphertext se calculan sobre bytes exactos.
3. El custodio descarga/recibe ambos archivos, verifica el descifrado, recomputa los dos hashes y valida el concurso/modalidad/fecha contra evidencia oficial archivada.
4. El custodio genera un recibo nuevo, con su propio reloj/servicio de timestamp y su propia identidad criptográfica. El recibo enlaza hashes, concurso, modalidad, candidato, commit, cutoff, fecha límite oficial, recepción y objeto de retención.
5. El custodio conserva payload, ciphertext, manifiesto, recibo y evidencia de tiempo en almacenamiento separado con retención/versionado inmutable; devuelve al proyecto el recibo verificable y una referencia de recuperación.
6. El proyecto verifica la firma/attestation del custodio y el timestamp, publica solo el compromiso no sensible y guarda el bundle de auditoría.

## Qué debe cambiar en el workflow actual

El workflow `.github/workflows/prospective-custody-attestation.yml` no debe ejecutar una certificación independiente. Debe:
- Renombrar su resultado semántico a `ORIGINATOR_BUILD_ATTESTATION` y advertir explícitamente que no es una custodia.
- Exigir un `payload_sha256` y un `ciphertext_sha256` vinculados a objetos reales recibidos por el custodio; nunca aceptar el hash como mera cadena autodeclarada.
- No firmar `READY_FOR_ATTESTATION` como si el propio workflow fuese el receptor.
- Verificar el recibo externo firmado del custodio y su timestamp antes de producir `CUSTODY_ACCEPTED`.
- Validar semánticamente la evidencia de calendario: concurso exacto, modalidad CLASSIC, fecha local, zona IANA, cierre/venta aplicable, URL oficial, hash de bytes originales y reglas de extracción documentadas. La presencia de un archivo gob.mx y su hash no bastan.
- Fallar cerrado: si falta cualquier evidencia o verificación criptográfica, el estado debe ser `BLOCKED_PROVENANCE`; nunca crear un artefacto con etiqueta `SEALED`.

No añadir un campo de identidad de custodio escrito por el generador como sustituto de una firma independiente. No usar artifacts de GitHub Actions de 90 días como evidencia de retención inmutable externa.

## Contrato mínimo de recibo del custodio

El recibo firmado debe incluir:
- `schema_version`, `receipt_id`, `contest_id`, `modality=CLASSIC`, `draw_date_local`, `timezone`, `official_close_at_utc`, `schedule_evidence_sha256`;
- `candidate_id`, `candidate_version`, `source_commit_sha`, `config_sha256`, `environment_sha256`;
- `input_history_sha256`, `input_max_contest_id`, `input_row_count`;
- `payload_sha256`, `ciphertext_sha256` (si aplica), `custodian_recomputed_payload_sha256`, `custodian_recomputed_ciphertext_sha256`;
- `generator_identity`, `custodian_identity`, declaración de independencia/conflictos;
- `generated_at_utc`, `received_at_utc`, referencia de timestamp verificable y resultado de validación pre-cierre;
- identificador/versionado del objeto en retención separada, política de retención, referencia de recuperación;
- firma/attestation del custodio sobre la serialización canónica exacta del recibo.

El custodio debe ser una persona/entidad distinta del generador y no participar en selección o ajuste del candidato. La revisión final debe ser realizada por un tercero distinto del generador y del custodio.

## Dos simulacros no puntuables (antes de iniciar la muestra)

Ejecutar con el custodio real y registrar todos los bytes/recibos:
1. Simulacro A: recepción válida, recomputación independiente, timestamp, almacenamiento separado, recuperación y verificación de firma.
2. Simulacro B: repetir desde un entorno limpio y recuperar el paquete sin acceso al entorno del generador.

Pruebas negativas obligatorias:
- cambiar un byte del payload y del ciphertext;
- hash declarado incorrecto;
- recibo ausente, firma inválida o identidad de custodio igual al generador;
- recepción posterior al cierre;
- concurso/modalidad/fecha equivocada;
- evidencia oficial alterada o que no corresponde al concurso;
- segunda inscripción del mismo concurso;
- borrar/reordenar un evento o truncar el ledger;
- perder acceso al generador y recuperar exclusivamente desde el custodio.

Cada prueba debe producir resultado reproducible PASS/REJECT con logs y hashes. Ningún simulacro se cuenta como sorteo prospectivo.

## Certificación física: carril separado

La certificación de custodia de predicciones no certifica el proceso físico del sorteo. Para `PHYSICAL_EVIDENCE_VERIFIED` se requiere, por concurso y modalidad, el paquete primario original: tira de pesaje de las 28 esferas, CS-11, acta firmada, certificado de calibración aplicable, identificación y continuidad del set de esferas, grabación audiovisual original y cadena de custodia verificable. Los originales deben proceder de Lotería Nacional/autoridad competente o custodio autorizado; capturas, OCR, transcripciones y documentos preparados por el equipo no sustituyen originales.

## Certificación estadística: tercer carril separado

Incluso con custodia perfecta, no existe certificación de ventaja predictiva hasta completar el protocolo preregistrado: mínimo 100 objetivos Classic cronológicos e intactos, candidato/hipótesis/métricas congelados, lift prequential positivo, Holm-ajustado p < 0.05, e-value Exact5 >= 20 bajo un e-process válido y revisión independiente. Todos los fallos, ausencias y misses permanecen en el ledger. No optimizar parámetros sobre los mismos objetivos ni sustituir V294.

## Gates de autorización

| Gate | Evidencia para pasar | Responsable |
|---|---|---|
| G0 — diseño | candidato, configuración, entorno, métricas y reglas preregistrados | equipo + revisor |
| G1 — tercero | custodio y revisor independientes identificados; conflicto declarado | organización externa |
| G2 — integración | contrato de recibo, firma, timestamp, cifrado y retención acordados | generador + custodio |
| G3 — dry-runs | dos simulacros presenciados y pruebas negativas completas | custodio + revisor |
| G4 — primer objetivo | recibo externo verificado estrictamente antes del cierre oficial | verificador |
| G5 — evidencia física | paquete original oficial y cadena de custodia completa | fuente oficial + verificador |
| G6 — edge | 100+ objetivos y todas las reglas estadísticas predeclaradas aprobadas | evaluador independiente |

No saltar gates. No declarar `CERTIFIED`, `SEALED`, `PHYSICAL_EVIDENCE_VERIFIED` ni `EDGE_SUPPORTED` antes de satisfacer el gate correspondiente.

## Solicitud operativa al custodio

La acción externa indispensable es contratar/designar un custodio independiente y acordar un canal seguro de recepción, timestamp y retención. Este repositorio no puede crear por sí solo independencia institucional ni fabricar documentos oficiales. Una vez designado, entregar al custodio: protocolo v1, esquema de manifiesto/recibo, paquete de simulacro, hashes del candidato y política estadística. Obtener aceptación escrita y calendario de los dos simulacros antes de abrir el primer objetivo.

## Protecciones del proyecto

- V294 permanece congelado.
- El CSV canónico permanece byte-a-byte intacto.
- No escribir en `main`, no fusionar PR, no promover candidato.
- No ejecutar el workflow de custodia con manifiestos sintéticos que puedan producir una falsa apariencia de sello.
- Los resultados retrospectivos V322/V323/V326 siguen siendo diagnósticos sin evidencia de edge.
