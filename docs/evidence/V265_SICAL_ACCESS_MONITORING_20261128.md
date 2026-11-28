# V265 — SICAL, control de acceso y monitoreo operativo
**Corte: 28 de noviembre de 2026 · Chispazo Clásico electrónico**

## Fuentes públicas vigentes y alcance

La Normateca de Lotería Nacional lista como sustantivas vigentes: SGVO-PRO-05 (Sorteos Electrónicos, actualización 20-03-2026), SGAF-INT-48 (Instructivo SICAL, actualización 27-03-2026), SGAF-PRO-47 (Monitoreo SICAL, actualización 23-03-2026) y SGAF-PRO-95 (Control de Accesos a Áreas Restringidas, actualización 27-03-2026). En la misma lista, SGVO-PRO-08, SGVO-PRO-34 y SGVO-PRO-15 están identificados expresamente como procedimientos de sorteos tradicionales; no se usan para describir Chispazo electrónico.

Fuentes:
- Normateca vigente: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- SGAF-PRO-95: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgaf_pro_95.pdf
- SGAF-INT-48: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgaf_int_48.pdf
- SGAF-PRO-47: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgaf_pro_47.pdf
- SGVO-PRO-05: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

## 1. SGAF-PRO-95 — acceso físico a áreas restringidas

El alcance incluye expresamente áreas restringidas de la Gerencia de Sorteos. La política exige que el registro de ingreso y egreso de visitantes incluya: hora de entrada, nombre completo, persona visitada, objeto de la visita, entidad/dependencia/empresa, hora de salida, firma del visitante y visto bueno de la persona visitada. También establece que las tarjetas/códigos de acceso son personales e intransferibles.

El flujo de autorización incluye solicitud por oficio, análisis y autorización del área, configuración de lectores por Seguridad Informática y entrega de código con acuse firmado. Es un control complementario al CS-12 de SGVO-PRO-05: CS-12 registra participantes durante el evento; SGAF-PRO-95 cubre permisos, visitantes y accesos a áreas restringidas; las bitácoras de limpieza/mantenimiento se rigen además por SGVO-PRO-05.

La Normateca lista última actualización 27-03-2026 y el control de cambios del PDF marca revisión 01, marzo de 2026. El sello de publicación de portada parece indicar 27 MAR 2025; se requiere confirmación oficial de la fecha efectiva porque no coincide visualmente con el control de cambios ni con la Normateca.

**Variables y prospectividad:** autorización, código/tarjeta, identidad/rol, área, motivo y horas de entrada/salida. Una autorización vigente puede existir antes del cierre; el registro de entrada/salida es contemporáneo o posterior. Sólo un log original con reloj sincronizado, identidad de activo/puerta y timestamp autenticado permitiría saber quién tuvo acceso antes del cierre. No es predictor de números.

## 2. SGAF-INT-48 — archivos SICAL y MD5

El instructivo, revisión 08 (marzo de 2026), establece que después del cierre automático se integran los archivos de concursos activos a servidores de Lotería Nacional y se verifican contra el reporte diario de ventas. Para sorteos de 13:00, 15:00, 17:00 y 19:00 se copian archivos de venta con su firma MD5 del servidor de producción al servidor de contingencia para cargar/verificar ventas y seleccionar ganadores. Para el sorteo de las 21:00, el procedimiento indica que esa copia al servidor de contingencia se realiza al día siguiente.

El MD5 es un digest de integridad de archivo; no debe llamarse firma electrónica ni confundirse con la firma de participaciones/cancelaciones resguardada por SGVO-PRO-05. La copia del concurso de 21:00 es explícitamente posterior al sorteo: sirve a integridad/reproceso administrativo, no a una predicción pre-cierre ni a una explicación física de la extracción.

El instructivo también exige autorización para altas/bajas/cambios de usuarios SICAL (formato STO-18), revisión de usuarios activos y atención de incidentes de cuenta. STO-18 no es CS-18: son formatos distintos y con finalidades distintas.

**Variables y prospectividad:** archivo de ventas, MD5, servidor origen/destino, fecha/hora de cierre, copia, carga, verificación y selección de ganadores; cuentas/roles/permisos SICAL. Los hashes y la copia de contingencia para Clásico son post-cierre y, para 21:00, del día siguiente. Las autorizaciones de usuario pueden ser previas, pero no predicen los números.

## 3. SGAF-PRO-47 — monitoreo de operación SICAL

El procedimiento de monitoreo (revisión 17; Normateca actualizada 23-03-2026) cubre sistemas de captación de apuestas en línea para concursos y sorteos electrónicos. La aplicación SICAL muestra en tiempo real transacciones de ventas, cancelaciones y validaciones; otras herramientas muestran estado de sistemas primario/secundario/alterno y comunicaciones.

Registros definidos:
- CA-01, Registro Diario de Ventas: revisión horaria de 08:00 a 21:00 de transacciones, cancelaciones y pagos.
- CA-02, Registro Diario de Comunicaciones: monitoreo cada media hora de 08:00 a 21:00 de estado UP/DOWN/DISCONNECTED.
- CA-04, Incidencias del Sistema: se registra después de que el incidente se soluciona y cuando la información fue validada/revisada; puede incluir evidencia electrónica/impresa y detalle de terminales, y se integra en CD para validación.
- CA-05, Mantenimientos Correctivos a Terminales: retrasos de atención de fallas de terminales físicas.
- CA-06, Informe de Interfaces: archivos con datos incorrectos o recibidos fuera del tiempo de tolerancia.
- La supervisión de interfaces incluye MJF, archivos técnicos, comunicaciones y logs del sistema.

Los incidentes de SICAL se refieren al registro de apuestas y su infraestructura: pérdida parcial de ventas, interfaces incorrectas/tardías, inoperatividad del sistema primario y demoras de mantenimiento de terminales. No son incidencias de la máquina de extracción, estuches ni esferas. El registro CA-04 puede ser posterior a la resolución; no usar su fecha de captura como inicio del incidente.

**Variables y prospectividad:** actividad de ventas, cancelaciones, validaciones, disponibilidad del sistema, red, interfaces, MJF, incidentes y mantenimiento de terminales. Los estados en tiempo real y CA-01/CA-02 pueden ser operativamente conocidos antes o al cierre si se preservan logs con timestamp; CA-04, CA-05, CA-06 y CDs de evidencia pueden generarse después. Para Clásico, el intervalo de monitoreo termina a las 21:00, coincidente con el cierre normal, por lo que no se presume que un reporte formal estuviera disponible antes del corte.

## 4. Vínculo con SGVO-PRO-05 y evaluación V265

SGVO-PRO-05 continúa siendo el procedimiento específico del sorteo electrónico. Sus CS-12, CS-09 y CS-18 no se sustituyen por CA-01/02/04/05/06 ni por STO-18. Los registros SICAL describen la captación de apuestas y su continuidad operativa, no la identidad/peso/orden de extracción de esferas.

V265 sigue consumiendo sólo machine_id, sphere_set_id, available_before_close, close_time_local y metadata_known_time_local. No autentica registros de acceso, SICAL, MD5, CA-01/02/04/05/06, ni consume pesos individuales, RFID esfera-número, orden de extracción o timestamps por extracción. Su guard mantiene physical_bias_evidence=false y actionable_for_betting=false.

## 5. Bloqueos y siguiente evidencia

No se obtuvieron registros reales por concurso de CS-12/bitácoras de acceso, permisos de puerta, CA-01/02, CA-04/05/06, logs de SICAL, hashes MD5 de archivos de venta, transferencias producción→contingencia, CD de incidentes ni archivos MJF. Los procedimientos prueban qué registros deberían existir y sus tiempos, no su ejecución en un concurso concreto.

La solicitud V8 pide estos documentos con timestamps, sistemas origen/destino, hashes, identidad de activos/usuarios y cadena de custodia, además de que se declare si algún registro no se genera, no existe, fue destruido o está bajo otra unidad.

Clasificación: DOCUMENTED_MECHANISM_ONLY. Sin datos físicos primarios por concurso y sin los gates OOS, multiplicidad y anytime e-value, no hay evidencia de sesgo ni ventaja predictiva.
