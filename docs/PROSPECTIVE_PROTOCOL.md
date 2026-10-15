# Protocolo operativo para evaluación prospectiva Exact5

Este procedimiento prepara un registro pre-sorteo verificable y una evaluación posterior reproducible. La integridad técnica del registro no demuestra que sus selecciones predigan mejor que el azar.

## Estado y regla de autorización

En el estado documentado por este checkout, V264 permanece `RESEARCH_ONLY_NO_EDGE`, la evidencia Exact-set no permite producción concentrada y V265 sigue requiriendo metadata externa. El estado de producción es `BLOCKED / RESEARCH_ONLY_NO_EDGE` (`docs/STATUS.md`). Además, el histórico versionado del repositorio termina en el concurso 12249 y `data/prospective-ledger/` no tiene registros efectivos. Ese CSV sólo sirve para reconstrucciones causales hasta el target 12250; no es el histórico vigente para un target actual.

Por tanto, hoy no hay autorización para crear una predicción prospectiva válida. El resto de este documento es el procedimiento que debe seguirse si, en una versión aprobada futura, los gates requeridos pasan y existe un histórico actualizado. Un resultado fallido, una fuente no confirmada o un cierre ya ocurrido significa **no registrar predicción**. No se reintenta el mismo target con cambios de modelo, parámetros, histórico o criterio después de conocer el resultado.

V294 sigue congelada, V304 rechazada y V312/V313 en shadow. Ningún paso de este protocolo cambia esos estados.

## Fuentes y evidencia por target

Use los canales oficiales de Lotería Nacional: [información del juego Chispazo](https://comercializadores.pronosticos.gob.mx/Chispazo/Chispazo) y [resultados oficiales de Chispazo](https://comercializadores.pronosticos.gob.mx/Chispazo/Resultados). La página del juego informa dos sorteos diarios (De las Tres y Clásico); esos horarios de sorteo no son por sí solos evidencia del cierre de ventas de un concurso concreto.

Antes de ejecutar el modelo, identifique el concurso exacto, su modalidad/fecha y la hora oficial de cierre de ventas en una página o aviso oficial que los vincule expresamente. No infiera el cierre a partir de la hora del sorteo, de otro juego ni de un concurso anterior. Si el cierre exacto no puede confirmarse en una fuente oficial, bloquee el target.

Para cada target, capture y conserve fuera del checkout, en un repositorio de evidencia controlado:

- número de concurso, modalidad, fecha y zona `America/Mexico_City`;
- cierre oficial de ventas con zona horaria y URL exacta de la fuente;
- hora UTC y hora local de captura, identidad del operador y fuente de reloj;
- archivo capturado (HTML, PDF o captura legible de la página oficial) y su SHA-256;
- último resultado oficial usado para formar el histórico: concurso, fecha, cinco números, URL, horas de captura y archivo de evidencia con SHA-256;
- ruta de la ejecución, versión de este protocolo y un manifiesto que relacione los archivos con sus checksums.

Conserve la evidencia original como bytes. Una URL o una transcripción escrita no sustituye la captura. Si la página no permite una captura automatizada íntegra, conserve una impresión PDF o captura de pantalla legible e identifique esa limitación. El sitio oficial es la fuente de contenido; un SHA-256 local sólo identifica bytes, no certifica quién los publicó ni cuándo.

El cierre oficial y el instante del operador son dos datos diferentes. El registro incluye `registered_at_utc` y `registered_at_mexico_city`, pero éstos provienen del reloj del host y no prueban independientemente que el registro se congeló antes del cierre. Guarde también el cierre oficial en el manifiesto del target y obtenga un sello temporal independiente para el SHA del registro y dicho manifiesto.

## Preparación del histórico sin modificar el baseline

El histórico entregado al preflight debe contener todos los concursos consecutivos hasta `T-1`, sin duplicados, sin filas de `T` o posteriores, y sus cinco números deben coincidir con resultados oficiales. `validate_history` comprueba integridad estructural, continuidad y cierre en `target-1`; esa validación no autentica por sí misma el resultado oficial.

No edite `data/history/Chispazo_through_12249.csv`. Cree un directorio nuevo por intento y trabaje sobre una copia de baseline o una reconstrucción versionada. Si usa `src.data.append_verified_result`, el comando modifica el CSV que recibe y añade provenance en otro archivo; por ello ejecútelo sólo sobre la copia de trabajo, nunca sobre el baseline ni sobre un artefacto ya congelado:

```powershell
$target = [int](Read-Host 'Número del concurso objetivo T')
$expectedLast = $target - 1
$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd'T'HHmmss'Z'")
$run = "runs/prospective/target_${target}_$runId"
if (Test-Path $run) { throw "La ruta de ejecución ya existe: $run" }
New-Item -ItemType Directory -Force "$run/source", "$run/inputs", "$run/reports" | Out-Null
$history = "$run/inputs/history_through_$expectedLast.csv"
$provenance = "$run/inputs/history_provenance.csv"
Copy-Item 'data/history/Chispazo_through_12249.csv' $history
```

La copia anterior es sólo una base histórica. Para `T-1` posterior a 12249, agregue cada sorteo faltante en orden, tras cotejarlo con la fuente oficial y conservar su evidencia. Por cada fila, invoque el comando existente con los datos reales verificados:

```powershell
python -m src.data.append_verified_result `
  --history $history `
  --contest <concurso_verificado> `
  --date <AAAA-MM-DD_verificada> `
  --numbers <N1> <N2> <N3> <N4> <N5> `
  --source-url '<URL_oficial_exacta>' `
  --provenance $provenance
if ($LASTEXITCODE -ne 0) { throw 'Append fallido; registrar incidente y bloquear esta copia' }
```

Los textos entre `<...>` son marcadores que se reemplazan con valores confirmados, no datos de ejemplo. La herramienta no es transaccional: si falla a mitad de escritura, preserve la carpeta de intento y registre el fallo; no use esa copia, no la presente como histórico aceptado y no la borre para ocultar el incidente. Reintente en un identificador de ejecución nuevo. Una vez completa, archive el CSV exacto y provenance como artefactos de sólo lectura; calcule SHA-256 y compruebe por separado que el máximo es `T-1`, que no hay huecos y que cada fila añadida coincide con su evidencia oficial.

Para generar nombres de ruta y mantener una captura de origen, use valores reales del concurso verificado. No añada capturas, manifiestos o ejemplos al directorio de registros efectivos.

## Ejecución reproducible de los gates

Use un checkout aprobado con dependencias instaladas, commit conocido y árbol de trabajo tracked limpio. Guarde todos los productos en el directorio único de esta ejecución. El comando V249 debe usar los defaults del commit aprobado; no añada overrides, `--force` ni `--force-retrain`, y desactive el registro paralelo interno para que el único registro operativo sea el de V266:

```powershell
$rankingDir = "$run/v249"
New-Item -ItemType Directory -Force $rankingDir | Out-Null
python -m src.v264.CHISPAZO_V264_PARENT_REPAIR `
  --history $history `
  --target $target `
  --expected-last $expectedLast `
  --lines 30 `
  --out-dir $rankingDir `
  --no-prospective-register
if ($LASTEXITCODE -ne 0) { throw 'V249 abortó; registrar incidente y bloquear el target' }
$ranking = "$rankingDir/v249_full_ranking_98280.csv"
$portfolio = "$rankingDir/v249_selected_30_target_${target}.csv"
```

El generador `CHISPAZO_V264_EXACTSET_ANYTIME.py` no tiene CLI de argumentos: su bloque `__main__` usa rutas fijas de otra máquina. No ejecute `python -m` sobre ese archivo. La función disponible es `main(history_path, outdir, warmup=800)`; para invocarla con las rutas de esta ejecución:

```powershell
$env:EXACT5_HISTORY = (Resolve-Path $history).Path
$env:EXACT5_EXACTSET_OUT = [System.IO.Path]::GetFullPath("$run/v264_exactset")
python -c 'import os; from src.v264.CHISPAZO_V264_EXACTSET_ANYTIME import main; main(os.environ["EXACT5_HISTORY"], os.environ["EXACT5_EXACTSET_OUT"], 800)'
if ($LASTEXITCODE -ne 0) { throw 'Exact-set falló; registrar incidente y bloquear el target' }
$exactset = "$run/v264_exactset/v264_summary.json"
Remove-Item Env:EXACT5_HISTORY, Env:EXACT5_EXACTSET_OUT
```

Ese resumen recorre resultados históricos en orden y no es un registro prospectivo real ni una observación nueva de la cohorte.

Ejecute el firewall usando los artefactos de la misma corrida:

```powershell
$firewallDir = "$run/v264_firewall"
python -m src.v264.CHISPAZO_V264_EVIDENCE_FIREWALL `
  --ranking $ranking `
  --meta "$rankingDir/v249_gate_meta_rows.csv" `
  --exactset-summary $exactset `
  --out-dir $firewallDir
if ($LASTEXITCODE -ne 0) { throw 'Firewall abortó; registrar incidente y bloquear el target' }
$firewall = "$firewallDir/v264_firewall_report.json"
$firewallState = (Get-Content $firewall -Raw | ConvertFrom-Json).state
if ($firewallState -ne 'PROMOTE_EXACT5') { throw "Firewall=$firewallState; no congelar" }
```

Finalmente, ejecute el preflight y exija tanto exit code 0 como estado JSON `PASS`:

```powershell
$preflight = "$run/reports/preflight.json"
$preflightLog = "$run/reports/preflight.log"
$preflightOutput = & python -m src.validation.preflight_v2 `
  --history $history `
  --target $target `
  --ranking $ranking `
  --firewall-report $firewall `
  --exactset-summary $exactset `
  --out $preflight 2>&1
$preflightExit = $LASTEXITCODE
$preflightOutput | Set-Content $preflightLog -Encoding utf8
if ($preflightExit -ne 0) {
  if (Test-Path $preflight) {
    throw 'Preflight bloqueado; conservar reporte y registrar no-registro'
  }
  throw 'Preflight abortó antes de escribir reporte; conservar preflight.log/traceback y registrar no-registro'
}
if ((Get-Content $preflight -Raw | ConvertFrom-Json).state -ne 'PASS') {
  throw 'Preflight no está en PASS; no congelar'
}
```

El código de salida 0 del firewall por sí solo no autoriza producción: también se exige `state == PROMOTE_EXACT5`. Un fallo crítico, un artefacto ausente, el estado `RESEARCH_ONLY_NO_EDGE`, una incertidumbre de fuente/hora o un preflight distinto de `PASS` bloquea la congelación. Conserve los informes fallidos y registre el target como no registrado; nunca transforme un fallo en PASS relajando reglas para ese mismo sorteo.

Los paths de ejecución deben ser nuevos. Las rutas `runs/` están ignoradas por Git y no son almacenamiento de auditoría durable: archive inputs, outputs, capturas y manifiestos fuera del checkout en almacenamiento con retención controlada.

## Congelación y anclaje externo

Antes de congelar:

1. Compruebe que la hora de cierre corresponde al concurso exacto, está expresada en `America/Mexico_City` y aún no ocurrió.
2. Verifique el identificador de target, `history_max == T-1`, los estados de gates y la relación entre los paths y el manifiesto.
3. Compruebe `git status --short` y que el SHA del código aprobado sea el checkout que produjo los artefactos.
4. Archive primero la evidencia fuente, histórico y ranking de sólo lectura, con sus hashes.

Sólo si esos puntos se cumplen, use el portfolio seleccionado por la versión aprobada, el preflight `PASS`, y el SHA completo del HEAD:

```powershell
$commit = (git rev-parse HEAD).Trim()
$freezeLog = "$run/reports/freeze.log"
$freezeOutput = & python -m src.pipeline.freeze_prediction `
  --target $target `
  --portfolio $portfolio `
  --preflight $preflight `
  --model-version 'V249/V266' `
  --commit-sha $commit `
  --repo-root . `
  --ledger-dir data/prospective-ledger 2>&1
$freezeExit = $LASTEXITCODE
$freezeOutput | Set-Content $freezeLog -Encoding utf8
if ($freezeExit -ne 0) { throw 'Freeze fallido; conservar errores y no sobrescribir el target' }
$registrationSha = ("$($freezeOutput | Select-Object -Last 1)").Trim()
if ($registrationSha -notmatch '^[0-9a-fA-F]{64}$') { throw 'No se capturó registration_sha256; no declarar freeze auditable' }
```

El comando imprime la ruta del registro y su `registration_sha256`; el ejemplo guarda ambas salidas en un log nuevo. El archivo efectivo es `data/prospective-ledger/target_T.json`; si ya existe, el freeze debe fallar y nunca debe reemplazarse. Calcule también el SHA-256 del archivo publicado. Copie inmediatamente `$registrationSha`, el manifiesto con cierre oficial, el log y las capturas a un anclaje independiente con escritura restringida, retención inmutable/Object Lock o servicio equivalente con sello temporal. Mantenga control de acceso separado del usuario que genera el archivo y registre el recibo del almacenamiento.

El enlace duro (o el fallback atómico de Windows) evita reemplazo en la operación normal, pero un administrador con acceso al disco puede editar o borrar el archivo posteriormente. Un checksum guardado sólo junto al registro tampoco prueba autenticidad. La inmutabilidad frente a un administrador requiere el anclaje externo; no describa el filesystem local como WORM.

El registro actual contiene target, dos timestamps del host, commit, versión, `history_max`, hashes del histórico y ranking, gates y las 30 líneas. No incluye la URL/captura del cierre oficial, un sello independiente ni recibos de archivo externo: esos elementos deben quedar en el manifiesto externo vinculado por hashes.

## Evaluación después del sorteo

Espere a que el resultado del concurso objetivo aparezca en la página oficial de [resultados de Chispazo](https://comercializadores.pronosticos.gob.mx/Chispazo/Resultados). Verifique el número de concurso exacto, conserve la página/captura, hora de adquisición y SHA-256. No use la hora publicada ni la modalidad para deducir que un resultado corresponde al target.

Use el histórico y el ranking pre-sorteo originales, byte por byte: el evaluador comprueba sus hashes contra el registro autenticado. No le pase el histórico ya extendido con el resultado observado. Pase además el SHA del registro recuperado del anclaje externo. Cree una ruta nueva para cada intento de evaluación; `--out` existente se invalida al iniciar una ejecución, así que nunca reutilice una ruta que contenga un informe anterior.

```powershell
$evalId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd'T'HHmmssfff'Z'")
$evaluation = "$run/reports/evaluation_$evalId.json"
$evaluationLog = "$run/reports/evaluation_$evalId.log"
if ((Test-Path $evaluation) -or (Test-Path $evaluationLog)) { throw 'La ruta de evaluación ya existe; use otro identificador' }
$trustedRegistrationSha = '<SHA256_recuperado_del_anclaje_externo>'
$evaluationOutput = & python -m src.pipeline.evaluate_registration `
  --registration "data/prospective-ledger/target_${target}.json" `
  --history $history `
  --ranking $ranking `
  --trusted-registration-sha256 $trustedRegistrationSha `
  --result <N1> <N2> <N3> <N4> <N5> `
  --out $evaluation 2>&1
$evaluationExit = $LASTEXITCODE
$evaluationOutput | Set-Content $evaluationLog -Encoding utf8
if ($evaluationExit -ne 0) { throw 'Evaluación fallida; registrar incidente, sin informe válido' }
if (-not (Test-Path $evaluation)) { throw 'El proceso terminó sin crear el informe esperado' }
```

Archive el resultado sólo si el comando termina con exit code 0, verifique que el informe enlaza el target y SHA esperados, y anclelo junto con la fuente del resultado y un recibo temporal. No edite el registro. Evaluación fallida, checksum incorrecto o archivo ausente produce un incidente, no una evaluación válida. Una corrección posterior de la publicación oficial debe preservarse como nuevo evento y nueva evaluación, sin sobrescribir la anterior.

## Incidentes y conservación append-only

Use un identificador de intento único por target y operador. Por cada gate fallido, fuente ambigua, error de proceso, interrupción de escritura, evaluación fallida o corrección oficial, conserve:

- timestamp UTC/local, target, fase, operador, comando (sin secretos) y SHA del checkout;
- exit code, stdout/stderr íntegros, excepción/traceback y último artefacto válido;
- archivos temporales o parciales relevantes, hashes y estado de recuperación;
- decisión: `no_registration`, `registration_valid_but_evaluation_failed` u otra categoría definida antes del piloto;
- siguiente acción autorizada y vínculo al intento nuevo, si lo hay.

El log debe ser append-only y tener anclaje externo. No borre artefactos parciales ni sustituya informes previos; una salida posterior debe tener nuevo identificador. Un fallo antes de congelar nunca se representa como registro efectivo. Un fallo después de congelar no modifica ni invalida por sí mismo la predicción: se conserva el registro y se anota que la evaluación no pudo completarse.

Para evitar evaluación selectiva, el censo de targets programados debe incluir también concursos sin registro por gates cerrados, fuentes inciertas, cutoff vencido o fallas operativas. No filtre el denominador después de ver resultados.

## Plan científico que debe fijarse antes de iniciar la cohorte

El espacio de combinaciones de cinco números distintos de 1 a 28 tiene `C(28,5) = 98,280` resultados posibles. Bajo el nulo uniforme, una línea fija tiene probabilidad `1/98,280` de Exact5 y un portfolio de 30 líneas distintas tiene probabilidad `30/98,280` por sorteo de contener el resultado ganador. La página oficial describe el juego de selección 5-de-28; la igualdad de probabilidad y la independencia entre sorteos son supuestos estadísticos que deben contrastarse con el reglamento/mecanismo oficial, no inferirse de que el pipeline pase sus pruebas.

Antes de abrir la cohorte, un protocolo estadístico versionado y fechado debe predefinir:

- una sola versión/commit, parámetros, semillas/configuración y política para fallas; ninguna selección posterior de la mejor versión;
- una secuencia de concursos y horizonte calendario fijo, sin extenderla hasta que aparezcan suficientes aciertos; todo target programado queda en el censo;
- una métrica de cobertura operativa (`registros válidos / targets programados`) y una regla previa para el análisis condicional de cada portfolio registrado; los targets bloqueados no se cuentan como fallas Exact5, pero tampoco se ocultan ni se sustituyen por concursos elegidos después;
- todos los registros congelados entran en el conjunto de resultados; una falla del evaluador requiere recuperación/re-evaluación o un tratamiento de dato faltante predefinido, nunca la eliminación selectiva del target;
- un endpoint primario: indicador de al menos un Exact5 por portfolio completo de 30 líneas; coincidencias parciales, masa Top30 y métricas de ranking son descriptivas/secundarias;
- el contraste confirmatorio contra `p0=30/98,280` (por ejemplo, binomial unilateral exacto sólo si la independencia/uniformidad del nulo está justificada), alternativa de interés, nivel alfa, potencia/muestra planificada, multiplicidad y regla de parada;
- tratamiento de cambios del reglamento, correcciones oficiales, faltantes y cualquier desviación, con auditor independiente y acceso a datos fijados antes del análisis.

No se asigna aquí un tamaño de cohorte, alfa ni umbral de éxito: no existe aprobación previa para esos valores. Son bloqueos para iniciar una afirmación confirmatoria y no se deben escoger después de observar resultados. Los thresholds históricos del firewall (incluidos Holm y e-value) son gates de ingeniería/evidencia de esta versión; no sustituyen un plan confirmatorio prospectivo nuevo. Un único Exact5, hits parciales, cobertura estructural, simulaciones, archivos íntegros o un resultado con CI exitoso no prueban ventaja predictiva.

## Bloqueos actuales

1. V264 y el preflight permanecen en estado `RESEARCH_ONLY_NO_EDGE`/`BLOCKED`; no se puede congelar una predicción de producción hasta superar los gates en el código aprobado.
2. El histórico del checkout acaba en 12249 y el ledger efectivo está vacío. Falta un histórico actual construido y cotejado con evidencia oficial por concurso.
3. Falta documentar para cada target una fuente oficial que especifique el cierre de ventas de ese concurso y un mecanismo externo de timestamp/retención.
4. No hay un protocolo confirmatorio aprobado que fije horizonte, alfa, potencia/tamaño de muestra, multiplicidad, manejo de fallas y revisión independiente.
5. La herramienta `append_verified_result` actual escribe el CSV in-place y no es una transacción atómica junto con provenance; por eso la instrucción de usar únicamente copias únicas de staging y preservar fallas es obligatoria. Antes de automatizar una cohorte conviene implementar y probar una publicación versionada/transaccional.

Hasta resolver esos bloqueos, el objetivo es investigación y preparación de auditoría. No existe evidencia prospectiva real y completa que permita declarar ventaja predictiva.
