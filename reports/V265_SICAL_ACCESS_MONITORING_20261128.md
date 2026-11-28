# V265 — Delta SICAL y control de acceso
**28 de noviembre de 2026 · Chispazo Clásico electrónico**

## Hallazgos nuevos

Se añadieron tres procedimientos públicos de la Normateca al mapa de evidencia:
- SGAF-PRO-95: acceso a áreas restringidas; incluye expresamente la Gerencia de Sorteos y exige campos de entrada/salida, identidad, motivo, entidad y firmas.
- SGAF-INT-48 revisión 08: para el sorteo de 21:00, la copia de archivos de venta con MD5 de producción a contingencia se realiza al día siguiente. MD5 es hash de integridad, no firma electrónica.
- SGAF-PRO-47 revisión 17: define CA-01 (ventas horarias), CA-02 (comunicaciones cada media hora), CA-04 (incidencias tras resolución), CA-05 (mantenimiento correctivo de terminales), CA-06 (interfaces) y monitoreo de MJF/logs.

Estos registros pertenecen a acceso físico y operación SICAL. No son telemetría de máquina, estuche o esfera. CA-04 se captura después de resolver/validar el incidente; para el concurso Clásico, el archivo MD5 de contingencia se copia al día siguiente. No pueden alimentar una predicción pre-cierre del mismo concurso.

## Reproducibilidad

- Documento: docs/evidence/V265_SICAL_ACCESS_MONITORING_20261128.md
- Script: scripts/audit_v265_sical_access_monitoring.py
- JSON: reports/V265_SICAL_ACCESS_MONITORING_20261128.json
- Pruebas: tests/test_v265_sical_access_monitoring.py
- Tipo: cruce estático de procedimientos públicos y auditoría AST de V265; sin resultados ni registros sintéticos.

## Dictamen

DOCUMENTED_MECHANISM_ONLY. No se obtuvieron logs reales por concurso, hashes MD5 originales, archivos de producción/contingencia, bitácoras de acceso ni CA-01/02/04/05/06. V265 permanece sin procedencia autenticada, pesos por esfera, mapeo RFID, orden ni timestamps de extracción. OOS, multiplicidad y anytime e-value siguen cerrados.
