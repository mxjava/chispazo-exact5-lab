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

## Histórico y evaluación prospectiva

`data/history/Chispazo_through_12249.csv` es un baseline histórico congelado que termina en el concurso 12249; por sí solo no es un histórico vigente para nuevos targets. No lo edites ni uses un ejemplo de target como si fuera un registro real.

El ledger efectivo no contiene registros prospectivos. La producción sigue bloqueada mientras V264/V266 no pasen sus gates. Para el procedimiento operativo, las fuentes oficiales, los comandos completos disponibles, el resguardo de evidencias y los criterios/bloqueos científicos, consulta [`docs/PROSPECTIVE_PROTOCOL.md`](docs/PROSPECTIVE_PROTOCOL.md).

## Tests

```powershell
pip install -r requirements.txt
pytest -q
```

CI ejecuta compilación y tests en cada push/PR.

## Protocolo

Ver `docs/PROSPECTIVE_PROTOCOL.md` y `docs/STATUS.md`.
