# V265 — Reconciliación documental de evidencia física y cronología (2026-11-23)

## Hallazgo nuevo

Se localizó una copia pública adicional de **SGM-PRO-06, Preparación de Sorteos, revisión 22, DN-07 v05**, bajo la ruta SUSTANTIVAS/VIGENTES. Sin embargo, **no aparece en la lista oficial actual de Normas Sustantivas Vigentes**, que sí enumera SGVO-PRO-05, actualizado el 20-03-2026. La revisión 22 de SGM-PRO-06 registra como último cambio junio de 2017. Su aplicabilidad vigente no queda acreditada sólo por la ruta del PDF.

Esto corrige una conclusión anterior incompleta: existe una copia pública rev.22 fuera de PROYECTO. No debe confundirse con el borrador rev.21 en PROYECTO ni con SGVO-MAN-02, que sigue apareciendo como proyecto normativo. SGM-PRO-06 y SGVO-MAN-02 son documentos distintos.

## Campos nuevos que describe SGM-PRO-06, si se confirma su aplicabilidad

- **CS-02:** fecha; revisión de compresor, consola, alimentador, turbina, trampas de selección, cápsula de mezclado, puerta, exhibidor, báscula e impresora; impresión de fecha/hora; número de sorteo, hora de inspección, firmas y observaciones de anomalías.
- **Tira de Pesaje:** 28 esferas de Chispazo, pesadas una por una en orden numérico; impresión individual de peso; número de objetos, promedio, máximo, mínimo y diferencia máximo-mínimo; impresión de fecha/hora al inicio y al final; rúbricas del operador, Inspector SEGOB, Subdirección de Concursos y Sorteos y Dirección General.
- **Identificación operativa:** Chispazo figura con esferas amarillas o azules según la máquina usada.
- **Horario previsto:** el anexo dice que el pesaje se hará preferentemente antes del cierre de ventas de las 21:15; la política 3 programa la cita nocturna a las 20:40 o 20:50 según el día.

La Tira descrita ofrece timestamps de inicio y fin del conjunto, no un timestamp por esfera ni un orden de extracción. El orden numérico de pesaje no es el orden de extracción. Tampoco queda confirmado que cada línea de peso imprima el número de esfera o un RFID.

## Contradicciones que bloquean el uso prospectivo

| Tema | SGVO-PRO-05 rev.39, indexado vigente | SGM-PRO-06 rev.22, copia pública no indexada | Dictamen |
|---|---|---|---|
| Cierre nocturno | 21:00 | 21:15 en el anexo de Chispazo | No reconciliado |
| Pesaje | Después de verificar SICAL Cerrado | Preferentemente antes del cierre | No clasificar pesos del mismo concurso como pre-cierre |
| Peso Ping Pong | 2.30–3.00 g; dispersión máxima 0.15 g | 2.20–2.90 g; dispersión máxima 0.15 g | Límites distintos |
| Peso Smartballs | 4.25–5.25 g; dispersión máxima 0.30 g | Rango genérico 2.20–2.90 g | No equivalente |
| Estuche rechazado | Sustituye y regresa a actividad 4.1 | Sustituye y vuelve a pesar | No inferir reapertura de ventas |

La página oficial de Chispazo publica el Clásico a las 21:00. SGVO-PRO-05 también fija el cierre nocturno a las 21:00. El 21:15 de SGM-PRO-06 es un indicio de una versión u operación anterior, no una hora aplicable al presente sin confirmación.

SGVO-PRO-05 contiene un error de referencia cruzada: actividad 5.2 y punto 2 del Plan de Calidad remiten a Política 8 para pesos, pero Política 8 trata de la firma electrónica del archivo de participaciones. Los rangos están en Política 6.

El Reglamento Chispazo, artículo 9, describe introducir 28 esferas en la urna antes del cierre, generar y resguardar la firma electrónica del archivo de participaciones y después extraer cinco esferas. SGVO-PRO-05 describe cierre SICAL, pesaje y posterior colocación en alimentadores. No se puede resolver por inferencia si urna y alimentadores son etapas distintas; se requiere aclaración escrita del orden físico y de los timestamps reales.

## Uso prospectivo

- **CS-02 y estado del equipo:** candidato si el original firmado, número de máquina/báscula y timestamp de disponibilidad preceden al cierre definitivo.
- **Máquina y estuche:** condicional a ID de activo, asignación por concurso, historial de sustituciones y hora de fijación del estuche final.
- **Pesos:** bloqueados para el mismo concurso hasta confirmar el procedimiento que gobierna y obtener la Tira original con hora de inicio/fin. Si la Tira fue generada antes del cierre definitivo y estaba disponible antes de éste, podría evaluarse; si fue posterior, sólo sería retrospectiva para ese concurso. Un uso rezagado en el siguiente requiere probar que el mismo estuche siguió asignado.
- **RFID:** el informe institucional 2018–2024 confirma reconocimiento RFID en máquinas y esferas, pero no aporta tags, mapeo RFID-número, lecturas de antena ni asignación por concurso. Declara 10 juegos para cada uno de siete productos, pero total 60; no corregimos por inferencia.
- **CS-11, Acta, video de extracción e incidencias:** registros de resultado/evento, no predictores pre-cierre del mismo sorteo.
- **Firma electrónica de participaciones/cancelaciones:** control de integridad del archivo de ventas generado después del cierre; no es medición física.

## Modalidades

La página oficial clasifica Chispazo como electrónico y separa los Tradicionales. El Reglamento de Sorteos Tradicionales de 2026 describe bolas de madera y esferas mecánicas para productos tradicionales. Esas especificaciones no se trasladan a Chispazo, que tiene su propio Reglamento, 28 esferas numeradas y extracción de cinco.

## V265

No se modificó el algoritmo V265. Su contrato actual sigue sin consumir los 28 pesos, mapeo RFID por esfera, orden de extracción, timestamps individuales ni procedencia documental obligatoria. Holm es opcional y no existe gate anytime e-value. V265 sigue siendo ASSOCIATION_SCREEN_ONLY; physical_bias_evidence=false.

## Datos, pruebas y bloqueos

- Datos nuevos: campos y secuencia descritos por la copia pública SGM-PRO-06 rev.22; especificaciones y cronología contrastadas con SGVO-PRO-05 rev.39, Reglamento Chispazo, página oficial y Reglamento Tradicional 2026.
- Registros por concurso obtenidos: ninguno. No se obtuvieron CS-02, Tira, CS-11, RFID logs, calibraciones, órdenes de mantenimiento, CS-09/12/18 ni video máster.
- Análisis: comparación determinista de documentos públicos; sin frecuencias, pares, tríos, transiciones ni pruebas sobre resultados.
- No se obtuvieron binarios de los PDF en el entorno; no se reclaman SHA-256 de los PDF originales.
- V294 congelado; histórico canónico sin cambios; main sin escrituras; sin merge ni promoción.

### Fuentes oficiales

1. [SGVO-PRO-05 rev.39](https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf)
2. [SGM-PRO-06 rev.22 — copia pública no listada en el índice actual](https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgm_p0_6.pdf)
3. [Normateca — Normas Sustantivas Vigentes](https://loterianacional.gob.mx/Normateca/Sustantivas?id=2)
4. [Normateca — Proyectos Normativos](https://loterianacional.gob.mx/Normateca/Proyectos?id=0)
5. [Chispazo — horarios y clasificación](https://loterianacional.gob.mx/Chispazo/Chispazo)
6. [Reglamento Chispazo](https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/Reglamento-Chispazo.pdf)
7. [Reglamento de Sorteos Tradicionales 2026, SIDOF/SEGOB](https://sidof.segob.gob.mx/notas/docFuente/5777789)
8. [Informe de Gestión Gubernamental 2018–2024, p. 43](https://www.loterianacional.gob.mx/Documentos/Transparencia/InformacionSocialmenteUtil/Informe_Consolidado.pdf)
