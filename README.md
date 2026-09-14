# Chispazo Exact5 Lab

Laboratorio reproducible para investigación, validación prospectiva y generación controlada de portafolios Chispazo 5-de-28.

## Objetivo

Maximizar evidencia real de mejora en Exact5 sin fuga temporal, sin ajuste post-hoc y sin promover señales que no sobrevivan evaluación fuera de muestra.

## Principios

1. Entrenar sólo con concursos anteriores al target.
2. Bloquear producción si los modelos Exact5 están muertos, constantes o degradados.
3. Separar `research_edge` de `actionable_edge`.
4. Comparar siempre contra el null uniforme 1/C(28,5).
5. Mantener ledger prospectivo inmutable por concurso.
6. No promover estrategias por un caso aislado; exigir evidencia OOS y corrección por multiplicidad.

## Estructura

- `data/history/`: históricos consolidados.
- `data/physical-metadata/`: estuche, máquina, pesos e incidencias cuando existan.
- `data/prospective-ledger/`: predicciones congeladas antes del sorteo.
- `src/v263/`: integridad + candidate islands + null hedge.
- `src/v264/`: evidence firewall + Exact5 CPU repair.
- `src/v265/`: physical-regime evidence scanner.
- `src/validation/`: preflight obligatorio.
- `reports/`: auditorías y resultados OOS.
- `predictions/`: salidas por target.

## Estado actual

- V264: `RESEARCH_ONLY_NO_EDGE`
- V265: `RESEARCH_ONLY_METADATA_REQUIRED`

No se debe presentar una combinación como superior al uniforme mientras el firewall de evidencia permanezca cerrado.
