# Línea de evidencia física — delta de auditoría 2026-11-20

**Corte:** 2026-11-20  
**Clasificación:** `BLOCKED_PROVENANCE`  
**Resultado científico:** evidencia de mecanismo y de secuencia operativa; **ninguna evidencia de sesgo ni de ventaja predictiva**.

Este delta añade sólo hallazgos nuevos respecto de la auditoría física del 2026-11-19. No vuelve a ejecutar análisis de frecuencias, pares, tríos ni transiciones. No modifica V294 ni el histórico canónico.

## 1. Separación normativa verificada en la Normateca vigente

La página oficial de Normas Sustantivas Vigentes, consultada el 2026-11-20, separa explícitamente las normas:

- **Electrónico:** SGVO-PRO-05, “Procedimiento Sorteos Electrónicos”, actualización 20-03-2026.
- **Tradicional:** SGVO-PRO-08, “Mantenimiento mayor y menor del equipo e instrumentos de sorteos tradicionales”, actualización 20-03-2026.
- **Tradicional:** SGVO-PRO-15, “Preparación y celebración del sorteo tradicional”, actualización 18-03-2026.
- **Tradicional:** SGVO-PRO-34, verificación de peso/diámetro de bolas de madera y operación de ábacos, actualización 20-03-2026.

La existencia de estos procedimientos tradicionales no autoriza a importar sus bolas de madera, ábacos, pesajes, secuencias o criterios de mantenimiento a Chispazo. La línea física de Chispazo debe mantenerse bajo SGVO-PRO-05 y el Reglamento Chispazo, no bajo SGVO-PRO-08/15/34.

Fuentes oficiales:
- Normateca: https://loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGVO-PRO-05 rev. 39: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- SGVO-PRO-08 (tradicional): https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_08.pdf
- SGVO-PRO-15 (tradicional): https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_15.pdf
- SGVO-PRO-34 (tradicional): https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_34.pdf

## 2. Corrección temporal importante: el pesaje no sirve para el mismo sorteo, pero puede ser candidato para uno posterior

La lectura conjunta de las actividades 2 a 6 de SGVO-PRO-05 rev. 39 establece:

1. **Antes del sorteo:** se revisa el equipo y se llena CS-02. El Plan de Calidad exige la inspección antes de cada sorteo.
2. **Antes del cierre:** se confirma con SEGOB y Dirección General que el número de sorteo y los estuches a utilizar correspondan al sorteo.
3. **Cierre automático:** TI muestra en SICAL el estado “Cerrado” y comprueba fecha, hora, número de sorteo y ventas. El Sumario de Cierre se imprime y rubrica.
4. **Después del cierre:** actividad 5.1 pesa cada esfera individualmente y en orden numérico.
5. **Rechazo:** si los pesos no cumplen, se cambia el estuche y el procedimiento vuelve a la actividad 4.1. Por ello, el estuche final puede diferir del inicialmente confirmado antes del cierre.
6. **Aceptación/carga:** la tira se firma y recibe rúbricas de Operaciones, SEGOB y Dirección General; se anexa al Acta. Las esferas se colocan en los alimentadores en orden progresivo.
7. **Extracción:** la máquina mezcla y captura las esferas; CS-11 se llena después de la captura y cotejo de los números.

La hora de cierre nocturno prevista en el procedimiento es 21:00, salvo modificación autorizada. El portal oficial publica Chispazo Clásico a las 21:00.

### Consecuencia estadística

- La masa medida después del cierre de un concurso **no puede usarse para predecir ese mismo concurso**.
- No debe descartarse automáticamente como registro histórico ni como posible covariable de un sorteo posterior.
- Puede ser candidata para un concurso posterior únicamente si, antes del cierre de ese concurso objetivo, se acredita que el archivo fuente ya estaba disponible y bajo custodia verificable, y que el mismo estuche, máquina y mapeo esfera↔número permanecieron sin cambios hasta el sorteo objetivo.
- Una sustitución, remapeo, mantenimiento, re-pesaje o cambio de posición no documentado rompe la continuidad y bloquea la elegibilidad.

Esta distinción source-draw/target-draw ya está contemplada en `physical_intake_v2.py`. Sus pruebas incluyen expresamente `test_measurement_after_source_close_can_be_eligible_for_later_target` y `test_measurement_before_close_but_receipt_after_target_close_is_ineligible`. No se afirma que el escenario sintético de esas pruebas haya ocurrido en un sorteo real.

Fuentes:
- SGVO-PRO-05, actividades 3.1, 4.1, 5.1–5.6 y 11–13: PDF oficial anterior.
- Página oficial Chispazo: https://loterianacional.gob.mx/Chispazo/Chispazo

## 3. RFID: mecanismo acreditado, trazas de uso no publicadas

El Informe de Gestión Gubernamental 2018–2024 acredita:
- Entrega el 07-03-2022 de 14 máquinas electrónicas: 10 Júpiter, 2 Mercury 5 y 2 Mercury 8.
- Instalación y puesta en marcha entre el 08 y 10-03-2022.
- Reconocimiento RFID en máquinas y esferas.
- Smartplay International Inc. como proveedor de máquinas, esferas y accesorios.
- Diez juegos de esferas por producto para la lista de siete productos que incluye Chispazo, pero el mismo informe suma 60 juegos. La multiplicación 10 × 7 = 70; la inconsistencia se conserva como conflicto documental y no se corrige por conjetura.
- Proyecto de 8 máquinas, 2 sistemas RFID, 4 básculas y 4 impresoras no autorizado al cierre de junio de 2024.
- Contrato 058-2024 de mantenimiento preventivo/correctivo de 21 máquinas y controles/consolas, que incluía Chispazo y que el informe registra como concluido dentro del periodo.

Esto demuestra que el sistema RFID formó parte del mecanismo adquirido. **No** publica el ID RFID de cada esfera, ID de lector/antena, lecturas por concurso, versión del mapeo RFID-número, hora de lectura, eventos de sustitución ni la asociación de cada lectura con el estuche final. El contrato de 2024 no es un historial de órdenes de trabajo por máquina/serie y no prueba el estado actual de una máquina concreta.

Fuente oficial:
https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf

## 4. Brechas nuevas identificadas en el contrato V2 de ingestión

El esquema V2 ya separa:
- sorteo de origen y sorteo objetivo;
- hora de cierre del origen y del objetivo;
- asignación del estuche, medición, firma del documento y disponibilidad/custodia;
- 28 esferas, IDs físicos, números impresos, masas, resolución, báscula y vigencia de calibración;
- referencias/hash de documento, firma, recibo de custodia y sello de tiempo.

Pero el contrato actual **todavía no captura como eventos obligatorios**:

1. `rfid_tag_id`, `rfid_reader_id`, antena/puerto, `rfid_event_id`, resultado bruto de lectura, hora del lector y versión del catálogo tag↔activo.
2. ID RFID de la máquina y del estuche, separados de los nombres/IDs operativos ingresados manualmente.
3. `feeder_id`, posición del alimentador y secuencia real de carga por esfera.
4. Secuencia de mezcla/captura y `extraction_order` por esfera, con timestamp y referencia a fotograma/timecode.
5. Identidad de cámara, archivo maestro de video, SHA-256, inicio/fin, zona horaria, deriva del reloj y correspondencia entre el video original y el segmento editado anexo al Acta.
6. Eventos explícitos de reemplazo, remapeo, limpieza, mantenimiento, calibración, re-pesaje, incidencia y acceso, con activo afectado, actor por rol, timestamp, documento fuente y hashes.

### Diseño V3 recomendado

Mantener una tabla de **activos** (máquina, estuche, esfera física, tag RFID, número impreso y vigencia del mapeo) separada de un **ledger de eventos inmutable** (asignación, lectura RFID, pesaje, aceptación/rechazo, sustitución, carga, extracción, mantenimiento, incidencia, video y custodia). Cada evento debe incluir concurso/modalidad, asset ID, event type, timestamp con zona, fuente de reloj, actor por rol, secuencia, referencia documental y SHA-256. La elegibilidad para un target se calcula reconstruyendo el estado de activos y mapeos en todo el intervalo; no se infiere del último registro ni de un campo booleano.

Este diseño es una especificación de ingestión pendiente, no datos ni una afirmación de que Lotería mantenga todos esos campos.

## 5. V265 endurecido: régimen proxy, nunca sesgo físico

El código original de V265 consume `sphere_set_id`, `machine_id`, `available_before_close`, `close_time_local` y `metadata_known_time_local`. No consume masas por esfera, IDs físicos, mapeo físico-número, lecturas RFID, orden de carga/extracción, documentos originales ni una cadena independiente de reloj/custodia.

El cálculo anterior podía establecer `actionable_for_betting=true` con una asociación de régimen, 100 observaciones, media positiva y p-valor Holm, sin exigir el Exact5 anytime e-value ni dos salidas selladas con custodia independiente. Eso era un defecto de guardrail, no evidencia de sesgo.

Se endureció el evaluador sin cambiar el cálculo del score de régimen:
- el resultado ahora se etiqueta `proxy_association`;
- `research_edge=false`;
- `physical_bias_evidence=false`;
- `physical_measurements_consumed=false`;
- `physical_identity_mapping_verified=false`;
- `rfid_event_log_consumed=false`;
- `extraction_order_consumed=false`;
- `actionable_for_betting=false`;
- `promotion_eligible=false`;
- se reportan bloqueos explícitos para masas, IDs, mapeo, RFID, orden, custodia, timestamps, anytime e-value y dos salidas selladas.

El parche no convierte los proxies existentes en datos físicos ni reabre sus resultados estadísticos. La salida de V265 queda clasificada `RESEARCH_ONLY_REGIME_PROXY_NOT_PHYSICAL_EVIDENCE`.

## 6. Validación ejecutada y alcance

En el head `c23121026ebb57bb01e9975d0b2783868151f46e), antes del parche V265:
- ORIGEN aislado: [run 44658161548](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44658161548), 220 pruebas pasadas, incluidas 26 pruebas de ingestión física V2.
- CI raíz: [run 44658161569](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44658161569), exitosa.

Los fixtures de ingestión son sintéticos. Las pruebas validan reglas y fail-closed; no acreditan pesajes, RFID ni sesgo en concursos reales.

Después del parche V265 se agregaron tres pruebas de guardrail para demostrar que incluso una asociación de régimen positiva nunca puede marcar sesgo físico, apuesta o promoción. Los workflows disparados por el nuevo commit se deben considerar pendientes hasta revisar sus conclusiones finales.

## 7. Estado de datos auténticos y decisión

Datos públicos auténticos obtenidos para esta actualización: normas vigentes de la Normateca, SGVO-PRO-05 rev. 39 y el Informe de Gestión Gubernamental 2018–2024. Estos documentos describen mecanismos, responsables, controles y límites; no incluyen un dataset por concurso con las 28 masas, mapeo físico-número, eventos RFID, secuencia de carga/extracción, calibración individual y timestamps verificables.

En el repositorio, las plantillas físicas siguen siendo encabezados/esquemas; no hay registros primarios recibidos. No se ejecutó un modelo de masa ni se produjo un ranking físico.

**Clasificación final:**
- Existencia de controles/procedimientos y hardware RFID: `MECHANISM_EVIDENCE`.
- Trazabilidad física por concurso: `BLOCKED_PROVENANCE`.
- Sesgo físico o ventaja prospectiva: **no demostrados**.
- Promoción: bloqueada hasta evidencia primaria completa, al menos 100 sorteos Clásico OOS intactos, lift prequential positivo preregistrado, Holm p < 0.05, Exact5 anytime e-value ≥20 y dos salidas pre-cierre selladas con custodio independiente.

## 8. Integridad protegida

- Rama de investigación: `research/origen-v0.3-engine-20261118`.
- `main` permanece en `424eee9dd906f8235541e97ae61026441083bbfe`; no se escribió en main.
- Histórico canónico: 505,274 bytes; Git blob SHA-1 `2f5ff5bfbd779fe505736398e417b7211955958e`; SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- V294 sigue congelado.
- PR #8 sigue abierto, draft y sin merge.
- No se descargaron los PDF binarios oficiales en este entorno; por tanto no se inventa SHA-256 de esos archivos. Se conservan URL, nombre, revisión/fecha de Normateca y las referencias de contenido citadas.
