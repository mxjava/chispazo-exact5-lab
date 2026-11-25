# Solicitud técnica de información — trazabilidad física Chispazo (v2)

Fecha de preparación: 2026-11-19  
Estado: BORRADOR PARA PRESENTAR; no enviada por el laboratorio.

## Objetivo

Obtener registros primarios que permitan comprobar o descartar si características físicas medidas antes del cierre (en particular masa individual de esferas) tienen asociación reproducible con la extracción de números de Chispazo. Esta solicitud no presupone sesgo ni solicita datos personales.

## Alcance recomendado

Solicitar desde el 25 de septiembre de 2017 hasta la fecha de respuesta, para ambas modalidades (Chispazo de las Tres y Clásico), identificando inequívocamente cada concurso. Si el volumen impide entregar todo, pedir primero el periodo más reciente disponible y que la institución informe el universo documental, formatos, plazos de conservación y costo de reproducción.

## Registros y campos solicitados

### A. Identidad y trazabilidad del sorteo
- Concurso, fecha, hora programada y hora efectiva, modalidad.
- Identificador del acta y del expediente/documento que contiene la tira de pesaje.
- Identificador de estuche/juego de esferas, tipo de esfera, máquina, modelo y número de serie (si se registra).
- Identificador físico individual de cada esfera y correspondencia exacta con el número impreso 1–28.
- Posición/orden de carga en alimentador y cualquier cambio de posición.
- Registro de selección del estuche y máquina: método, responsable por rol, fecha/hora en que quedó asignado y si esa asignación fue anterior al cierre de ventas.

### B. Medición metrológica
- Peso individual de cada una de las 28 esferas, valor original, unidad, resolución/precisión y cualquier redondeo.
- Peso mínimo, máximo, rango y resultado de aceptación/rechazo.
- Marca/modelo/identificador de báscula, fecha de calibración, certificado vigente, tolerancia e incertidumbre declarada.
- Fecha/hora de medición, repeticiones, mediciones descartadas y motivo.
- Tira de pesaje completa y anexos asociados al concurso.

### C. Cambios, incidencias y controles
- Rechazo de estuche, nueva selección, re-pesaje y motivo.
- Sustitución de esfera, estuche, máquina o componente; fecha/hora y correspondencia antes/después.
- Incidencias, mantenimiento, limpieza, almacenamiento, transporte, manipulación o anomalías asentadas.
- Registros RFID u otro control de identidad, únicamente si forman parte del expediente.
- Video o evidencia documental de identificación, carga y extracción, si existe y se conserva.

### D. Integridad y disponibilidad
- Copia digital legible de acta, tira de pesaje, formato CS-11 y anexos, vinculados por concurso.
- Catálogo de campos y formatos; diccionario de datos si existe.
- Confirmación expresa de qué campos no se generan, no obran en poder de la institución o fueron dados de baja; fundamento y plazo de conservación aplicable.
- Si hay versiones públicas, entregar versión pública con datos personales testados, preservando fechas, roles, identificadores técnicos y trazabilidad.

## Formato preferido

CSV/XLSX para datos tabulares y PDF nativo o escaneo legible para actas y tiras. No solicitar nombres, firmas autógrafas, domicilios ni datos personales de servidores públicos; basta rol institucional, sello/folio, fecha y evidencia de validación.

## Preguntas críticas que deben contestarse

1. ¿Las esferas tienen identificador físico único que permite enlazar su masa con el número 1–28?
2. ¿La correspondencia esfera física ↔ número impreso permanece fija entre sorteos o puede cambiar? ¿Dónde se registra?
3. ¿Los pesos individuales se miden y registran antes de cada sorteo o se conserva únicamente el rango/resumen?
4. ¿El estuche y la máquina quedan determinados antes del cierre de ventas? ¿Qué registro acredita el momento?
5. ¿Los datos históricos permiten vincular sin ambigüedad cada tira con un concurso y modalidad?
6. ¿Qué registros existen para sustituciones, re-pesajes y cambios de asignación?

## Por qué estos campos son indispensables

Un rango permitido de pesos no identifica qué número corresponde a cada masa. Sin el enlace físico-número y la marca temporal pre-cierre, no es posible construir una característica predictiva válida. Sin calibración y trazabilidad, las diferencias pequeñas pueden ser ruido de medición. Sin conocer cambios de estuche/máquina, se puede atribuir erróneamente a un número un efecto que pertenece al equipo o al periodo.

## Plan de análisis predefinido al recibir datos

1. Calcular hashes de cada archivo recibido y preservar originales inmutables.
2. Verificar integridad documental, correspondencia concurso-modalidad, timestamps, calibración y continuidad de identificadores.
3. Separar variables conocidas antes del cierre de variables posteriores; excluir toda variable no disponible antes del cierre de ventas de predicción para ese concurso.
4. Congelar el mapa esfera-número por periodo/estuche; cuarentenar filas sin correspondencia demostrable.
5. Modelar extracción secuencial sin reemplazo; controlar por estuche, máquina, tipo, periodo y cambios operativos.
6. Evaluar cronológicamente contra uniforme 5-de-28 y baselines preregistrados, sin retocar en el holdout.
7. Corregir multiplicidad, revisar calibración y mantener un e-process Exact5 separado.
8. No recomendar números por peso hasta superar validación prospectiva independiente.

## Límites y clasificación

La existencia de una tira de pesaje no prueba sesgo. Los límites de tolerancia publicados tampoco prueban que las masas sean diferentes de forma relevante ni que la masa afecte la probabilidad de extracción. La hipótesis física permanece **BLOCKED_PROVENANCE** hasta recibir registros primarios completos. No se autoriza selección de números, promoción de modelo ni afirmación de ventaja con datos incompletos o retrospectivos.

## Referencia normativa identificada

Lotería Nacional, SGVO-PRO-05, Procedimiento Sorteos Electrónicos, revisión 39, publicado 20-03-2026:  
https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
