# V265 — Delta de Acta y cadena de custodia
**28 de noviembre de 2026 · Chispazo Clásico electrónico**

## Avance nuevo

Se amplió el cruce de SGVO-PRO-05 rev. 39 hacia el expediente posterior al sorteo: contenido obligatorio del Acta, anexos específicos de Chispazo, entrega semanal en DVD, procedimiento de discrepancias SICAL/Selección de Ganadores, incidencias, firma diferida, escaneo al OIC, CS-18 opcional y CS-12. La tabla del DVD identifica cuatro códigos Chispazo: CLSBR140, CLIER195, CLSKR170 y CLSAR110; se añadieron a la solicitud de originales.

La firma del Acta puede diferirse hasta cinco días hábiles bajo una excepción limitada; los anexos digitales se entregan semanalmente; CS-18 es potestativo. Por ello, timestamps de firma/entrega no son timestamps del sorteo ni datos pre-cierre.

Se distinguieron dos obligaciones documentales de grabación: la continua contratada desde el pesaje hasta el sorteo y la captación de números en exhibidores por cámaras de sala. El procedimiento no aclara si comparten equipo o archivo. No se obtuvo el máster original ni cadena de custodia.

## Reproducibilidad

- Script: scripts/audit_v265_acta_custody_chain.py
- Pruebas: tests/test_v265_acta_custody_chain.py
- JSON: reports/V265_ACTA_CUSTODY_CHAIN_20261128.json
- Documento: docs/evidence/V265_ACTA_CUSTODY_CHAIN_20261128.md
- Pruebas locales: 9 passed.
- Cruce documental estático y auditoría AST; sin resultados, registros sintéticos ni pruebas estadísticas.

## Fuentes oficiales

- SGVO-PRO-05 rev. 39: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Reglamento Chispazo, arts. 8, 9 y 15: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/ChizpasoDOF18062003.pdf
- Reforma art. 8, SIDOF/SEGOB: https://sidof.segob.gob.mx/notas/docFuente/5236917
- Normateca: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2

## Dictamen

DOCUMENTED_MECHANISM_ONLY. El Acta es el registro oficial; CS-11 es un documento separado/anexo. V265 sigue sin procedencia autenticada ni datos físicos primarios; no prueba sesgo y no autoriza apuestas. OOS, multiplicidad y anytime e-value siguen cerrados.

No se descargaron los PDF oficiales, por lo que no se declara SHA-256 de esas fuentes. Los hashes SHA-256 locales de los artefactos nuevos se informan por separado; no son hashes de los PDF institucionales ni Git blob SHA-1.

V294 congelado; histórico canónico intacto; no se escribió en main, no hubo merge ni promoción.
