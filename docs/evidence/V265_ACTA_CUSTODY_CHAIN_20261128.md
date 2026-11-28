# V265 — Cadena documental del Acta, anexos y custodia
**Corte: 28 de noviembre de 2026 · Chispazo Clásico electrónico**

## Alcance

Delta nuevo de SGVO-PRO-05 rev. 39, sin repetir frecuencias, pares, tríos ni transiciones. La Normateca lo lista como sustantivo vigente, actualizado el 20-03-2026. Se cruza con el Reglamento Chispazo y la reforma SIDOF/SEGOB para determinar la jerarquía del Acta. No se importan procedimientos de sorteos tradicionales.

Fuentes oficiales:
- SGVO-PRO-05: https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Normateca: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- Reglamento Chispazo, arts. 8, 9 y 15: https://www.loterianacional.gob.mx/Documentos/Legal/ReglamentoJuegos/ChizpasoDOF18062003.pdf
- Reforma art. 8, SIDOF/SEGOB 07-03-2012: https://sidof.segob.gob.mx/notas/docFuente/5236917
- Chispazo electrónico, Clásico 21:00: https://www.loterianacional.gob.mx/Chispazo/Chispazo

## Hallazgos nuevos: políticas 11–17, 19 y 30

1. **Acta y CS-11 son documentos distintos.** La política 11 exige que el Acta contenga lugar, fecha, horario, nombres, roles y firmas de los participantes, Inspector SEGOB, resultados e incidencias. Se anexa la Relación de Ganadores. La tabla de anexos marca para Chispazo Sumario de cierre, CS-11, Sumario de Sorteo y Tira de Pesaje. El artículo 15 del Reglamento exige Acta con antecedentes, resultados e incidentes; el artículo 8 reformado establece que los resultados oficiales son los asentados en esa Acta. La mascarilla pública y CS-11 aislado no sustituyen el Acta.

2. **Custodia digital semanal.** La política 12 ordena grabar en DVD los reportes anexos y la firma electrónica de la Relación de Ganadores del día y entregarlos semanalmente (lunes a domingo), mediante oficio DTT, a la Gerencia de Operación de Concursos y Sorteos para anexarlos a las Actas. Es respaldo posterior, no predictor pre-cierre. No se obtuvieron DVD, hashes ni oficios de entrega por concurso.

3. **Discrepancias SICAL vs. Selección de Ganadores.** La política 13 exige que, si no coinciden ventas/cancelaciones, ganadores o premios, el Acta use la pantalla del sistema administrativo de Selección de Ganadores y agregue la pantalla SICAL. El responsable notifica el mismo día a DTT; DTT solicita aclaración escrita al prestador SICAL y ésta se integra al Acta. Esto describe el rastro esperado, no demuestra que una discrepancia haya ocurrido.

4. **Incidencias y firma diferida.** La política 14 exige registrar en el Acta cualquier incidencia de una etapa que salga del procedimiento y afecte resultados. La política 15 permite firmar el Acta el siguiente día hábil, máximo cinco días hábiles, sólo si no fue posible imprimirla y los resultados no se comprometen; debe dejarse constancia en CS-09. La política 16 exige escanear el Acta firmada y enviarla al OIC. Por tanto, el timestamp de firma o escaneo puede ser posterior al sorteo y no equivale al timestamp del evento.

5. **CS-18 es opcional.** La política 17 dice que el personal podrá usar CS-18 para comunicar debilidades de control y riesgos potenciales. La ausencia del formato no demuestra ausencia de riesgos.

6. **CS-12 y accesos.** La política 19 restringe la sala y exige registrar participantes mediante CS-12. Limpieza y mantenimiento deben asentarse en bitácoras de acceso y realizarse bajo vigilancia institucional. Sirve para auditoría de custodia, no demuestra intervención sobre máquina o estuche.

7. **Dos obligaciones documentales de grabación.** La política 30 contrata grabación desde el pesaje hasta el sorteo; sólo la versión editada del sorteo se incorpora al Acta. La actividad 12.1 también exige que cámaras ubicadas en la sala capten y graben los números expresados por el presentador al aparecer las esferas en exhibidores. El procedimiento no especifica si ambas obligaciones comparten equipo, fuente técnica o archivo; no debe suponerse que el video editado es el máster continuo. No se obtuvo máster, metadatos, hash ni cadena de custodia por concurso.

## Cronología frente al cierre

| Elemento | Momento | ¿Predictor pre-cierre del mismo concurso? |
|---|---|---|
| CS-02 y confirmación inicial de máquina/estuche | Antes del cierre | Sólo con original, ID de activo, hora y procedencia autenticados |
| Cierre SICAL y Sumario | Al cierre; Clásico normalmente 21:00 | No; marca el corte de apuestas |
| Firma de participaciones/cancelaciones | Inmediatamente después del cierre, antes de ceremonia | No; post-cierre/pre-sorteo |
| Tira de Pesaje | Después de verificar SICAL cerrado, antes de cargar | No; post-cierre |
| Cámaras, extracción y exhibidores | Durante el sorteo | No; retrospectivo |
| CS-11 y Relación de Ganadores | Después de extracción/cotejo | No; retrospectivo |
| Acta y anexos | Al concluir ceremonia; firma puede diferirse bajo excepción hasta cinco días hábiles | No; retrospectivo |
| CS-09 | Al documentar incidencia/retraso | Sólo si el hecho y aviso auténtico ya se conocían antes del cierre |
| CS-18 | Comunicación opcional de riesgo | Sólo si fue emitido y recibido antes del cierre |
| DVD semanal de anexos | Entrega lunes-domingo posterior | No |
| MJF y firma impresa | Respaldo diario después de 21:00 | No |

## V265 y dictamen

V265 consume etiquetas machine_id y sphere_set_id, más available_before_close, close_time_local y metadata_known_time_local. Valida cronología declarada, pero no autentica CS-02, Acta, CS-11, Tira, CS-09, CS-12, CS-18, DVD, MJF, video ni sus firmas, hashes o custodia. No consume pesos individuales, mapeo RFID esfera-número, orden de extracción ni timestamps por extracción. Su guard conserva physical_bias_evidence=false, actionable_for_betting=false y anytime_evalue_gate_implemented=false.

Este delta no modifica V265 ni calcula research_edge. Clasificación DOCUMENTED_MECHANISM_ONLY. No usa resultados, histórico ni registros sintéticos; no ejecuta pruebas estadísticas. El script inspecciona esta transcripción y el contrato AST del evaluador; no autentica PDF, firmas o expedientes físicos.

Bloqueos: Acta original y anexos; CS-11 y recibos de cuatro ejemplares; tira con 28 pesos y báscula identificada; CS-02 con seriales/RFID y timestamps; CS-09/CS-18/CS-12; pantallas SICAL y Selección de Ganadores y aclaraciones; DVD semanal/oficio/hashes; MJF; máster continuo y video de sala con metadatos y cadena de custodia.

V294 congelado; histórico canónico intacto; sin escritura en main, merge o promoción. OOS, multiplicidad y anytime e-value siguen sin superar.
