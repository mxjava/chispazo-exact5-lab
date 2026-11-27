# V265 — Actualización de evidencia física y operativa
**Corte: 27 de noviembre de 2026 · Chispazo Clásico electrónico**

## Avances nuevos

### 1. Corrección de CS-11: ya no existe la supuesta copia sin destinatario

La lectura completa de la actividad 13.6 de SGVO-PRO-05, página 17, enumera las tres copias: Inspector SEGOB, representante DTT y operador de Control de Datos. Con el original para SVO quedan identificados los cuatro ejemplares. Se corrigieron el mapa de fuente, el script, el JSON y las pruebas del hallazgo del 26 de noviembre.

Lo que sigue faltando son constancias reales de entrega/recepción por concurso. El procedimiento no demuestra que cada ejemplar haya sido recibido en cada sorteo.

### 2. RFID: infraestructura acreditada históricamente; trazabilidad física no publicada

El Informe de Gestión Gubernamental 2018–2024 afirma que las 14 máquinas entregadas en marzo de 2022 y las esferas contaban con RFID. Pero el mismo informe declara diez juegos por cada uno de siete productos y reporta un total de 60 juegos; 10 × 7 daría 70. Se conserva la discrepancia, sin corregirla por inferencia.

El informe también indica que la adquisición de ocho máquinas adicionales y dos sistemas RFID, así como cuatro balanzas de precisión, no fue autorizada al cierre de junio de 2024. Esto no demuestra el inventario actual ni que no existieran equipos alternos; sólo impide asumir que esas compras propuestas se ejecutaron.

No se obtuvo el catálogo RFID tag → máquina/estuche/esfera → número, ni eventos de lectura por concurso, ni hora de carga/extracción. Por ello, la mención histórica de RFID no equivale a datos utilizables por V265.

### 3. Mantenimiento de máquinas: contrato histórico 058-2024

El informe oficial registra el contrato 058-2024 de mantenimiento preventivo y correctivo de 21 máquinas, controles y consolas de operación de ocho productos, incluyendo Chispazo. Señala que concluyó dentro del periodo reportado al 30 de junio de 2024.

El resumen no publica seriales por máquina, órdenes de trabajo, fechas/horas de intervención, componentes sustituidos, calibraciones, pruebas de aceptación ni relación con concursos individuales. Es evidencia de contratación histórica, no un registro físico por sorteo.

### 4. Nuevo documento 2026: invitación 222-2026, pero su alcance no es la máquina de sorteo

Lotería Nacional publicó la invitación IA-06-HJY-006HJY001-N-222-2026 para mantenimiento de equipos eléctricos de inmuebles. La convocatoria se aprobó el 20-oct-2026, se publicó el 29-oct y programó fallo para el 10-nov. El alcance incluye plantas de emergencia, UPS, subestación/transformador, bancos de capacitores, pararrayos, tableros y sistemas solares.

El anexo técnico exige reportes con identificación/serie del equipo, fecha y horas de inicio/fin, causa de falla, refacciones, mediciones eléctricas antes/después, fotografías y firmas, con entrega dentro de tres días hábiles del servicio. Es una fuente potencial de contexto de continuidad eléctrica, no mantenimiento de máquinas de extracción, esferas o básculas.

El PDF es una invitación: por sí solo no acredita adjudicación ni ejecución. No se recuperaron acta de fallo, contrato firmado ni reportes de servicio.

### 5. Custodia y responsabilidades

El Manual SAF-MAN-12 de febrero de 2026, tipo público, asigna a la Subgerencia de Operación de Concursos, Juegos y Sorteos Electrónicos e Instantáneos funciones de supervisión de mantenimiento, control de incidencias y resguardo de actas, videos y registros operativos. Es el área organizacional más directamente relacionada para solicitar expedientes originales. No se obtuvo ningún registro por concurso.

### 6. Evaluador V265: límite confirmado en el código

El evaluador exige seis campos: CONCURSO, sphere_set_id, machine_id, available_before_close, close_time_local y metadata_known_time_local. Los dos identificadores son etiquetas proporcionadas al evaluador; el validador comprueba cronología declarada, pero no autentica procedencia.

No consume pesos individuales, mapeo RFID esfera-número, orden de extracción ni timestamps por extracción. source_provenance_required es falso. El guard mantiene physical_bias_evidence=false y actionable_for_betting=false; tampoco implementa anytime e-value. research_edge es una pantalla de asociación con un posible filtro Holm, no una conclusión de sesgo físico.

## Matriz de prospectividad

| Dato | Momento | Estado |
|---|---|---|
| CS-02 y estado de máquina | Pre-cierre | Candidato condicional, sin originales autenticados |
| Identificador de máquina/estuche y lectura RFID | Podría ser pre-cierre | Sin mapeo ni log de lectura por concurso |
| Peso individual por esfera | Después del cierre SICAL, antes de cargar | No es pre-cierre para el mismo concurso |
| Orden y tiempo de cada extracción | No especificados en campos públicos recuperados | Ausente |
| CS-11 y resultado | Post-extracción | Retrospectivo |
| Firma de participaciones/cancelaciones | Post-cierre, pre-sorteo | No pre-cierre |
| Video desde pesaje hasta sorteo | Durante y después del cierre | No pre-cierre |
| Calendario de mantenimiento | Puede conocerse antes | Contexto potencial, si está ligado a activo y fecha |
| Reporte real de mantenimiento/eléctrico | Después de servicio | No se presume disponible antes del cierre |
| Certificado de calibración | Depende de fecha y recepción | No se obtuvo; no se afirma frecuencia anual |
| MJF diario | Después de 21:00 | No pre-cierre |

## Reproducibilidad, pruebas y hashes

- Script nuevo: scripts/audit_v265_physical_operational_delta.py
- Pruebas nuevas: tests/test_v265_physical_operational_delta.py
- Salida estructurada: reports/V265_PHYSICAL_OPERATIONAL_DELTA_20261127.json
- El script lee la transcripción controlada y el código V265; no descarga PDFs, no lee resultados, no genera registros y no ejecuta pruebas estadísticas.
- La auditoría anterior de semántica V265 se hizo portable entre Python 3.11 y 3.12 usando AST canónico, corrigiendo dos fallos de CI por diferencias de paréntesis de ast.unparse.
- No se capturaron bytes de los PDF oficiales en el entorno, por lo que no se inventa SHA-256 de fuentes. Los SHA-256 de los artefactos del repositorio se reportan después de su confirmación en GitHub.

## Bloqueo real

No se encontraron originales por concurso: CS-02 firmado, Tira de Pesaje, identificadores RFID y su mapeo, logs de carga/extracción, timestamps, CS-11 firmado y recibos de sus cuatro ejemplares, video original, órdenes de mantenimiento, certificados de calibración, registros de incidencias, firmas de participación ni MJF. Sin estos datos no existe base para estimar sesgo físico.

## Dictamen

**Evidencia de mecanismo y operación, no ventaja predictiva.** No se ejecutaron análisis de frecuencia, pares, tríos, transiciones ni pruebas sobre resultados. OOS, multiplicidad y anytime e-value no están superados. V294 sigue congelado; el histórico canónico permanece intacto; no se escribe en main ni se promueve la rama.
