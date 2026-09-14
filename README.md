# Chispazo Exact5 Lab

Laboratorio reproducible para investigación causal, validación prospectiva y control de producción sobre Chispazo 5-de-28.

## Objetivo

Buscar evidencia real de mejora en Exact5 sin fuga temporal, sin ajuste post-hoc y sin confundir cobertura estructural con ventaja predictiva.

La probabilidad uniforme de una combinación exacta es `1 / C(28,5) = 1 / 98,280`. Un portafolio de 30 líneas distintas tiene masa Exact5 uniforme de `30 / 98,280`.

## Regla principal

**Ninguna combinación se promueve como predictivamente superior al uniforme mientras los gates de evidencia permanezcan cerrados.**

## Versiones

- `src/v263/`: integridad del parent, candidate islands y null hedge explícito.
- `src/v264/`: CPU Exact5 repair, evidence firewall, exact-set anytime test y auditoría reciente.
- `src/v265/`: scanner/evaluator de régimen físico y metadata externa.
- `src/validation/preflight_v2.py`: V266 strict pre-sorteo gate.
- `src/pipeline/`: congelamiento y evaluación de registros prospectivos.

## Estado científico actual

- V264 OOS: `RESEARCH_ONLY_NO_EDGE`.
- Exact-set anytime evidence: no demuestra ventaja suficiente frente al null uniforme.
- V265: `RESEARCH_ONLY_METADATA_REQUIRED`.
- Producción predictiva concentrada: **BLOCKED** hasta superar los gates.

Esto no impide usar un null hedge para cobertura, pero debe etiquetarse como cobertura, no como predicción.

## Histórico causal

`data/history/Chispazo_through_12249.csv` termina exactamente en el concurso 12249 y sirve como baseline congelado para reconstruir el target 12250 sin leakage.

Para agregar un resultado verificado:

```powershell
python -m src.data.append_verified_result `
  --history data/history/Chispazo_through_12249.csv `
  --contest 12250 `
  --date 2026-09-13 `
  --numbers N1 N2 N3 N4 N5 `
  --source-url "URL_VERIFICADA"
```

No se debe ejecutar ese append antes de haber congelado la predicción del propio target.

## Preflight V266

Ejemplo estricto:

```powershell
python -m src.validation.preflight_v2 `
  --history data/history/Chispazo_through_12249.csv `
  --target 12250 `
  --ranking runs/target_12250/v249_full_ranking_98280.csv `
  --firewall-report reports/v264_firewall100_report.json `
  --exactset-summary reports/v264_summary.json `
  --out runs/target_12250/preflight.json
```

El preflight valida, entre otras cosas:

- histórico legible y contiguo;
- concurso objetivo = último histórico + 1;
- cero filas del target/futuro;
- cinco números únicos en rango 1..28;
- ranking completo de 98,280 exact sets;
- combinaciones únicas;
- al menos dos especialistas Exact5 vivos;
- evidencia OOS V264;
- e-value exact-set mínimo para permitir concentración.

Cualquier fallo crítico produce `state=BLOCKED`.

## Ledger prospectivo

Sólo después de un `PASS` puede congelarse un portafolio:

```powershell
python -m src.pipeline.freeze_prediction `
  --target 12251 `
  --portfolio predictions/target_12251.csv `
  --preflight runs/target_12251/preflight.json `
  --model-version V266 `
  --ledger-dir data/prospective-ledger
```

El registro almacena timestamp UTC, hashes de histórico/ranking y las 30 líneas. Un target ya registrado no puede sobrescribirse.

Después del sorteo:

```powershell
python -m src.pipeline.evaluate_registration `
  --registration data/prospective-ledger/target_12251.json `
  --result N1 N2 N3 N4 N5
```

## Tests

```powershell
pip install -r requirements.txt
pytest -q
```

CI ejecuta compilación y tests en cada push/PR.

## Protocolo

Ver `docs/PROSPECTIVE_PROTOCOL.md` y `docs/STATUS.md`.
