# Ledger prospectivo de registros efectivos

Este directorio contiene únicamente archivos efectivos creados por `src.pipeline.freeze_prediction`, con nombres `target_<T>.json`. No agregues plantillas, ejemplos, predicciones retrospectivas ni resultados futuros ficticios. En este checkout el ledger está vacío: este README no es un registro.

Un archivo sólo es un registro prospectivo válido si fue creado por el flujo aprobado antes del cierre oficial de ventas, su preflight está en `PASS`, su concurso coincide con `history_max + 1`, y su `registration_sha256` fue retenido independientemente con sello temporal. No edites ni reemplaces un registro existente. El congelador rechaza el mismo destino, pero un archivo local no impide que un administrador del sistema lo altere o borre; conserva registro, manifiesto, evidencia fuente y hashes en almacenamiento externo con retención inmutable/control de acceso.

El JSON contiene el target, timestamps del host, SHA del commit, versión del modelo, máximo del histórico, SHA-256 del histórico y ranking, gates y las 30 líneas normalizadas. No contiene la fuente del cierre oficial ni sus capturas, el resultado posterior ni un sello temporal independiente. Esos elementos se conservan como evidencia separada, vinculada por hashes, fuera del ledger efectivo.

No escribas evaluaciones posteriores en este directorio ni modifiques la predicción al conocer el resultado. Guarda cada evaluación y cada incidente como artefacto separado y append-only en el repositorio de auditoría controlado, con referencia al target y al SHA del registro. Consulta [`../../docs/PROSPECTIVE_PROTOCOL.md`](../../docs/PROSPECTIVE_PROTOCOL.md) para el procedimiento y las limitaciones vigentes.
